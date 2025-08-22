# MCP Server Architecture Proposal

## Implementation Goals

* NO MIGRATION PHASES: Do not create temporary compatibility periods
* NO PARTIAL UPDATES: Change everything or change nothing  
* NO COMPATIBILITY LAYERS: Do not maintain old and new paths simultaneously
* NO BACKUPS OF OLD CODE: Do not comment out old code "just in case"
* NO CODE DUPLICATION: Do not duplicate functions to handle both patterns
* NO WRAPPER FUNCTIONS: Direct replacements only, no abstraction layers
* DO NOT CALL FUNCTIONS ENHANCED or IMPROVED: Update actual methods directly
* Use snake_case consistently throughout
* Full Pydantic validation for all data models
* No optional imports - all dependencies are required
* Clean, modular, high-quality demo implementation
* Drop and recreate database approach (demo focus, not production complexity)

## Executive Summary

Replace the Flask-based API server with a pure FastMCP implementation that provides LLM-optimized tools for real estate search, property analysis, and location intelligence. This approach eliminates the REST API layer entirely, focusing on direct tool interfaces that are naturally accessible to language models.

## Current Architecture Problems

1. **Flask + Flask-RESTX complexity**: Multiple middleware layers, error handlers, and blueprints create unnecessary overhead
2. **Marshmallow + Pydantic mixing**: Redundant validation layers with different schemas
3. **REST-centric design**: Not optimized for LLM interaction patterns
4. **Complex routing**: Multiple namespaces and versioning schemes add confusion
5. **Poor composability**: Difficult to combine operations in meaningful ways

## Proposed FastMCP Architecture

### Core Design Principles

1. **Tool-First Design**: Each capability is a discrete, composable tool
2. **Single Validation Layer**: Pure Pydantic models throughout
3. **Semantic Operations**: Tools named by intent, not HTTP verbs
4. **Stateless Tools**: Each tool is self-contained with clear inputs/outputs
5. **Rich Context**: Tools provide detailed context for LLM understanding
6. **Hybrid Access**: MCP tools for LLMs + HTTP endpoints for web UIs and monitoring

### Tool Organization

```python
# mcp_server/server.py
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

mcp = FastMCP(
    name="real-estate-search",
    description="AI-powered real estate search with Wikipedia enrichment"
)

# Tool categories:
# 1. Search Tools - finding properties
# 2. Analysis Tools - property insights  
# 3. Location Tools - area information
# 4. Data Tools - direct data access
```

### Proposed Tool Structure

#### 1. Search Tools

```python
class PropertySearchParams(BaseModel):
    """Parameters for searching properties."""
    query: Optional[str] = Field(None, description="Natural language search query")
    location: Optional[str] = Field(None, description="City, neighborhood, or area")
    min_price: Optional[float] = Field(None, description="Minimum price in USD")
    max_price: Optional[float] = Field(None, description="Maximum price in USD")
    bedrooms: Optional[int] = Field(None, ge=0, description="Minimum bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, description="Minimum bathrooms")
    property_types: Optional[List[str]] = Field(None, description="Property types to include")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    features: Optional[List[str]] = Field(None, description="Required features")
    max_results: int = Field(20, ge=1, le=100, description="Maximum results to return")

@mcp.tool
async def search_properties(params: PropertySearchParams) -> PropertySearchResults:
    """
    Search for properties matching specified criteria.
    Combines semantic search with structured filters.
    """
    search_engine = SearchEngine()
    results = await search_engine.search(params)
    return PropertySearchResults(
        properties=results.properties,
        total_found=results.total,
        search_context=results.context
    )

@mcp.tool  
async def find_similar_properties(
    property_id: str = Field(..., description="ID of reference property"),
    max_results: int = Field(10, description="Maximum similar properties")
) -> SimilarPropertiesResult:
    """Find properties similar to a reference property."""
    search_engine = SearchEngine()
    reference = await search_engine.get_property(property_id)
    similar = await search_engine.find_similar(reference, max_results)
    return SimilarPropertiesResult(
        reference=reference,
        similar_properties=similar,
        similarity_factors=search_engine.explain_similarity(reference, similar)
    )

@mcp.tool
async def search_by_commute(
    work_address: str = Field(..., description="Work/destination address"),
    max_commute_minutes: int = Field(..., description="Maximum commute time"),
    transport_mode: str = Field("driving", description="driving, transit, walking, cycling"),
    other_filters: Optional[PropertySearchParams] = None
) -> CommuteSearchResults:
    """Find properties within commute distance of a location."""
    # Implementation uses location services and search engine
    pass
```

