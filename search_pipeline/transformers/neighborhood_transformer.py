"""Neighborhood DataFrame transformer for search pipeline.

Transforms neighborhood DataFrames from data pipeline to NeighborhoodDocument schema
using Spark-native operations. Handles neighborhood-specific field mappings and
nested object creation for Elasticsearch indexing.
"""

import logging
from datetime import datetime
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, lit, when, struct, array, size, split,
    to_timestamp, regexp_replace, trim, coalesce
)
from pyspark.sql.types import FloatType, IntegerType, TimestampType

from .base_transformer import BaseDataFrameTransformer

logger = logging.getLogger(__name__)


class NeighborhoodDataFrameTransformer(BaseDataFrameTransformer):
    """
    Transforms neighborhood DataFrames to NeighborhoodDocument schema.
    
    Handles the conversion from input neighborhood data structure to the
    target Elasticsearch document schema with proper nested objects
    and field mappings.
    """
    
    def __init__(self):
        """Initialize neighborhood transformer."""
        super().__init__("neighborhood")
    
    def _get_id_field(self) -> str:
        """Get the ID field for neighborhoods."""
        return "neighborhood_id"
    
    def _apply_transformation(self, input_df: DataFrame) -> DataFrame:
        """
        Apply neighborhood-specific transformations.
        
        Args:
            input_df: Input neighborhood DataFrame from data pipeline
            
        Returns:
            Transformed DataFrame with NeighborhoodDocument schema
        """
        self.logger.info("Applying neighborhood transformations")
        
        # Start with core neighborhood fields
        df = self._map_core_neighborhood_fields(input_df)
        
        # Create nested objects
        df = self._create_address_object(df)
        
        # Handle characteristics/scores
        df = self._map_characteristics_and_scores(df)
        
        # Handle description and lifestyle
        df = self._map_description_and_lifestyle(df)
        
        # Preserve enrichment fields if present
        df = self._preserve_enrichment_fields(df)
        
        # Preserve embedding fields if present
        df = self._preserve_embedding_fields(df)
        
        return df
    
    def _map_core_neighborhood_fields(self, df: DataFrame) -> DataFrame:
        """Map core neighborhood fields from input to output schema."""
        return df.select(
            # Primary ID and name
            col("neighborhood_id"),
            col("name"),
            
            # Location fields
            self._safe_column_access(df, "city").alias("city"),
            self._safe_column_access(df, "county").alias("county"), 
            self._safe_column_access(df, "state").alias("state"),
            
            # Description
            self._safe_column_access(df, "description").alias("description"),
            
            # Keep original nested objects for processing
            col("coordinates"),
            col("characteristics"),
            col("amenities"),
            col("lifestyle_tags"),
            col("demographics"),
            col("graph_metadata"),
            
            # Keep all other fields for further processing
            col("*")
        )
    
    def _create_address_object(self, df: DataFrame) -> DataFrame:
        """Create address nested object for neighborhood location."""
        # For neighborhoods, we create address from city/state and coordinates
        address_struct = struct(
            lit(None).alias("street"),  # Neighborhoods don't have street addresses
            self._safe_column_access(df, "city").alias("city"),
            self._safe_column_access(df, "state").alias("state"),
            lit(None).alias("zip_code"),  # Not typically available for neighborhoods
            # Create location array from coordinates [longitude, latitude]
            when(
                (col("coordinates.latitude").isNotNull()) & (col("coordinates.longitude").isNotNull()),
                array(col("coordinates.longitude"), col("coordinates.latitude"))
            ).otherwise(lit(None)).alias("location")
        )
        
        return df.withColumn("address", address_struct)
    
    def _map_characteristics_and_scores(self, df: DataFrame) -> DataFrame:
        """Map characteristics and scores from nested object."""
        # Extract scores from characteristics object with validation (0-100)
        df = df.withColumn("walkability_score",
                          when(col("characteristics.walkability_score").between(0, 100),
                               col("characteristics.walkability_score").cast(IntegerType()))
                          .otherwise(lit(None)))
        
        df = df.withColumn("transit_score", 
                          when(col("characteristics.transit_score").between(0, 100),
                               col("characteristics.transit_score").cast(IntegerType()))
                          .otherwise(lit(None)))
        
        df = df.withColumn("school_rating",
                          when(col("characteristics.school_rating").between(0, 10),
                               col("characteristics.school_rating").cast(FloatType()))
                          .otherwise(lit(None)))
        
        return df
    
    def _map_description_and_lifestyle(self, df: DataFrame) -> DataFrame:
        """Map description and lifestyle fields."""
        # Description is already mapped in core fields
        
        # Handle boundaries (could be GeoJSON string if available)
        df = df.withColumn("boundaries", lit(None))  # Not in current data
        
        return df
    
    def _preserve_enrichment_fields(self, df: DataFrame) -> DataFrame:
        """Preserve enrichment fields if present."""
        # Simplified for demo - just preserve if exist, set null otherwise
        enrichment_fields = [
            "location_context", "neighborhood_context", "nearby_poi",
            "enriched_search_text", "location_scores"
        ]
        
        for field in enrichment_fields:
            if field not in df.columns:
                df = df.withColumn(field, lit(None))
        
        return df
    
    def _preserve_embedding_fields(self, df: DataFrame) -> DataFrame:
        """Preserve embedding fields if present."""
        # Simplified for demo - just preserve if exist, set null otherwise
        embedding_fields = ["embedding", "embedding_model", "embedding_dimension", "embedded_at"]
        
        for field in embedding_fields:
            if field not in df.columns:
                df = df.withColumn(field, lit(None))
        
        return df
    
    def _validate_input(self, df: DataFrame) -> None:
        """Validate neighborhood-specific input requirements."""
        super()._validate_input(df)
        
        # Check for required name field
        if "name" not in df.columns:
            raise ValueError("Required field 'name' not found in neighborhood DataFrame")
        
        # Check for recommended nested structures
        if "coordinates" not in df.columns:
            self.logger.warning("Coordinates object not found in input DataFrame")
        
        if "characteristics" not in df.columns:
            self.logger.warning("Characteristics object not found in input DataFrame")
        
        self.logger.debug("Neighborhood input validation completed")