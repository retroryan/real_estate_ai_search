"""Integration tests for MCP Server search services (Phase 2)."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from real_estate_search.mcp_server.config.settings import MCPServerConfig, EmbeddingConfig
from real_estate_search.mcp_server.services.embedding_service import (
    EmbeddingService,
    VoyageEmbeddingProvider,
    OpenAIEmbeddingProvider,
    EmbeddingProvider
)
from real_estate_search.mcp_server.services.property_search import PropertySearchService
from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
from real_estate_search.mcp_server.models.search import (
    PropertySearchRequest,
    WikipediaSearchRequest,
    PropertyFilter,
    PropertySearchResponse,
    WikipediaSearchResponse
)


class TestEmbeddingService:
    """Test embedding service."""
    
    def test_embedding_service_initialization(self):
        """Test embedding service initialization."""
        config = EmbeddingConfig(
            provider="voyage",
            model_name="voyage-3",
            dimension=1024,
            api_key="test-key"
        )
        
        with patch('real_estate_search.mcp_server.services.embedding_service.VoyageEmbeddingProvider') as mock_provider:
            service = EmbeddingService(config)
            assert service.config == config
            mock_provider.assert_called_once_with(config)
    
    def test_embed_text_validation(self):
        """Test text embedding validation."""
        config = EmbeddingConfig(provider="voyage", api_key="test-key")
        
        # Mock provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024
        
        service = EmbeddingService(config)
        service.provider = mock_provider
        
        # Test empty text
        with pytest.raises(ValueError):
            service.embed_text("")
        
        # Test valid text
        embedding = service.embed_text("test query")
        assert len(embedding) == 1024
        mock_provider.generate_embedding.assert_called_once_with("test query")
    
    def test_embed_texts_batch(self):
        """Test batch text embedding."""
        config = EmbeddingConfig(provider="voyage", api_key="test-key", batch_size=2)
        
        # Mock provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.generate_embeddings.return_value = [[0.1] * 1024] * 3
        
        service = EmbeddingService(config)
        service.provider = mock_provider
        
        # Test batch embedding
        texts = ["text1", "text2", "text3"]
        embeddings = service.embed_texts(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 1024 for e in embeddings)
        mock_provider.generate_embeddings.assert_called_once_with(texts)
    
    def test_create_query_embedding(self):
        """Test query embedding creation."""
        config = EmbeddingConfig(
            provider="voyage",
            model_name="voyage-3",
            dimension=1024,
            api_key="test-key"
        )
        
        # Mock provider
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024
        
        service = EmbeddingService(config)
        service.provider = mock_provider
        
        result = service.create_query_embedding("test query")
        
        assert "vector" in result
        assert "dimension" in result
        assert "model" in result
        assert "provider" in result
        assert result["dimension"] == 1024
        assert result["model"] == "voyage-3"
        assert result["provider"] == "voyage"


class TestPropertySearchService:
    """Test property search service."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create mock Elasticsearch client."""
        client = Mock(spec=ElasticsearchClient)
        client.search.return_value = {
            "hits": {
                "total": {"value": 10},
                "max_score": 0.95,
                "hits": [
                    {
                        "_source": {
                            "listing_id": "PROP-001",
                            "property_type": "House",
                            "price": 500000,
                            "bedrooms": 3,
                            "bathrooms": 2,
                            "description": "Beautiful home"
                        },
                        "_score": 0.95
                    }
                ]
            }
        }
        return client
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock(spec=EmbeddingService)
        service.embed_text.return_value = [0.1] * 1024
        service.embed_texts.return_value = [[0.1] * 1024]
        return service
    
    def test_property_search_initialization(self, mock_es_client, mock_embedding_service):
        """Test property search service initialization."""
        config = MCPServerConfig.from_env()
        
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        assert service.config == config
        assert service.es_client == mock_es_client
        assert service.embedding_service == mock_embedding_service
        assert service.index_name == config.elasticsearch.property_index
    
    def test_build_filter_query(self, mock_es_client, mock_embedding_service):
        """Test filter query building."""
        config = MCPServerConfig.from_env()
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        # Test with multiple filters
        filters = PropertyFilter(
            property_type="House",
            min_price=200000,
            max_price=500000,
            min_bedrooms=2,
            city="San Francisco",
            state="CA"
        )
        
        filter_clauses = service.build_filter_query(filters)
        
        assert len(filter_clauses) == 5
        assert {"term": {"property_type": "House"}} in filter_clauses
        assert {"term": {"address.city": "san francisco"}} in filter_clauses
        assert {"term": {"address.state": "CA"}} in filter_clauses
    
    def test_build_text_query(self, mock_es_client, mock_embedding_service):
        """Test text query building."""
        config = MCPServerConfig.from_env()
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        query = service.build_text_query("modern home with pool")
        
        assert "multi_match" in query
        assert query["multi_match"]["query"] == "modern home with pool"
        assert "description^3" in query["multi_match"]["fields"]
    
    def test_search_text_mode(self, mock_es_client, mock_embedding_service):
        """Test text search mode."""
        config = MCPServerConfig.from_env()
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        request = PropertySearchRequest(
            query="modern home",
            search_type="text",
            size=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, PropertySearchResponse)
        assert response.metadata.total_hits == 10
        assert response.metadata.returned_hits == 1
        assert response.original_query == "modern home"
        assert len(response.results) == 1
        
        # Verify embedding service not called for text search
        mock_embedding_service.embed_text.assert_not_called()
    
    def test_search_semantic_mode(self, mock_es_client, mock_embedding_service):
        """Test semantic search mode."""
        config = MCPServerConfig.from_env()
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        request = PropertySearchRequest(
            query="family home near parks",
            search_type="semantic",
            size=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, PropertySearchResponse)
        assert response.metadata.query_type == "semantic"
        
        # Verify embedding service called
        mock_embedding_service.embed_text.assert_called_once_with("family home near parks")
    
    def test_search_hybrid_mode(self, mock_es_client, mock_embedding_service):
        """Test hybrid search mode."""
        config = MCPServerConfig.from_env()
        service = PropertySearchService(config, mock_es_client, mock_embedding_service)
        
        request = PropertySearchRequest(
            query="luxury condo downtown",
            search_type="hybrid",
            size=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, PropertySearchResponse)
        assert response.metadata.query_type == "hybrid"
        
        # Verify embedding service called for hybrid search
        mock_embedding_service.embed_text.assert_called_once_with("luxury condo downtown")