#### 2. Analysis Tools

```python
@mcp.tool
async def analyze_property(
    property_id: str = Field(..., description="Property ID to analyze")
) -> PropertyAnalysis:
    """
    Comprehensive analysis of a property including market position,
    neighborhood context, and investment potential.
    """
    property_data = await get_property(property_id)
    market_analysis = await analyze_market_position(property_data)
    location_analysis = await analyze_location(property_data.location)
    
    return PropertyAnalysis(
        property=property_data,
        market_position=market_analysis,
        location_insights=location_analysis,
        investment_metrics=calculate_investment_metrics(property_data),
        comparable_sales=await find_comparable_sales(property_data)
    )

@mcp.tool
async def compare_properties(
    property_ids: List[str] = Field(..., description="List of property IDs to compare")
) -> PropertyComparison:
    """Compare multiple properties across key dimensions."""
    properties = await get_properties(property_ids)
    return PropertyComparison(
        properties=properties,
        price_comparison=compare_prices(properties),
        feature_comparison=compare_features(properties),
        location_comparison=compare_locations(properties),
        recommendation=generate_recommendation(properties)
    )

@mcp.tool
async def calculate_affordability(
    property_id: str = Field(..., description="Property to evaluate"),
    annual_income: float = Field(..., description="Annual household income"),
    down_payment: float = Field(..., description="Available down payment"),
    interest_rate: float = Field(6.5, description="Mortgage interest rate")
) -> AffordabilityAnalysis:
    """Calculate affordability and financing options for a property."""
    # Detailed affordability calculations
    pass
```

#### 3. Location Intelligence Tools

```python
@mcp.tool
async def analyze_neighborhood(
    location: str = Field(..., description="Neighborhood or address to analyze")
) -> NeighborhoodAnalysis:
    """
    Deep analysis of a neighborhood including demographics,
    amenities, schools, and quality of life factors.
    """
    location_data = await geocode_location(location)
    wikipedia_context = await get_wikipedia_context(location)
    nearby_amenities = await find_nearby_amenities(location_data)
    
    return NeighborhoodAnalysis(
        location=location_data,
        wikipedia_summary=wikipedia_context,
        demographics=await get_demographics(location_data),
        schools=await get_school_data(location_data),
        amenities=nearby_amenities,
        walkability_score=calculate_walkability(nearby_amenities),
        safety_metrics=await get_safety_data(location_data),
        market_trends=await get_market_trends(location_data)
    )

@mcp.tool
async def find_points_of_interest(
    location: str = Field(..., description="Center location"),
    radius_miles: float = Field(2.0, description="Search radius"),
    categories: Optional[List[str]] = Field(None, description="POI categories to include")
) -> PointsOfInterest:
    """Find notable places and points of interest near a location."""
    # Wikipedia-enriched POI discovery
    pass

@mcp.tool
async def get_location_history(
    location: str = Field(..., description="Location to research")
) -> LocationHistory:
    """Get historical context and development history of a location."""
    # Wikipedia and local data sources
    pass
```

#### 4. Data Management Tools

