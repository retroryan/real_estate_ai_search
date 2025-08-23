# CORRELATION.md: Complete Integration Plan for Moving Correlation Functionality to Common Ingest

## Executive Summary

This document provides a comprehensive plan to completely move the correlation functionality from `common_embeddings/correlation/` into `common_ingest/` and integrate it as part of the data ingestion pipeline. **The goal is to provide API endpoints that allow downstream consumers to ingest both real estate and Wikipedia data with their associated embeddings in a single, unified interface.**

## Key Implementation Principles

- **Python Naming Conventions**: Follow PEP 8 strictly (snake_case for functions/variables, PascalCase for classes)
- **Logging Over Print**: Use Python's logging module exclusively, no print statements
- **Constructor-Based Dependency Injection**: All dependencies passed through constructors
- **Modular Organization**: Clear separation of concerns with well-organized module structure
- **Pydantic Models**: All data structures defined as Pydantic models for validation
- **NO PARTIAL UPDATES**: Change everything or change nothing (atomic operations)
- **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
- **Demo Quality Focus**: This is for a high-quality demo, not production - skip performance testing, fault-tolerance, benchmarking
- **NO MIGRATION PHASES**: There does not need to be any backwards compatibility

## Current State Analysis

### Existing Correlation Components in common_embeddings/

1. **Models** (`correlation/models.py`):
   - `SourceDataCache`: Caching for source data with hit/miss tracking
   - `CorrelationResult`: Result of correlating embedding with source
   - `EnrichedEntity`: Entity enriched with embedding data
   - `CorrelationReport`: Comprehensive correlation operation report
   - `BulkCorrelationRequest`: Request configuration for bulk operations

2. **Correlation Manager** (`correlation/correlation_manager.py`):
   - Core correlation logic between embeddings and source data
   - Identifier extraction based on entity type
   - Source data loading from JSON files and SQLite
   - Bulk correlation with parallel processing
   - Multi-chunk document reconstruction

3. **Enrichment Engine** (`correlation/enrichment_engine.py`):
   - Entity-specific enrichment processors
   - Parallel bulk enrichment capabilities
   - Property, neighborhood, and Wikipedia-specific enrichments
   - Similarity search integration points

### Target State in common_ingest/

The correlation functionality will be fully integrated into `common_ingest/` as:
- New services layer for correlation and enrichment
- Extended API endpoints with embedding correlation
- Unified response models with embedded vectors
- Integrated caching and performance optimization

## Implementation Plan

### Phase 1: Core Services Integration

#### 1.1 Create New Services Structure
```
common_ingest/
├── services/
│   ├── __init__.py
│   ├── correlation_service.py     # Main correlation logic
│   ├── enrichment_service.py      # Entity enrichment
│   └── embedding_service.py       # Embedding retrieval
```

#### 1.2 Move and Refactor Models
```
common_ingest/
├── models/
│   ├── correlation.py    # Correlation-specific models
│   └── enriched.py      # Enriched entity models
```

**Key Changes**:
- Merge correlation models with existing property/neighborhood/wikipedia models
- Create unified `EnrichedProperty`, `EnrichedNeighborhood`, `EnrichedWikipediaArticle` models
- Add embedding fields directly to base models

#### 1.3 Service Implementation

**CorrelationService** (`services/correlation_service.py`):
```python
class CorrelationService:
    def __init__(self, 
                 property_loader: PropertyLoader,
                 neighborhood_loader: NeighborhoodLoader,
                 wikipedia_loader: WikipediaLoader,
                 embedding_service: EmbeddingService):
        self.property_loader = property_loader
        self.neighborhood_loader = neighborhood_loader
        self.wikipedia_loader = wikipedia_loader
        self.embedding_service = embedding_service
        self._cache = {}
    
    async def correlate_properties_with_embeddings(self, 
                                                  properties: List[Property],
                                                  collection_name: str) -> List[EnrichedProperty]:
        """Correlate properties with their embeddings from ChromaDB."""
        pass
    
    async def correlate_neighborhoods_with_embeddings(self,
                                                     neighborhoods: List[Neighborhood],
                                                     collection_name: str) -> List[EnrichedNeighborhood]:
        """Correlate neighborhoods with their embeddings."""
        pass
```

