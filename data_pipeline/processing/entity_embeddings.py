"""
Entity-specific embedding generators with proper typing.

Each entity type has its own embedding logic without mixing concerns.
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array_join,
    coalesce,
    col,
    concat_ws,
    length,
    when,
)

from data_pipeline.config.models import PipelineConfig
from .base_embedding import BaseEmbeddingGenerator

logger = logging.getLogger(__name__)


class WikipediaEmbeddingGenerator(BaseEmbeddingGenerator):
    """Generate embeddings specifically for Wikipedia articles."""
    
    def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare Wikipedia text for embedding.
        
        Wikipedia articles use long_summary directly without additional formatting.
        
        Args:
            df: DataFrame with Wikipedia articles
            
        Returns:
            DataFrame with embedding_text column added
        """
        logger.info("Preparing Wikipedia text for embeddings")
        
        # For Wikipedia, embedding_text is simply the long_summary
        # No need for complex concatenation since long_summary is already optimized
        result_df = df.withColumn(
            "embedding_text",
            col("long_summary")
        )
        
        # Log statistics
        from pyspark.sql.functions import avg, max as spark_max, min as spark_min
        
        text_stats = result_df.select(
            avg(length(col("embedding_text"))).alias("avg_length"),
            spark_max(length(col("embedding_text"))).alias("max_length"),
            spark_min(length(col("embedding_text"))).alias("min_length")
        ).collect()[0]
        
        logger.info(f"Embedding text statistics - Avg: {text_stats['avg_length']:.0f}, Max: {text_stats['max_length']}, Min: {text_stats['min_length']} chars")
        
        return result_df
    


class PropertyEmbeddingGenerator(BaseEmbeddingGenerator):
    """Generate embeddings specifically for property listings."""
    
    def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare property text for embedding.
        
        Combines property attributes into a structured text representation.
        
        Args:
            df: DataFrame with property listings
            
        Returns:
            DataFrame with embedding_text column added
        """
        logger.info("Preparing property text for embeddings")
        
        # Build structured text representation for properties
        result_df = df.withColumn(
            "embedding_text",
            concat_ws(
                " | ",
                # Address and location
                concat_ws(" ", 
                    coalesce(col("street"), lit("")),
                    col("city"),
                    col("state"),
                    coalesce(col("zip_code"), lit(""))
                ),
                # Property type and price
                concat_ws(" ",
                    lit("Type:"), coalesce(col("property_type"), lit("N/A"))
                ),
                concat_ws(" ",
                    lit("Price: $"), coalesce(col("price").cast("string"), lit("N/A"))
                ),
                # Size and rooms
                concat_ws(" ",
                    coalesce(col("bedrooms").cast("string"), lit("0")), lit("BR"),
                    coalesce(col("bathrooms").cast("string"), lit("0")), lit("BA")
                ),
                concat_ws(" ",
                    coalesce(col("square_feet").cast("string"), lit("N/A")), lit("sqft")
                ),
                # Features
                when(
                    col("features").isNotNull() & (col("features").getItem(0).isNotNull()),
                    concat_ws(" ", lit("Features:"), array_join(col("features"), ", "))
                ).otherwise(lit("")),
                # Description
                coalesce(col("description"), lit(""))
            )
        )
        
        # Log statistics
        from pyspark.sql.functions import avg, max as spark_max, min as spark_min
        
        text_stats = result_df.select(
            avg(length(col("embedding_text"))).alias("avg_length"),
            spark_max(length(col("embedding_text"))).alias("max_length"),
            spark_min(length(col("embedding_text"))).alias("min_length")
        ).collect()[0]
        
        logger.info(f"Embedding text statistics - Avg: {text_stats['avg_length']:.0f}, Max: {text_stats['max_length']}, Min: {text_stats['min_length']} chars")
        
        return result_df
    


class NeighborhoodEmbeddingGenerator(BaseEmbeddingGenerator):
    """Generate embeddings specifically for neighborhoods."""
    
    def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare neighborhood text for embedding.
        
        Combines neighborhood attributes into a structured text representation.
        
        Args:
            df: DataFrame with neighborhoods
            
        Returns:
            DataFrame with embedding_text column added
        """
        logger.info("Preparing neighborhood text for embeddings")
        
        # Build structured text representation for neighborhoods
        result_df = df.withColumn(
            "embedding_text",
            concat_ws(
                " | ",
                # Name and location
                concat_ws(" - ", col("name"), col("city"), col("state")),
                # Demographics if available
                when(
                    col("population").isNotNull(),
                    concat_ws(" ", lit("Population:"), col("population").cast("string"))
                ).otherwise(lit("")),
                when(
                    col("median_income").isNotNull(),
                    concat_ws(" ", lit("Median Income: $"), col("median_income").cast("string"))
                ).otherwise(lit("")),
                # Amenities
                when(
                    col("amenities").isNotNull() & (col("amenities").getItem(0).isNotNull()),
                    concat_ws(" ", lit("Amenities:"), array_join(col("amenities"), ", "))
                ).otherwise(lit("")),
                # Points of interest
                when(
                    col("points_of_interest").isNotNull() & (col("points_of_interest").getItem(0).isNotNull()),
                    concat_ws(" ", lit("POIs:"), array_join(col("points_of_interest"), ", "))
                ).otherwise(lit("")),
                # Description
                coalesce(col("description"), lit(""))
            )
        )
        
        # Log statistics
        from pyspark.sql.functions import avg, max as spark_max, min as spark_min
        
        text_stats = result_df.select(
            avg(length(col("embedding_text"))).alias("avg_length"),
            spark_max(length(col("embedding_text"))).alias("max_length"),
            spark_min(length(col("embedding_text"))).alias("min_length")
        ).collect()[0]
        
        logger.info(f"Embedding text statistics - Avg: {text_stats['avg_length']:.0f}, Max: {text_stats['max_length']}, Min: {text_stats['min_length']} chars")
        
        return result_df
    
    # Use inherited generate_embeddings method from BaseEmbeddingGenerator
    # which already uses Pandas UDFs properly