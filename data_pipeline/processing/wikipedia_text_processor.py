"""
Wikipedia-specific text processing for embedding preparation.

This module provides text processing specifically for Wikipedia articles,
preparing content for embedding generation with minimal processing since
the content is already optimized.
"""

import logging
from typing import Optional

from pydantic import Field
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    coalesce,
    col,
    concat_ws,
    expr,
    lit,
    when,
)

from .base_processor import BaseTextConfig, BaseTextProcessor

logger = logging.getLogger(__name__)


class WikipediaTextConfig(BaseTextConfig):
    """Configuration for Wikipedia text processing."""
    
    # Override defaults for Wikipedia
    enable_cleaning: bool = Field(
        default=False,  # Wikipedia summaries are pre-cleaned
        description="Enable text cleaning (usually not needed for Wikipedia)"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Include title and location metadata in embedding text"
    )
    


class WikipediaTextProcessor(BaseTextProcessor):
    """
    Processes Wikipedia text content for embedding generation.
    
    Optimized specifically for Wikipedia articles which already have
    well-structured, clean content. Minimal processing is needed.
    """
    
    def _get_default_config(self) -> WikipediaTextConfig:
        """Get the default configuration for Wikipedia text processor."""
        return WikipediaTextConfig()
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Process Wikipedia text content for embeddings.
        
        Wikipedia content is already optimized (long_summary ~985 chars avg),
        so minimal processing is needed.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            DataFrame with embedding_text column added
        """
        # Use base class process method
        processed_df = super().process(df)
        
        # Log additional Wikipedia-specific statistics
        stats = self.get_text_statistics(processed_df)
        logger.info(f"Average embedding text length: {stats['avg_length']:.0f} characters")
        
        return processed_df
    
    def _clean_text_fields(self, df: DataFrame) -> DataFrame:
        """
        Light cleaning for Wikipedia text fields.
        
        Usually not needed as Wikipedia summaries are pre-cleaned.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with cleaned text fields
        """
        cleaned_df = df
        
        # Clean long_summary and title if needed
        if "long_summary" in df.columns:
            cleaned_df = self._clean_text_column(cleaned_df, "long_summary", "long_summary_cleaned")
        
        if "title" in df.columns:
            cleaned_df = self._clean_text_column(cleaned_df, "title", "title_cleaned")
        
        return cleaned_df
    
    def _build_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Build embedding text for Wikipedia articles.
        
        For Wikipedia, we primarily use the long_summary field which is
        already optimized for embeddings (avg ~985 chars, max ~1873 chars).
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with embedding_text column
        """
        # Use long_summary directly - it's guaranteed to be available and optimized
        if self.config.include_metadata:
            # Add title and location for better search context
            components = []
            
            # Title (guaranteed to exist)
            if "title_cleaned" in df.columns:
                components.append(col("title_cleaned"))
            else:
                components.append(col("title"))
            
            # Location metadata
            if "best_city" in df.columns and "best_state" in df.columns:
                components.append(
                    concat_ws(", ",
                        when(col("best_city").isNotNull(), col("best_city")),
                        when(col("best_state").isNotNull(), col("best_state"))
                    )
                )
            
            # Main content (long_summary)
            if "long_summary_cleaned" in df.columns:
                components.append(col("long_summary_cleaned"))
            else:
                components.append(col("long_summary"))
            
            # Combine with separator
            embedding_text_expr = concat_ws(" | ", *[c for c in components if c is not None])
        else:
            # Just use long_summary directly
            if "long_summary_cleaned" in df.columns:
                embedding_text_expr = col("long_summary_cleaned")
            else:
                embedding_text_expr = col("long_summary")
        
        return df.withColumn(
            "embedding_text",
            when(col("embedding_text").isNull(), embedding_text_expr)
            .otherwise(col("embedding_text"))
        )
    
    def get_statistics(self, df: DataFrame) -> dict:
        """
        Get statistics about text processing.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Basic counts
        total = df.count()
        with_text = df.filter(col("embedding_text").isNotNull()).count()
        
        stats["total_articles"] = total
        stats["articles_with_embedding_text"] = with_text
        stats["coverage_percentage"] = (with_text / total * 100) if total > 0 else 0
        
        # Text length statistics
        if with_text > 0:
            length_stats = df.filter(col("embedding_text").isNotNull()).select(
                expr("avg(embedding_text_length) as avg_length"),
                expr("min(embedding_text_length) as min_length"),
                expr("max(embedding_text_length) as max_length"),
                expr("percentile_approx(embedding_text_length, 0.5) as median_length"),
                expr("percentile_approx(embedding_text_length, 0.95) as p95_length")
            ).collect()[0]
            
            stats["avg_text_length"] = length_stats["avg_length"]
            stats["min_text_length"] = length_stats["min_length"]
            stats["max_text_length"] = length_stats["max_length"]
            stats["median_text_length"] = length_stats["median_length"]
            stats["p95_text_length"] = length_stats["p95_length"]
        
        # Confidence score statistics (if available)
        if "confidence_score" in df.columns:
            confidence_stats = df.filter(col("confidence_score").isNotNull()).select(
                expr("avg(confidence_score) as avg_confidence"),
                expr("min(confidence_score) as min_confidence"),
                expr("max(confidence_score) as max_confidence")
            ).collect()[0]
            
            stats["avg_confidence_score"] = confidence_stats["avg_confidence"]
            stats["min_confidence_score"] = confidence_stats["min_confidence"]
            stats["max_confidence_score"] = confidence_stats["max_confidence"]
        
        # Location coverage
        if "best_city" in df.columns:
            with_city = df.filter(col("best_city").isNotNull()).count()
            stats["articles_with_city"] = with_city
            stats["city_coverage_percentage"] = (with_city / total * 100) if total > 0 else 0
        
        return stats