**EmbeddingService** (`services/embedding_service.py`):
```python
class EmbeddingService:
    def __init__(self, chromadb_path: str):
        self.chromadb_client = chromadb.PersistentClient(path=chromadb_path)
    
    async def get_embeddings_by_ids(self, 
                                   collection_name: str,
                                   entity_ids: List[str]) -> Dict[str, EmbeddingData]:
        """Bulk retrieve embeddings by entity IDs."""
        pass
    
    async def get_all_embeddings(self, 
                                collection_name: str,
                                entity_type: Optional[EntityType] = None) -> List[EmbeddingData]:
        """Get all embeddings from a collection with optional filtering."""
        pass
```

### Phase 2: API Endpoint Enhancement

#### 2.1 Extended Property Endpoints

**Update** `api/routers/properties.py`:
```python
@router.get("/properties/enriched", response_model=List[EnrichedPropertyResponse])
async def get_enriched_properties(
    include_embeddings: bool = Query(True, description="Include embedding vectors"),
    collection_name: Optional[str] = Query(None, description="ChromaDB collection name"),
    correlation_service: CorrelationService = Depends(get_correlation_service)
):
    """Get all properties with correlated embeddings."""
    properties = await property_loader.load_all()
    
    if include_embeddings and collection_name:
        enriched = await correlation_service.correlate_properties_with_embeddings(
            properties, collection_name
        )
        return enriched
    
    return properties

@router.get("/properties/{listing_id}/with-embeddings")
async def get_property_with_embeddings(
    listing_id: str,
    collection_name: str,
    correlation_service: CorrelationService = Depends(get_correlation_service)
):
    """Get a single property with its embeddings."""
    pass
```

#### 2.2 New Neighborhood Endpoints

**Create** `api/routers/neighborhoods.py`:
```python
@router.get("/neighborhoods/enriched")
async def get_enriched_neighborhoods(
    include_embeddings: bool = Query(True),
    collection_name: Optional[str] = Query(None),
    correlation_service: CorrelationService = Depends(get_correlation_service)
):
    """Get all neighborhoods with correlated embeddings."""
    pass
```

#### 2.3 Wikipedia Endpoints

**Create** `api/routers/wikipedia.py`:
```python
@router.get("/wikipedia/articles/enriched")
async def get_enriched_wikipedia_articles(
    include_embeddings: bool = Query(True),
    collection_name: Optional[str] = Query(None),
    page_ids: Optional[List[int]] = Query(None),
    correlation_service: CorrelationService = Depends(get_correlation_service)
):
    """Get Wikipedia articles with their embeddings."""
    pass
```

### Phase 3: Response Models and Schemas

#### 3.1 Enriched Response Models

**Create** `api/schemas/enriched.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class EmbeddingData(BaseModel):
    """Embedding data with metadata."""
    embedding_id: str
    vector: Optional[List[float]] = None
    chunk_index: Optional[int] = None
    metadata: Dict[str, Any]
    created_at: datetime

class EnrichedPropertyResponse(BaseModel):
    """Property with correlated embeddings."""
    listing_id: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: float
    address: AddressResponse
    features: List[str]
    
    # Embedding data
    embeddings: Optional[List[EmbeddingData]] = None
    embedding_count: int = 0
    has_embeddings: bool = False
    correlation_confidence: float = Field(0.0, ge=0.0, le=1.0)
    
    # Enrichment metadata
    enriched_at: Optional[datetime] = None
    enrichment_source: Optional[str] = None

class EnrichedNeighborhoodResponse(BaseModel):
    """Neighborhood with embeddings."""
    neighborhood_id: str
    neighborhood_name: str
    city: str
    state: str
    median_price: float
    demographics: Dict[str, Any]
    amenities: List[str]
    
    # Embedding data
    embeddings: Optional[List[EmbeddingData]] = None
    embedding_count: int = 0
    has_embeddings: bool = False

class BulkCorrelationResponse(BaseModel):
    """Response for bulk correlation operations."""
    total_entities: int
    successful_correlations: int
    failed_correlations: int
    processing_time_seconds: float
    entities: List[Union[EnrichedPropertyResponse, EnrichedNeighborhoodResponse]]
    report: CorrelationReportResponse
```

