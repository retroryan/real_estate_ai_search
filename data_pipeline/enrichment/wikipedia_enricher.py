"""
Wikipedia-specific data enrichment engine.

This module provides enrichment capabilities specifically for Wikipedia articles,
including location extraction, relevance scoring, and confidence metrics.
"""

import logging
import uuid
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    coalesce,
    col,
    current_timestamp,
    expr,
    length,
    lit,
    trim,
    udf,
    when,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class WikipediaEnrichmentConfig(BaseModel):
    """Configuration for Wikipedia enrichment operations."""
    
    enable_location_extraction: bool = Field(
        default=True,
        description="Extract and validate location references"
    )
    
    enable_relevance_scoring: bool = Field(
        default=True,
        description="Calculate article relevance scores"
    )
    
    enable_confidence_metrics: bool = Field(
        default=True,
        description="Add confidence metrics for extracted data"
    )
    
    enable_quality_scoring: bool = Field(
        default=True,
        description="Calculate article data quality scores"
    )
    
    enable_correlation_ids: bool = Field(
        default=True,
        description="Generate correlation IDs for tracking"
    )
    
    min_quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score for articles"
    )
    
    min_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for location extraction"
    )


class WikipediaEnricher:
    """
    Enriches Wikipedia article data with location references, relevance scores,
    and confidence metrics specific to geographic content.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[WikipediaEnrichmentConfig] = None):
        """
        Initialize the Wikipedia enricher.
        
        Args:
            spark: Active SparkSession
            config: Wikipedia enrichment configuration
        """
        self.spark = spark
        self.config = config or WikipediaEnrichmentConfig()
        
        # Register UDF for UUID generation
        self._register_udfs()
    
    def _register_udfs(self):
        """Register necessary UDFs."""
        def generate_uuid() -> str:
            return str(uuid.uuid4())
        
        self.generate_uuid_udf = udf(generate_uuid, StringType())
    
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
        
        initial_count = df.count()
        enriched_df = df
        
        # Add correlation IDs if configured
        if self.config.enable_correlation_ids:
            enriched_df = self._add_correlation_ids(enriched_df)
            logger.info("Added correlation IDs to articles")
        
        # Validate and enrich location data
        if self.config.enable_location_extraction:
            enriched_df = self._validate_locations(enriched_df)
            logger.info("Validated location references")
        
        # Calculate relevance scores
        if self.config.enable_relevance_scoring:
            enriched_df = self._calculate_relevance_scores(enriched_df)
            logger.info("Calculated relevance scores")
        
        # Add confidence metrics
        if self.config.enable_confidence_metrics:
            enriched_df = self._add_confidence_metrics(enriched_df)
            logger.info("Added confidence metrics")
        
        # Calculate quality scores
        if self.config.enable_quality_scoring:
            enriched_df = self._calculate_quality_scores(enriched_df)
            logger.info("Calculated article quality scores")
        
        # Add processing timestamp
        enriched_df = enriched_df.withColumn("processed_at", current_timestamp())
        
        # Validate enrichment
        final_count = enriched_df.count()
        if final_count != initial_count:
            logger.warning(f"Article count changed: {initial_count} -> {final_count}")
        
        logger.info(f"Wikipedia enrichment completed for {final_count} articles")
        return enriched_df
    
    def _add_correlation_ids(self, df: DataFrame) -> DataFrame:
        """Add correlation IDs for article tracking."""
        # Check if column already exists
        if "article_correlation_id" in df.columns:
            return df.withColumn(
                "article_correlation_id",
                when(col("article_correlation_id").isNull(), self.generate_uuid_udf())
                .otherwise(col("article_correlation_id"))
            )
        else:
            # Create new column
            return df.withColumn("article_correlation_id", self.generate_uuid_udf())
    
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
                (col("best_city").isNotNull() | col("best_state").isNotNull()) &
                (col("confidence_score") >= self.config.min_confidence_threshold),
                lit(True)
            ).otherwise(lit(False))
        )
        
        # Normalize location fields
        df_with_normalized = df_with_location_check.withColumn(
            "city_validated",
            when(
                col("best_city").isNotNull() & 
                (col("confidence_score") >= self.config.min_confidence_threshold),
                trim(col("best_city"))
            ).otherwise(lit(None))
        ).withColumn(
            "state_validated",
            when(
                col("best_state").isNotNull() &
                (col("confidence_score") >= self.config.min_confidence_threshold),
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
            # Location relevance (40% weight)
            when(col("has_valid_location") == True, 0.4)
            .otherwise(0.0)
        ) + (
            # Confidence score contribution (30% weight)
            when(col("confidence_score").isNotNull(),
                 col("confidence_score") * 0.3)
            .otherwise(0.0)
        ) + (
            # Content quality indicators (30% weight)
            when(col("long_summary").isNotNull() & 
                 (length(col("long_summary")) > 500), 0.15)
            .otherwise(0.0) +
            when(col("key_topics").isNotNull() & 
                 (expr("size(key_topics)") > 0), 0.15)
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
    
    def _add_confidence_metrics(self, df: DataFrame) -> DataFrame:
        """
        Add confidence metrics for extracted data.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with confidence metrics
        """
        # Categorize confidence levels
        df_with_confidence_level = df.withColumn(
            "confidence_level",
            when(col("confidence_score") >= 0.9, lit("very_high"))
            .when(col("confidence_score") >= 0.75, lit("high"))
            .when(col("confidence_score") >= 0.6, lit("medium"))
            .when(col("confidence_score") >= 0.4, lit("low"))
            .otherwise(lit("very_low"))
        )
        
        # Add extraction reliability flag
        df_with_reliability = df_with_confidence_level.withColumn(
            "extraction_reliable",
            when(col("confidence_score") >= self.config.min_confidence_threshold,
                 lit(True))
            .otherwise(lit(False))
        )
        
        # Calculate overall confidence (combining multiple signals)
        df_with_overall = df_with_reliability.withColumn(
            "overall_confidence",
            (
                coalesce(col("confidence_score"), lit(0.0)) * 0.6 +
                when(col("has_valid_location") == True, 0.2).otherwise(0.0) +
                when(col("key_topics").isNotNull(), 0.2).otherwise(0.0)
            ).cast("decimal(3,2)")
        )
        
        return df_with_overall
    
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
            (when(col("has_valid_location") == True, 0.15).otherwise(0.0)) +
            (when(col("confidence_score") >= self.config.min_confidence_threshold, 0.15)
             .otherwise(0.0)) +
            
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
        
        # Add validation status
        df_with_validation = df_with_quality.withColumn(
            "article_validation_status",
            when(
                col("article_quality_score") >= self.config.min_quality_score,
                lit("validated")
            ).when(
                col("article_quality_score") < self.config.min_quality_score,
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
        stats["total_articles"] = total
        
        # Location validation
        if "has_valid_location" in df.columns:
            with_location = df.filter(col("has_valid_location") == True).count()
            stats["articles_with_valid_location"] = with_location
            stats["location_coverage"] = (with_location / total * 100) if total > 0 else 0
        
        # Location specificity
        if "location_specificity" in df.columns:
            specificity_counts = df.groupBy("location_specificity").count().collect()
            stats["location_specificity"] = {
                row["location_specificity"]: row["count"] for row in specificity_counts
            }
        
        # Confidence metrics
        if "confidence_score" in df.columns:
            confidence_stats = df.select(
                expr("avg(confidence_score) as avg_confidence"),
                expr("min(confidence_score) as min_confidence"),
                expr("max(confidence_score) as max_confidence"),
                expr("count(case when extraction_reliable = true then 1 end) as reliable_count")
            ).collect()[0]
            
            stats["avg_confidence_score"] = float(confidence_stats["avg_confidence"]) if confidence_stats["avg_confidence"] else 0
            stats["min_confidence_score"] = float(confidence_stats["min_confidence"]) if confidence_stats["min_confidence"] else 0
            stats["max_confidence_score"] = float(confidence_stats["max_confidence"]) if confidence_stats["max_confidence"] else 0
            stats["reliable_extractions"] = confidence_stats["reliable_count"]
        
        # Relevance scores
        if "location_relevance_score" in df.columns:
            relevance_stats = df.select(
                expr("avg(location_relevance_score) as avg_relevance"),
                expr("count(case when relevance_category = 'highly_relevant' then 1 end) as highly_relevant"),
                expr("count(case when relevance_category = 'relevant' then 1 end) as relevant")
            ).collect()[0]
            
            stats["avg_relevance_score"] = float(relevance_stats["avg_relevance"]) if relevance_stats["avg_relevance"] else 0
            stats["highly_relevant_articles"] = relevance_stats["highly_relevant"]
            stats["relevant_articles"] = relevance_stats["relevant"]
        
        # Quality scores
        if "article_quality_score" in df.columns:
            quality_stats = df.select(
                expr("avg(article_quality_score) as avg_quality"),
                expr("count(case when article_validation_status = 'validated' then 1 end) as validated"),
                expr("count(case when article_validation_status = 'low_quality' then 1 end) as low_quality")
            ).collect()[0]
            
            stats["avg_quality_score"] = float(quality_stats["avg_quality"]) if quality_stats["avg_quality"] else 0
            stats["validated_articles"] = quality_stats["validated"]
            stats["low_quality_articles"] = quality_stats["low_quality"]
        
        # Content statistics
        if "long_summary" in df.columns:
            content_stats = df.filter(col("long_summary").isNotNull()).select(
                expr("avg(length(long_summary)) as avg_summary_length"),
                expr("min(length(long_summary)) as min_summary_length"),
                expr("max(length(long_summary)) as max_summary_length")
            ).collect()[0]
            
            stats["avg_summary_length"] = float(content_stats["avg_summary_length"]) if content_stats["avg_summary_length"] else 0
            stats["min_summary_length"] = content_stats["min_summary_length"]
            stats["max_summary_length"] = content_stats["max_summary_length"]
        
        return stats