```python
@mcp.tool
async def refresh_property_data(
    source: str = Field("all", description="Data source to refresh")
) -> RefreshResult:
    """Refresh property listings and enrichment data."""
    indexer = PropertyIndexer()
    result = await indexer.refresh_index(source)
    return RefreshResult(
        properties_updated=result.updated_count,
        properties_added=result.added_count,
        enrichment_status=result.enrichment_status
    )

@mcp.tool
async def get_search_statistics() -> SearchStatistics:
    """Get statistics about the search index and data quality."""
    stats = await calculate_index_statistics()
    return SearchStatistics(
        total_properties=stats.total,
        cities_covered=stats.cities,
        data_freshness=stats.last_updated,
        enrichment_coverage=stats.enrichment_percentage,
        index_health=stats.health_metrics
    )
```

### Data Models (Pydantic)

```python
# models/property.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class PropertyType(str, Enum):
    single_family = "single_family"
    condo = "condo"
    townhouse = "townhouse"
    multi_family = "multi_family"
    land = "land"
    other = "other"

class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    location: Optional[GeoLocation] = None

class Property(BaseModel):
    id: str
    listing_id: str
    property_type: PropertyType
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    address: Address
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    listing_date: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.now)

class WikipediaContext(BaseModel):
    title: str
    summary: str
    historical_significance: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    notable_features: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)

class PropertySearchResults(BaseModel):
    properties: List[Property]
    total_found: int
    search_context: Dict[str, Any]
    wikipedia_enrichment: Optional[List[WikipediaContext]] = None
```

### Core Services

```python
# services/search_engine.py
from typing import List, Optional
import asyncio
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel

class SearchEngine:
    def __init__(self):
        self.es = AsyncElasticsearch(["http://localhost:9200"])
        self.index_name = "properties_demo"
    
    async def search(self, params: PropertySearchParams) -> SearchResults:
        """Execute property search with intelligent query building."""
        query = self._build_query(params)
        
        response = await self.es.search(
            index=self.index_name,
            body=query,
            size=params.max_results
        )
        
        properties = [self._parse_property(hit) for hit in response['hits']['hits']]
        
        return SearchResults(
            properties=properties,
            total=response['hits']['total']['value'],
            context=self._extract_context(response)
        )
    
    def _build_query(self, params: PropertySearchParams) -> dict:
        """Build Elasticsearch query from search parameters."""
        must_clauses = []
        filter_clauses = []
        
        # Natural language query
        if params.query:
            must_clauses.append({
                "multi_match": {
                    "query": params.query,
                    "fields": ["description^2", "features", "amenities", "address.city"],
                    "type": "best_fields"
                }
            })
        
        # Location filter
        if params.location:
            filter_clauses.append({
                "match": {"address.city": params.location}
            })
        
        # Price range
        if params.min_price or params.max_price:
            price_range = {}
            if params.min_price:
                price_range["gte"] = params.min_price
            if params.max_price:
                price_range["lte"] = params.max_price
            filter_clauses.append({"range": {"price": price_range}})
        
        # Property specifications
        if params.bedrooms:
            filter_clauses.append({"range": {"bedrooms": {"gte": params.bedrooms}}})
        
        if params.bathrooms:
            filter_clauses.append({"range": {"bathrooms": {"gte": params.bathrooms}}})
        
        if params.property_types:
            filter_clauses.append({"terms": {"property_type": params.property_types}})
        
        # Features and amenities
        if params.amenities:
            for amenity in params.amenities:
                filter_clauses.append({"term": {"amenities": amenity}})
        
        if params.features:
            for feature in params.features:
                filter_clauses.append({"term": {"features": feature}})
        
        # Build final query
        query_body = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            }
        }
        
        return query_body

# services/enrichment.py
class WikipediaEnrichmentService:
    """Service for enriching property data with Wikipedia context."""
    
    async def enrich_location(self, location: GeoLocation) -> WikipediaContext:
        """Get Wikipedia context for a geographic location."""
        # Query Wikipedia API or local database
        pass
    
    async def enrich_neighborhood(self, neighborhood: str, city: str) -> WikipediaContext:
        """Get Wikipedia context for a neighborhood."""
        # Implementation
        pass

# services/market_analysis.py  
class MarketAnalysisService:
    """Service for property market analysis."""
    
    async def analyze_market_position(self, property: Property) -> MarketPosition:
        """Analyze property's position in the market."""
        comparables = await self.find_comparables(property)
        price_analysis = self.analyze_pricing(property, comparables)
        demand_indicators = await self.calculate_demand(property)
        
        return MarketPosition(
            price_percentile=price_analysis.percentile,
            days_on_market_estimate=demand_indicators.estimated_dom,
            competitive_properties=len(comparables),
            pricing_recommendation=price_analysis.recommendation
        )
```

