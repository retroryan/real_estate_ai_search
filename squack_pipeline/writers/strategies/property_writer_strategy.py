"""Property-specific writer strategy."""

from typing import Dict, Any, Optional
import pandas as pd

from squack_pipeline.writers.strategies.base_writer_strategy import (
    BaseWriterStrategy, WriterConfig
)
from squack_pipeline.models import EntityType
from squack_pipeline.config.entity_config import EntityConfig


class PropertyWriterStrategy(BaseWriterStrategy):
    """Writer strategy for property entities.
    
    Handles property-specific transformations including:
    - Flattening nested address and property_details structures
    - Converting coordinates to appropriate formats
    - Mapping field names for different output systems
    - Preparing data for Elasticsearch indexing
    """
    
    def __init__(self, config: Optional[WriterConfig] = None):
        """Initialize property writer strategy.
        
        Args:
            config: Optional writer configuration
        """
        if config is None:
            config = WriterConfig(
                entity_type=EntityType.PROPERTY,
                flatten_nested=True,
                include_metadata=True
            )
        super().__init__(config)
    
    def prepare_for_output(
        self,
        data: pd.DataFrame,
        entity_config: Optional[EntityConfig] = None
    ) -> pd.DataFrame:
        """Prepare property data for output format.
        
        Args:
            data: Property DataFrame to prepare
            entity_config: Optional entity-specific configuration
            
        Returns:
            Prepared DataFrame
        """
        # Make a copy to avoid modifying original
        prepared = data.copy()
        
        # Handle format-specific transformations
        if self.config.output_format == "elasticsearch":
            prepared = self._prepare_for_elasticsearch(prepared)
        elif self.config.output_format == "csv":
            prepared = self._prepare_for_csv(prepared)
        elif self.config.output_format == "parquet":
            prepared = self._prepare_for_parquet(prepared)
        
        # Apply common transformations
        if self.config.flatten_nested:
            prepared = self.flatten_nested_structures(prepared)
        
        # Apply field mappings
        prepared = self.apply_field_mappings(prepared)
        
        # Exclude unwanted fields
        prepared = self.exclude_fields(prepared)
        
        # Add metadata
        if self.config.include_metadata:
            prepared = self.add_metadata(prepared)
        
        # Validate
        if not self.validate_output(prepared):
            self.logger.warning("Output validation failed")
        
        return prepared
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single property record for output.
        
        Args:
            record: Property record to transform
            
        Returns:
            Transformed record
        """
        transformed = record.copy()
        
        # Handle nested address structure
        if "address" in transformed and isinstance(transformed["address"], dict):
            address = transformed.pop("address")
            transformed["street"] = address.get("street")
            transformed["city"] = address.get("city")
            transformed["state"] = address.get("state")
            transformed["zip"] = address.get("zip")
        
        # Handle nested property_details structure
        if "property_details" in transformed and isinstance(transformed["property_details"], dict):
            details = transformed.pop("property_details")
            transformed["property_type"] = details.get("property_type")
            transformed["bedrooms"] = details.get("bedrooms")
            transformed["bathrooms"] = details.get("bathrooms")
            transformed["square_feet"] = details.get("square_feet")
            transformed["year_built"] = details.get("year_built")
            transformed["lot_size"] = details.get("lot_size")
        
        # Handle coordinates
        if "coordinates" in transformed and isinstance(transformed["coordinates"], dict):
            coords = transformed.pop("coordinates")
            transformed["latitude"] = coords.get("latitude")
            transformed["longitude"] = coords.get("longitude")
            
            # Create location array for Elasticsearch
            if self.config.output_format == "elasticsearch":
                if coords.get("latitude") and coords.get("longitude"):
                    transformed["location"] = [coords["longitude"], coords["latitude"]]
        
        # Handle parking structure
        if "parking" in transformed and isinstance(transformed["parking"], dict):
            parking = transformed.pop("parking")
            transformed["parking_spaces"] = parking.get("spaces")
            transformed["parking_available"] = parking.get("available")
        
        # Handle arrays
        for field in ["features", "amenities"]:
            if field in transformed and isinstance(transformed[field], list):
                if self.config.output_format == "csv":
                    # Convert to comma-separated string for CSV
                    transformed[field] = ", ".join(transformed[field])
                # Keep as array for other formats
        
        # Apply field mappings
        mappings = self.get_field_mappings()
        for old_name, new_name in mappings.items():
            if old_name in transformed:
                transformed[new_name] = transformed.pop(old_name)
        
        return transformed
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get property-specific field name mappings.
        
        Returns:
            Dictionary of source field to output field mappings
        """
        # Default mappings for property entities
        base_mappings = {
            "listing_id": "id",
            "price_per_sqft": "price_per_square_foot",
            "days_on_market": "dom",
            "listing_date": "listed_date"
        }
        
        # Add format-specific mappings
        if self.config.output_format == "elasticsearch":
            base_mappings.update({
                "listing_id": "_id",  # Use as document ID
                "description": "description_text",
                "amenities": "amenities_list"
            })
        
        return base_mappings
    
    def _prepare_for_elasticsearch(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare property data for Elasticsearch indexing.
        
        Args:
            data: Property DataFrame
            
        Returns:
            DataFrame prepared for Elasticsearch
        """
        # Handle location field for geo queries
        if "coordinates" in data.columns:
            def create_location(row):
                if pd.notna(row.get("coordinates")):
                    coords = row["coordinates"]
                    if isinstance(coords, dict):
                        lat = coords.get("latitude")
                        lon = coords.get("longitude")
                        if lat and lon:
                            return [lon, lat]  # Elasticsearch expects [lon, lat]
                return None
            
            data["location"] = data.apply(create_location, axis=1)
        
        # Ensure proper data types
        numeric_fields = ["price", "square_feet", "bedrooms", "bathrooms", "year_built"]
        for field in numeric_fields:
            if field in data.columns:
                data[field] = pd.to_numeric(data[field], errors='coerce')
        
        # Handle date fields
        date_fields = ["listing_date", "last_updated"]
        for field in date_fields:
            if field in data.columns:
                data[field] = pd.to_datetime(data[field], errors='coerce')
        
        return data
    
    def _prepare_for_csv(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare property data for CSV export.
        
        Args:
            data: Property DataFrame
            
        Returns:
            DataFrame prepared for CSV
        """
        # Flatten all nested structures
        self.config.flatten_nested = True
        
        # Convert all list/array fields to strings
        for col in data.columns:
            if data[col].dtype == 'object':
                data[col] = data[col].apply(
                    lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x
                )
        
        return data
    
    def _prepare_for_parquet(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare property data for Parquet export.
        
        Args:
            data: Property DataFrame
            
        Returns:
            DataFrame prepared for Parquet
        """
        # Parquet handles nested structures well, minimal transformation needed
        
        # Ensure consistent data types
        if "price" in data.columns:
            data["price"] = data["price"].astype('float64', errors='ignore')
        
        if "listing_date" in data.columns:
            data["listing_date"] = pd.to_datetime(data["listing_date"], errors='coerce')
        
        return data
    
    def get_elasticsearch_mapping(self) -> Dict[str, Any]:
        """Get Elasticsearch mapping for property entities.
        
        Returns:
            Elasticsearch mapping configuration
        """
        return {
            "properties": {
                "listing_id": {"type": "keyword"},
                "price": {"type": "float"},
                "price_per_square_foot": {"type": "float"},
                "street": {"type": "text"},
                "city": {"type": "keyword"},
                "state": {"type": "keyword"},
                "zip": {"type": "keyword"},
                "property_type": {"type": "keyword"},
                "bedrooms": {"type": "integer"},
                "bathrooms": {"type": "float"},
                "square_feet": {"type": "integer"},
                "year_built": {"type": "integer"},
                "lot_size": {"type": "float"},
                "description": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "features": {"type": "keyword"},
                "amenities_list": {"type": "keyword"},
                "location": {"type": "geo_point"},
                "latitude": {"type": "float"},
                "longitude": {"type": "float"},
                "neighborhood_id": {"type": "keyword"},
                "neighborhood_name": {"type": "keyword"},
                "dom": {"type": "integer"},
                "listed_date": {"type": "date"},
                "last_updated": {"type": "date"},
                "_entity_type": {"type": "keyword"},
                "_processed_at": {"type": "long"}
            }
        }