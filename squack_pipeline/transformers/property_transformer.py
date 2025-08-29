"""Property transformer for Elasticsearch format compatibility.

This transformer handles Property data from the Gold tier, which already has:
- Nested structures preserved (address, property_details, coordinates)
- Location array created [lon, lat]
- Parking object created
- Price renamed from listing_price

The transformer now performs minimal operations, mainly:
- Converting Decimal types to float for Elasticsearch
- Ensuring arrays are properly formatted
- Handling dates for Elasticsearch format
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from squack_pipeline.utils.logging import PipelineLogger


class PropertyTransformer:
    """Transform Property Gold tier data for Elasticsearch.
    
    Gold tier data already has nested structures preserved, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize property transformer."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def transform(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Gold tier property data to Elasticsearch format.
        
        Gold tier already provides:
        - Nested structures (address, property_details, coordinates)
        - Location array [lon, lat] for geo_point
        - Parking object with spaces and available
        - Price field (renamed from listing_price)
        - Entity type field
        
        This transformer:
        - Converts Decimal types to float
        - Ensures proper date formatting
        - Validates array fields
        - Passes through nested structures unchanged
        
        Args:
            property_data: Property data from Gold tier (DuckDB)
            
        Returns:
            Document ready for Elasticsearch indexing
        """
        # Start with a copy to avoid modifying original
        doc = {}
        
        # Core fields - pass through with type conversion
        doc['listing_id'] = property_data.get('listing_id')
        doc['neighborhood_id'] = property_data.get('neighborhood_id')
        doc['price'] = self._to_float(property_data.get('price'))
        doc['price_per_sqft'] = self._to_float(property_data.get('price_per_sqft'))
        doc['calculated_price_per_sqft'] = self._to_float(property_data.get('calculated_price_per_sqft'))
        doc['days_on_market'] = self._to_int(property_data.get('days_on_market'))
        
        # Pass through nested structures unchanged (already correct from Gold)
        if 'address' in property_data:
            doc['address'] = self._convert_nested_decimals(property_data['address'])
        
        if 'property_details' in property_data:
            doc['property_details'] = self._convert_nested_decimals(property_data['property_details'])
        
        if 'coordinates' in property_data:
            doc['coordinates'] = self._convert_nested_decimals(property_data['coordinates'])
        
        # Denormalized fields from Gold (pass through)
        doc['city'] = property_data.get('city')
        doc['state'] = property_data.get('state')
        doc['bedrooms'] = self._to_int(property_data.get('bedrooms'))
        doc['bathrooms'] = self._to_float(property_data.get('bathrooms'))
        doc['property_type'] = property_data.get('property_type')
        doc['square_feet'] = self._to_int(property_data.get('square_feet'))
        
        # Location array (already created in Gold as [lon, lat])
        if 'location' in property_data:
            doc['location'] = property_data['location']
        
        # Parking object (already created in Gold)
        if 'parking' in property_data:
            doc['parking'] = self._convert_nested_decimals(property_data['parking'])
        
        # Arrays - ensure proper format
        doc['features'] = self._ensure_array(property_data.get('features'))
        doc['images'] = self._ensure_array(property_data.get('images'))
        doc['price_history'] = self._ensure_array(property_data.get('price_history'))
        
        # Text fields
        doc['description'] = property_data.get('description')
        doc['virtual_tour_url'] = property_data.get('virtual_tour_url')
        
        # Dates
        doc['listing_date'] = self._to_datetime(property_data.get('listing_date'))
        
        # Gold tier metadata
        doc['entity_type'] = property_data.get('entity_type', 'property')
        doc['gold_processed_at'] = self._to_datetime(property_data.get('gold_processed_at'))
        doc['processing_version'] = property_data.get('processing_version')
        
        # Handle embeddings if present
        if 'embedding' in property_data and property_data['embedding']:
            doc['embedding'] = property_data['embedding']
            doc['embedding_model'] = property_data.get('embedding_model')
            doc['embedding_dimension'] = self._to_int(property_data.get('embedding_dimension'))
        
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