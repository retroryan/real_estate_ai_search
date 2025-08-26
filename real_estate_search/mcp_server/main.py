"""
FastMCP Server for Real Estate Search.
Clean, modular implementation with no Flask dependencies.
"""

import logging
import structlog
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app
from elasticsearch import AsyncElasticsearch
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
import uvicorn

from config.settings import settings
from services import (
    SearchEngine, PropertyIndexer, WikipediaEnrichmentService,
    MarketAnalysisService, LocationService
)
from tools import (
    # Property tools
    search_properties_tool,
    get_property_details_tool,
    analyze_property_tool,
    find_similar_properties_tool,
    
    # Neighborhood tools
    analyze_neighborhood_tool,
    find_nearby_amenities_tool,
    get_walkability_score_tool,
    
    # Market tools
    analyze_market_trends_tool,
    calculate_investment_metrics_tool,
    compare_properties_tool,
    get_price_history_tool
)


# Configure structured logging
def setup_logging():
    """Configure structured logging based on settings."""
    log_level = getattr(logging, settings.log_level)
    
    if settings.log_format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=log_level,
    )


# Setup logging on module load
setup_logging()
logger = structlog.get_logger()


@dataclass
class ServerResources:
    """Shared server resources managed by lifespan."""
    es: Optional[AsyncElasticsearch] = None
    search_engine: Optional[SearchEngine] = None
    indexer: Optional[PropertyIndexer] = None
    enrichment_service: Optional[WikipediaEnrichmentService] = None
    market_service: Optional[MarketAnalysisService] = None
    location_service: Optional[LocationService] = None


# Global resources instance
resources = ServerResources()


# Initialize MCP server
mcp = FastMCP(
    name=settings.server.name
)


# Register MCP Tools

# Property tools
@mcp.tool
async def search_properties(
    query: Optional[str] = None,
    location: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_bathrooms: Optional[float] = None,
    max_bathrooms: Optional[float] = None,
    min_square_feet: Optional[int] = None,
    max_square_feet: Optional[int] = None,
    amenities: Optional[List[str]] = None,
    max_results: int = 20,
    search_mode: str = "semantic"
) -> Dict[str, Any]:
    """Search for properties matching specified criteria."""
    return await search_properties_tool(
        query, location, property_type, min_price, max_price,
        min_bedrooms, max_bedrooms, min_bathrooms, max_bathrooms,
        min_square_feet, max_square_feet, amenities, max_results, search_mode
    )


