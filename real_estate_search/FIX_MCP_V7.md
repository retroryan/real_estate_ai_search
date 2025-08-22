# MCP Implementation - Simple Constructor Injection Pattern

## Executive Summary
This document outlines a clean, simple approach to fixing the MCP implementation using constructor injection - the most straightforward and maintainable dependency injection pattern.

## Core Principle: Constructor Injection
Constructor injection is the preferred pattern because:
- **Explicit dependencies** - Classes clearly declare what they need
- **Guaranteed valid state** - Objects cannot exist without required dependencies  
- **Easy to test** - Dependencies can be easily mocked
- **Simple to understand** - No magic, no hidden behavior

## Current Issues to Fix

### 1. Remove Tool Indirection
**Problem**: Tools are wrappers calling separate functions
```python
# ❌ CURRENT: Unnecessary indirection
@mcp.tool
async def search_properties(...):
    return await search_properties_tool(...)  # Why this extra layer?
```

**Solution**: Direct implementation
```python
# ✅ FIXED: Direct implementation
@mcp.tool
async def search_properties(ctx: Context, query: str, **filters):
    """Search for properties matching criteria."""
    if not resources.search_engine:
        raise RuntimeError("Search engine not initialized")
    return await resources.search_engine.search(query, **filters)
```

### 2. Add FastMCP Context
Every tool needs a context parameter for progress reporting and logging:
```python
@mcp.tool
async def analyze_property(ctx: Context, property_id: str):
    ctx.report_progress(0.5, "Analyzing...")
    # Implementation here
```

## Clean Architecture with Constructor Injection

### Service Classes - Pure Constructor Injection
```python
# ✅ CLEAN: Required dependencies in constructor
class SearchEngine:
    def __init__(self, es_client: AsyncElasticsearch, settings: Settings):
        """All dependencies are required - no defaults, no fallbacks."""
        self.es_client = es_client
        self.settings = settings
        self.index_name = settings.elasticsearch.index_name

class PropertyIndexer:
    def __init__(self, es_client: AsyncElasticsearch, settings: Settings):
        """Simple, explicit dependencies."""
        self.es_client = es_client
        self.settings = settings

class MarketAnalysisService:
    def __init__(self, es_client: AsyncElasticsearch, settings: Settings):
        """Clear what this service needs to function."""
        self.es_client = es_client
        self.settings = settings
```

### Service Container - Simple and Clean
```python
@dataclass
class ServerResources:
    """Simple container for all services."""
    es: Optional[AsyncElasticsearch] = None
    search_engine: Optional[SearchEngine] = None
    indexer: Optional[PropertyIndexer] = None
    market_service: Optional[MarketAnalysisService] = None

# Global container (like Flask's app context)
resources = ServerResources()
```

### Initialization - Clear and Explicit
```python
@asynccontextmanager
async def lifespan(app):
    """Initialize all services with constructor injection."""
    # Create Elasticsearch client
    es_client = AsyncElasticsearch(
        [settings.elasticsearch.url],
        timeout=settings.elasticsearch.timeout
    )
    
    # Create services with explicit dependencies
    resources.es = es_client
    resources.search_engine = SearchEngine(es_client, settings)
    resources.indexer = PropertyIndexer(es_client, settings)
    resources.market_service = MarketAnalysisService(es_client, settings)
    
    yield
    
    # Cleanup
    await es_client.close()
```

## Tool Implementation Example

Here's how a clean tool looks with proper constructor injection:

```python
@mcp.tool
async def search_properties(
    ctx: Context,
    query: Optional[str] = None,
    location: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    max_results: int = 20
) -> Dict[str, Any]:
    """Search for properties matching criteria."""
    
    # Check service is available
    if not resources.search_engine:
        raise RuntimeError("Search engine not initialized")
    
    # Report progress
    ctx.report_progress(0.3, "Building search...")
    
    # Build search parameters
    params = PropertySearchParams(
        query=query,
        location=location,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        max_results=max_results
    )
    
    # Execute search
    ctx.report_progress(0.7, "Searching database...")
    results = await resources.search_engine.search(params)
    
    # Return formatted results
    return {
        "success": True,
        "total": results.total,
        "properties": [format_property(p) for p in results.hits]
    }
```

## Simple Implementation Steps

### Step 1: Clean Up Services
Update all service classes to use pure constructor injection:
- Remove any default parameters
- Remove any fallback logic (no `or` patterns)
- Make all dependencies explicit and required

### Step 2: Simplify Tools
For each tool:
1. Add `ctx: Context` as first parameter
2. Move implementation directly into the `@mcp.tool` function
3. Remove wrapper functions
4. Add progress reporting at 2-3 key points

### Step 3: Test Everything
- Verify each service initializes correctly
- Test each tool with the MCP Inspector
- Ensure error handling is clean and informative

## Key Principles for a Clean Demo

### What Makes Good Constructor Injection
1. **Explicit Dependencies** - No hidden requirements
2. **Required Parameters** - No defaults that hide dependencies
3. **Simple Initialization** - Straightforward object creation
4. **Easy Testing** - Dependencies can be mocked easily

### What to Keep
- **ServerResources container** - Clean service organization
- **Service classes** - Business logic encapsulation
- **Pydantic models** - Type safety

### What to Fix
- **Remove wrapper functions** - Direct implementation in tools
- **Add Context parameter** - For progress and logging
- **Simplify initialization** - Clear constructor injection

## Complete Example: Clean Tool with Constructor Injection

```python
@mcp.tool
async def analyze_property(ctx: Context, property_id: str) -> Dict[str, Any]:
    """Analyze a property with market data and investment metrics."""
    
    # Verify services are available (injected at startup)
    if not resources.search_engine or not resources.market_service:
        raise RuntimeError("Required services not initialized")
    
    # Simple, clear implementation
    ctx.report_progress(0.3, "Loading property...")
    property = await resources.search_engine.get_property(property_id)
    
    ctx.report_progress(0.6, "Analyzing market...")
    analysis = await resources.market_service.analyze(property)
    
    ctx.report_progress(0.9, "Calculating metrics...")
    metrics = await resources.market_service.calculate_metrics(property)
    
    return {
        "property": property.dict(),
        "analysis": analysis.dict(),
        "metrics": metrics.dict()
    }
```

## Summary

This demo showcases clean, professional Python code using constructor injection:
- Services declare their dependencies explicitly
- Tools are simple and focused
- Testing is straightforward
- The code is maintainable and easy to understand

The pattern is simple: **Classes require their dependencies in the constructor, period.** No magic, no fallbacks, no hidden behavior.