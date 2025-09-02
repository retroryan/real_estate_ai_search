"""
Natural language semantic search demo using query embeddings.

This module demonstrates semantic search using natural language queries
by generating embeddings on-the-fly and performing KNN search.
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.columns import Columns

from .models import DemoQueryResult
from ..embeddings import QueryEmbeddingService, EmbeddingConfig
from ..embeddings.exceptions import (
    EmbeddingServiceError, 
    EmbeddingGenerationError,
    ConfigurationError
)
from ..config import AppConfig

logger = logging.getLogger(__name__)
console = Console()


def demo_natural_language_search(
    es_client: Elasticsearch,
    query: str = "modern home with mountain views and open floor plan",
    size: int = 10,
    config: Optional[AppConfig] = None
) -> DemoQueryResult:
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
        DemoQueryResult with semantically similar properties
    """
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Initialize embedding service
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
    except (ConfigurationError, EmbeddingServiceError) as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query}'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": f"Embedding service initialization failed: {str(e)}"},
            es_features=["Failed to generate query embedding"]
        )
    
    # Generate query embedding
    start_time = time.time()
    try:
        logger.info(f"Generating embedding for query: '{query}'")
        query_embedding = embedding_service.embed_query(query)
        embedding_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Generated query embedding in {embedding_time_ms:.1f}ms")
    except EmbeddingGenerationError as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query}'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": f"Embedding generation failed: {str(e)}"},
            es_features=["Failed to generate query embedding"]
        )
    finally:
        # Clean up embedding service
        embedding_service.close()
    
    # Build KNN query with generated embedding
    es_query = {
        "knn": {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": size,
            "num_candidates": min(100, size * 10)
        },
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features", "amenities"
        ]
    }
    
    # Execute search
    try:
        search_start = time.time()
        response = es_client.search(index="properties", body=es_query)
        search_time_ms = (time.time() - search_start) * 1000
        
        # Process results
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            result['_similarity_score'] = hit['_score']
            results.append(result)
        
        total_time_ms = embedding_time_ms + search_time_ms
        
        result = DemoQueryResult(
            query_name=f"Natural Language Search: '{query}'",
            query_description=f"Semantic search using natural language query: '{query}'",
            execution_time_ms=int(total_time_ms),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
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
        return DemoQueryResult(
            query_name=f"Natural Language Search: '{query}'",
            query_description="Natural language semantic search using query embeddings",
            execution_time_ms=int(embedding_time_ms),
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=es_query,
            es_features=[f"Search failed: {str(e)}"]
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
        List of DemoQueryResult objects, one for each example query
    """
    
    example_queries = [
        ("cozy family home near good schools and parks", "Family-oriented home search"),
        ("modern downtown condo with city views", "Urban condo search"),
        ("spacious property with home office and fast internet", "Work-from-home property search"),
        ("eco-friendly house with solar panels and energy efficiency", "Sustainable home search"),
        ("luxury estate with pool and entertainment areas", "Luxury property search")
    ]
    
    demo_results = []
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Initialize embedding service once for all queries
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        # Return empty list on initialization failure
        return []
    
    try:
        for i, (query_text, query_description) in enumerate(example_queries, 1):
            # Generate embedding
            start_time = time.time()
            try:
                query_embedding = embedding_service.embed_query(query_text)
            except Exception as e:
                logger.error(f"Failed to generate embedding for query {i}: {e}")
                # Create error result for this query
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=0,
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl={"error": f"Embedding generation failed: {str(e)}"},
                    es_features=[f"Failed to generate embedding for query {i}"]
                ))
                continue
            
            # Build and execute query
            es_query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": 5,
                    "num_candidates": 50
                },
                "size": 5,
                "_source": [
                    "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                    "square_feet", "address", "description"
                ]
            }
            
            try:
                response = es_client.search(index="properties", body=es_query)
                query_time = (time.time() - start_time) * 1000
                
                # Process results for this query
                results = []
                for hit in response['hits']['hits']:
                    result = hit['_source']
                    result['_score'] = hit['_score']
                    result['_similarity_score'] = hit['_score']
                    results.append(result)
                
                # Create DemoQueryResult for this specific example
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=int(query_time),
                    total_hits=response['hits']['total']['value'],
                    returned_hits=len(results),
                    results=results,
                    query_dsl=es_query,
                    es_features=[
                        f"Query {i} of {len(example_queries)}: {query_description}",
                        f"Execution time: {query_time:.1f}ms",
                        "KNN search with 1024-dimensional embeddings",
                        "Semantic understanding of natural language"
                    ],
                    indexes_used=[
                        "properties index with pre-computed embeddings",
                        f"Found {response['hits']['total']['value']} semantically similar properties"
                    ]
                ))
                
            except Exception as e:
                logger.error(f"Search failed for query {i}: {e}")
                demo_results.append(DemoQueryResult(
                    query_name=f"Example {i}: {query_description}",
                    query_description=f"Natural language search: '{query_text}'",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl=es_query,
                    es_features=[f"Search failed: {str(e)}"]
                ))
    
    finally:
        embedding_service.close()
    
    # Display rich formatted results for all examples
    display_natural_language_examples_results(demo_results)
    return demo_results


def display_natural_language_examples_results(results: List[DemoQueryResult]):
    """Display natural language examples with rich formatting."""
    
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return
    
    console.print("\n[bold cyan]Natural Language Query Examples[/bold cyan]")
    console.print("=" * 70)
    
    for idx, result in enumerate(results, 1):
        # Extract query text from the description
        query_text = result.query_description.split("'")[1] if "'" in result.query_description else result.query_description
        
        # Create a panel for each example
        panel_content = f"[cyan]Query:[/cyan] [yellow]{query_text}[/yellow]\n"
        panel_content += f"[green]Found:[/green] {result.total_hits} properties\n"
        panel_content += f"[yellow]Time:[/yellow] {result.execution_time_ms}ms\n\n"
        
        if result.results:
            panel_content += "[bold]Top 3 Matches:[/bold]\n\n"
            for i, prop in enumerate(result.results[:3], 1):
                address = prop.get('address', {})
                desc = prop.get('description', 'No description available')
                
                # Show full description (no truncation)
                
                panel_content += f"[bold]{i}. {address.get('street', 'Unknown')}[/bold]\n"
                panel_content += f"   [green]${prop.get('price', 0):,.0f}[/green] • "
                panel_content += f"{prop.get('bedrooms', 'N/A')} bed / {prop.get('bathrooms', 'N/A')} bath • "
                panel_content += f"[cyan]Score: {prop.get('_score', 0):.3f}[/cyan]\n"
                panel_content += f"   [dim]{desc}[/dim]\n\n"
        
        # Add why it matches explanation based on query type
        match_explanation = get_match_explanation(idx, query_text)
        if match_explanation:
            panel_content += f"\n[bold yellow]Why these match:[/bold yellow] {match_explanation}"
        
        panel = Panel(
            panel_content.strip(),
            title=f"[bold]Example {idx}: {result.query_name.split(': ')[1] if ': ' in result.query_name else result.query_name}[/bold]",
            border_style="cyan"
        )
        console.print(panel)
    
    # Summary
    total_time = sum(r.execution_time_ms for r in results)
    total_found = sum(r.total_hits for r in results)
    
    summary = Panel(
        f"[green]✓ Completed {len(results)} natural language searches[/green]\n"
        f"[yellow]Total execution time: {total_time}ms[/yellow]\n"
        f"[cyan]Total properties found: {total_found}[/cyan]\n"
        f"[magenta]Average time per query: {total_time/len(results):.1f}ms[/magenta]",
        title="[bold green]Summary[/bold green]",
        border_style="green"
    )
    console.print(summary)


def get_match_explanation(example_idx: int, query_text: str) -> str:
    """Get explanation for why properties match each specific query type."""
    explanations = {
        1: "AI understands 'family' context - properties with multiple bedrooms, residential neighborhoods, space for children",
        2: "Semantic search identifies urban/city characteristics - downtown locations, modern architecture, high-rise features", 
        3: "AI recognizes work-from-home needs - spacious properties, dedicated office spaces, quiet environments",
        4: "Embeddings understand sustainability concepts - energy-efficient features, eco-friendly materials, green amenities",
        5: "Semantic search finds luxury indicators - high-end finishes, premium amenities, entertainment features"
    }
    return explanations.get(example_idx, "")


def demo_semantic_vs_keyword_comparison(
    es_client: Elasticsearch,
    query: str = "stunning views from modern kitchen",
    size: int = 5,
    config: Optional[AppConfig] = None
) -> DemoQueryResult:
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
        Dictionary with 'semantic' and 'keyword' DemoQueryResults
    """
    
    # Load config if not provided
    if config is None:
        config = AppConfig.load()
    
    # Run semantic search
    semantic_start = time.time()
    
    # Initialize embedding service
    try:
        embedding_service = QueryEmbeddingService(config=config.embedding)
        embedding_service.initialize()
        query_embedding = embedding_service.embed_query(query)
        embedding_service.close()
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        query_embedding = None
    
    semantic_results = []
    semantic_hits = 0
    
    if query_embedding:
        semantic_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": size,
                "num_candidates": size * 10
            },
            "size": size,
            "_source": [
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description", "features", "amenities", "year_built"
            ]
        }
        
        try:
            response = es_client.search(index="properties", body=semantic_query)
            semantic_hits = response['hits']['total']['value']
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                semantic_results.append(result)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
    
    semantic_time = (time.time() - semantic_start) * 1000
    
    # Run keyword search
    keyword_start = time.time()
    keyword_query = {
        "query": {
            "multi_match": {
                "query": query,
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
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features", "amenities", "year_built"
        ]
    }
    
    keyword_results = []
    keyword_hits = 0
    
    try:
        response = es_client.search(index="properties", body=keyword_query)
        keyword_hits = response['hits']['total']['value']
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['_score'] = hit['_score']
            keyword_results.append(result)
    except Exception as e:
        logger.error(f"Error in keyword search: {e}")
    
    keyword_time = (time.time() - keyword_start) * 1000
    
    # Compare results
    semantic_ids = {r.get('listing_id') for r in semantic_results if 'listing_id' in r}
    keyword_ids = {r.get('listing_id') for r in keyword_results if 'listing_id' in r}
    overlap = semantic_ids & keyword_ids
    
    # Combine results for comparison
    comparison_results = {
        'semantic': {
            'total_hits': semantic_hits,
            'top_results': semantic_results[:3] if semantic_results else [],
            'execution_time_ms': semantic_time
        },
        'keyword': {
            'total_hits': keyword_hits,
            'top_results': keyword_results[:3] if keyword_results else [],
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
    
    # Combine semantic and keyword results for display, prioritizing semantic results
    combined_results = []
    seen_ids = set()
    
    # Add semantic results first
    for res in semantic_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'semantic'
            # Prepend search type to description for visibility
            original_desc = res.get('description', '')
            res['description'] = f"[SEMANTIC] {original_desc}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    # Add keyword results that aren't already in the list
    for res in keyword_results:
        if res.get('listing_id') not in seen_ids:
            res['search_type'] = 'keyword'
            # Prepend search type to description for visibility
            original_desc = res.get('description', '')
            res['description'] = f"[KEYWORD] {original_desc}"
            combined_results.append(res)
            seen_ids.add(res.get('listing_id'))
    
    result = DemoQueryResult(
        query_name="Demo 13: Semantic vs Keyword Search Comparison (Combined Results)",
        query_description=f"Comparing semantic and keyword search for: '{query}'",
        execution_time_ms=int(semantic_time + keyword_time),
        total_hits=semantic_hits + keyword_hits,
        returned_hits=len(combined_results),
        results=combined_results,
        query_dsl={
            "semantic_query": {"knn": "..."},
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


def display_semantic_vs_keyword_comparison(result: DemoQueryResult, query: str, comparison: dict):
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
    comp = comparison['comparison']
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


def display_natural_language_results(result: DemoQueryResult):
    """Display natural language search results with rich formatting."""
    
    if not result.results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Extract query from result name/description
    query_text = "modern home with mountain views and open floor plan"  # Default query
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
    
    for i, prop in enumerate(result.results[:10], 1):
        address = prop.get('address', {})
        street = address.get('street', 'Unknown')
        city = address.get('city', '')
        
        table.add_row(
            str(i),
            f"{street}\n{city}",
            f"${prop.get('price', 0):,.0f}" if prop.get('price') else 'N/A',
            f"{prop.get('bedrooms', 'N/A')}/{prop.get('bathrooms', 'N/A')}",
            f"{prop.get('square_feet', 0):,}" if prop.get('square_feet') else 'N/A',
            f"{prop.get('_score', 0):.3f}"
        )
    
    console.print(table)
    
    # Show detailed match analysis
    console.print(f"\n[bold cyan]🔍 Why These Properties Match: '{query_text}'[/bold cyan]")
    
    # Show property descriptions with match highlighting
    for i, prop in enumerate(result.results[:3], 1):
        address = prop.get('address', {})
        desc = prop.get('description', 'No description available')
        features = prop.get('features', [])
        
        # Show full description (no truncation)
        
        # Create match insights based on query keywords
        insights = []
        query_lower = query_text.lower()
        desc_lower = desc.lower()
        
        if 'modern' in query_lower and any(word in desc_lower for word in ['modern', 'contemporary', 'updated', 'new']):
            insights.append("✓ Modern/contemporary features mentioned")
        if 'mountain' in query_lower and any(word in desc_lower for word in ['view', 'mountain', 'vista', 'scenic']):
            insights.append("✓ Views/scenic location described")  
        if 'open' in query_lower and any(word in desc_lower for word in ['open', 'spacious', 'floor plan', 'concept']):
            insights.append("✓ Open/spacious layout features")
        if 'home' in query_lower and any(word in desc_lower for word in ['family', 'home', 'residential', 'neighborhood']):
            insights.append("✓ Family-friendly/residential character")
            
        # Add score insight
        insights.append(f"🎯 Semantic similarity score: {prop.get('_score', 0):.3f}")
        
        panel_content = f"[bold]{address.get('street', 'Unknown')}[/bold]\n"
        panel_content += f"[yellow]${prop.get('price', 0):,.0f}[/yellow] • "
        panel_content += f"{prop.get('bedrooms', 'N/A')} bed / {prop.get('bathrooms', 'N/A')} bath • "
        panel_content += f"{prop.get('square_feet', 0):,} sq ft\n\n"
        panel_content += f"[bright_blue]{desc}[/bright_blue]\n\n"
        
        if insights:
            panel_content += "[bold green]Match Insights:[/bold green]\n"
            for insight in insights:
                panel_content += f"{insight}\n"
        
        panel = Panel(
            panel_content.strip(),
            title=f"Match #{i} - AI Semantic Analysis",
            border_style="green"
        )
        console.print(panel)
    
    # Add overall explanation
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