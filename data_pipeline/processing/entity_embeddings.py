"""
Entity-specific embedding generators with proper typing.

Each entity type has its own embedding logic without mixing concerns.
"""

import logging
import time
from typing import List, Optional, Tuple
from uuid import uuid4

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    array_join,
    coalesce,
    col,
    concat_ws,
    current_timestamp,
    length,
    lit,
    pandas_udf,
    udf,
    when,
)
from pyspark.sql.types import ArrayType, DoubleType, IntegerType, StringType

from data_pipeline.config.models import EmbeddingConfig

logger = logging.getLogger(__name__)


class WikipediaEmbeddingGenerator:
    """Generate embeddings specifically for Wikipedia articles."""
    
    def __init__(self, spark, config: EmbeddingConfig):
        """
        Initialize Wikipedia embedding generator.
        
        Args:
            spark: SparkSession
            config: Embedding configuration
        """
        self.spark = spark
        self.config = config
        self.model_identifier = self._get_model_identifier()
        
        # Register UDFs
        self._register_udfs()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string."""
        from data_pipeline.config.models import ProviderType
        
        provider = self.config.provider
        
        if provider == ProviderType.OPENAI:
            return "text-embedding-3-small"
        elif provider == ProviderType.GEMINI:
            return "models/embedding-001"
        elif provider == ProviderType.OLLAMA:
            return "nomic-embed-text"
        elif provider == ProviderType.VOYAGE:
            return "voyage-2"
        else:
            return f"{provider.value}-embedding"
    
    def _register_udfs(self):
        """Register UDFs for embedding generation."""
        # Mock embedding function for testing
        def generate_mock_embedding(text: str) -> List[float]:
            """Generate a mock embedding for testing."""
            if not text:
                return None
            # Generate deterministic mock embedding based on text length
            dim = 384  # Common embedding dimension
            return [float(i % 10) / 10.0 for i in range(dim)]
        
        # Register as Spark UDF
        self.embedding_udf = udf(generate_mock_embedding, ArrayType(DoubleType()))
        
        # For production, you would use pandas_udf for batch processing
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def batch_generate_embeddings(texts):
            """Batch generate embeddings using the configured provider."""
            # This would call the actual embedding API
            # For now, return mock embeddings
            import pandas as pd
            return pd.Series([[float(i % 10) / 10.0 for i in range(384)] for _ in texts])
        
        self.batch_embedding_udf = batch_generate_embeddings
    
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
    
    def generate_embeddings(self, df: DataFrame) -> DataFrame:
        """
        Generate embeddings for Wikipedia articles.
        
        No chunking is applied since long_summary is already optimized.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embeddings added
        """
        start_time = time.time()
        logger.info(f"Generating Wikipedia embeddings using {self.model_identifier}")
        
        total_articles = df.count()
        logger.info(f"Processing {total_articles} Wikipedia articles")
        
        # Generate embeddings (using mock for testing, batch UDF for production)
        from data_pipeline.config.models import ProviderType
        if self.config.provider == ProviderType.OLLAMA:
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        else:
            # Use batch processing for production
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.batch_embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        
        # Add embedding metadata
        result_df = result_df.withColumn(
            "embedding_model",
            when(col("embedding").isNotNull(), lit(self.model_identifier))
        ).withColumn(
            "embedding_dimension",
            when(col("embedding").isNotNull(), lit(384))  # Would be dynamic in production
        ).withColumn(
            "embedded_at",
            when(col("embedding").isNotNull(), current_timestamp())
        )
        
        # Count successful embeddings
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        elapsed_time = time.time() - start_time
        
        logger.info(f"Generated {embedded_count}/{total_articles} embeddings in {elapsed_time:.2f} seconds")
        if embedded_count > 0:
            logger.info(f"Average time per embedding: {elapsed_time / embedded_count:.3f} seconds")
        
        return result_df


class PropertyEmbeddingGenerator:
    """Generate embeddings specifically for property listings."""
    
    def __init__(self, spark, config: EmbeddingConfig):
        """
        Initialize property embedding generator.
        
        Args:
            spark: SparkSession
            config: Embedding configuration
        """
        self.spark = spark
        self.config = config
        self.model_identifier = self._get_model_identifier()
        
        # Register UDFs
        self._register_udfs()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string."""
        from data_pipeline.config.models import ProviderType
        
        provider = self.config.provider
        
        if provider == ProviderType.OPENAI:
            return "text-embedding-3-small"
        elif provider == ProviderType.GEMINI:
            return "models/embedding-001"
        elif provider == ProviderType.OLLAMA:
            return "nomic-embed-text"
        elif provider == ProviderType.VOYAGE:
            return "voyage-2"
        else:
            return f"{provider.value}-embedding"
    
    def _register_udfs(self):
        """Register UDFs for embedding generation."""
        # Mock embedding function for testing
        def generate_mock_embedding(text: str) -> List[float]:
            """Generate a mock embedding for testing."""
            if not text:
                return None
            # Generate deterministic mock embedding based on text length
            dim = 384  # Common embedding dimension
            return [float(i % 10) / 10.0 for i in range(dim)]
        
        # Register as Spark UDF
        self.embedding_udf = udf(generate_mock_embedding, ArrayType(DoubleType()))
        
        # For production, you would use pandas_udf for batch processing
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def batch_generate_embeddings(texts):
            """Batch generate embeddings using the configured provider."""
            # This would call the actual embedding API
            # For now, return mock embeddings
            import pandas as pd
            return pd.Series([[float(i % 10) / 10.0 for i in range(384)] for _ in texts])
        
        self.batch_embedding_udf = batch_generate_embeddings
    
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
    
    def generate_embeddings(self, df: DataFrame) -> DataFrame:
        """
        Generate embeddings for property listings.
        
        Properties typically have short descriptions that don't need chunking.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embeddings added
        """
        start_time = time.time()
        logger.info(f"Generating property embeddings using {self.model_identifier}")
        
        total_properties = df.count()
        logger.info(f"Processing {total_properties} property listings")
        
        # Generate embeddings (using mock for testing, batch UDF for production)
        from data_pipeline.config.models import ProviderType
        if self.config.provider == ProviderType.OLLAMA:
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        else:
            # Use batch processing for production
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.batch_embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        
        # Add embedding metadata
        result_df = result_df.withColumn(
            "embedding_model",
            when(col("embedding").isNotNull(), lit(self.model_identifier))
        ).withColumn(
            "embedding_dimension",
            when(col("embedding").isNotNull(), lit(384))  # Would be dynamic in production
        ).withColumn(
            "embedded_at",
            when(col("embedding").isNotNull(), current_timestamp())
        )
        
        # Count successful embeddings
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        elapsed_time = time.time() - start_time
        
        logger.info(f"Generated {embedded_count}/{total_properties} embeddings in {elapsed_time:.2f} seconds")
        if embedded_count > 0:
            logger.info(f"Average time per embedding: {elapsed_time / embedded_count:.3f} seconds")
        
        return result_df