### Server Implementation

```python
# mcp_server/main.py
from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app
from contextlib import asynccontextmanager
import logging
from elasticsearch import AsyncElasticsearch
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    name="real-estate-search",
    description="AI-powered real estate search with Wikipedia enrichment and market analysis"
)

# Shared resources
class Resources:
    es: AsyncElasticsearch = None
    search_engine: SearchEngine = None
    enrichment_service: WikipediaEnrichmentService = None
    market_service: MarketAnalysisService = None

resources = Resources()

@asynccontextmanager
async def lifespan(app):
    """Manage server lifecycle and resources."""
    # Startup
    logger.info("Initializing Real Estate MCP Server...")
    
    # Initialize Elasticsearch
    resources.es = AsyncElasticsearch(["http://localhost:9200"])
    
    # Initialize services
    resources.search_engine = SearchEngine(resources.es)
    resources.enrichment_service = WikipediaEnrichmentService()
    resources.market_service = MarketAnalysisService(resources.es)
    
    # Verify index exists or create it
    await ensure_index_exists(resources.es)
    
    logger.info("Server initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Real Estate MCP Server...")
    await resources.es.close()
    logger.info("Server shutdown complete")

# Apply lifespan to server
mcp.lifespan = lifespan

# Register all tools
from .tools import search, analysis, location, data

mcp.include_module(search)
mcp.include_module(analysis)
mcp.include_module(location)
mcp.include_module(data)

# Resources for LLM context
@mcp.resource("properties://featured")
async def get_featured_properties() -> str:
    """Get featured property listings."""
    # Return curated property descriptions
    pass

@mcp.resource("properties://markets")
async def get_market_summaries() -> str:
    """Get market summaries for major areas."""
    # Return market overviews
    pass

# HTTP API Endpoints (alongside MCP tools)
# Note: Using direct route creation pattern for reliability with newer FastMCP versions

async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "real-estate-search",
        "mcp_enabled": True,
        "tools": [
            "search_properties",
            "find_similar_properties", 
            "search_by_commute",
            "analyze_property",
            "compare_properties",
            "analyze_neighborhood"
        ],
        "elasticsearch": await check_es_health(resources.es)
    })

async def api_search(request: Request) -> JSONResponse:
    """REST API endpoint for property search (useful for web UIs)."""
    try:
        body = await request.json()
        # Convert REST request to MCP tool call
        params = PropertySearchParams(**body)
        results = await resources.search_engine.search(params)
        return JSONResponse({
            "success": True,
            "data": results.model_dump()
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

async def demo_ui(request: Request) -> HTMLResponse:
    """Simple demo UI for testing the MCP server."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real Estate MCP Server Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .tool { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .tool h3 { margin: 0 0 10px 0; color: #333; }
            code { background: #e8e8e8; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Real Estate MCP Server</h1>
        <p>This server provides AI-optimized tools for real estate search and analysis.</p>
        
        <h2>Available MCP Tools</h2>
        <div class="tool">
            <h3>search_properties</h3>
            <p>Search for properties with natural language queries and filters</p>
        </div>
        <div class="tool">
            <h3>analyze_property</h3>
            <p>Get comprehensive analysis of a property including market position</p>
        </div>
        <div class="tool">
            <h3>analyze_neighborhood</h3>
            <p>Deep analysis of neighborhoods with Wikipedia enrichment</p>
        </div>
        
        <h2>API Endpoints</h2>
        <ul>
            <li><code>GET /health</code> - Health check</li>
            <li><code>POST /api/search</code> - REST search endpoint</li>
            <li><code>GET /demo</code> - This demo page</li>
            <li><code>POST /mcp</code> - MCP protocol endpoint</li>
        </ul>
        
        <p>Connect with Claude Desktop or any MCP client at: <code>http://localhost:8000/mcp</code></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

async def check_es_health(es: AsyncElasticsearch) -> dict:
    """Check Elasticsearch health status."""
    try:
        health = await es.cluster.health()
        return {
            "status": health["status"],
            "number_of_nodes": health["number_of_nodes"]
        }
    except Exception:
        return {"status": "unavailable"}

if __name__ == "__main__":
    # Create custom routes for HTTP endpoints
    custom_routes = [
        Route("/health", endpoint=health_check, methods=["GET"]),
        Route("/api/search", endpoint=api_search, methods=["POST"]),
        Route("/demo", endpoint=demo_ui, methods=["GET"])
    ]
    
    # Create the app with SSE support and custom routes
    app = create_sse_app(
        mcp, 
        message_path="/mcp",
        sse_path="/sse",
        routes=custom_routes
    )
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Configuration

```yaml
# config/mcp_config.yaml
server:
  name: real-estate-search
  version: 1.0.0
  description: AI-powered real estate search with enrichment

