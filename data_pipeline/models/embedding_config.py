"""
Embedding configuration models for data pipeline.

Clean, modular Pydantic-based configuration for embeddings.
Self-contained with no external dependencies to common_embeddings.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum
import os


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    VOYAGE = "voyage"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    COHERE = "cohere"


class EmbeddingConfig(BaseModel):
    """
    Embedding service configuration supporting multiple providers.
    
    This is a clean, self-contained configuration that can be:
    - Serialized/deserialized for broadcast in Spark
    - Validated with Pydantic
    - Used to create embedding providers
    """
    
    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.VOYAGE,
        description="Embedding provider to use"
    )
    
    # Voyage settings
    voyage_api_key: Optional[str] = Field(None, description="Voyage API key")
    voyage_model: str = Field(
        default="voyage-3",
        description="Voyage model name"
    )
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model name"
    )
    
    # Ollama settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    ollama_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name"
    )
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(None, description="Google API key")
    gemini_model: str = Field(
        default="models/embedding-001",
        description="Gemini model name"
    )
    
    # Cohere settings
    cohere_api_key: Optional[str] = Field(None, description="Cohere API key")
    cohere_model: str = Field(
        default="embed-english-v3.0",
        description="Cohere model name"
    )
    
    @field_validator('voyage_api_key')
    @classmethod
    def load_voyage_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Voyage API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.VOYAGE and not v:
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v
    
    @field_validator('openai_api_key')
    @classmethod
    def load_openai_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load OpenAI API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.OPENAI and not v:
            v = os.getenv('OPENAI_API_KEY')
            if not v:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")
        return v
    
    @field_validator('gemini_api_key')
    @classmethod
    def load_gemini_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Gemini API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.GEMINI and not v:
            v = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set for Gemini provider")
        return v
    
    @field_validator('cohere_api_key')
    @classmethod
    def load_cohere_key(cls, v: Optional[str], info) -> Optional[str]:
        """Load Cohere API key from environment if needed."""
        if info.data.get('provider') == EmbeddingProvider.COHERE and not v:
            v = os.getenv('COHERE_API_KEY')
            if not v:
                raise ValueError("COHERE_API_KEY must be set for Cohere provider")
        return v
    
    def get_model_identifier(self) -> str:
        """Get a unique identifier for the current model configuration."""
        if self.provider == EmbeddingProvider.VOYAGE:
            return f"voyage_{self.voyage_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.OPENAI:
            return f"openai_{self.openai_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.OLLAMA:
            return f"ollama_{self.ollama_model.replace('-', '_')}"
        elif self.provider == EmbeddingProvider.GEMINI:
            model_name = self.gemini_model.split('/')[-1].replace('-', '_')
            return f"gemini_{model_name}"
        elif self.provider == EmbeddingProvider.COHERE:
            return f"cohere_{self.cohere_model.replace('-', '_')}"
        else:
            return f"{self.provider.value}_unknown"
    
    def get_embedding_dimension(self) -> int:
        """Get expected embedding dimension for the configured model."""
        # Known dimensions for common models
        dimensions = {
            # Voyage models
            "voyage-3": 1024,
            "voyage-large-2": 1536,
            
            # OpenAI models
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            
            # Ollama models
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            
            # Gemini models
            "embedding-001": 768,
            
            # Cohere models
            "embed-english-v3.0": 1024,
            "embed-multilingual-v3.0": 1024,
        }
        
        # Get the model name based on provider
        if self.provider == EmbeddingProvider.VOYAGE:
            model = self.voyage_model
        elif self.provider == EmbeddingProvider.OPENAI:
            model = self.openai_model
        elif self.provider == EmbeddingProvider.OLLAMA:
            model = self.ollama_model
        elif self.provider == EmbeddingProvider.GEMINI:
            model = self.gemini_model.split('/')[-1]
        elif self.provider == EmbeddingProvider.COHERE:
            model = self.cohere_model
        else:
            return 768  # Default dimension
        
        # Look up dimension
        for key, dim in dimensions.items():
            if key in model:
                return dim
        
        # Default dimensions by provider
        provider_defaults = {
            EmbeddingProvider.VOYAGE: 1024,
            EmbeddingProvider.OPENAI: 1536,
            EmbeddingProvider.OLLAMA: 768,
            EmbeddingProvider.GEMINI: 768,
            EmbeddingProvider.COHERE: 1024,
        }
        
        return provider_defaults.get(self.provider, 768)


class ProcessingConfig(BaseModel):
    """Configuration for batch processing and performance."""
    
    batch_size: int = Field(
        default=32,
        ge=1,
        le=1000,
        description="Batch size for embedding calls"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries for failed embeddings"
    )
    
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for embedding API calls"
    )


class EmbeddingPipelineConfig(BaseModel):
    """
    Complete configuration for embedding pipeline.
    
    This is the root configuration used in the data pipeline.
    """
    
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding provider configuration"
    )
    
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration"
    )
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "EmbeddingPipelineConfig":
        """
        Create configuration from a dictionary.
        
        Handles various config formats from YAML/JSON.
        """
        # Handle flat provider config
        if 'provider' in config_dict and 'embedding' not in config_dict:
            provider = config_dict['provider']
            models_config = config_dict.get('models', {})
            provider_config = models_config.get(provider, {})
            
            embedding_config = {
                'provider': provider,
                f'{provider}_model': provider_config.get('model'),
                f'{provider}_api_key': provider_config.get('api_key'),
            }
            
            # Handle Ollama base URL
            if provider == 'ollama':
                embedding_config['ollama_base_url'] = provider_config.get('base_url', 'http://localhost:11434')
            
            config_dict = {
                'embedding': embedding_config,
                'processing': config_dict.get('processing', {})
            }
        
        return cls(**config_dict)
    
    @classmethod
    def from_pipeline_config(cls, pipeline_config) -> "EmbeddingPipelineConfig":
        """
        Create from a pipeline configuration object.
        
        Handles legacy configuration formats.
        """
        config_dict = {}
        
        # Extract provider
        if hasattr(pipeline_config, 'provider'):
            provider = pipeline_config.provider
        elif hasattr(pipeline_config, 'get') and callable(pipeline_config.get):
            provider = pipeline_config.get('provider', 'voyage')
        else:
            provider = 'voyage'
        
        # Extract models config
        if hasattr(pipeline_config, 'models'):
            models_config = pipeline_config.models
        elif hasattr(pipeline_config, 'get') and callable(pipeline_config.get):
            models_config = pipeline_config.get('models', {})
        else:
            models_config = {}
        
        # Get provider-specific config
        provider_config = models_config.get(provider, {}) if isinstance(models_config, dict) else {}
        
        # Build embedding config
        embedding_config = {'provider': provider}
        
        if provider == 'voyage':
            embedding_config['voyage_model'] = provider_config.get('model', 'voyage-3')
        elif provider == 'openai':
            embedding_config['openai_model'] = provider_config.get('model', 'text-embedding-3-small')
        elif provider == 'ollama':
            embedding_config['ollama_model'] = provider_config.get('model', 'nomic-embed-text')
            embedding_config['ollama_base_url'] = provider_config.get('base_url', 'http://localhost:11434')
        elif provider == 'gemini':
            embedding_config['gemini_model'] = provider_config.get('model', 'models/embedding-001')
        elif provider == 'cohere':
            embedding_config['cohere_model'] = provider_config.get('model', 'embed-english-v3.0')
        
        config_dict['embedding'] = embedding_config
        
        # Extract processing config if available
        if hasattr(pipeline_config, 'processing'):
            config_dict['processing'] = pipeline_config.processing
        elif hasattr(pipeline_config, 'get') and callable(pipeline_config.get):
            config_dict['processing'] = pipeline_config.get('processing', {})
        
        return cls(**config_dict)