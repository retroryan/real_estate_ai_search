"""
Demo runner for rich listing functionality.

This module orchestrates the execution of rich listing demos,
coordinating between query building, search execution, and display.
"""

from typing import Optional
from elasticsearch import Elasticsearch
import logging

from .models import RichListingDisplayConfig
from .query_builder import RichListingQueryBuilder
from .search_executor import RichListingSearchExecutor
from .display_service import RichListingDisplayService
from real_estate_search.demo_queries.models import DemoQueryResult


logger = logging.getLogger(__name__)

# Default demo property ID from the actual Elasticsearch data
DEFAULT_DEMO_PROPERTY_ID = "prop-oak-125"


class RichListingDemoRunner:
    """
    Orchestrates rich listing demo execution.
    
    This class coordinates between query building, search execution,
    and display to provide complete demo workflows.
    """
    
    def __init__(
        self,
        es_client: Elasticsearch,
        config: Optional[RichListingDisplayConfig] = None
    ):
        """
        Initialize the demo runner.
        
        Args:
            es_client: Elasticsearch client
            config: Display configuration
        """
        self.es_client = es_client
        self.config = config or RichListingDisplayConfig()
        
        # Initialize components
        self.query_builder = RichListingQueryBuilder()
        self.search_executor = RichListingSearchExecutor(es_client)
        self.display_service = RichListingDisplayService(config)
    
    def run_rich_listing(
        self,
        listing_id: Optional[str] = None
    ) -> DemoQueryResult:
        """
        Run a rich property listing demo.
        
        This demonstrates retrieving a complete property listing with
        embedded neighborhood and Wikipedia data from a single query.
        
        Args:
            listing_id: Optional specific listing ID to display
            
        Returns:
            DemoQueryResult with the listing data
        """
        # Use provided ID or default
        target_listing_id = listing_id or DEFAULT_DEMO_PROPERTY_ID
        
        logger.info(f"Running rich listing demo for property: {target_listing_id}")
        
        # Execute the search
        search_result = self.search_executor.execute_listing_query(target_listing_id)
        
        # Check if we found the listing
        if not search_result.has_results:
            logger.warning(f"No property found with ID: {target_listing_id}")
            return self._create_empty_result(target_listing_id, search_result.execution_time_ms)
        
        # Get the first (and should be only) listing
        listing = search_result.first_listing
        
        # Display the listing
        self.display_service.display_rich_listing(listing)
        
        # Display search summary
        self.display_service.display_search_summary(search_result)
        
        # Generate and open HTML if configured
        html_path = self.display_service.generate_and_open_html(listing)
        if html_path:
            self._display_html_status(html_path)
        
        # Create demo result
        return self._create_demo_result(listing, search_result, target_listing_id)
    
    def run_search(
        self,
        query_text: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        size: Optional[int] = None
    ) -> DemoQueryResult:
        """
        Run a search with filters and display results.
        
        Args:
            query_text: Text to search
            city: City filter
            state: State filter
            property_type: Property type filter
            min_price: Minimum price
            max_price: Maximum price
            min_bedrooms: Minimum bedrooms
            size: Number of results
            
        Returns:
            DemoQueryResult with search results
        """
        logger.info(f"Running rich listing search: {query_text}")
        
        # Execute the search
        search_result = self.search_executor.execute_search_query(
            query_text=query_text,
            city=city,
            state=state,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            size=size
        )
        
        # Display results
        if search_result.has_results:
            for listing in search_result.listings:
                self.display_service.display_rich_listing(listing)
        
        # Display search summary
        self.display_service.display_search_summary(search_result)
        
        # Convert to demo result
        results_data = []
        for listing in search_result.listings:
            property_data = listing.property_data.model_dump()
            property_data['neighborhood'] = listing.neighborhood.model_dump() if listing.neighborhood else None
            property_data['wikipedia_articles'] = [
                article.model_dump() for article in listing.wikipedia_articles
            ]
            results_data.append(property_data)
        
        return DemoQueryResult(
            query_name="Rich Property Search",
            total_hits=search_result.total_hits,
            returned_hits=search_result.returned_hits,
            execution_time_ms=search_result.execution_time_ms,
            results=results_data,
            query_dsl=search_result.query_dsl,
            aggregations=search_result.aggregations
        )
    
    def _create_demo_result(
        self,
        listing,
        search_result,
        listing_id: str
    ) -> DemoQueryResult:
        """
        Create a DemoQueryResult from the search results.
        
        Args:
            listing: The rich listing model
            search_result: The search result
            listing_id: The requested listing ID
            
        Returns:
            DemoQueryResult for the demo system
        """
        # Prepare the result data
        property_data = listing.property_data.model_dump()
        property_data['neighborhood'] = listing.neighborhood.model_dump() if listing.neighborhood else None
        property_data['wikipedia_articles'] = [
            article.model_dump() for article in listing.wikipedia_articles
        ]
        
        # Create aggregations showing data sources
        aggregations = {
            "data_sources": {
                "property": 1,
                "neighborhood": 1 if listing.neighborhood else 0,
                "wikipedia_articles": len(listing.wikipedia_articles)
            }
        }
        
        return DemoQueryResult(
            query_name="Rich Property Listing (Single Query)",
            total_hits=search_result.total_hits,
            returned_hits=search_result.returned_hits,
            execution_time_ms=search_result.execution_time_ms,
            results=[property_data],
            query_dsl=search_result.query_dsl,
            aggregations=aggregations
        )
    
    def _create_empty_result(
        self,
        listing_id: str,
        execution_time_ms: int
    ) -> DemoQueryResult:
        """
        Create an empty result when no listing is found.
        
        Args:
            listing_id: The requested listing ID
            execution_time_ms: Query execution time
            
        Returns:
            Empty DemoQueryResult
        """
        return DemoQueryResult(
            query_name="Rich Property Listing",
            total_hits=0,
            returned_hits=0,
            execution_time_ms=execution_time_ms,
            results=[],
            query_dsl={"query": {"term": {"listing_id": listing_id}}}
        )
    
    def _display_html_status(self, html_path) -> None:
        """
        Display HTML generation status in console.
        
        Args:
            html_path: Path to generated HTML file
        """
        if self.display_service.console:
            self.display_service.console.print("\n")
            self.display_service.console.print(Panel(
                f"[bold green]✅ HTML listing generated![/bold green]\n\n"
                f"📄 File: {html_path.name}\n"
                f"📁 Location: {html_path.absolute()}\n\n"
                f"[green]The property listing page has been opened in your browser[/green]",
                title="📊 HTML Report Generated",
                border_style="green"
            ))