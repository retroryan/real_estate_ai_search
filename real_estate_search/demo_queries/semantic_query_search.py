"""
Natural language semantic search demo using query embeddings.

This module demonstrates semantic search using natural language queries
by generating embeddings on-the-fly and performing KNN search.
"""

from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager
from elasticsearch import Elasticsearch
import logging
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.columns import Columns

from .result_models import PropertySearchResult
from ..models import PropertyListing
from .models import DemoQueryResult
from ..embeddings import QueryEmbeddingService, EmbeddingConfig
from ..embeddings.exceptions import (
    EmbeddingServiceError, 
    EmbeddingGenerationError,
    ConfigurationError
)
from ..config import AppConfig

# ============================================================================
# CONSTANTS
# ============================================================================

# Search configuration
DEFAULT_QUERY = "modern home with mountain views and open floor plan"
DEFAULT_SIZE = 10
KNN_NUM_CANDIDATES_MULTIPLIER = 10
MAX_DISPLAY_RESULTS = 10
TOP_MATCH_DISPLAY_COUNT = 3

# Property fields to retrieve
PROPERTY_FIELDS = [
    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
    "square_feet", "address", "description", "features", "year_built"
]

BASIC_PROPERTY_FIELDS = [
    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
    "square_feet", "address", "description"
]

# Example queries for demo
EXAMPLE_QUERIES = [
    ("cozy family home near good schools and parks", "Family-oriented home search"),
    ("modern downtown condo with city views", "Urban condo search"),
    ("spacious property with home office and fast internet", "Work-from-home property search"),
    ("eco-friendly house with solar panels and energy efficiency", "Sustainable home search"),
    ("luxury estate with pool and entertainment areas", "Luxury property search")
]

# Match explanations for example queries
MATCH_EXPLANATIONS = {
    1: "AI understands 'family' context - properties with multiple bedrooms, residential neighborhoods, space for children",
    2: "Semantic search identifies urban/city characteristics - downtown locations, modern architecture, high-rise features", 
    3: "AI recognizes work-from-home needs - spacious properties, dedicated office spaces, quiet environments",
    4: "Embeddings understand sustainability concepts - energy-efficient features, eco-friendly materials, green amenities",
    5: "Semantic search finds luxury indicators - high-end finishes, premium amenities, entertainment features"
}

logger = logging.getLogger(__name__)
console = Console()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@contextmanager
def get_embedding_service(config: Optional[AppConfig] = None):
    """
    Context manager for embedding service lifecycle management.
    
    Args:
        config: Optional application configuration
        
    Yields:
        QueryEmbeddingService: Initialized embedding service
        
    Raises:
        ConfigurationError: If service cannot be configured
        EmbeddingServiceError: If service cannot be initialized
    """
    if config is None:
        config = AppConfig.load()
    
    service = None
    try:
        service = QueryEmbeddingService(config=config.embedding)
        service.initialize()
        yield service
    finally:
        if service:
            service.close()


def convert_to_property_results(raw_results: List[Dict[str, Any]]) -> List[PropertyListing]:
    """
    Convert raw Elasticsearch results to PropertyListing objects.
    
    Args:
        raw_results: List of raw result dictionaries from Elasticsearch
        
    Returns:
        List of PropertyListing objects
    """
    from ..converters import PropertyConverter
    return PropertyConverter.from_elasticsearch_batch(raw_results)


def build_knn_query(
    query_vector: List[float], 
    size: int = DEFAULT_SIZE,
    fields: List[str] = None
) -> Dict[str, Any]:
    """
    Build a KNN query for semantic search.
    
    Args:
        query_vector: The embedding vector for the query
        size: Number of results to return
        fields: Fields to retrieve (defaults to PROPERTY_FIELDS)
        
    Returns:
        Elasticsearch query dictionary
    """
    if fields is None:
        fields = PROPERTY_FIELDS
        
    return {
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": size,
            "num_candidates": min(100, size * KNN_NUM_CANDIDATES_MULTIPLIER)
        },
        "size": size,
        "_source": fields
    }


