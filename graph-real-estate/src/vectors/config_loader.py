"""Configuration loader for vector embeddings"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .models import VectorIndexConfig, EmbeddingConfig, SearchConfig


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file (defaults to src/vectors/config.yaml)
        
    Returns:
        Dictionary with configuration
    """
    if config_path is None:
        # Default to config.yaml in the same directory
        config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables if set
    if os.getenv("OPENAI_API_KEY"):
        config["embedding"]["openai_api_key"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        config["embedding"]["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
    
    return config


def get_embedding_config(config_path: Optional[str] = None) -> EmbeddingConfig:
    """
    Get embedding configuration
    
    Args:
        config_path: Path to config file
        
    Returns:
        EmbeddingConfig instance
    """
    config = load_config(config_path)
    return EmbeddingConfig(**config["embedding"])


def get_vector_index_config(config_path: Optional[str] = None) -> VectorIndexConfig:
    """
    Get vector index configuration
    
    Args:
        config_path: Path to config file
        
    Returns:
        VectorIndexConfig instance
    """
    config = load_config(config_path)
    vector_config = VectorIndexConfig(**config["vector_index"])
    
    # Auto-adjust dimensions based on embedding model
    embedding_config = get_embedding_config(config_path)
    vector_config.vector_dimensions = embedding_config.get_dimensions()
    
    return vector_config


def get_search_config(config_path: Optional[str] = None) -> SearchConfig:
    """
    Get search configuration
    
    Args:
        config_path: Path to config file
        
    Returns:
        SearchConfig instance
    """
    config = load_config(config_path)
    return SearchConfig(**config["search"])