"""Integration tests for MCP Server foundation (Phase 1)."""

import pytest
from pathlib import Path
from datetime import datetime

from real_estate_search.mcp_server.config.settings import (
    MCPServerConfig,
    ElasticsearchConfig,
    EmbeddingConfig,
    SearchConfig,
    LoggingConfig
)
from real_estate_search.mcp_server.models.property import (
    Property,
    Address,
    Neighborhood,
    Parking,
    PropertySearchResult
)
from real_estate_search.mcp_server.models.wikipedia import (
    WikipediaArticle,
    WikipediaSearchResult,
    WikipediaChunk
)
from real_estate_search.mcp_server.models.search import (
    PropertyFilter,
    PropertySearchRequest,
    WikipediaSearchRequest,
    SearchMetadata,
    HealthCheckResponse,
    ErrorResponse
)
from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
from real_estate_search.mcp_server.services.health_check import HealthCheckService
from real_estate_search.mcp_server.utils.logging import setup_logging, get_logger


class TestConfiguration:
    """Test configuration module."""
    
    def test_config_from_env(self):
        """Test loading configuration from environment."""
        config = MCPServerConfig.from_env()
        
        assert config.server_name == "real-estate-search-mcp"
        assert config.server_version == "0.1.0"
        assert isinstance(config.elasticsearch, ElasticsearchConfig)
        assert isinstance(config.embedding, EmbeddingConfig)
        assert isinstance(config.search, SearchConfig)
        assert isinstance(config.logging, LoggingConfig)
    
    def test_config_from_yaml(self):
        """Test loading configuration from YAML."""
        yaml_path = Path(__file__).parent.parent / "mcp_server/config/config.yaml"
        if yaml_path.exists():
            config = MCPServerConfig.from_yaml(yaml_path)
            
            assert config.server_name == "real-estate-search-mcp"
            assert config.elasticsearch.host == "localhost"
            assert config.elasticsearch.port == 9200
            assert config.embedding.provider == "voyage"
            assert config.embedding.dimension == 1024
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid port
        with pytest.raises(ValueError):
            ElasticsearchConfig(port=100000)
        
        # Test invalid dimension
        with pytest.raises(ValueError):
            EmbeddingConfig(dimension=-1)
        
        # Test invalid batch size
        with pytest.raises(ValueError):
            EmbeddingConfig(batch_size=1000)
        
        # Test invalid weights
        with pytest.raises(ValueError):
            SearchConfig(vector_weight=1.5)


