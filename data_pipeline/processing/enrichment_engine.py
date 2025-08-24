"""
Data enrichment engine using Spark SQL transformations.

This module provides distributed data enrichment capabilities using
Spark's built-in SQL functions and catalyst optimizer for optimal performance.
Follows Apache Spark best practices and uses Pydantic for configuration.
"""

import logging
import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    current_timestamp,
    expr,
    hash as spark_hash,
    lit,
    lower,
    regexp_replace,
    trim,
    udf,
    upper,
    when,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class LocationMapping(BaseModel):
    """Location normalization mapping configuration."""
    
    city_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "SF": "San Francisco",
            "PC": "Park City",
            "NYC": "New York City",
            "LA": "Los Angeles",
        },
        description="City abbreviation to full name mappings"
    )
    
    state_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "CA": "California",
            "UT": "Utah",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
            "WA": "Washington",
            "OR": "Oregon",
            "NV": "Nevada",
            "AZ": "Arizona",
            "CO": "Colorado",
        },
        description="State abbreviation to full name mappings"
    )


class EnrichmentConfig(BaseModel):
    """Configuration for data enrichment operations."""
    
    enable_location_normalization: bool = Field(
        default=True,
        description="Enable city/state normalization"
    )
    
    enable_derived_fields: bool = Field(
        default=True,
        description="Calculate derived fields like price_per_sqft"
    )
    
    enable_correlation_ids: bool = Field(
        default=True,
        description="Generate correlation IDs for entity tracking"
    )
    
    enable_quality_scoring: bool = Field(
        default=True,
        description="Calculate data quality scores"
    )
    
    min_quality_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score"
    )
    
    location_mappings: LocationMapping = Field(
        default_factory=LocationMapping,
        description="Location normalization mappings"
    )


