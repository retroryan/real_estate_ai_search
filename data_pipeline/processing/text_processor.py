"""
Text processing pipeline for content preparation.

This module provides distributed text processing capabilities for preparing
content for embedding generation, using Spark's built-in functions for
optimal performance and Pydantic for configuration.
"""

import logging
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array_join,
    coalesce,
    col,
    concat_ws,
    expr,
    length,
    lit,
    lower,
    regexp_replace,
    split,
    trim,
    udf,
    when,
)
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

logger = logging.getLogger(__name__)


class ChunkingConfig(BaseModel):
    """Configuration for text chunking operations."""
    
    method: str = Field(
        default="simple",
        description="Chunking method: simple, semantic, or sentence"
    )
    
    chunk_size: int = Field(
        default=512,
        ge=100,
        le=2000,
        description="Target chunk size in characters"
    )
    
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Overlap between chunks in characters"
    )
    
    min_chunk_size: int = Field(
        default=100,
        ge=50,
        description="Minimum chunk size to keep"
    )


class TextProcessingConfig(BaseModel):
    """Configuration for text processing operations."""
    
    enable_cleaning: bool = Field(
        default=True,
        description="Enable text cleaning and normalization"
    )
    
    enable_chunking: bool = Field(
        default=True,
        description="Enable text chunking for embeddings"
    )
    
    remove_html_tags: bool = Field(
        default=True,
        description="Remove HTML tags from content"
    )
    
    normalize_whitespace: bool = Field(
        default=True,
        description="Normalize whitespace characters"
    )
    
    remove_special_chars: bool = Field(
        default=False,
        description="Remove special characters (keeps alphanumeric and basic punctuation)"
    )
    
    lowercase_text: bool = Field(
        default=False,
        description="Convert text to lowercase"
    )
    
    chunking_config: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Text chunking configuration"
    )
    
    max_embedding_text_length: int = Field(
        default=8000,
        ge=1000,
        description="Maximum length for embedding text"
    )


