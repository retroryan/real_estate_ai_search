"""Integration tests for MCP Server (Phase 3)."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from real_estate_search.mcp_server.main import MCPServer
from real_estate_search.mcp_server.config.settings import MCPServerConfig
from real_estate_search.mcp_server.tools.property_tools import search_properties, get_property_details
from real_estate_search.mcp_server.tools.wikipedia_tools import (
    search_wikipedia,
    get_wikipedia_article,
    search_wikipedia_by_location
)


class TestMCPServer:
    """Test MCP Server initialization and configuration."""
    
    def test_server_initialization_from_env(self):
        """Test server initialization from environment."""
        server = MCPServer()
        
        assert server.config is not None
        assert isinstance(server.config, MCPServerConfig)
        assert server.config.server_name == "real-estate-search-mcp"
        assert server.app is not None
    
    def test_server_initialization_from_yaml(self):
        """Test server initialization from YAML config."""
        config_path = Path(__file__).parent.parent / "mcp_server/config/config.yaml"
        if config_path.exists():
            server = MCPServer(config_path)
            
            assert server.config is not None
            assert server.config.server_name == "real-estate-search-mcp"
            assert server.config.debug is True
    
    @patch('real_estate_search.mcp_server.services.elasticsearch_client.ElasticsearchClient')
    @patch('real_estate_search.mcp_server.services.embedding_service.EmbeddingService')
    def test_service_initialization(self, mock_embedding_service, mock_es_client):
        """Test service initialization."""
        server = MCPServer()
        
        # Mock service constructors
        mock_es_instance = Mock()
        mock_embedding_instance = Mock()
        mock_es_client.return_value = mock_es_instance
        mock_embedding_service.return_value = mock_embedding_instance
        
        # Initialize services
        server._initialize_services()
        
        # Verify services were created
        assert server.es_client is not None
        assert server.embedding_service is not None
        assert server.property_search_service is not None
        assert server.wikipedia_search_service is not None
        assert server.health_check_service is not None
    
    def test_context_creation(self):
        """Test context creation for tools."""
        server = MCPServer()
        
        # Mock services
        server.config = MCPServerConfig.from_env()
        server.es_client = Mock()
        server.embedding_service = Mock()
        server.property_search_service = Mock()
        server.wikipedia_search_service = Mock()
        server.health_check_service = Mock()
        
        context = server._create_context()
        
        assert context.get("config") == server.config
        assert context.get("es_client") == server.es_client
        assert context.get("embedding_service") == server.embedding_service
        assert context.get("property_search_service") == server.property_search_service
        assert context.get("wikipedia_search_service") == server.wikipedia_search_service
        assert context.get("health_check_service") == server.health_check_service


class TestPropertyTools:
    """Test property search tools."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context with services."""
        context = Mock()
        property_service = Mock()
        property_service.search.return_value = Mock(
            metadata=Mock(
                total_hits=5,
                returned_hits=2,
                execution_time_ms=150
            ),
            results=[
                {
                    "listing_id": "PROP-001",
                    "property_type": "House",
                    "price": 500000,
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "square_feet": 2000,
                    "description": "Beautiful home with modern amenities",
                    "address": {
                        "street": "123 Main St",
                        "city": "San Francisco",
                        "state": "CA",
                        "zip_code": "94102"
                    },
                    "features": ["pool", "garage"],
                    "amenities": ["gym", "park"],
                    "_score": 0.85
                }
            ]
        )
        context.get.return_value = property_service
        return context
    
    @pytest.mark.asyncio
    async def test_search_properties_tool(self, mock_context):
        """Test property search tool."""
        result = await search_properties(
            mock_context,
            query="modern home with pool",
            min_price=200000,
            max_price=600000,
            size=10
        )
        
        assert "query" in result
        assert "total_results" in result
        assert "properties" in result
        assert result["query"] == "modern home with pool"
        assert result["total_results"] == 5
        assert len(result["properties"]) == 1
        
        property_result = result["properties"][0]
        assert property_result["listing_id"] == "PROP-001"
        assert property_result["property_type"] == "House"
        assert property_result["price"] == 500000
        assert "address" in property_result
    
    @pytest.mark.asyncio
    async def test_get_property_details_tool(self):
        """Test property details tool."""
        context = Mock()
        es_client = Mock()
        config = Mock()
        
        es_client.get_document.return_value = {
            "listing_id": "PROP-001",
            "property_type": "House",
            "price": 500000,
            "description": "Detailed property information"
        }
        
        context.get.side_effect = lambda key: {
            "es_client": es_client,
            "config": config
        }.get(key)
        
        result = await get_property_details(context, "PROP-001")
        
        assert "listing_id" in result
        assert "property" in result
        assert result["listing_id"] == "PROP-001"
        assert result["property"]["property_type"] == "House"
    
    @pytest.mark.asyncio
    async def test_property_search_error_handling(self):
        """Test property search error handling."""
        context = Mock()
        context.get.return_value = None  # Service not available
        
        result = await search_properties(context, query="test query")
        
        assert "error" in result
        assert "query" in result
        assert result["query"] == "test query"


