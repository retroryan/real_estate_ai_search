"""
Pydantic models for Wikipedia embedding pipeline.
Clean, simple data models focused on Wikipedia location content.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class QueryType(str, Enum):
    """Types of location-based queries."""
    GEOGRAPHIC = "geographic"
    LANDMARK = "landmark"
    HISTORICAL = "historical"
    RECREATIONAL = "recreational"
    CULTURAL = "cultural"
    ADMINISTRATIVE = "administrative"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OLLAMA = "ollama"
    GEMINI = "gemini"
    VOYAGE = "voyage"


class EmbeddingMethod(str, Enum):
    """Embedding generation methods."""
    TRADITIONAL = "traditional"
    AUGMENTED = "augmented"
    BOTH = "both"


class ChunkingMethod(str, Enum):
    """Chunking strategies for documents."""
    SIMPLE = "simple"
    SEMANTIC = "semantic"


class VectorStoreProvider(str, Enum):
    """Supported vector store providers."""
    CHROMADB = "chromadb"
    ELASTICSEARCH = "elasticsearch"


# Configuration Models
class EmbeddingConfig(BaseModel):
    """Embedding service configuration for Wikipedia content."""
    provider: EmbeddingProvider = Field(default=EmbeddingProvider.OLLAMA)
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "nomic-embed-text"
    # Gemini settings
    gemini_api_key: Optional[str] = None
    gemini_model: str = "models/embedding-001"
    # Voyage settings
    voyage_api_key: Optional[str] = None
    voyage_model: str = "voyage-3"
    
    @validator('gemini_api_key', pre=True, always=True)
    def check_gemini_key(cls, v, values):
        if values.get('provider') == EmbeddingProvider.GEMINI and not v:
            import os
            v = os.getenv('GOOGLE_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY must be set for Gemini provider")
        return v
    
    @validator('voyage_api_key', pre=True, always=True)
    def check_voyage_key(cls, v, values):
        if values.get('provider') == EmbeddingProvider.VOYAGE and not v:
            import os
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v


class ChromaDBConfig(BaseModel):
    """ChromaDB configuration for Wikipedia embeddings."""
    path: str = "./data/wiki_chroma_db"
    collection_prefix: str = "wiki_embeddings"


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration for Wikipedia embeddings."""
    host: str = "localhost"
    port: int = 9200
    index_prefix: str = "wiki_embeddings"
    username: Optional[str] = None
    password: Optional[str] = None
    vector_field: str = "embedding"
    text_field: str = "content"
    metadata_field: str = "metadata"
    
    @validator('username', pre=True, always=True)
    def load_username_from_env(cls, v):
        if v is None:
            import os
            return os.getenv('ELASTICSEARCH_USERNAME')
        return v
    
    @validator('password', pre=True, always=True)
    def load_password_from_env(cls, v):
        if v is None:
            import os
            return os.getenv('ELASTICSEARCH_PASSWORD')
        return v


class VectorStoreConfig(BaseModel):
    """Vector store configuration supporting multiple providers."""
    provider: VectorStoreProvider
    chromadb: Optional[ChromaDBConfig] = None
    elasticsearch: Optional[ElasticsearchConfig] = None
    
    @validator('chromadb', pre=True, always=True)
    def check_chromadb_config(cls, v, values):
        if values.get('provider') == VectorStoreProvider.CHROMADB and not v:
            return ChromaDBConfig()
        return v
    
    @validator('elasticsearch', pre=True, always=True)
    def check_elasticsearch_config(cls, v, values):
        if values.get('provider') == VectorStoreProvider.ELASTICSEARCH and not v:
            return ElasticsearchConfig()
        return v


class DataConfig(BaseModel):
    """Wikipedia data source configuration."""
    source_dir: str = "./data/wikipedia/pages"
    registry_path: str = "./data/wikipedia/REGISTRY.json"
    attribution_path: str = "./data/wikipedia/attribution/WIKIPEDIA_ATTRIBUTION.json"
    wikipedia_db: str = "./data/wikipedia/wikipedia.db"  # Path to SQLite database with summaries
    max_articles: Optional[int] = None  # Limit articles for testing


class ChunkingConfig(BaseModel):
    """Chunking configuration for Wikipedia articles."""
    method: ChunkingMethod = Field(default=ChunkingMethod.SEMANTIC)
    # Simple parser settings
    chunk_size: int = Field(default=800, ge=128, le=2048)
    chunk_overlap: int = Field(default=100, ge=0, le=200)
    # Semantic parser settings (recommended for Wikipedia)
    breakpoint_percentile: int = Field(default=90, ge=50, le=99)
    buffer_size: int = Field(default=2, ge=1, le=10)
    # Embedding method selection
    embedding_method: EmbeddingMethod = Field(default=EmbeddingMethod.TRADITIONAL)
    # Augmented embedding settings
    max_summary_words: int = Field(default=100, ge=50, le=200, description="Max words for summary context")
    max_total_words: int = Field(default=500, ge=200, le=1000, description="Max total words per augmented chunk")
    # Chunk size management
    split_oversized_chunks: bool = Field(default=False, description="Split chunks that exceed max_total_words")


