# Direct Integration Contracts

**Date**: 2025-01-07  
**Feature**: MCP Server Direct Search Service Integration  
**Branch**: 001-update-the-real

## Overview

This document defines the contracts for direct integration between MCP server and search_service. Following constitutional principles, there are NO adapters, NO compatibility layers, and NO transformation functions. MCP tools use search_service directly.

## 1. MCP Tool Contracts

### Property Search Tool Contract

**Tool Name**: `search_properties`  
**Purpose**: Search for properties using search_service directly

```python
async def search_properties(
    context: Context,
    query: Optional[str] = None,
    search_type: str = "text",
    filters: Optional[Dict] = None,
    size: int = 10
) -> Dict[str, Any]:
    """
    Search properties using search_service.
    
    Args:
        context: MCP context with search services
        query: Search text
        search_type: Type of search (text/semantic/hybrid)
        filters: Property filters
        size: Number of results
        
    Returns:
        search_service.PropertySearchResponse as dict
        
    Raises:
        SearchError: If search fails
    """
    pass
```

**Contract Requirements**:
- MUST use search_service.models.PropertySearchRequest
- MUST return search_service.PropertySearchResponse.model_dump()
- NO transformation of request or response
- NO backward compatibility handling

### Wikipedia Search Tool Contract

**Tool Name**: `search_wikipedia`  
**Purpose**: Search Wikipedia using search_service directly

```python
async def search_wikipedia(
    context: Context,
    query: str,
    search_type: str = "fulltext",
    categories: Optional[List[str]] = None,
    size: int = 10
) -> Dict[str, Any]:
    """
    Search Wikipedia using search_service.
    
    Args:
        context: MCP context with search services
        query: Search text (required)
        search_type: Type of search (fulltext/chunks/summaries)
        categories: Category filters
        size: Number of results
        
    Returns:
        search_service.WikipediaSearchResponse as dict
        
    Raises:
        SearchError: If search fails
    """
    pass
```

**Contract Requirements**:
- MUST use search_service.models.WikipediaSearchRequest
- MUST return search_service.WikipediaSearchResponse.model_dump()
- NO transformation of request or response
- NO adapter functions

### Neighborhood Search Tool Contract

**Tool Name**: `search_neighborhoods`  
**Purpose**: Search neighborhoods using search_service directly

```python
async def search_neighborhoods(
    context: Context,
    city: str,
    state: str,
    include_properties: bool = True,
    include_wikipedia: bool = True,
    size: int = 10
) -> Dict[str, Any]:
    """
    Search neighborhoods using search_service.
    
    Args:
        context: MCP context with search services
        city: City name
        state: State code
        include_properties: Include property statistics
        include_wikipedia: Include Wikipedia articles
        size: Number of results
        
    Returns:
        search_service.NeighborhoodSearchResponse as dict
        
    Raises:
        SearchError: If search fails
    """
    pass
```

**Contract Requirements**:
- MUST use search_service.models.NeighborhoodSearchRequest
- MUST return search_service.NeighborhoodSearchResponse.model_dump()
- NO transformation layers
- Direct service usage only

## 2. Service Initialization Contract

### MCP Server Initialization

```python
class MCPServer:
    def __init__(self, config: MCPServerConfig):
        """
        Initialize MCP server with search_service.
        
        Args:
            config: Server configuration
        """
        # Initialize Elasticsearch
        self.es_client = Elasticsearch(hosts=[config.elasticsearch.host])
        
        # Initialize search services directly
        self.property_service = PropertySearchService(self.es_client)
        self.wikipedia_service = WikipediaSearchService(self.es_client)
        self.neighborhood_service = NeighborhoodSearchService(self.es_client)
```

**Contract Requirements**:
- MUST use raw Elasticsearch client
- MUST initialize search_service classes directly
- NO wrapper classes
- NO adapter layers

## 3. Response Format Contracts

### Property Search Response Format

Direct from search_service.PropertySearchResponse:
```json
{
    "results": [
        {
            "property_id": "123",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "price": 1000000.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "square_feet": 1500,
            "property_type": "single_family",
            "description": "...",
            "score": 0.95,
            "highlights": {}
        }
    ],
    "total_hits": 100,
    "execution_time_ms": 150,
    "aggregations": {},
    "request": {
        "query": "San Francisco",
        "search_type": "text",
        "filters": null,
        "size": 10,
        "from_offset": 0
    }
}
```

