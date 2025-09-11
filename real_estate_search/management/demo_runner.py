"""
Demo query runner module for executing and managing demo queries.
"""

import logging
from typing import List, Optional, Callable, Dict, Any
from elasticsearch import Elasticsearch

from ..demo_queries import (
    demo_basic_property_search,
    demo_property_filter,
    demo_geo_search,
    demo_neighborhood_stats,
    demo_price_distribution,
    demo_wikipedia_location_search,
    demo_simplified_relationships,
    demo_natural_language_examples,
    demo_rich_property_listing,
    demo_hybrid_search,
    demo_location_understanding,
    demo_location_aware_waterfront_luxury,
    demo_location_aware_family_schools,
    demo_location_aware_recreation_mountain,
    demo_location_aware_search_showcase
)
from ..demo_queries.wikipedia import WikipediaDemoRunner
from .models import DemoQuery, DemoExecutionResult


class DemoRunner:
    """Manages and executes demo queries."""
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize demo runner.
        
        Args:
            es_client: Elasticsearch client
        """
        self.es_client = es_client
        self.logger = logging.getLogger(__name__)
        self.demo_registry = self._initialize_demo_registry()
    
    def _initialize_demo_registry(self) -> Dict[int, DemoQuery]:
        """
        Initialize the registry of demo queries.
        
        Returns:
            Dictionary mapping demo numbers to DemoQuery objects
        """
        demos = {
            1: DemoQuery(
                number=1,
                name="Basic Property Search",
                description="Multi-match search across property fields",
                query_function="demo_basic_property_search"
            ),
            2: DemoQuery(
                number=2,
                name="Property Filter Search",
                description="Filter by type, bedrooms, price, location",
                query_function="demo_property_filter"
            ),
            3: DemoQuery(
                number=3,
                name="Geographic Distance Search",
                description="Find properties within radius of point",
                query_function="demo_geo_search"
            ),
            4: DemoQuery(
                number=4,
                name="Neighborhood Statistics",
                description="Aggregate property stats by neighborhood",
                query_function="demo_neighborhood_stats"
            ),
            5: DemoQuery(
                number=5,
                name="Price Distribution Analysis",
                description="Histogram of prices by property type",
                query_function="demo_price_distribution"
            ),
            6: DemoQuery(
                number=6,
                name="Wikipedia Full-Text Search",
                description="Full-text search across Wikipedia articles",
                query_function="WikipediaDemoRunner.run_demo"
            ),
            7: DemoQuery(
                number=7,
                name="Property Relationships via Denormalized Index",
                description="Demonstrates single-query retrieval using denormalized index",
                query_function="demo_simplified_relationships"
            ),
            8: DemoQuery(
                number=8,
                name="Natural Language Examples",
                description="Multiple examples of natural language property search",
                query_function="demo_natural_language_examples"
            ),
            9: DemoQuery(
                number=9,
                name="Rich Real Estate Listing",
                description="Complete property listing with neighborhood and Wikipedia data from single query",
                query_function="demo_rich_property_listing"
            ),
            10: DemoQuery(
                number=10,
                name="Hybrid Search with RRF",
                description="Combines semantic vector search with text search using native Elasticsearch RRF",
                query_function="demo_hybrid_search"
            ),
            11: DemoQuery(
                number=11,
                name="Location Understanding",
                description="Extract location information from natural language queries using DSPy",
                query_function="demo_location_understanding"
            ),
            12: DemoQuery(
                number=12,
                name="Location-Aware: Waterfront Luxury",
                description="Luxury waterfront property search with city-specific filtering",
                query_function="demo_location_aware_waterfront_luxury"
            ),
            13: DemoQuery(
                number=13,
                name="Location-Aware: Family Schools",
                description="Family-oriented search with school proximity and location extraction",
                query_function="demo_location_aware_family_schools"
            ),
            14: DemoQuery(
                number=14,
                name="Location-Aware: Recreation Mountain",
                description="Recreation-focused property search in mountain areas",
                query_function="demo_location_aware_recreation_mountain"
            ),
            15: DemoQuery(
                number=15,
                name="Location-Aware Search Showcase",
                description="Run multiple location-aware demos to showcase full capabilities",
                query_function="demo_location_aware_search_showcase"
            ),
            16: DemoQuery(
                number=16,
                name="Wikipedia Location Search",
                description="Wikipedia search with automatic location extraction from natural language",
                query_function="demo_wikipedia_location_search"
            )
        }
        return demos
    
    def get_demo_list(self) -> List[DemoQuery]:
        """
        Get list of all available demo queries.
        
        Returns:
            List of demo queries
        """
        return list(self.demo_registry.values())
    
    def run_demo(self, demo_number: int, verbose: bool = False) -> DemoExecutionResult:
        """
        Run a specific demo query.
        
        Args:
            demo_number: Demo query number to run
            verbose: If True, include query DSL in result
            
        Returns:
            Demo execution result
        """
        if demo_number not in self.demo_registry:
            error_msg = f"Invalid demo number: {demo_number}"
            self.logger.error(error_msg)
            return DemoExecutionResult(
                demo_number=demo_number,
                demo_name="Unknown",
                success=False,
                error=error_msg
            )
        
        demo = self.demo_registry[demo_number]
        
        try:
            self.logger.info(f"Running demo {demo_number}: {demo.name}")
            
            # Get the demo function
            query_func = self._get_demo_function(demo_number)
            
            # Execute the demo query
            result = query_func(self.es_client)
            
            # Handle demos that return a list of results
            if demo_number in [8, 15]:
                # demo_natural_language_examples and demo_location_aware_search_showcase return List[DemoQueryResult]
                if not result:  # Empty list means initialization failed
                    return DemoExecutionResult(
                        demo_number=demo_number,
                        demo_name=demo.name,
                        success=False,
                        error="Failed to initialize service or no results"
                    )
                
                # Aggregate statistics from all example results
                total_time = sum(r.execution_time_ms for r in result)
                total_hits = sum(r.total_hits for r in result)
                total_returned = sum(r.returned_hits for r in result)
                
                # Create execution result with aggregated stats
                execution_result = DemoExecutionResult(
                    demo_number=demo_number,
                    demo_name=demo.name,
                    success=True,
                    execution_time_ms=total_time,
                    total_hits=total_hits,
                    returned_hits=total_returned,
                    query_dsl={"examples_count": len(result)} if verbose else None
                )
                
                self.logger.info(f"Successfully executed {len(result)} examples for demo {demo_number}")
                return execution_result
            
            # Standard handling for demos that return single DemoQueryResult
            # Extract query DSL if verbose - all results have query_dsl field
            query_dsl = None
            if verbose and result:
                query_dsl = result.query_dsl
            
            # Create execution result
            execution_result = DemoExecutionResult(
                demo_number=demo_number,
                demo_name=demo.name,
                success=True,
                execution_time_ms=getattr(result, 'execution_time_ms', None),
                total_hits=getattr(result, 'total_hits', None),
                returned_hits=getattr(result, 'returned_hits', None),
                query_dsl=query_dsl
            )
            
            self.logger.info(f"Successfully executed demo {demo_number}: {demo.name}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Failed to execute demo {demo_number}: {str(e)}")
            return DemoExecutionResult(
                demo_number=demo_number,
                demo_name=demo.name,
                success=False,
                error=str(e)
            )
    
    def _get_demo_function(self, demo_number: int) -> Callable:
        """
        Get the demo function for a given demo number.
        
        Args:
            demo_number: Demo number
            
        Returns:
            Demo function callable
        """
        demo_functions = {
            1: demo_basic_property_search,
            2: demo_property_filter,
            3: demo_geo_search,
            4: demo_neighborhood_stats,
            5: demo_price_distribution,
            6: lambda es: WikipediaDemoRunner(es).run_demo(),
            7: demo_simplified_relationships,
            8: demo_natural_language_examples,
            9: demo_rich_property_listing,
            10: demo_hybrid_search,
            11: demo_location_understanding,
            12: demo_location_aware_waterfront_luxury,
            13: demo_location_aware_family_schools,
            14: demo_location_aware_recreation_mountain,
            15: demo_location_aware_search_showcase,
            16: demo_wikipedia_location_search
        }
        
        return demo_functions[demo_number]
    
    def get_demo_descriptions(self) -> Dict[int, str]:
        """
        Get special descriptions for specific demos.
        
        Returns:
            Dictionary of demo number to special description
        """
        descriptions = {
            6: """🔍 Full-Text Search Overview:
