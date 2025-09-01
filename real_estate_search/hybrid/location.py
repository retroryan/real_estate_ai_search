"""
Location understanding and filtering for hybrid search.

Uses DSPy for natural language location extraction and provides
Elasticsearch filter building capabilities.
"""

import dspy
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from real_estate_search.config import AppConfig
from .models import LocationIntent

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
        desc="Confidence score between 0 and 1 for the extraction accuracy",
        prefix="Confidence: "
    )


class LocationUnderstandingModule(dspy.Module):
    """
    DSPy module for extracting location information from natural language queries.
    
    Uses ChainOfThought reasoning to identify and extract location components
    from real estate search queries.
    """
    
    def __init__(self):
        """Initialize the location understanding module."""
        super().__init__()
        ensure_dspy_initialized()
        
        # Use ChainOfThought for better reasoning about location extraction
        self.extract_location = dspy.ChainOfThought(LocationExtractionSignature)
        logger.info("Initialized LocationUnderstandingModule with ChainOfThought")
    
    def forward(self, query: str) -> LocationIntent:
        """
        Extract location information from a natural language query.
        
        Args:
            query: Natural language search query
            
        Returns:
            LocationIntent with extracted location information
        """
        try:
            # Execute DSPy prediction
            result = self.extract_location(query_text=query)
            
            # Process and clean the extracted values
            city = None if result.city.lower() in ['unknown', 'none', ''] else result.city
            state = None if result.state.lower() in ['unknown', 'none', ''] else result.state
            neighborhood = None if result.neighborhood.lower() in ['unknown', 'none', ''] else result.neighborhood
            zip_code = None if result.zip_code.lower() in ['unknown', 'none', ''] else result.zip_code
            
            # Determine if location was found
            has_location = any([city, state, neighborhood, zip_code])
            
            # Parse confidence score
            try:
                confidence = float(result.confidence)
            except (ValueError, TypeError):
                confidence = 1.0 if has_location else 0.0
            
            # Create LocationIntent object
            return LocationIntent(
                city=city,
                state=state,
                neighborhood=neighborhood,
                zip_code=zip_code,
                has_location=has_location,
                cleaned_query=result.cleaned_query,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Location extraction failed: {e}")
            # Return query as-is if extraction fails
            return LocationIntent(
                city=None,
                state=None,
                neighborhood=None,
                zip_code=None,
                has_location=False,
                cleaned_query=query,
                confidence=0.0
            )
    
    def __call__(self, query: str) -> LocationIntent:
        """
        Make the module callable following DSPy best practices.
        
        Args:
            query: Natural language search query
            
        Returns:
            LocationIntent with extracted location information
        """
        return self.forward(query)


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
        
        # City filter using address.city field (keyword with lowercase normalizer)
        if location_intent.city:
            filters.append({
                "term": {
                    "address.city": location_intent.city.lower()
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