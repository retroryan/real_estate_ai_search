"""Pydantic models for configuration"""
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pathlib import Path


class DatabaseConfig(BaseModel):
    """Neo4j database configuration"""
    model_config = ConfigDict(frozen=True)
    
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    user: str = Field(default="neo4j", description="Database username")
    password: str = Field(default="password", description="Database password")
    database: str = Field(default="neo4j", description="Database name")
    
    @field_validator('uri')
    @classmethod
    def validate_uri(cls, v: str) -> str:
        if not v.startswith(('bolt://', 'neo4j://', 'neo4j+s://', 'bolt+s://')):
            raise ValueError(f"Invalid Neo4j URI scheme: {v}")
        return v


class APIConfig(BaseModel):
    """API configuration for external services"""
    model_config = ConfigDict(frozen=True)
    
    base_url: str = Field(default="http://localhost:8000", description="API base URL")
    timeout: int = Field(default=30, gt=0, description="Request timeout in seconds")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0, description="Delay between retries in seconds")


class VoyageModelConfig(BaseModel):
    """Voyage embedding model configuration"""
    model_config = ConfigDict(frozen=True)
    
    model: str = Field(default="voyage-3", description="Voyage model name")
    api_key: Optional[str] = Field(default=None, description="Voyage API key")
    dimension: int = Field(default=1024, gt=0, description="Embedding dimension")


class OllamaModelConfig(BaseModel):
    """Ollama embedding model configuration"""
    model_config = ConfigDict(frozen=True)
    
    model: str = Field(default="nomic-embed-text", description="Ollama model name")
    base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    dimension: int = Field(default=1024, gt=0, description="Embedding dimension")


class OpenAIModelConfig(BaseModel):
    """OpenAI embedding model configuration"""
    model_config = ConfigDict(frozen=True)
    
    model: str = Field(default="text-embedding-3-small", description="OpenAI model name")
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    dimension: int = Field(default=1536, gt=0, description="Embedding dimension")


class GeminiModelConfig(BaseModel):
    """Gemini embedding model configuration"""
    model_config = ConfigDict(frozen=True)
    
    model: str = Field(default="models/embedding-001", description="Gemini model name")
    api_key: Optional[str] = Field(default=None, description="Gemini API key")
    dimension: int = Field(default=1024, gt=0, description="Embedding dimension")


class EmbeddingConfig(BaseModel):
    """Embedding configuration"""
    model_config = ConfigDict(frozen=True)
    
    provider: Literal["voyage", "ollama", "openai", "gemini"] = Field(
        default="voyage", 
        description="Embedding provider"
    )
    batch_size: int = Field(default=50, gt=0, description="Batch size for processing")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=2, ge=0, description="Delay between retries in seconds")
    
    # Model-specific configurations
    voyage: Optional[VoyageModelConfig] = None
    ollama: Optional[OllamaModelConfig] = None
    openai: Optional[OpenAIModelConfig] = None
    gemini: Optional[GeminiModelConfig] = None
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str, info) -> str:
        """Ensure the selected provider has configuration"""
        return v
    
    def get_active_model_config(self) -> BaseModel:
        """Get configuration for the active provider"""
        configs = {
            "voyage": self.voyage,
            "ollama": self.ollama,
            "openai": self.openai,
            "gemini": self.gemini
        }
        config = configs.get(self.provider)
        if config is None:
            # Return default config for the provider
            defaults = {
                "voyage": VoyageModelConfig(),
                "ollama": OllamaModelConfig(),
                "openai": OpenAIModelConfig(),
                "gemini": GeminiModelConfig()
            }
            return defaults[self.provider]
        return config
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions for active provider"""
        return self.get_active_model_config().dimension
    
    def get_model_name(self) -> str:
        """Get model name for active provider"""
        return self.get_active_model_config().model


class VectorIndexConfig(BaseModel):
    """Vector index configuration"""
    model_config = ConfigDict(frozen=True)
    
    index_name: str = Field(default="property_embeddings", description="Index name")
    vector_dimensions: int = Field(default=1024, gt=0, description="Vector dimensions")
    similarity_function: Literal["cosine", "euclidean"] = Field(
        default="cosine", 
        description="Similarity function"
    )
    node_label: str = Field(default="Property", description="Node label for indexing")
    embedding_property: str = Field(default="embedding", description="Property name for embeddings")
    source_property: str = Field(default="description", description="Source text property")


class SearchConfig(BaseModel):
    """Search configuration"""
    model_config = ConfigDict(frozen=True)
    
    default_top_k: int = Field(default=10, gt=0, description="Default number of results")
    use_graph_boost: bool = Field(default=True, description="Use graph relationships for boosting")
    vector_weight: float = Field(default=0.6, ge=0, le=1, description="Weight for vector similarity")
    graph_weight: float = Field(default=0.2, ge=0, le=1, description="Weight for graph relationships")
    features_weight: float = Field(default=0.2, ge=0, le=1, description="Weight for feature matching")
    min_similarity: float = Field(default=0.01, ge=0, le=1, description="Minimum similarity threshold")
    
    @field_validator('vector_weight')
    @classmethod
    def validate_weights(cls, v: float, info) -> float:
        """Validate that weights sum to 1.0"""
        if 'graph_weight' in info.data and 'features_weight' in info.data:
            total = v + info.data['graph_weight'] + info.data['features_weight']
            if abs(total - 1.0) > 0.001:  # Allow small floating point errors
                raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v


class GraphRealEstateConfig(BaseModel):
    """Main configuration for graph_real_estate application"""
    model_config = ConfigDict(frozen=True)
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_index: VectorIndexConfig = Field(default_factory=VectorIndexConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "GraphRealEstateConfig":
        """Load configuration from YAML file"""
        import yaml
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Handle environment variable resolution
        data = cls._resolve_env_vars(data)
        
        # Handle embedding models structure
        if 'embedding' in data and 'models' in data['embedding']:
            models = data['embedding'].pop('models')
            for provider, config in models.items():
                data['embedding'][provider] = config
        
        return cls(**data)
    
    @staticmethod
    def _resolve_env_vars(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve environment variables in config"""
        import os
        import re
        
        def resolve_value(value):
            if isinstance(value, str):
                # Match ${VAR} or ${VAR:-default}
                pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
                matches = re.findall(pattern, value)
                for var_name, default in matches:
                    env_value = os.getenv(var_name, default if default else "")
                    value = value.replace(f"${{{var_name}}}", env_value)
                    if default:
                        value = value.replace(f"${{{var_name}:-{default}}}", env_value)
                return value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value
        
        return resolve_value(data)
    
    def to_yaml(self) -> str:
        """Export configuration to YAML format"""
        import yaml
        
        data = self.model_dump(exclude_none=True)
        
        # Restructure embedding config for YAML
        if 'embedding' in data:
            models = {}
            for provider in ['voyage', 'ollama', 'openai', 'gemini']:
                if provider in data['embedding']:
                    models[provider] = data['embedding'].pop(provider)
            if models:
                data['embedding']['models'] = models
        
        return yaml.dump(data, default_flow_style=False, sort_keys=False)