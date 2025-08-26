"""
Base embedding generator for the data pipeline.

This module provides the foundation for generating embeddings using various providers
(Voyage, OpenAI, Ollama, Gemini) via LlamaIndex. It implements a clean, modular design
with Pydantic-based configuration and efficient batch processing.

Architecture Overview:
----------------------
1. Configuration is validated using Pydantic models
2. Embedding providers are created via a factory pattern
3. Text is processed in batches using Pandas UDFs
4. Metadata (model, dimension, timestamp) is tracked for each embedding

Technical Design Decisions:
---------------------------
- No broadcast variables: Due to incompatibility with Neo4j writer (see BROADCAST.md)
- Simple batch UDF: Avoids iterator pattern that causes Python worker crashes
- Configuration serialization: Passed directly to UDF as dict to avoid closure issues
- Provider initialization per batch: Balances performance with reliability

Author: Data Pipeline Team
Date: 2024
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    length,
    lit,
    pandas_udf,
    when,
    avg
)
from pyspark.sql.types import ArrayType, DoubleType

from data_pipeline.models.embedding_config import (
    EmbeddingPipelineConfig,
    EmbeddingProvider
)

logger = logging.getLogger(__name__)


class BaseEmbeddingGenerator(ABC):
    """
    Abstract base class for entity-specific embedding generators.
    
    This class provides the core functionality for generating embeddings from text data
    using various embedding providers (Voyage, OpenAI, Ollama, Gemini) through LlamaIndex.
    
    Key Features:
    - Supports multiple embedding providers via configuration
    - Validates configuration using Pydantic models
    - Generates embeddings in batches for efficiency
    - Tracks metadata (model, dimension, timestamp) for each embedding
    - Handles errors gracefully without failing entire batches
    
    Implementation Notes:
    - Does NOT use broadcast variables due to Neo4j compatibility issues
    - Configuration is serialized and passed directly to UDF
    - Provider is initialized once per batch (not per record) for efficiency
    
    Subclasses must implement:
    - prepare_embedding_text(): Define how to create embedding text from entity data

    Example:
    --------
    ```python
    from data_pipeline.models.embedding_config import EmbeddingPipelineConfig
    
    class PropertyEmbeddingGenerator(BaseEmbeddingGenerator):
        def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
            # Combine property fields into embedding text
            return df.withColumn("embedding_text",
                concat_ws(" ", col("address"), col("description")))

    # Create proper config
    config = EmbeddingPipelineConfig.from_dict({
        'provider': 'voyage',
        'models': {'voyage': {'model': 'voyage-3'}}
    })
    
    # Use the generator
    generator = PropertyEmbeddingGenerator(spark, config)
    df_with_text = generator.prepare_embedding_text(property_df)
    df_with_embeddings = generator.generate_embeddings(df_with_text)
    ```
    """
    
    def __init__(self, spark: SparkSession, config: EmbeddingPipelineConfig):
        """
        Initialize the embedding generator.
        
        Args:
            spark: Active SparkSession for distributed processing
            config: Validated EmbeddingPipelineConfig instance
        """
        self.spark = spark
        self.config = config
        
        # Extract key metadata for logging and tracking
        self.model_identifier = self.config.embedding.get_model_identifier()
        self.embedding_dimension = self.config.embedding.get_embedding_dimension()
        self.provider_name = self.config.embedding.provider.value
        
        # Register the Pandas UDF for embedding generation
        self._register_udfs()
        
        logger.info(
            f"Initialized {self.__class__.__name__} | "
            f"Provider: {self.provider_name} | "
            f"Model: {self.model_identifier} | "
            f"Dimension: {self.embedding_dimension}"
        )
    
    
    def _register_udfs(self):
        """
        Register Pandas UDF for batch embedding generation.
        
        Technical Details:
        - Configuration is serialized to dict to avoid closure/broadcast issues
        - UDF initializes embedding provider once per batch (not per record)
        - Errors are logged but don't fail the entire batch
        - Returns None for failed embeddings to maintain DataFrame structure
        
        The UDF is stored as self.embedding_udf for use in generate_embeddings().
        """
        # Serialize configuration to pass to UDF
        # This avoids broadcast variable issues with Neo4j
        config_dict = self.config.model_dump()
        
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def generate_embeddings_batch(text_series: pd.Series) -> pd.Series:
            """
            Generate embeddings for a batch of texts.
            
            This UDF is executed on worker nodes and:
            1. Recreates configuration from serialized dict
            2. Initializes embedding provider once for the batch
            3. Generates embeddings for each text
            4. Returns None for empty/failed texts
            
            Args:
                text_series: Pandas Series containing text to embed
                
            Returns:
                Pandas Series of embedding vectors (lists of floats)
            """
            # Import inside UDF to avoid serialization issues
            import logging as udf_logging
            from data_pipeline.models.embedding_config import EmbeddingPipelineConfig
            from data_pipeline.embedding.factory import EmbeddingFactory
            
            udf_logger = udf_logging.getLogger(__name__)
            
            # Recreate configuration from serialized dict
            try:
                config = EmbeddingPipelineConfig(**config_dict)
                embed_model, model_id = EmbeddingFactory.create_provider(config)
                udf_logger.debug(f"Initialized {model_id} for batch of {len(text_series)} texts")
            except Exception as e:
                udf_logger.error(f"Failed to initialize embedding provider: {e}")
                # Return None for all texts if provider initialization fails
                return pd.Series([None] * len(text_series))
            
            # Generate embeddings for each text in the batch
            embeddings = []
            for idx, text in enumerate(text_series):
                if pd.isna(text) or text == "" or text is None:
                    # Skip empty texts
                    embeddings.append(None)
                else:
                    try:
                        # Generate embedding using LlamaIndex provider
                        embedding = embed_model.get_text_embedding(str(text))
                        embeddings.append(embedding)
                    except Exception as e:
                        # Log error but don't fail the batch
                        if idx < 3:  # Only log first few errors to avoid spam
                            udf_logger.error(
                                f"Failed to generate embedding for text {idx}: {str(e)[:200]}"
                            )
                        embeddings.append(None)
            
            return pd.Series(embeddings)
        
        # Store UDF for use in generate_embeddings
        self.embedding_udf = generate_embeddings_batch
    
    @abstractmethod
    def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
        """
        Prepare entity-specific text for embedding generation.
        
        This method must be implemented by subclasses to define how to
        create embedding text from entity-specific data fields.
        
        The implementation should:
        1. Combine relevant fields into a single text representation
        2. Handle missing values appropriately
        3. Add an 'embedding_text' column to the DataFrame
        
        Args:
            df: Input DataFrame with entity data
            
        Returns:
            DataFrame with 'embedding_text' column added
            
        Example:
            ```python
            def prepare_embedding_text(self, df: DataFrame) -> DataFrame:
                return df.withColumn(
                    "embedding_text",
                    concat_ws(" | ", 
                        col("title"), 
                        col("description"),
                        array_join(col("tags"), ", "))
                )
            ```
        """
        pass
    
    def generate_embeddings(self, df: DataFrame) -> DataFrame:
        """
        Generate embeddings for prepared text and add metadata.
        
        This method:
        1. Applies the embedding UDF to generate vectors
        2. Adds metadata columns (model, dimension, timestamp)
        3. Logs statistics about the embedding process
        
        Args:
            df: DataFrame with 'embedding_text' column
            
        Returns:
            DataFrame with embeddings and metadata columns:
            - embedding: Array of doubles (the embedding vector)
            - embedding_model: String identifier of the model used
            - embedding_dimension: Integer dimension of embeddings
            - embedded_at: Timestamp when embedding was generated
            
        The method handles null/empty texts gracefully by setting
        embedding to None for those records.
        """
        entity_name = self.__class__.__name__.replace("EmbeddingGenerator", "")
        start_time = time.time()
        
        logger.info(f"Starting embedding generation for {entity_name}")
        logger.info(f"Using model: {self.model_identifier} (dimension: {self.embedding_dimension})")
        
        # Count records for statistics
        total_records = df.count()
        logger.info(f"Processing {total_records:,} {entity_name} records")
        
        # Apply embedding UDF only to non-empty texts
        result_df = df.withColumn(
            "embedding",
            when(
                col("embedding_text").isNotNull() & 
                (length(col("embedding_text")) > 0),
                self.embedding_udf(col("embedding_text"))
            ).otherwise(lit(None))
        )
        
        # Add embedding metadata for tracking and debugging
        result_df = self._add_embedding_metadata(result_df)
        
        # Calculate and log statistics
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        elapsed_time = time.time() - start_time
        
        # Log summary statistics
        logger.info(
            f"Embedding generation complete for {entity_name} | "
            f"Embedded: {embedded_count:,}/{total_records:,} "
            f"({embedded_count/total_records*100:.1f}%) | "
            f"Time: {elapsed_time:.2f}s"
        )
        
        if embedded_count > 0:
            avg_time = elapsed_time / embedded_count
            logger.info(
                f"Performance: {avg_time:.3f}s per embedding, "
                f"{embedded_count/elapsed_time:.1f} embeddings/second"
            )
        
        return result_df
    
    def _add_embedding_metadata(self, df: DataFrame) -> DataFrame:
        """
        Add metadata columns for embedded records.
        
        Adds the following columns for records with embeddings:
        - embedding_model: Model identifier (e.g., "voyage_voyage_3")
        - embedding_dimension: Vector dimension (e.g., 1024)
        - embedded_at: Timestamp of embedding generation
        
        These columns are set to None for records without embeddings.
        
        Args:
            df: DataFrame with embedding column
            
        Returns:
            DataFrame with metadata columns added
        """
        return (
            df.withColumn(
                "embedding_model",
                when(col("embedding").isNotNull(), lit(self.model_identifier))
            )
            .withColumn(
                "embedding_dimension",
                when(col("embedding").isNotNull(), lit(self.embedding_dimension))
            )
            .withColumn(
                "embedded_at",
                when(col("embedding").isNotNull(), current_timestamp())
            )
        )
    
    def get_embedding_statistics(self, df: DataFrame) -> Dict[str, Any]:
        """
        Calculate detailed statistics about embeddings in the DataFrame.
        
        Computes:
        - Total and embedded record counts
        - Embedding rate (percentage)
        - Model and dimension information
        - Average text length for embedded records
        
        Args:
            df: DataFrame with embeddings and metadata
            
        Returns:
            Dictionary containing:
            - total_records: Total number of records
            - embedded_records: Number with embeddings
            - embedding_rate: Percentage with embeddings
            - model: Model identifier used
            - dimension: Embedding dimension
            - provider: Provider name (voyage, openai, etc.)
            - avg_text_length: Average length of embedded texts (if available)
        
        Example:
            ```python
            stats = generator.get_embedding_statistics(df)
            print(f"Embedded {stats['embedded_records']} of {stats['total_records']} records")
            print(f"Using {stats['provider']} model: {stats['model']}")
            ```
        """
        total = df.count()
        embedded = df.filter(col("embedding").isNotNull()).count()
        
        stats = {
            "total_records": total,
            "embedded_records": embedded,
            "embedding_rate": (embedded / total * 100) if total > 0 else 0,
            "model": self.model_identifier,
            "dimension": self.embedding_dimension,
            "provider": self.provider_name
        }
        
        # Calculate average text length if embedding_text column exists
        if "embedding_text" in df.columns:
            from pyspark.sql.functions import length as spark_length
            
            avg_length_row = df.filter(
                col("embedding").isNotNull() & col("embedding_text").isNotNull()
            ).select(
                avg(spark_length(col("embedding_text"))).alias("avg_length")
            ).collect()
            
            if avg_length_row and avg_length_row[0]["avg_length"]:
                stats["avg_text_length"] = float(avg_length_row[0]["avg_length"])
        
        return stats
    
    def validate_embeddings(self, df: DataFrame) -> bool:
        """
        Validate that embeddings were generated correctly.
        
        Checks:
        - At least some embeddings were generated
        - Embeddings have the expected dimension
        - Metadata columns are present and populated
        
        Args:
            df: DataFrame with embeddings to validate
            
        Returns:
            True if validation passes, False otherwise
            
        Logs warnings for any validation issues found.
        """
        try:
            # Check that some embeddings exist
            embedded_count = df.filter(col("embedding").isNotNull()).count()
            if embedded_count == 0:
                logger.warning("No embeddings were generated")
                return False
            
            # Check embedding dimension (sample first non-null embedding)
            sample = df.filter(col("embedding").isNotNull()).select("embedding").first()
            if sample and sample["embedding"]:
                actual_dim = len(sample["embedding"])
                if actual_dim != self.embedding_dimension:
                    logger.warning(
                        f"Embedding dimension mismatch: "
                        f"expected {self.embedding_dimension}, got {actual_dim}"
                    )
                    return False
            
            # Check metadata columns exist
            required_columns = ["embedding_model", "embedding_dimension", "embedded_at"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"Missing metadata columns: {missing_columns}")
                return False
            
            logger.info("Embedding validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Embedding validation failed: {e}")
            return False