class TestingConfig(BaseModel):
    """Testing configuration for Wikipedia queries."""
    queries_path: str = "./data/wiki_test_queries.json"
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)


class Config(BaseModel):
    """Main configuration for Wikipedia embedding pipeline."""
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    data: DataConfig
    chunking: ChunkingConfig
    testing: TestingConfig
    
    @classmethod
    def from_yaml(cls, config_path: str = "wiki_embed/config.yaml") -> "Config":
        """Load and validate configuration from YAML file."""
        import yaml
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)


# Wikipedia Data Models
class WikiLocation(BaseModel):
    """Location information from Wikipedia registry."""
    path: str
    city: str
    state: str
    country: str
    crawl_date: str
    articles: int
    has_pages: bool
    size_mb: float


class PageSummary(BaseModel):
    """Summary data from wikipedia.db page_summaries table."""
    page_id: int
    summary: str
    key_topics: List[str] = Field(default_factory=list)
    best_city: Optional[str] = None
    best_county: Optional[str] = None
    best_state: Optional[str] = None
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class WikiArticle(BaseModel):
    """Wikipedia article with metadata."""
    page_id: str
    title: str
    content: str
    url: Optional[str] = None
    location: Optional[str] = None  # e.g., "Park City, Utah"
    state: Optional[str] = None
    country: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    word_count: int = 0
    # Summary fields (populated when available)
    summary_data: Optional[PageSummary] = None
    
    @validator('word_count', always=True)
    def calculate_word_count(cls, v, values):
        if 'content' in values:
            return len(values['content'].split())
        return v


class LocationQuery(BaseModel):
    """Location-based test query for Wikipedia content."""
    query: str
    expected_articles: List[str]  # List of page_ids
    location_context: Optional[str] = None  # e.g., "Utah", "California"
    query_type: QueryType = QueryType.GEOGRAPHIC
    description: Optional[str] = None


class QueryResult(BaseModel):
    """Result from a Wikipedia query test."""
    query: str
    retrieved_ids: List[str]
    expected_ids: List[str]
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1_score: float = Field(ge=0, le=1)
    query_type: Optional[QueryType] = None
    location_context: Optional[str] = None
    
    def calculate_metrics(self) -> None:
        """Calculate precision, recall, and F1 score."""
        if not self.retrieved_ids:
            self.precision = 0.0
            self.recall = 0.0
            self.f1_score = 0.0
            return
        
        retrieved_set = set(self.retrieved_ids)
        expected_set = set(self.expected_ids)
        
        true_positives = len(retrieved_set & expected_set)
        
        self.precision = true_positives / len(retrieved_set) if retrieved_set else 0
        self.recall = true_positives / len(expected_set) if expected_set else 0
        
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0


class ModelComparison(BaseModel):
    """Comparison results for Wikipedia embedding models."""
    model_name: str
    embedding_method: Optional[EmbeddingMethod] = None  # Track which method was used
    avg_precision: float = Field(ge=0, le=1)
    avg_recall: float = Field(ge=0, le=1)
    avg_f1: float = Field(ge=0, le=1)
    total_queries: int
    results: List[QueryResult]
    results_by_type: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    def calculate_averages(self) -> None:
        """Calculate average metrics across all queries and by type."""
        if not self.results:
            self.avg_precision = 0.0
            self.avg_recall = 0.0
            self.avg_f1 = 0.0
            return
        
        # Overall averages
        self.avg_precision = sum(r.precision for r in self.results) / len(self.results)
        self.avg_recall = sum(r.recall for r in self.results) / len(self.results)
        self.avg_f1 = sum(r.f1_score for r in self.results) / len(self.results)
        self.total_queries = len(self.results)
        
        # Averages by query type
        type_metrics = {}
        for result in self.results:
            if result.query_type:
                type_name = result.query_type.value
                if type_name not in type_metrics:
                    type_metrics[type_name] = {'precision': [], 'recall': [], 'f1': []}
                type_metrics[type_name]['precision'].append(result.precision)
                type_metrics[type_name]['recall'].append(result.recall)
                type_metrics[type_name]['f1'].append(result.f1_score)
        
        self.results_by_type = {}
        for type_name, metrics in type_metrics.items():
            self.results_by_type[type_name] = {
                'avg_precision': sum(metrics['precision']) / len(metrics['precision']),
                'avg_recall': sum(metrics['recall']) / len(metrics['recall']),
                'avg_f1': sum(metrics['f1']) / len(metrics['f1']),
                'count': len(metrics['precision'])
            }


# For compatibility with existing code that imports TestQuery
TestQuery = LocationQuery