def build_keyword_query(
    query_text: str,
    size: int = DEFAULT_SIZE,
    fields: List[str] = None
) -> Dict[str, Any]:
    """
    Build a keyword-based multi-match query.
    
    Args:
        query_text: The text query
        size: Number of results to return
        fields: Fields to retrieve (defaults to PROPERTY_FIELDS)
        
    Returns:
        Elasticsearch query dictionary
    """
    if fields is None:
        fields = PROPERTY_FIELDS
        
    return {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": [
                    "description^2",
                    "features^1.5",
                    "amenities^1.5",
                    "address.city",
                    "address.neighborhood"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "size": size,
        "_source": fields
    }


def execute_search(
    es_client: Elasticsearch,
    query: Dict[str, Any],
    index: str = "properties"
) -> Tuple[List[Dict[str, Any]], int, float]:
    """
    Execute an Elasticsearch search and return processed results.
    
    Args:
        es_client: Elasticsearch client
        query: Query dictionary
        index: Index to search
        
    Returns:
        Tuple of (results list, total hits, execution time in ms)
    """
    start_time = time.time()
    response = es_client.search(index=index, body=query)
    execution_time_ms = (time.time() - start_time) * 1000
    
    results = []
    for hit in response['hits']['hits']:
        result = hit['_source']
        result['_score'] = hit['_score']
        result['_similarity_score'] = hit['_score']
        results.append(result)
    
    total_hits = response['hits']['total']['value']
    return results, total_hits, execution_time_ms


def create_error_result(
    query_name: str,
    query_description: str,
    error_message: str,
    execution_time_ms: int = 0
) -> PropertySearchResult:
    """
    Create a PropertySearchResult for error cases.
    
    Args:
        query_name: Name of the query
        query_description: Description of the query
        error_message: Error message to include
        execution_time_ms: Execution time if available
        
    Returns:
        PropertySearchResult with error information
    """
    return PropertySearchResult(
        query_name=query_name,
        query_description=query_description,
        execution_time_ms=execution_time_ms,
        total_hits=0,
        returned_hits=0,
        results=[],
        query_dsl={"error": error_message},
        es_features=[f"Error: {error_message}"]
    )


# ============================================================================
# MAIN DEMO FUNCTIONS
# ============================================================================