### Wikipedia Search Response Format

Direct from search_service.WikipediaSearchResponse:
```json
{
    "results": [
        {
            "title": "San Francisco",
            "url": "https://en.wikipedia.org/wiki/San_Francisco",
            "summary": "...",
            "categories": ["Cities in California"],
            "content": "...",
            "score": 0.89
        }
    ],
    "total_hits": 50,
    "execution_time_ms": 120,
    "request": {
        "query": "San Francisco",
        "search_type": "fulltext",
        "categories": null,
        "size": 10
    }
}
```

### Neighborhood Search Response Format

Direct from search_service.NeighborhoodSearchResponse:
```json
{
    "neighborhoods": [
        {
            "name": "Mission District",
            "city": "San Francisco",
            "state": "CA",
            "population": 45000,
            "median_income": 85000,
            "description": "..."
        }
    ],
    "total_hits": 5,
    "property_stats": {
        "avg_price": 1200000,
        "median_price": 1100000,
        "total_properties": 500,
        "price_range": {
            "min": 500000,
            "max": 5000000
        }
    },
    "related_wikipedia": [
        {
            "title": "Mission District, San Francisco",
            "url": "https://..."
        }
    ],
    "request": {
        "city": "San Francisco",
        "state": "CA",
        "include_properties": true,
        "include_wikipedia": true,
        "size": 10
    }
}
```

### Error Response Format

Direct from search_service.SearchError:
```json
{
    "error": {
        "message": "Search failed: index not found",
        "code": "INDEX_NOT_FOUND",
        "details": {
            "index": "properties",
            "suggestion": "Run setup-indices command"
        }
    }
}
```

## 4. Testing Contracts

### Unit Test Contract

```python
def test_mcp_tool_uses_search_service():
    """Test that MCP tools use search_service directly."""
    # Create mock context with real search_service
    context = {
        "property_search_service": PropertySearchService(es_client)
    }
    
    # Call MCP tool
    response = await search_properties(
        context,
        query="San Francisco",
        search_type="text"
    )
    
    # Verify response is search_service format
    assert "results" in response
    assert "total_hits" in response
    assert "request" in response
    # NO adapter verification needed
```

### Integration Test Contract

```python
def test_end_to_end_integration():
    """Test complete integration without adapters."""
    # Start MCP server
    server = MCPServer(config)
    
    # Execute search through MCP protocol
    response = await server.handle_tool_call(
        "search_properties",
        {"query": "San Francisco"}
    )
    
    # Verify direct search_service response
    assert response["request"]["query"] == "San Francisco"
    # NO transformation verification
    # NO backward compatibility checks
```

## 5. Deletion Contract

The following MUST be deleted completely:

### Files to Delete
```
mcp_server/models/property.py
mcp_server/models/wikipedia.py
mcp_server/models/search.py
mcp_server/models/hybrid.py
mcp_server/models/responses.py
mcp_server/services/property_search.py
mcp_server/services/wikipedia_search.py
```

### Code to Remove
- All adapter functions
- All transformation functions
- All compatibility layers
- All duplicate model definitions
- All duplicate service implementations

## 6. Import Update Contract

All imports MUST be updated to use search_service:

```python
# OLD - DELETE
from real_estate_search.mcp_server.models.property import PropertySearchRequest
from real_estate_search.mcp_server.services.property_search import PropertySearchService

# NEW - DIRECT IMPORT
from real_estate_search.search_service.models import PropertySearchRequest
from real_estate_search.search_service.properties import PropertySearchService
```

## Validation Requirements

### Success Criteria
1. All duplicate code deleted
2. All imports use search_service
3. MCP tools return search_service format
4. No adapters or transformations
5. Tests pass with new format
6. MCP demos work with new format

### Forbidden Patterns
- NO adapter classes
- NO transformation functions
- NO compatibility imports
- NO wrapper methods
- NO "Enhanced" or "Improved" classes
- NO gradual migration code