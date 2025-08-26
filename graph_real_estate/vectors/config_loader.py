"""Configuration loader for vector embeddings using Pydantic models"""
from pathlib import Path
from typing import Optional

from graph_real_estate.config.settings import get_settings
from graph_real_estate.config.models import EmbeddingConfig, VectorIndexConfig, SearchConfig


def get_embedding_config(config_path: Optional[str] = None) -> EmbeddingConfig:
    """Get embedding configuration
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        EmbeddingConfig instance
    """
    if config_path:
        from graph_real_estate.config.settings import Settings
        settings = Settings(Path(config_path))
    else:
        settings = get_settings()
    
    return settings.embedding


def get_vector_index_config(config_path: Optional[str] = None) -> VectorIndexConfig:
    """Get vector index configuration
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        VectorIndexConfig instance
    """
    if config_path:
        from graph_real_estate.config.settings import Settings
        settings = Settings(Path(config_path))
    else:
        settings = get_settings()
    
    # Auto-adjust dimensions based on embedding model
    config = settings.vector_index
    embedding_config = settings.embedding
    
    # Create a new config with updated dimensions if needed
    if config.vector_dimensions != embedding_config.get_dimensions():
        from config.models import VectorIndexConfig as VIC
        config = VIC(
            index_name=config.index_name,
            vector_dimensions=embedding_config.get_dimensions(),
            similarity_function=config.similarity_function,
            node_label=config.node_label,
            embedding_property=config.embedding_property,
            source_property=config.source_property
        )
    
    return config


def get_search_config(config_path: Optional[str] = None) -> SearchConfig:
    """Get search configuration
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        SearchConfig instance
    """
    if config_path:
        from graph_real_estate.config.settings import Settings
        settings = Settings(Path(config_path))
    else:
        settings = get_settings()
    
    return settings.search