def demo_natural_language_search(
    es_client: Elasticsearch,
    query: str = DEFAULT_QUERY,
    size: int = DEFAULT_SIZE,
    config: Optional[AppConfig] = None
) -> PropertySearchResult:
    """
    Demo: Natural language semantic search using query embeddings.
    
    This demo shows how to:
    1. Take a natural language query
    2. Generate an embedding using the same model as property embeddings
    3. Use KNN search to find semantically similar properties
    4. Return results ranked by semantic similarity
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        config: Application configuration (for embedding service)
        
    Returns:
        PropertySearchResult with semantically similar properties
    """
    query_name = f"Natural Language Search: '{query}'"
    query_description = f"Semantic search using natural language query: '{query}'"
    
    # Generate query embedding
    embedding_time_ms = 0
    query_embedding = None
    
    try:
        with get_embedding_service(config) as embedding_service:
            start_time = time.time()
            logger.info(f"Generating embedding for query: '{query}'")
            query_embedding = embedding_service.embed_query(query)
            embedding_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Generated query embedding in {embedding_time_ms:.1f}ms")
    except (ConfigurationError, EmbeddingServiceError, EmbeddingGenerationError) as e:
        logger.error(f"Failed to generate embedding: {e}")
        return create_error_result(
            query_name=query_name,
            query_description=query_description,
            error_message=f"Embedding generation failed: {str(e)}"
        )
    
    # Build and execute KNN query
    es_query = build_knn_query(query_embedding, size)
    
    try:
        raw_results, total_hits, search_time_ms = execute_search(
            es_client, es_query, "properties"
        )
        
        total_time_ms = embedding_time_ms + search_time_ms
        property_results = convert_to_property_results(raw_results)
        
        result = PropertySearchResult(
            query_name=query_name,
            query_description=query_description,
            execution_time_ms=int(total_time_ms),
            total_hits=total_hits,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=es_query,
            es_features=[
                f"Query Embedding Generation - {embedding_time_ms:.1f}ms using Voyage-3 model",
                f"KNN Search - {search_time_ms:.1f}ms for vector similarity search",
                "Dense Vectors - 1024-dimensional embeddings for semantic understanding",
                "Natural Language Understanding - Convert text queries to semantic vectors",
                "Cosine Similarity - Vector distance metric for relevance ranking"
            ],
            indexes_used=[
                "properties index - Real estate listings with AI embeddings",
                f"Searching for {size} properties semantically similar to query"
            ],
            aggregations={
                "timing_breakdown": {
                    "embedding_generation_ms": embedding_time_ms,
                    "elasticsearch_search_ms": search_time_ms,
                    "total_ms": total_time_ms
                }
            }
        )
        
        # Display rich formatted results
        display_natural_language_results(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in natural language search: {e}")
        return create_error_result(
            query_name=query_name,
            query_description=query_description,
            error_message=f"Search failed: {str(e)}",
            execution_time_ms=int(embedding_time_ms)
        )


def demo_natural_language_examples(
    es_client: Elasticsearch,
    config: Optional[AppConfig] = None
) -> List[DemoQueryResult]:
    """
    Run multiple natural language search examples.
    
    Demonstrates various types of natural language queries that can be
    understood semantically by the embedding model.
    
    Args:
        es_client: Elasticsearch client
        config: Application configuration
        
    Returns:
        List[DemoQueryResult] containing individual query results
    """
    # Early return if no examples configured
    if not EXAMPLE_QUERIES:
        console.print("[red]No example queries configured[/red]")
        return []
    
    # Display header for the examples demo
    console.print("\n" + "=" * 80)
    console.print("🔍 NATURAL LANGUAGE SEARCH EXAMPLES")
    console.print("=" * 80)
    console.print("Demonstrating semantic understanding with AI embeddings")
    console.print("Multiple example queries showing various search patterns\n")
    
    demo_results = []
    all_properties = []
    total_execution_time = 0
    total_hits_sum = 0
    query_descriptions = []
    successful_queries = 0
    failed_queries = 0
    
    try:
        with get_embedding_service(config) as embedding_service:
            for i, (query_text, query_description) in enumerate(EXAMPLE_QUERIES, 1):
                # Generate embedding
                start_time = time.time()
                try:
                    query_embedding = embedding_service.embed_query(query_text)
                    embedding_time_ms = (time.time() - start_time) * 1000
                    
                    # Build and execute query
                    es_query = build_knn_query(
                        query_embedding, 
                        size=5, 
                        fields=BASIC_PROPERTY_FIELDS
                    )
                    
                    raw_results, total_hits, search_time_ms = execute_search(
                        es_client, es_query, "properties"
                    )
                    
                    total_time_ms = embedding_time_ms + search_time_ms
                    property_results = convert_to_property_results(raw_results)
                    
                    # Collect results
                    all_properties.extend(property_results)
                    total_execution_time += total_time_ms
                    total_hits_sum += total_hits
                    query_descriptions.append(f"{i}. {query_description}: '{query_text}'")
                    successful_queries += 1
                    
                    # Display individual query results
                    console.print(f"\n[bold cyan]Example {i}: {query_description}[/bold cyan]")
                    console.print(f"Query: [yellow]{query_text}[/yellow]")
                    console.print(f"Found: {total_hits} properties • Time: {total_time_ms:.1f}ms")
                    
                    if property_results:
                        console.print("[bold]Top 3 Matches:[/bold]")
                        for j, prop in enumerate(property_results[:3], 1):
                            console.print(format_property_summary(prop, j))
                    
                    # Add match explanation
                    match_explanation = MATCH_EXPLANATIONS.get(i, "")
                    if match_explanation:
                        console.print(f"[bold yellow]Why these match:[/bold yellow] {match_explanation}\n")
                    
                    # Create DemoQueryResult for this individual query
                    individual_result = DemoQueryResult(
                        query_name=f"Example {i}: {query_description}",
                        query_description=query_text,
                        execution_time_ms=int(total_time_ms),
                        total_hits=total_hits,
                        returned_hits=len(property_results),
                        results=[prop.model_dump() for prop in property_results],
                        query_dsl=es_query
                    )
                    demo_results.append(individual_result)
                    
                except Exception as e:
                    logger.error(f"Failed to process query {i}: {e}")
                    query_descriptions.append(f"{i}. {query_description}: ERROR - {str(e)}")
                    failed_queries += 1
                    console.print(f"\n[red]Example {i} failed: {str(e)}[/red]")
                    
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        console.print(f"[red]Failed to initialize embedding service: {str(e)}[/red]")
        return []
    
    # Check if any queries succeeded
    if successful_queries == 0:
        console.print(f"[red]All {len(EXAMPLE_QUERIES)} queries failed[/red]")
        return []
    
    # Display summary
    display_examples_summary_stats(successful_queries, total_execution_time, total_hits_sum)
    
    # Return the list of individual demo results
    return demo_results


def demo_semantic_vs_keyword_comparison(
    es_client: Elasticsearch,
    query: str = "stunning views from modern kitchen",
    size: int = 5,
    config: Optional[AppConfig] = None
) -> PropertySearchResult:
    """
    Compare semantic search with traditional keyword search.
    
    Runs the same query using both semantic (embedding-based) and
    keyword (text-based) search to demonstrate the differences.
    
    Args:
        es_client: Elasticsearch client
        query: Natural language search query
        size: Number of results to return
        config: Application configuration
        
    Returns:
        PropertySearchResult with combined results from both search methods
    """
    # Run semantic search
    semantic_results = []
    semantic_hits = 0
    semantic_time = 0
    
    try:
        with get_embedding_service(config) as embedding_service:
            start_time = time.time()
            query_embedding = embedding_service.embed_query(query)
            embedding_time = (time.time() - start_time) * 1000
            
            semantic_query = build_knn_query(query_embedding, size)
            raw_results, semantic_hits, search_time = execute_search(
                es_client, semantic_query, "properties"
            )
            semantic_results = raw_results
            semantic_time = embedding_time + search_time
            
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
    
    # Run keyword search
    keyword_query = build_keyword_query(query, size)
    keyword_results = []
    keyword_hits = 0
    keyword_time = 0
    
    try:
        raw_results, keyword_hits, keyword_time = execute_search(
            es_client, keyword_query, "properties"
        )
        keyword_results = raw_results
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
    
    # Compare and combine results
    semantic_ids = {r.get('listing_id') for r in semantic_results if 'listing_id' in r}
    keyword_ids = {r.get('listing_id') for r in keyword_results if 'listing_id' in r}
    overlap = semantic_ids & keyword_ids
    
    comparison_results = {
        'semantic': {
            'total_hits': semantic_hits,
            'top_results': semantic_results[:3],
            'execution_time_ms': semantic_time
        },
        'keyword': {
            'total_hits': keyword_hits,
            'top_results': keyword_results[:3],
            'execution_time_ms': keyword_time
        },
        'comparison': {
            'overlap_count': len(overlap),
            'unique_to_semantic': len(semantic_ids - keyword_ids),
            'unique_to_keyword': len(keyword_ids - semantic_ids),
            'semantic_top_score': semantic_results[0].get('_score', 0) if semantic_results else 0,
            'keyword_top_score': keyword_results[0].get('_score', 0) if keyword_results else 0
        }
    }
    
    # Combine results for display
    combined_results = []
    seen_ids = set()
    
    # Add semantic results first with search type marker
    for res in semantic_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'semantic'
            res['description'] = f"[SEMANTIC] {res.get('description', '')}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    # Add unique keyword results with search type marker
    for res in keyword_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'keyword'
            res['description'] = f"[KEYWORD] {res.get('description', '')}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    # Convert to PropertyResult objects
    property_results = convert_to_property_results(combined_results)
    
    result = PropertySearchResult(
        query_name="Demo 13: Semantic vs Keyword Search Comparison (Combined Results)",
        query_description=f"Comparing semantic and keyword search for: '{query}'",
        execution_time_ms=int(semantic_time + keyword_time),
        total_hits=semantic_hits + keyword_hits,
        returned_hits=len(property_results),
        results=property_results,
        query_dsl={
            "semantic_query": {"knn": "...truncated..."},
            "keyword_query": keyword_query
        },
        es_features=[
            "SEMANTIC SEARCH:",
            f"  • Found {semantic_hits} properties in {semantic_time:.1f}ms",
            f"  • Top score: {comparison_results['comparison']['semantic_top_score']:.3f}",
            "  • Uses AI embeddings for semantic understanding",
            "",
            "KEYWORD SEARCH:",
            f"  • Found {keyword_hits} properties in {keyword_time:.1f}ms",
            f"  • Top score: {comparison_results['comparison']['keyword_top_score']:.3f}",
            "  • Uses traditional text matching with BM25",
            "",
            "COMPARISON:",
            f"  • Overlap in top {size}: {len(overlap)} properties",
            f"  • Unique to semantic: {len(semantic_ids - keyword_ids)}",
            f"  • Unique to keyword: {len(keyword_ids - semantic_ids)}",
            "",
            "RESULTS TABLE BELOW:",
            "  • Shows combined results from BOTH search methods",
            "  • Results marked with [SEMANTIC] or [KEYWORD] prefix",
            "  • Semantic results appear first, followed by keyword-only results"
        ],
        indexes_used=[
            "properties index - tested with both search methods",
            f"Query tested: '{query}'"
        ],
        aggregations=comparison_results
    )
    
    # Display rich formatted comparison
    display_semantic_vs_keyword_comparison(result, query, comparison_results)
    return result


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def display_natural_language_results(result: PropertySearchResult):
    """Display natural language search results with rich formatting."""
    
    if not result.results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Extract query from result description
    query_text = DEFAULT_QUERY
    if "'" in result.query_description:
        query_text = result.query_description.split("'")[1]
    
    # Create results table
    table = Table(title="🤖 Natural Language Search Results", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Property", style="white")
    table.add_column("Price", style="green", justify="right")
    table.add_column("Beds/Baths", style="yellow", justify="center")
    table.add_column("Sq Ft", style="magenta", justify="right")
    table.add_column("Score", style="bright_green", justify="right")
    
    for i, prop in enumerate(result.results[:MAX_DISPLAY_RESULTS], 1):
        address = prop.address if hasattr(prop, 'address') else {}
        street = address.get('street', 'Unknown') if isinstance(address, dict) else 'Unknown'
        city = address.get('city', '') if isinstance(address, dict) else ''
        
        table.add_row(
            str(i),
            f"{street}\n{city}",
            f"${prop.price:,.0f}" if hasattr(prop, 'price') and prop.price else 'N/A',
            f"{prop.bedrooms if hasattr(prop, 'bedrooms') else 'N/A'}/{prop.bathrooms if hasattr(prop, 'bathrooms') else 'N/A'}",
            f"{prop.square_feet:,}" if hasattr(prop, 'square_feet') and prop.square_feet else 'N/A',
            f"{prop.score:.3f}" if hasattr(prop, 'score') and prop.score else "0.000"
        )
    
    console.print(table)
    
    # Show detailed match analysis
    console.print(f"\n[bold cyan]🔍 Why These Properties Match: '{query_text}'[/bold cyan]")
    
    # Show property descriptions with match highlighting
    for i, prop in enumerate(result.results[:TOP_MATCH_DISPLAY_COUNT], 1):
        display_property_match_panel(prop, i, query_text)
    
    # Add overall explanation
    display_semantic_search_explanation()


def display_property_match_panel(prop: PropertyListing, index: int, query_text: str):
    """Display a single property match with insights."""
    # PropertyListing always has these fields
    address = prop.address
    desc = prop.description or 'No description available'
    
    # Generate match insights
    insights = generate_match_insights(query_text, desc, prop)
    
    street = address.get('street', 'Unknown') if isinstance(address, dict) else 'Unknown'
    panel_content = f"[bold]{street}[/bold]\n"
    panel_content += f"[yellow]${prop.price:,.0f}[/yellow] • " if hasattr(prop, 'price') and prop.price else "[yellow]$N/A[/yellow] • "
    panel_content += f"{prop.bedrooms if hasattr(prop, 'bedrooms') else 'N/A'} bed / {prop.bathrooms if hasattr(prop, 'bathrooms') else 'N/A'} bath • "
    panel_content += f"{prop.square_feet:,} sq ft\n\n" if hasattr(prop, 'square_feet') and prop.square_feet else "N/A sq ft\n\n"
    panel_content += f"[bright_blue]{desc}[/bright_blue]\n\n"
    
    if insights:
        panel_content += "[bold green]Match Insights:[/bold green]\n"
        for insight in insights:
            panel_content += f"{insight}\n"
    
    panel = Panel(
        panel_content.strip(),
        title=f"Match #{index} - AI Semantic Analysis",
        border_style="green"
    )
    console.print(panel)


def generate_match_insights(query_text: str, description: str, prop: PropertyListing) -> List[str]:
    """Generate insights about why a property matches the query."""
    insights = []
    query_lower = query_text.lower()
    desc_lower = description.lower() if description else ''
    
    if 'modern' in query_lower and any(word in desc_lower for word in ['modern', 'contemporary', 'updated', 'new']):
        insights.append("✓ Modern/contemporary features mentioned")
    if 'mountain' in query_lower and any(word in desc_lower for word in ['view', 'mountain', 'vista', 'scenic']):
        insights.append("✓ Views/scenic location described")  
    if 'open' in query_lower and any(word in desc_lower for word in ['open', 'spacious', 'floor plan', 'concept']):
        insights.append("✓ Open/spacious layout features")
    if 'home' in query_lower and any(word in desc_lower for word in ['family', 'home', 'residential', 'neighborhood']):
        insights.append("✓ Family-friendly/residential character")
        
    # Add score insight
    insights.append(f"🎯 Semantic similarity score: {prop.score:.3f}" if hasattr(prop, 'score') and prop.score else "🎯 Semantic similarity score: 0.000")
    
    return insights


def display_semantic_search_explanation():
    """Display explanation of how semantic search works."""
    explanation = Panel(
        f"[bold yellow]How Semantic Search Works:[/bold yellow]\n\n"
        f"• Query converted to 1024-dimensional vector using Voyage-3 AI model\n"
        f"• Property descriptions pre-encoded with same model during indexing\n"
        f"• Vector similarity (cosine distance) finds semantically related properties\n"
        f"• Results ranked by conceptual similarity, not just keyword matching\n"
        f"• AI understands context: 'modern home' → contemporary, updated, new construction",
        title="🧠 AI Understanding",
        border_style="yellow"
    )
    console.print(explanation)




def format_property_summary(prop: PropertyListing, index: int) -> str:
    """Format a property summary for display."""
    # PropertyListing always has these fields - use the model's properties
    desc = prop.description or 'No description available'
    street = prop.address.street or 'Unknown'
    
    summary = f"[bold]{index}. {street}[/bold]\n"
    summary += f"   [green]{prop.display_price}[/green] • "
    summary += f"{prop.bedrooms or 'N/A'} bed / {prop.bathrooms or 'N/A'} bath • "
    summary += f"[cyan]Score: {prop.score:.3f}[/cyan]\n" if prop.score else "[cyan]Score: 0.000[/cyan]\n"
    summary += f"   [dim]{desc}[/dim]\n\n"
    
    return summary


def display_examples_summary_stats(num_queries: int, total_time: float, total_found: int):
    """Display summary statistics for example queries."""
    summary = Panel(
        f"[green]✓ Completed {num_queries} natural language searches[/green]\n"
        f"[yellow]Total execution time: {total_time:.0f}ms[/yellow]\n"
        f"[cyan]Total properties found: {total_found}[/cyan]\n"
        f"[magenta]Average time per query: {total_time/num_queries:.1f}ms[/magenta]",
        title="[bold green]Summary[/bold green]",
        border_style="green"
    )
    console.print(summary)


def display_semantic_vs_keyword_comparison(result: PropertySearchResult, query: str, comparison: dict):
    """Display semantic vs keyword comparison with rich formatting."""
    
    console.print("\n[bold cyan]Semantic vs Keyword Search Comparison[/bold cyan]")
    console.print("=" * 70)
    console.print(f"\n[yellow]Query: '{query}'[/yellow]\n")
    
    # Create side-by-side comparison
    semantic_data = comparison['semantic']
    keyword_data = comparison['keyword']
    
    # Semantic Search Results Panel
    semantic_content = f"[green]Found:[/green] {semantic_data['total_hits']} properties\n"
    semantic_content += f"[yellow]Time:[/yellow] {semantic_data['execution_time_ms']:.1f}ms\n"
    semantic_content += f"[cyan]Top Score:[/cyan] {comparison['comparison']['semantic_top_score']:.3f}\n\n"
    semantic_content += "[bold]Top 3 Results:[/bold]\n"
    
    for i, prop in enumerate(semantic_data['top_results'][:3], 1):
        addr = prop.get('address', {})
        semantic_content += f"{i}. {addr.get('street', 'Unknown')}\n"
        semantic_content += f"   ${prop.get('price', 0):,.0f} • Score: {prop.get('_score', 0):.3f}\n"
    
    semantic_panel = Panel(
        semantic_content.strip(),
        title="[bold green]🤖 Semantic Search (AI Embeddings)[/bold green]",
        border_style="green"
    )
    
    # Keyword Search Results Panel  
    keyword_content = f"[green]Found:[/green] {keyword_data['total_hits']} properties\n"
    keyword_content += f"[yellow]Time:[/yellow] {keyword_data['execution_time_ms']:.1f}ms\n"
    keyword_content += f"[cyan]Top Score:[/cyan] {comparison['comparison']['keyword_top_score']:.3f}\n\n"
    keyword_content += "[bold]Top 3 Results:[/bold]\n"
    
    for i, prop in enumerate(keyword_data['top_results'][:3], 1):
        addr = prop.get('address', {})
        keyword_content += f"{i}. {addr.get('street', 'Unknown')}\n"
        keyword_content += f"   ${prop.get('price', 0):,.0f} • Score: {prop.get('_score', 0):.3f}\n"
    
    keyword_panel = Panel(
        keyword_content.strip(),
        title="[bold blue]📝 Keyword Search (BM25)[/bold blue]",
        border_style="blue"
    )
    
    # Display side by side
    columns = Columns([semantic_panel, keyword_panel], equal=True, expand=True)
    console.print(columns)
    
    # Comparison Analysis
    display_comparison_analysis(comparison['comparison'])


def display_comparison_analysis(comp: Dict[str, Any]):
    """Display analysis of search comparison."""
    analysis = f"""[bold]Analysis:[/bold]
    
• [cyan]Result Overlap:[/cyan] {comp['overlap_count']} properties appear in both top 5 results
• [green]Unique to Semantic:[/green] {comp['unique_to_semantic']} properties found only by semantic search
• [blue]Unique to Keyword:[/blue] {comp['unique_to_keyword']} properties found only by keyword search

[bold]Key Insights:[/bold]
• Semantic search understands meaning and context beyond exact word matches
• Keyword search is faster and finds exact phrase matches effectively
• Combining both approaches can provide comprehensive search coverage"""
    
    analysis_panel = Panel(
        analysis,
        title="[bold yellow]📊 Comparison Analysis[/bold yellow]",
        border_style="yellow"
    )
    console.print(analysis_panel)