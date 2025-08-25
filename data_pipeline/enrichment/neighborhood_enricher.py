"""
Neighborhood-specific data enrichment engine.

This module provides enrichment capabilities specifically for neighborhood data,
including location normalization, demographic validation, and boundary processing.
"""

import logging
from typing import Any, Dict, Optional

from pydantic import Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    expr,
    least,
    lit,
    trim,
    upper,
    when,
)

from .base_enricher import BaseEnricher

logger = logging.getLogger(__name__)


class NeighborhoodEnricher(BaseEnricher):
    """
    Enriches neighborhood data with normalized fields, demographic validation,
    and quality metrics specific to neighborhood information.
    """
    
    def __init__(self, spark: SparkSession, location_broadcast: Optional[Any] = None):
        """
        Initialize the neighborhood enricher.
        
        Args:
            spark: Active SparkSession
            location_broadcast: Broadcast variable containing location reference data
        """
        super().__init__(spark, location_broadcast)
        
        # Create broadcast variables for location lookups - always enabled
        self._create_location_broadcasts()
        
        # Override location enricher initialization with neighborhood-specific config - always enabled if location broadcast available
        if self.location_broadcast:
            from .location_enricher import LocationEnricher, LocationEnrichmentConfig
            location_config = LocationEnrichmentConfig(
                enable_hierarchy_resolution=True,
                enable_parent_relationships=True
            )
            self.location_enricher = LocationEnricher(spark, location_broadcast, location_config)
    
    
    def set_location_data(self, location_broadcast: Any):
        """
        Set location broadcast data and create LocationEnricher after initialization.
        
        Args:
            location_broadcast: Broadcast variable containing location reference data
        """
        super().set_location_data(location_broadcast)
        
        if self.location_broadcast:
            from .location_enricher import LocationEnricher, LocationEnrichmentConfig
            location_config = LocationEnrichmentConfig(
                enable_hierarchy_resolution=True,
                enable_parent_relationships=True
            )
            self.location_enricher = LocationEnricher(self.spark, location_broadcast, location_config)
            logger.info("LocationEnricher initialized for neighborhoods with broadcast data")
    
    def _create_location_broadcasts(self):
        """Create broadcast variables for location normalization using base class constants."""
        city_data = [(k, v) for k, v in self.get_city_abbreviations().items()]
        self.city_lookup_df = self.spark.createDataFrame(city_data, ["city_abbr", "city_full"])
        state_data = [(k, v) for k, v in self.get_state_abbreviations().items()]
        self.state_lookup_df = self.spark.createDataFrame(state_data, ["state_abbr", "state_full"])

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
        
        # Add correlation IDs - always enabled
        enriched_df = self.add_correlation_ids(enriched_df, "neighborhood_correlation_id")
        logger.info("Added correlation IDs to neighborhoods")
        
        # Normalize location names - always enabled
        enriched_df = self._normalize_locations(enriched_df)
        logger.info("Normalized neighborhood locations")
        
        # Enhance with location hierarchy and parent relationships - always enabled if location enricher available
        if self.location_enricher:
            enriched_df = self._enhance_with_location_hierarchy(enriched_df)
            logger.info("Enhanced neighborhoods with location hierarchy")
        
        # Validate and enrich demographics - always enabled
        enriched_df = self._validate_demographics(enriched_df)
        logger.info("Validated demographic data")
        
        # Process boundaries - always enabled
        enriched_df = self._process_boundaries(enriched_df)
        logger.info("Processed neighborhood boundaries")
        
        # Calculate quality scores - always enabled
        enriched_df = self._calculate_quality_scores(enriched_df)
        logger.info("Calculated neighborhood quality scores")
        
        # Add processing timestamp
        enriched_df = self.add_processing_timestamp(enriched_df)
        
        # Validate enrichment
        return self.validate_enrichment(enriched_df, initial_count, "Neighborhood")
    
    
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
        )

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
                col("neighborhood_quality_score") >= 0.5,
                lit("validated")
            ).when(
                col("neighborhood_quality_score") < 0.5,
                lit("low_quality")
            ).otherwise(lit("pending"))
        )
        
        return df_with_validation
    
    def _enhance_with_location_hierarchy(self, df: DataFrame) -> DataFrame:
        """
        Enhance neighborhoods with location hierarchy and parent relationships.
        
        Args:
            df: Neighborhood DataFrame to enhance
            
        Returns:
            DataFrame with location hierarchy enhancements
        """
        try:
            # Neighborhoods already have city and state columns directly
            # Enhance with hierarchy (adds county information)
            enhanced_df = self.location_enricher.enhance_with_hierarchy(df, "city", "state")
            
            # Rename county_resolved to county for consistency with graph model
            if "county_resolved" in enhanced_df.columns:
                enhanced_df = enhanced_df.withColumnRenamed("county_resolved", "county")
            
            # Standardize location names 
            enhanced_df = self.location_enricher.standardize_location_names(
                enhanced_df, "city", "state", "name"
            )
            
            # Normalize state names from abbreviations to full names
            enhanced_df = self.location_enricher.normalize_state_names(enhanced_df, "state")
            
            # Establish parent relationships if configured
            if True:
                enhanced_df = self.location_enricher.establish_parent_relationships(enhanced_df)
            
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to enhance neighborhoods with location hierarchy: {e}")
            # Return original DataFrame if enhancement fails
            return df
    
    def get_enrichment_statistics(self, df: DataFrame) -> Dict[str, Any]:
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
    
    def calculate_knowledge_score(self, df: DataFrame, wikipedia_df: Optional[DataFrame] = None) -> DataFrame:
        """
        Calculate knowledge score based on Wikipedia coverage for neighborhoods.
        
        Args:
            df: Neighborhood DataFrame
            wikipedia_df: Optional Wikipedia DataFrame with page summaries
            
        Returns:
            DataFrame with knowledge_score and wikipedia_count columns
        """
        from pyspark.sql.functions import count, sum as spark_sum, avg, max as spark_max
        
        # If no Wikipedia data provided, set default scores
        if wikipedia_df is None:
            logger.warning("No Wikipedia data provided for knowledge score calculation")
            return df.withColumn("knowledge_score", lit(0.0)) \
                     .withColumn("wikipedia_count", lit(0))
        
        # Count Wikipedia articles per neighborhood based on location matching
        # Match on city and state to find related articles
        wiki_counts = wikipedia_df.filter(
            col("best_city").isNotNull() & 
            col("best_state").isNotNull()
        ).groupBy("best_city", "best_state").agg(
            count("page_id").alias("wiki_article_count")
        )
        
        # Join with neighborhoods
        df_with_wiki = df.join(
            wiki_counts,
            (df["city"] == wiki_counts["best_city"]) & 
            (df["state"] == wiki_counts["best_state"]),
            "left"
        ).drop("best_city", "best_state")
        
        # Calculate knowledge score
        # Formula: based on article count only
        df_with_score = df_with_wiki.withColumn(
            "wikipedia_count",
            coalesce(col("wiki_article_count"), lit(0))
        ).withColumn(
            "knowledge_score",
            when(col("wiki_article_count").isNotNull(),
                 # Score based on article count (max 1.0)
                 least(col("wiki_article_count") / 10.0, lit(1.0))
            ).otherwise(lit(0.0))
        ).withColumn(
            "knowledge_score",
            # Ensure score is between 0 and 1
            least(col("knowledge_score"), lit(1.0))
        )
        
        # Drop intermediate columns
        df_with_score = df_with_score.drop(
            "wiki_article_count"
        )
        
        return df_with_score
    
    def aggregate_wikipedia_topics(self, df: DataFrame, wikipedia_df: Optional[DataFrame] = None) -> DataFrame:
        """
        Aggregate Wikipedia topics for neighborhoods from related articles.
        
        Args:
            df: Neighborhood DataFrame
            wikipedia_df: Optional Wikipedia DataFrame with key_topics
            
        Returns:
            DataFrame with aggregated_topics column
        """
        from pyspark.sql.functions import collect_set, flatten, array_distinct, split
        
        # If no Wikipedia data provided, add empty topics
        if wikipedia_df is None:
            logger.warning("No Wikipedia data provided for topic aggregation")
            return df.withColumn("aggregated_topics", expr("array()"))
        
        # Prepare Wikipedia topics (handle both string and array formats)
        wiki_with_topics = wikipedia_df.filter(
            col("key_topics").isNotNull() & 
            col("best_city").isNotNull() & 
            col("best_state").isNotNull()
        ).withColumn(
            "topics_array",
            when(col("key_topics").rlike("^\\[.*\\]$"),
                 # If it's a JSON array string, parse it
                 expr("from_json(key_topics, 'array<string>')")
            ).otherwise(
                 # If it's a comma-separated string, split it
                 split(col("key_topics"), ",")
            )
        ).withColumn(
            "topics_array",
            expr("transform(topics_array, x -> trim(x))")
        )
        
        # Aggregate topics by city/state
        topics_by_location = wiki_with_topics.groupBy("best_city", "best_state").agg(
            flatten(collect_set("topics_array")).alias("all_topics")
        ).withColumn(
            "aggregated_topics",
            array_distinct(col("all_topics"))
        )
        
        # Join with neighborhoods
        df_with_topics = df.join(
            topics_by_location,
            (df["city"] == topics_by_location["best_city"]) & 
            (df["state"] == topics_by_location["best_state"]),
            "left"
        ).drop("best_city", "best_state", "all_topics")
        
        # Handle null topics
        df_with_topics = df_with_topics.withColumn(
            "aggregated_topics",
            coalesce(col("aggregated_topics"), expr("array()"))
        )
        
        return df_with_topics
    
    def enrich_with_wikipedia_data(self, df: DataFrame, wikipedia_df: Optional[DataFrame] = None) -> DataFrame:
        """
        Enrich neighborhoods with Wikipedia knowledge scores and topics.
        
        Args:
            df: Neighborhood DataFrame
            wikipedia_df: Optional Wikipedia DataFrame
            
        Returns:
            DataFrame enriched with Wikipedia data
        """
        if wikipedia_df is None:
            logger.warning("No Wikipedia data available for neighborhood enrichment")
            return df.withColumn("knowledge_score", lit(0.0)) \
                     .withColumn("wikipedia_count", lit(0)) \
                     .withColumn("aggregated_topics", expr("array()"))
        
        # Calculate knowledge score
        df_with_score = self.calculate_knowledge_score(df, wikipedia_df)
        
        # Aggregate topics
        df_with_topics = self.aggregate_wikipedia_topics(df_with_score, wikipedia_df)
        
        logger.info("Enriched neighborhoods with Wikipedia knowledge scores and topics")
        return df_with_topics