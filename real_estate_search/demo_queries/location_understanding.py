"""
Location understanding using DSPy for natural language query processing.

This module provides location extraction capabilities using DSPy signatures,
following the proven patterns from the wiki_summary module. It extracts location
intent from natural language queries and converts them to Elasticsearch filters.
"""

import dspy
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from real_estate_search.config import AppConfig

logger = logging.getLogger(__name__)

# Initialize DSPy configuration once at module level
_dspy_initialized = False

def ensure_dspy_initialized():
    """Ensure DSPy is initialized with proper configuration."""
    global _dspy_initialized
    if not _dspy_initialized:
        try:
            config = AppConfig.load()
            config.dspy_config.initialize_dspy()
            _dspy_initialized = True
            logger.info("DSPy initialized successfully for location understanding")
        except Exception as e:
            logger.error(f"Failed to initialize DSPy: {e}")
            raise


class LocationIntent(BaseModel):
    """Extracted location intent from natural language query."""
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state name")
    neighborhood: Optional[str] = Field(None, description="Extracted neighborhood name")
    zip_code: Optional[str] = Field(None, description="Extracted ZIP code")
    has_location: bool = Field(False, description="Whether location was found in query")
    cleaned_query: str = Field(..., description="Query with location terms removed")
    confidence: float = Field(0.0, description="Confidence score for extraction")


class LocationExtractionSignature(dspy.Signature):
    """
    Extract location information from natural language real estate queries.
    
    Analyze the provided query to identify location references including city, state,
    neighborhood, or ZIP code. Extract these elements and provide a cleaned version
    of the query with location terms removed for better property feature matching.
    
    Focus on identifying:
    1. City names (e.g., "in San Francisco", "Park City homes")
    2. State names (e.g., "California properties", "Utah real estate")
    3. Neighborhood names (e.g., "Mission District", "Castro area")
    4. ZIP codes (e.g., "94102", "84060")
    
    Provide high confidence only when location is clearly mentioned.
    """
    
    # Input field
    query_text: str = dspy.InputField(
        desc="Natural language real estate search query to analyze for location information"
    )
    
    # Output fields
    city: str = dspy.OutputField(
        desc="Extracted city name, or 'unknown' if not clearly identified",
        prefix="City: "
    )
    
    state: str = dspy.OutputField(
        desc="Extracted state name, or 'unknown' if not clearly identified",
        prefix="State: "
    )
    
    neighborhood: str = dspy.OutputField(
        desc="Extracted neighborhood name, or 'unknown' if not clearly identified",
        prefix="Neighborhood: "
    )
    
    zip_code: str = dspy.OutputField(
        desc="Extracted ZIP code, or 'unknown' if not clearly identified",
        prefix="ZIP Code: "
    )
    
    has_location: bool = dspy.OutputField(
        desc="True if any location information was found in the query",
        prefix="Has Location: "
    )
    
    cleaned_query: str = dspy.OutputField(
        desc="Original query with location terms removed, focusing on property features",
        prefix="Cleaned Query: "
    )
    
    confidence: float = dspy.OutputField(
        desc="Confidence score from 0.0 to 1.0 for the location extraction accuracy",
        prefix="Confidence: "
    )