elasticsearch:
  hosts:
    - http://localhost:9200
  index: properties_demo
  refresh_on_write: true  # Demo mode - immediate consistency

enrichment:
  wikipedia:
    enabled: true
    cache_ttl: 3600
  market_data:
    enabled: true
    
search:
  default_size: 20
  max_size: 100
  enable_fuzzy: true
  boost_factors:
    description: 2.0
    features: 1.5
    amenities: 1.5
    location: 1.8

demo:
  reset_on_startup: true
  sample_data_path: ./data/demo_properties.json
  enrich_on_load: true
```

### Testing Strategy

```python
# tests/test_mcp_tools.py
import pytest
from fastmcp.testing import MCPTestClient
from mcp_server.main import mcp

@pytest.fixture
async def client():
    async with MCPTestClient(mcp) as client:
        yield client

async def test_search_properties(client):
    """Test property search tool."""
    result = await client.call_tool(
        "search_properties",
        params={
            "query": "modern kitchen pool",
            "location": "Austin",
            "min_price": 400000,
            "max_price": 800000,
            "bedrooms": 3
        }
    )
    
    assert result.properties
    assert all(p.price >= 400000 and p.price <= 800000 for p in result.properties)
    assert all(p.bedrooms >= 3 for p in result.properties)

async def test_analyze_property(client):
    """Test property analysis tool."""
    # First, get a property
    search_result = await client.call_tool(
        "search_properties",
        params={"location": "Austin", "max_results": 1}
    )
    
    property_id = search_result.properties[0].id
    
    # Analyze it
    analysis = await client.call_tool(
        "analyze_property",
        params={"property_id": property_id}
    )
    
    assert analysis.property.id == property_id
    assert analysis.market_position
    assert analysis.location_insights
    assert analysis.investment_metrics

async def test_neighborhood_analysis(client):
    """Test neighborhood analysis tool."""
    result = await client.call_tool(
        "analyze_neighborhood",
        params={"location": "Downtown Austin"}
    )
    
    assert result.location
    assert result.wikipedia_summary
    assert result.demographics
    assert result.walkability_score >= 0
