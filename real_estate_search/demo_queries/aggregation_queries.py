"""
Aggregation demo queries for statistical analysis.

ELASTICSEARCH AGGREGATIONS OVERVIEW:
- Aggregations provide analytics and statistics on your data
- They operate alongside search requests (or independently with size:0)
- Three main types: Metric (math), Bucket (grouping), Pipeline (post-processing)
- Can be nested for complex multi-dimensional analysis
"""

from typing import Dict, Any, List
from elasticsearch import Elasticsearch
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn
from rich.layout import Layout

from .result_models import AggregationSearchResult
from ..models import PropertyListing

logger = logging.getLogger(__name__)


# ============================================================================
# ELASTICSEARCH AGGREGATION QUERIES - Core aggregation logic at the top
# ============================================================================


def build_neighborhood_stats_query(size: int = 20) -> Dict[str, Any]:
    """
    Build neighborhood statistics aggregation query.
    
    ELASTICSEARCH AGGREGATION STRUCTURE:
    - terms aggregation: Groups by neighborhood_id (like SQL GROUP BY)
    - sub-aggregations: Calculates metrics per bucket
    - global aggregations: Overall statistics across all documents
    """
    return {
        # SIZE: 0 means don't return documents, only aggregations
        # This improves performance when you only need statistics
        "size": 0,
        
        # AGGREGATIONS: The analytics framework of Elasticsearch
        "aggs": {
            # BUCKET AGGREGATION: Groups documents into buckets
            "by_neighborhood": {
                # TERMS AGGREGATION: Creates a bucket for each unique value
                # Similar to SQL's GROUP BY
                "terms": {
                    "field": "neighborhood_id",  # Must use keyword field for exact matching
                    "size": size,  # Maximum number of buckets to return
                    
                    # ORDER: Sort buckets by a metric (can reference sub-aggregations)
                    "order": {"property_count": "desc"}  # Most properties first
                    # Other options: {"_count": "desc"}, {"_key": "asc"}, {"avg_price": "desc"}
                },
                
                # SUB-AGGREGATIONS: Calculate metrics for each bucket
                # These run in the context of their parent bucket
                "aggs": {
                    # METRIC AGGREGATION: Single-value numeric metric
                    "property_count": {
                        "value_count": {"field": "listing_id"}  # Count unique values
                    },
                    
                    # AVG AGGREGATION: Calculate average value
                    "avg_price": {
                        "avg": {"field": "price"}
                    },
                    
                    # MIN/MAX AGGREGATIONS: Find extremes
                    "min_price": {
                        "min": {"field": "price"}
                    },
                    "max_price": {
                        "max": {"field": "price"}
                    },
                    
                    # Multiple metrics on different fields
                    "avg_bedrooms": {
                        "avg": {"field": "bedrooms"}
                    },
                    "avg_square_feet": {
                        "avg": {"field": "square_feet"}
                    },
                    "price_per_sqft": {
                        "avg": {"field": "price_per_sqft"}
                    },
                    
                    # NESTED BUCKET AGGREGATION: Create sub-buckets within each neighborhood
                    "property_types": {
                        "terms": {
                            "field": "property_type",
                            "size": 10  # Top 10 property types per neighborhood
                        }
                    }
                }
            },
            
            # GLOBAL METRICS: Calculate across all documents (not per bucket)
            "total_properties": {
                "value_count": {"field": "listing_id"}
            },
            "overall_avg_price": {
                "avg": {"field": "price"}
            }
        }
    }


def demo_neighborhood_stats(
    es_client: Elasticsearch,
    size: int = 20
) -> AggregationSearchResult:
    """
    Demo 4: Neighborhood statistics aggregation.
    
    DEMONSTRATES:
    - Terms aggregation for grouping
    - Metric sub-aggregations (avg, min, max)
    - Nested aggregations for property type breakdown
    - Global aggregations for overall statistics
    """
    # BUILD ELASTICSEARCH QUERY
    query = build_neighborhood_stats_query(size)
    
    # EXECUTE QUERY
    try:
        response = es_client.search(index="properties", body=query)
        
        # PROCESS RESULTS
        results = process_neighborhood_aggregations(response)
        
        # DISPLAY RESULTS (separated from query logic)
        display_neighborhood_stats(response, results, size)
        
        return AggregationSearchResult(
            query_name="Demo 4: Neighborhood Statistics Aggregation",
            query_description=f"Aggregates property data by neighborhood showing average prices, counts, and breakdowns for top {size} neighborhoods",
            execution_time_ms=response.get('took', 0),
            total_hits=response['aggregations']['total_properties']['value'] if 'aggregations' in response else 0,
            returned_hits=0,
            aggregations=response.get('aggregations', {}),
            top_properties=[],
            query_dsl=query,
            es_features=[
                "Terms Aggregation - Groups properties by neighborhood_id (like SQL GROUP BY)",
                "Metric Aggregations - Calculates avg, min, max prices and other statistics",
                "Nested Aggregations - Property type breakdown within each neighborhood",
                "Sub-aggregations - Multiple metrics calculated per bucket",
                "Ordering - Sorts neighborhoods by property count",
                "Global Aggregations - Overall statistics across all properties"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Returns statistics for top {size} neighborhoods by property count"
            ]
        )
    except Exception as e:
        logger.error(f"Error in neighborhood stats aggregation: {e}")
        return AggregationSearchResult(
            query_name="Neighborhood Statistics Aggregation",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            aggregations={},
            top_properties=[],
            query_dsl=query
        )


