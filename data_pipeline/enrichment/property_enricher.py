"""
Property-specific data enrichment engine.

This module provides enrichment capabilities specifically for property data,
including price calculations, address normalization, and quality scoring.
"""

import logging
import uuid
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    current_timestamp,
    expr,
    lit,
    lower,
    trim,
    udf,
    upper,
    when,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class PropertyEnrichmentConfig(BaseModel):
    """Configuration for property enrichment operations."""
    
    enable_price_calculations: bool = Field(
        default=True,
        description="Calculate derived price fields like price_per_sqft"
    )
    
    enable_address_normalization: bool = Field(
        default=True,
        description="Normalize address and location fields"
    )
    
    enable_quality_scoring: bool = Field(
        default=True,
        description="Calculate property data quality scores"
    )
    
    enable_correlation_ids: bool = Field(
        default=True,
        description="Generate correlation IDs for tracking"
    )
    
    min_quality_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score for properties"
    )
    
    city_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "SF": "San Francisco",
            "PC": "Park City",
            "NYC": "New York City",
            "LA": "Los Angeles",
        },
        description="City abbreviation mappings"
    )
    
    state_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "CA": "California",
            "UT": "Utah",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
        },
        description="State abbreviation mappings"
    )


class PropertyEnricher:
    """
    Enriches property data with calculated fields, normalized values,
    and quality metrics specific to real estate listings.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[PropertyEnrichmentConfig] = None):
        """
        Initialize the property enricher.
        
        Args:
            spark: Active SparkSession
            config: Property enrichment configuration
        """
        self.spark = spark
        self.config = config or PropertyEnrichmentConfig()
        
        # Register UDF for UUID generation
        self._register_udfs()
        
        # Create broadcast variables for location lookups
        if self.config.enable_address_normalization:
            self._create_location_broadcasts()
    
    def _register_udfs(self):
        """Register necessary UDFs."""
        def generate_uuid() -> str:
            return str(uuid.uuid4())
        
        self.generate_uuid_udf = udf(generate_uuid, StringType())
    
    def _create_location_broadcasts(self):
        """Create broadcast variables for location normalization."""
        # City mappings
        city_data = [(k, v) for k, v in self.config.city_abbreviations.items()]
        self.city_lookup_df = self.spark.createDataFrame(
            city_data, ["city_abbr", "city_full"]
        )
        
        # State mappings
        state_data = [(k, v) for k, v in self.config.state_abbreviations.items()]
        self.state_lookup_df = self.spark.createDataFrame(
            state_data, ["state_abbr", "state_full"]
        )
    
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply property-specific enrichments.
        
        Args:
            df: Property DataFrame to enrich
            
        Returns:
            Enriched property DataFrame
        """
        logger.info("Starting property enrichment process")
        
        initial_count = df.count()
        enriched_df = df
        
        # Add correlation IDs if configured
        if self.config.enable_correlation_ids:
            enriched_df = self._add_correlation_ids(enriched_df)
            logger.info("Added correlation IDs to properties")
        
        # Normalize addresses and locations
        if self.config.enable_address_normalization:
            enriched_df = self._normalize_addresses(enriched_df)
            logger.info("Normalized property addresses")
        
        # Calculate price-related fields
        if self.config.enable_price_calculations:
            enriched_df = self._calculate_price_fields(enriched_df)
            logger.info("Calculated price-related fields")
        
        # Calculate quality scores
        if self.config.enable_quality_scoring:
            enriched_df = self._calculate_quality_scores(enriched_df)
            logger.info("Calculated property quality scores")
        
        # Add processing timestamp
        enriched_df = enriched_df.withColumn("processed_at", current_timestamp())
        
        # Validate enrichment
        final_count = enriched_df.count()
        if final_count != initial_count:
            logger.warning(f"Property count changed: {initial_count} -> {final_count}")
        
        logger.info(f"Property enrichment completed for {final_count} records")
        return enriched_df
    
    def _add_correlation_ids(self, df: DataFrame) -> DataFrame:
        """Add correlation IDs for property tracking."""
        # Check if column already exists
        if "property_correlation_id" in df.columns:
            return df.withColumn(
                "property_correlation_id",
                when(col("property_correlation_id").isNull(), self.generate_uuid_udf())
                .otherwise(col("property_correlation_id"))
            )
        else:
            # Create new column
            return df.withColumn("property_correlation_id", self.generate_uuid_udf())
    
    def _normalize_addresses(self, df: DataFrame) -> DataFrame:
        """
        Normalize property addresses and location fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized address fields
        """
        # Extract city, state, and zip_code from nested address structure
        df_with_location = df.withColumn("city", col("address.city")).withColumn("state", col("address.state")).withColumn("zip_code", col("address.zip_code"))
        
        # Normalize cities
        df_with_city = df_with_location.join(
            broadcast(self.city_lookup_df),
            upper(trim(col("city"))) == upper(self.city_lookup_df.city_abbr),
            "left"
        ).withColumn(
            "city_normalized",
            coalesce(col("city_full"), col("city"))
        ).drop("city_abbr", "city_full")
        
        # Normalize states
        df_with_state = df_with_city.join(
            broadcast(self.state_lookup_df),
            upper(trim(col("state"))) == upper(self.state_lookup_df.state_abbr),
            "left"
        ).withColumn(
            "state_normalized",
            coalesce(col("state_full"), col("state"))
        ).drop("state_abbr", "state_full")
        
        # Normalize street address (extract from nested structure)
        df_with_address = df_with_state.withColumn(
            "address_normalized",
            when(col("address.street").isNotNull(),
                 trim(lower(col("address.street"))))
            .otherwise(lit(None))
        )
        
        return df_with_address
    
    def _calculate_price_fields(self, df: DataFrame) -> DataFrame:
        """
        Calculate price-related derived fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with calculated price fields
        """
        # Price per square foot
        df_with_price_sqft = df.withColumn(
            "price_per_sqft",
            when(
                (col("square_feet") > 0) & col("price").isNotNull(),
                (col("price") / col("square_feet")).cast("decimal(10,2)")
            ).otherwise(lit(None))
        )
        
        # Price per bedroom
        df_with_price_bedroom = df_with_price_sqft.withColumn(
            "price_per_bedroom",
            when(
                (col("bedrooms") > 0) & col("price").isNotNull(),
                (col("price") / col("bedrooms")).cast("decimal(10,2)")
            ).otherwise(lit(None))
        )
        
        # Price category
        df_with_price_category = df_with_price_bedroom.withColumn(
            "price_category",
            when(col("price") < 200000, lit("budget"))
            .when(col("price") < 500000, lit("mid-range"))
            .when(col("price") < 1000000, lit("high-end"))
            .when(col("price") >= 1000000, lit("luxury"))
            .otherwise(lit("unknown"))
        )
        
        # Property size category
        df_with_size_category = df_with_price_category.withColumn(
            "size_category",
            when(col("square_feet") < 1000, lit("small"))
            .when(col("square_feet") < 2000, lit("medium"))
            .when(col("square_feet") < 3500, lit("large"))
            .when(col("square_feet") >= 3500, lit("extra-large"))
            .otherwise(lit("unknown"))
        )
        
        return df_with_size_category
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate property data quality scores.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with quality scores
        """
        # Property-specific quality score calculation
        quality_expr = (
            # Essential fields (50% weight)
            (when(col("listing_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("price").isNotNull() & (col("price") > 0), 0.15).otherwise(0.0)) +
            (when(col("bedrooms").isNotNull() & (col("bedrooms") >= 0), 0.1).otherwise(0.0)) +
            (when(col("bathrooms").isNotNull() & (col("bathrooms") >= 0), 0.05).otherwise(0.0)) +
            (when(col("square_feet").isNotNull() & (col("square_feet") > 0), 0.1).otherwise(0.0)) +
            
            # Location fields (25% weight)
            (when(col("address").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("city").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("state").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("zip_code").isNotNull(), 0.05).otherwise(0.0)) +
            
            # Description and features (15% weight)
            (when(col("description").isNotNull() & (col("description") != ""), 0.1).otherwise(0.0)) +
            (when(col("features").isNotNull() & (expr("size(features)") > 0), 0.05).otherwise(0.0)) +
            
            # Additional valuable fields (10% weight)
            (when(col("property_type").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("year_built").isNotNull() & (col("year_built") > 1800), 0.05).otherwise(0.0))
        )
        
        # Apply quality score
        df_with_quality = df.withColumn(
            "property_quality_score",
            quality_expr.cast("decimal(3,2)")
        )
        
        # Add validation status
        df_with_validation = df_with_quality.withColumn(
            "property_validation_status",
            when(
                col("property_quality_score") >= self.config.min_quality_score,
                lit("validated")
            ).when(
                col("property_quality_score") < self.config.min_quality_score,
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
        
        total = df.count()
        stats["total_properties"] = total
        
        # Price calculations
        if "price_per_sqft" in df.columns:
            with_price_sqft = df.filter(col("price_per_sqft").isNotNull()).count()
            stats["properties_with_price_per_sqft"] = with_price_sqft
            
            avg_price_sqft = df.filter(col("price_per_sqft").isNotNull()) \
                              .select(expr("avg(price_per_sqft)")).collect()[0][0]
            stats["avg_price_per_sqft"] = float(avg_price_sqft) if avg_price_sqft else 0
        
        # Address normalization
        if "city_normalized" in df.columns:
            with_normalized_city = df.filter(col("city_normalized").isNotNull()).count()
            stats["properties_with_normalized_city"] = with_normalized_city
        
        # Quality scores
        if "property_quality_score" in df.columns:
            quality_stats = df.select(
                expr("avg(property_quality_score) as avg_quality"),
                expr("min(property_quality_score) as min_quality"),
                expr("max(property_quality_score) as max_quality"),
                expr("count(case when property_validation_status = 'validated' then 1 end) as validated"),
                expr("count(case when property_validation_status = 'low_quality' then 1 end) as low_quality")
            ).collect()[0]
            
            stats["avg_quality_score"] = float(quality_stats["avg_quality"]) if quality_stats["avg_quality"] else 0
            stats["min_quality_score"] = float(quality_stats["min_quality"]) if quality_stats["min_quality"] else 0
            stats["max_quality_score"] = float(quality_stats["max_quality"]) if quality_stats["max_quality"] else 0
            stats["validated_properties"] = quality_stats["validated"]
            stats["low_quality_properties"] = quality_stats["low_quality"]
        
        # Price categories
        if "price_category" in df.columns:
            category_counts = df.groupBy("price_category").count().collect()
            stats["price_categories"] = {row["price_category"]: row["count"] for row in category_counts}
        
        return stats