"""
Advanced search demo queries including semantic similarity and multi-entity search.

ADVANCED ELASTICSEARCH CONCEPTS:
- KNN (k-nearest neighbor) search for semantic similarity using vectors
- Script Score queries for custom ranking algorithms
- Multi-index search patterns
- Complex bool query combinations
- Query and filter context interactions
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.syntax import Syntax
from rich.tree import Tree

from .models import DemoQueryResult

logger = logging.getLogger(__name__)


def demo_semantic_search(
    es_client: Elasticsearch,
    reference_property_id: Optional[str] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 6: Semantic similarity search using embeddings.
    
    ELASTICSEARCH CONCEPTS:
    - KNN SEARCH: k-nearest neighbor for vector similarity
    - SCRIPT SCORE: Custom scoring using Painless scripts
    - DENSE VECTORS: Storing and searching embeddings
    - COSINE SIMILARITY: Vector similarity metric
    
    Finds properties similar to a reference property using vector embeddings,
    demonstrating AI-powered semantic search capabilities.
    
    Args:
        es_client: Elasticsearch client
        reference_property_id: Property to find similar ones to
        size: Number of similar properties to return
        
    Returns:
        DemoQueryResult with semantically similar properties
    """
    
    # First, get a reference property (random if not specified)
    if not reference_property_id:
        # RANDOM SAMPLING: Get a random document for demonstration
        random_query = {
            # FUNCTION SCORE QUERY: Modify document scores with functions
            "query": {
                "function_score": {
                    "query": {"match_all": {}},
                    # RANDOM SCORE: Randomize results for sampling
                    "random_score": {"seed": random.randint(1, 10000)}
                }
            },
            "size": 1
        }
        
        try:
            random_response = es_client.search(index="properties", body=random_query)
            if random_response['hits']['hits']:
                reference_property_id = random_response['hits']['hits'][0]['_id']
        except Exception as e:
            logger.error(f"Error getting random property: {e}")
            reference_property_id = "prop-001"
    
    # First get the reference property's embedding
    reference_embedding = None
    ref_property_details = {}
    
    try:
        # Get reference property with its embedding
        if reference_property_id:
            ref_doc = es_client.get(index="properties", id=reference_property_id)
            if 'embedding' in ref_doc.get('_source', {}):
                reference_embedding = ref_doc['_source']['embedding']
                ref_property_details = {
                    'address': ref_doc['_source'].get('address', {}),
                    'property_type': ref_doc['_source'].get('property_type', 'Unknown'),
                    'price': ref_doc['_source'].get('price', 0),
                    'bedrooms': ref_doc['_source'].get('bedrooms', 0),
                    'bathrooms': ref_doc['_source'].get('bathrooms', 0),
                    'square_feet': ref_doc['_source'].get('square_feet', 0),
                    'description': ref_doc['_source'].get('description', 'No description available')
                }
                # Log property details for context
                addr = ref_property_details['address']
                street = addr.get('street', 'Unknown street')
                city = addr.get('city', 'Unknown city')
                price_fmt = f"${ref_property_details['price']:,.0f}" if ref_property_details['price'] else "Unknown price"
                beds = ref_property_details['bedrooms']
                baths = ref_property_details['bathrooms']
                sqft = ref_property_details['square_feet']
                prop_type = ref_property_details['property_type']
                
                logger.info(f"\n" + "="*60 + 
                           f"\n🔍 REFERENCE PROPERTY FOR SIMILARITY SEARCH:" +
                           f"\n{'-'*60}" +
                           f"\nProperty ID: {reference_property_id}" +
                           f"\nAddress: {street}, {city}" +
                           f"\nType: {prop_type}" +
                           f"\nPrice: {price_fmt}" +
                           f"\nSize: {beds}bd/{baths}ba | {sqft} sqft" +
                           f"\n" + "="*60)
            else:
                logger.warning(f"Reference property {reference_property_id} has no embedding")
                return DemoQueryResult(
                    query_name="Semantic Similarity Search",
                    execution_time_ms=0,
                    total_hits=0,
                    returned_hits=0,
                    results=[],
                    query_dsl={"error": "Reference property has no embedding"}
                )
    except Exception as e:
        logger.error(f"Error getting reference property: {e}")
        return DemoQueryResult(
            query_name="Semantic Similarity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl={"error": str(e)}
        )
    
    # Build the KNN semantic similarity query
    # KNN is the modern, efficient way to do vector similarity in Elasticsearch
    query = {
        # KNN SEARCH: K-Nearest Neighbors for vector similarity
        # This is much more efficient than script_score for dense_vector fields
        "knn": {
            "field": "embedding",  # The dense_vector field containing embeddings
            "query_vector": reference_embedding,  # The reference vector to compare against
            "k": size + 1,  # Number of neighbors to find (+1 as reference might be included)
            "num_candidates": 100  # Number of candidates per shard (higher = more accurate but slower)
        },
        # FILTER: Exclude the reference property from results
        "query": {
            "bool": {
                "must_not": [
                    {"term": {"_id": reference_property_id}}
                ]
            }
        },
        "size": size,
        "_source": [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features"
        ]
    }
    
    console = Console()
    
    # Show reference property details in a nice panel
    if ref_property_details:
        ref_text = Text()
        ref_text.append("🏠 Reference Property\n", style="bold yellow")
        ref_text.append(f"Address: {street}, {city}\n", style="cyan")
        ref_text.append(f"Type: {prop_type}\n", style="magenta")
        ref_text.append(f"Price: {price_fmt}\n", style="green")
        ref_text.append(f"Size: {beds}bd/{baths}ba | {sqft:,} sqft\n", style="blue")
        ref_text.append(f"\n📝 Description:\n", style="bold yellow")
        ref_text.append(f"{ref_property_details.get('description', 'No description available')[:300]}...", style="bright_blue")
        
        console.print(Panel(
            ref_text,
            title="[bold cyan]🤖 AI Semantic Similarity Search[/bold cyan]",
            subtitle=f"Finding similar properties using embeddings",
            border_style="cyan"
        ))
    
    try:
        with console.status("[yellow]Searching for semantically similar properties...[/yellow]"):
            response = es_client.search(index="properties", body=query)
        
        results = []
        
        if response['hits']['hits']:
            # Create similarity results table
            table = Table(
                title=f"[bold green]Found {len(response['hits']['hits'])} Similar Properties[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True
            )
            table.add_column("#", style="dim", width=4)
            table.add_column("Score", style="magenta", justify="right", width=8)
            table.add_column("Property Details", style="cyan", width=50)
            table.add_column("Description", style="bright_blue", width=60)
            
            for i, hit in enumerate(response['hits']['hits'], 1):
                result = hit['_source']
                # Include similarity score for transparency
                result['_similarity_score'] = hit['_score']
                result['_reference_property'] = reference_property_id
                results.append(result)
                
                # Format address
                addr = result.get('address', {})
                address_str = f"{addr.get('street', 'N/A')}, {addr.get('city', 'N/A')}"
                
                # Format price
                price = result.get('price', 0)
                price_str = f"${price:,.0f}" if price else "N/A"
                
                # Format size
                beds = result.get('bedrooms', 0)
                baths = result.get('bathrooms', 0)
                sqft = result.get('square_feet', 0)
                size_str = f"{beds}bd/{baths}ba | {sqft:,}sqft"
                
                # Format property details
                property_details = Text()
                property_details.append(f"📍 {address_str}\n", style="cyan")
                property_details.append(f"💰 {price_str} ", style="green")
                property_details.append(f"• {result.get('property_type', 'N/A').title()}\n", style="yellow")
                property_details.append(f"🏠 {size_str}", style="blue")
                
                # Format description
                description = result.get('description', 'No description available')
                desc_text = Text(description[:200] + "..." if len(description) > 200 else description, style="bright_blue")
                
                # Add to table
                table.add_row(
                    str(i),
                    f"{hit['_score']:.2f}",
                    property_details,
                    desc_text
                )
            
            console.print(table)
            
            # Show AI insights
            console.print(Panel(
                f"[green]✓[/green] Found [bold]{len(results)}[/bold] semantically similar properties\n"
                f"[green]✓[/green] Using [bold]1024-dimensional[/bold] voyage-3 embeddings\n"
                f"[green]✓[/green] Query time: [bold]{response.get('took', 0)}ms[/bold]\n"
                f"[dim]💡 Higher similarity scores indicate more similar properties[/dim]",
                title="[bold]🤖 AI Search Results[/bold]",
                border_style="green"
            ))
        
        # Create descriptive query name with reference property info
        query_name = f"Semantic Similarity Search - Finding properties similar to: {street}, {city} ({prop_type}, {price_fmt})"
        
        return DemoQueryResult(
            query_name="Demo 6: " + query_name,
            query_description=f"Finds properties semantically similar to reference property {reference_property_id} using AI embeddings and vector similarity",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=results,
            query_dsl=query,
            es_features=[
                "KNN Search - K-nearest neighbors for efficient vector similarity search",
                "Dense Vectors - 1024-dimensional embeddings for semantic understanding (voyage-3 model)",
                "Cosine Similarity - Vector distance metric for finding similar properties",
                "Function Score Query - Random sampling to find reference property",
                "Bool Query - Exclude reference property from results",
                "Vector Search at Scale - Efficient similarity search on large datasets"
            ],
            indexes_used=[
                "properties index - Real estate listings with AI embeddings",
                f"Searching for {size} properties most similar to reference property"
            ]
        )
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return DemoQueryResult(
            query_name="Semantic Similarity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_multi_entity_search(
    es_client: Elasticsearch,
    query_text: str = "historic downtown",
    size: int = 5
) -> DemoQueryResult:
    """
    Demo 7: Multi-entity combined search across different indices.
    
    ELASTICSEARCH CONCEPTS:
    - MULTI-INDEX SEARCH: Query multiple indices in one request
    - INDEX BOOSTING: Weight importance of different indices
    - CROSS-INDEX RANKING: Unified relevance scoring
    - RESULT DISCRIMINATION: Identify source index of each result
    
    Searches across properties, neighborhoods, and Wikipedia articles
    to provide comprehensive results from multiple data sources.
    
    Args:
        es_client: Elasticsearch client
        query_text: Search query text
        size: Number of results per entity type
        
    Returns:
        DemoQueryResult with mixed entity results
    """
    
    # MULTI-INDEX QUERY: Search multiple indices simultaneously
    # This is more efficient than separate queries
    query = {
        "query": {
            # MULTI_MATCH across all text fields in all indices
            "multi_match": {
                "query": query_text,
                # FIELD PATTERNS: Use wildcards to match fields across indices
                "fields": [
                    # Property fields
                    "description^2",
                    "features^1.5",
                    "amenities",
                    "address.city",
                    "neighborhood_name",
                    
                    # Neighborhood fields (will be ignored if not present)
                    "name^3",
                    "demographics.description",
                    
                    # Wikipedia fields
                    "title^3",
                    "summary^2",
                    "content",
                    "categories"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        
        # AGGREGATION: Count results by index for overview
        "aggs": {
            "by_index": {
                # INDEX AGGREGATION: Group by _index metadata field
                "terms": {
                    "field": "_index",
                    "size": 10
                }
            }
        },
        
        "size": size * 3,  # Get more since we're searching multiple indices
        
        # Include index name in results for discrimination
        "_source": {
            "includes": ["*"]  # All fields
        },
        
        # HIGHLIGHT: Works across all indices
        "highlight": {
            "fields": {
                "*": {}  # Highlight any matching field
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"]
        }
    }
    
    # INDEX SPECIFICATION: Use list format for multiple indices
    indices = ["properties", "neighborhoods", "wikipedia"]
    
    console = Console()
    
    # Show search header
    console.print(Panel(
        f"[bold cyan]🌐 Multi-Entity Search[/bold cyan]\n"
        f"[yellow]Query: '{query_text}'[/yellow]\n"
        f"[dim]Searching across properties, neighborhoods, and Wikipedia[/dim]",
        border_style="cyan"
    ))
    
    try:
        with console.status("[yellow]Searching multiple data sources...[/yellow]"):
            response = es_client.search(
                index=indices,  # Multiple indices
                body=query,
                # INDEX BOOST: Weight certain indices as more important
                # Can be specified in URL: "properties^2,neighborhoods^1.5,wikipedia"
            )
        
        # Process results and add entity type
        results = []
        entity_groups = {'property': [], 'neighborhood': [], 'wikipedia': []}
        
        for hit in response['hits']['hits']:
            result = hit['_source']
            
            # ADD METADATA: Include index and type information
            result['_index'] = hit['_index']
            result['_id'] = hit['_id']
            result['_score'] = hit['_score']
            
            # ENTITY TYPE DETECTION: Based on index name
            if 'properties' in hit['_index']:
                result['_entity_type'] = 'property'
                entity_groups['property'].append((hit, result))
            elif 'neighborhoods' in hit['_index']:
                result['_entity_type'] = 'neighborhood'
                entity_groups['neighborhood'].append((hit, result))
            elif 'wikipedia' in hit['_index']:
                result['_entity_type'] = 'wikipedia'
                entity_groups['wikipedia'].append((hit, result))
            else:
                result['_entity_type'] = 'unknown'
            
            # Add highlights if present
            if 'highlight' in hit:
                result['_highlights'] = hit['highlight']
            
            results.append(result)
        
        # Display results grouped by entity type
        if entity_groups['property']:
            prop_table = Table(
                title="[bold]🏠 Properties[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            prop_table.add_column("Score", style="magenta", justify="right", width=8)
            prop_table.add_column("Address", style="cyan")
            prop_table.add_column("Price", style="green", justify="right")
            prop_table.add_column("Type", style="yellow")
            
            for hit, result in entity_groups['property'][:5]:
                addr = result.get('address', {})
                address_str = f"{addr.get('street', 'N/A')}, {addr.get('city', 'N/A')}"
                price = result.get('price', 0)
                price_str = f"${price:,.0f}" if price else "N/A"
                
                prop_table.add_row(
                    f"{hit['_score']:.2f}",
                    address_str,
                    price_str,
                    result.get('property_type', 'N/A').title()
                )
            
            console.print(prop_table)
        
        if entity_groups['neighborhood']:
            neigh_table = Table(
                title="\n[bold]📍 Neighborhoods[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            neigh_table.add_column("Score", style="magenta", justify="right", width=8)
            neigh_table.add_column("Name", style="cyan")
            neigh_table.add_column("City", style="green")
            
            for hit, result in entity_groups['neighborhood'][:5]:
                neigh_table.add_row(
                    f"{hit['_score']:.2f}",
                    result.get('name', 'N/A'),
                    result.get('city', 'N/A')
                )
            
            console.print(neigh_table)
        
        if entity_groups['wikipedia']:
            wiki_table = Table(
                title="\n[bold]📚 Wikipedia Articles[/bold]",
                box=box.SIMPLE,
                show_header=True,
                header_style="cyan"
            )
            wiki_table.add_column("Score", style="magenta", justify="right", width=8)
            wiki_table.add_column("Title", style="cyan")
            wiki_table.add_column("Categories", style="yellow")
            
            for hit, result in entity_groups['wikipedia'][:5]:
                categories = result.get('categories', [])
                cat_str = ', '.join(categories[:2]) if categories else 'N/A'
                
                wiki_table.add_row(
                    f"{hit['_score']:.2f}",
                    result.get('title', 'N/A'),
                    cat_str
                )
            
            console.print(wiki_table)
        
        # Show summary statistics
        if 'aggregations' in response and 'by_index' in response['aggregations']:
            stats_text = Text()
            for bucket in response['aggregations']['by_index']['buckets']:
                index_name = bucket['key']
                count = bucket['doc_count']
                if 'properties' in index_name:
                    stats_text.append(f"🏠 Properties: {count}  ", style="cyan")
                elif 'neighborhoods' in index_name:
                    stats_text.append(f"📍 Neighborhoods: {count}  ", style="yellow")
                elif 'wikipedia' in index_name:
                    stats_text.append(f"📚 Wikipedia: {count}  ", style="magenta")
            
            console.print(Panel(
                stats_text,
                title="[bold]Search Results Summary[/bold]",
                border_style="green"
            ))
        
        # Include aggregation results
        aggregations = {}
        if 'aggregations' in response:
            aggregations = response['aggregations']
        
        # Extract only property results for the standard display table
        property_results = [r for r in results if r.get('_entity_type') == 'property']
        
        return DemoQueryResult(
            query_name=f"Demo 7: Multi-Entity Search - '{query_text}'",
            query_description=f"Unified search across properties, neighborhoods, and Wikipedia articles for '{query_text}', combining results from multiple data sources",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(property_results),
            results=property_results,  # Only return property results for standard display
            aggregations=aggregations,
            query_dsl=query,
            es_features=[
                "Multi-Index Search - Query multiple indices in single request",
                "Cross-Index Ranking - Unified relevance scoring across different entity types",
                "Field Boosting - Weight different fields by importance (title^3, description^2)",
                "Index Aggregation - Count results by source index",
                "Highlighting - Show matching content snippets",
                "Fuzzy Matching - Handle typos with AUTO fuzziness"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                "neighborhoods index - Neighborhood demographics and descriptions",
                "wikipedia index - Geographic Wikipedia articles",
                f"Searching {', '.join(indices)} indices simultaneously"
            ]
        )
    except Exception as e:
        logger.error(f"Error in multi-entity search: {e}")
        return DemoQueryResult(
            query_name="Multi-Entity Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )


def demo_wikipedia_search(
    es_client: Elasticsearch,
    city: Optional[str] = "San Francisco",
    state: Optional[str] = "CA",
    topics: Optional[List[str]] = None,
    size: int = 10
) -> DemoQueryResult:
    """
    Demo 8: Wikipedia article search with location filtering.
    
    ELASTICSEARCH CONCEPTS:
    - COMPLEX BOOL QUERIES: Combining multiple conditions
    - QUERY vs FILTER CONTEXT: When to use each
    - FIELD EXISTENCE CHECKS: Using exists query
    - MULTI-FIELD SORTING: Primary and secondary sort orders
    - NULL HANDLING: Dealing with missing values in sorts
    
    Searches Wikipedia articles with geographic and topical filters,
    demonstrating complex query construction.
    
    Args:
        es_client: Elasticsearch client
        city: Filter by city
        state: Filter by state
        topics: Filter by topics/categories
        size: Number of results
        
    Returns:
        DemoQueryResult with Wikipedia articles
    """
    
    # BUILD COMPLEX BOOL QUERY
    # Demonstrates query vs filter context usage
    
    # MUST CLAUSES: Query context - affects scoring
    must_clauses = []
    
    # Add topic search if provided
    if topics:
        must_clauses.append({
            "multi_match": {
                "query": " ".join(topics),
                "fields": [
                    "title^2",      # Article title most important
                    "summary^1.5",  # Summary quite important
                    "categories",   # Categories/topics
                    "content"       # Full content
                ],
                "type": "best_fields"
            }
        })
    
    # FILTER CLAUSES: Filter context - no scoring, cacheable
    filter_clauses = []
    
    # Geographic filters
    if city:
        filter_clauses.append({
            # NESTED BOOL: OR condition within AND
            "bool": {
                "should": [  # OR - match any of these
                    {"match": {"city": city}},  # Match city field
                    {"match": {"title": city}}  # Also check title for city name
                ],
                "minimum_should_match": 1  # At least one must match
            }
        })
    
    if state:
        filter_clauses.append({
            "bool": {
                "should": [
                    {"match": {"state": state}},  # Match state field
                    {"term": {"state": state.upper()}}  # Also try uppercase (UT vs Utah)
                ],
                "minimum_should_match": 1
            }
        })
    
    # Ensure articles have city data  
    filter_clauses.append({
        "exists": {"field": "city"}  # Only articles with city field
    })
    
    query = {
        "query": {
            "bool": {
                # QUERY CONTEXT: Scoring queries
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                
                # FILTER CONTEXT: Non-scoring filters
                "filter": filter_clauses,
                
                # BOOSTING: Prefer certain articles
                "should": [
                    # Boost high-quality articles
                    {"range": {"article_quality_score": {"gte": 0.8, "boost": 2.0}}},
                    # Boost if title contains the city
                    {"match": {"title": {"query": city or "", "boost": 1.5}}},
                    # Boost comprehensive articles
                    {"range": {"content_length": {"gte": 5000, "boost": 1.2}}}
                ]
            }
        } if filter_clauses else {"bool": {"must": must_clauses}},
        
        "size": size,
        
        "_source": [
            "page_id", "title", "url", "short_summary", "long_summary", "city", "state",
            "location", "article_quality_score", "topics", "full_content"
        ],
        
        # HIGHLIGHTING: Show matching content
        "highlight": {
            "fields": {
                "summary": {"fragment_size": 150},
                "content": {"fragment_size": 200}
            }
        },
        
        # COMPLEX SORTING: Multiple sort criteria
        "sort": [
            "_score",  # Primary: relevance
            # Secondary: quality score (handle nulls)
            {"article_quality_score": {"order": "desc", "missing": "_last"}}
        ]
    }
    
    # Clean up query if no filters
    if not filter_clauses:
        query['query'] = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    console = Console()
    
    # Show search header
    console.print(Panel(
        f"[bold cyan]📚 Wikipedia Article Search[/bold cyan]\n"
        f"[yellow]Location: {city}, {state}[/yellow]\n"
        f"[dim]Topics: {', '.join(topics) if topics else 'All topics'}[/dim]",
        border_style="cyan"
    ))
    
    try:
        with console.status("[yellow]Searching Wikipedia articles...[/yellow]"):
            response = es_client.search(index="wikipedia", body=query)
        
        results = []
        
        if response['hits']['hits']:
            # Create results table
            table = Table(
                title=f"[bold green]Found {len(response['hits']['hits'])} Wikipedia Articles[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True,
                width=None  # Let table auto-size
            )
            table.add_column("ID", style="dim", width=6, no_wrap=True)
            table.add_column("Score", style="magenta", justify="right", width=6, no_wrap=True)
            table.add_column("Article", style="cyan", overflow="fold")
            table.add_column("Summary", style="bright_blue", overflow="fold")
            
            for i, hit in enumerate(response['hits']['hits'], 1):
                result = hit['_source']
                result['_score'] = hit['_score']
                
                # Add highlights
                if 'highlight' in hit:
                    result['_highlights'] = hit['highlight']
                
                # Add computed relevance info
                result['_relevance_factors'] = {
                    'score': hit['_score'],
                    'has_location': 'location' in result,
                    'quality_score': result.get('article_quality_score', 0)
                }
                
                results.append(result)
                
                # Format article info
                article_info = Text()
                article_info.append(f"📖 {result.get('title', 'N/A')}\n", style="bold white")
                article_info.append(f"📍 {result.get('city', 'N/A')}, {result.get('state', 'N/A')}\n", style="green")
                if result.get('topics'):
                    topics_str = ", ".join(result['topics'][:3]) if isinstance(result['topics'], list) else str(result['topics'])
                    article_info.append(f"🏷️ {topics_str}", style="yellow")
                
                # Format summary - try multiple fields
                summary = result.get('short_summary', '').strip()
                
                # Fall back to long_summary if short_summary is empty
                if not summary:
                    summary = result.get('long_summary', '').strip()
                
                # Fall back to extracting from full_content if both summaries are empty
                if not summary and result.get('full_content'):
                    content = result['full_content']
                    # Skip the title line and get actual content
                    lines = content.split('\n')
                    # Find first non-empty line after the title
                    for i, line in enumerate(lines):
                        if i > 0 and line.strip() and not line.strip() == result.get('title', ''):
                            # Clean up and take first meaningful content
                            summary = ' '.join(line.split())[:250]
                            break
                
                if not summary:
                    summary = 'No summary available'
                    
                summary_text = Text(summary[:250] + "..." if len(summary) > 250 else summary, style="bright_blue")
                
                # Add to table with article ID
                article_id = result.get('page_id', hit.get('_id', str(i)))
                table.add_row(
                    str(article_id),
                    f"{hit['_score']:.2f}",
                    article_info,
                    summary_text
                )
            
            console.print(table)
            
            # Show search insights
            console.print(Panel(
                f"[green]✓[/green] Found [bold]{len(results)}[/bold] Wikipedia articles\n"
                f"[green]✓[/green] Location: [bold]{city}, {state}[/bold]\n"
                f"[green]✓[/green] Query time: [bold]{response.get('took', 0)}ms[/bold]",
                title="[bold]📚 Search Results[/bold]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[yellow]No Wikipedia articles found for {city}, {state}[/yellow]",
                border_style="yellow"
            ))
        
        # Return empty results for standard property display since these are Wikipedia articles
        # The custom display above already shows the Wikipedia results properly
        return DemoQueryResult(
            query_name=f"Demo 8: Wikipedia Location & Topic Search",
            query_description=f"Searches Wikipedia articles about {', '.join(topics or [])} in {city}, {state}, demonstrating complex filtering and boosting strategies",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'],
            returned_hits=len(results),
            results=[],  # Empty list since Wikipedia articles are not properties
            query_dsl=query,
            es_features=[
                "Complex Bool Query - Combining must, filter, and should clauses",
                "Query vs Filter Context - Scoring vs non-scoring clauses",
                "Nested Bool Queries - OR conditions within AND logic",
                "Exists Query - Filter documents with specific fields",
                "Multi-Field Sorting - Primary (_score) and secondary (quality) sorts",
                "Boosting Strategies - Prefer high-quality and comprehensive articles",
                "Field-Specific Highlighting - Different fragment sizes per field"
            ],
            indexes_used=[
                "wikipedia index - Curated Wikipedia articles with location data",
                f"Filtering for articles in {city}, {state} about {', '.join(topics or [])}"
            ]
        )
    except Exception as e:
        logger.error(f"Error in Wikipedia search: {e}")
        return DemoQueryResult(
            query_name="Wikipedia Search",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            results=[],
            query_dsl=query
        )
