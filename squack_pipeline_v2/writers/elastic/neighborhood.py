"""Neighborhood writer for Elasticsearch."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from squack_pipeline_v2.writers.elastic.base import ElasticsearchWriterBase
from squack_pipeline_v2.writers.elastic.property import GeoPoint  # Reuse from property module
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


# ============================================================================
# NEIGHBORHOOD DOCUMENT MODEL
# ============================================================================

class NeighborhoodDocument(BaseModel):
    """Neighborhood document for Elasticsearch - single model for transformation."""
    
    # Core fields
    neighborhood_id: str
    name: str
    city: str
    state: str
    population: int = 0
    
    # Scores and ratings
    walkability_score: float = 0.0
    school_rating: float = 0.0
    overall_livability_score: float = 0.0
    
    # Location
    location: GeoPoint
    
    # Text and list fields
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
    lifestyle_tags: List[str] = Field(default_factory=list)
    
    # Complex fields
    demographics: Dict[str, Any] = Field(default_factory=dict)
    wikipedia_correlations: Dict[str, Any] = Field(default_factory=dict)
    
    # Historical data - simple annual records
    historical_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Embedding fields
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# TRANSFORMATION FUNCTION
# ============================================================================

def transform_neighborhood(record: Dict[str, Any], embedding_model: str) -> NeighborhoodDocument:
    """Transform DuckDB neighborhood record to Elasticsearch document.
    
    Args:
        record: Raw dictionary from DuckDB query
        embedding_model: Name of the embedding model used
        
    Returns:
        NeighborhoodDocument ready for Elasticsearch
    """
    # Build GeoPoint from center coordinates
    location = GeoPoint(
        lat=record.get('center_latitude', 0.0) or 0.0,
        lon=record.get('center_longitude', 0.0) or 0.0
    )
    
    # Convert embedding to list for Elasticsearch
    embedding_vector = record.get('embedding_vector', [])
    embedding_list = list(embedding_vector) if embedding_vector else []
    
    # Get embedding timestamp
    embedded_at = record.get('embedding_generated_at') or datetime.now()
    
    # Handle demographics JSON from DuckDB
    import json
    demographics_raw = record.get('demographics', {})
    try:
        demographics = json.loads(demographics_raw) if demographics_raw else {}
    except (TypeError, json.JSONDecodeError):
        demographics = demographics_raw or {}
    
    # Handle wikipedia_correlations JSON from DuckDB
    correlations_raw = record.get('wikipedia_correlations')
    try:
        wikipedia_correlations = json.loads(correlations_raw) if correlations_raw else {}
    except (TypeError, json.JSONDecodeError):
        wikipedia_correlations = correlations_raw or {}
    
    # Handle historical_data JSON from DuckDB
    historical_raw = record.get('historical_data')
    historical_data = []
    
    if historical_raw:
        try:
            # DuckDB stores JSON as string, parse it
            historical_data = json.loads(historical_raw)
        except (TypeError, json.JSONDecodeError):
            # If already parsed, use as-is
            try:
                # Check if it's already a list by attempting list operations
                historical_data = list(historical_raw)
            except (TypeError, ValueError):
                logger.warning(f"Failed to parse historical_data for {record.get('neighborhood_id', 'unknown')}")
                historical_data = []
    
    # Create NeighborhoodDocument - let Pydantic handle validation
    return NeighborhoodDocument(
        neighborhood_id=record.get('neighborhood_id', ''),
        name=record.get('name', ''),
        city=record.get('city', ''),
        state=record.get('state', ''),
        population=record.get('population', 0) or 0,  # Handle None without int()
        walkability_score=record.get('walkability_score', 0.0) or 0.0,
        school_rating=record.get('school_rating', 0.0) or 0.0,
        overall_livability_score=record.get('overall_livability_score', 0.0) or 0.0,
        location=location,
        description=record.get('description', ''),
        amenities=record.get('amenities', []) or [],
        lifestyle_tags=record.get('lifestyle_tags', []) or [],
        demographics=demographics,
        wikipedia_correlations=wikipedia_correlations,
        historical_data=historical_data,
        embedding=embedding_list,
        embedding_model=embedding_model,
        embedding_dimension=len(embedding_list),
        embedded_at=embedded_at
    )


# ============================================================================
# NEIGHBORHOOD WRITER CLASS
# ============================================================================

class NeighborhoodWriter(ElasticsearchWriterBase):
    """Writer for indexing neighborhoods to Elasticsearch."""
    
    @log_stage("Elasticsearch: Index neighborhoods")
    def index_neighborhoods(
        self,
        table_name: str = "gold_neighborhoods",
        index_name: str = "neighborhoods",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index neighborhoods to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing neighborhoods
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        # Create transform function with embedded model name
        def transform(record: Dict[str, Any]) -> NeighborhoodDocument:
            return transform_neighborhood(record, self.embedding_model)
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transform=transform,
            id_field="neighborhood_id",
            batch_size=batch_size
        )