class TextProcessor:
    """
    Processes text content for embedding generation using Spark SQL.
    
    Follows Apache Spark best practices by minimizing UDF usage and
    leveraging built-in functions for text processing.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[TextProcessingConfig] = None):
        """
        Initialize the text processor.
        
        Args:
            spark: Active SparkSession
            config: Text processing configuration
        """
        self.spark = spark
        self.config = config or TextProcessingConfig()
        
        # Register minimal UDFs only when necessary
        if self.config.enable_chunking and self.config.chunking_config.method != "simple":
            self._register_chunking_udf()
    
    def _register_chunking_udf(self):
        """Register UDF for advanced chunking (only when needed)."""
        def chunk_text(text: str) -> List[str]:
            """Simple chunking implementation."""
            if not text:
                return []
            
            chunks = []
            chunk_size = self.config.chunking_config.chunk_size
            overlap = self.config.chunking_config.chunk_overlap
            
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                
                if len(chunk) >= self.config.chunking_config.min_chunk_size:
                    chunks.append(chunk)
                
                start = end - overlap if overlap > 0 else end
            
            return chunks
        
        self.chunk_text_udf = udf(chunk_text, ArrayType(StringType()))
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Process text content in the DataFrame.
        
        Args:
            df: Input DataFrame with text content
            
        Returns:
            DataFrame with processed text ready for embedding generation
        """
        logger.info("Starting text processing")
        
        processed_df = df
        
        # Clean text content if enabled
        if self.config.enable_cleaning:
            processed_df = self._clean_text(processed_df)
            logger.info("Cleaned text content")
        
        # Prepare embedding text
        processed_df = self._prepare_embedding_text(processed_df)
        logger.info("Prepared embedding text")
        
        # Apply chunking if enabled (for future chunk-based embeddings)
        if self.config.enable_chunking:
            processed_df = self._add_chunk_metadata(processed_df)
            logger.info("Added chunking metadata")
        
        logger.info("Text processing completed")
        return processed_df
    
    def _clean_text(self, df: DataFrame) -> DataFrame:
        """
        Clean and normalize text content using Spark SQL functions.
        
        Uses native Spark functions for optimal performance.
        """
        # Start with the original DataFrame
        cleaned_df = df
        
        # Remove HTML tags using regexp_replace (Spark built-in)
        if self.config.remove_html_tags:
            cleaned_df = cleaned_df.withColumn(
                "content_cleaned",
                when(
                    col("content").isNotNull(),
                    regexp_replace(col("content"), "<[^>]+>", " ")
                ).otherwise(col("content"))
            )
        else:
            cleaned_df = cleaned_df.withColumn(
                "content_cleaned",
                col("content")
            )
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            cleaned_df = cleaned_df.withColumn(
                "content_cleaned",
                when(
                    col("content_cleaned").isNotNull(),
                    regexp_replace(
                        regexp_replace(
                            regexp_replace(col("content_cleaned"), r"\s+", " "),
                            r"^\s+", ""
                        ),
                        r"\s+$", ""
                    )
                ).otherwise(col("content_cleaned"))
            )
        
        # Remove special characters if configured
        if self.config.remove_special_chars:
            cleaned_df = cleaned_df.withColumn(
                "content_cleaned",
                when(
                    col("content_cleaned").isNotNull(),
                    regexp_replace(col("content_cleaned"), r"[^a-zA-Z0-9\s\.\,\!\?\-]", "")
                ).otherwise(col("content_cleaned"))
            )
        
        # Convert to lowercase if configured
        if self.config.lowercase_text:
            cleaned_df = cleaned_df.withColumn(
                "content_cleaned",
                when(
                    col("content_cleaned").isNotNull(),
                    lower(col("content_cleaned"))
                ).otherwise(col("content_cleaned"))
            )
        
        # Also clean title and description fields
        for field in ["title", "description", "summary"]:
            if self.config.normalize_whitespace:
                cleaned_df = cleaned_df.withColumn(
                    f"{field}_cleaned",
                    when(
                        col(field).isNotNull(),
                        trim(regexp_replace(col(field), r"\s+", " "))
                    ).otherwise(col(field))
                )
            else:
                cleaned_df = cleaned_df.withColumn(
                    f"{field}_cleaned",
                    col(field)
                )
        
        return cleaned_df
    
    def _prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare text for embedding generation.
        
        Creates a unified text representation optimized for embedding models.
        """
        # Build embedding text based on entity type using Spark SQL
        embedding_text_expr = when(
            col("entity_type") == "PROPERTY",
            concat_ws(
                " | ",
                coalesce(col("title_cleaned"), col("title"), lit("")),
                concat_ws(" ", 
                    lit("Property Type:"), coalesce(col("property_type"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Price:"), coalesce(col("price").cast("string"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Bedrooms:"), coalesce(col("bedrooms").cast("string"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Bathrooms:"), coalesce(col("bathrooms").cast("string"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Square Feet:"), coalesce(col("square_feet").cast("string"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Location:"), 
                    coalesce(col("city_normalized"), col("city"), lit("")),
                    coalesce(col("state_normalized"), col("state"), lit(""))
                ),
                concat_ws(" ",
                    lit("Features:"),
                    when(
                        col("features").isNotNull(),
                        array_join(col("features"), ", ")
                    ).otherwise(lit("None"))
                ),
                coalesce(col("description_cleaned"), col("description"), lit(""))
            )
        ).when(
            col("entity_type") == "WIKIPEDIA_ARTICLE",
            concat_ws(
                " | ",
                coalesce(col("title_cleaned"), col("title"), lit("")),
                concat_ws(" ",
                    lit("Location:"),
                    coalesce(col("city_normalized"), col("city"), lit("")),
                    coalesce(col("state_normalized"), col("state"), lit(""))
                ),
                coalesce(col("summary_cleaned"), col("summary"), lit("")),
                concat_ws(" ",
                    lit("Topics:"),
                    coalesce(col("key_topics"), lit(""))
                ),
                # Include truncated content for Wikipedia articles
                when(
                    col("content_cleaned").isNotNull(),
                    expr(f"substring(content_cleaned, 1, {self.config.max_embedding_text_length})")
                ).otherwise(
                    when(
                        col("content").isNotNull(),
                        expr(f"substring(content, 1, {self.config.max_embedding_text_length})")
                    ).otherwise(lit(""))
                )
            )
        ).when(
            col("entity_type") == "NEIGHBORHOOD",
            concat_ws(
                " | ",
                coalesce(col("title_cleaned"), col("title"), lit("")),
                concat_ws(" ",
                    lit("Location:"),
                    coalesce(col("city_normalized"), col("city"), lit("")),
                    coalesce(col("state_normalized"), col("state"), lit(""))
                ),
                concat_ws(" ",
                    lit("Amenities:"),
                    when(
                        col("features").isNotNull(),
                        array_join(col("features"), ", ")
                    ).otherwise(lit("None"))
                ),
                coalesce(col("description_cleaned"), col("description"), lit(""))
            )
        ).otherwise(
            # Fallback for any other entity types
            concat_ws(
                " | ",
                coalesce(col("title_cleaned"), col("title"), lit("")),
                coalesce(col("description_cleaned"), col("description"), lit("")),
                coalesce(col("summary_cleaned"), col("summary"), lit(""))
            )
        )
        
        # Apply the embedding text expression
        df_with_embedding = df.withColumn(
            "embedding_text",
            when(
                col("embedding_text").isNull(),
                embedding_text_expr
            ).otherwise(col("embedding_text"))
        )
        
        # Add text length for monitoring
        df_with_length = df_with_embedding.withColumn(
            "embedding_text_length",
            when(
                col("embedding_text").isNotNull(),
                length(col("embedding_text"))
            ).otherwise(lit(0))
        )
        
        return df_with_length
    
    def _add_chunk_metadata(self, df: DataFrame) -> DataFrame:
        """
        Add chunking metadata for future chunk-based processing.
        
        This prepares the data structure for chunk-based embeddings
        but doesn't actually create chunks yet (that happens in Phase 4).
        """
        # Calculate estimated number of chunks (for planning purposes)
        chunk_count_expr = when(
            col("embedding_text_length") > 0,
            expr(f"ceiling(embedding_text_length / {self.config.chunking_config.chunk_size})")
        ).otherwise(lit(0))
        
        df_with_chunks = df.withColumn(
            "estimated_chunks",
            chunk_count_expr
        ).withColumn(
            "chunking_method",
            lit(self.config.chunking_config.method)
        ).withColumn(
            "chunk_size_config",
            lit(self.config.chunking_config.chunk_size)
        )
        
        return df_with_chunks
    
    def get_text_statistics(self, df: DataFrame) -> Dict:
        """
        Calculate statistics about text processing.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary of text processing statistics
        """
        stats = {}
        
        # Calculate text statistics using Spark SQL
        text_stats = df.select(
            expr("count(*) as total_records"),
            expr("count(embedding_text) as records_with_embedding_text"),
            expr("avg(embedding_text_length) as avg_text_length"),
            expr("min(embedding_text_length) as min_text_length"),
            expr("max(embedding_text_length) as max_text_length"),
            expr("sum(estimated_chunks) as total_estimated_chunks")
        ).collect()[0]
        
        stats["total_records"] = text_stats["total_records"]
        stats["records_with_embedding_text"] = text_stats["records_with_embedding_text"]
        stats["avg_text_length"] = text_stats["avg_text_length"]
        stats["min_text_length"] = text_stats["min_text_length"]
        stats["max_text_length"] = text_stats["max_text_length"]
        stats["total_estimated_chunks"] = text_stats["total_estimated_chunks"]
        
        # Get statistics by entity type
        entity_stats = df.groupBy("entity_type").agg(
            expr("avg(embedding_text_length) as avg_length"),
            expr("count(*) as count")
        ).collect()
        
        stats["entity_text_stats"] = {
            row["entity_type"]: {
                "avg_length": row["avg_length"],
                "count": row["count"]
            }
            for row in entity_stats
        }
        
        return stats