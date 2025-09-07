"""Wikipedia writer for Elasticsearch."""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from squack_pipeline_v2.writers.elastic.base import ElasticsearchWriterBase
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


# ============================================================================
# WIKIPEDIA DOCUMENT MODEL
# ============================================================================

class WikipediaDocument(BaseModel):
    """Wikipedia document for Elasticsearch - single model for transformation."""
    
    # Core fields
    page_id: str  # ES expects string
    title: str
    url: str = ""
    article_filename: str = ""
    
    # Content fields
    long_summary: str = ""
    short_summary: str = ""
    content_length: int = 0
    content_loaded: bool = False
    content_loaded_at: datetime = Field(default_factory=datetime.now)
    
    # Location fields (note: no location geo_point in wikipedia template)
    city: str = ""
    state: str = ""
    
    # Neighborhood association fields (from Gold layer)
    neighborhood_ids: List[str] = Field(default_factory=list)
    neighborhood_names: List[str] = Field(default_factory=list)
    primary_neighborhood_name: str = ""
    neighborhood_count: int = 0
    has_neighborhood_association: bool = False
    
    # Metadata fields
    categories: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    article_quality_score: float = 0.0
    article_quality: str = ""
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Embedding fields
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# TRANSFORMATION FUNCTION
# ============================================================================

def transform_wikipedia(record: Dict[str, Any], embedding_model: str) -> WikipediaDocument:
    """Transform DuckDB Wikipedia record to Elasticsearch document.
    
    Data types from gold_wikipedia:
    - categories: VARCHAR (JSON string)
    - key_topics: VARCHAR[] (array)
    - neighborhood_ids: VARCHAR[] (array)
    - neighborhood_names: VARCHAR[] (array)
    - embedding_vector: DOUBLE[] (returned as tuple from DuckDB)
    
    Args:
        record: Raw dictionary from DuckDB query
        embedding_model: Name of the embedding model used
        
    Returns:
        WikipediaDocument ready for Elasticsearch
    """
    # Parse categories from JSON string (categories is VARCHAR in Gold layer)
    categories = []
    categories_raw = record.get('categories')
    if categories_raw:
        try:
            # Categories is stored as JSON string in Gold layer
            categories = json.loads(categories_raw) or []
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback for malformed JSON - split on comma
            categories = [c.strip() for c in categories_raw.split(',') if c.strip()]
    
    # Convert embedding to list for Elasticsearch
    # DuckDB returns DOUBLE[] arrays - ensure it's a list for ES
    embedding_vector = record.get('embedding_vector', [])
    embedding_list = list(embedding_vector) if embedding_vector else []
    
    # Get embedding timestamp - should always exist for Wikipedia
    embedded_at = record.get('embedding_generated_at')
    if not embedded_at:
        raise ValueError(f"Missing embedding_generated_at for page_id {record.get('page_id')}")
    
    # Handle nullable datetime fields with defaults
    content_loaded_at = record.get('content_loaded_at') or datetime.now()
    last_updated = record.get('last_updated') or datetime.now()
    
    # Extract neighborhood fields - these are VARCHAR[] arrays from Gold layer
    # DuckDB returns arrays as lists, None if NULL
    neighborhood_ids = record.get('neighborhood_ids', []) or []
    neighborhood_names = record.get('neighborhood_names', []) or []
    primary_neighborhood_name = record.get('primary_neighborhood_name', '') or ''
    neighborhood_count = record.get('neighborhood_count', 0) or 0
    has_neighborhood_association = record.get('has_neighborhood_association', False) or False
    
    # key_topics is VARCHAR[] array from Gold layer
    # DuckDB returns it as a list, None if NULL
    key_topics = record.get('key_topics', []) or []
    
    # Create WikipediaDocument - let Pydantic handle validation
    # page_id needs string conversion as ES requires string IDs
    page_id_value = record.get('page_id')
    page_id_str = f"{page_id_value}" if page_id_value is not None else ""
    
    return WikipediaDocument(
        page_id=page_id_str,  # ES requires string IDs
        title=record.get('title', '') or '',
        url=record.get('url', '') or '',
        article_filename=record.get('article_filename', '') or '',
        long_summary=record.get('long_summary', '') or '',
        short_summary=record.get('short_summary', '') or '',
        content_length=record.get('content_length', 0) or 0,
        content_loaded=record.get('content_loaded', False) or False,
        content_loaded_at=content_loaded_at,
        city=record.get('city', '') or '',
        state=record.get('state', '') or '',
        neighborhood_ids=neighborhood_ids,
        neighborhood_names=neighborhood_names,
        primary_neighborhood_name=primary_neighborhood_name,
        neighborhood_count=neighborhood_count,
        has_neighborhood_association=has_neighborhood_association,
        categories=categories,
        key_topics=key_topics,
        relevance_score=record.get('relevance_score', 0.0) or 0.0,
        article_quality_score=record.get('article_quality_score', 0.0) or 0.0,
        article_quality=record.get('article_quality', '') or '',
        last_updated=last_updated,
        embedding=embedding_list,
        embedding_model=embedding_model,
        embedding_dimension=len(embedding_list),
        embedded_at=embedded_at
    )


# ============================================================================
# WIKIPEDIA WRITER CLASS
# ============================================================================

class WikipediaWriter(ElasticsearchWriterBase):
    """Writer for indexing Wikipedia articles to Elasticsearch."""
    
    @log_stage("Elasticsearch: Index Wikipedia")
    def index_wikipedia(
        self,
        table_name: str = "gold_wikipedia",
        index_name: str = "wikipedia",
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """Index Wikipedia articles to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing Wikipedia articles
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch (smaller due to larger docs)
            
        Returns:
            Indexing statistics
        """
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        # Create transform function with embedded model name
        def transform(record: Dict[str, Any]) -> WikipediaDocument:
            return transform_wikipedia(record, self.embedding_model)
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transform=transform,
            id_field="page_id",
            batch_size=batch_size
        )