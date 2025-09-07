"""Wikipedia writer for Elasticsearch."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from squack_pipeline_v2.writers.elastic.base import ElasticsearchWriterBase
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import PipelineSettings

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
    
    Args:
        record: Raw dictionary from DuckDB query
        embedding_model: Name of the embedding model used
        
    Returns:
        WikipediaDocument ready for Elasticsearch
    """
    # Parse categories from JSON string if present
    categories = []
    categories_raw = record.get('categories')
    if categories_raw:
        try:
            # Try to parse as JSON
            parsed = json.loads(categories_raw)
            categories = list(parsed) if parsed else []
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback to comma-separated
            categories = [c.strip() for c in str(categories_raw).split(',') if c.strip()]
    
    # Convert tuple embedding to list
    embedding_vector = record.get('embedding_vector', tuple())
    embedding_list = list(embedding_vector) if embedding_vector else []
    
    # Get embedding timestamp
    embedded_at = record.get('embedding_generated_at')
    if not embedded_at:
        embedded_at = datetime.now()
    
    # Handle nullable datetime fields
    content_loaded_at = record.get('content_loaded_at')
    if not content_loaded_at:
        content_loaded_at = datetime.now()
    
    last_updated = record.get('last_updated')
    if not last_updated:
        last_updated = datetime.now()
    
    # Create WikipediaDocument with all transformations
    return WikipediaDocument(
        page_id=str(record['page_id']),  # Convert int to string for ES
        title=record['title'],
        url=record.get('url', ''),
        article_filename=record.get('article_filename', ''),
        long_summary=record.get('long_summary', ''),
        short_summary=record.get('short_summary', ''),
        content_length=int(record.get('content_length', 0)),
        content_loaded=bool(record.get('content_loaded', False)),
        content_loaded_at=content_loaded_at,
        city=record.get('city', ''),
        state=record.get('state', ''),
        categories=categories,
        key_topics=record.get('key_topics', []),
        relevance_score=float(record.get('relevance_score', 0.0)),
        article_quality_score=float(record.get('article_quality_score', 0.0)),
        article_quality=record.get('article_quality', ''),
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