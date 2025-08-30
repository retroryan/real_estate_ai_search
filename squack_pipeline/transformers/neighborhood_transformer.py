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

from squack_pipeline.transformers.base_embedding_transformer import BaseEmbeddingTransformer
from squack_pipeline.models.transformer_models import (
    TransformedNeighborhood,
    CoordinatesModel
)


class NeighborhoodTransformer(BaseEmbeddingTransformer):
    """Transform Neighborhood Gold tier data for Elasticsearch.
    
    Gold tier data already has nested structures preserved, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize neighborhood transformer with embedding capabilities."""
        super().__init__()  # Initialize embedding service from parent
    
    def transform(self, neighborhood_data: Dict[str, Any]) -> TransformedNeighborhood:
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
            TransformedNeighborhood model ready for Elasticsearch indexing
        """
        # Process coordinates
        coordinates_data = None
        if 'coordinates' in neighborhood_data and neighborhood_data['coordinates']:
            coords = self._convert_nested_decimals(neighborhood_data['coordinates'])
            if isinstance(coords, dict):
                coordinates_data = CoordinatesModel(**coords)
        
        # Process nested dictionaries (convert Decimals but keep as dicts)
        characteristics = None
        if 'characteristics' in neighborhood_data:
            characteristics = self._convert_nested_decimals(neighborhood_data['characteristics'])
        
        demographics = None
        if 'demographics' in neighborhood_data:
            demographics = self._convert_nested_decimals(neighborhood_data['demographics'])
        
        wikipedia_correlations = None
        if 'wikipedia_correlations' in neighborhood_data:
            wikipedia_correlations = self._convert_nested_decimals(
                neighborhood_data['wikipedia_correlations']
            )
        
        # Generate embeddings if service is available
        embedding = None
        embedding_model = None
        embedding_dimension = None
        if self.embedding_service:
            neighborhood_text = self._create_neighborhood_text(neighborhood_data)
            embedding = self.generate_embedding(neighborhood_text)
            if embedding:
                embedding_model = self.service_config.model_name if self.service_config else None
                embedding_dimension = len(embedding)
        
        # Create the transformed neighborhood model
        transformed = TransformedNeighborhood(
            # Core identifiers
            neighborhood_id=neighborhood_data.get('neighborhood_id'),
            name=neighborhood_data.get('name'),
            city=neighborhood_data.get('city'),
            county=neighborhood_data.get('county'),
            state=neighborhood_data.get('state'),
            
            # Coordinates
            coordinates=coordinates_data,
            location=neighborhood_data.get('location'),
            
            # Characteristics
            characteristics=characteristics,
            demographics=demographics,
            wikipedia_correlations=wikipedia_correlations,
            
            # Scores
            walkability_score=self._to_int(neighborhood_data.get('walkability_score')),
            transit_score=self._to_int(neighborhood_data.get('transit_score')),
            school_rating=self._to_float(neighborhood_data.get('school_rating')),
            safety_rating=self._to_float(neighborhood_data.get('safety_rating')),
            
            # Statistics
            population=self._to_int(neighborhood_data.get('population')),
            median_household_income=self._to_float(neighborhood_data.get('median_household_income')),
            median_home_price=self._to_float(neighborhood_data.get('median_home_price')),
            
            # Arrays
            amenities=self._ensure_array(neighborhood_data.get('amenities')),
            lifestyle_tags=self._ensure_array(neighborhood_data.get('lifestyle_tags')),
            
            # Text
            description=neighborhood_data.get('description'),
            
            # Metadata
            entity_type=neighborhood_data.get('entity_type', 'neighborhood'),
            gold_processed_at=neighborhood_data.get('gold_processed_at'),
            processing_version=neighborhood_data.get('processing_version'),
            
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
    
    def _create_neighborhood_text(self, neighborhood_data: Dict[str, Any]) -> str:
        """Create searchable text from neighborhood data for embedding generation.
        
        Combines the most relevant fields into a single text representation
        optimized for semantic search.
        
        Args:
            neighborhood_data: Neighborhood data dictionary
            
        Returns:
            Concatenated text suitable for embedding
        """
        text_parts = []
        
        # Name and location
        name = neighborhood_data.get('name')
        city = neighborhood_data.get('city')
        state = neighborhood_data.get('state')
        
        if name:
            text_parts.append(name)
        
        if city and state:
            text_parts.append(f"{city}, {state}")
        
        # Description - most important for semantic understanding
        description = neighborhood_data.get('description')
        if description:
            text_parts.append(description)
        
        # Characteristics
        characteristics = neighborhood_data.get('characteristics')
        if characteristics:
            if isinstance(characteristics, list):
                text_parts.append(" ".join(characteristics))
            elif isinstance(characteristics, str):
                text_parts.append(characteristics)
        
        # Amenities
        amenities = neighborhood_data.get('amenities')
        if amenities:
            if isinstance(amenities, list):
                text_parts.append(" ".join(amenities))
            elif isinstance(amenities, str):
                text_parts.append(amenities)
        
        # Statistics summary (if available)
        stats = neighborhood_data.get('statistics', {})
        if stats:
            median_price = stats.get('median_home_price')
            if median_price:
                text_parts.append(f"median home price ${median_price:,.0f}")
            
            school_rating = stats.get('school_rating')
            if school_rating:
                text_parts.append(f"school rating {school_rating}")
        
        # Join all parts with spaces
        return " ".join(filter(None, text_parts))