### Phase 4: Data Flow Integration

#### 4.1 Unified Loading and Correlation Pipeline

```python
# In api/routers/properties.py

@router.post("/properties/bulk-enrich")
async def bulk_enrich_properties(
    request: BulkEnrichmentRequest,
    property_loader: PropertyLoader = Depends(get_property_loader),
    correlation_service: CorrelationService = Depends(get_correlation_service),
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
) -> BulkCorrelationResponse:
    """
    Bulk load and enrich properties with embeddings.
    
    1. Load properties from source files
    2. Correlate with embeddings from ChromaDB
    3. Apply entity-specific enrichments
    4. Return enriched data with correlation report
    """
    # Load base data
    properties = await property_loader.load_all()
    
    # Correlate with embeddings
    correlated = await correlation_service.correlate_properties_with_embeddings(
        properties, request.collection_name
    )
    
    # Apply enrichments
    enriched = await enrichment_service.bulk_enrich(
        correlated,
        include_similar=request.include_similar,
        parallel_workers=request.parallel_workers
    )
    
    # Generate report
    report = correlation_service.generate_report()
    
    return BulkCorrelationResponse(
        total_entities=len(enriched),
        successful_correlations=report.successful_correlations,
        failed_correlations=report.failed_correlations,
        processing_time_seconds=report.processing_time_seconds,
        entities=enriched,
        report=report
    )
```

#### 4.2 Caching Strategy

```python
# In services/correlation_service.py

class CorrelationService:
    def __init__(self, ...):
        # Use Redis or in-memory cache for correlation results
        self._correlation_cache: Dict[str, CorrelationResult] = {}
        self._ttl = 3600  # 1 hour cache TTL
    
    def _cache_key(self, entity_id: str, collection_name: str) -> str:
        return f"{collection_name}:{entity_id}"
    
    async def get_cached_correlation(self, entity_id: str, collection_name: str) -> Optional[CorrelationResult]:
        key = self._cache_key(entity_id, collection_name)
        return self._correlation_cache.get(key)
```

### Phase 5: Complete File Movement and Deletion

#### 5.1 Files to Move (with transformations)

**From `common_embeddings/correlation/` to `common_ingest/`:**

1. **models.py** → Split into:
   - `models/correlation.py` (CorrelationResult, CorrelationReport)
   - `models/enriched.py` (EnrichedProperty, EnrichedNeighborhood, etc.)
   - `models/cache.py` (SourceDataCache)

2. **correlation_manager.py** → Transform into:
   - `services/correlation_service.py` (main correlation logic)
   - `services/cache_service.py` (caching logic)

3. **enrichment_engine.py** → Transform into:
   - `services/enrichment_service.py` (enrichment logic)
   - `enrichers/property_enricher.py` (property-specific)
   - `enrichers/neighborhood_enricher.py` (neighborhood-specific)
   - `enrichers/wikipedia_enricher.py` (Wikipedia-specific)

#### 5.2 Files to Delete

After successful integration, **completely remove**:
- `common_embeddings/correlation/` directory and all its contents
- Any imports or references to the old correlation module

#### 5.3 Update Dependencies

**Update** `common_ingest/requirements.txt`:
```
chromadb>=0.4.0
pydantic>=2.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
httpx>=0.24.0
python-multipart>=0.0.6
```

### Phase 6: Integration Testing

#### 6.1 Create Integration Tests