def build_price_distribution_query(
    interval: int = 100000,
    min_price: float = 0,
    max_price: float = 2000000
) -> Dict[str, Any]:
    """
    Build price distribution histogram query.
    
    ELASTICSEARCH AGGREGATION STRUCTURE:
    - histogram: Fixed-size interval buckets for price ranges
    - percentiles: Statistical distribution analysis
    - nested terms: Property type breakdown per bucket
    - stats: Multiple metrics in one aggregation
    """
    return {
        "size": 5,  # Return top 5 documents along with aggregations
        
        # SORT: Order documents by price descending to show most expensive
        "sort": [
            {"price": {"order": "desc"}}
        ],
        
        # QUERY WITH AGGREGATIONS: Filter documents before aggregating
        # Aggregations only operate on documents matching the query
        "query": {
            # RANGE QUERY in QUERY CONTEXT: Although it doesn't need scoring,
            # it's used here to limit the aggregation scope
            "range": {
                "price": {
                    "gte": min_price,  # Greater than or equal
                    "lte": max_price   # Less than or equal
                }
            }
        },
        
        "aggs": {
            # HISTOGRAM AGGREGATION: Fixed-size interval buckets
            # Like terms but for numeric ranges
            "price_histogram": {
                "histogram": {
                    "field": "price",
                    "interval": interval,  # Bucket width (e.g., $100,000)
                    
                    # MIN_DOC_COUNT: Omit empty buckets (0 = show all)
                    "min_doc_count": 1,
                    
                    # EXTENDED_BOUNDS: Force histogram range even if no data
                    # Useful for consistent visualizations
                    "extended_bounds": {
                        "min": min_price,
                        "max": max_price
                    }
                    # Other options:
                    # "offset": 50000 - Shift bucket boundaries
                    # "keyed": true - Return as object instead of array
                },
                
                # SUB-AGGREGATIONS per price bucket
                "aggs": {
                    # Break down each price range by property type
                    "by_property_type": {
                        "terms": {
                            "field": "property_type",
                            "size": 10
                        }
                    },
                    
                    # STATS AGGREGATION: Multiple metrics in one
                    # Returns: min, max, avg, sum, count
                    "stats": {
                        "stats": {"field": "price"}
                    }
                }
            },
            
            # PERCENTILES AGGREGATION: Statistical distribution
            # Find values at specific percentile ranks
            "price_percentiles": {
                "percentiles": {
                    "field": "price",
                    "percents": [25, 50, 75, 90, 95, 99]  # Quartiles + high percentiles
                    # 50th percentile = median
                    # 25th-75th = interquartile range
                }
            },
            
            # COMPLEX NESTED AGGREGATION: Stats per property type
            "by_property_type_stats": {
                "terms": {
                    "field": "property_type",
                    "size": 10
                },
                "aggs": {
                    # Multiple metric aggregations per bucket
                    "price_stats": {
                        "stats": {"field": "price"}
                    },
                    "price_percentiles": {
                        "percentiles": {
                            "field": "price",
                            "percents": [50]  # Just the median
                        }
                    }
                }
            }
        }
    }