class TestWikipediaTools:
    """Test Wikipedia search tools."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context with Wikipedia service."""
        context = Mock()
        wikipedia_service = Mock()
        wikipedia_service.search.return_value = Mock(
            metadata=Mock(
                total_hits=3,
                returned_hits=1,
                execution_time_ms=200
            ),
            results=[
                {
                    "page_id": "WIKI-001",
                    "title": "Golden Gate Bridge",
                    "short_summary": "Famous suspension bridge in San Francisco",
                    "entity_type": "wikipedia_article",
                    "best_city": "san francisco",
                    "best_state": "CA",
                    "key_topics": ["bridge", "architecture", "transportation"],
                    "_score": 0.92
                }
            ]
        )
        context.get.return_value = wikipedia_service
        return context
    
    @pytest.mark.asyncio
    async def test_search_wikipedia_tool(self, mock_context):
        """Test Wikipedia search tool."""
        result = await search_wikipedia(
            mock_context,
            query="Golden Gate Bridge history",
            search_in="full",
            city="San Francisco",
            state="CA"
        )
        
        assert "query" in result
        assert "articles" in result
        assert result["query"] == "Golden Gate Bridge history"
        assert result["search_in"] == "full"
        assert result["total_results"] == 3
        assert len(result["articles"]) == 1
        
        article = result["articles"][0]
        assert article["page_id"] == "WIKI-001"
        assert article["title"] == "Golden Gate Bridge"
        assert "location" in article
        assert article["location"]["city"] == "san francisco"
    
    @pytest.mark.asyncio
    async def test_search_wikipedia_by_location_tool(self, mock_context):
        """Test Wikipedia location search tool."""
        result = await search_wikipedia_by_location(
            mock_context,
            city="San Francisco",
            state="CA",
            query="landmarks"
        )
        
        assert "location" in result
        assert "articles" in result
        assert result["location"]["city"] == "San Francisco"
        assert result["location"]["state"] == "CA"
        assert "search_query" in result
        assert "landmarks" in result["search_query"]
    
    @pytest.mark.asyncio
    async def test_get_wikipedia_article_tool(self):
        """Test Wikipedia article details tool."""
        context = Mock()
        es_client = Mock()
        config = Mock()
        
        es_client.get_document.return_value = {
            "page_id": "WIKI-001",
            "title": "Golden Gate Bridge",
            "url": "https://en.wikipedia.org/wiki/Golden_Gate_Bridge",
            "short_summary": "Famous bridge",
            "long_summary": "The Golden Gate Bridge is a suspension bridge...",
            "key_topics": ["bridge", "engineering"],
            "content_loaded": True
        }
        
        context.get.side_effect = lambda key: {
            "es_client": es_client,
            "config": config
        }.get(key)
        
        result = await get_wikipedia_article(context, "WIKI-001")
        
        assert "page_id" in result
        assert "title" in result
        assert "url" in result
        assert result["page_id"] == "WIKI-001"
        assert result["title"] == "Golden Gate Bridge"


class TestToolIntegration:
    """Test tool integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_property_search_with_location_context(self):
        """Test using Wikipedia tools to provide context for property searches."""
        # This would be a more complex integration test combining both tools
        # For now, we'll test that both tools can work with the same context
        
        context = Mock()
        
        # Mock services
        property_service = Mock()
        wikipedia_service = Mock()
        
        # Setup property search response
        property_service.search.return_value = Mock(
            metadata=Mock(total_hits=1, returned_hits=1, execution_time_ms=100),
            results=[{"listing_id": "PROP-001", "address": {"city": "San Francisco"}}]
        )
        
        # Setup Wikipedia search response
        wikipedia_service.search.return_value = Mock(
            metadata=Mock(total_hits=1, returned_hits=1, execution_time_ms=150),
            results=[{"page_id": "WIKI-001", "title": "San Francisco", "entity_type": "wikipedia_article"}]
        )
        
        def mock_get(key):
            if "property_search_service" in key:
                return property_service
            elif "wikipedia_search_service" in key:
                return wikipedia_service
            return None
        
        context.get.side_effect = mock_get
        
        # Test property search
        prop_result = await search_properties(context, "home in San Francisco")
        assert "properties" in prop_result
        
        # Test Wikipedia search for same location
        wiki_result = await search_wikipedia_by_location(context, "San Francisco")
        assert "articles" in wiki_result
        
        # Both should work with the same context
        assert prop_result["properties"][0]["address"]["city"] == "San Francisco"
        assert wiki_result["location"]["city"] == "San Francisco"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])