**Create** `common_ingest/integration_tests/test_correlation_endpoints.py`:
```python
import pytest
from httpx import AsyncClient
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_get_enriched_properties_with_embeddings(async_client: AsyncClient):
    """Test getting properties with correlated embeddings."""
    response = await async_client.get(
        "/api/v1/properties/enriched",
        params={
            "include_embeddings": True,
            "collection_name": "test_collection"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert all("embeddings" in entity for entity in data["entities"])

@pytest.mark.asyncio
async def test_bulk_correlation_performance(async_client: AsyncClient):
    """Test bulk correlation completes within reasonable time."""
    response = await async_client.post(
        "/api/v1/properties/bulk-enrich",
        json={
            "collection_name": "test_collection",
            "include_similar": False,
            "parallel_workers": 4
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["processing_time_seconds"] < 5.0  # Should complete quickly
```

### Phase 7: API Documentation

#### 7.1 OpenAPI Schema Updates

The FastAPI framework will automatically generate updated OpenAPI documentation. Ensure all new endpoints have proper:
- Descriptions
- Request/response models
- Query parameters with defaults and descriptions
- Error response models

#### 7.2 Create Usage Examples

**Create** `common_ingest/examples/correlation_usage.py`:
```python
import httpx
import asyncio

async def example_get_enriched_properties():
    """Example: Get properties with their embeddings."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/properties/enriched",
            params={
                "include_embeddings": True,
                "collection_name": "embeddings_nomic-embed-text"
            }
        )
        return response.json()

async def example_bulk_correlation():
    """Example: Bulk correlate and enrich entities."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/properties/bulk-enrich",
            json={
                "collection_name": "embeddings_nomic-embed-text",
                "include_similar": True,
                "similarity_threshold": 0.8,
                "parallel_workers": 4
            }
        )
        return response.json()
```

## Implementation Timeline

### Day 1: Core Services
- Create services directory structure
- Move and refactor correlation models
- Implement CorrelationService and EmbeddingService
- Set up dependency injection

### Day 2: API Integration
- Create enriched response models
- Update property endpoints
- Create neighborhood endpoints
- Create Wikipedia endpoints

### Day 3: Complete Migration
- Move enrichment logic
- Implement caching
- Delete old correlation module
- Update all imports

### Day 4: Testing and Documentation
- Write integration tests
- Test all endpoints
- Update API documentation
- Create usage examples

## Success Criteria

1. **Complete Migration**: All correlation code moved from `common_embeddings/` to `common_ingest/`
2. **API Functionality**: All endpoints return enriched data with embeddings
3. **Performance**: Bulk correlation completes in < 5 seconds for 1000 entities
4. **No Backwards Compatibility**: Old correlation module completely removed
5. **Clean Architecture**: Clear separation of concerns with service layer
6. **Full Type Safety**: All models use Pydantic with proper validation
7. **Logging**: All operations use Python logging, no print statements
8. **Documentation**: Complete API documentation with examples

## Risk Mitigation

### Potential Issues and Solutions

1. **ChromaDB Connection Issues**
   - Solution: Implement connection pooling and retry logic in EmbeddingService

2. **Large Embedding Vectors in API Responses**
   - Solution: Add optional vector exclusion, return only metadata by default

3. **Memory Usage with Bulk Operations**
   - Solution: Implement streaming responses for large datasets

4. **Cache Invalidation**
   - Solution: Simple TTL-based cache with manual invalidation endpoints

## Conclusion

This plan provides a complete, atomic migration of correlation functionality from `common_embeddings/` to `common_ingest/`. The implementation follows all specified principles:
- No partial updates or compatibility layers
- Clean, modular architecture with dependency injection
- Full Pydantic model validation
- Python logging throughout
- Demo-quality focus without production concerns

The resulting system will provide unified API endpoints that serve both data and embeddings to downstream consumers, achieving the goal of centralizing all ingestion and correlation logic in a single, well-organized module.