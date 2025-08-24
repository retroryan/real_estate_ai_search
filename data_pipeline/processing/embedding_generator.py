"""
Optimized distributed embedding generation using LlamaIndex best practices and Pandas UDFs.

This module provides high-performance embedding generation using:
- LlamaIndex nodes as atomic units of data
- PySpark Pandas UDFs for vectorized batch processing
- Proper document-node relationship management
- Following best practices from PANDA_UDFS.md
"""

import logging
import os
import time
import json
from enum import Enum
from typing import Dict, List, Optional, Iterator, Any
import hashlib
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    explode,
    expr,
    lit,
    monotonically_increasing_id,
    pandas_udf,
    size,
    udf,
    when,
    from_json,
    to_json,
    struct
)
from pyspark.sql.types import ArrayType, DoubleType, StringType, StructType, StructField

# LlamaIndex imports for node-based processing
from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import (
    SimpleNodeParser,
    SentenceSplitter,
)

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    VOYAGE = "voyage"
    GEMINI = "gemini"
    MOCK = "mock"  # For testing without API calls


class ChunkingMethod(str, Enum):
    """Text chunking strategies aligned with LlamaIndex node parsers."""
    SIMPLE = "simple"      # Uses SimpleNodeParser
    SENTENCE = "sentence"  # Uses SentenceSplitter  
    SEMANTIC = "semantic"  # Would use SemanticSplitterNodeParser
    NONE = "none"         # No chunking, single node per document


class ProviderConfig(BaseModel):
    """Configuration for embedding providers."""
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.VOYAGE,
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
    
    # Batch settings optimized for Pandas UDF
    batch_size: int = Field(
        default=20,  # Smaller batch size for API calls
        ge=1,
        le=100,
        description="Batch size for API calls"
    )
    pandas_batch_size: int = Field(
        default=100,  # Larger batch for Pandas UDF processing
        ge=10,
        le=1000,
        description="Number of rows processed per Pandas UDF batch"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries for API calls"
    )
    timeout: int = Field(
        default=60,  # Increased timeout
        ge=1,
        description="Timeout for API calls in seconds"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        description="Delay between retries in seconds"
    )
    embedding_dimension: int = Field(
        default=1024,
        ge=1,
        description="Expected embedding dimension"
    )


