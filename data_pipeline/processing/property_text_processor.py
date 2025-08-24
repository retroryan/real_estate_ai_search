"""
Property-specific text processing for embedding preparation.

This module provides text processing specifically for property data,
preparing content for embedding generation with property-specific logic.
"""

import logging
from typing import Dict, Optional

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
    trim,
    when,
)

logger = logging.getLogger(__name__)


class PropertyTextConfig(BaseModel):
    """Configuration for property text processing."""
    
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
    
    max_description_length: int = Field(
        default=2000,
        ge=500,
        description="Maximum length for property descriptions in embedding text"
    )
    
    include_price: bool = Field(
        default=True,
        description="Include price in embedding text"
    )
    
    include_features: bool = Field(
        default=True,
        description="Include property features in embedding text"
    )


class PropertyTextProcessor:
    """
    Processes property text content for embedding generation.
    
    Optimized specifically for real estate property data,
    focusing on key searchable attributes.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[PropertyTextConfig] = None):
        """
        Initialize the property text processor.
        
        Args:
            spark: Active SparkSession
            config: Property text processing configuration
        """
        self.spark = spark
        self.config = config or PropertyTextConfig()
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Process property text content for embeddings.
        
        Args:
            df: Property DataFrame
            
        Returns:
            DataFrame with embedding_text column added
        """
        logger.info("Processing property text for embeddings")
        
        processed_df = df
        
        # Clean text fields if enabled
        if self.config.enable_cleaning:
            processed_df = self._clean_text_fields(processed_df)
        
        # Build property-specific embedding text
        processed_df = self._build_embedding_text(processed_df)
        
        # Add text length for monitoring
        processed_df = processed_df.withColumn(
            "embedding_text_length",
            when(col("embedding_text").isNotNull(), length(col("embedding_text")))
            .otherwise(lit(0))
        )
        
        logger.info(f"Processed text for {processed_df.count()} properties")
        return processed_df
    
    def _clean_text_fields(self, df: DataFrame) -> DataFrame:
        """
        Clean property text fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with cleaned text fields
        """
        cleaned_df = df
        
        # Clean description field
        if "description" in df.columns:
            if self.config.remove_html_tags:
                cleaned_df = cleaned_df.withColumn(
                    "description_cleaned",
                    regexp_replace(col("description"), "<[^>]+>", " ")
                )
            else:
                cleaned_df = cleaned_df.withColumn(
                    "description_cleaned", col("description")
                )
            
            if self.config.normalize_whitespace:
                cleaned_df = cleaned_df.withColumn(
                    "description_cleaned",
                    trim(regexp_replace(col("description_cleaned"), r"\s+", " "))
                )
        
        # Clean property_type field
        if "property_type" in df.columns:
            cleaned_df = cleaned_df.withColumn(
                "property_type_cleaned",
                trim(lower(col("property_type")))
            )
        
        return cleaned_df
    
    def _build_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Build embedding text optimized for property search.
        
        Args:
            df: Input DataFrame with cleaned fields
            
        Returns:
            DataFrame with embedding_text column
        """
        # Build components for embedding text
        components = []
        
        # Property type and basic info
        components.append(
            concat_ws(" ",
                lit("Property Type:"),
                coalesce(col("property_type_cleaned"), col("property_type"), lit("Unknown"))
            )
        )
        
        # Price information
        if self.config.include_price and "price" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Price:"),
                    when(col("price").isNotNull(), concat_ws("", lit("$"), col("price").cast("string")))
                    .otherwise(lit("Not listed"))
                )
            )
        
        # Bedrooms and bathrooms
        if "bedrooms" in df.columns:
            components.append(
                concat_ws(" ",
                    coalesce(col("bedrooms").cast("string"), lit("0")),
                    lit("bedrooms")
                )
            )
        
        if "bathrooms" in df.columns:
            components.append(
                concat_ws(" ",
                    coalesce(col("bathrooms").cast("string"), lit("0")),
                    lit("bathrooms")
                )
            )
        
        # Square footage
        if "square_feet" in df.columns:
            components.append(
                concat_ws(" ",
                    coalesce(col("square_feet").cast("string"), lit("Unknown")),
                    lit("square feet")
                )
            )
        
        # Location
        location_parts = []
        if "address" in df.columns:
            # Extract street from nested address structure
            location_parts.append(col("address.street"))
        if "city_normalized" in df.columns:
            location_parts.append(coalesce(col("city_normalized"), col("city")))
        elif "city" in df.columns:
            location_parts.append(col("city"))
        if "state_normalized" in df.columns:
            location_parts.append(coalesce(col("state_normalized"), col("state")))
        elif "state" in df.columns:
            location_parts.append(col("state"))
        
        if location_parts:
            components.append(
                concat_ws(" ",
                    lit("Located in"),
                    concat_ws(", ", *location_parts)
                )
            )
        
        # Features
        if self.config.include_features and "features" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Features:"),
                    when(col("features").isNotNull(), array_join(col("features"), ", "))
                    .otherwise(lit("Standard"))
                )
            )
        
        # Description (truncated if needed)
        if "description_cleaned" in df.columns:
            components.append(
                when(
                    length(col("description_cleaned")) > self.config.max_description_length,
                    concat_ws("", 
                        expr(f"substring(description_cleaned, 1, {self.config.max_description_length})"),
                        lit("...")
                    )
                ).otherwise(coalesce(col("description_cleaned"), col("description"), lit("")))
            )
        elif "description" in df.columns:
            components.append(
                when(
                    length(col("description")) > self.config.max_description_length,
                    concat_ws("",
                        expr(f"substring(description, 1, {self.config.max_description_length})"),
                        lit("...")
                    )
                ).otherwise(col("description"))
            )
        
        # Combine all components
        embedding_text_expr = concat_ws(" | ", *components)
        
        return df.withColumn("embedding_text", embedding_text_expr)
    
    def get_statistics(self, df: DataFrame) -> Dict:
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
        
        stats["total_properties"] = total
        stats["properties_with_embedding_text"] = with_text
        stats["coverage_percentage"] = (with_text / total * 100) if total > 0 else 0
        
        # Text length statistics
        if with_text > 0:
            length_stats = df.filter(col("embedding_text").isNotNull()).select(
                expr("avg(embedding_text_length) as avg_length"),
                expr("min(embedding_text_length) as min_length"),
                expr("max(embedding_text_length) as max_length")
            ).collect()[0]
            
            stats["avg_text_length"] = length_stats["avg_length"]
            stats["min_text_length"] = length_stats["min_length"]
            stats["max_text_length"] = length_stats["max_length"]
        
        return stats