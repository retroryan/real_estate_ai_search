# Data Model: MCP Server Direct Search Service Integration

**Date**: 2025-01-07  
**Feature**: MCP Server Direct Search Service Integration  
**Branch**: 001-update-the-real

## Overview

This document defines the unified data model for the direct integration of MCP server with search_service. Following constitutional principles, there will be ONE set of models (search_service models) used everywhere, with no adapters, no duplicates, and no compatibility layers.

## Single Source of Truth: search_service.models

All models come from `real_estate_search/search_service/models.py`. The MCP server will import and use these directly.

### Core Request Models

#### PropertySearchRequest
**Location**: `search_service.models.PropertySearchRequest`  
**Purpose**: Unified property search request  
**Key Attributes**:
- `query`: Optional[str] - Search text
- `search_type`: SearchType - Enum (text, semantic, hybrid)
- `filters`: Optional[PropertyFilter] - Property filters
- `size`: int = 10 - Number of results
- `from_offset`: int = 0 - Pagination offset

#### WikipediaSearchRequest
**Location**: `search_service.models.WikipediaSearchRequest`  
**Purpose**: Unified Wikipedia search request  
**Key Attributes**:
- `query`: str - Search text (required)
- `search_type`: WikiSearchType - Enum (fulltext, chunks, summaries)
- `categories`: Optional[List[str]] - Category filters
- `size`: int = 10 - Number of results

#### NeighborhoodSearchRequest
**Location**: `search_service.models.NeighborhoodSearchRequest`  
**Purpose**: Unified neighborhood search request  
**Key Attributes**:
- `city`: str - City name
- `state`: str - State code
- `include_properties`: bool = False - Include related properties
- `include_wikipedia`: bool = False - Include Wikipedia articles
- `size`: int = 10 - Number of results

### Core Response Models

#### PropertySearchResponse
**Location**: `search_service.models.PropertySearchResponse`  
**Purpose**: Unified property search response  
**Key Attributes**:
- `results`: List[PropertyResult] - Search results
- `total_hits`: int - Total matching documents
- `execution_time_ms`: int - Query execution time
- `aggregations`: Optional[Dict] - Aggregation results
- `request`: PropertySearchRequest - Original request

#### WikipediaSearchResponse
**Location**: `search_service.models.WikipediaSearchResponse`  
**Purpose**: Unified Wikipedia search response  
**Key Attributes**:
- `results`: List[WikipediaResult] - Search results
- `total_hits`: int - Total matching documents
- `execution_time_ms`: int - Query execution time
- `request`: WikipediaSearchRequest - Original request

#### NeighborhoodSearchResponse
**Location**: `search_service.models.NeighborhoodSearchResponse`  
**Purpose**: Unified neighborhood search response  
**Key Attributes**:
- `neighborhoods`: List[NeighborhoodResult] - Search results
- `total_hits`: int - Total matching neighborhoods
- `property_stats`: Optional[PropertyStats] - Aggregated statistics
- `related_wikipedia`: Optional[List[WikipediaResult]] - Related articles
- `request`: NeighborhoodSearchRequest - Original request

### Supporting Models

#### PropertyFilter
**Location**: `search_service.models.PropertyFilter`  
**Purpose**: Property search filters  
**Key Attributes**:
- `min_price`: Optional[float]
- `max_price`: Optional[float]
- `min_bedrooms`: Optional[int]
- `max_bedrooms`: Optional[int]
- `property_types`: Optional[List[PropertyType]]
- `cities`: Optional[List[str]]
- `states`: Optional[List[str]]

#### PropertyResult
**Location**: `search_service.models.PropertyResult`  
**Purpose**: Individual property in search results  
**Key Attributes**:
- `property_id`: str
- `address`: str
- `city`: str
- `state`: str
- `zip_code`: str
- `price`: float
- `bedrooms`: int
- `bathrooms`: float
- `square_feet`: Optional[int]
- `property_type`: PropertyType
- `description`: str
- `score`: float - Relevance score
- `highlights`: Optional[Dict] - Search highlights

#### SearchError
**Location**: `search_service.models.SearchError`  
**Purpose**: Unified error response  
**Key Attributes**:
- `message`: str - Error description
- `code`: str - Error code
- `details`: Optional[Dict] - Additional context

## Direct Integration Points

### MCP Tool Integration

MCP tools will directly use search_service models and services:

```python
# mcp_server/tools/property_tools.py
from real_estate_search.search_service.models import (
    PropertySearchRequest,
    PropertySearchResponse
)
from real_estate_search.search_service.properties import PropertySearchService

async def search_properties(context: Context, **params) -> Dict[str, Any]:
    # Create request using search_service model
    request = PropertySearchRequest(**params)
    
    # Get service from context
    service: PropertySearchService = context.get("property_search_service")
    
    # Execute search
    response: PropertySearchResponse = await service.search(request)
    
    # Return response directly (as dict for MCP)
    return response.model_dump()
```

### Service Initialization

Services are initialized with raw Elasticsearch client:

```python
# mcp_server/main.py
from elasticsearch import Elasticsearch
from real_estate_search.search_service.properties import PropertySearchService
from real_estate_search.search_service.wikipedia import WikipediaSearchService
from real_estate_search.search_service.neighborhoods import NeighborhoodSearchService

# Initialize Elasticsearch
es_client = Elasticsearch(hosts=[config.elasticsearch.host])

# Initialize search services directly
property_service = PropertySearchService(es_client)
wikipedia_service = WikipediaSearchService(es_client)
neighborhood_service = NeighborhoodSearchService(es_client)
```

## Deleted Models

The following duplicate models will be completely removed:

### From mcp_server/models/
- `property.py` - All property-related models
- `wikipedia.py` - All Wikipedia-related models
- `search.py` - All search request/response models
- `hybrid.py` - Hybrid search models
- `responses.py` - Response format models

### Replacement Strategy
- No gradual migration
- No compatibility imports
- Direct deletion and replacement
- Update all imports to use search_service.models

## State Transitions

### Search Request Flow
1. **MCP Tool Receives Request** → Parameters from MCP client
2. **Create search_service Model** → Direct instantiation
3. **Execute Search** → Call search_service method
4. **Return Response** → Direct model_dump() to dict

### Error Handling Flow
1. **Search Error Occurs** → SearchError raised
2. **MCP Tool Catches** → Handle SearchError
3. **Return Error Dict** → Format for MCP protocol

## Validation Rules

All validation is handled by Pydantic models in search_service:

### Request Validation
- Query required for text/hybrid search
- Size must be 1-100
- Valid enum values for search types
- Filter ranges must be valid

### Response Validation
- Automatic via Pydantic
- No additional validation needed
- Type safety guaranteed

## Migration Notes

### Complete Replacement
Per constitution, this is a complete atomic change:
1. Delete all MCP model files
2. Update all imports
3. Update all tools
4. Update all tests
5. No backwards compatibility

### Import Changes
```python
# Before
from real_estate_search.mcp_server.models.property import PropertySearchRequest
from real_estate_search.mcp_server.services.property_search import PropertySearchService

# After
from real_estate_search.search_service.models import PropertySearchRequest
from real_estate_search.search_service.properties import PropertySearchService
```

### Response Format Changes
MCP tools will return search_service response format directly. Any clients expecting old format must be updated.

## Testing Requirements

### Unit Tests
- Test search_service models directly
- No duplicate model tests
- Remove all MCP model tests

### Integration Tests
- Test MCP tools with search_service
- Verify direct integration works
- No adapter testing needed

### End-to-End Tests
- Update MCP demos for new response format
- Validate complete integration
- No compatibility testing