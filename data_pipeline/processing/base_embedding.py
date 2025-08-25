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

from data_pipeline.config.pipeline_config import ProviderType

logger = logging.getLogger(__name__)


class BaseEmbeddingGenerator(ABC):
    """
    Abstract base class for entity-specific embedding generators.
    
    Provides common functionality like model identification, UDF registration,
    and embedding metadata management.
    """
    
    def __init__(self, spark: SparkSession, config):
        """
        Initialize the base embedding generator.
        
        Args:
            spark: Active SparkSession
            config: Embedding configuration (dict or PipelineConfig)
        """
        self.spark = spark
        self.config = config
        self.model_identifier = self._get_model_identifier()
        
        # Register UDFs
        self._register_udfs()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string based on provider."""
        # Handle both dict and object config
        if isinstance(self.config, dict):
            provider_str = self.config.get('provider', 'voyage')
            models_config = self.config.get('models', {})
            model_config = models_config.get(provider_str, {}) if provider_str in models_config else None
        else:
            provider = self.config.provider
            provider_str = provider.value if hasattr(provider, 'value') else str(provider)
            # Get model config if available
            model_config = self.config.get_model_config() if hasattr(self.config, 'get_model_config') else None
        
        # Convert string to ProviderType enum for consistent comparison
        try:
            provider_enum = ProviderType(provider_str.lower()) if isinstance(provider_str, str) else provider_str
        except ValueError:
            # If provider string doesn't match any enum value, use it as-is
            provider_enum = None
        
        # Get model from config or use defaults
        if isinstance(model_config, dict):
            model = model_config.get('model')
        else:
            model = model_config.model if model_config and hasattr(model_config, 'model') else None
        
        # Use ProviderType constants for comparison
        if provider_enum == ProviderType.OPENAI:
            return model or "text-embedding-3-small"
        elif provider_enum == ProviderType.GEMINI:
            return model or "models/embedding-001"
        elif provider_enum == ProviderType.OLLAMA:
            return model or "nomic-embed-text"
        elif provider_enum == ProviderType.VOYAGE:
            return model or "voyage-3"
        elif provider_enum == ProviderType.MOCK:
            return "mock-embedding"
        else:
            # Fallback for unknown providers
            return f"{provider_str}-embedding"
    
    def _register_udfs(self):
        """Register UDFs for embedding generation."""
        # Get dimension once, outside the UDF - use config if available
        if isinstance(self.config, dict):
            # For dict config, get dimension from models config
            provider = self.config.get('provider', 'voyage')
            models_config = self.config.get('models', {})
            model_config = models_config.get(provider, {})
            dim = model_config.get('dimension') if model_config else self._get_embedding_dimension()
        elif hasattr(self.config, 'models') and self.config.models:
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
        # Get provider from config
        if isinstance(self.config, dict):
            provider_str = self.config.get('provider', 'voyage')
        else:
            provider = self.config.provider
            provider_str = provider.value if hasattr(provider, 'value') else str(provider)
        
        # Convert to enum for comparison
        try:
            provider_enum = ProviderType(provider_str.lower()) if isinstance(provider_str, str) else provider_str
        except ValueError:
            provider_enum = None
        
        # Common dimensions:
        # - OpenAI text-embedding-3-small: 1536
        # - Gemini embedding-001: 768
        # - Nomic embed-text: 768
        # - Voyage-3: 1024
        if provider_enum == ProviderType.OPENAI:
            return 1536
        elif provider_enum == ProviderType.GEMINI:
            return 768
        elif provider_enum == ProviderType.OLLAMA:
            return 768  # Nomic default
        elif provider_enum == ProviderType.VOYAGE:
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