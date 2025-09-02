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
    demo_semantic_search,
    demo_multi_entity_search,
    demo_wikipedia_search,
    demo_wikipedia_fulltext,
    demo_simplified_relationships,
    demo_natural_language_search,
    demo_natural_language_examples,
    demo_semantic_vs_keyword_comparison,
    demo_rich_property_listing,
    demo_hybrid_search,
    demo_location_understanding,
    demo_location_aware_waterfront_luxury,
    demo_location_aware_family_schools,
    demo_location_aware_urban_modern,
    demo_location_aware_recreation_mountain,
    demo_location_aware_historic_urban,
    demo_location_aware_beach_proximity,
    demo_location_aware_investment_market,
    demo_location_aware_luxury_urban_views,
    demo_location_aware_suburban_architecture,
    demo_location_aware_neighborhood_character,
    demo_location_aware_search_showcase
)
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
                name="Semantic Similarity Search",
                description="Find similar properties using embeddings",
                query_function="demo_semantic_search"
            ),
            7: DemoQuery(
                number=7,
                name="Multi-Entity Combined Search",
                description="Search across all entity types",
                query_function="demo_multi_entity_search"
            ),
            8: DemoQuery(
                number=8,
                name="Wikipedia Article Search",
                description="Search Wikipedia with location filters",
                query_function="demo_wikipedia_search"
            ),
            9: DemoQuery(
                number=9,
                name="Wikipedia Full-Text Search",
                description="Full-text search across Wikipedia articles",
                query_function="demo_wikipedia_fulltext"
            ),
            10: DemoQuery(
                number=10,
                name="Property Relationships via Denormalized Index",
                description="Demonstrates single-query retrieval using denormalized index",
                query_function="demo_simplified_relationships"
            ),
            11: DemoQuery(
                number=11,
                name="Natural Language Semantic Search",
                description="Convert natural language queries to embeddings for semantic search",
                query_function="demo_natural_language_search"
            ),
            12: DemoQuery(
                number=12,
                name="Natural Language Examples",
                description="Multiple examples of natural language property search",
                query_function="demo_natural_language_examples"
            ),
            13: DemoQuery(
                number=13,
                name="Semantic vs Keyword Comparison",
                description="Compare semantic embedding search with traditional keyword search",
                query_function="demo_semantic_vs_keyword_comparison"
            ),
            14: DemoQuery(
                number=14,
                name="Rich Real Estate Listing",
                description="Complete property listing with neighborhood and Wikipedia data from single query",
                query_function="demo_rich_property_listing"
            ),
            15: DemoQuery(
                number=15,
                name="Hybrid Search with RRF",
                description="Combines semantic vector search with text search using native Elasticsearch RRF",
                query_function="demo_hybrid_search"
            ),
            16: DemoQuery(
                number=16,
                name="Location Understanding",
                description="Extract location information from natural language queries using DSPy",
                query_function="demo_location_understanding"
            ),
            17: DemoQuery(
                number=17,
                name="Location-Aware: Waterfront Luxury",
                description="Luxury waterfront property search with city-specific filtering",
                query_function="demo_location_aware_waterfront_luxury"
            ),
            18: DemoQuery(
                number=18,
                name="Location-Aware: Family Schools",
                description="Family-oriented search with school proximity and location extraction",
                query_function="demo_location_aware_family_schools"
            ),
            19: DemoQuery(
                number=19,
                name="Location-Aware: Urban Modern",
                description="Modern urban property search with neighborhood understanding",
                query_function="demo_location_aware_urban_modern"
            ),
            20: DemoQuery(
                number=20,
                name="Location-Aware: Recreation Mountain",
                description="Recreation-focused property search in mountain areas",
                query_function="demo_location_aware_recreation_mountain"
            ),
            21: DemoQuery(
                number=21,
                name="Location-Aware: Historic Urban",
                description="Historic property search in urban neighborhoods",
                query_function="demo_location_aware_historic_urban"
            ),
            22: DemoQuery(
                number=22,
                name="Location-Aware: Beach Proximity",
                description="Beach property search with proximity-based location understanding",
                query_function="demo_location_aware_beach_proximity"
            ),
            23: DemoQuery(
                number=23,
                name="Location-Aware: Investment Market",
                description="Investment property search with market-specific targeting",
                query_function="demo_location_aware_investment_market"
            ),
            24: DemoQuery(
                number=24,
                name="Location-Aware: Luxury Urban Views",
                description="Luxury urban property search emphasizing premium views",
                query_function="demo_location_aware_luxury_urban_views"
            ),
            25: DemoQuery(
                number=25,
                name="Location-Aware: Suburban Architecture",
                description="Architectural style search in suburban markets",
                query_function="demo_location_aware_suburban_architecture"
            ),
            26: DemoQuery(
                number=26,
                name="Location-Aware: Neighborhood Character",
                description="Neighborhood character search with architectural details",
                query_function="demo_location_aware_neighborhood_character"
            ),
            27: DemoQuery(
                number=27,
                name="Location-Aware Search Showcase",
                description="Run multiple location-aware demos to showcase full capabilities",
                query_function="demo_location_aware_search_showcase"
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
            if demo_number in [12, 27]:
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
            # Extract query DSL if verbose
            query_dsl = None
            if verbose and hasattr(result, 'query'):
                query_dsl = result.query
            
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
            6: demo_semantic_search,
            7: demo_multi_entity_search,
            8: demo_wikipedia_search,
            9: demo_wikipedia_fulltext,
            10: demo_simplified_relationships,
            11: demo_natural_language_search,
            12: demo_natural_language_examples,
            13: demo_semantic_vs_keyword_comparison,
            14: demo_rich_property_listing,
            15: demo_hybrid_search,
            16: demo_location_understanding,
            17: demo_location_aware_waterfront_luxury,
            18: demo_location_aware_family_schools,
            19: demo_location_aware_urban_modern,
            20: demo_location_aware_recreation_mountain,
            21: demo_location_aware_historic_urban,
            22: demo_location_aware_beach_proximity,
            23: demo_location_aware_investment_market,
            24: demo_location_aware_luxury_urban_views,
            25: demo_location_aware_suburban_architecture,
            26: demo_location_aware_neighborhood_character,
            27: demo_location_aware_search_showcase
        }
        
        return demo_functions[demo_number]
    
    def get_demo_descriptions(self) -> Dict[int, str]:
        """
        Get special descriptions for specific demos.
        
        Returns:
            Dictionary of demo number to special description
        """
        descriptions = {
            9: """🔍 Full-Text Search Overview:
This demo showcases Wikipedia full-text search after HTML enrichment:

• Searches across complete Wikipedia article content
• Demonstrates various query patterns and operators
• Shows highlighted relevant content from articles""",
            
            10: """📊 Denormalized Index Architecture:
This demo shows property relationships using a denormalized index:

• Single query retrieves property, neighborhood, and Wikipedia data
• All related data pre-joined at index time for optimal performance
• Demonstrates production-ready pattern for read-heavy applications
• Trades storage space for dramatic query performance gains""",
            
            11: """🤖 Natural Language Semantic Search:
This demo uses AI embeddings to understand natural language queries:

• Converts text queries to 1024-dimensional vectors using Voyage-3
• Performs KNN search against pre-computed property embeddings
• Understands semantic meaning beyond simple keyword matching
• Example: "modern home with mountain views and open floor plan" finds relevant properties""",
            
            12: """🔍 Natural Language Search Examples:
Demonstrates various natural language queries:

• Family-oriented: "cozy family home near good schools and parks"
• Urban living: "modern downtown condo with city views"
• Work from home: "spacious property with home office and fast internet"
• Eco-friendly: "eco-friendly house with solar panels"
• And more examples showing semantic understanding""",
            
            13: """⚖️ Semantic vs Keyword Search Comparison:
Compares AI-powered semantic search with traditional keyword search:

• Runs the same query using both approaches
• Shows how semantic search understands meaning
• Demonstrates differences in result relevance
• Highlights unique strengths of each approach""",
            
            14: """🏡 Rich Real Estate Listing (Single Query):
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