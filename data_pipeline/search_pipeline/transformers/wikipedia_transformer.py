"""Wikipedia DataFrame transformer for search pipeline.

Transforms Wikipedia article DataFrames from data pipeline to WikipediaDocument schema
using Spark-native operations. Handles Wikipedia-specific field mappings and
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


class WikipediaDataFrameTransformer(BaseDataFrameTransformer):
    """
    Transforms Wikipedia article DataFrames to WikipediaDocument schema.
    
    Handles the conversion from input Wikipedia data structure to the
    target Elasticsearch document schema with proper nested objects
    and field mappings.
    """
    
    def __init__(self):
        """Initialize Wikipedia transformer."""
        super().__init__("wikipedia")
    
    def _get_id_field(self) -> str:
        """Get the ID field for Wikipedia articles."""
        return "page_id"
    
    def _apply_transformation(self, input_df: DataFrame) -> DataFrame:
        """
        Apply Wikipedia-specific transformations.
        
        Args:
            input_df: Input Wikipedia DataFrame from data pipeline
            
        Returns:
            Transformed DataFrame with WikipediaDocument schema
        """
        self.logger.info("Applying Wikipedia transformations")
        
        # Start with core Wikipedia fields
        df = self._map_core_wikipedia_fields(input_df)
        
        # Create nested objects
        df = self._create_address_object(df)
        
        # Handle content fields
        df = self._map_content_fields(df)
        
        # Handle topics and metadata
        df = self._map_topics_and_metadata(df)
        
        # Preserve enrichment fields if present
        df = self._preserve_enrichment_fields(df)
        
        # Preserve embedding fields if present
        df = self._preserve_embedding_fields(df)
        
        # Convert decimal fields for Elasticsearch compatibility
        df = self._convert_decimal_fields(df)
        
        return df
    
    def _map_core_wikipedia_fields(self, df: DataFrame) -> DataFrame:
        """Map core Wikipedia fields from input to output schema."""
        # Check what content field is available
        if "short_summary" in df.columns or "long_summary" in df.columns:
            # Use summaries if available (actual data structure)
            summary_col = self._safe_column_access(df, "short_summary").alias("summary")
            content_col = self._safe_column_access(df, "long_summary").alias("content")
        else:
            # Fallback to summary/content fields
            summary_col = self._safe_column_access(df, "summary").alias("summary")
            content_col = self._safe_column_access(df, "content").alias("content")
            
        # Get all columns except the ones we're explicitly handling
        exclude_cols = ["page_id", "title", "url", "summary", "content", "city", "state", 
                       "best_city", "best_state", "latitude", "longitude", "key_topics", 
                       "topics", "last_modified", "short_summary", "long_summary"]
        other_cols = [col(c) for c in df.columns if c not in exclude_cols]
        
        return df.select(
            # Primary ID and core fields
            col("page_id").cast(IntegerType()),
            col("title"),
            self._safe_column_access(df, "url").alias("url"),
            
            # Content fields
            summary_col,
            content_col,
            
            # Location fields (use best_city and best_state if city/state not available)
            coalesce(
                self._safe_column_access(df, "city"),
                self._safe_column_access(df, "best_city")
            ).alias("city"),
            coalesce(
                self._safe_column_access(df, "state"),
                self._safe_column_access(df, "best_state")
            ).alias("state"),
            
            # Keep latitude/longitude for creating location
            self._safe_column_access(df, "latitude").alias("latitude"),
            self._safe_column_access(df, "longitude").alias("longitude"),
            
            # Keep topics if exists (otherwise will be handled later)
            self._safe_column_access(df, "key_topics").alias("topics"),
            self._safe_column_access(df, "last_modified").alias("last_modified"),
            
            # Keep other fields for further processing
            *other_cols
        )
    
    def _create_address_object(self, df: DataFrame) -> DataFrame:
        """Create address nested object for Wikipedia article location."""
        # For Wikipedia articles, create address from available location data
        address_struct = struct(
            lit(None).alias("street"),  # Street address not typically available
            self._safe_column_access(df, "city").alias("city"),
            self._safe_column_access(df, "state").alias("state"),
            lit(None).alias("zip_code"),  # ZIP not typically available
            # Create location array from latitude/longitude [longitude, latitude]
            when(
                (col("latitude").isNotNull()) & (col("longitude").isNotNull()),
                array(col("longitude"), col("latitude"))
            ).otherwise(lit(None)).alias("location")
        )
        
        return df.withColumn("address", address_struct)
    
    def _map_content_fields(self, df: DataFrame) -> DataFrame:
        """Map content fields with proper handling."""
        # Content fields are already mapped in core fields
        # Just ensure they're properly handled
        return df
    
    def _map_topics_and_metadata(self, df: DataFrame) -> DataFrame:
        """Map topics and metadata fields."""
        # Handle topics array - the field was already renamed in core mapping
        # Just ensure it's an array
        if "topics" not in df.columns:
            df = df.withColumn("topics", array().cast("array<string>"))
        else:
            df = df.withColumn("topics",
                              when(col("topics").isNotNull(), col("topics"))
                              .otherwise(array().cast("array<string>")))
        
        # Handle last_modified date
        df = df.withColumn("last_modified",
                          when(col("last_modified").isNotNull(),
                               # Try to parse various datetime formats
                               coalesce(
                                   to_timestamp(col("last_modified"), "yyyy-MM-dd'T'HH:mm:ss'Z'"),
                                   to_timestamp(col("last_modified"), "yyyy-MM-dd HH:mm:ss"),
                                   to_timestamp(col("last_modified"), "yyyy-MM-dd")
                               ))
                          .otherwise(lit(None).cast(TimestampType())))
        
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
    
    def _convert_decimal_fields(self, df: DataFrame) -> DataFrame:
        """Convert ALL Decimal fields to Double for Elasticsearch compatibility."""
        # Get schema and identify all decimal fields
        for field in df.schema.fields:
            if isinstance(field.dataType, DecimalType):
                self.logger.debug(f"Converting decimal field '{field.name}' to double")
                df = df.withColumn(field.name, col(field.name).cast(DoubleType()))
        
        return df
    
    def _validate_input(self, df: DataFrame) -> None:
        """Validate Wikipedia-specific input requirements."""
        super()._validate_input(df)
        
        # Check for required title field
        if "title" not in df.columns:
            raise ValueError("Required field 'title' not found in Wikipedia DataFrame")
        
        # Check for recommended content fields
        if "summary" not in df.columns and "content" not in df.columns:
            self.logger.warning("Neither 'summary' nor 'content' found in Wikipedia DataFrame")
        
        self.logger.debug("Wikipedia input validation completed")