class ChunkingConfig(BaseModel):
    """Configuration for text chunking using LlamaIndex node parsers."""
    
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SIMPLE,
        description="Chunking method aligned with LlamaIndex parsers"
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
        description="Overlap between chunks for context preservation"
    )
    
    enable_chunking: bool = Field(
        default=False,
        description="Whether to chunk text before embedding"
    )
    
    # LlamaIndex node parser settings
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in nodes"
    )
    
    include_prev_next_rel: bool = Field(
        default=True,
        description="Include previous/next node relationships"
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
    
    use_pandas_udf: bool = Field(
        default=True,
        description="Use Pandas UDF for batch processing (recommended)"
    )
    
    use_llamaindex_nodes: bool = Field(
        default=True,
        description="Use LlamaIndex nodes for better document structure"
    )


class DistributedEmbeddingGenerator:
    """
    Optimized embedding generator using LlamaIndex nodes and Pandas UDFs.
    
    This implementation follows best practices:
    - Uses LlamaIndex nodes as atomic units (from common_embeddings)
    - Leverages vectorized Pandas UDFs (from PANDA_UDFS.md)
    - Maintains document-node relationships
    - Processes data in batches to minimize JVM-Python communication
    - Caches embedding models per partition for efficiency
    """
    
    def __init__(self, spark: SparkSession, config: Optional[EmbeddingGeneratorConfig] = None):
        """
        Initialize the optimized embedding generator.
        
        Args:
            spark: Active SparkSession
            config: Embedding generation configuration
        """
        self.spark = spark
        self.config = config or EmbeddingGeneratorConfig()
        
        # Create UDFs
        if self.config.chunking_config.enable_chunking:
            if self.config.use_llamaindex_nodes:
                self.node_creation_udf = self._create_node_creation_pandas_udf()
            else:
                self.chunking_udf = self._create_chunking_udf()
        
        # Create optimized Pandas UDF for batch embedding
        self.batch_embedding_pandas_udf = self._create_optimized_pandas_udf()
        
        # Get model identifier
        self.model_identifier = self._get_model_identifier()
        
        logger.info(f"Initialized DistributedEmbeddingGenerator with {self.model_identifier}")
        logger.info(f"Using LlamaIndex nodes: {self.config.use_llamaindex_nodes}")
        logger.info(f"Using Pandas UDF: {self.config.use_pandas_udf}")
        logger.info(f"Chunking enabled: {self.config.chunking_config.enable_chunking}")
    
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
        Add embeddings to DataFrame using optimized processing.
        
        Uses LlamaIndex nodes if enabled for better document structure.
        
        Args:
            df: DataFrame with embedding_text column
            
        Returns:
            DataFrame with embedding columns added
        """
        start_time = time.time()
        logger.info(f"Starting optimized embedding generation using {self.model_identifier}")
        
        # Count total records
        total_records = df.count()
        logger.info(f"Total records to process: {total_records:,}")
        
        # Apply chunking/node creation if enabled
        if self.config.chunking_config.enable_chunking:
            if self.config.use_llamaindex_nodes:
                df_to_embed = self._apply_node_chunking(df)
            else:
                df_to_embed = self._apply_simple_chunking(df)
        else:
            # Check if chunk_index already exists
            if "chunk_index" not in df.columns:
                df_to_embed = df.withColumn("chunk_index", lit(0))
            else:
                df_to_embed = df
                
            df_to_embed = df_to_embed.withColumn("node_id", 
                udf(lambda: str(uuid4()), StringType())()
            )
            logger.info("Chunking disabled - processing full text")
        
        # Optimize partitioning for Pandas UDF processing
        record_count = df_to_embed.count()
        optimal_partitions = self._calculate_optimal_partitions(record_count)
        
        logger.info(f"Repartitioning data into {optimal_partitions} partitions")
        logger.info(f"Approximately {record_count // optimal_partitions if optimal_partitions > 0 else 0} records per partition")
        
        df_to_embed = df_to_embed.repartition(optimal_partitions)
        
        # Apply embeddings using optimized Pandas UDF
        logger.info("Generating embeddings using optimized Pandas UDF...")
        logger.info(f"Provider: {self.config.provider_config.provider}")
        logger.info(f"API batch size: {self.config.provider_config.batch_size}")
        logger.info(f"Timeout: {self.config.provider_config.timeout}s")
        
        # Use Pandas UDF for batch processing
        result_df = df_to_embed.withColumn(
            "embedding",
            when(
                col("embedding_text").isNotNull() & (col("embedding_text") != ""),
                self.batch_embedding_pandas_udf(col("embedding_text"))
            ).otherwise(lit(None))
        )
        
        # Add metadata columns
        result_df = self._add_metadata_columns(result_df)
        
        # Force evaluation and count results
        embedded_count = result_df.filter(col("embedding").isNotNull()).count()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Successfully generated {embedded_count:,} embeddings in {elapsed_time:.2f} seconds")
        logger.info(f"Average time per embedding: {elapsed_time / embedded_count:.3f} seconds" if embedded_count > 0 else "No embeddings generated")
        
        return result_df
    
    def _calculate_optimal_partitions(self, record_count: int) -> int:
        """Calculate optimal number of partitions based on data size."""
        if record_count < 100:
            return 2  # Minimal partitions for small data
        elif record_count < 1000:
            return 4
        elif record_count < 10000:
            return 10
        else:
            # For large datasets, aim for ~1000 records per partition
            return min(200, max(10, record_count // 1000))
    
    def _apply_node_chunking(self, df: DataFrame) -> DataFrame:
        """
        Apply text chunking using LlamaIndex nodes.
        
        This follows the pattern from common_embeddings where nodes
        are the atomic unit of data with proper relationships.
        """
        logger.info(f"Applying {self.config.chunking_config.method} chunking with LlamaIndex nodes")
        logger.info(f"Chunk size: {self.config.chunking_config.chunk_size}, Overlap: {self.config.chunking_config.chunk_overlap}")
        
        # Schema for node data
        node_schema = ArrayType(StructType([
            StructField("node_id", StringType(), False),
            StructField("text", StringType(), False),
            StructField("metadata", StringType(), True),
            StructField("chunk_index", StringType(), True)
        ]))
        
        # Create nodes using Pandas UDF
        df_with_nodes = df.withColumn(
            "nodes",
            self.node_creation_udf(col("entity_id"), col("embedding_text"))
        )
        
        # Parse JSON nodes
        df_with_nodes = df_with_nodes.withColumn(
            "nodes_parsed",
            from_json(col("nodes"), node_schema)
        )
        
        # Drop existing chunk_index if it exists to avoid ambiguity
        columns_to_keep = [c for c in df_with_nodes.columns if c not in ["chunk_index", "nodes", "embedding_text"]]
        
        # Explode nodes into separate rows
        df_exploded = df_with_nodes.select(
            *columns_to_keep,
            explode(col("nodes_parsed")).alias("node")
        ).select(
            "*",
            col("node.node_id").alias("node_id"),
            col("node.text").alias("embedding_text_chunked"),
            col("node.metadata").alias("node_metadata"),
            col("node.chunk_index").cast("long").alias("chunk_index")
        ).drop("nodes_parsed", "node")
        
        # Rename chunked text back to embedding_text for consistency
        df_result = df_exploded.withColumnRenamed("embedding_text_chunked", "embedding_text")
        
        chunk_count = df_result.count()
        logger.info(f"Total nodes/chunks created: {chunk_count:,}")
        
        return df_result
    
    def _apply_simple_chunking(self, df: DataFrame) -> DataFrame:
        """Apply simple text chunking without LlamaIndex nodes."""
        logger.info(f"Applying {self.config.chunking_config.method} chunking")
        logger.info(f"Chunk size: {self.config.chunking_config.chunk_size}, Overlap: {self.config.chunking_config.chunk_overlap}")
        
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
        df_with_index = df_chunked.withColumn(
            "chunk_index",
            monotonically_increasing_id()
        )
        
        # Add node_id for consistency
        df_with_index = df_with_index.withColumn(
            "node_id",
            udf(lambda: str(uuid4()), StringType())()
        )
        
        chunk_count = df_with_index.count()
        logger.info(f"Total chunks after splitting: {chunk_count:,}")
        
        return df_with_index
    
    def _add_metadata_columns(self, result_df: DataFrame) -> DataFrame:
        """Add metadata columns to the result DataFrame."""
        result_df = result_df.withColumn(
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
        
        # Add node relationship data if using LlamaIndex nodes
        if self.config.use_llamaindex_nodes and "node_metadata" in result_df.columns:
            result_df = result_df.withColumn(
                "node_relationships",
                when(col("node_metadata").isNotNull(), col("node_metadata"))
                .otherwise(lit("{}"))
            )
        
        return result_df
    
    def _create_node_creation_pandas_udf(self):
        """
        Create Pandas UDF for LlamaIndex node creation.
        
        This follows the pattern from common_embeddings where Documents
        are parsed into Nodes with proper relationships.
        """
        config = self.config.chunking_config
        
        @pandas_udf(returnType=StringType())
        def create_nodes_batch(entity_ids: pd.Series, texts: pd.Series) -> pd.Series:
            """Create LlamaIndex nodes from text."""
            from llama_index.core import Document
            from llama_index.core.node_parser import SimpleNodeParser, SentenceSplitter
            
            # Initialize node parser based on method
            if config.method == ChunkingMethod.SENTENCE:
                node_parser = SentenceSplitter(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    include_metadata=config.include_metadata,
                    include_prev_next_rel=config.include_prev_next_rel
                )
            else:
                # Default to SimpleNodeParser
                node_parser = SimpleNodeParser.from_defaults(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    include_metadata=config.include_metadata,
                    include_prev_next_rel=config.include_prev_next_rel
                )
            
            results = []
            
            for entity_id, text in zip(entity_ids, texts):
                if not text or not isinstance(text, str):
                    results.append("[]")
                    continue
                
                try:
                    # Create Document with proper ID
                    doc = Document(
                        text=text,
                        doc_id=str(entity_id),
                        metadata={
                            "entity_id": str(entity_id),
                            "source": "data_pipeline"
                        }
                    )
                    
                    # Parse into nodes
                    nodes = node_parser.get_nodes_from_documents([doc])
                    
                    # Convert nodes to JSON
                    nodes_data = []
                    for i, node in enumerate(nodes):
                        node_dict = {
                            "node_id": node.node_id,
                            "text": node.text,
                            "metadata": json.dumps({
                                "entity_id": str(entity_id),
                                "chunk_index": i,
                                "total_chunks": len(nodes),
                                **node.metadata
                            }),
                            "chunk_index": str(i)  # Keep as string for JSON
                        }
                        nodes_data.append(node_dict)
                    
                    results.append(json.dumps(nodes_data))
                    
                except Exception as e:
                    logger.error(f"Node creation error: {str(e)[:200]}")
                    results.append("[]")
            
            return pd.Series(results)
        
        return create_nodes_batch
    
    def _create_optimized_pandas_udf(self):
        """
        Create an optimized Pandas UDF for batch embedding generation.
        
        This follows best practices from PANDA_UDFS.md:
        - Processes data in vectorized batches
        - Reuses embedding model per partition
        - Implements retry logic with exponential backoff
        - Handles errors gracefully
        """
        provider = self.config.provider_config.provider
        provider_config = self.config.provider_config
        
        @pandas_udf(returnType=ArrayType(DoubleType()))
        def generate_embeddings_batch(texts: pd.Series) -> pd.Series:
            """
            Generate embeddings for a batch of texts using vectorized processing.
            
            This function is executed once per partition, processing all texts
            in that partition as a batch for maximum efficiency.
            """
            batch_start_time = time.time()
            partition_size = len(texts)
            
            # Log partition processing
            logger.info(f"Processing partition with {partition_size} texts")
            
            # Initialize the embedding model once per partition (cached)
            embed_model = None
            
            try:
                if provider == EmbeddingProvider.VOYAGE:
                    from llama_index.embeddings.voyageai import VoyageEmbedding
                    api_key = provider_config.voyage_api_key or os.getenv('VOYAGE_API_KEY')
                    
                    if not api_key:
                        error_msg = "VOYAGE_API_KEY not found. Please set it in the .env file in the project root."
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    
                    embed_model = VoyageEmbedding(
                        api_key=api_key,
                        model_name=provider_config.voyage_model,
                        embed_batch_size=provider_config.batch_size
                    )
                    logger.debug(f"Initialized Voyage embedding model: {provider_config.voyage_model}")
                
                elif provider == EmbeddingProvider.OPENAI:
                    from llama_index.embeddings.openai import OpenAIEmbedding
                    api_key = provider_config.openai_api_key or os.getenv("OPENAI_API_KEY")
                    
                    if not api_key:
                        logger.error("OPENAI_API_KEY not found")
                        return pd.Series([None] * partition_size)
                    
                    embed_model = OpenAIEmbedding(
                        api_key=api_key,
                        model=provider_config.openai_model,
                        embed_batch_size=provider_config.batch_size
                    )
                    logger.debug(f"Initialized OpenAI embedding model: {provider_config.openai_model}")
                
                elif provider == EmbeddingProvider.OLLAMA:
                    from llama_index.embeddings.ollama import OllamaEmbedding
                    embed_model = OllamaEmbedding(
                        model_name=provider_config.ollama_model,
                        base_url=provider_config.ollama_base_url,
                        embed_batch_size=provider_config.batch_size
                    )
                    logger.debug(f"Initialized Ollama embedding model: {provider_config.ollama_model}")
                
                elif provider == EmbeddingProvider.GEMINI:
                    from llama_index.embeddings.google import GeminiEmbedding
                    api_key = provider_config.gemini_api_key or os.getenv("GEMINI_API_KEY")
                    
                    if not api_key:
                        logger.error("GEMINI_API_KEY not found")
                        return pd.Series([None] * partition_size)
                    
                    embed_model = GeminiEmbedding(
                        api_key=api_key,
                        model_name=provider_config.gemini_model
                    )
                    logger.debug(f"Initialized Gemini embedding model: {provider_config.gemini_model}")
                
                elif provider == EmbeddingProvider.MOCK:
                    # Mock embeddings for testing
                    results = []
                    for text in texts:
                        if text and isinstance(text, str):
                            # Generate deterministic fake embedding
                            text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
                            np.random.seed(text_hash)
                            embedding = np.random.normal(0, 1, provider_config.embedding_dimension).tolist()
                            results.append(embedding)
                        else:
                            results.append(None)
                    return pd.Series(results)
                
                else:
                    logger.error(f"Unknown provider: {provider}")
                    return pd.Series([None] * partition_size)
                
                # Process texts in batches with the embedding model
                results = []
                valid_texts = []
                valid_indices = []
                
                # Collect valid texts and their indices
                for idx, text in enumerate(texts):
                    if text and isinstance(text, str) and len(text.strip()) > 0:
                        valid_texts.append(text)
                        valid_indices.append(idx)
                    results.append(None)  # Initialize with None
                
                if not valid_texts:
                    logger.warning("No valid texts in this partition")
                    return pd.Series(results)
                
                logger.info(f"Processing {len(valid_texts)} valid texts out of {partition_size}")
                
                # Process in smaller sub-batches to avoid timeouts
                sub_batch_size = provider_config.batch_size
                for i in range(0, len(valid_texts), sub_batch_size):
                    sub_batch = valid_texts[i:i + sub_batch_size]
                    sub_indices = valid_indices[i:i + sub_batch_size]
                    
                    # Retry logic with exponential backoff
                    for retry in range(provider_config.max_retries):
                        try:
                            logger.debug(f"Processing sub-batch {i//sub_batch_size + 1} with {len(sub_batch)} texts")
                            
                            # Get embeddings for the batch using LlamaIndex
                            if hasattr(embed_model, 'get_text_embedding_batch'):
                                embeddings = embed_model.get_text_embedding_batch(sub_batch)
                            else:
                                # Fallback to individual processing if batch not supported
                                embeddings = [embed_model.get_text_embedding(text) for text in sub_batch]
                            
                            # Map embeddings back to results
                            for j, embedding in enumerate(embeddings):
                                results[sub_indices[j]] = embedding
                            
                            logger.debug(f"Successfully processed sub-batch {i//sub_batch_size + 1}")
                            break  # Success, exit retry loop
                            
                        except Exception as e:
                            logger.warning(f"Retry {retry + 1}/{provider_config.max_retries} failed: {str(e)[:200]}")
                            
                            if retry < provider_config.max_retries - 1:
                                # Exponential backoff
                                delay = provider_config.retry_delay * (2 ** retry)
                                logger.info(f"Waiting {delay:.1f} seconds before retry...")
                                time.sleep(delay)
                            else:
                                logger.error(f"Failed to process sub-batch after {provider_config.max_retries} retries")
                                # Leave these as None in results
                
                # Log completion stats
                successful = sum(1 for r in results if r is not None)
                elapsed = time.time() - batch_start_time
                logger.info(f"Partition completed: {successful}/{partition_size} embeddings in {elapsed:.2f}s")
                
                return pd.Series(results)
                
            except Exception as e:
                logger.error(f"Critical error in partition processing: {str(e)}")
                return pd.Series([None] * partition_size)
        
        return generate_embeddings_batch
    
    def _create_chunking_udf(self):
        """Create UDF for simple text chunking (non-LlamaIndex)."""
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
                    if chunk.strip():
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
                logger.warning("Semantic chunking requires LlamaIndex nodes. Falling back to sentence.")
                return chunk_text(text)  # Will use sentence method as fallback
            
            else:
                return [text]
        
        return udf(chunk_text, ArrayType(StringType()))
    
    def get_statistics(self, df: DataFrame) -> Dict:
        """Get statistics about embeddings in the DataFrame."""
        stats = {}
        
        total_records = df.count()
        stats["total_records"] = total_records
        
        if "embedding" in df.columns:
            with_embeddings = df.filter(col("embedding").isNotNull()).count()
            stats["records_with_embeddings"] = with_embeddings
            stats["records_without_embeddings"] = total_records - with_embeddings
            stats["embedding_coverage"] = with_embeddings / total_records if total_records > 0 else 0
        
        if "node_id" in df.columns:
            unique_nodes = df.select("node_id").distinct().count()
            stats["unique_nodes"] = unique_nodes
        
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
        
        # Add node relationship stats if available
        if "node_metadata" in df.columns:
            nodes_with_metadata = df.filter(col("node_metadata").isNotNull()).count()
            stats["nodes_with_metadata"] = nodes_with_metadata
        
        return stats