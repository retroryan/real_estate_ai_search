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
    demo_relationship_search,
    demo_wikipedia_fulltext
)
from ..demo_queries.demo_single_query_relationships import demo_simplified_relationships
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
                name="Property-Neighborhood-Wikipedia Relationships",
                description="Demonstrates entity linking across indices",
                query_function="demo_relationship_search"
            ),
            10: DemoQuery(
                number=10,
                name="Wikipedia Full-Text Search",
                description="Full-text search across Wikipedia articles",
                query_function="demo_wikipedia_fulltext"
            ),
            11: DemoQuery(
                number=11,
                name="Simplified Single-Query Relationships",
                description="Denormalized index for single-query retrieval",
                query_function="demo_simplified_relationships"
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
            9: demo_relationship_search,
            10: demo_wikipedia_fulltext,
            11: demo_simplified_relationships
        }
        
        return demo_functions[demo_number]
    
    def get_demo_descriptions(self) -> Dict[int, str]:
        """
        Get special descriptions for specific demos.
        
        Returns:
            Dictionary of demo number to special description
        """
        descriptions = {
            9: """📊 Query Architecture Overview:
This demo performs three types of relationship queries:

1️⃣  Property → Neighborhood → Wikipedia
   Starting from a property, finds its neighborhood and related articles
   Shows: Property details, neighborhood context, location Wikipedia

2️⃣  Neighborhood → Properties + Wikipedia
   Shows all properties in a neighborhood plus Wikipedia context
   Example: Pacific Heights with all its properties and articles

3️⃣  Location → Properties + Wikipedia
   City-level search combining real estate and encyclopedia data
   Example: All San Francisco properties with city Wikipedia articles

🔗 Relationships established through:
   • neighborhood_id field linking properties to neighborhoods
   • Location matching between Wikipedia and property/neighborhood data
   • Confidence scoring (primary=95%, neighborhood=85%, park=90%, etc.)""",
            
            10: """🔍 Full-Text Search Overview:
This demo showcases Wikipedia full-text search after HTML enrichment:

• Searches across complete Wikipedia article content
• Demonstrates various query patterns and operators
• Shows highlighted relevant content from articles"""
        }
        
        return descriptions