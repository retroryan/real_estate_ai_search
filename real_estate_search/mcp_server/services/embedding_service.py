"""Embedding service for generating vector embeddings."""

import os
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

from ..config.settings import EmbeddingConfig
from ..utils.logging import get_logger


logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embedding provider."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize Voyage provider.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Voyage client."""
        try:
            import voyageai
            self._client = voyageai.Client(api_key=self.config.api_key)
            logger.info(f"Voyage client initialized with model {self.config.model_name}")
        except ImportError:
            logger.error("voyageai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Voyage client: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        result = self._client.embed(
            [text],
            model=self.config.model_name,
            truncation=True
        )
        return result.embeddings[0]
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            result = self._client.embed(
                batch,
                model=self.config.model_name,
                truncation=True
            )
            embeddings.extend(result.embeddings)
        
        return embeddings


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize OpenAI provider.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.api_key)
            logger.info(f"OpenAI client initialized with model {self.config.model_name}")
        except ImportError:
            logger.error("openai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = self._client.embeddings.create(
            input=text,
            model=self.config.model_name
        )
        return response.data[0].embedding
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            response = self._client.embeddings.create(
                input=batch,
                model=self.config.model_name
            )
            embeddings.extend([data.embedding for data in response.data])
        
        return embeddings


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embedding provider."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize Gemini provider.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self._client = genai
            logger.info(f"Gemini client initialized with model {self.config.model_name}")
        except ImportError:
            logger.error("google-generativeai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        result = self._client.embed_content(
            model=self.config.model_name,
            content=text
        )
        return result['embedding']
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        embeddings = []
        for text in texts:
            result = self._client.embed_content(
                model=self.config.model_name,
                content=text
            )
            embeddings.append(result['embedding'])
        
        return embeddings


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embedding provider."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize Ollama provider.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        self.base_url = "http://localhost:11434"
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        import requests
        
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.config.model_name,
                "prompt": text
            },
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.generate_embedding(text) for text in texts]


class EmbeddingService:
    """Service for managing embeddings."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize embedding service.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        self.provider = self._create_provider()
    
    def _create_provider(self) -> EmbeddingProvider:
        """Create the appropriate embedding provider.
        
        Returns:
            Embedding provider instance
        """
        provider_map = {
            "voyage": VoyageEmbeddingProvider,
            "openai": OpenAIEmbeddingProvider,
            "gemini": GeminiEmbeddingProvider,
            "ollama": OllamaEmbeddingProvider
        }
        
        provider_class = provider_map.get(self.config.provider)
        if not provider_class:
            raise ValueError(f"Unknown embedding provider: {self.config.provider}")
        
        logger.info(f"Creating {self.config.provider} embedding provider")
        return provider_class(self.config)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self.provider.generate_embedding(text)
            
            # Validate dimension
            if len(embedding) != self.config.dimension:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self.config.dimension}, "
                    f"got {len(embedding)}"
                )
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter empty texts
        valid_texts = [t for t in texts if t]
        if not valid_texts:
            return []
        
        try:
            embeddings = self.provider.generate_embeddings(valid_texts)
            
            # Validate dimensions
            for i, embedding in enumerate(embeddings):
                if len(embedding) != self.config.dimension:
                    logger.warning(
                        f"Embedding {i} dimension mismatch: expected {self.config.dimension}, "
                        f"got {len(embedding)}"
                    )
            
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def create_query_embedding(self, query: str) -> Dict[str, Any]:
        """Create embedding for a search query.
        
        Args:
            query: Search query
            
        Returns:
            Query embedding with metadata
        """
        embedding = self.embed_text(query)
        
        return {
            "vector": embedding,
            "dimension": len(embedding),
            "model": self.config.model_name,
            "provider": self.config.provider
        }