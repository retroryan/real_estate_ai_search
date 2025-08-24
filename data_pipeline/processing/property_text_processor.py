"""
Property-specific text processing for embedding preparation.

This module provides text processing specifically for property data,
preparing content for embedding generation with property-specific logic.
"""

import logging
from typing import Optional

from pydantic import Field
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    array_join,
    coalesce,
    col,
    concat_ws,
    expr,
    length,
    lit,
    lower,
    trim,
    when,
)

from .base_processor import BaseTextConfig, BaseTextProcessor

logger = logging.getLogger(__name__)


class PropertyTextConfig(BaseTextConfig):
    """Configuration for property text processing."""
    
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


class PropertyTextProcessor(BaseTextProcessor):
    """
    Processes property text content for embedding generation.
    
    Optimized specifically for real estate property data,
    focusing on key searchable attributes.
    """
    
    def _get_default_config(self) -> PropertyTextConfig:
        """Get the default configuration for property text processor."""
        return PropertyTextConfig()
    
    
    def _clean_text_fields(self, df: DataFrame) -> DataFrame:
        """
        Clean property text fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with cleaned text fields
        """
        cleaned_df = df
        
        # Use base class method for description
        cleaned_df = super()._clean_text_fields(df)
        
        # Clean additional property-specific fields
        if "description" in df.columns:
            cleaned_df = self._clean_text_column(cleaned_df, "description", "description_cleaned")
        
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