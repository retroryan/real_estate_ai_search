"""Configuration loader for vector embeddings"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .models import VectorIndexConfig, EmbeddingConfig, SearchConfig

# Load environment variables from parent .env file
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


def resolve_env_var(value: str) -> str:
    """Resolve environment variable if value is in ${VAR} format"""
    if value and isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, value)  # Return original if env var not found
    return value


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file (defaults to config.yaml in project root)
        
    Returns:
        Dictionary with configuration
    """
    if config_path is None:
        # Look for config.yaml in project root first, then fallback to vectors directory
        project_root = Path(__file__).parent.parent.parent
        root_config = project_root / "config.yaml"
        vector_config = Path(__file__).parent / "config.yaml"
        
        if root_config.exists():
            config_path = root_config
        elif vector_config.exists():
            config_path = vector_config
        else:
            # Default to root location even if not found (will error with clear message)
            config_path = root_config
    
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
    embedding_config = config["embedding"]
    provider = embedding_config.get("provider", "ollama")
    
    # Handle the models structure to extract provider-specific config
    if "models" in embedding_config:
        models_config = embedding_config.get("models", {})
        
        if provider == "voyage" and "voyage" in models_config:
            voyage_config = models_config["voyage"]
            embedding_config["voyage_model"] = voyage_config.get("model")
            embedding_config["voyage_api_key"] = resolve_env_var(voyage_config.get("api_key"))
            embedding_config["voyage_dimension"] = voyage_config.get("dimension")
        
        elif provider == "openai" and "openai" in models_config:
            openai_config = models_config["openai"]
            embedding_config["openai_model"] = openai_config.get("model")
            embedding_config["openai_api_key"] = resolve_env_var(openai_config.get("api_key"))
            embedding_config["openai_dimension"] = openai_config.get("dimension")
        
        elif provider == "gemini" and "gemini" in models_config:
            gemini_config = models_config["gemini"]
            embedding_config["gemini_model"] = gemini_config.get("model")
            embedding_config["gemini_api_key"] = resolve_env_var(gemini_config.get("api_key"))
            embedding_config["gemini_dimension"] = gemini_config.get("dimension")
        
        elif provider == "ollama" and "ollama" in models_config:
            ollama_config = models_config["ollama"]
            embedding_config["ollama_model"] = ollama_config.get("model")
            embedding_config["ollama_base_url"] = ollama_config.get("base_url", embedding_config.get("ollama_base_url"))
            embedding_config["ollama_dimension"] = ollama_config.get("dimension")
        
        # Remove models key as it's not part of EmbeddingConfig
        embedding_config = {k: v for k, v in embedding_config.items() if k != "models"}
    
    return EmbeddingConfig(**embedding_config)


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