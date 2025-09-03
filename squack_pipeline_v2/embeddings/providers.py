"""Embedding provider implementations.

EMBEDDING PROVIDER ARCHITECTURE:
================================

This module implements the concrete embedding providers that generate dense vector
representations from text. Each provider uses its own models and tokenization approach.

KEY DESIGN DECISIONS:
--------------------
1. **No LlamaIndex Integration**: Direct API calls to embedding providers
   - No intermediate text processing or chunking frameworks
   - Simplifies architecture and reduces dependencies
   - Text sent directly to provider APIs

2. **Provider-Specific Tokenization**: Each provider handles its own tokenization
   - Voyage AI: Proprietary tokenizer optimized for voyage models
   - OpenAI: tiktoken library (cl100k_base encoder for text-embedding-3)
   - Ollama: Model-specific tokenizers (e.g., SentencePiece for nomic-embed-text)

3. **Batch Processing**: Different batch sizes per provider
   - Voyage: 10 texts per batch (API recommendation for optimal performance)
   - OpenAI: 100 texts per batch (supports larger batches efficiently)
   - Ollama: 1 text at a time (local model processing)

TOKENIZATION DETAILS BY PROVIDER:
---------------------------------

VOYAGE AI:
- **Tokenizer**: Proprietary, optimized for voyage-3 model
- **Context Window**: 16,000 tokens (voyage-3)
- **Truncation**: Automatic server-side if text exceeds limit
- **Special Tokens**: Handled internally by Voyage API
- **Dimension**: 1024 for voyage-3

OPENAI:
- **Tokenizer**: tiktoken (cl100k_base) for text-embedding-3 models
- **Context Window**: 8,191 tokens
- **Truncation**: Automatic server-side truncation
- **Special Tokens**: <|endoftext|> and others handled internally
- **Dimensions**: 1536 (small) or 3072 (large)

OLLAMA (LOCAL):
- **Tokenizer**: Model-specific (e.g., SentencePiece for nomic-embed-text)
- **Context Window**: Varies by model (typically 2048-8192 tokens)
- **Truncation**: Model-dependent behavior
- **Special Tokens**: Model-specific
- **Dimension**: 768 for nomic-embed-text

EMBEDDING GENERATION FLOW:
-------------------------
1. Text received from Silver layer transformers (already concatenated)
2. Provider validates request using Pydantic models
3. Text sent to provider API/server
4. Provider tokenizes text internally
5. Tokens converted to embeddings by model
6. Dense vectors returned to caller
7. Vectors stored in DuckDB as DOUBLE[] arrays

NO PRE-PROCESSING:
-----------------
- No text chunking (providers handle long text)
- No pre-tokenization (providers tokenize internally)
- No text cleaning (preserve original content)
- No stopword removal (models trained on natural text)

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
    """Voyage AI embedding provider.
    
    TOKENIZATION:
    - Uses proprietary tokenizer optimized for voyage models
    - No client-side tokenization - API handles everything
    - Supports up to 16,000 tokens per text (voyage-3)
    - Automatic truncation if text exceeds limit
    - No LlamaIndex preprocessing - text sent directly to API
    """
    
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
        
        TOKENIZATION PROCESS:
        1. Raw text sent to Voyage API without preprocessing
        2. Voyage applies proprietary tokenizer server-side
        3. Tokens converted to 1024-dimensional vectors
        4. No LlamaIndex or local tokenization involved
        
        Args:
            texts: Texts to embed (no chunking required)
            
        Returns:
            EmbeddingResponse with embeddings
        """
        request = self.validate_request(texts)
        client = self._get_client()
        
        # Call Voyage API - tokenization happens server-side
        # input_type="document" optimizes for document-style text
        result = client.embed(
            texts=request.texts,
            model=request.model_name,
            input_type="document"  # Optimized for document embeddings
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
    """OpenAI embedding provider.
    
    TOKENIZATION:
    - Uses tiktoken library with cl100k_base encoder
    - Tokenization happens server-side by OpenAI API
    - Supports up to 8,191 tokens per text
    - Automatic truncation for texts exceeding limit
    - No client-side chunking or LlamaIndex usage
    """
    
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
        
        TOKENIZATION PROCESS:
        1. Raw text sent to OpenAI API
        2. OpenAI tokenizes using tiktoken (cl100k_base encoder)
        3. Tokens converted to vectors (1536 or 3072 dimensions)
        4. No local preprocessing or LlamaIndex involved
        
        Args:
            texts: Texts to embed (no pre-chunking needed)
            
        Returns:
            EmbeddingResponse with embeddings
        """
        request = self.validate_request(texts)
        client = self._get_client()
        
        # Call OpenAI API - tiktoken tokenization happens server-side
        # text-embedding-3 models use cl100k_base tokenizer
        response = client.embeddings.create(
            input=request.texts,
            model=request.model_name  # e.g., text-embedding-3-small
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
    """Ollama local embedding provider.
    
    TOKENIZATION:
    - Uses model-specific tokenizers (e.g., SentencePiece for nomic-embed-text)
    - Tokenization happens within Ollama server
    - Token limits vary by model (typically 2048-8192)
    - No external API calls - runs locally
    - No LlamaIndex or pre-processing required
    """
    
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
        
        TOKENIZATION PROCESS:
        1. Text sent to local Ollama server
        2. Model-specific tokenizer applied (e.g., SentencePiece)
        3. Tokens converted to vectors (typically 768 dimensions)
        4. Processing happens locally - no external API
        5. No LlamaIndex or text chunking used
        
        Args:
            texts: Texts to embed (processed one at a time)
            
        Returns:
            EmbeddingResponse with embeddings
        """
        import requests
        import json
        
        request = self.validate_request(texts)
        embeddings = []
        
        # Ollama processes one at a time - no batch support
        # Each model has its own tokenizer (nomic uses SentencePiece)
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
    
    IMPORTANT ARCHITECTURE NOTES:
    - No LlamaIndex is used anywhere in the embedding pipeline
    - Each provider handles its own tokenization internally
    - Text is sent directly to providers without pre-processing
    - No text chunking - providers handle long texts via truncation
    - Embeddings are generated in batches for efficiency
    
    TOKENIZER SUMMARY BY PROVIDER:
    - Voyage: Proprietary tokenizer, 16k token limit
    - OpenAI: tiktoken (cl100k_base), 8k token limit  
    - Ollama: Model-specific (e.g., SentencePiece), varies by model
    
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