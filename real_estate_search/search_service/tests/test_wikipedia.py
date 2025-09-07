"""
Tests for Wikipedia search service.
"""

import pytest
from unittest.mock import Mock
from elasticsearch import Elasticsearch

from ..wikipedia import WikipediaSearchService
from ..models import (
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    WikipediaSearchType
)


class TestWikipediaSearchService:
    """Test cases for WikipediaSearchService."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock(spec=Elasticsearch)
    
    @pytest.fixture
    def service(self, mock_es_client):
        """Create a WikipediaSearchService instance with mock client."""
        return WikipediaSearchService(mock_es_client)
    
    @pytest.fixture
    def sample_es_response(self):
        """Sample Elasticsearch response for Wikipedia articles."""
        return {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "page-001",
                        "_score": 0.98,
                        "_source": {
                            "page_id": "page-001",
                            "title": "San Francisco",
                            "url": "https://en.wikipedia.org/wiki/San_Francisco",
                            "summary": "San Francisco is a city in California",
                            "categories": ["Cities in California", "San Francisco Bay Area"],
                            "content_length": 50000,
                            "full_content": "San Francisco, officially the City and County..."
                        }
                    },
                    {
                        "_id": "page-002",
                        "_score": 0.87,
                        "_source": {
                            "page_id": "page-002",
                            "title": "Golden Gate Bridge",
                            "url": "https://en.wikipedia.org/wiki/Golden_Gate_Bridge",
                            "summary": "The Golden Gate Bridge is a suspension bridge",
                            "categories": ["Bridges in San Francisco", "Landmarks"],
                            "content_length": 35000,
                            "full_content": "The Golden Gate Bridge is a suspension bridge..."
                        }
                    }
                ]
            },
            "execution_time_ms": 45
        }
    
    def test_search_fulltext(self, service, mock_es_client, sample_es_response):
        """Test full-text search."""
        mock_es_client.search.return_value = sample_es_response
        
        response = service.search_fulltext(
            query="San Francisco bridges",
            size=10
        )
        
        assert isinstance(response, WikipediaSearchResponse)
        assert response.total_hits == 2
        assert len(response.results) == 2
        assert response.results[0].page_id == "page-001"
        assert response.results[0].title == "San Francisco"
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        
        # Verify Elasticsearch was called correctly
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args[1]["index"] == "wikipedia"
        query_body = call_args[1]["body"]
        assert "multi_match" in str(query_body)
        assert "title^3" in str(query_body)
    
    def test_search_chunks(self, service, mock_es_client):
        """Test chunk-based search."""
        chunk_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_id": "chunk-001",
                    "_score": 0.92,
                    "_source": {
                        "page_id": "page-001",
                        "chunk_id": "chunk-001",
                        "title": "San Francisco",
                        "url": "https://en.wikipedia.org/wiki/San_Francisco",
                        "chunk_content": "The city of San Francisco...",
                        "categories": ["Cities in California"]
                    }
                }]
            },
            "execution_time_ms": 30
        }
        
        mock_es_client.search.return_value = chunk_response
        
        response = service.search_chunks(
            query="city history",
            size=10
        )
        
        assert isinstance(response, WikipediaSearchResponse)
        assert response.total_hits == 1
        assert response.results[0].chunk_id == "chunk-001"
        assert response.search_type == WikipediaSearchType.CHUNKS
        
        # Verify correct index pattern
        call_args = mock_es_client.search.call_args
        assert "wiki_chunks_*" in call_args[1]["index"]
    
    def test_search_summaries(self, service, mock_es_client):
        """Test summary search."""
        summary_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_id": "sum-001",
                    "_score": 0.89,
                    "_source": {
                        "page_id": "page-001",
                        "title": "San Francisco",
                        "url": "https://en.wikipedia.org/wiki/San_Francisco",
                        "summary": "San Francisco is a major city...",
                        "categories": ["Cities"]
                    }
                }]
            },
            "execution_time_ms": 25
        }
        
        mock_es_client.search.return_value = summary_response
        
        response = service.search_summaries(
            query="major city",
            size=10
        )
        
        assert isinstance(response, WikipediaSearchResponse)
        assert response.total_hits == 1
        assert response.search_type == WikipediaSearchType.SUMMARIES
        
        # Verify correct index pattern
        call_args = mock_es_client.search.call_args
        assert "wiki_summaries_*" in call_args[1]["index"]
    
    def test_search_by_category(self, service, mock_es_client, sample_es_response):
        """Test category filtering."""
        mock_es_client.search.return_value = sample_es_response
        
        response = service.search_by_category(
            categories=["Cities in California", "Landmarks"],
            query="bridge",
            size=10
        )
        
        assert isinstance(response, WikipediaSearchResponse)
        assert response.applied_categories == ["Cities in California", "Landmarks"]
        
        # Verify category filter was applied
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "filter" in query_body["query"]["bool"]
        assert "terms" in str(query_body["query"]["bool"]["filter"])
        assert "categories" in str(query_body["query"]["bool"]["filter"])
    
    def test_search_with_highlights(self, service, mock_es_client):
        """Test search with highlighting."""
        response_with_highlights = {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_id": "page-001",
                    "_score": 0.95,
                    "_source": {
                        "page_id": "page-001",
                        "title": "San Francisco",
                        "url": "https://en.wikipedia.org/wiki/San_Francisco",
                        "summary": "San Francisco is a city",
                        "categories": ["Cities"],
                        "content_length": 10000
                    },
                    "highlight": {
                        "full_content": [
                            "The <em>San Francisco</em> Bay Area...",
                            "<em>San Francisco</em> is known for..."
                        ],
                        "summary": ["<em>San Francisco</em> is a city"]
                    }
                }]
            },
            "execution_time_ms": 35
        }
        
        mock_es_client.search.return_value = response_with_highlights
        
        request = WikipediaSearchRequest(
            query="San Francisco",
            search_type=WikipediaSearchType.FULL_TEXT,
            include_highlights=True,
            highlight_fragment_size=200,
            size=10
        )
        
        response = service.search(request)
        
        assert response.results[0].highlights is not None
        assert len(response.results[0].highlights) == 3
        assert "<em>San Francisco</em>" in response.results[0].highlights[0]
        
        # Verify highlight configuration
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "highlight" in query_body
        assert query_body["highlight"]["fields"]["full_content"]["fragment_size"] == 200
    
    def test_search_without_query(self, service, mock_es_client, sample_es_response):
        """Test search with only category filters."""
        mock_es_client.search.return_value = sample_es_response
        
        request = WikipediaSearchRequest(
            query="",
            search_type=WikipediaSearchType.FULL_TEXT,
            categories=["Cities in California"],
            size=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, WikipediaSearchResponse)
        
        # Verify match_all query was used
        call_args = mock_es_client.search.call_args
        query_body = call_args[1]["body"]
        assert "match_all" in str(query_body["query"]["bool"]["must"])
    
    def test_search_with_pagination(self, service, mock_es_client, sample_es_response):
        """Test search with pagination."""
        mock_es_client.search.return_value = sample_es_response
        
        request = WikipediaSearchRequest(
            query="San Francisco",
            search_type=WikipediaSearchType.FULL_TEXT,
            size=5,
            from_offset=10
        )
        
        response = service.search(request)
        
        assert isinstance(response, WikipediaSearchResponse)
        
        # Verify pagination parameters
        call_args = mock_es_client.search.call_args
        assert call_args[1]["body"]["size"] == 5
        assert call_args[1]["body"]["from"] == 10
    
    def test_search_error_handling(self, service, mock_es_client):
        """Test error handling during search."""
        mock_es_client.search.side_effect = Exception("Elasticsearch error")
        
        with pytest.raises(Exception) as exc_info:
            service.search_fulltext("test query")
        
        assert "Elasticsearch error" in str(exc_info.value)
    
    def test_get_index_for_search_type(self, service):
        """Test index selection based on search type."""
        assert service._get_index_for_search_type(WikipediaSearchType.FULL_TEXT) == "wikipedia"
        assert service._get_index_for_search_type(WikipediaSearchType.CHUNKS) == "wiki_chunks_*"
        assert service._get_index_for_search_type(WikipediaSearchType.SUMMARIES) == "wiki_summaries_*"