```

### Migration Plan

1. **Phase 1: Setup MCP Server Structure**
   - Create new `mcp_server/` directory
   - Set up Pydantic models (no Marshmallow)
   - Implement core MCP server with tools

2. **Phase 2: Port Search Logic**
   - Migrate SearchEngine to async
   - Convert all search operations to tools
   - Remove REST endpoint concepts

3. **Phase 3: Add Enrichment Services**
   - Port Wikipedia enrichment
   - Add market analysis service
   - Integrate with MCP tools

4. **Phase 4: Testing & Demo**
   - Create comprehensive test suite
   - Build demo data loader
   - Document tool usage patterns

5. **Phase 5: Complete Cutover**
   - Remove Flask application entirely
   - Update all documentation
   - Deploy MCP server

### HTTP Endpoint Best Practices

Based on FastMCP patterns and community usage:

1. **Use Direct Route Creation**: Due to changes in FastMCP 2.4+, create routes directly using Starlette's `Route` class and pass them to `create_sse_app()` rather than relying on the `@custom_route` decorator

2. **Common HTTP Endpoints to Include**:
   - `/health` - Health check for monitoring and load balancers
   - `/api/*` - REST endpoints for web UIs that need to access MCP functionality
   - `/demo` or `/docs` - Interactive documentation or demo UI
   - `/metrics` - Prometheus/OpenTelemetry metrics endpoint
   - `/admin` - Administrative interface for server management

3. **Route Implementation Pattern**:
```python
# Define endpoint functions
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})

# Create routes explicitly
custom_routes = [
    Route("/health", endpoint=health_check, methods=["GET"])
]

# Pass to create_sse_app
app = create_sse_app(mcp, routes=custom_routes)
```

4. **Bridge Pattern**: HTTP endpoints can call MCP tools internally, providing a REST interface for legacy systems or web UIs while maintaining the MCP tool structure

5. **Separation of Concerns**: Keep HTTP endpoints minimal - they should primarily delegate to MCP tools or provide operational endpoints (health, metrics, etc.)

### Benefits of MCP Architecture

1. **LLM-Native Design**: Tools are designed for AI agents, not HTTP clients
2. **Simplified Stack**: Single server, single validation layer, single paradigm
3. **Better Composability**: Tools can be combined naturally by LLMs
4. **Rich Context**: Each tool provides detailed context and explanations
5. **Type Safety**: Full Pydantic validation throughout
6. **Testability**: Built-in testing utilities for MCP tools
7. **Scalability**: Async-first design with proper resource management
8. **Hybrid Access**: Support both MCP clients and traditional HTTP clients when needed

### Key Differences from Flask API

| Aspect | Flask API | MCP Server |
|--------|-----------|------------|
| Interface | REST endpoints | Semantic tools |
| Validation | Marshmallow + Pydantic | Pure Pydantic |
| Operations | CRUD-based | Intent-based |
| Errors | HTTP status codes | Structured error models |
| Discovery | OpenAPI/Swagger | MCP tool descriptions |
| Testing | HTTP client tests | MCP tool tests |
| Composition | Manual orchestration | LLM-driven composition |

### Example Usage by LLM

```python
# LLM can naturally compose operations
"Find me a 3-bedroom house in Austin under $600k with a pool"
-> search_properties(location="Austin", bedrooms=3, max_price=600000, amenities=["pool"])

"Compare these three properties and tell me which is the best investment"
-> compare_properties(property_ids=[...])
-> analyze_property(property_id=best_match)

"What's the neighborhood like around this property?"
-> analyze_neighborhood(location=property.address)
-> find_points_of_interest(location=property.address, radius_miles=1)
```

### Conclusion

This MCP server architecture provides a clean, modern, LLM-optimized interface for real estate search and analysis. By eliminating the REST layer and focusing on semantic tools, we create a more natural and powerful system for AI-assisted property discovery and evaluation.

The implementation is straightforward, testable, and maintainable while providing rich functionality through composable tools that LLMs can naturally understand and use effectively.