"""
Neighborhood-specific text processing for embedding preparation.

This module provides text processing specifically for neighborhood data,
preparing content for embedding generation with neighborhood-specific logic.
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
    regexp_replace,
    trim,
    when,
)

logger = logging.getLogger(__name__)


class NeighborhoodTextConfig(BaseModel):
    """Configuration for neighborhood text processing."""
    
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
        default=3000,
        ge=500,
        description="Maximum length for neighborhood descriptions"
    )
    
    include_demographics: bool = Field(
        default=True,
        description="Include demographic information in embedding text"
    )
    
    include_amenities: bool = Field(
        default=True,
        description="Include amenities and features in embedding text"
    )


class NeighborhoodTextProcessor:
    """
    Processes neighborhood text content for embedding generation.
    
    Optimized specifically for neighborhood and location data,
    focusing on amenities, demographics, and area characteristics.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[NeighborhoodTextConfig] = None):
        """
        Initialize the neighborhood text processor.
        
        Args:
            spark: Active SparkSession
            config: Neighborhood text processing configuration
        """
        self.spark = spark
        self.config = config or NeighborhoodTextConfig()
    
    def process(self, df: DataFrame) -> DataFrame:
        """
        Process neighborhood text content for embeddings.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            DataFrame with embedding_text column added
        """
        logger.info("Processing neighborhood text for embeddings")
        
        processed_df = df
        
        # Clean text fields if enabled
        if self.config.enable_cleaning:
            processed_df = self._clean_text_fields(processed_df)
        
        # Build neighborhood-specific embedding text
        processed_df = self._build_embedding_text(processed_df)
        
        # Add text length for monitoring
        processed_df = processed_df.withColumn(
            "embedding_text_length",
            when(col("embedding_text").isNotNull(), length(col("embedding_text")))
            .otherwise(lit(0))
        )
        
        logger.info(f"Processed text for {processed_df.count()} neighborhoods")
        return processed_df
    
    def _clean_text_fields(self, df: DataFrame) -> DataFrame:
        """
        Clean neighborhood text fields.
        
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
        
        # Clean neighborhood name
        if "neighborhood_name" in df.columns:
            cleaned_df = cleaned_df.withColumn(
                "neighborhood_name_cleaned",
                trim(col("neighborhood_name"))
            )
        elif "name" in df.columns:
            cleaned_df = cleaned_df.withColumn(
                "neighborhood_name_cleaned",
                trim(col("name"))
            )
        
        return cleaned_df
    
    def _build_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Build embedding text optimized for neighborhood search.
        
        Args:
            df: Input DataFrame with cleaned fields
            
        Returns:
            DataFrame with embedding_text column
        """
        # Build components for embedding text
        components = []
        
        # Neighborhood name
        if "neighborhood_name_cleaned" in df.columns:
            components.append(
                concat_ws(" ",
                    col("neighborhood_name_cleaned"),
                    lit("neighborhood")
                )
            )
        elif "neighborhood_name" in df.columns:
            components.append(
                concat_ws(" ",
                    col("neighborhood_name"),
                    lit("neighborhood")
                )
            )
        
        # Location
        location_parts = []
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
        
        # Demographics (if included)
        if self.config.include_demographics:
            if "population" in df.columns:
                components.append(
                    concat_ws(" ",
                        lit("Population:"),
                        coalesce(col("population").cast("string"), lit("Unknown"))
                    )
                )
            
            if "median_income" in df.columns:
                components.append(
                    concat_ws(" ",
                        lit("Median income:"),
                        when(col("median_income").isNotNull(),
                             concat_ws("", lit("$"), col("median_income").cast("string")))
                        .otherwise(lit("Not available"))
                    )
                )
            
            if "median_age" in df.columns:
                components.append(
                    concat_ws(" ",
                        lit("Median age:"),
                        coalesce(col("median_age").cast("string"), lit("Not available"))
                    )
                )
        
        # Amenities and features
        if self.config.include_amenities and "features" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Amenities and features:"),
                    when(col("features").isNotNull(), array_join(col("features"), ", "))
                    .otherwise(lit("Residential area"))
                )
            )
        
        # Schools (if available)
        if "schools" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Schools:"),
                    when(col("schools").isNotNull(), array_join(col("schools"), ", "))
                    .otherwise(lit("School information not available"))
                )
            )
        
        # Transportation
        if "transit_score" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Transit score:"),
                    coalesce(col("transit_score").cast("string"), lit("Not rated"))
                )
            )
        
        if "walk_score" in df.columns:
            components.append(
                concat_ws(" ",
                    lit("Walk score:"),
                    coalesce(col("walk_score").cast("string"), lit("Not rated"))
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
        
        stats["total_neighborhoods"] = total
        stats["neighborhoods_with_embedding_text"] = with_text
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
        
        # Feature statistics
        if "features" in df.columns:
            with_features = df.filter(
                col("features").isNotNull() & (expr("size(features)") > 0)
            ).count()
            stats["neighborhoods_with_features"] = with_features
        
        return stats