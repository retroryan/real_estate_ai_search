"""
Neighborhood-specific data enrichment engine.

This module provides enrichment capabilities specifically for neighborhood data,
including location normalization, demographic validation, and boundary processing.
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
    trim,
    udf,
    upper,
    when,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class NeighborhoodEnrichmentConfig(BaseModel):
    """Configuration for neighborhood enrichment operations."""
    
    enable_location_normalization: bool = Field(
        default=True,
        description="Normalize location names and boundaries"
    )
    
    enable_demographic_validation: bool = Field(
        default=True,
        description="Validate and enrich demographic data"
    )
    
    enable_boundary_processing: bool = Field(
        default=True,
        description="Process and validate boundary data"
    )
    
    enable_quality_scoring: bool = Field(
        default=True,
        description="Calculate neighborhood data quality scores"
    )
    
    enable_correlation_ids: bool = Field(
        default=True,
        description="Generate correlation IDs for tracking"
    )
    
    min_quality_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score for neighborhoods"
    )
    
    city_mappings: Dict[str, str] = Field(
        default_factory=lambda: {
            "SF": "San Francisco",
            "PC": "Park City",
            "NYC": "New York City",
            "LA": "Los Angeles",
        },
        description="City name mappings"
    )
    
    state_mappings: Dict[str, str] = Field(
        default_factory=lambda: {
            "CA": "California",
            "UT": "Utah",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
        },
        description="State name mappings"
    )


class NeighborhoodEnricher:
    """
    Enriches neighborhood data with normalized fields, demographic validation,
    and quality metrics specific to neighborhood information.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[NeighborhoodEnrichmentConfig] = None):
        """
        Initialize the neighborhood enricher.
        
        Args:
            spark: Active SparkSession
            config: Neighborhood enrichment configuration
        """
        self.spark = spark
        self.config = config or NeighborhoodEnrichmentConfig()
        
        # Register UDF for UUID generation
        self._register_udfs()
        
        # Create broadcast variables for location lookups
        if self.config.enable_location_normalization:
            self._create_location_broadcasts()
    
    def _register_udfs(self):
        """Register necessary UDFs."""
        def generate_uuid() -> str:
            return str(uuid.uuid4())
        
        self.generate_uuid_udf = udf(generate_uuid, StringType())
    
    def _create_location_broadcasts(self):
        """Create broadcast variables for location normalization."""
        # City mappings
        city_data = [(k, v) for k, v in self.config.city_mappings.items()]
        self.city_lookup_df = self.spark.createDataFrame(
            city_data, ["city_abbr", "city_full"]
        )
        
        # State mappings
        state_data = [(k, v) for k, v in self.config.state_mappings.items()]
        self.state_lookup_df = self.spark.createDataFrame(
            state_data, ["state_abbr", "state_full"]
        )
    
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply neighborhood-specific enrichments.
        
        Args:
            df: Neighborhood DataFrame to enrich
            
        Returns:
            Enriched neighborhood DataFrame
        """
        logger.info("Starting neighborhood enrichment process")
        
        initial_count = df.count()
        enriched_df = df
        
        # Add correlation IDs if configured
        if self.config.enable_correlation_ids:
            enriched_df = self._add_correlation_ids(enriched_df)
            logger.info("Added correlation IDs to neighborhoods")
        
        # Normalize location names
        if self.config.enable_location_normalization:
            enriched_df = self._normalize_locations(enriched_df)
            logger.info("Normalized neighborhood locations")
        
        # Validate and enrich demographics
        if self.config.enable_demographic_validation:
            enriched_df = self._validate_demographics(enriched_df)
            logger.info("Validated demographic data")
        
        # Process boundaries
        if self.config.enable_boundary_processing:
            enriched_df = self._process_boundaries(enriched_df)
            logger.info("Processed neighborhood boundaries")
        
        # Calculate quality scores
        if self.config.enable_quality_scoring:
            enriched_df = self._calculate_quality_scores(enriched_df)
            logger.info("Calculated neighborhood quality scores")
        
        # Add processing timestamp
        enriched_df = enriched_df.withColumn("processed_at", current_timestamp())
        
        # Validate enrichment
        final_count = enriched_df.count()
        if final_count != initial_count:
            logger.warning(f"Neighborhood count changed: {initial_count} -> {final_count}")
        
        logger.info(f"Neighborhood enrichment completed for {final_count} records")
        return enriched_df
    
    def _add_correlation_ids(self, df: DataFrame) -> DataFrame:
        """Add correlation IDs for neighborhood tracking."""
        # Check if column already exists
        if "neighborhood_correlation_id" in df.columns:
            return df.withColumn(
                "neighborhood_correlation_id",
                when(col("neighborhood_correlation_id").isNull(), self.generate_uuid_udf())
                .otherwise(col("neighborhood_correlation_id"))
            )
        else:
            # Create new column
            return df.withColumn("neighborhood_correlation_id", self.generate_uuid_udf())
    
    def _normalize_locations(self, df: DataFrame) -> DataFrame:
        """
        Normalize neighborhood location fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized location fields
        """
        # Normalize neighborhood names (using 'name' column)
        df_with_name = df.withColumn(
            "neighborhood_name_normalized",
            when(col("name").isNotNull(),
                 trim(col("name")))
            .otherwise(lit(None))
        )
        
        # Normalize cities
        df_with_city = df_with_name.join(
            broadcast(self.city_lookup_df),
            upper(trim(df_with_name.city)) == upper(self.city_lookup_df.city_abbr),
            "left"
        ).withColumn(
            "city_normalized",
            coalesce(col("city_full"), col("city"))
        ).drop("city_abbr", "city_full")
        
        # Normalize states
        df_with_state = df_with_city.join(
            broadcast(self.state_lookup_df),
            upper(trim(df_with_city.state)) == upper(self.state_lookup_df.state_abbr),
            "left"
        ).withColumn(
            "state_normalized",
            coalesce(col("state_full"), col("state"))
        ).drop("state_abbr", "state_full")
        
        return df_with_state
    
    def _validate_demographics(self, df: DataFrame) -> DataFrame:
        """
        Validate and enrich demographic data.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with validated demographics
        """
        # Validate population
        df_with_pop = df.withColumn(
            "population_validated",
            when((col("population").isNotNull()) & (col("population") >= 0),
                 col("population"))
            .otherwise(lit(None))
        )
        
        # Validate median income
        df_with_income = df_with_pop.withColumn(
            "median_income_validated",
            when((col("median_income").isNotNull()) & (col("median_income") >= 0),
                 col("median_income"))
            .otherwise(lit(None))
        )
        
        # Validate median age
        df_with_age = df_with_income.withColumn(
            "median_age_validated",
            when((col("median_age").isNotNull()) & 
                 (col("median_age") >= 0) & 
                 (col("median_age") <= 120),
                 col("median_age"))
            .otherwise(lit(None))
        )
        
        # Calculate demographic completeness score
        df_with_demo_score = df_with_age.withColumn(
            "demographic_completeness",
            (
                when(col("population_validated").isNotNull(), 0.33).otherwise(0.0) +
                when(col("median_income_validated").isNotNull(), 0.33).otherwise(0.0) +
                when(col("median_age_validated").isNotNull(), 0.34).otherwise(0.0)
            ).cast("decimal(3,2)")
        )
        
        # Add income bracket
        df_with_bracket = df_with_demo_score.withColumn(
            "income_bracket",
            when(col("median_income_validated") < 30000, lit("low"))
            .when(col("median_income_validated") < 60000, lit("lower-middle"))
            .when(col("median_income_validated") < 100000, lit("middle"))
            .when(col("median_income_validated") < 150000, lit("upper-middle"))
            .when(col("median_income_validated") >= 150000, lit("high"))
            .otherwise(lit("unknown"))
        )
        
        return df_with_bracket
    
    def _process_boundaries(self, df: DataFrame) -> DataFrame:
        """
        Process and validate boundary data.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with processed boundaries
        """
        # Check if boundaries exist and are valid
        df_with_boundary_check = df.withColumn(
            "has_valid_boundary",
            when(col("boundary").isNotNull() & 
                 (expr("size(boundary)") > 0),
                 lit(True))
            .otherwise(lit(False))
        )
        
        # Calculate boundary area if coordinates exist
        # This is a simplified check - actual area calculation would be more complex
        df_with_area = df_with_boundary_check.withColumn(
            "boundary_point_count",
            when(col("boundary").isNotNull(),
                 expr("size(boundary)"))
            .otherwise(lit(0))
        )
        
        return df_with_area
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate neighborhood data quality scores.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with quality scores
        """
        # Neighborhood-specific quality score calculation
        quality_expr = (
            # Essential fields (40% weight)
            (when(col("neighborhood_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("neighborhood_name_normalized").isNotNull(), 0.15).otherwise(0.0)) +
            (when(col("city").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("state").isNotNull(), 0.05).otherwise(0.0)) +
            
            # Demographics (25% weight)
            (when(col("population_validated").isNotNull(), 0.08).otherwise(0.0)) +
            (when(col("median_income_validated").isNotNull(), 0.08).otherwise(0.0)) +
            (when(col("median_age_validated").isNotNull(), 0.09).otherwise(0.0)) +
            
            # Amenities (20% weight)
            (when(col("amenities").isNotNull() & (expr("size(amenities)") > 0), 0.2).otherwise(0.0)) +
            
            # Description (15% weight)
            (when(col("description").isNotNull() & (col("description") != ""), 0.15).otherwise(0.0))
        )
        
        # Apply quality score
        df_with_quality = df.withColumn(
            "neighborhood_quality_score",
            quality_expr.cast("decimal(3,2)")
        )
        
        # Add validation status
        df_with_validation = df_with_quality.withColumn(
            "neighborhood_validation_status",
            when(
                col("neighborhood_quality_score") >= self.config.min_quality_score,
                lit("validated")
            ).when(
                col("neighborhood_quality_score") < self.config.min_quality_score,
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
        stats["total_neighborhoods"] = total
        
        # Location normalization
        if "city_normalized" in df.columns:
            with_normalized_city = df.filter(col("city_normalized").isNotNull()).count()
            stats["neighborhoods_with_normalized_city"] = with_normalized_city
        
        # Demographics
        if "demographic_completeness" in df.columns:
            demo_stats = df.select(
                expr("avg(demographic_completeness) as avg_completeness"),
                expr("count(case when demographic_completeness = 1.0 then 1 end) as fully_complete")
            ).collect()[0]
            
            stats["avg_demographic_completeness"] = float(demo_stats["avg_completeness"]) if demo_stats["avg_completeness"] else 0
            stats["neighborhoods_with_complete_demographics"] = demo_stats["fully_complete"]
        
        # Boundaries
        if "has_valid_boundary" in df.columns:
            with_boundaries = df.filter(col("has_valid_boundary") == True).count()
            stats["neighborhoods_with_boundaries"] = with_boundaries
        
        # Quality scores
        if "neighborhood_quality_score" in df.columns:
            quality_stats = df.select(
                expr("avg(neighborhood_quality_score) as avg_quality"),
                expr("min(neighborhood_quality_score) as min_quality"),
                expr("max(neighborhood_quality_score) as max_quality"),
                expr("count(case when neighborhood_validation_status = 'validated' then 1 end) as validated"),
                expr("count(case when neighborhood_validation_status = 'low_quality' then 1 end) as low_quality")
            ).collect()[0]
            
            stats["avg_quality_score"] = float(quality_stats["avg_quality"]) if quality_stats["avg_quality"] else 0
            stats["min_quality_score"] = float(quality_stats["min_quality"]) if quality_stats["min_quality"] else 0
            stats["max_quality_score"] = float(quality_stats["max_quality"]) if quality_stats["max_quality"] else 0
            stats["validated_neighborhoods"] = quality_stats["validated"]
            stats["low_quality_neighborhoods"] = quality_stats["low_quality"]
        
        # Income brackets
        if "income_bracket" in df.columns:
            bracket_counts = df.groupBy("income_bracket").count().collect()
            stats["income_brackets"] = {row["income_bracket"]: row["count"] for row in bracket_counts}
        
        return stats