This demo showcases Wikipedia full-text search after HTML enrichment:

• Searches across complete Wikipedia article content
• Demonstrates various query patterns and operators
• Shows highlighted relevant content from articles""",
            
            7: """📊 Denormalized Index Architecture:
This demo shows property relationships using a denormalized index:

• Single query retrieves property, neighborhood, and Wikipedia data
• All related data pre-joined at index time for optimal performance
• Demonstrates production-ready pattern for read-heavy applications
• Trades storage space for dramatic query performance gains""",
            
            8: """🔍 Natural Language Search Examples:
Demonstrates various natural language queries:

• Family-oriented: "cozy family home near good schools and parks"
• Urban living: "modern downtown condo with city views"
• Work from home: "spacious property with home office and fast internet"
• Eco-friendly: "eco-friendly house with solar panels"
• And more examples showing semantic understanding""",
            
            9: """🏡 Rich Real Estate Listing (Single Query):
Demonstrates the power of denormalized property_relationships index:

✨ Complete Property Information:
• Property details (price, beds, baths, square footage)
• Full property description and features
• Amenities and special characteristics

📍 Embedded Neighborhood Data:
• Demographics (population, median income)
• Walkability and school ratings
• Local amenities and characteristics
• Neighborhood description

📚 Wikipedia Context:
• Related articles about the area
• Historical and cultural information
• Local landmarks and points of interest

⚡ Performance Benefits:
• Single query retrieves ALL data
• 5-10x faster than multiple queries
• Simplified error handling
• Clean, maintainable code

This is what modern real estate platforms need - rich, contextual
listings that help buyers make informed decisions, all delivered
with exceptional performance!"""
        }
        
        return descriptions