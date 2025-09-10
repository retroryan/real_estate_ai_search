"""
Demo for location understanding functionality.
"""

import logging
import time
from typing import Dict, Any, List
from elasticsearch import Elasticsearch

from .result_models import LocationExtractionResult
from ..hybrid import LocationUnderstandingModule
from ..models.location import LocationIntent

logger = logging.getLogger(__name__)


def demo_location_understanding(es_client: Elasticsearch) -> LocationExtractionResult:
    """
    Demo: Extract location information from natural language queries.
    
    Demonstrates DSPy-based location understanding for real estate queries,
    extracting city, state, neighborhood, and ZIP code information.
    
    Following DSPy best practices:
    - Module called as callable (not calling forward() directly)
    - Synchronous execution (no async)
    - Returns Pydantic model for structured output
    
    Args:
        es_client: Elasticsearch client (not used in this demo)
        
    Returns:
        LocationExtractionResult with location extraction examples
    """
    # Example queries using actual cities in our data
    # Includes various location formats: city only, city+state, abbreviated states
    # Additional queries demonstrate different property types with full location specification
    test_queries = [
        "Find a great family home in San Francisco",
        "Luxury condo in Oakland California", 
        "Properties near downtown San Jose",
        "Affordable homes in Salinas CA",
        "Condo in San Francisco California",
        "Townhome in Oakland California"
    ]
    
    logger.info(f"Running location understanding demo with {len(test_queries)} example queries")
    
    # Initialize location understanding module
    module = LocationUnderstandingModule()
    
    start_time = time.time()
    results: List[LocationIntent] = []
    
    # Extract location intent for each query
    for query in test_queries:
        try:
            # DO NOT CHANGE - THIS IS DSPY BEST PRACTICE!!!!
            # Call module as callable, not forward() directly
            result = module(query)
            
            logger.info(f"Query: '{query}'")
            logger.info(f"  City: {result.city}")
            logger.info(f"  State: {result.state}")
            logger.info(f"  Has Location: {result.has_location}")
            logger.info(f"  Cleaned Query: '{result.cleaned_query}'")
            
            # Store the Pydantic model directly
            results.append(result)
            
        except Exception as e:
            logger.error(f"Location understanding failed for '{query}': {e}")
            # Create LocationIntent with defaults for errors
            results.append(LocationIntent(cleaned_query=query))
    
    execution_time = int((time.time() - start_time) * 1000)
    
    # Return LocationExtractionResult
    return LocationExtractionResult(
        query_name="Location Understanding Demo",
        query_description="Extract location information from natural language queries using DSPy",
        total_hits=len(test_queries),
        returned_hits=len([r for r in results if r.has_location]),
        execution_time_ms=execution_time,
        results=results,
        queries=test_queries,
        query_dsl={"demo": "location_extraction", "examples": len(test_queries)},
        es_features=["DSPy location extraction", "Natural language understanding", "City/State parsing"]
    )