class LocationUnderstandingModule(dspy.Module):
    """
    DSPy module for understanding location intent in real estate queries.
    
    Uses ChainOfThought for better reasoning following DSPy best practices.
    Extracts location information and provides cleaned queries for property search.
    """
    
    def __init__(self):
        """Initialize the location understanding module with ChainOfThought."""
        super().__init__()
        # Ensure DSPy is initialized with proper configuration
        ensure_dspy_initialized()
        # Always use ChainOfThought for better reasoning per DSPy best practices
        self.extract = dspy.ChainOfThought(LocationExtractionSignature)
        logger.info("Initialized LocationUnderstandingModule with ChainOfThought")
    
    def forward(self, query: str) -> LocationIntent:
        """
        Extract location intent from natural language query.
        
        Following DSPy best practices:
        - Forward method accepts simple arguments
        - Module should be called as callable: module(query)
        - Returns Pydantic model for structured output
        - Handles errors gracefully with fallback
        
        Args:
            query: Natural language search query
            
        Returns:
            LocationIntent with extracted information
        """
        logger.debug(f"Extracting location intent from: '{query}'")
        
        try:
            # Call DSPy module (synchronous by default)
            result = self.extract(query_text=query)
            
            # Convert DSPy result to Pydantic model
            location_intent = self._parse_result(result, original_query=query)
            
            logger.debug(f"Extracted location intent: city={location_intent.city}, "
                        f"state={location_intent.state}, confidence={location_intent.confidence}")
            
            return location_intent
            
        except Exception as e:
            logger.error(f"Location extraction failed for query '{query}': {e}")
            # Return default intent with original query (graceful degradation)
            return LocationIntent(
                cleaned_query=query,
                has_location=False,
                confidence=0.0
            )
    
    def _parse_result(self, result: dspy.Prediction, original_query: str) -> LocationIntent:
        """
        Parse DSPy result into LocationIntent Pydantic model.
        
        Follows DSPy best practices:
        - Clean parsing without isinstance checks
        - Direct field access with getattr
        - Proper validation through Pydantic
        
        Args:
            result: DSPy prediction result
            original_query: Original query text for fallback
            
        Returns:
            Validated LocationIntent object
        """
        # Parse location fields, converting 'unknown' to None
        def parse_field(field_name: str) -> Optional[str]:
            value = getattr(result, field_name, None)
            return None if value == 'unknown' else value
        
        city = parse_field('city')
        state = parse_field('state')
        neighborhood = parse_field('neighborhood')
        zip_code = parse_field('zip_code')
        
        # Parse boolean and float fields with defaults
        has_location = bool(getattr(result, 'has_location', False))
        cleaned_query = getattr(result, 'cleaned_query', original_query) or original_query
        
        # Parse and validate confidence score
        confidence = getattr(result, 'confidence', 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        
        # Ensure consistency: if no location fields, set has_location to False
        if not any([city, state, neighborhood, zip_code]):
            has_location = False
            confidence = 0.0
        
        return LocationIntent(
            city=city,
            state=state,
            neighborhood=neighborhood,
            zip_code=zip_code,
            has_location=has_location,
            cleaned_query=cleaned_query,
            confidence=confidence
        )


class LocationFilterBuilder:
    """
    Builds Elasticsearch filters from extracted location intent.
    
    Converts LocationIntent objects into Elasticsearch query filters
    using only existing property index fields.
    """
    
    def build_filters(self, location_intent: LocationIntent) -> List[Dict[str, Any]]:
        """
        Build Elasticsearch filters from location intent.
        
        Args:
            location_intent: Extracted location information
            
        Returns:
            List of Elasticsearch filter clauses
        """
        if not location_intent.has_location:
            return []
        
        filters = []
        
        # City filter using address.city field
        if location_intent.city:
            filters.append({
                "term": {
                    "address.city.keyword": location_intent.city
                }
            })
            logger.debug(f"Added city filter: {location_intent.city}")
        
        # State filter using address.state field
        if location_intent.state:
            filters.append({
                "term": {
                    "address.state": location_intent.state
                }
            })
            logger.debug(f"Added state filter: {location_intent.state}")
        
        # Neighborhood filter using neighborhood.name field
        if location_intent.neighborhood:
            filters.append({
                "term": {
                    "neighborhood.name.keyword": location_intent.neighborhood
                }
            })
            logger.debug(f"Added neighborhood filter: {location_intent.neighborhood}")
        
        # ZIP code filter using address.zip_code field
        if location_intent.zip_code:
            filters.append({
                "term": {
                    "address.zip_code": location_intent.zip_code
                }
            })
            logger.debug(f"Added ZIP code filter: {location_intent.zip_code}")
        
        return filters


def demo_location_understanding(query: str = "Find a great family home in Park City") -> LocationIntent:
    """
    Demo: Extract location information from natural language queries.
    
    Demonstrates DSPy-based location understanding for real estate queries,
    extracting city, state, neighborhood, and ZIP code information.
    
    Following DSPy best practices:
    - Module called as callable (not calling forward() directly)
    - Synchronous execution (no async)
    - Returns Pydantic model for structured output
    
    Args:
        query: Natural language query to process
        
    Returns:
        LocationIntent with extracted information
    """
    logger.info(f"Running location understanding demo for query: '{query}'")
    
    # Initialize location understanding module
    module = LocationUnderstandingModule()
    
    # Extract location intent using module as callable (DSPy best practice)
    try:
        # Call module as callable, not forward() directly
        result = module(query)
        
        logger.info(f"Location extraction results:")
        logger.info(f"  City: {result.city}")
        logger.info(f"  State: {result.state}")
        logger.info(f"  Neighborhood: {result.neighborhood}")
        logger.info(f"  ZIP Code: {result.zip_code}")
        logger.info(f"  Has Location: {result.has_location}")
        logger.info(f"  Cleaned Query: '{result.cleaned_query}'")
        logger.info(f"  Confidence: {result.confidence}")
        
        return result
        
    except Exception as e:
        logger.error(f"Location understanding demo failed: {e}")
        raise