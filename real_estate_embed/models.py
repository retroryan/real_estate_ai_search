"""
Pydantic models for type safety and validation in the embedding pipeline.
Simple, clean data models without unnecessary abstraction.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from pathlib import Path


# Configuration Models
class EmbeddingConfig(BaseModel):
    """Embedding service configuration - supports ollama, gemini, or voyage."""
    provider: str = Field(default="ollama", pattern="^(ollama|gemini|voyage)$")
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
        if values.get('provider') == 'gemini' and not v:
            import os
            v = os.getenv('GOOGLE_API_KEY')
            if not v:
                raise ValueError("GOOGLE_API_KEY must be set for Gemini provider")
        return v
    
    @validator('voyage_api_key', pre=True, always=True)
    def check_voyage_key(cls, v, values):
        if values.get('provider') == 'voyage' and not v:
            import os
            v = os.getenv('VOYAGE_API_KEY')
            if not v:
                raise ValueError("VOYAGE_API_KEY must be set for Voyage provider")
        return v


class ChromaConfig(BaseModel):
    """ChromaDB vector store configuration."""
    path: str = "./chroma_db"
    collection_prefix: str = "embeddings"


class DataConfig(BaseModel):
    """Data source configuration."""
    source_dir: str = "./real_estate_data"


class ChunkingConfig(BaseModel):
    """Chunking configuration - supports simple or semantic methods."""
    method: str = Field(default="simple", pattern="^(simple|semantic)$")
    # Simple parser settings
    chunk_size: int = Field(default=512, ge=128, le=2048)
    chunk_overlap: int = Field(default=50, ge=0, le=200)
    # Semantic parser settings (only used when method="semantic")
    breakpoint_percentile: int = Field(default=95, ge=50, le=99)
    buffer_size: int = Field(default=1, ge=1, le=10)


class Config(BaseModel):
    """Main configuration model - validates the entire config.yaml."""
    embedding: EmbeddingConfig
    chromadb: ChromaConfig
    data: DataConfig
    chunking: ChunkingConfig
    
    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Config":
        """Load and validate configuration from YAML file."""
        import yaml
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)


# Data Models for Queries and Results
class TestQuery(BaseModel):
    """Test query with expected results for evaluation."""
    query: str
    expected_results: List[str]
    description: Optional[str] = None


class QueryResult(BaseModel):
    """Result from a single query test with metrics."""
    query: str
    retrieved_ids: List[str]
    expected_ids: List[str]
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1_score: float = Field(ge=0, le=1)
    
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
    """Comparison results between embedding models."""
    model_name: str
    avg_precision: float = Field(ge=0, le=1)
    avg_recall: float = Field(ge=0, le=1)
    avg_f1: float = Field(ge=0, le=1)
    total_queries: int
    results: List[QueryResult]
    
    def calculate_averages(self) -> None:
        """Calculate average metrics across all queries."""
        if not self.results:
            self.avg_precision = 0.0
            self.avg_recall = 0.0
            self.avg_f1 = 0.0
            return
        
        self.avg_precision = sum(r.precision for r in self.results) / len(self.results)
        self.avg_recall = sum(r.recall for r in self.results) / len(self.results)
        self.avg_f1 = sum(r.f1_score for r in self.results) / len(self.results)
        self.total_queries = len(self.results)