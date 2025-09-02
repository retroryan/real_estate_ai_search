"""Embedding provider implementations.

Following DuckDB best practices:
- Providers handle external API communication
- Pydantic models validate API responses
- Bulk operations for efficiency
- No runtime type checking with hasattr/isinstance
"""

from typing import List, Optional
import logging
from pydantic import BaseModel, Field
from squack_pipeline_v2.embeddings.base import (
    EmbeddingProvider,
    EmbeddingResponse
)

logger = logging.getLogger(__name__)


class VoyageAPIResponse(BaseModel):
    """Voyage API response model."""
    embeddings: List[List[float]]
    total_tokens: int = 0  # Default to 0 if not present


class OpenAIAPIResponse(BaseModel):
    """OpenAI API response model."""
    data: List[dict]
    usage: dict = Field(default_factory=dict)


class VoyageProvider(EmbeddingProvider):
    """Voyage AI embedding provider."""
    
    def __init__(self, api_key: str, model_name: str, dimension: int):
        """Initialize Voyage provider.
        
        Args:
            api_key: Voyage API key
            model_name: Model name
            dimension: Embedding dimension
        """
        super().__init__(api_key, model_name, dimension)
        self._client: Optional[object] = None
    
    def _get_client(self):
        """Lazy load Voyage client."""
        if self._client is None:
            try:
                import voyageai
                self._client = voyageai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("voyageai package not installed")
        return self._client
    
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generate embeddings using Voyage AI.
        
        Args:
            texts: Texts to embed
            
        Returns:
            EmbeddingResponse with embeddings
        """
        request = self.validate_request(texts)
        client = self._get_client()
        
        # Call Voyage API
        result = client.embed(
            texts=request.texts,
            model=request.model_name,
            input_type="document"
        )
        
        # Create structured response from API result
        # Voyage API returns an object with embeddings and may have total_tokens
        parsed_result = VoyageAPIResponse(
            embeddings=result.embeddings,
            total_tokens=0  # Default value, Voyage may not always return token count
        )
        
        return EmbeddingResponse(
            embeddings=parsed_result.embeddings,
            model_name=self.model_name,
            dimension=self.dimension,
            token_count=parsed_result.total_tokens
        )
    
    def get_batch_size(self) -> int:
        """Get recommended batch size for Voyage."""
        return 10  # Voyage recommends small batches


class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: str, model_name: str, dimension: int):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model_name: Model name
            dimension: Embedding dimension
        """
        super().__init__(api_key, model_name, dimension)
        self._client: Optional[object] = None
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed")
        return self._client
    
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generate embeddings using OpenAI.
        
        Args:
            texts: Texts to embed
            
        Returns:
            EmbeddingResponse with embeddings
        """
        request = self.validate_request(texts)
        client = self._get_client()
        
        # Call OpenAI API
        response = client.embeddings.create(
            input=request.texts,
            model=request.model_name
        )
        
        # Extract embeddings
        embeddings = [item.embedding for item in response.data]
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model_name=self.model_name,
            dimension=self.dimension,
            token_count=response.usage.total_tokens if response.usage else 0
        )
    
    def get_batch_size(self) -> int:
        """Get recommended batch size for OpenAI."""
        return 100  # OpenAI supports larger batches


class OllamaProvider(EmbeddingProvider):
    """Ollama local embedding provider."""
    
    def __init__(self, model_name: str, dimension: int, base_url: str):
        """Initialize Ollama provider.
        
        Args:
            model_name: Model name
            dimension: Embedding dimension
            base_url: Ollama server URL
        """
        super().__init__(api_key="", model_name=model_name, dimension=dimension)
        self.base_url = base_url
    
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generate embeddings using local Ollama.
        
        Args:
            texts: Texts to embed
            
        Returns:
            EmbeddingResponse with embeddings
        """
        import requests
        import json
        
        request = self.validate_request(texts)
        embeddings = []
        
        # Ollama processes one at a time
        for text in request.texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": request.model_name,
                    "prompt": text
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                embeddings.append(result["embedding"])
            else:
                raise RuntimeError(f"Ollama error: {response.text}")
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model_name=self.model_name,
            dimension=self.dimension,
            token_count=0  # Ollama doesn't report tokens
        )
    
    def get_batch_size(self) -> int:
        """Get recommended batch size for Ollama."""
        return 1  # Process one at a time for local model


def create_provider(provider_type: str, api_key: str = "", model_name: str = "", base_url: str = None) -> EmbeddingProvider:
    """Factory function to create embedding providers.
    
    Args:
        provider_type: Type of provider (voyage, openai, ollama)
        api_key: API key if required
        model_name: Model name to use
        base_url: Base URL for Ollama provider
        
    Returns:
        EmbeddingProvider instance
    """
    # Default dimensions for each provider/model
    default_dimensions = {
        "voyage": {"voyage-3": 1024},
        "openai": {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072},
        "ollama": {"nomic-embed-text": 768}
    }
    
    providers = {
        "voyage": VoyageProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider
    }
    
    if provider_type not in providers:
        raise ValueError(f"Unknown provider: {provider_type}")
    
    provider_class = providers[provider_type]
    
    # Get dimension based on provider and model
    provider_dims = default_dimensions.get(provider_type, {})
    dimension = provider_dims.get(model_name, 1024)  # fallback to 1024
    
    if provider_type == "ollama":
        return provider_class(
            model_name=model_name or "nomic-embed-text", 
            dimension=dimension,
            base_url=base_url or "http://localhost:11434"
        )
    else:
        return provider_class(
            api_key=api_key, 
            model_name=model_name, 
            dimension=dimension
        )