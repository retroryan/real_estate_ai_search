"""
Distributed embedding generation using Spark UDFs.

This module provides simple, clean embedding generation directly as DataFrame columns
without any storage complexity. It copies proven patterns from common_embeddings
but simplifies to just embedding generation (no ChromaDB, no correlation management).
"""

import logging
import os
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array,
    col,
    current_timestamp,
    explode,
    expr,
    lit,
    monotonically_increasing_id,
    size,
    split,
    udf,
    when,
)
from pyspark.sql.types import ArrayType, DoubleType, IntegerType, LongType, StringType

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    VOYAGE = "voyage"
    GEMINI = "gemini"
    MOCK = "mock"  # For testing without API calls


class ChunkingMethod(str, Enum):
    """Text chunking strategies."""
    SIMPLE = "simple"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"  # Falls back to sentence for simplicity
    NONE = "none"


class ProviderConfig(BaseModel):
    """Configuration for embedding providers."""
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OLLAMA,
        description="Embedding provider to use"
    )
    
    # Ollama settings
    ollama_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model name"
    )
    
    # Voyage settings
    voyage_api_key: Optional[str] = Field(
        default=None,
        description="Voyage API key"
    )
    voyage_model: str = Field(
        default="voyage-3",
        description="Voyage model name (voyage-3, voyage-large-2, etc.)"
    )
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Gemini API key"
    )
    gemini_model: str = Field(
        default="models/embedding-001",
        description="Gemini model name"
    )
    
    # General settings
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for API calls"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries for API calls"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        description="Timeout for API calls in seconds"
    )
    embedding_dimension: int = Field(
        default=1024,
        ge=1,
        description="Expected embedding dimension (voyage-3: 1024, voyage-large-2: 1536)"
    )


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""
    
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SIMPLE,
        description="Chunking method to use"
    )
    
    chunk_size: int = Field(
        default=512,
        ge=100,
        le=8000,
        description="Target chunk size in characters"
    )
    
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Overlap between chunks"
    )
    
    enable_chunking: bool = Field(
        default=True,
        description="Whether to chunk text before embedding"
    )


class EmbeddingGeneratorConfig(BaseModel):
    """Complete configuration for embedding generation."""
    
    provider_config: ProviderConfig = Field(
        default_factory=ProviderConfig,
        description="Provider configuration"
    )
    
    chunking_config: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Chunking configuration"
    )
    
    process_empty_text: bool = Field(
        default=False,
        description="Whether to process empty text"
    )
    
    skip_existing_embeddings: bool = Field(
        default=True,
        description="Skip rows that already have embeddings"
    )


