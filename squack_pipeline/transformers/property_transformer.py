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

from squack_pipeline.transformers.base_embedding_transformer import BaseEmbeddingTransformer
from squack_pipeline.models.transformer_models import (
    TransformedProperty,
    AddressModel,
    PropertyDetailsModel,
    CoordinatesModel,
    ParkingModel
)


class PropertyTransformer(BaseEmbeddingTransformer):
    """Transform Property Gold tier data for Elasticsearch.
    
    Gold tier data already has nested structures preserved, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize property transformer with embedding capabilities."""
        super().__init__()  # Initialize embedding service from parent
    
    def transform(self, property_data: Dict[str, Any]) -> TransformedProperty:
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
            TransformedProperty model ready for Elasticsearch indexing
        """
        # Process address structure - rename 'zip' to 'zip_code' for real_estate_search compatibility
        address_data = None
        if 'address' in property_data and property_data['address']:
            address = self._convert_nested_decimals(property_data['address'])
            # Rename 'zip' to 'zip_code' if present
            if isinstance(address, dict):
                if 'zip' in address:
                    address['zip_code'] = address.pop('zip')
                address_data = AddressModel(**address)
        
        # Process property details
        property_details_data = None
        if 'property_details' in property_data and property_data['property_details']:
            details = self._convert_nested_decimals(property_data['property_details'])
            if isinstance(details, dict):
                property_details_data = PropertyDetailsModel(**details)
        
        # Process coordinates
        coordinates_data = None
        if 'coordinates' in property_data and property_data['coordinates']:
            coords = self._convert_nested_decimals(property_data['coordinates'])
            if isinstance(coords, dict):
                coordinates_data = CoordinatesModel(**coords)
        
        # Process parking
        parking_data = None
        if 'parking' in property_data and property_data['parking']:
            parking = self._convert_nested_decimals(property_data['parking'])
            if isinstance(parking, dict):
                parking_data = ParkingModel(**parking)
        
        # Generate embeddings if service is available
        embedding = None
        embedding_model = None
        embedding_dimension = None
        if self.embedding_service:
            property_text = self._create_property_text(property_data)
            embedding = self.generate_embedding(property_text)
            if embedding:
                embedding_model = self.service_config.model_name if self.service_config else None
                embedding_dimension = len(embedding)
        
        # Create the transformed property model
        transformed = TransformedProperty(
            # Core identifiers
            listing_id=property_data.get('listing_id'),
            neighborhood_id=property_data.get('neighborhood_id'),
            
            # Price fields
            price=self._to_float(property_data.get('price')),
            price_per_sqft=self._to_float(property_data.get('price_per_sqft')),
            calculated_price_per_sqft=self._to_float(property_data.get('calculated_price_per_sqft')),
            days_on_market=self._to_int(property_data.get('days_on_market')),
            
            # Nested structures
            address=address_data,
            property_details=property_details_data,
            coordinates=coordinates_data,
            parking=parking_data,
            
            # Denormalized fields
            city=property_data.get('city'),
            state=property_data.get('state'),
            bedrooms=self._to_int(property_data.get('bedrooms')),
            bathrooms=self._to_float(property_data.get('bathrooms')),
            property_type=property_data.get('property_type'),
            square_feet=self._to_int(property_data.get('square_feet')),
            
            # Location for geo_point
            location=property_data.get('location'),
            
            # Arrays
            features=self._ensure_array(property_data.get('features')),
            images=self._ensure_array(property_data.get('images')),
            price_history=self._ensure_array(property_data.get('price_history')),
            
            # Text fields
            description=property_data.get('description'),
            virtual_tour_url=property_data.get('virtual_tour_url'),
            
            # Dates
            listing_date=self._to_datetime(property_data.get('listing_date')),
            
            # Metadata
            entity_type=property_data.get('entity_type', 'property'),
            gold_processed_at=property_data.get('gold_processed_at'),
            processing_version=property_data.get('processing_version'),
            
            # Embeddings
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension
        )
        
        return transformed
    
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
    
    def _create_property_text(self, property_data: Dict[str, Any]) -> str:
        """Create searchable text from property data for embedding generation.
        
        Combines the most relevant fields into a single text representation
        optimized for semantic search.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            Concatenated text suitable for embedding
        """
        text_parts = []
        
        # Address information
        address = property_data.get('address', {})
        if address:
            street = address.get('street', '')
            city = address.get('city', property_data.get('city', ''))
            state = address.get('state', property_data.get('state', ''))
            if street:
                text_parts.append(f"{street}, {city}, {state}")
            elif city:
                text_parts.append(f"{city}, {state}")
        
        # Property characteristics
        bedrooms = property_data.get('bedrooms')
        bathrooms = property_data.get('bathrooms')
        square_feet = property_data.get('square_feet')
        property_type = property_data.get('property_type')
        
        if bedrooms and bathrooms:
            text_parts.append(f"{bedrooms} bedroom {bathrooms} bathroom")
        
        if property_type:
            text_parts.append(property_type)
        
        if square_feet:
            text_parts.append(f"{square_feet} square feet")
        
        # Price information
        price = property_data.get('price')
        if price:
            text_parts.append(f"${price:,.0f}")
        
        # Description - most important for semantic understanding
        description = property_data.get('description')
        if description:
            text_parts.append(description)
        
        # Features
        features = property_data.get('features')
        if features:
            if isinstance(features, list):
                text_parts.append(" ".join(features))
            elif isinstance(features, str):
                text_parts.append(features)
        
        # Join all parts with spaces
        return " ".join(filter(None, text_parts))