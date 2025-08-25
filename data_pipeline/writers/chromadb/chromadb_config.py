"""
ChromaDB writer configuration models.

This module provides Pydantic models for ChromaDB writer configurations,
ensuring type safety and validation for vector database operations.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from data_pipeline.writers.base import WriterConfig


class ChromaDBWriterConfig(WriterConfig):
    """Base configuration for ChromaDB writers."""
    
    persist_directory: str = Field(
        default="./data/chroma_db",
        description="Directory for ChromaDB persistence"
    )
    
    collection_prefix: str = Field(
        default="embeddings",
        description="Prefix for collection names"
    )
    
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for similarity search"
    )
    
    embedding_dimension: Optional[int] = Field(
        default=None,
        description="Embedding dimension (auto-detected if None)"
    )
    
    batch_size: int = Field(
        default=500,
        gt=0,
        le=5000,
        description="Batch size for ChromaDB operations"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for failed operations"
    )
    
    anonymized_telemetry: bool = Field(
        default=False,
        description="Enable anonymized telemetry for ChromaDB"
    )
    
    @field_validator("distance_metric")
    @classmethod
    def validate_distance_metric(cls, v: str) -> str:
        """Validate distance metric."""
        valid_metrics = ["cosine", "l2", "ip"]  # inner product
        if v.lower() not in valid_metrics:
            raise ValueError(f"Invalid distance metric: {v}. Must be one of {valid_metrics}")
        return v.lower()


class PropertyChromaConfig(ChromaDBWriterConfig):
    """Configuration specific to property ChromaDB writer."""
    
    collection_name: str = Field(
        default="properties_embeddings",
        description="Collection name for property embeddings"
    )
    
    metadata_fields: List[str] = Field(
        default_factory=lambda: [
            "listing_id",
            "price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "property_type",
            "city",
            "state",
            "zip_code",
            "price_category",
            "size_category"
        ],
        description="Metadata fields to store with embeddings"
    )
    
    searchable_fields: List[str] = Field(
        default_factory=lambda: [
            "city",
            "state",
            "property_type",
            "price_category"
        ],
        description="Fields to enable filtering on"
    )


class NeighborhoodChromaConfig(ChromaDBWriterConfig):
    """Configuration specific to neighborhood ChromaDB writer."""
    
    collection_name: str = Field(
        default="neighborhoods_embeddings",
        description="Collection name for neighborhood embeddings"
    )
    
    metadata_fields: List[str] = Field(
        default_factory=lambda: [
            "neighborhood_id",
            "neighborhood_name",
            "city",
            "state",
            "population",
            "median_income",
            "median_age",
            "income_bracket",
            "demographic_completeness"
        ],
        description="Metadata fields to store with embeddings"
    )
    
    searchable_fields: List[str] = Field(
        default_factory=lambda: [
            "city",
            "state",
            "income_bracket"
        ],
        description="Fields to enable filtering on"
    )


class WikipediaChromaConfig(ChromaDBWriterConfig):
    """Configuration specific to Wikipedia ChromaDB writer."""
    
    collection_name: str = Field(
        default="wikipedia_embeddings",
        description="Collection name for Wikipedia embeddings"
    )
    
    metadata_fields: List[str] = Field(
        default_factory=lambda: [
            "page_id",
            "title",
            "url",
            "best_city",
            "best_state",
            "confidence_score",
            "relevance_score",
            "location_relevance_score",
            "relevance_category",
            "location_specificity"
        ],
        description="Metadata fields to store with embeddings"
    )
    
    searchable_fields: List[str] = Field(
        default_factory=lambda: [
            "best_city",
            "best_state",
            "relevance_category",
            "location_specificity"
        ],
        description="Fields to enable filtering on"
    )
    
    min_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for storing articles"
    )