class TestModels:
    """Test Pydantic models."""
    
    def test_address_model(self):
        """Test Address model validation."""
        address = Address(
            street="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            latitude=37.7749,
            longitude=-122.4194
        )
        
        assert address.state == "CA"
        assert address.latitude == 37.7749
        
        # Test invalid state
        with pytest.raises(ValueError):
            Address(
                street="123 Main St",
                city="San Francisco",
                state="California",  # Should be 2-letter code
                zip_code="94102"
            )
        
        # Test invalid latitude
        with pytest.raises(ValueError):
            Address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94102",
                latitude=100  # Invalid latitude
            )
    
    def test_property_model(self):
        """Test Property model validation."""
        property_data = Property(
            listing_id="PROP-001",
            property_type="House",
            price=500000,
            bedrooms=3,
            bathrooms=2.5,
            square_feet=2000,
            address=Address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94102"
            ),
            description="Beautiful home in the heart of the city"
        )
        
        assert property_data.listing_id == "PROP-001"
        assert property_data.bathrooms == 2.5
        
        # Test invalid property type
        with pytest.raises(ValueError):
            Property(
                listing_id="PROP-002",
                property_type="Castle",  # Invalid type
                price=500000,
                bedrooms=3,
                bathrooms=2,
                square_feet=2000,
                address=Address(
                    street="456 Oak Ave",
                    city="San Francisco",
                    state="CA",
                    zip_code="94103"
                ),
                description="Test property"
            )
        
        # Test invalid bathrooms (not 0.5 increment)
        with pytest.raises(ValueError):
            Property(
                listing_id="PROP-003",
                property_type="House",
                price=500000,
                bedrooms=3,
                bathrooms=2.3,  # Should be in 0.5 increments
                square_feet=2000,
                address=Address(
                    street="789 Pine St",
                    city="San Francisco",
                    state="CA",
                    zip_code="94104"
                ),
                description="Test property"
            )
    
    def test_search_request_models(self):
        """Test search request models."""
        # Property search request
        prop_request = PropertySearchRequest(
            query="modern home with pool",
            size=10,
            search_type="hybrid"
        )
        
        assert prop_request.query == "modern home with pool"
        assert prop_request.size == 10
        assert prop_request.from_ == 0
        
        # Wikipedia search request
        wiki_request = WikipediaSearchRequest(
            query="Golden Gate Bridge history",
            search_in="full",
            include_highlights=True
        )
        
        assert wiki_request.query == "Golden Gate Bridge history"
        assert wiki_request.search_in == "full"
    
    def test_property_filter_validation(self):
        """Test PropertyFilter validation."""
        # Valid filter
        filter_obj = PropertyFilter(
            min_price=100000,
            max_price=500000,
            min_bedrooms=2,
            max_bedrooms=4
        )
        
        assert filter_obj.min_price == 100000
        assert filter_obj.max_price == 500000
        
        # Invalid price range
        with pytest.raises(ValueError):
            PropertyFilter(
                min_price=500000,
                max_price=100000  # max < min
            )
        
        # Invalid bedroom range
        with pytest.raises(ValueError):
            PropertyFilter(
                min_bedrooms=4,
                max_bedrooms=2  # max < min
            )


class TestElasticsearchClient:
    """Test Elasticsearch client wrapper."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        config = ElasticsearchConfig()
        client = ElasticsearchClient(config)
        
        assert client.config == config
        assert client.client is not None
    
    def test_client_context_manager(self):
        """Test client as context manager."""
        config = ElasticsearchConfig()
        
        with ElasticsearchClient(config) as client:
            assert client.client is not None
        
        # Client should be closed after context
        assert client._client is None or not client._client.transport.pool.closed


class TestHealthCheck:
    """Test health check service."""
    
    def test_health_check_initialization(self):
        """Test health check service initialization."""
        config = MCPServerConfig.from_env()
        es_client = ElasticsearchClient(config.elasticsearch)
        
        health_service = HealthCheckService(config, es_client)
        
        assert health_service.config == config
        assert health_service.es_client == es_client
    
    def test_overall_status_determination(self):
        """Test overall status determination logic."""
        config = MCPServerConfig.from_env()
        es_client = ElasticsearchClient(config.elasticsearch)
        health_service = HealthCheckService(config, es_client)
        
        # All healthy
        services = {
            "service1": {"status": "healthy"},
            "service2": {"status": "healthy"}
        }
        assert health_service.get_overall_status(services) == "healthy"
        
        # One degraded
        services = {
            "service1": {"status": "healthy"},
            "service2": {"status": "degraded"}
        }
        assert health_service.get_overall_status(services) == "degraded"
        
        # One unhealthy
        services = {
            "service1": {"status": "healthy"},
            "service2": {"status": "unhealthy"}
        }
        assert health_service.get_overall_status(services) == "unhealthy"


class TestLogging:
    """Test logging configuration."""
    
    def test_logging_setup(self):
        """Test logging setup."""
        config = LoggingConfig(level="INFO", structured=False)
        setup_logging(config)
        
        logger = get_logger("test_logger")
        assert logger is not None
        assert logger.level <= 20  # INFO level
    
    def test_structured_logging(self):
        """Test structured logging formatter."""
        from real_estate_search.mcp_server.utils.logging import StructuredFormatter
        import logging
        
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "timestamp" in formatted
        assert "level" in formatted
        assert "message" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])