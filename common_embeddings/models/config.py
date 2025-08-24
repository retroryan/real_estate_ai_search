"""
Configuration models specific to embeddings processing.

Core configuration models (Config, EmbeddingConfig, ChromaDBConfig) are 
imported from property_finder_models.
"""

from pydantic import BaseModel, Field
from pathlib import Path
import yaml
import logging
from typing import Optional

from property_finder_models import Config as BaseConfig
from .enums import ChunkingMethod

logger = logging.getLogger(__name__)


class ChunkingConfig(BaseModel):
    """
    Configuration for text chunking strategies.
    
    Follows LlamaIndex best practices for node parsing.
    """
    
    method: ChunkingMethod = Field(
        default=ChunkingMethod.SEMANTIC,
        description="Chunking method to use"
    )
    
    # Simple chunking parameters
    chunk_size: int = Field(
        default=800,
        ge=128,
        le=2048,
        description="Maximum chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=200,
        description="Overlap between chunks"
    )
    
    # Semantic chunking parameters
    breakpoint_percentile: int = Field(
        default=90,
        ge=50,
        le=99,
        description="Percentile for semantic breakpoints"
    )
    buffer_size: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Buffer size for semantic chunking"
    )
    
    # Processing options
    split_oversized_chunks: bool = Field(
        default=False,
        description="Split chunks exceeding max size"
    )
    max_chunk_size: int = Field(
        default=1000,
        ge=200,
        le=2000,
        description="Maximum size for any chunk"
    )


class ProcessingConfig(BaseModel):
    """
    Configuration for batch processing and performance.
    """
    
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for processing"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum parallel workers"
    )
    show_progress: bool = Field(
        default=True,
        description="Show progress indicators"
    )
    rate_limit_delay: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Delay between API calls in seconds"
    )
    document_batch_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Batch size for processing documents during chunking"
    )


class ExtendedConfig(BaseConfig):
    """
    Extended configuration for embeddings with chunking and processing.
    
    Extends the base Config from property_finder_models with embedding-specific
    configuration options.
    """
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)


def load_config_from_yaml(config_path: str = "config.yaml"):
    """
    Load configuration from YAML file and create ExtendedConfig instance.
    
    Returns an ExtendedConfig that includes chunking and processing configs.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        logger.info(f"Config file not found at {config_path}, using defaults")
        return ExtendedConfig()
    
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            logger.info("Empty config file, using defaults")
            return ExtendedConfig()
        
        # Build config dict with all sections
        config_data = {}
        
        # Add embedding config if present
        if 'embedding' in data:
            config_data['embedding'] = data['embedding']
        
        # Add chromadb config if present
        if 'chromadb' in data:
            config_data['chromadb'] = data['chromadb']
        
        # Add chunking config if present
        if 'chunking' in data:
            config_data['chunking'] = ChunkingConfig(**data['chunking'])
        
        # Add processing config if present
        if 'processing' in data:
            config_data['processing'] = ProcessingConfig(**data['processing'])
        
        # Create ExtendedConfig with all data
        config = ExtendedConfig(**config_data)
        
        logger.info(f"Loaded config from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        logger.info("Using default configuration")
        return ExtendedConfig()