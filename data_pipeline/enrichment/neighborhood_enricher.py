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
    avg,
    size,
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
        
        # Override location enricher initialization - always enabled if location broadcast available
        if self.location_broadcast:
            from .location_enricher import LocationEnricher
            self.location_enricher = LocationEnricher(spark, location_broadcast)
    
    
    def set_location_data(self, location_broadcast: Any):
        """
        Set location broadcast data and create LocationEnricher after initialization.
        
        Args:
            location_broadcast: Broadcast variable containing location reference data
        """
        super().set_location_data(location_broadcast)
        
        if self.location_broadcast:
            from .location_enricher import LocationEnricher
            self.location_enricher = LocationEnricher(self.spark, location_broadcast)
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
        
        enriched_df = df
        
        # Add correlation IDs - always enabled
        enriched_df = self.add_correlation_ids(enriched_df, "neighborhood_correlation_id")
        logger.info("Added correlation IDs to neighborhoods")
        
        # Preserve and process Wikipedia correlations
        enriched_df = self._preserve_wikipedia_correlations(enriched_df)
        logger.info("Preserved Wikipedia correlations")
        
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
        
        # Calculate quality scores - always enabled
        enriched_df = self._calculate_quality_scores(enriched_df)
        logger.info("Calculated neighborhood quality scores")
        
        # Add Phase 2 fields (scores and timestamps)
        enriched_df = self._add_phase2_fields(enriched_df)
        logger.info("Added Phase 2 score fields")
        
        # Add processing timestamp
        enriched_df = self.add_processing_timestamp(enriched_df)
        
        # Validate enrichment
        return self.validate_enrichment(enriched_df, entity_name="Neighborhood")
    
    
    def _preserve_wikipedia_correlations(self, df: DataFrame) -> DataFrame:
        """
        Preserve Wikipedia correlations and calculate confidence metrics.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with preserved wikipedia_correlations and confidence metrics
        """
        # Check if wikipedia_correlations exists
        if "wikipedia_correlations" not in df.columns:
            logger.info("No wikipedia_correlations field found")
            return df.withColumn("wikipedia_confidence_avg", lit(0.0))
        
        # Simply add confidence metric without accessing nested fields that might be null
        # This avoids the VOID type error when the field is null
        df_with_confidence = df.withColumn(
            "wikipedia_confidence_avg",
            lit(0.0)  # Default to 0.0 for now, will be calculated properly when data is available
        )
        
        logger.info("Added Wikipedia confidence score field")
        return df_with_confidence
    
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
        # Validate population - access from nested demographics struct
        df_with_pop = df.withColumn(
            "population_validated",
            when((col("demographics.population").isNotNull()) & (col("demographics.population") >= 0),
                 col("demographics.population"))
            .otherwise(lit(None))
        )
        
        # Validate median income - access from nested demographics struct
        df_with_income = df_with_pop.withColumn(
            "median_income_validated",
            when((col("demographics.median_income").isNotNull()) & (col("demographics.median_income") >= 0),
                 col("demographics.median_income"))
            .otherwise(lit(None))
        )
        
        # Validate median age - access from nested demographics struct
        df_with_age = df_with_income.withColumn(
            "median_age_validated",
            when((col("demographics.median_age").isNotNull()) & 
                 (col("demographics.median_age") >= 0) & 
                 (col("demographics.median_age") <= 120),
                 col("demographics.median_age"))
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
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate neighborhood data quality scores including Wikipedia confidence.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with quality scores
        """
        # Check if wikipedia_confidence_avg exists
        has_wiki_confidence = "wikipedia_confidence_avg" in df.columns
        
        # Neighborhood-specific quality score calculation
        quality_expr = (
            # Essential fields (35% weight)
            (when(col("neighborhood_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("neighborhood_name_normalized").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("city").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("state").isNotNull(), 0.05).otherwise(0.0)) +
            
            # Demographics (20% weight)
            (when(col("population_validated").isNotNull(), 0.07).otherwise(0.0)) +
            (when(col("median_income_validated").isNotNull(), 0.07).otherwise(0.0)) +
            (when(col("median_age_validated").isNotNull(), 0.06).otherwise(0.0)) +
            
            # Amenities (15% weight)
            (when(col("amenities").isNotNull() & (expr("size(amenities)") > 0), 0.15).otherwise(0.0)) +
            
            # Description (15% weight)
            (when(col("description").isNotNull() & (col("description") != ""), 0.15).otherwise(0.0)) +
            
            # Wikipedia confidence (15% weight)
            (when(col("wikipedia_confidence_avg").isNotNull(), 
                  col("wikipedia_confidence_avg") * 0.15).otherwise(0.0) if has_wiki_confidence else 0.0)
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
    
    def _add_phase2_fields(self, df: DataFrame) -> DataFrame:
        """
        Add Phase 2 fields including score calculations and timestamps.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with Phase 2 fields
        """
        from pyspark.sql.functions import current_timestamp
        from data_pipeline.processing.score_calculator import ScoreCalculator
        
        # Add timestamps
        df_with_timestamps = df.withColumn("created_at", current_timestamp()) \
                               .withColumn("updated_at", current_timestamp())
        
        # Initialize score calculator with fixed Pandas UDFs
        score_calculator = ScoreCalculator(self.spark)
        
        # Add all lifestyle scores using the efficient Pandas UDF approach
        df_with_scores = score_calculator.add_lifestyle_scores(df_with_timestamps)
        
        # Add knowledge scores if Wikipedia data is available
        if "wikipedia_count" in df_with_scores.columns:
            df_with_scores = score_calculator.add_knowledge_scores(df_with_scores)
        else:
            # Set knowledge score to 0 when Wikipedia data is not available
            df_with_scores = df_with_scores.withColumn("knowledge_score", lit(0.0))
        
        return df_with_scores
    
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
        Get enrichment metadata without forcing evaluation.
        
        Note: This method is deprecated and not used in the pipeline.
        Kept for backward compatibility only.
        
        Args:
            df: Enriched DataFrame
            
        Returns:
            Dictionary of metadata
        """
        return super().get_enrichment_statistics(df)
    
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