class NeighborhoodEmbeddingGenerator:
    """Generate embeddings specifically for neighborhoods."""
    
    def __init__(self, spark, config: EmbeddingConfig):
        """
        Initialize neighborhood embedding generator.
        
        Args:
            spark: SparkSession
            config: Embedding configuration
        """
        self.spark = spark
        self.config = config
        self.model_identifier = self._get_model_identifier()
        
        # Register UDFs
        self._register_udfs()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string."""
        from data_pipeline.config.models import ProviderType
        
        provider = self.config.provider
        
        if provider == ProviderType.OPENAI:
            return "text-embedding-3-small"
        elif provider == ProviderType.GEMINI:
            return "models/embedding-001"
        elif provider == ProviderType.OLLAMA:
            return "nomic-embed-text"
        elif provider == ProviderType.VOYAGE:
            return "voyage-2"
        else:
            return f"{provider.value}-embedding"
    
    def _register_udfs(self):
        """Register UDFs for embedding generation."""
        # Mock embedding function for testing
        def generate_mock_embedding(text: str) -> List[float]:
            """Generate a mock embedding for testing."""
            if not text:
                return None
            # Generate deterministic mock embedding based on text length
            dim = 384  # Common embedding dimension
            return [float(i % 10) / 10.0 for i in range(dim)]
        
        # Register as Spark UDF
        self.embedding_udf = udf(generate_mock_embedding, ArrayType(DoubleType()))
        
        # For production, you would use pandas_udf for batch processing
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def batch_generate_embeddings(texts):
            """Batch generate embeddings using the configured provider."""
            # This would call the actual embedding API
            # For now, return mock embeddings
            import pandas as pd
            return pd.Series([[float(i % 10) / 10.0 for i in range(384)] for _ in texts])
        
        self.batch_embedding_udf = batch_generate_embeddings
    
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
    
    def generate_embeddings(self, df: DataFrame) -> DataFrame:
        """
        Generate embeddings for neighborhoods.
        
        Neighborhoods typically have moderate-length descriptions that don't need chunking.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embeddings added
        """
        start_time = time.time()
        logger.info(f"Generating neighborhood embeddings using {self.model_identifier}")
        
        total_neighborhoods = df.count()
        logger.info(f"Processing {total_neighborhoods} neighborhoods")
        
        # Generate embeddings (using mock for testing, batch UDF for production)
        from data_pipeline.config.models import ProviderType
        if self.config.provider == ProviderType.OLLAMA:
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        else:
            # Use batch processing for production
            result_df = df.withColumn(
                "embedding",
                when(
                    col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                    self.batch_embedding_udf(col("embedding_text"))
                ).otherwise(lit(None))
            )
        
        # Add embedding metadata
        result_df = result_df.withColumn(
            "embedding_model",
            when(col("embedding").isNotNull(), lit(self.model_identifier))
        ).withColumn(
            "embedding_dimension",
            when(col("embedding").isNotNull(), lit(384))  # Would be dynamic in production
        ).withColumn(
            "embedded_at",
            when(col("embedding").isNotNull(), current_timestamp())
        )
        
        # Count successful embeddings
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        elapsed_time = time.time() - start_time
        
        logger.info(f"Generated {embedded_count}/{total_neighborhoods} embeddings in {elapsed_time:.2f} seconds")
        if embedded_count > 0:
            logger.info(f"Average time per embedding: {elapsed_time / embedded_count:.3f} seconds")
        
        return result_df