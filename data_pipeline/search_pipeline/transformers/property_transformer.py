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
from pyspark.sql.types import FloatType, IntegerType, TimestampType, DoubleType, DecimalType

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
        
        # Convert decimal fields for Elasticsearch compatibility
        df = self._convert_decimal_fields(df)
        
        return df
    
    def _map_core_property_fields(self, df: DataFrame) -> DataFrame:
        """Map core property fields from input to output schema."""
        # Get all column names and select them explicitly to avoid duplicates
        all_columns = df.columns
        selected_columns = []
        
        # Add core fields first
        selected_columns.extend([
            col("listing_id"),
            self._safe_column_access(df, "property_type").alias("property_type"),
            self._safe_column_access(df, "listing_price").cast(FloatType()).alias("price"),
            self._safe_column_access(df, "bedrooms").cast(IntegerType()).alias("bedrooms"),
            self._safe_column_access(df, "bathrooms").cast(FloatType()).alias("bathrooms"),
            self._safe_column_access(df, "square_feet").cast(IntegerType()).alias("square_feet"),
            self._safe_column_access(df, "year_built").cast(IntegerType()).alias("year_built"),
            self._safe_column_access(df, "lot_size").cast(IntegerType()).alias("lot_size"),
            self._safe_column_access(df, "description").alias("description"),
            self._safe_column_access(df, "neighborhood_id").alias("neighborhood_id")
        ])
        
        # Add all other columns except the ones we've already handled
        handled_fields = {
            "listing_id", "property_type", "listing_price", "bedrooms", 
            "bathrooms", "square_feet", "year_built", "lot_size", 
            "description", "neighborhood_id"
        }
        
        for column_name in all_columns:
            if column_name not in handled_fields:
                selected_columns.append(col(column_name))
        
        return df.select(*selected_columns)
    
    def _create_address_object(self, df: DataFrame) -> DataFrame:
        """Create address nested object from flattened fields."""
        address_struct = struct(
            self._safe_column_access(df, "street").alias("street"),
            self._safe_column_access(df, "city").alias("city"),
            self._safe_column_access(df, "state").alias("state"),
            self._safe_column_access(df, "zip_code").alias("zip_code"),
            # Create location array from flattened coordinate fields [longitude, latitude]
            when(
                (self._safe_column_access(df, "latitude").isNotNull()) & (self._safe_column_access(df, "longitude").isNotNull()),
                array(
                    self._safe_column_access(df, "longitude").cast(DoubleType()), 
                    self._safe_column_access(df, "latitude").cast(DoubleType())
                )
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
            self._safe_column_access(df, "garage_spaces").cast(IntegerType()).alias("spaces"),
            lit(None).cast(IntegerType()).alias("capacity"),
            when(
                col("garage_spaces").isNotNull() & (col("garage_spaces") > 0),
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
    
    def _convert_decimal_fields(self, df: DataFrame) -> DataFrame:
        """Convert ALL Decimal fields to Double for Elasticsearch compatibility.
        
        The Elasticsearch-Spark connector explicitly rejects DecimalType values.
        This method recursively converts all decimal types in the schema.
        """
        from pyspark.sql.types import ArrayType, StructType, StructField
        from pyspark.sql import functions as F
        
        def convert_data_type(data_type):
            """Recursively convert DecimalType to DoubleType in schema."""
            if isinstance(data_type, DecimalType):
                return DoubleType()
            elif isinstance(data_type, ArrayType):
                return ArrayType(convert_data_type(data_type.elementType), data_type.containsNull)
            elif isinstance(data_type, StructType):
                return StructType([
                    StructField(field.name, convert_data_type(field.dataType), field.nullable)
                    for field in data_type.fields
                ])
            else:
                return data_type
        
        # Check if any conversions are needed
        schema_needs_conversion = False
        new_schema_fields = []
        
        for field in df.schema.fields:
            new_data_type = convert_data_type(field.dataType)
            if new_data_type != field.dataType:
                schema_needs_conversion = True
                self.logger.debug(f"Schema conversion needed for field '{field.name}'")
            new_schema_fields.append(StructField(field.name, new_data_type, field.nullable))
        
        if not schema_needs_conversion:
            return df
        
        # Apply conversions by casting columns with the new schema
        select_expressions = []
        for old_field, new_field in zip(df.schema.fields, new_schema_fields):
            if old_field.dataType != new_field.dataType:
                self.logger.debug(f"Converting field '{old_field.name}' from {old_field.dataType} to {new_field.dataType}")
                select_expressions.append(col(old_field.name).cast(new_field.dataType).alias(old_field.name))
            else:
                select_expressions.append(col(old_field.name))
        
        return df.select(*select_expressions)
    
    def _validate_input(self, df: DataFrame) -> None:
        """Validate property-specific input requirements."""
        super()._validate_input(df)
        
        # Check for recommended flattened address fields
        if "street" not in df.columns and "city" not in df.columns:
            self.logger.warning("Address fields (street, city, etc.) not found in input DataFrame")
        
        # Check for recommended flattened property detail fields
        if "property_type" not in df.columns and "bedrooms" not in df.columns:
            self.logger.warning("Property detail fields not found in input DataFrame")
        
        # Data pipeline produces flattened structure, so no nested objects expected
        self.logger.debug("Property input validation completed for flattened schema")