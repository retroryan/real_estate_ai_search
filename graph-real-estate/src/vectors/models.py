"""Pydantic models for vector embeddings configuration"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class VectorIndexConfig(BaseModel):
    """Configuration for Neo4j vector indexes"""
    index_name: str = Field(default="property_embeddings", description="Name of the vector index")
    vector_dimensions: int = Field(default=768, description="Dimension of embedding vectors")
    similarity_function: Literal["cosine", "euclidean"] = Field(
        default="cosine", 
        description="Similarity function for vector search"
    )
    node_label: str = Field(default="Property", description="Neo4j node label")
    embedding_property: str = Field(
        default="descriptionEmbedding", 
        description="Property name for storing embeddings"
    )
    source_property: str = Field(
        default="description", 
        description="Property name containing text to embed"
    )


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation"""
    provider: Literal["ollama", "openai", "gemini"] = Field(
        default="ollama",
        description="Embedding provider to use"
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
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Gemini API key"
    )
    gemini_model: str = Field(
        default="models/embedding-001",
        description="Gemini embedding model"
    )
    
    # Processing settings
    batch_size: int = Field(
        default=100,
        description="Number of properties to process in each batch"
    )
    show_progress: bool = Field(
        default=True,
        description="Show progress bar during embedding generation"
    )
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions for the configured model"""
        dimensions_map = {
            # Ollama models
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            # OpenAI models
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            # Gemini models
            "models/embedding-001": 768,
        }
        
        model_key = self.ollama_model if self.provider == "ollama" else (
            self.openai_model if self.provider == "openai" else self.gemini_model
        )
        
        return dimensions_map.get(model_key, 768)


class SearchConfig(BaseModel):
    """Configuration for hybrid search"""
    default_top_k: int = Field(
        default=10,
        description="Default number of results to return"
    )
    use_graph_boost: bool = Field(
        default=True,
        description="Whether to boost scores using graph metrics"
    )
    vector_weight: float = Field(
        default=0.6,
        description="Weight for vector similarity score"
    )
    graph_weight: float = Field(
        default=0.2,
        description="Weight for graph centrality score"
    )
    features_weight: float = Field(
        default=0.2,
        description="Weight for feature richness score"
    )
    min_similarity: float = Field(
        default=0.3,
        description="Minimum similarity score for results"
    )