class DataEnrichmentEngine:
    """
    Enriches unified data with normalized fields, derived calculations,
    and quality metrics using Spark SQL transformations.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[EnrichmentConfig] = None):
        """
        Initialize the enrichment engine.
        
        Args:
            spark: Active SparkSession
            config: Enrichment configuration
        """
        self.spark = spark
        self.config = config or EnrichmentConfig()
        
        # Register UDF for UUID generation (only when absolutely necessary)
        self._register_udfs()
        
        # Create broadcast variables for small lookup tables
        self._create_broadcast_variables()
    
    def _register_udfs(self):
        """Register necessary UDFs (minimized per Spark best practices)."""
        # Only use UDF for UUID generation as there's no built-in Spark function
        def generate_uuid() -> str:
            return str(uuid.uuid4())
        
        self.generate_uuid_udf = udf(generate_uuid, StringType())
    
    def _create_broadcast_variables(self):
        """Create broadcast variables for small lookup tables."""
        # Create DataFrame for city mappings (small dataset, perfect for broadcast)
        city_data = [(k, v) for k, v in self.config.location_mappings.city_abbreviations.items()]
        self.city_lookup_df = self.spark.createDataFrame(
            city_data, ["city_abbr", "city_full"]
        )
        
        # Create DataFrame for state mappings
        state_data = [(k, v) for k, v in self.config.location_mappings.state_abbreviations.items()]
        self.state_lookup_df = self.spark.createDataFrame(
            state_data, ["state_abbr", "state_full"]
        )
    
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply all enrichment transformations to the DataFrame.
        
        Args:
            df: Input DataFrame to enrich
            
        Returns:
            Enriched DataFrame with all transformations applied
        """
        logger.info("Starting data enrichment process")
        
        # Track initial record count
        initial_count = df.count()
        logger.info(f"Enriching {initial_count} records")
        
        # Apply enrichments in sequence
        enriched_df = df
        
        if self.config.enable_correlation_ids:
            enriched_df = self._add_correlation_ids(enriched_df)
            logger.info("Added correlation IDs")
        
        if self.config.enable_location_normalization:
            enriched_df = self._normalize_locations(enriched_df)
            logger.info("Normalized location fields")
        
        if self.config.enable_derived_fields:
            enriched_df = self._calculate_derived_fields(enriched_df)
            logger.info("Calculated derived fields")
        
        if self.config.enable_quality_scoring:
            enriched_df = self._calculate_quality_scores(enriched_df)
            logger.info("Calculated quality scores")
        
        # Add processing timestamp
        enriched_df = enriched_df.withColumn("processed_at", current_timestamp())
        
        # Validate enrichment
        final_count = enriched_df.count()
        if final_count != initial_count:
            logger.warning(f"Record count changed: {initial_count} -> {final_count}")
        
        logger.info("Data enrichment completed successfully")
        return enriched_df
    
    def _add_correlation_ids(self, df: DataFrame) -> DataFrame:
        """
        Add correlation IDs for entity tracking.
        
        Uses a combination of UUID and deterministic hash for tracking.
        """
        return df.withColumn(
            "correlation_uuid",
            when(col("correlation_uuid").isNull(), self.generate_uuid_udf())
            .otherwise(col("correlation_uuid"))
        )
    
    def _normalize_locations(self, df: DataFrame) -> DataFrame:
        """
        Normalize city and state fields using broadcast joins.
        
        Uses Spark SQL broadcast joins for efficient lookups.
        """
        # Normalize cities using broadcast join (efficient for small lookup tables)
        df_with_city = df.join(
            broadcast(self.city_lookup_df),
            upper(trim(df.city)) == upper(self.city_lookup_df.city_abbr),
            "left"
        ).withColumn(
            "city_normalized",
            coalesce(col("city_full"), col("city"))
        ).drop("city_abbr", "city_full")
        
        # Normalize states using broadcast join
        df_with_state = df_with_city.join(
            broadcast(self.state_lookup_df),
            upper(trim(df_with_city.state)) == upper(self.state_lookup_df.state_abbr),
            "left"
        ).withColumn(
            "state_normalized",
            coalesce(col("state_full"), col("state"))
        ).drop("state_abbr", "state_full")
        
        return df_with_state
    
    def _calculate_derived_fields(self, df: DataFrame) -> DataFrame:
        """
        Calculate derived fields using Spark SQL expressions.
        
        Uses native Spark SQL functions for optimal performance.
        """
        # Calculate price per square foot for properties
        df_with_price_sqft = df.withColumn(
            "price_per_sqft",
            when(
                (col("entity_type") == "PROPERTY") & 
                (col("square_feet") > 0) & 
                col("price").isNotNull(),
                (col("price") / col("square_feet")).cast("decimal(10,4)")
            ).otherwise(col("price_per_sqft"))
        )
        
        # Create content hash for deduplication (using Spark's built-in hash function)
        df_with_hash = df_with_price_sqft.withColumn(
            "content_hash",
            when(
                col("content_hash").isNull() & col("content").isNotNull(),
                expr("sha2(content, 256)")
            ).otherwise(col("content_hash"))
        )
        
        # Add feature count for analysis
        df_with_feature_count = df_with_hash.withColumn(
            "feature_count",
            when(
                col("features").isNotNull(),
                expr("size(features)")
            ).otherwise(lit(0))
        )
        
        return df_with_feature_count
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate data quality scores using Spark SQL.
        
        Uses a weighted scoring system based on field completeness.
        """
        # Define quality score calculation using Spark SQL expressions
        quality_expr = (
            # Core fields (40% weight)
            (when(col("entity_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("entity_type").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("city").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("state").isNotNull(), 0.1).otherwise(0.0)) +
            
            # Content fields (30% weight)
            (when(col("title").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("content").isNotNull() & (col("content") != ""), 0.2)
             .otherwise(0.0)) +
            
            # Entity-specific fields (30% weight)
            when(
                col("entity_type") == "PROPERTY",
                (when(col("price").isNotNull(), 0.1).otherwise(0.0)) +
                (when(col("bedrooms").isNotNull(), 0.1).otherwise(0.0)) +
                (when(col("square_feet").isNotNull(), 0.1).otherwise(0.0))
            ).when(
                col("entity_type") == "WIKIPEDIA_ARTICLE",
                (when(col("url").isNotNull(), 0.1).otherwise(0.0)) +
                (when(col("summary").isNotNull(), 0.1).otherwise(0.0)) +
                (when(col("confidence_score") > 0.5, 0.1).otherwise(0.0))
            ).when(
                col("entity_type") == "NEIGHBORHOOD",
                (when(col("features").isNotNull() & (expr("size(features)") > 0), 0.15)
                 .otherwise(0.0)) +
                (when(col("description").isNotNull(), 0.15).otherwise(0.0))
            ).otherwise(0.0)
        )
        
        # Apply quality score
        df_with_quality = df.withColumn(
            "data_quality_score",
            when(col("data_quality_score").isNull(), quality_expr)
            .otherwise(col("data_quality_score"))
        )
        
        # Update validation status based on quality score
        df_with_validation = df_with_quality.withColumn(
            "validation_status",
            when(
                col("data_quality_score") >= self.config.min_quality_score,
                lit("validated")
            ).when(
                col("data_quality_score") < self.config.min_quality_score,
                lit("low_quality")
            ).otherwise(lit("pending"))
        )
        
        return df_with_validation
    
    def get_enrichment_statistics(self, df: DataFrame) -> Dict:
        """
        Calculate statistics about the enrichment process.
        
        Args:
            df: Enriched DataFrame
            
        Returns:
            Dictionary of enrichment statistics
        """
        stats = {}
        
        # Calculate basic statistics using Spark SQL
        stats["total_records"] = df.count()
        stats["records_with_correlation_id"] = df.filter(
            col("correlation_uuid").isNotNull()
        ).count()
        stats["records_with_normalized_city"] = df.filter(
            col("city_normalized").isNotNull()
        ).count()
        stats["records_with_normalized_state"] = df.filter(
            col("state_normalized").isNotNull()
        ).count()
        
        # Quality statistics
        quality_stats = df.select(
            expr("avg(data_quality_score) as avg_quality"),
            expr("min(data_quality_score) as min_quality"),
            expr("max(data_quality_score) as max_quality"),
            expr("count(case when validation_status = 'validated' then 1 end) as validated_count"),
            expr("count(case when validation_status = 'low_quality' then 1 end) as low_quality_count")
        ).collect()[0]
        
        stats["avg_quality_score"] = quality_stats["avg_quality"]
        stats["min_quality_score"] = quality_stats["min_quality"]
        stats["max_quality_score"] = quality_stats["max_quality"]
        stats["validated_records"] = quality_stats["validated_count"]
        stats["low_quality_records"] = quality_stats["low_quality_count"]
        
        # Entity-specific statistics
        entity_stats = df.groupBy("entity_type").count().collect()
        stats["entity_counts"] = {row["entity_type"]: row["count"] for row in entity_stats}
        
        return stats