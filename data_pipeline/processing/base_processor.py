"""
Base processor classes for common text processing and embedding functionality.

Provides shared functionality for all entity-specific processors to reduce
code duplication and ensure consistent patterns.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    length,
    lit,
    regexp_replace,
    trim,
    when,
)

logger = logging.getLogger(__name__)


class BaseTextConfig(BaseModel):
    """Base configuration for text processing."""
    
    enable_cleaning: bool = Field(
        default=True,
        description="Enable text cleaning and normalization"
    )
    
    normalize_whitespace: bool = Field(
        default=True,
        description="Normalize whitespace characters"
    )
    
    remove_html_tags: bool = Field(
        default=True,
        description="Remove HTML tags from content"
    )


class BaseTextProcessor(ABC):
    """
    Abstract base class for entity-specific text processors.
    
    Provides common functionality like text cleaning, normalization,
    and length tracking.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[BaseTextConfig] = None):
        """
        Initialize the base text processor.
        
        Args:
            spark: Active SparkSession
            config: Text processing configuration
        """
        self.spark = spark
        self.config = config or self._get_default_config()
    
    @abstractmethod
    def _get_default_config(self) -> BaseTextConfig:
        """Get the default configuration for this processor type."""
        pass
    
    @abstractmethod
    def _build_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Build entity-specific embedding text.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with embedding_text column
        """
        pass
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Process text content for embeddings.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with embedding_text column added
        """
        entity_name = self.__class__.__name__.replace("TextProcessor", "").lower()
        logger.info(f"Processing {entity_name} text for embeddings")
        
        processed_df = df
        
        # Clean text fields if enabled
        if self.config.enable_cleaning:
            processed_df = self._clean_text_fields(processed_df)
        
        # Build entity-specific embedding text
        processed_df = self._build_embedding_text(processed_df)
        
        # Add text length for monitoring
        processed_df = self._add_text_length(processed_df)
        
        record_count = processed_df.count()
        logger.info(f"Processed text for {record_count} {entity_name} records")
        
        return processed_df
    
    def _clean_text_fields(self, df: DataFrame) -> DataFrame:
        """
        Clean text fields with common patterns.
        
        Subclasses should override for entity-specific cleaning.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with cleaned text fields
        """
        cleaned_df = df
        
        # Clean description field if it exists
        if "description" in df.columns:
            cleaned_df = self._clean_text_column(cleaned_df, "description", "description_cleaned")
        
        return cleaned_df
    
    def _clean_text_column(self, df: DataFrame, input_col: str, output_col: str) -> DataFrame:
        """
        Clean a single text column.
        
        Args:
            df: Input DataFrame
            input_col: Name of input column
            output_col: Name of output column
            
        Returns:
            DataFrame with cleaned column
        """
        result_df = df
        
        # Remove HTML tags if configured
        if self.config.remove_html_tags:
            result_df = result_df.withColumn(
                output_col,
                regexp_replace(col(input_col), "<[^>]+>", " ")
            )
        else:
            result_df = result_df.withColumn(output_col, col(input_col))
        
        # Normalize whitespace if configured
        if self.config.normalize_whitespace:
            result_df = result_df.withColumn(
                output_col,
                trim(regexp_replace(col(output_col), r"\s+", " "))
            )
        
        return result_df
    
    def _add_text_length(self, df: DataFrame) -> DataFrame:
        """
        Add text length column for monitoring.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embedding_text_length column
        """
        return df.withColumn(
            "embedding_text_length",
            when(col("embedding_text").isNotNull(), length(col("embedding_text")))
            .otherwise(lit(0))
        )
    
    def get_text_statistics(self, df: DataFrame) -> dict:
        """
        Calculate text statistics.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            Dictionary of statistics
        """
        from pyspark.sql.functions import avg, max as spark_max, min as spark_min
        
        if "embedding_text_length" not in df.columns:
            df = self._add_text_length(df)
        
        stats = df.select(
            avg(col("embedding_text_length")).alias("avg_length"),
            spark_max(col("embedding_text_length")).alias("max_length"),
            spark_min(col("embedding_text_length")).alias("min_length")
        ).collect()[0]
        
        return {
            "avg_length": float(stats["avg_length"]) if stats["avg_length"] else 0,
            "max_length": int(stats["max_length"]) if stats["max_length"] else 0,
            "min_length": int(stats["min_length"]) if stats["min_length"] else 0
        }