def demo_price_distribution(
    es_client: Elasticsearch,
    interval: int = 100000,
    min_price: float = 0,
    max_price: float = 2000000
) -> AggregationSearchResult:
    """
    Demo 5: Price distribution analysis with top 5 most expensive properties.
    
    DEMONSTRATES:
    - Histogram aggregation for price ranges
    - Percentiles aggregation for distribution
    - Nested aggregations for property type breakdown
    - Stats aggregation for multiple metrics
    - Sorting by price to show most expensive properties
    """
    # BUILD ELASTICSEARCH QUERY
    query = build_price_distribution_query(interval, min_price, max_price)
    
    # EXECUTE QUERY
    try:
        response = es_client.search(index="properties", body=query)
        
        # PROCESS AGGREGATION RESULTS
        histogram_results = process_price_distribution(response, interval)
        aggregations = response.get('aggregations', {})
        
        # EXTRACT TOP PROPERTIES FOR DISPLAY
        property_results = []
        if 'hits' in response and 'hits' in response['hits']:
            for hit in response['hits']['hits']:
                source = hit['_source']
                property_results.append(source)
        
        # DISPLAY RESULTS (separated from query logic)
        display_price_distribution(response, histogram_results, interval, min_price, max_price)
        
        # Convert raw property dicts to PropertyListing objects using converter
        from ..converters import PropertyConverter
        top_properties = PropertyConverter.from_elasticsearch_batch(property_results)
        
        return AggregationSearchResult(
            query_name=f"Demo 5: Price Distribution Analysis",
            query_description=f"Creates histogram of property prices from ${min_price:,.0f} to ${max_price:,.0f} with ${interval:,.0f} intervals, showing top 5 most expensive properties",
            execution_time_ms=response.get('took', 0),
            total_hits=response['hits']['total']['value'] if 'hits' in response else 0,
            returned_hits=len(top_properties),
            aggregations=aggregations,
            top_properties=top_properties,
            query_dsl=query,
            es_features=[
                "Histogram Aggregation - Creates fixed-size price range buckets",
                "Range Query - Filters properties within price boundaries",
                "Percentiles Aggregation - Calculates price distribution percentiles",
                "Stats Aggregation - Multiple metrics (min/max/avg/sum) in one aggregation",
                "Nested Terms Aggregation - Property type breakdown per price bucket",
                "Extended Bounds - Forces consistent histogram range",
                "Min Doc Count - Omits empty buckets for cleaner results",
                "Sort - Orders results by price descending"
            ],
            indexes_used=[
                "properties index - Real estate property listings",
                f"Analyzes price distribution across {(max_price - min_price) / interval:.0f} price ranges"
            ]
        )
    except Exception as e:
        logger.error(f"Error in price distribution analysis: {e}")
        return AggregationSearchResult(
            query_name="Price Distribution Analysis",
            execution_time_ms=0,
            total_hits=0,
            returned_hits=0,
            aggregations={},
            top_properties=[],
            query_dsl=query
        )


# ============================================================================
# RESULT PROCESSING FUNCTIONS - Data transformation logic
# ============================================================================

