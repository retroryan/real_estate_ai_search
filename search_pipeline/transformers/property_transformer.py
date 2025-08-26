"""Property DataFrame transformer for search pipeline.

Transforms property DataFrames from data pipeline to PropertyDocument schema
using Spark-native operations. Handles property-specific field mappings and
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


class PropertyDataFrameTransformer(BaseDataFrameTransformer):
    """
    Transforms property DataFrames to PropertyDocument schema.
    
    Handles the conversion from input property data structure to the
    target Elasticsearch document schema with proper nested objects
    and field mappings.
    """
    
    def __init__(self):
        """Initialize property transformer."""
        super().__init__("property")
    
    def _get_id_field(self) -> str:
        """Get the ID field for properties."""
        return "listing_id"
    
    def _apply_transformation(self, input_df: DataFrame) -> DataFrame:
        """
        Apply property-specific transformations.
        
        Args:
            input_df: Input property DataFrame from data pipeline
            
        Returns:
            Transformed DataFrame with PropertyDocument schema
        """
        self.logger.info("Applying property transformations")
        
        # Start with core property fields
        df = self._map_core_property_fields(input_df)
        
        # Create nested objects
        df = self._create_address_object(df)
        df = self._create_neighborhood_object(df)
        df = self._create_parking_object(df)
        
        # Handle financial fields
        df = self._map_financial_fields(df)
        
        # Handle status and dates
        df = self._map_status_and_dates(df)
        
        # Handle features and amenities arrays
        df = self._map_features_and_amenities(df)
        
        # Handle media fields
        df = self._map_media_fields(df)
        
        # Preserve enrichment fields if present
        df = self._preserve_enrichment_fields(df)
        
        # Preserve embedding fields if present
        df = self._preserve_embedding_fields(df)
        
        return df
    
    def _map_core_property_fields(self, df: DataFrame) -> DataFrame:
        """Map core property fields from input to output schema."""
        return df.select(
            # Primary ID
            col("listing_id"),
            
            # Property type and basic info
            self._safe_column_access(df, "property_details.property_type").alias("property_type"),
            self._safe_column_access(df, "listing_price").cast(FloatType()).alias("price"),
            self._safe_column_access(df, "property_details.bedrooms").cast(IntegerType()).alias("bedrooms"),
            self._safe_column_access(df, "property_details.bathrooms").cast(FloatType()).alias("bathrooms"),
            self._safe_column_access(df, "property_details.square_feet").cast(IntegerType()).alias("square_feet"),
            self._safe_column_access(df, "property_details.year_built").cast(IntegerType()).alias("year_built"),
            
            # Convert lot_size from acres to square feet (1 acre = 43,560 sq ft)
            when(
                col("property_details.lot_size").isNotNull(),
                (col("property_details.lot_size") * 43560).cast(IntegerType())
            ).otherwise(lit(None)).alias("lot_size"),
            
            # Description and neighborhood
            self._safe_column_access(df, "description").alias("description"),
            self._safe_column_access(df, "neighborhood_id").alias("neighborhood_id"),
            
            # Keep original nested objects for processing
            col("address"),
            col("coordinates"),
            col("property_details"),
            col("features"),
            col("images"),
            
            # Keep other fields for further processing
            col("*")
        )
    
    def _create_address_object(self, df: DataFrame) -> DataFrame:
        """Create address nested object."""
        address_struct = struct(
            self._safe_column_access(df, "address.street").alias("street"),
            self._safe_column_access(df, "address.city").alias("city"),
            self._safe_column_access(df, "address.state").alias("state"),
            self._safe_column_access(df, "address.zip").alias("zip_code"),
            # Create location array from coordinates [longitude, latitude]
            when(
                (col("coordinates.latitude").isNotNull()) & (col("coordinates.longitude").isNotNull()),
                array(col("coordinates.longitude"), col("coordinates.latitude"))
            ).otherwise(lit(None)).alias("location")
        )
        
        return df.withColumn("address", address_struct)
    
    def _create_neighborhood_object(self, df: DataFrame) -> DataFrame:
        """Create neighborhood nested object if data available."""
        # Basic neighborhood object with ID and name
        # Additional fields like walkability_score will come from enrichment
        neighborhood_struct = struct(
            self._safe_column_access(df, "neighborhood_id").alias("id"),
            lit(None).alias("name"),  # Will be enriched later
            lit(None).alias("walkability_score"),
            lit(None).alias("school_rating")
        )
        
        return df.withColumn("neighborhood", neighborhood_struct)
    
    def _create_parking_object(self, df: DataFrame) -> DataFrame:
        """Create parking nested object."""
        parking_struct = struct(
            self._safe_column_access(df, "property_details.garage_spaces").cast(IntegerType()).alias("spaces"),
            when(
                col("property_details.garage_spaces").isNotNull() & (col("property_details.garage_spaces") > 0),
                lit("garage")
            ).otherwise(lit("none")).alias("type")
        )
        
        return df.withColumn("parking", parking_struct)
    
    def _map_financial_fields(self, df: DataFrame) -> DataFrame:
        """Map financial fields."""
        return df.withColumn("price_per_sqft", 
                           self._safe_column_access(df, "price_per_sqft").cast(FloatType())) \
                 .withColumn("hoa_fee", lit(None).cast(FloatType())) \
                 .withColumn("tax_assessed_value", lit(None).cast(IntegerType())) \
                 .withColumn("annual_tax", lit(None).cast(FloatType()))
    
    def _map_status_and_dates(self, df: DataFrame) -> DataFrame:
        """Map status and date fields."""
        # Convert listing_date string to timestamp
        df = df.withColumn("listing_date",
                          when(col("listing_date").isNotNull(),
                               to_timestamp(col("listing_date"), "yyyy-MM-dd"))
                          .otherwise(lit(None).cast(TimestampType())))
        
        # Add other status fields
        df = df.withColumn("status", lit("active")) \
               .withColumn("last_updated", lit(None).cast(TimestampType())) \
               .withColumn("days_on_market", 
                          self._safe_column_access(df, "days_on_market").cast(IntegerType()))
        
        return df
    
    def _map_features_and_amenities(self, df: DataFrame) -> DataFrame:
        """Map features and amenities arrays."""
        # Features are already arrays in input, just clean them
        df = df.withColumn("features", 
                          when(col("features").isNotNull(), col("features"))
                          .otherwise(array().cast("array<string>")))
        
        # Amenities will be empty for now (can be enriched later)
        df = df.withColumn("amenities", array().cast("array<string>"))
        
        return df
    
    def _map_media_fields(self, df: DataFrame) -> DataFrame:
        """Map media fields."""
        return df.withColumn("virtual_tour_url", 
                           self._safe_column_access(df, "virtual_tour_url")) \
                 .withColumn("images",
                           when(col("images").isNotNull(), col("images"))
                           .otherwise(array().cast("array<string>"))) \
                 .withColumn("mls_number", lit(None)) \
                 .withColumn("search_tags", lit(None))
    
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
        """Validate property-specific input requirements."""
        super()._validate_input(df)
        
        # Check for required nested structures
        if "address" not in df.columns:
            self.logger.warning("Address object not found in input DataFrame")
        
        if "property_details" not in df.columns:
            self.logger.warning("Property details object not found in input DataFrame")
        
        self.logger.debug("Property input validation completed")