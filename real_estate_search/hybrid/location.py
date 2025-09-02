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
    Extract location information from real estate search queries.
    
    Your job is to find cities, states, neighborhoods, and ZIP codes in the text, then create a cleaned query with locations removed.
    
    LOCATION EXTRACTION:
    - Look for city names (e.g., San Francisco, San Jose, Salinas, Oakland)
    - Look for state names or abbreviations (e.g., California, CA, Utah, UT)
    - Look for neighborhood names
    - Look for ZIP codes (5-digit numbers)
    - If ANY location is found, set has_location = true
    - Convert "CA" to "California" for consistency
    
    QUERY CLEANING:
    - Remove all location terms from the original query
    - Keep the property features and descriptions
    - Preserve the natural language structure
    
    EXAMPLES:
    Input: "Modern kitchen in San Francisco"
    → city: "San Francisco", state: "unknown", has_location: true, cleaned_query: "Modern kitchen"
    
    Input: "Family home in Salinas California" 
    → city: "Salinas", state: "California", has_location: true, cleaned_query: "Family home"
    
    Input: "Condo in San Jose CA"
    → city: "San Jose", state: "California", has_location: true, cleaned_query: "Condo"
    
    Input: "Property in Salinas"
    → city: "Salinas", state: "unknown", has_location: true, cleaned_query: "Property"
    
    Input: "Updated kitchen and bathrooms"
    → city: "unknown", state: "unknown", has_location: false, cleaned_query: "Updated kitchen and bathrooms"
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
        
        # Try Predict instead of ChainOfThought for more direct extraction
        self.extract_location = dspy.Predict(LocationExtractionSignature)
        logger.info("Initialized LocationUnderstandingModule with Predict")
    
    def forward(self, query: str) -> LocationIntent:
        """
        Extract location information from a natural language query.
        
        Args:
            query: Natural language search query
            
        Returns:
            LocationIntent with extracted location information
        """
        # Try rule-based extraction first as backup
        rule_based_result = self._rule_based_extraction(query)
        
        try:
            # Execute DSPy prediction
            result = self.extract_location(query_text=query)
            
            # Debug logging
            logger.info(f"DSPy raw result for query '{query}': city='{result.city}', state='{result.state}', has_location='{result.has_location}'")
            
            # Process and clean the extracted values
            city = None if not result.city or result.city.lower() in ['unknown', 'none', ''] else result.city
            state = None if not result.state or result.state.lower() in ['unknown', 'none', ''] else result.state
            neighborhood = None if not result.neighborhood or result.neighborhood.lower() in ['unknown', 'none', ''] else result.neighborhood
            zip_code = None if not result.zip_code or result.zip_code.lower() in ['unknown', 'none', ''] else result.zip_code
            
            # Determine if location was found
            has_location = any([city, state, neighborhood, zip_code])
            
            # Parse confidence score
            try:
                confidence = float(result.confidence)
            except (ValueError, TypeError):
                confidence = 1.0 if has_location else 0.0
            
            # Ensure cleaned_query is never None - fallback to original query
            cleaned_query = result.cleaned_query if result.cleaned_query else query
            
            # If DSPy failed but rule-based found location, use rule-based result
            if not has_location and rule_based_result.has_location:
                logger.info(f"DSPy failed, using rule-based extraction for: {query}")
                return rule_based_result
            
            # Create LocationIntent object
            return LocationIntent(
                city=city,
                state=state,
                neighborhood=neighborhood,
                zip_code=zip_code,
                has_location=has_location,
                cleaned_query=cleaned_query,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"DSPy extraction failed: {e}, falling back to rule-based")
            return rule_based_result
    
    def _rule_based_extraction(self, query: str) -> LocationIntent:
        """
        Minimal rule-based backup - only as last resort, no hardcoded locations.
        
        Args:
            query: Natural language search query
            
        Returns:
            LocationIntent with minimal extraction
        """
        # Very minimal rule-based fallback - just return no location found
        # Let DSPy handle all location extraction
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