def process_neighborhood_aggregations(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process neighborhood aggregation results."""
    results = []
    if 'aggregations' in response and 'by_neighborhood' in response['aggregations']:
        for bucket in response['aggregations']['by_neighborhood']['buckets']:
            results.append({
                'neighborhood_id': bucket['key'],
                'property_count': bucket['property_count']['value'],
                'avg_price': round(bucket['avg_price']['value'], 2) if bucket['avg_price']['value'] else 0,
                'min_price': bucket['min_price']['value'],
                'max_price': bucket['max_price']['value'],
                'avg_bedrooms': round(bucket['avg_bedrooms']['value'], 1) if bucket['avg_bedrooms']['value'] else 0,
                'avg_square_feet': round(bucket['avg_square_feet']['value'], 0) if bucket['avg_square_feet']['value'] else 0,
                'price_per_sqft': round(bucket['price_per_sqft']['value'], 2) if bucket['price_per_sqft']['value'] else 0,
                'property_types': [
                    {'type': t['key'], 'count': t['doc_count']} 
                    for t in bucket['property_types']['buckets']
                ]
            })
    return results


def process_price_distribution(response: Dict[str, Any], interval: int) -> List[Dict[str, Any]]:
    """Process price distribution histogram results."""
    results = []
    if 'aggregations' in response and 'price_histogram' in response['aggregations']:
        for bucket in response['aggregations']['price_histogram']['buckets']:
            range_start = bucket['key']
            range_end = range_start + interval
            
            property_type_breakdown = {}
            for type_bucket in bucket['by_property_type']['buckets']:
                property_type_breakdown[type_bucket['key']] = type_bucket['doc_count']
            
            results.append({
                'price_range': f"${range_start:,.0f} - ${range_end:,.0f}",
                'range_start': range_start,
                'range_end': range_end,
                'count': bucket['doc_count'],
                'property_types': property_type_breakdown,
                'avg_price': bucket['stats']['avg'] if 'stats' in bucket else None
            })
    return results


# ============================================================================
# DISPLAY FUNCTIONS - All UI/formatting logic at the bottom
# ============================================================================

def display_neighborhood_stats(response: Dict[str, Any], results: List[Dict[str, Any]], size: int):
    """Display neighborhood statistics with rich formatting."""
    console = Console()
    
    # Header
    console.print(Panel(
        f"[bold cyan]📊 Neighborhood Statistics Analysis[/bold cyan]\n"
        f"[yellow]Analyzing top {size} neighborhoods by property count[/yellow]",
        border_style="cyan"
    ))
    
    if not results:
        console.print("[red]No aggregation results found[/red]")
        return
    
    # Create neighborhood stats table
    table = Table(
        title=f"[bold green]Neighborhood Property Statistics[/bold green]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Neighborhood", style="cyan", width=20)
    table.add_column("Properties", style="yellow", justify="right")
    table.add_column("Avg Price", style="green", justify="right")
    table.add_column("Price Range", style="blue", justify="right")
    table.add_column("Avg Beds", style="magenta", justify="right")
    table.add_column("Avg SqFt", style="yellow", justify="right")
    table.add_column("$/SqFt", style="green", justify="right")
    
    for neighborhood_data in results:
        price_range = f"${neighborhood_data['min_price']:,.0f}-${neighborhood_data['max_price']:,.0f}"
        table.add_row(
            neighborhood_data['neighborhood_id'],
            str(neighborhood_data['property_count']),
            f"${neighborhood_data['avg_price']:,.0f}",
            price_range,
            f"{neighborhood_data['avg_bedrooms']:.1f}",
            f"{neighborhood_data['avg_square_feet']:,.0f}",
            f"${neighborhood_data['price_per_sqft']:.2f}"
        )
    
    console.print(table)
    
    # Show global statistics
    if 'aggregations' in response and 'total_properties' in response['aggregations']:
        stats_panel = Panel(
            f"[green]✓[/green] Total Properties: [bold]{response['aggregations']['total_properties']['value']:.0f}[/bold]\n"
            f"[green]✓[/green] Overall Average Price: [bold]${response['aggregations']['overall_avg_price']['value']:,.0f}[/bold]\n"
            f"[green]✓[/green] Neighborhoods Analyzed: [bold]{len(results)}[/bold]\n"
            f"[green]✓[/green] Query Time: [bold]{response.get('took', 0)}ms[/bold]",
            title="[bold]📈 Overall Market Statistics[/bold]",
            border_style="green"
        )
        console.print(stats_panel)


def display_price_distribution(
    response: Dict[str, Any], 
    results: List[Dict[str, Any]], 
    interval: int,
    min_price: float,
    max_price: float
):
    """Display price distribution with rich formatting."""
    console = Console()
    
    # Header
    console.print(Panel(
        f"[bold cyan]📊 Price Distribution Analysis[/bold cyan]\n"
        f"[yellow]Range: ${min_price:,.0f} - ${max_price:,.0f}[/yellow]\n"
        f"[yellow]Bucket Size: ${interval:,.0f}[/yellow]",
        border_style="cyan"
    ))
    
    if not results:
        console.print("[red]No distribution results found[/red]")
        return
    
    # Draw histogram
    console.print("\n[bold]Price Distribution Histogram:[/bold]")
    max_count = max(r['count'] for r in results) if results else 1
    
    for result in results:
        bar_width = int((result['count'] / max_count) * 50)
        bar = "█" * bar_width
        price_label = f"${result['range_start']/1000:.0f}k-${result['range_end']/1000:.0f}k"
        console.print(f"  {price_label:>15} │ [green]{bar}[/green] {result['count']}")
    
    # Show percentiles
    if 'aggregations' in response and 'price_percentiles' in response['aggregations']:
        percentiles = response['aggregations']['price_percentiles']['values']
        
        percentile_table = Table(
            title="\n[bold]Price Percentiles[/bold]",
            box=box.SIMPLE,
            show_header=False
        )
        percentile_table.add_column("Percentile", style="yellow")
        percentile_table.add_column("Price", style="green", justify="right")
        
        for p, value in percentiles.items():
            percentile_table.add_row(
                f"{p}th percentile",
                f"${value:,.0f}" if value else "N/A"
            )
        
        console.print(percentile_table)
    
    # Show property type statistics
    if 'aggregations' in response and 'by_property_type_stats' in response['aggregations']:
        type_table = Table(
            title="\n[bold]Statistics by Property Type[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="yellow", justify="right")
        type_table.add_column("Avg Price", style="green", justify="right")
        type_table.add_column("Min Price", style="blue", justify="right")
        type_table.add_column("Max Price", style="red", justify="right")
        
        for type_bucket in response['aggregations']['by_property_type_stats']['buckets']:
            stats = type_bucket['price_stats']
            type_table.add_row(
                type_bucket['key'].title(),
                str(type_bucket['doc_count']),
                f"${stats['avg']:,.0f}" if stats['avg'] else "N/A",
                f"${stats['min']:,.0f}" if stats['min'] else "N/A",
                f"${stats['max']:,.0f}" if stats['max'] else "N/A"
            )
        
        console.print(type_table)