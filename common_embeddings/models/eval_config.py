"""
Evaluation configuration model.

Pydantic model for eval.config.yaml validation and type safety.
"""

from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import yaml
import logging
import os

# Import base config classes to extend
from .config import EmbeddingConfig, ChromaDBConfig
from .config import ChunkingConfig, ProcessingConfig, ExtendedConfig

logger = logging.getLogger(__name__)


class EvalChromaDBConfig(ChromaDBConfig):
    """ChromaDB configuration for evaluation with explicit collection name."""
    
    collection_name: str = Field(
        description="Specific collection name for this evaluation"
    )


class EvaluationDataConfig(BaseModel):
    """Evaluation data configuration."""
    
    articles_path: str = Field(
        default="common_embeddings/evaluate_data/gold_articles.json",
        description="Path to evaluation articles JSON"
    )
    queries_path: str = Field(
        default="common_embeddings/evaluate_data/gold_queries.json",
        description="Path to evaluation queries JSON"
    )
    dataset_type: str = Field(
        default="gold",
        description="Dataset type (gold, generated)"
    )


class EvalConfig(ExtendedConfig):
    """
    Evaluation configuration extending ExtendedConfig.
    
    Inherits embedding, chunking, and processing configs from ExtendedConfig.
    Overrides chromadb to require collection_name.
    """
    
    chromadb: EvalChromaDBConfig = Field(
        description="ChromaDB storage configuration with explicit collection name"
    )
    evaluation_data: EvaluationDataConfig = Field(
        default_factory=EvaluationDataConfig,
        description="Evaluation data configuration"
    )


def load_eval_config(config_path: str = "common_embeddings/eval.config.yaml") -> EvalConfig:
    """
    Load evaluation configuration from YAML file.
    
    Args:
        config_path: Path to eval configuration file
        
    Returns:
        EvalConfig object with validated settings
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Eval config not found: {config_path}")
    
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Empty eval configuration file")
        
        # Create EvalConfig with validation
        config = EvalConfig(**data)
        
        logger.info(f"Loaded eval config from {config_path}")
        logger.info(f"  Provider: {config.embedding.provider}")
        logger.info(f"  Collection: {config.chromadb.collection_name}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load eval config from {config_path}: {e}")
        raise