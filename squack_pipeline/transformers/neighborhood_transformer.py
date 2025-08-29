"""Neighborhood transformer for Elasticsearch format compatibility.

This transformer handles Neighborhood data from the Gold tier, which already has:
- Nested structures preserved (coordinates, characteristics, demographics)
- Location array created [lon, lat]
- Wikipedia correlations preserved
- All denormalized fields added

The transformer now performs minimal operations, mainly:
- Converting Decimal types to float for Elasticsearch
- Ensuring arrays are properly formatted
- Passing through nested structures unchanged
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional

from squack_pipeline.utils.logging import PipelineLogger


class NeighborhoodTransformer:
    """Transform Neighborhood Gold tier data for Elasticsearch.
    
    Gold tier data already has nested structures preserved, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize neighborhood transformer."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def transform(self, neighborhood_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Gold tier neighborhood data to Elasticsearch format.
        
        Gold tier already provides:
        - Nested structures (coordinates, characteristics, demographics)
        - Location array [lon, lat] for geo_point
        - Wikipedia correlations structure
        - Denormalized fields for queries
        - Entity type field
        
        This transformer:
        - Converts Decimal types to float
        - Ensures arrays are properly formatted
        - Passes through nested structures unchanged
        
        Args:
            neighborhood_data: Neighborhood data from Gold tier (DuckDB)
            
        Returns:
            Document ready for Elasticsearch indexing
        """
        # Start with a copy to avoid modifying original
        doc = {}
        
        # Core fields
        doc['neighborhood_id'] = neighborhood_data.get('neighborhood_id')
        doc['name'] = neighborhood_data.get('name')
        doc['city'] = neighborhood_data.get('city')
        doc['county'] = neighborhood_data.get('county')
        doc['state'] = neighborhood_data.get('state')
        
        # Pass through nested structures unchanged (already correct from Gold)
        if 'coordinates' in neighborhood_data:
            doc['coordinates'] = self._convert_nested_decimals(neighborhood_data['coordinates'])
        
        if 'characteristics' in neighborhood_data:
            doc['characteristics'] = self._convert_nested_decimals(neighborhood_data['characteristics'])
        
        if 'demographics' in neighborhood_data:
            doc['demographics'] = self._convert_nested_decimals(neighborhood_data['demographics'])
        
        if 'wikipedia_correlations' in neighborhood_data:
            doc['wikipedia_correlations'] = self._convert_nested_decimals(
                neighborhood_data['wikipedia_correlations']
            )
        
        # Denormalized fields from Gold (pass through with type conversion)
        doc['walkability_score'] = self._to_int(neighborhood_data.get('walkability_score'))
        doc['transit_score'] = self._to_int(neighborhood_data.get('transit_score'))
        doc['school_rating'] = self._to_float(neighborhood_data.get('school_rating'))
        doc['safety_rating'] = self._to_float(neighborhood_data.get('safety_rating'))
        doc['population'] = self._to_int(neighborhood_data.get('population'))
        doc['median_household_income'] = self._to_float(neighborhood_data.get('median_household_income'))
        
        # Location array (already created in Gold as [lon, lat])
        if 'location' in neighborhood_data:
            doc['location'] = neighborhood_data['location']
        
        # Arrays - ensure proper format
        doc['amenities'] = self._ensure_array(neighborhood_data.get('amenities'))
        doc['lifestyle_tags'] = self._ensure_array(neighborhood_data.get('lifestyle_tags'))
        
        # Other fields
        doc['median_home_price'] = self._to_float(neighborhood_data.get('median_home_price'))
        doc['price_trend'] = self._to_float(neighborhood_data.get('price_trend'))
        doc['description'] = neighborhood_data.get('description')
        
        # Gold tier metadata
        doc['entity_type'] = neighborhood_data.get('entity_type', 'neighborhood')
        doc['gold_processed_at'] = self._to_datetime(neighborhood_data.get('gold_processed_at'))
        doc['processing_version'] = neighborhood_data.get('processing_version')
        
        # Handle embeddings if present
        if 'embedding' in neighborhood_data and neighborhood_data['embedding']:
            doc['embedding'] = neighborhood_data['embedding']
            doc['embedding_model'] = neighborhood_data.get('embedding_model')
            doc['embedding_dimension'] = self._to_int(neighborhood_data.get('embedding_dimension'))
        
        # Remove None values for cleaner Elasticsearch documents
        doc = {k: v for k, v in doc.items() if v is not None}
        
        return doc
    
    def _convert_nested_decimals(self, obj: Any) -> Any:
        """
        Recursively convert Decimal types in nested structures.
        
        Args:
            obj: Object to convert (dict, list, or value)
            
        Returns:
            Object with Decimals converted to float
        """
        if isinstance(obj, dict):
            return {k: self._convert_nested_decimals(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._convert_nested_decimals(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj
    
    def _ensure_array(self, value: Any) -> List[Any]:
        """
        Ensure value is an array.
        
        Args:
            value: Value to convert to array
            
        Returns:
            Array representation of value
        """
        if value is None:
            return []
        if isinstance(value, list):
            # Convert any Decimals in the list
            return [self._convert_nested_decimals(item) for item in value]
        if isinstance(value, str):
            # Handle comma-separated strings
            if ',' in value:
                return [item.strip() for item in value.split(',')]
            return [value]
        return []
    
    def _to_float(self, value: Any) -> Optional[float]:
        """
        Convert value to float, handling Decimal types.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _to_int(self, value: Any) -> Optional[int]:
        """
        Convert value to integer.
        
        Args:
            value: Value to convert
            
        Returns:
            Integer value or None
        """
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _to_datetime(self, value: Any) -> Optional[str]:
        """
        Convert value to ISO datetime string for Elasticsearch.
        
        Args:
            value: Value to convert
            
        Returns:
            ISO datetime string or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            # Return as-is if already a string (Gold tier timestamps)
            return value
        return None