class DistributedEmbeddingGenerator:
    """
    Simple embedding generator that provides UDFs for DataFrame operations.
    
    Following the simplified Phase 5 approach - provides UDFs for chunking and
    embedding generation with direct DataFrame column operations.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[EmbeddingGeneratorConfig] = None):
        """
        Initialize the embedding generator.
        
        Args:
            spark: Active SparkSession
            config: Embedding generation configuration
        """
        self.spark = spark
        self.config = config or EmbeddingGeneratorConfig()
        
        # Create the UDFs
        self.embedding_udf = self._create_embedding_udf()
        if self.config.chunking_config.enable_chunking:
            self.chunking_udf = self._create_chunking_udf()
        
        # Get model identifier for tracking
        self.model_identifier = self._get_model_identifier()
    
    def _get_model_identifier(self) -> str:
        """Get the model identifier string."""
        provider = self.config.provider_config.provider
        
        if provider == EmbeddingProvider.OLLAMA:
            return f"ollama_{self.config.provider_config.ollama_model}"
        elif provider == EmbeddingProvider.OPENAI:
            return f"openai_{self.config.provider_config.openai_model}"
        elif provider == EmbeddingProvider.VOYAGE:
            return f"voyage_{self.config.provider_config.voyage_model}"
        elif provider == EmbeddingProvider.GEMINI:
            model_name = self.config.provider_config.gemini_model.split('/')[-1]
            return f"gemini_{model_name}"
        else:
            return "mock_embedding"
    
    def add_embeddings_to_dataframe(self, df: DataFrame) -> DataFrame:
        """
        Add embeddings directly to DataFrame columns.
        
        This is the simplified approach - uses withColumn() operations
        following Spark best practices. Handles chunking if configured.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embedding columns added
        """
        logger.info(f"Adding embeddings to DataFrame using {self.model_identifier}")
        
        # Apply chunking if enabled
        if self.config.chunking_config.enable_chunking:
            logger.info(f"Applying {self.config.chunking_config.method} chunking")
            # Create chunks using UDF
            df_with_chunks = df.withColumn(
                "text_chunks",
                self.chunking_udf(col("embedding_text"))
            )
            
            # Explode chunks into separate rows
            df_chunked = df_with_chunks.select(
                "*",
                explode(col("text_chunks")).alias("chunk_text")
            ).drop("text_chunks", "embedding_text").withColumnRenamed("chunk_text", "embedding_text")
            
            # Add chunk index
            df_to_embed = df_chunked.withColumn(
                "chunk_index",
                monotonically_increasing_id()
            )
        else:
            # No chunking - add chunk_index = 0
            df_to_embed = df.withColumn("chunk_index", lit(0))
        
        # Simple, direct DataFrame operations for embeddings
        result_df = df_to_embed.withColumn(
            "embedding",
            when(
                col("embedding_text").isNotNull() & (col("embedding_text") != ""),
                self.embedding_udf(col("embedding_text"))
            ).otherwise(lit(None))
        ).withColumn(
            "embedding_model",
            when(col("embedding").isNotNull(), lit(self.model_identifier))
            .otherwise(lit(None))
        ).withColumn(
            "embedding_dimension",
            when(col("embedding").isNotNull(), size(col("embedding")))
            .otherwise(lit(None))
        ).withColumn(
            "embedding_generated_at",
            when(col("embedding").isNotNull(), current_timestamp())
            .otherwise(lit(None))
        )
        
        logger.info("Embeddings added successfully")
        return result_df
    
    def _create_chunking_udf(self):
        """
        Create UDF for text chunking.
        
        Returns:
            Spark UDF for chunking text
        """
        method = self.config.chunking_config.method
        chunk_size = self.config.chunking_config.chunk_size
        chunk_overlap = self.config.chunking_config.chunk_overlap
        
        def chunk_text(text: str) -> List[str]:
            """Chunk text based on configured method."""
            if not text:
                return []
            
            if method == ChunkingMethod.NONE:
                return [text]
            
            elif method == ChunkingMethod.SIMPLE:
                # Simple character-based chunking
                chunks = []
                start = 0
                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunk = text[start:end]
                    if chunk.strip():  # Only add non-empty chunks
                        chunks.append(chunk)
                    start = end - chunk_overlap if chunk_overlap > 0 else end
                return chunks if chunks else [text]
            
            elif method == ChunkingMethod.SENTENCE:
                # Sentence-based chunking
                sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
                
                chunks = []
                current_chunk = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # Check if adding sentence exceeds chunk size
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        current_chunk = (current_chunk + " " + sentence).strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                return chunks if chunks else [text]
            
            elif method == ChunkingMethod.SEMANTIC:
                # For simplicity, fall back to sentence chunking
                # Real semantic chunking would require embeddings to find breakpoints
                return chunk_text(text)  # Will use sentence method as fallback
            
            else:
                # Default to simple chunking
                return [text]
        
        return udf(chunk_text, ArrayType(StringType()))
    
    def _create_embedding_udf(self):
        """
        Create UDF for embedding generation.
        
        Returns:
            Spark UDF for generating embeddings
        """
        provider = self.config.provider_config.provider
        provider_config = self.config.provider_config
        
        def generate_embedding(text: str) -> List[float]:
            """Generate embedding for text using configured provider."""
            if not text:
                return None
            
            try:
                if provider == EmbeddingProvider.OLLAMA:
                    # Use llama-index for Ollama
                    from llama_index.embeddings.ollama import OllamaEmbedding
                    embed_model = OllamaEmbedding(
                        model_name=provider_config.ollama_model,
                        base_url=provider_config.ollama_base_url
                    )
                    embedding = embed_model.get_text_embedding(text)
                    return embedding
                
                elif provider == EmbeddingProvider.OPENAI:
                    # Use llama-index for OpenAI
                    from llama_index.embeddings.openai import OpenAIEmbedding
                    api_key = provider_config.openai_api_key or os.getenv("OPENAI_API_KEY")
                    embed_model = OpenAIEmbedding(
                        api_key=api_key,
                        model=provider_config.openai_model
                    )
                    embedding = embed_model.get_text_embedding(text)
                    return embedding
                
                elif provider == EmbeddingProvider.VOYAGE:
                    # Use llama-index for Voyage
                    from llama_index.embeddings.voyageai import VoyageEmbedding
                    api_key = provider_config.voyage_api_key or os.getenv('VOYAGE_API_KEY')
                    embed_model = VoyageEmbedding(
                        api_key=api_key,
                        model_name=provider_config.voyage_model
                    )
                    embedding = embed_model.get_text_embedding(text)
                    return embedding
                
                elif provider == EmbeddingProvider.GEMINI:
                    # Use llama-index for Gemini
                    from llama_index.embeddings.google import GeminiEmbedding
                    api_key = provider_config.gemini_api_key or os.getenv("GEMINI_API_KEY")
                    embed_model = GeminiEmbedding(
                        api_key=api_key,
                        model_name=provider_config.gemini_model
                    )
                    embedding = embed_model.get_text_embedding(text)
                    return embedding
                
                elif provider == EmbeddingProvider.MOCK:
                    # Mock embedding for testing
                    import hashlib
                    import numpy as np
                    
                    # Generate deterministic fake embedding from text hash
                    text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
                    np.random.seed(text_hash)
                    return np.random.normal(0, 1, provider_config.embedding_dimension).tolist()
                
                else:
                    logger.error(f"Unknown provider: {provider}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                return None
        
        return udf(generate_embedding, ArrayType(DoubleType()))
    
    def get_statistics(self, df: DataFrame) -> Dict:
        """
        Get statistics about embeddings in the DataFrame.
        
        Args:
            df: DataFrame with embeddings
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Basic counts
        total_records = df.count()
        stats["total_records"] = total_records
        
        if "embedding" in df.columns:
            with_embeddings = df.filter(col("embedding").isNotNull()).count()
            stats["records_with_embeddings"] = with_embeddings
            stats["records_without_embeddings"] = total_records - with_embeddings
            stats["embedding_coverage"] = with_embeddings / total_records if total_records > 0 else 0
        
        if "chunk_index" in df.columns:
            chunk_stats = df.select(
                expr("max(chunk_index) as max_chunks"),
                expr("avg(chunk_index) as avg_chunks")
            ).collect()[0]
            stats["max_chunks"] = chunk_stats["max_chunks"]
            stats["avg_chunks"] = chunk_stats["avg_chunks"]
        
        if "embedding_model" in df.columns:
            model_counts = df.groupBy("embedding_model").count().collect()
            stats["embeddings_by_model"] = {
                row["embedding_model"]: row["count"]
                for row in model_counts if row["embedding_model"]
            }
        
        return stats