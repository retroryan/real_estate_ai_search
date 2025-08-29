"""Neighborhood-specific writer strategy."""

from typing import Dict, Any, Optional
import pandas as pd

from squack_pipeline.writers.strategies.base_writer_strategy import (
    BaseWriterStrategy, WriterConfig
)
from squack_pipeline.models import EntityType
from squack_pipeline.config.entity_config import EntityConfig


class NeighborhoodWriterStrategy(BaseWriterStrategy):
    """Writer strategy for neighborhood entities.
    
    Handles neighborhood-specific transformations including:
    - Flattening demographics and statistics structures
    - Processing school data arrays
    - Converting boundaries for geo queries
    - Mapping field names for different output systems
    """
    
    def __init__(self, config: Optional[WriterConfig] = None):
        """Initialize neighborhood writer strategy.
        
        Args:
            config: Optional writer configuration
        """
        if config is None:
            config = WriterConfig(
                entity_type=EntityType.NEIGHBORHOOD,
                flatten_nested=True,
                include_metadata=True
            )
        super().__init__(config)
    
    def prepare_for_output(
        self,
        data: pd.DataFrame,
        entity_config: Optional[EntityConfig] = None
    ) -> pd.DataFrame:
        """Prepare neighborhood data for output format.
        
        Args:
            data: Neighborhood DataFrame to prepare
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
        """Transform a single neighborhood record for output.
        
        Args:
            record: Neighborhood record to transform
            
        Returns:
            Transformed record
        """
        transformed = record.copy()
        
        # Handle nested demographics structure
        if "demographics" in transformed and isinstance(transformed["demographics"], dict):
            demo = transformed.pop("demographics")
            transformed["population"] = demo.get("population")
            transformed["median_age"] = demo.get("median_age")
            transformed["median_income"] = demo.get("median_income")
            transformed["households"] = demo.get("households")
            transformed["education_level"] = demo.get("education_level")
            transformed["employment_rate"] = demo.get("employment_rate")
        
        # Handle nested statistics structure
        if "statistics" in transformed and isinstance(transformed["statistics"], dict):
            stats = transformed.pop("statistics")
            transformed["avg_home_value"] = stats.get("avg_home_value")
            transformed["avg_rent"] = stats.get("avg_rent")
            transformed["crime_rate"] = stats.get("crime_rate")
            transformed["walkability_score"] = stats.get("walkability_score")
            transformed["transit_score"] = stats.get("transit_score")
            transformed["bike_score"] = stats.get("bike_score")
        
        # Handle coordinates
        if "coordinates" in transformed and isinstance(transformed["coordinates"], dict):
            coords = transformed.pop("coordinates")
            transformed["center_latitude"] = coords.get("latitude")
            transformed["center_longitude"] = coords.get("longitude")
            
            # Create location for Elasticsearch
            if self.config.output_format == "elasticsearch":
                if coords.get("latitude") and coords.get("longitude"):
                    transformed["center_location"] = [coords["longitude"], coords["latitude"]]
        
        # Handle schools array
        if "schools" in transformed and isinstance(transformed["schools"], list):
            if self.config.output_format == "csv":
                # Extract school names for CSV
                school_names = [s.get("name", "") for s in transformed["schools"] if isinstance(s, dict)]
                transformed["school_names"] = ", ".join(school_names)
                transformed["school_count"] = len(transformed["schools"])
                del transformed["schools"]
            elif self.config.output_format == "elasticsearch":
                # Keep structured for Elasticsearch
                transformed["schools"] = [
                    {
                        "name": s.get("name"),
                        "type": s.get("type"),
                        "rating": s.get("rating"),
                        "distance": s.get("distance")
                    }
                    for s in transformed["schools"]
                    if isinstance(s, dict)
                ]
        
        # Handle arrays
        for field in ["characteristics", "amenities", "zip_codes"]:
            if field in transformed and isinstance(transformed[field], list):
                if self.config.output_format == "csv":
                    # Convert to comma-separated string for CSV
                    transformed[field] = ", ".join(map(str, transformed[field]))
                # Keep as array for other formats
        
        # Handle boundaries (GeoJSON or polygon data)
        if "boundaries" in transformed:
            if self.config.output_format == "csv":
                # Remove complex boundary data for CSV
                del transformed["boundaries"]
            elif self.config.output_format == "elasticsearch":
                # Ensure proper GeoJSON format for Elasticsearch
                if isinstance(transformed["boundaries"], dict):
                    # Validate it's a proper GeoJSON
                    if "type" not in transformed["boundaries"]:
                        del transformed["boundaries"]
        
        # Apply field mappings
        mappings = self.get_field_mappings()
        for old_name, new_name in mappings.items():
            if old_name in transformed:
                transformed[new_name] = transformed.pop(old_name)
        
        return transformed
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get neighborhood-specific field name mappings.
        
        Returns:
            Dictionary of source field to output field mappings
        """
        # Default mappings for neighborhood entities
        base_mappings = {
            "neighborhood_id": "id",
            "avg_home_value": "average_home_value",
            "avg_rent": "average_rent"
        }
        
        # Add format-specific mappings
        if self.config.output_format == "elasticsearch":
            base_mappings.update({
                "neighborhood_id": "_id",  # Use as document ID
                "description": "description_text",
                "characteristics": "characteristics_list"
            })
        
        return base_mappings
    
    def _prepare_for_elasticsearch(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare neighborhood data for Elasticsearch indexing.
        
        Args:
            data: Neighborhood DataFrame
            
        Returns:
            DataFrame prepared for Elasticsearch
        """
        # Handle center location for geo queries
        if "coordinates" in data.columns:
            def create_center_location(row):
                if pd.notna(row.get("coordinates")):
                    coords = row["coordinates"]
                    if isinstance(coords, dict):
                        lat = coords.get("latitude")
                        lon = coords.get("longitude")
                        if lat and lon:
                            return [lon, lat]  # Elasticsearch expects [lon, lat]
                return None
            
            data["center_location"] = data.apply(create_center_location, axis=1)
        
        # Ensure proper data types
        numeric_fields = [
            "population", "median_age", "median_income", "households",
            "avg_home_value", "avg_rent", "crime_rate",
            "walkability_score", "transit_score", "bike_score"
        ]
        for field in numeric_fields:
            if field in data.columns:
                data[field] = pd.to_numeric(data[field], errors='coerce')
        
        return data
    
    def _prepare_for_csv(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare neighborhood data for CSV export.
        
        Args:
            data: Neighborhood DataFrame
            
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
        
        # Remove complex fields not suitable for CSV
        complex_fields = ["boundaries", "schools", "wikipedia_articles"]
        for field in complex_fields:
            if field in data.columns:
                if field == "schools":
                    # Extract count before removing
                    data["school_count"] = data[field].apply(
                        lambda x: len(x) if isinstance(x, list) else 0
                    )
                data = data.drop(columns=[field])
        
        return data
    
    def _prepare_for_parquet(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare neighborhood data for Parquet export.
        
        Args:
            data: Neighborhood DataFrame
            
        Returns:
            DataFrame prepared for Parquet
        """
        # Parquet handles nested structures well
        
        # Ensure consistent data types for numeric fields
        numeric_fields = ["population", "median_income", "avg_home_value", "avg_rent"]
        for field in numeric_fields:
            if field in data.columns:
                data[field] = data[field].astype('float64', errors='ignore')
        
        return data
    
    def get_elasticsearch_mapping(self) -> Dict[str, Any]:
        """Get Elasticsearch mapping for neighborhood entities.
        
        Returns:
            Elasticsearch mapping configuration
        """
        return {
            "properties": {
                "neighborhood_id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "city": {"type": "keyword"},
                "state": {"type": "keyword"},
                "county": {"type": "keyword"},
                "zip_codes": {"type": "keyword"},
                "description_text": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "characteristics_list": {"type": "keyword"},
                "amenities": {"type": "keyword"},
                "population": {"type": "integer"},
                "median_age": {"type": "float"},
                "median_income": {"type": "float"},
                "households": {"type": "integer"},
                "education_level": {"type": "keyword"},
                "employment_rate": {"type": "float"},
                "average_home_value": {"type": "float"},
                "average_rent": {"type": "float"},
                "crime_rate": {"type": "float"},
                "walkability_score": {"type": "integer"},
                "transit_score": {"type": "integer"},
                "bike_score": {"type": "integer"},
                "center_location": {"type": "geo_point"},
                "center_latitude": {"type": "float"},
                "center_longitude": {"type": "float"},
                "boundaries": {"type": "geo_shape"},
                "schools": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text"},
                        "type": {"type": "keyword"},
                        "rating": {"type": "float"},
                        "distance": {"type": "float"}
                    }
                },
                "property_count": {"type": "integer"},
                "_entity_type": {"type": "keyword"},
                "_processed_at": {"type": "long"}
            }
        }