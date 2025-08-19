"""
Global settings for wiki_embed module, following DSPy pattern.
Provides clean configuration management for vector stores and searchers.
"""

import os
from pathlib import Path
from typing import Optional
from wiki_embed.base.vector_store import VectorStore, VectorSearcher

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file if it exists."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return True
    except ImportError:
        # python-dotenv not installed, skip
        pass
    return False

# Load environment variables on import
load_env()


class WikiEmbedSettings:
    """Global settings for wiki_embed module."""
    
    def __init__(self):
        self.vector_store: Optional[VectorStore] = None
        self.vector_searcher: Optional[VectorSearcher] = None
        self.config = None
    
    def configure(self, vector_store: VectorStore = None, vector_searcher: VectorSearcher = None, config = None):
        """Configure global vector store and searcher instances."""
        if vector_store:
            self.vector_store = vector_store
        if vector_searcher:
            self.vector_searcher = vector_searcher
        if config:
            self.config = config


# Global settings instance
settings = WikiEmbedSettings()


# Dynamic loading of vector store implementations
def get_vector_store_class(provider: str):
    """Dynamically load vector store class based on provider."""
    if provider == "chromadb":
        from wiki_embed.chromadb import ChromaDBStore
        return ChromaDBStore
    elif provider == "elasticsearch":
        from wiki_embed.elasticsearch import ElasticsearchStore
        return ElasticsearchStore
    else:
        raise ValueError(f"Unknown vector store provider: {provider}")


def get_vector_searcher_class(provider: str):
    """Dynamically load vector searcher class based on provider."""
    if provider == "chromadb":
        from wiki_embed.chromadb import ChromaDBSearcher
        return ChromaDBSearcher
    elif provider == "elasticsearch":
        from wiki_embed.elasticsearch import ElasticsearchSearcher
        return ElasticsearchSearcher
    else:
        raise ValueError(f"Unknown vector searcher provider: {provider}")


def configure_from_config(config):
    """Helper to configure global settings from config file."""
    provider = config.vector_store.provider.value
    
    # Dynamically load classes
    store_cls = get_vector_store_class(provider)
    searcher_cls = get_vector_searcher_class(provider)
    
    vector_store = store_cls(config)
    vector_searcher = searcher_cls(config, "")  # Collection name set later
    
    # Configure globally
    settings.configure(
        vector_store=vector_store,
        vector_searcher=vector_searcher,
        config=config
    )