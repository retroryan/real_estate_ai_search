"""
Wikipedia-specific data enrichment engine.

This module provides enrichment capabilities specifically for Wikipedia articles,
including location extraction, relevance scoring, and confidence metrics.
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
    length,
    lit,
    trim,
    when,
)

from .base_enricher import BaseEnricher

logger = logging.getLogger(__name__)


class WikipediaEnricher(BaseEnricher):
    """
    Enriches Wikipedia article data with location references, relevance scores,
    and confidence metrics specific to geographic content.
    """
    
    def __init__(self, spark: SparkSession,
                 location_broadcast: Optional[Any] = None):
        """
        Initialize the Wikipedia enricher.
        
        Args:
            spark: Active SparkSession
            location_broadcast: Broadcast variable containing location reference data
        """
        super().__init__(spark, location_broadcast)
        
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
            logger.info("LocationEnricher initialized for Wikipedia articles with broadcast data")
    
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply Wikipedia-specific enrichments.
        
        Note: Wikipedia articles are already well-structured with extracted
        location data (best_city, best_state) and confidence scores from
        the summarization process.
        
        Args:
            df: Wikipedia DataFrame to enrich
            
        Returns:
            Enriched Wikipedia DataFrame
        """
        logger.info("Starting Wikipedia article enrichment process")
        
        enriched_df = df
        
        # Add correlation IDs - always enabled
        enriched_df = self.add_correlation_ids(enriched_df, "article_correlation_id")
        logger.info("Added correlation IDs to articles")
        
        # Validate and enrich location data - always enabled
        enriched_df = self._validate_locations(enriched_df)
        logger.info("Validated location references")
        
        # Enhance with canonical location matching and geographic context - always enabled if location enricher available
        if self.location_enricher:
            enriched_df = self._enhance_with_location_data(enriched_df)
            logger.info("Enhanced articles with canonical location data")
        
        # Add location-specific organization - always enabled
        enriched_df = self._organize_by_location(enriched_df)
        logger.info("Added location-specific organization")
        
        # Calculate relevance scores - always enabled
        enriched_df = self._calculate_relevance_scores(enriched_df)
        logger.info("Calculated relevance scores")
        
        
        # Calculate quality scores - always enabled
        enriched_df = self._calculate_quality_scores(enriched_df)
        logger.info("Calculated article quality scores")
        
        # Add Phase 2 fields (metadata and timestamps)
        enriched_df = self._add_phase2_fields(enriched_df)
        logger.info("Added Phase 2 metadata fields")
        
        # Add processing timestamp
        enriched_df = self.add_processing_timestamp(enriched_df)
        
        # Validate enrichment
        return self.validate_enrichment(enriched_df, entity_name="Wikipedia article")
    
    
    def _validate_locations(self, df: DataFrame) -> DataFrame:
        """
        Validate and enrich location data.
        
        Wikipedia articles already have best_city and best_state extracted
        during summarization, so we validate and enhance these.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with validated location fields
        """
        # Validate extracted locations
        df_with_location_check = df.withColumn(
            "has_valid_location",
            when(
                col("best_city").isNotNull() | col("best_state").isNotNull(),
                lit(True)
            ).otherwise(lit(False))
        )
        
        # Normalize location fields
        df_with_normalized = df_with_location_check.withColumn(
            "city_validated",
            when(
                col("best_city").isNotNull(),
                trim(col("best_city"))
            ).otherwise(lit(None))
        ).withColumn(
            "state_validated",
            when(
                col("best_state").isNotNull(),
                trim(col("best_state"))
            ).otherwise(lit(None))
        )
        
        # Add location specificity level
        df_with_specificity = df_with_normalized.withColumn(
            "location_specificity",
            when(
                col("city_validated").isNotNull() & col("state_validated").isNotNull(),
                lit("city_and_state")
            ).when(
                col("state_validated").isNotNull(),
                lit("state_only")
            ).when(
                col("city_validated").isNotNull(),
                lit("city_only")
            ).otherwise(lit("none"))
        )
        
        return df_with_specificity
    
    def _calculate_relevance_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate article relevance scores for location-based content.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with relevance scores
        """
        # Calculate relevance based on multiple factors
        relevance_expr = (
            # Location relevance (60% weight)
            when(col("has_valid_location") == True, 0.6)
            .otherwise(0.0)
        ) + (
            # Content quality indicators (40% weight)
            when(col("long_summary").isNotNull() & 
                 (length(col("long_summary")) > 500), 0.2)
            .otherwise(0.0) +
            when(col("key_topics").isNotNull() & 
                 (expr("size(key_topics)") > 0), 0.2)
            .otherwise(0.0)
        )
        
        # Apply relevance score
        df_with_relevance = df.withColumn(
            "location_relevance_score",
            relevance_expr.cast("decimal(3,2)")
        )
        
        # Add relevance category
        df_with_category = df_with_relevance.withColumn(
            "relevance_category",
            when(col("location_relevance_score") >= 0.8, lit("highly_relevant"))
            .when(col("location_relevance_score") >= 0.6, lit("relevant"))
            .when(col("location_relevance_score") >= 0.4, lit("somewhat_relevant"))
            .otherwise(lit("low_relevance"))
        )
        
        return df_with_category
    
    
    def _enhance_with_location_data(self, df: DataFrame) -> DataFrame:
        """
        Enhance Wikipedia articles with canonical location data and geographic context.
        
        Args:
            df: Wikipedia DataFrame to enhance
            
        Returns:
            DataFrame with location enhancements
        """
        try:
            # Use already extracted location fields (best_city, best_state)
            # Enhance with hierarchy (adds county information)
            enhanced_df = self.location_enricher.enhance_with_hierarchy(df, "best_city", "best_state")
            
            # Rename county_resolved to county for consistency with graph model
            if "county_resolved" in enhanced_df.columns:
                enhanced_df = enhanced_df.withColumnRenamed("county_resolved", "county")
            
            # Standardize location names using canonical reference data
            enhanced_df = self.location_enricher.standardize_location_names(
                enhanced_df, "best_city", "best_state", "title"
            )
            
            # Normalize state names from abbreviations to full names
            enhanced_df = self.location_enricher.normalize_state_names(enhanced_df, "best_state")
            
            # Add geographic context fields - always enabled
            enhanced_df = self._add_geographic_context(enhanced_df)
            
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to enhance articles with location data: {e}")
            # Return original DataFrame if enhancement fails
            return df
    
    def _add_geographic_context(self, df: DataFrame) -> DataFrame:
        """
        Add geographic context fields to Wikipedia articles.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with geographic context fields
        """
        # Add location hierarchy context
        df_with_context = df.withColumn(
            "geographic_scope",
            when(
                col("best_city").isNotNull() & col("best_state").isNotNull(),
                lit("city")
            ).when(
                col("best_state").isNotNull(),
                lit("state")
            ).otherwise(lit("unspecified"))
        )
        
        # Add administrative level
        df_with_admin = df_with_context.withColumn(
            "administrative_level",
            when(col("best_city").isNotNull(), lit("municipal"))
            .when(col("best_state").isNotNull(), lit("state"))
            .otherwise(lit("unknown"))
        )
        
        # Create location context summary
        df_with_summary = df_with_admin.withColumn(
            "location_context",
            when(
                col("best_city").isNotNull() & col("best_state").isNotNull(),
                expr("concat(best_city, ', ', best_state)")
            ).when(
                col("best_state").isNotNull(),
                col("best_state")
            ).otherwise(lit("General"))
        )
        
        return df_with_summary
    
    def _organize_by_location(self, df: DataFrame) -> DataFrame:
        """
        Add location-specific content organization fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with organization fields
        """
        # First, ensure geographic_scope column exists
        df_with_scope = df.withColumn(
            "geographic_scope",
            when(
                col("best_city").isNotNull() & col("best_state").isNotNull(),
                lit("city")
            ).when(
                col("best_state").isNotNull(),
                lit("state")
            ).otherwise(lit("general"))
        )
        
        # Create location-based content categories
        df_with_category = df_with_scope.withColumn(
            "content_category",
            when(
                col("geographic_scope") == "city",
                lit("local_content")
            ).when(
                col("geographic_scope") == "state",
                lit("regional_content")
            ).otherwise(lit("general_content"))
        )
        
        # Add content organization key for grouping
        df_with_key = df_with_category.withColumn(
            "organization_key",
            when(
                col("best_state").isNotNull(),
                expr("concat('state_', best_state)")
            ).otherwise(lit("general"))
        )
        
        # Add searchability score for location-based queries
        df_with_searchability = df_with_key.withColumn(
            "location_searchability",
            (
                when(col("best_city").isNotNull(), 0.4).otherwise(0.0) +
                when(col("best_state").isNotNull(), 0.3).otherwise(0.0) +
                0.1
            ).cast("decimal(3,2)")
        )
        
        return df_with_searchability
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate Wikipedia article quality scores.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with quality scores
        """
        # Wikipedia-specific quality score calculation
        quality_expr = (
            # Essential fields (35% weight)
            (when(col("page_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("title").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("url").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("long_summary").isNotNull() & 
                  (length(col("long_summary")) > 100), 0.1).otherwise(0.0)) +
            
            # Location data (30% weight)
            (when(col("has_valid_location") == True, 0.30).otherwise(0.0)) +
            
            # Content richness (20% weight)
            (when(col("key_topics").isNotNull() & 
                  (expr("size(key_topics)") > 0), 0.1).otherwise(0.0)) +
            (when(col("long_summary").isNotNull() & 
                  (length(col("long_summary")) > 200), 0.1).otherwise(0.0)) +
            
            # Metadata (15% weight)
            (when(col("categories").isNotNull() & 
                  (expr("size(categories)") > 0), 0.075).otherwise(0.0)) +
            (when(col("relevance_score").isNotNull() & 
                  (col("relevance_score") > 0), 0.075).otherwise(0.0))
        )
        
        # Apply quality score
        df_with_quality = df.withColumn(
            "article_quality_score",
            quality_expr.cast("decimal(3,2)")
        )

        return df_with_quality
    
    def _add_phase2_fields(self, df: DataFrame) -> DataFrame:
        """
        Add Phase 2 fields including metadata and timestamps.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with Phase 2 fields
        """
        from pyspark.sql.functions import current_timestamp, size, when, coalesce
        from data_pipeline.processing.score_calculator import ScoreCalculator
        
        # Add timestamps
        df_with_timestamps = df.withColumn("created_at", current_timestamp()) \
                               .withColumn("updated_at", current_timestamp())
        
        # Add content metadata fields
        df_with_metadata = df_with_timestamps.withColumn(
            "content_length",
            when(col("long_summary").isNotNull(),
                 length(col("long_summary")))
            .otherwise(lit(None))
        ).withColumn(
            "topic_count",
            when(col("key_topics").isNotNull(),
                 size(col("key_topics")))
            .otherwise(lit(0))
        )
        
        # Add confidence scores (using existing relevance_score as extraction_confidence)
        df_with_confidence = df_with_metadata.withColumn(
            "extraction_confidence",
            coalesce(col("relevance_score"), lit(0.5))
        ).withColumn(
            "content_ratio",
            when(col("content_length") > 500, lit(0.8))
            .when(col("content_length") > 200, lit(0.6))
            .when(col("content_length") > 100, lit(0.4))
            .otherwise(lit(0.2))
        )
        
        # Add location_confidence if missing (set to 0.5 for Wikipedia articles)
        if "location_confidence" not in df_with_confidence.columns:
            df_with_confidence = df_with_confidence.withColumn("location_confidence", lit(0.5))
        
        # Initialize score calculator with fixed Pandas UDFs
        score_calculator = ScoreCalculator(self.spark)
        
        # Add confidence scores using the efficient Pandas UDF approach
        df_with_overall_confidence = score_calculator.add_confidence_scores(df_with_confidence)
        
        return df_with_overall_confidence
    
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