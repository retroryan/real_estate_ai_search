"""
Base embedding generator class for common embedding functionality.

Provides shared functionality for all entity-specific embedding generators
to reduce code duplication and ensure consistent patterns.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    length,
    lit,
    pandas_udf,
    udf,
    when,
)
from pyspark.sql.types import ArrayType, DoubleType

from data_pipeline.config.models import EmbeddingConfig, ProviderType

logger = logging.getLogger(__name__)


class BaseEmbeddingGenerator(ABC):
    """
    Abstract base class for entity-specific embedding generators.
    
    Provides common functionality like model identification, UDF registration,
    and embedding metadata management.
    """
    
    def __init__(self, spark: SparkSession, config: EmbeddingConfig):
        """
        Initialize the base embedding generator.
        
        Args:
            spark: Active SparkSession
            config: Embedding configuration
        """
        self.spark = spark
        self.config = config
        self.model_identifier = self._get_model_identifier()
        
        # Register UDFs
        self._register_udfs()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string based on provider."""
        provider = self.config.provider
        
        # Get model config if available
        model_config = self.config.get_model_config() if hasattr(self.config, 'get_model_config') else None
        
        if provider == ProviderType.OPENAI:
            return model_config.model if model_config else "text-embedding-3-small"
        elif provider == ProviderType.GEMINI:
            return model_config.model if model_config else "models/embedding-001"
        elif provider == ProviderType.OLLAMA:
            return model_config.model if model_config else "nomic-embed-text"
        elif provider == ProviderType.VOYAGE:
            return model_config.model if model_config else "voyage-3"
        elif provider == ProviderType.MOCK:
            return "mock-embedding"
        else:
            return f"{provider.value}-embedding"
    
    def _register_udfs(self):
        """Register UDFs for embedding generation."""
        # Get dimension once, outside the UDF - use config if available
        if hasattr(self.config, 'models') and self.config.models:
            model_config = self.config.get_model_config()
            dim = model_config.dimension if model_config and hasattr(model_config, 'dimension') else self._get_embedding_dimension()
        else:
            dim = self._get_embedding_dimension()
        
        # Use only Pandas UDF for batch processing (more efficient)
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def batch_generate_embeddings(texts):
            """Batch generate embeddings using the configured provider."""
            # This would call the actual embedding API
            # For now, return mock embeddings
            import pandas as pd
            import numpy as np
            
            # Generate deterministic mock embeddings based on text
            result = []
            for text in texts:
                if text is None or text == "":
                    result.append(None)
                else:
                    # Create deterministic embedding based on text hash
                    np.random.seed(hash(text) % 2**32)
                    embedding = np.random.rand(dim).tolist()
                    result.append(embedding)
            
            return pd.Series(result)
        
        self.batch_embedding_udf = batch_generate_embeddings
        # Also assign to embedding_udf for compatibility
        self.embedding_udf = batch_generate_embeddings
    
    def _get_embedding_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        # This would be determined by the actual model
        # Common dimensions:
        # - OpenAI text-embedding-3-small: 1536
        # - Gemini embedding-001: 768
        # - Nomic embed-text: 768
        # - Voyage-3: 1024
        if self.config.provider == ProviderType.OPENAI:
            return 1536
        elif self.config.provider == ProviderType.GEMINI:
            return 768
        elif self.config.provider == ProviderType.OLLAMA:
            return 768  # Nomic default
        elif self.config.provider == ProviderType.VOYAGE:
            return 1024
        else:
            return 384  # Default/mock dimension
    
    @abstractmethod
    def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare entity-specific text for embedding.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with embedding_text column added
        """
        pass
    
    def generate_embeddings(self, df: DataFrame) -> DataFrame:
        """
        Generate embeddings for the entity.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embeddings added
        """
        entity_name = self.__class__.__name__.replace("EmbeddingGenerator", "")
        start_time = time.time()
        logger.info(f"Generating {entity_name} embeddings using {self.model_identifier}")
        
        total_records = df.count()
        logger.info(f"Processing {total_records} {entity_name} records")
        
        # Always use Pandas UDF for batch processing (more efficient)
        result_df = df.withColumn(
            "embedding",
            when(
                col("embedding_text").isNotNull() & (length(col("embedding_text")) > 0),
                self.batch_embedding_udf(col("embedding_text"))
            ).otherwise(lit(None))
        )
        
        # Add embedding metadata
        result_df = self._add_embedding_metadata(result_df)
        
        # Log statistics
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        elapsed_time = time.time() - start_time
        
        logger.info(f"Generated {embedded_count}/{total_records} embeddings in {elapsed_time:.2f} seconds")
        if embedded_count > 0:
            logger.info(f"Average time per embedding: {elapsed_time / embedded_count:.3f} seconds")
        
        return result_df
    
    def _add_embedding_metadata(self, df: DataFrame) -> DataFrame:
        """
        Add embedding metadata columns.
        
        Args:
            df: DataFrame with embedding column
            
        Returns:
            DataFrame with metadata columns added
        """
        return df.withColumn(
            "embedding_model",
            when(col("embedding").isNotNull(), lit(self.model_identifier))
        ).withColumn(
            "embedding_dimension",
            when(col("embedding").isNotNull(), lit(self._get_embedding_dimension()))
        ).withColumn(
            "embedded_at",
            when(col("embedding").isNotNull(), current_timestamp())
        )
    
    def get_embedding_statistics(self, df: DataFrame) -> dict:
        """
        Calculate embedding statistics.
        
        Args:
            df: DataFrame with embeddings
            
        Returns:
            Dictionary of statistics
        """
        total = df.count()
        embedded = df.filter(col("embedding").isNotNull()).count()
        
        stats = {
            "total_records": total,
            "embedded_records": embedded,
            "embedding_rate": (embedded / total * 100) if total > 0 else 0,
            "model": self.model_identifier,
            "dimension": self._get_embedding_dimension()
        }
        
        # Add text length stats if available
        if "embedding_text_length" in df.columns:
            from pyspark.sql.functions import avg
            avg_length = df.filter(col("embedding").isNotNull()).select(
                avg(col("embedding_text_length"))
            ).collect()[0][0]
            stats["avg_text_length"] = float(avg_length) if avg_length else 0
        
        return stats