class TestWikipediaSearchService:
    """Test Wikipedia search service."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create mock Elasticsearch client."""
        client = Mock(spec=ElasticsearchClient)
        client.search.return_value = {
            "hits": {
                "total": {"value": 5},
                "max_score": 0.85,
                "hits": [
                    {
                        "_source": {
                            "page_id": "WIKI-001",
                            "title": "Golden Gate Bridge",
                            "short_summary": "Famous bridge in San Francisco",
                            "best_city": "san francisco",
                            "best_state": "CA"
                        },
                        "_score": 0.85,
                        "_index": "wikipedia"
                    }
                ]
            }
        }
        return client
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock(spec=EmbeddingService)
        service.embed_text.return_value = [0.1] * 1024
        return service
    
    def test_wikipedia_search_initialization(self, mock_es_client, mock_embedding_service):
        """Test Wikipedia search service initialization."""
        config = MCPServerConfig.from_env()
        
        service = WikipediaSearchService(config, mock_es_client, mock_embedding_service)
        
        assert service.config == config
        assert service.es_client == mock_es_client
        assert service.embedding_service == mock_embedding_service
    
    def test_get_index_for_search(self, mock_es_client, mock_embedding_service):
        """Test index selection based on search type."""
        config = MCPServerConfig.from_env()
        service = WikipediaSearchService(config, mock_es_client, mock_embedding_service)
        
        assert service.get_index_for_search("full") == "wikipedia"
        assert service.get_index_for_search("chunks").startswith("wiki_chunks")
        assert service.get_index_for_search("summaries").startswith("wiki_summaries")
    
    def test_search_full_content(self, mock_es_client, mock_embedding_service):
        """Test searching full Wikipedia content."""
        config = MCPServerConfig.from_env()
        service = WikipediaSearchService(config, mock_es_client, mock_embedding_service)
        
        request = WikipediaSearchRequest(
            query="Golden Gate Bridge history",
            search_in="full",
            search_type="text"
        )
        
        response = service.search(request)
        
        assert isinstance(response, WikipediaSearchResponse)
        assert response.metadata.total_hits == 5
        assert response.metadata.returned_hits == 1
        assert response.original_query == "Golden Gate Bridge history"
        assert response.search_in == "full"
        assert len(response.results) == 1
        assert response.results[0]["entity_type"] == "wikipedia_article"
    
    def test_search_with_filters(self, mock_es_client, mock_embedding_service):
        """Test Wikipedia search with filters."""
        config = MCPServerConfig.from_env()
        service = WikipediaSearchService(config, mock_es_client, mock_embedding_service)
        
        request = WikipediaSearchRequest(
            query="landmarks",
            city="San Francisco",
            state="CA",
            search_type="text"
        )
        
        response = service.search(request)
        
        assert isinstance(response, WikipediaSearchResponse)
        
        # Verify the search was called with appropriate filters
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        
        # Check that filters were applied
        assert "query" in body
        if "bool" in body["query"] and "filter" in body["query"]["bool"]:
            filters = body["query"]["bool"]["filter"]
            assert any("term" in f and "best_city" in f.get("term", {}) for f in filters)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])