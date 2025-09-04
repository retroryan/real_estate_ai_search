"""
Refactored property search demo queries with Pydantic models and comprehensive documentation.

This module demonstrates fundamental Elasticsearch property search patterns:
1. Full-text search with multi-match queries
2. Filtered searches combining text and criteria
3. Range queries for numeric fields
4. Geo-distance searches for location-based queries
5. Complex boolean queries with multiple conditions

ELASTICSEARCH CONCEPTS DEMONSTRATED:
- Query vs Filter context (scoring vs non-scoring)
- Field boosting for relevance tuning
- Fuzzy matching for typo tolerance
- Aggregations for faceted search
- Geo queries for location-based search
- Highlighting for search result context
- Source filtering for performance optimization
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from elasticsearch import Elasticsearch
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

from .base_models import (
    SearchRequest,
    SearchResponse,
    SourceFilter,
    BoolQuery,
    QueryClause,
    QueryType,
    GeoPoint,
    TypedDemoResult,
    AggregationType,
    AggregationResult,
    BucketAggregation,
    StatsAggregation
)
from .result_models import PropertySearchResult, PropertyResult, AggregationSearchResult
from .es_models import ESProperty, ESSearchHit
from .display_formatter import PropertyDisplayFormatter

logger = logging.getLogger(__name__)


# ============================================================================
# ELASTICSEARCH QUERY BUILDERS - Core query logic at the top for clarity
# ============================================================================

class PropertyQueryBuilder:
    """
    Builder class for constructing property search queries.
    
    This class encapsulates the logic for building various types of
    Elasticsearch queries for property searches, from simple text searches
    to complex geo-spatial and filtered queries.
    """
    
    @staticmethod
    def basic_search(
        query_text: str,
        size: int = 10,
        highlight: bool = True
    ) -> SearchRequest:
        """
        Build a basic property search query using multi-match.
        
        ELASTICSEARCH CONCEPTS:
        1. MULTI-MATCH QUERY:
           - Searches text across multiple fields simultaneously
           - More flexible than single-field match queries
           - Supports different matching strategies
        
        2. FIELD BOOSTING:
           - description^2 gives 2x weight to description matches
           - Influences relevance scoring, not filtering
           - Critical for tuning search result quality
        
        3. FUZZINESS:
           - AUTO adapts based on term length
           - Handles typos and variations
           - Essential for user-friendly search
        
        Args:
            query_text: Text to search for
            size: Maximum results to return
            highlight: Whether to include highlighting
            
        Returns:
            SearchRequest configured for basic text search
        """
        query: Dict[str, Any] = {
            "multi_match": {
                "query": query_text,
                "fields": [
                    "description^2",      # Primary content field
                    "amenities^1.5",      # Important features
                    "address.street",     # Location context
                    "address.city",       # City search
                ],
                "type": "best_fields",   # Use best matching field's score
                "fuzziness": "AUTO",      # Adaptive fuzzy matching
                "prefix_length": 2,       # Minimum exact prefix
                "operator": "OR"          # Match ANY term (vs AND for ALL)
            }
        }
        
        request = SearchRequest(
            index=["properties"],
            query=query,
            size=size,
            source=SourceFilter(includes=[  # Only return needed fields
                "listing_id", "property_type", "price", 
                "bedrooms", "bathrooms", "square_feet",
                "address", "description", "amenities"
            ])
        )
        
        if highlight:
            request.highlight = {
                "fields": {
                    "description": {"fragment_size": 150},
                    "amenities": {"fragment_size": 100}
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        
        return request
    
    @staticmethod
    def filtered_search(
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        min_bathrooms: Optional[float] = None,
        amenities: Optional[List[str]] = None,
        size: int = 10
    ) -> SearchRequest:
        """
        Build a filtered property search query.
        
        ELASTICSEARCH CONCEPTS:
        1. BOOL QUERY:
           - Combines multiple query clauses with boolean logic
           - filter: Must match but doesn't affect score (cached)
           - must: Must match and affects score
           - should: Optional matches that boost score
        
        2. FILTER CONTEXT:
           - Used for yes/no questions (has 3 bedrooms?)
           - Results are cached for performance
           - No relevance scores calculated
        
        3. RANGE QUERIES:
           - gte/lte for inclusive bounds
           - gt/lt for exclusive bounds
           - Works with numbers, dates, strings
        
        Args:
            property_type: Filter by property type
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum bedrooms
            min_bathrooms: Minimum bathrooms
            amenities: Required amenities
            size: Maximum results
            
        Returns:
            SearchRequest with filter criteria
        """
        bool_query = BoolQuery()
        
        # Build filter clauses (non-scoring, cached)
        filters: List[Dict[str, Any]] = []
        
        if property_type:
            # Normalize property type to match data format
            pt_normalized = property_type.lower().replace(' ', '-')
            filters.append({"term": {"property_type": pt_normalized}})
        
        if min_price is not None or max_price is not None:
            range_clause: Dict[str, Any] = {}
            if min_price is not None:
                range_clause["gte"] = min_price
            if max_price is not None:
                range_clause["lte"] = max_price
            filters.append({"range": {"price": range_clause}})
        
        if min_bedrooms is not None:
            filters.append({"range": {"bedrooms": {"gte": min_bedrooms}}})
        
        if min_bathrooms is not None:
            filters.append({"range": {"bathrooms": {"gte": min_bathrooms}}})
        
        if amenities:
            # Each amenity must exist
            for amenity in amenities:
                filters.append({"match": {"amenities": amenity}})
        
        # Use match_all if no filters (returns everything)
        if filters:
            query = {
                "bool": {
                    "filter": filters
                }
            }
        else:
            query = {"match_all": {}}
        
        return SearchRequest(
            index=["properties"],
            query=query,
            size=size,
            sort=[{"price": {"order": "asc"}}],  # Sort by price when filtering
            # Return all fields by default
        )
    
    @staticmethod
    def geo_search(
        center_lat: float,
        center_lon: float,
        radius_km: float = 5.0,
        property_type: Optional[str] = None,
        max_price: Optional[float] = None,
        size: int = 10
    ) -> SearchRequest:
        """
        Build a geo-distance property search query.
        
        ELASTICSEARCH CONCEPTS:
        1. GEO_DISTANCE QUERY:
           - Filters documents within radius of a point
           - Requires geo_point field mapping
           - Supports various distance units (km, mi, m)
        
        2. DISTANCE CALCULATION:
           - arc: Most accurate, slowest (default)
           - plane: Faster, less accurate for large distances
           - Distance returned in sort for display
        
        3. COMBINED FILTERING:
           - Geo filter reduces search space first
           - Additional filters apply within radius
           - Order matters for performance
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Search radius in kilometers
            property_type: Optional property type filter
            max_price: Optional maximum price
            size: Maximum results
            
        Returns:
            SearchRequest for geo-distance search
        """
        filters = [
            {
                "geo_distance": {
                    "distance": f"{radius_km}km",
                    "address.location": {
                        "lat": center_lat,
                        "lon": center_lon
                    }
                }
            }
        ]
        
        if property_type:
            # Normalize property type to match data format
            pt_normalized = property_type.lower().replace(' ', '-')
            filters.append({"term": {"property_type": pt_normalized}})
        
        if max_price is not None:
            filters.append({"range": {"price": {"lte": max_price}}})
        
        query = {
            "bool": {
                "filter": filters
            }
        }
        
        # Sort by distance from center point
        sort = [
            {
                "_geo_distance": {
                    "address.location": {
                        "lat": center_lat,
                        "lon": center_lon
                    },
                    "order": "asc",
                    "unit": "km",
                    "distance_type": "arc"
                }
            }
        ]
        
        return SearchRequest(
            index=["properties"],
            query=query,
            size=size,
            sort=sort,
            # Return all fields by default
        )
    
    @staticmethod
    def price_range_with_stats(
        min_price: float,
        max_price: float,
        include_stats: bool = True
    ) -> SearchRequest:
        """
        Build a price range query with statistical aggregations.
        
        ELASTICSEARCH CONCEPTS:
        1. AGGREGATIONS:
           - Calculate metrics across matching documents
           - Don't affect search results, add metadata
           - Can be nested for complex analytics
        
        2. STATS AGGREGATION:
           - Returns min, max, avg, sum, count
           - Single pass calculation for efficiency
           - Useful for result set context
        
        3. HISTOGRAM AGGREGATION:
           - Buckets data into intervals
           - Fixed or automatic interval sizing
           - Great for price distribution visualization
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            include_stats: Whether to include aggregations
            
        Returns:
            SearchRequest with price range and optional stats
        """
        query = {
            "range": {
                "price": {
                    "gte": min_price,
                    "lte": max_price
                }
            }
        }
        
        aggs = None
        if include_stats:
            aggs = {
                "price_stats": {
                    "stats": {
                        "field": "price"
                    }
                },
                "price_histogram": {
                    "histogram": {
                        "field": "price",
                        "interval": 100000,  # $100k buckets
                        "min_doc_count": 1  # Only return non-empty buckets
                    }
                },
                "property_types": {
                    "terms": {
                        "field": "property_type",
                        "size": 10
                    }
                },
                "bedroom_stats": {
                    "stats": {
                        "field": "bedrooms"
                    }
                }
            }
        
        return SearchRequest(
            index=["properties"],
            query=query,
            size=20,
            aggs=aggs,
            sort=[{"price": {"order": "asc"}}],
            # Return all fields by default
        )


# ============================================================================
# DEMO EXECUTION - Query execution with display logic separated
# ============================================================================

class PropertySearchDemo:
    """
    Demo class for property searches using Pydantic models.
    
    Organization:
    - Elasticsearch query execution methods first
    - Display/formatting methods at the bottom
    - Clear separation between query logic and presentation
    """
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize with Elasticsearch client."""
        self.es_client = es_client
        self.query_builder = PropertyQueryBuilder()
    
    def execute_search(self, request: SearchRequest) -> Tuple[Optional[SearchResponse], int]:
        """
        Execute a search request and measure timing.
        
        Args:
            request: SearchRequest to execute
            
        Returns:
            Tuple of (SearchResponse or None, execution time in ms)
        """
        import time
        start_time = time.time()
        
        try:
            response = self.es_client.search(
                index=request.index,
                body=request.to_dict()
            )
            execution_time = int((time.time() - start_time) * 1000)
            return SearchResponse.from_elasticsearch(response), execution_time
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            return None, execution_time
    
    # ------------------------------------------------------------------------
    # ELASTICSEARCH QUERY EXECUTION METHODS
    # ------------------------------------------------------------------------
    
    def demo_basic_search(
        self,
        query_text: str = "modern home with pool"
    ) -> PropertySearchResult:
        """
        Execute basic property search demo.
        
        ELASTICSEARCH FEATURES:
        - Multi-match query across multiple fields
        - Field boosting (description^2, amenities^1.5)
        - Fuzzy matching with AUTO
        - Result highlighting
        """
        # BUILD ELASTICSEARCH QUERY
        request = self.query_builder.basic_search(query_text)
        
        # EXECUTE QUERY
        response, exec_time = self.execute_search(request)
        
        # PROCESS RESULTS
        if not response:
            self._display_no_results("Basic Property Search", exec_time)
            return PropertySearchResult(
                query_name="Basic Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        results = self._process_search_results(response)
        
        # DISPLAY RESULTS (separated from query logic)
        self._display_basic_search(query_text, response, results, exec_time)
        
        # Convert results to PropertyResult objects
        property_results = []
        for r in results:
            property_results.append(PropertyResult(
                listing_id=r.get('listing_id', ''),
                property_type=r.get('property_type', 'Unknown'),
                price=r.get('price', 0),
                bedrooms=r.get('bedrooms', 0),
                bathrooms=r.get('bathrooms', 0),
                square_feet=r.get('square_feet', 0),
                year_built=r.get('year_built'),
                address=r.get('address', {}),
                description=r.get('description', ''),
                score=r.get('_score')
            ))
        
        return PropertySearchResult(
            query_name=f"Basic Property Search: '{query_text}'",
            query_description=f"Full-text search for '{query_text}' across property descriptions, amenities, and addresses with fuzzy matching to handle typos",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=request.to_dict(),
            es_features=[
                "Multi-Match Query: Searches across multiple fields simultaneously",
                "Field Boosting: Weights description 2x, amenities 1.5x for relevance",
                "Fuzzy Matching: AUTO fuzziness handles typos and variations",
                "Highlighting: Shows matched text fragments in results",
                "Query Context: Calculates relevance scores for ranking"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Fields searched: description, amenities, address.street, address.city, neighborhood_id"
            ],
            explanation=f"Searched for '{query_text}' across description, amenities, and address fields with fuzzy matching"
        )
    
    def demo_filtered_search(
        self,
        property_type: str = "single-family",
        min_price: float = 300000,
        max_price: float = 800000,
        min_bedrooms: int = 3,
        min_bathrooms: float = 2.0
    ) -> PropertySearchResult:
        """
        Execute filtered property search demo.
        
        This demonstrates:
        - Filter context for non-scoring criteria
        - Range queries for numeric fields
        - Combining multiple filter conditions
        - Efficient caching of filter results
        
        Args:
            property_type: Type of property
            min_price: Minimum price
            max_price: Maximum price  
            min_bedrooms: Minimum bedrooms
            min_bathrooms: Minimum bathrooms
            
        Returns:
            DemoQueryResult with filtered properties
        """
        console = Console()
        
        # Show filter criteria in a nice panel
        criteria_text = Text()
        criteria_text.append("🏠 Property Type: ", style="yellow")
        criteria_text.append(f"{PropertyDisplayFormatter.format_property_type(property_type)}\n", style="cyan")
        criteria_text.append("💰 Price Range: ", style="yellow")
        criteria_text.append(f"${min_price:,.0f} - ${max_price:,.0f}\n", style="green")
        criteria_text.append("🛏️  Bedrooms: ", style="yellow")
        criteria_text.append(f"{min_bedrooms}+\n", style="cyan")
        criteria_text.append("🚿 Bathrooms: ", style="yellow")
        criteria_text.append(f"{min_bathrooms}+", style="cyan")
        
        console.print(Panel(
            criteria_text,
            title="[bold cyan]🔍 Filtered Property Search[/bold cyan]",
            border_style="cyan"
        ))
        
        request = self.query_builder.filtered_search(
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            min_bathrooms=min_bathrooms
        )
        
        with console.status("[yellow]Applying filters and searching...[/yellow]") as status:
            response, exec_time = self.execute_search(request)
        
        if not response:
            console.print(Panel(
                "[red]Search failed - no response received[/red]",
                border_style="red"
            ))
            return PropertySearchResult(
                query_name="Filtered Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert hits to results with display formatting
        results = []
        
        if response.total_hits > 0:
            # Create property cards layout
            table = Table(
                title=f"[bold green]Found {response.total_hits} Matching Properties[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                width=120
            )
            table.add_column("#", style="dim", width=3)
            table.add_column("Address", style="cyan", width=35)
            table.add_column("Price", style="green", justify="right", width=12)
            table.add_column("Beds/Baths", style="yellow", justify="center", width=10)
            table.add_column("Sq Ft", style="blue", justify="right", width=10)
            table.add_column("Type", style="magenta", width=15)
            
            for i, hit in enumerate(response.hits[:15], 1):
                try:
                    prop = ESProperty(**hit.source)
                    formatted = PropertyDisplayFormatter.format_for_display(prop)
                    
                    beds_baths = f"{prop.bedrooms or 'N/A'}/{prop.bathrooms or 'N/A'}"
                    sq_ft = f"{prop.square_feet:,}" if prop.square_feet else "N/A"
                    
                    table.add_row(
                        str(i),
                        formatted['address'],
                        formatted['price'],
                        beds_baths,
                        sq_ft,
                        formatted['property_type']
                    )
                    
                    result = {
                        **hit.source,
                        '_display': formatted,
                        '_score': hit.score
                    }
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse property: {e}")
                    continue
            
            console.print(table)
            
            # Summary stats
            console.print(Panel(
                f"[green]✓[/green] Filters applied successfully\n"
                f"[green]✓[/green] Query time: [bold]{exec_time}ms[/bold]\n"
                f"[green]✓[/green] Total matches: [bold]{response.total_hits}[/bold]\n"
                f"[green]✓[/green] Showing: [bold]{len(results)}[/bold] properties",
                title="[bold]Filter Results[/bold]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[red]No properties found matching your filters.[/red]\n"
                "[yellow]Try adjusting your criteria for more results.[/yellow]",
                border_style="red"
            ))
        
        # Convert results to PropertyResult objects
        property_results = []
        for r in results:
            property_results.append(PropertyResult(
                listing_id=r.get('listing_id', ''),
                property_type=r.get('property_type', 'Unknown'),
                price=r.get('price', 0),
                bedrooms=r.get('bedrooms', 0),
                bathrooms=r.get('bathrooms', 0),
                square_feet=r.get('square_feet', 0),
                year_built=r.get('year_built'),
                address=r.get('address', {}),
                description=r.get('description', ''),
                score=r.get('_score')
            ))
        
        return PropertySearchResult(
            query_name="Filtered Property Search",
            query_description=f"Filter properties by: {PropertyDisplayFormatter.format_property_type(property_type)} type, ${min_price:,.0f}-${max_price:,.0f} price range, {min_bedrooms}+ bedrooms, {min_bathrooms}+ bathrooms",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=request.to_dict(),
            es_features=[
                "Bool Query with Filters: Combines multiple criteria using filter context",
                "Filter Context: Non-scoring queries cached for performance",
                "Range Queries: Numeric filtering for price, bedrooms, bathrooms",
                "Term Query: Exact matching on property type",
                "Sort by Price: Results ordered by price ascending"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Filtered fields: property_type, price, bedrooms, bathrooms"
            ],
            explanation=f"Properties: {property_type}, ${min_price:,.0f}-${max_price:,.0f}, {min_bedrooms}+ beds, {min_bathrooms}+ baths"
        )
    
    def demo_geo_search(
        self,
        center_lat: float = 37.7749,  # San Francisco
        center_lon: float = -122.4194,
        radius_km: float = 5.0,
        max_price: Optional[float] = 1000000
    ) -> PropertySearchResult:
        """
        Execute geo-distance search demo.
        
        This demonstrates:
        - Geo-distance filtering
        - Sorting by distance
        - Combining geo and other filters
        - Distance calculation in results
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius in km
            max_price: Optional price limit
            
        Returns:
            DemoQueryResult with nearby properties
        """
        console = Console()
        
        # Show search parameters with map emoji
        search_info = Text()
        search_info.append("📍 Center Location: ", style="yellow")
        search_info.append(f"({center_lat:.4f}, {center_lon:.4f})\n", style="cyan")
        search_info.append("📏 Search Radius: ", style="yellow")
        search_info.append(f"{radius_km} km\n", style="cyan")
        if max_price:
            search_info.append("💰 Max Price: ", style="yellow")
            search_info.append(f"${max_price:,.0f}", style="green")
        
        console.print(Panel(
            search_info,
            title="[bold cyan]🗺️  Geo-Distance Property Search[/bold cyan]",
            border_style="cyan"
        ))
        
        request = self.query_builder.geo_search(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            max_price=max_price
        )
        
        with console.status("[yellow]Calculating distances and searching...[/yellow]") as status:
            response, exec_time = self.execute_search(request)
        
        if not response:
            console.print(Panel(
                "[red]Search failed - no response received[/red]",
                border_style="red"
            ))
            return PropertySearchResult(
                query_name="Geo-Distance Property Search",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert hits to results with display formatting and distance
        results = []
        
        if response.total_hits > 0:
            # Create distance-sorted table
            table = Table(
                title=f"[bold green]Found {response.total_hits} Properties Within {radius_km}km[/bold green]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            table.add_column("#", style="dim", width=3)
            table.add_column("Distance", style="magenta", justify="right", width=10)
            table.add_column("Address", style="cyan", width=35)
            table.add_column("Price", style="green", justify="right")
            table.add_column("Details", style="yellow")
            
            for i, hit in enumerate(response.hits[:15], 1):
                try:
                    prop = ESProperty(**hit.source)
                    formatted = PropertyDisplayFormatter.format_for_display(prop)
                    result = {
                        **hit.source,
                        '_display': formatted,
                        '_score': hit.score
                    }
                    
                    # Get distance from sort values
                    sort_values = hit.model_extra.get('sort', [])
                    distance_str = "N/A"
                    if sort_values:
                        distance_km = sort_values[0]
                        result['_distance_km'] = distance_km
                        distance_str = f"{distance_km:.2f} km"
                    
                    table.add_row(
                        str(i),
                        distance_str,
                        formatted['address'],
                        formatted['price'],
                        formatted['summary']
                    )
                    
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse property: {e}")
                    continue
            
            console.print(table)
            
            # Show map visualization hint
            console.print(Panel(
                f"[green]✓[/green] Found [bold]{response.total_hits}[/bold] properties within [bold]{radius_km}km[/bold]\n"
                f"[green]✓[/green] Query time: [bold]{exec_time}ms[/bold]\n"
                f"[green]✓[/green] Results sorted by distance from center\n"
                f"[dim]💡 Tip: Properties are sorted from nearest to farthest[/dim]",
                title="[bold]📍 Location Search Results[/bold]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]No properties found within {radius_km}km of the specified location.[/red]\n"
                "[yellow]Try increasing the search radius or adjusting the price limit.[/yellow]",
                border_style="red"
            ))
        
        # Convert results to PropertyResult objects
        property_results = []
        for r in results:
            property_results.append(PropertyResult(
                listing_id=r.get('listing_id', ''),
                property_type=r.get('property_type', 'Unknown'),
                price=r.get('price', 0),
                bedrooms=r.get('bedrooms', 0),
                bathrooms=r.get('bathrooms', 0),
                square_feet=r.get('square_feet', 0),
                year_built=r.get('year_built'),
                address=r.get('address', {}),
                description=r.get('description', ''),
                score=r.get('_score')
            ))
        
        return PropertySearchResult(
            query_name="Geo-Distance Property Search",
            query_description=f"Find properties within {radius_km}km radius of coordinates ({center_lat:.4f}, {center_lon:.4f}) with optional price filtering",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(property_results),
            results=property_results,
            query_dsl=request.to_dict(),
            es_features=[
                "Geo-Distance Query: Filters documents within radius of a point",
                "Geo-Point Field: Uses address.location field for coordinates",
                "Distance Sorting: Results ordered by distance from center",
                "Distance Calculation: Arc method for accurate distances",
                "Combined Filters: Geo filter with optional price constraints"
            ],
            indexes_used=[
                "properties index: 420 real estate listings with geo-coordinates",
                "Geo field: address.location (lat/lon pairs)",
                f"Search area: {radius_km}km radius in San Francisco area"
            ],
            explanation=f"Properties within {radius_km}km of ({center_lat}, {center_lon})"
        )
    
    # ------------------------------------------------------------------------
    # RESULT PROCESSING METHODS
    # ------------------------------------------------------------------------
    
    def _process_search_results(self, response: SearchResponse) -> List[Dict[str, Any]]:
        """Process Elasticsearch response into result list."""
        results = []
        for hit in response.hits:
            try:
                prop = ESProperty(**hit.source)
                formatted = PropertyDisplayFormatter.format_for_display(prop)
                result = {
                    **hit.source,
                    '_display': formatted,
                    '_score': hit.score
                }
                if hit.highlight:
                    result['_highlights'] = hit.highlight
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse property: {e}")
                continue
        return results
    
    # ------------------------------------------------------------------------
    # DISPLAY METHODS - All UI/formatting logic separated at the bottom
    # ------------------------------------------------------------------------
    
    def _display_no_results(self, query_name: str, exec_time: int):
        """Display no results message."""
        console = Console()
        console.print(Panel(
            "[red]Search failed - no response received[/red]",
            border_style="red"
        ))
    
    def _display_basic_search(
        self,
        query_text: str,
        response: SearchResponse,
        results: List[Dict[str, Any]],
        exec_time: int
    ):
        """Display basic search results with rich formatting."""
        console = Console()
        
        # Header
        console.print(Panel.fit(
            f"[bold cyan]🔍 Basic Property Search[/bold cyan]\n[yellow]Query: '{query_text}'[/yellow]",
            border_style="cyan"
        ))
        
        if response.total_hits == 0:
            console.print(Panel(
                "[red]No properties found matching your search.[/red]",
                border_style="red"
            ))
            return
        
        # Results table
        table = Table(
            title=f"[bold green]Found {response.total_hits} Properties[/bold green]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Address", style="cyan", width=30)
        table.add_column("Price", style="green", justify="right")
        table.add_column("Details", style="yellow")
        table.add_column("Score", style="magenta", justify="right")
        
        for i, result in enumerate(results[:10], 1):
            display = result['_display']
            table.add_row(
                str(i),
                display['address'],
                display['price'],
                display['summary'],
                f"{result.get('_score', 0):.2f}"
            )
        
        console.print(table)
        
        # Statistics
        console.print(Panel(
            f"[green]✓[/green] Query executed in [bold]{exec_time}ms[/bold]\n"
            f"[green]✓[/green] Total hits: [bold]{response.total_hits}[/bold]\n"
            f"[green]✓[/green] Results shown: [bold]{len(results)}[/bold]",
            title="[bold]Search Statistics[/bold]",
            border_style="green"
        ))
    
    def demo_price_range_with_analytics(
        self,
        min_price: float = 400000,
        max_price: float = 800000
    ) -> PropertySearchResult:
        """
        Execute price range search with analytics.
        
        This demonstrates:
        - Range queries for price filtering
        - Statistical aggregations
        - Histogram aggregations for distribution
        - Terms aggregations for categories
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            DemoQueryResult with properties and statistics
        """
        console = Console()
        
        # Show price range header
        console.print(Panel(
            f"[bold cyan]📊 Price Range Analysis[/bold cyan]\n"
            f"[yellow]Range:[/yellow] [green]${min_price:,.0f} - ${max_price:,.0f}[/green]",
            border_style="cyan"
        ))
        
        request = self.query_builder.price_range_with_stats(
            min_price=min_price,
            max_price=max_price,
            include_stats=True
        )
        
        with console.status("[yellow]Analyzing price distribution...[/yellow]") as status:
            response, exec_time = self.execute_search(request)
        
        if not response:
            console.print(Panel(
                "[red]Analysis failed - no response received[/red]",
                border_style="red"
            ))
            return PropertySearchResult(
                query_name="Price Range Search with Analytics",
                execution_time_ms=exec_time,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl=request.to_dict()
            )
        
        # Convert hits to results with display formatting
        results = []
        for hit in response.hits:
            try:
                prop = ESProperty(**hit.source)
                formatted = PropertyDisplayFormatter.format_for_display(prop)
                result = {
                    **hit.source,
                    '_display': formatted,
                    '_score': hit.score
                }
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse property: {e}")
                continue
        
        # Process aggregations - keep as dict for compatibility
        aggregations = None
        if response.aggregations:
            aggregations = {}
            
            # Show aggregation results in a nice format
            if 'price_stats' in response.aggregations:
                stats = response.aggregations['price_stats']
                aggregations['price_stats'] = {
                    "min": stats.get('min', 0),
                    "max": stats.get('max', 0),
                    "avg": stats.get('avg', 0),
                    "sum": stats.get('sum', 0),
                    "count": stats.get('count', 0)
                }
                
                # Create statistics panel
                stats_table = Table(box=box.SIMPLE, show_header=False)
                stats_table.add_column("Metric", style="yellow")
                stats_table.add_column("Value", style="green", justify="right")
                
                stats_table.add_row("Properties Found", str(stats.get('count', 0)))
                stats_table.add_row("Minimum Price", f"${stats.get('min', 0):,.0f}")
                stats_table.add_row("Maximum Price", f"${stats.get('max', 0):,.0f}")
                stats_table.add_row("Average Price", f"${stats.get('avg', 0):,.0f}")
                
                console.print(Panel(
                    stats_table,
                    title="[bold]📈 Price Statistics[/bold]",
                    border_style="blue"
                ))
            
            # Property type distribution
            if 'property_types' in response.aggregations:
                aggregations['property_types'] = response.aggregations['property_types']
                
                # Show property type distribution
                type_buckets = response.aggregations['property_types'].get('buckets', [])
                if type_buckets:
                    type_table = Table(box=box.SIMPLE, show_header=False)
                    type_table.add_column("Type", style="cyan")
                    type_table.add_column("Count", style="magenta", justify="right")
                    
                    for bucket in type_buckets[:5]:
                        prop_type = PropertyDisplayFormatter.format_property_type(bucket['key'])
                        type_table.add_row(prop_type, str(bucket['doc_count']))
                    
                    console.print(Panel(
                        type_table,
                        title="[bold]🏠 Property Types[/bold]",
                        border_style="magenta"
                    ))
            
            # Price histogram
            if 'price_histogram' in response.aggregations:
                aggregations['price_histogram'] = response.aggregations['price_histogram']
                
                # Show price distribution as a simple bar chart
                hist_buckets = response.aggregations['price_histogram'].get('buckets', [])
                if hist_buckets:
                    console.print(Panel(
                        "[bold]📊 Price Distribution (in $100k buckets)[/bold]",
                        border_style="yellow"
                    ))
                    
                    max_count = max(b['doc_count'] for b in hist_buckets) if hist_buckets else 1
                    for bucket in hist_buckets[:10]:
                        price_range = f"${bucket['key']/1000:.0f}k"
                        count = bucket['doc_count']
                        bar_width = int((count / max_count) * 40)
                        bar = "█" * bar_width
                        console.print(f"  {price_range:>10} │ {bar} {count}")
            
            # Bedroom stats
            if 'bedroom_stats' in response.aggregations:
                aggregations['bedroom_stats'] = response.aggregations['bedroom_stats']
        
        # Show final summary
        console.print(Panel(
            f"[green]✓[/green] Analysis complete in [bold]{exec_time}ms[/bold]\n"
            f"[green]✓[/green] Properties analyzed: [bold]{response.total_hits}[/bold]\n"
            f"[green]✓[/green] Statistical aggregations calculated",
            title="[bold]✅ Search Complete[/bold]",
            border_style="green"
        ))
        
        # Convert results to PropertyResult objects
        property_results = []
        for r in results:
            property_results.append(PropertyResult(
                listing_id=r.get('listing_id', ''),
                property_type=r.get('property_type', 'Unknown'),
                price=r.get('price', 0),
                bedrooms=r.get('bedrooms', 0),
                bathrooms=r.get('bathrooms', 0),
                square_feet=r.get('square_feet', 0),
                year_built=r.get('year_built'),
                address=r.get('address', {}),
                description=r.get('description', ''),
                score=r.get('_score')
            ))
        
        return AggregationSearchResult(
            query_name="Price Range Search with Analytics",
            query_description=f"Search properties in ${min_price:,.0f}-${max_price:,.0f} range with statistical aggregations for market analysis",
            execution_time_ms=exec_time,
            total_hits=response.total_hits,
            returned_hits=len(property_results),
            top_properties=property_results,
            query_dsl=request.to_dict(),
            aggregations=aggregations,
            es_features=[
                "Range Query: Filter properties by price range",
                "Stats Aggregation: Calculate min, max, avg, sum statistics",
                "Histogram Aggregation: Price distribution in $100k buckets",
                "Terms Aggregation: Group by property types",
                "Multi-Aggregation: Multiple analytics in single query"
            ],
            indexes_used=[
                "properties index: 420 real estate listings",
                "Aggregation fields: price, property_type, bedrooms",
                "Statistical analysis across matching properties"
            ],
            explanation=f"Properties ${min_price:,.0f}-${max_price:,.0f} with statistical analysis"
        )


# Public API functions for backward compatibility
def demo_basic_property_search(
    es_client: Elasticsearch,
    query_text: str = "family home with pool",
    size: int = 10
) -> PropertySearchResult:
    """
    Demo 1: Basic property search using multi-match query.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_basic_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_basic_search(query_text)


def demo_filtered_property_search(
    es_client: Elasticsearch,
    property_type: str = "single-family",
    min_price: float = 300000,
    max_price: float = 800000,
    min_bedrooms: int = 3,
    min_bathrooms: float = 2.0,
    amenities: Optional[List[str]] = None
) -> PropertySearchResult:
    """
    Demo 2: Filtered property search with multiple criteria.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_filtered_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_filtered_search(
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        min_bathrooms=min_bathrooms
    )


def demo_geo_distance_search(
    es_client: Elasticsearch,
    center_lat: float = 37.7749,
    center_lon: float = -122.4194,
    radius_km: float = 5.0,
    property_type: Optional[str] = None,
    max_price: Optional[float] = None
) -> PropertySearchResult:
    """
    Demo 3: Geo-distance search for properties near a location.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_geo_search for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_geo_search(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        max_price=max_price
    )


def demo_price_range_search(
    es_client: Elasticsearch,
    min_price: float = 400000,
    max_price: float = 800000
) -> PropertySearchResult:
    """
    Demo 4: Price range search with aggregation statistics.
    
    Refactored to use Pydantic models for type safety.
    See PropertySearchDemo.demo_price_range_with_analytics for implementation.
    """
    demo = PropertySearchDemo(es_client)
    return demo.demo_price_range_with_analytics(
        min_price=min_price,
        max_price=max_price
    )


# Aliases for backward compatibility with existing imports
demo_property_filter = demo_filtered_property_search
demo_geo_search = demo_geo_distance_search