@mcp.tool
async def get_property_details(property_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific property."""
    return await get_property_details_tool(property_id)


@mcp.tool
async def analyze_property(property_id: str) -> Dict[str, Any]:
    """Perform comprehensive analysis of a property."""
    return await analyze_property_tool(property_id)


@mcp.tool
async def find_similar_properties(
    property_id: str,
    max_results: int = 10,
    max_price_diff_percent: float = 20.0,
    max_distance_miles: float = 5.0
) -> Dict[str, Any]:
    """Find properties similar to a given property."""
    return await find_similar_properties_tool(
        property_id, max_results, max_price_diff_percent, max_distance_miles
    )


# Neighborhood tools
@mcp.tool
async def analyze_neighborhood(
    location: str,
    radius_miles: float = 2.0
) -> Dict[str, Any]:
    """Analyze a neighborhood for amenities, walkability, and demographics."""
    return await analyze_neighborhood_tool(location, radius_miles)


@mcp.tool
async def find_nearby_amenities(
    location: str,
    category: Optional[str] = None,
    radius_miles: float = 1.0,
    max_results: int = 20
) -> Dict[str, Any]:
    """Find specific amenities near a location."""
    return await find_nearby_amenities_tool(
        location, category, radius_miles, max_results
    )


@mcp.tool
async def get_walkability_score(location: str) -> Dict[str, Any]:
    """Get detailed walkability score and analysis for a location."""
    return await get_walkability_score_tool(location)


# Market tools
@mcp.tool
async def analyze_market_trends(
    location: str,
    property_type: Optional[str] = None,
    time_period_days: int = 90
) -> Dict[str, Any]:
    """Analyze market trends for a specific location."""
    return await analyze_market_trends_tool(
        location, property_type, time_period_days
    )


@mcp.tool
async def calculate_investment_metrics(
    property_id: str,
    down_payment_percent: float = 20.0,
    mortgage_rate: float = 7.0,
    property_tax_rate: float = 1.2,
    insurance_annual: Optional[float] = None,
    hoa_monthly: Optional[float] = None,
    maintenance_percent: float = 1.0
) -> Dict[str, Any]:
    """Calculate detailed investment metrics for a property."""
    return await calculate_investment_metrics_tool(
        property_id, down_payment_percent, mortgage_rate,
        property_tax_rate, insurance_annual, hoa_monthly, maintenance_percent
    )


@mcp.tool
async def compare_properties(
    property_ids: List[str],
    comparison_factors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Compare multiple properties side by side."""
    return await compare_properties_tool(property_ids, comparison_factors)


@mcp.tool
async def get_price_history(
    property_id: str,
    include_estimates: bool = True
) -> Dict[str, Any]:
    """Get price history and estimates for a property."""
    return await get_price_history_tool(property_id, include_estimates)


@asynccontextmanager
async def lifespan(app):
    """Manage server lifecycle and resources."""
    # Startup
    logger.info(
        "starting_mcp_server",
        environment=settings.environment,
        debug=settings.debug,
        demo_mode=settings.is_demo
    )
    
    try:
        # Initialize Elasticsearch
        resources.es = AsyncElasticsearch(
            [settings.elasticsearch.url],
            timeout=settings.elasticsearch.timeout
        )
        
        # Verify Elasticsearch connection
        info = await resources.es.info()
        logger.info(
            "elasticsearch_connected",
            version=info['version']['number'],
            cluster_name=info['cluster_name']
        )
        
        # Initialize services
        resources.search_engine = SearchEngine(resources.es)
        resources.indexer = PropertyIndexer(resources.es)
        resources.enrichment_service = WikipediaEnrichmentService()
        resources.market_service = MarketAnalysisService(resources.es)
        resources.location_service = LocationService()
        
        # Setup demo index if needed
        if settings.is_demo and settings.demo.reset_on_startup:
            logger.info("setting_up_demo_index")
            await resources.indexer.setup_index(force_recreate=True)
            # Demo data loading would be done here
        
        logger.info("mcp_server_started_successfully")
        
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("shutting_down_mcp_server")
    
    if resources.es:
        await resources.es.close()
    
    logger.info("mcp_server_shutdown_complete")


# Apply lifespan to server
mcp.lifespan = lifespan


# HTTP API Endpoints
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    health_status = {
        "status": "healthy",
        "service": settings.server.name,
        "version": settings.server.version,
        "environment": settings.environment,
        "mcp_enabled": True
    }
    
    # Check Elasticsearch health
    if resources.es:
        try:
            es_health = await resources.es.cluster.health()
            health_status["archive_elasticsearch"] = {
                "status": es_health["status"],
                "number_of_nodes": es_health["number_of_nodes"],
                "active_shards": es_health["active_primary_shards"]
            }
        except Exception as e:
            health_status["archive_elasticsearch"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["archive_elasticsearch"] = {"status": "not_initialized"}
        health_status["status"] = "degraded"
    
    return JSONResponse(health_status)


async def demo_ui(request: Request) -> HTMLResponse:
    """Simple demo UI for testing the MCP server."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{settings.server.name} - MCP Server</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            h1 {{
                margin: 0 0 10px 0;
                color: #333;
                font-size: 2.5em;
            }}
            .subtitle {{
                color: #666;
                margin-bottom: 30px;
                font-size: 1.2em;
            }}
            .status {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                background: #10b981;
                color: white;
                font-size: 0.9em;
                margin-left: 10px;
            }}
            .section {{
                margin: 30px 0;
                padding: 20px;
                background: #f9fafb;
                border-radius: 8px;
            }}
            h2 {{
                color: #444;
                margin-top: 0;
            }}
            .endpoint {{
                background: white;
                padding: 12px;
                margin: 10px 0;
                border-radius: 6px;
                border: 1px solid #e5e7eb;
                font-family: 'Courier New', monospace;
            }}
            .method {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-weight: bold;
                margin-right: 10px;
                font-size: 0.9em;
            }}
            .get {{ background: #3b82f6; color: white; }}
            .post {{ background: #10b981; color: white; }}
            .info {{
                background: #fef3c7;
                border: 1px solid #fbbf24;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{settings.server.name} <span class="status">Active</span></h1>
            <div class="subtitle">{settings.server.description}</div>
            
            <div class="info">
                <strong>Environment:</strong> {settings.environment}<br>
                <strong>Version:</strong> {settings.server.version}<br>
                <strong>MCP Endpoint:</strong> http://{settings.server.host}:{settings.server.port}/mcp
            </div>
            
            <div class="section">
                <h2>Available Endpoints</h2>
                <div class="endpoint">
                    <span class="method get">GET</span> /health - Health check endpoint
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span> /demo - This demo interface
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span> /mcp - MCP protocol endpoint
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span> /sse - Server-sent events endpoint
                </div>
            </div>
            
            <div class="section">
                <h2>MCP Tools</h2>
                <p><strong>Property Tools:</strong></p>
                <ul>
                    <li><code>search_properties</code> - Search for properties with filters</li>
                    <li><code>get_property_details</code> - Get detailed property information</li>
                    <li><code>analyze_property</code> - Comprehensive property analysis</li>
                    <li><code>find_similar_properties</code> - Find similar properties</li>
                </ul>
                <p><strong>Neighborhood Tools:</strong></p>
                <ul>
                    <li><code>analyze_neighborhood</code> - Neighborhood analysis</li>
                    <li><code>find_nearby_amenities</code> - Find amenities</li>
                    <li><code>get_walkability_score</code> - Walkability analysis</li>
                </ul>
                <p><strong>Market Tools:</strong></p>
                <ul>
                    <li><code>analyze_market_trends</code> - Market trend analysis</li>
                    <li><code>calculate_investment_metrics</code> - Investment analysis</li>
                    <li><code>compare_properties</code> - Compare multiple properties</li>
                    <li><code>get_price_history</code> - Price history and estimates</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>Connect with Claude Desktop</h2>
                <p>Add this server to your Claude Desktop configuration:</p>
                <pre style="background: #1f2937; color: #f3f4f6; padding: 15px; border-radius: 8px; overflow-x: auto;">
{{
  "mcpServers": {{
    "real-estate-search": {{
      "command": "python",
      "args": ["-m", "mcp_server.main"],
      "env": {{
        "ENVIRONMENT": "demo"
      }}
    }}
  }}
}}</pre>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def create_app():
    """Create the FastMCP application with HTTP routes."""
    # Define custom HTTP routes
    custom_routes = [
        Route("/health", endpoint=health_check, methods=["GET"]),
        Route("/demo", endpoint=demo_ui, methods=["GET"])
    ]
    
    # Create the app with SSE support and custom routes
    app = create_sse_app(
        mcp,
        message_path="/mcp",
        sse_path="/sse",
        routes=custom_routes
    )
    
    return app


def run_server():
    """Run the MCP server."""
    app = create_app()
    
    logger.info(
        "starting_uvicorn_server",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload
    )
    
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    run_server()