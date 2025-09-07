"""
Tests for base search service.
"""

import pytest
from unittest.mock import Mock
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError
from ..base import BaseSearchService
from ..models import SearchError


class TestBaseSearchService:
    """Test cases for BaseSearchService."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock(spec=Elasticsearch)
    
    @pytest.fixture
    def service(self, mock_es_client):
        """Create a BaseSearchService instance with mock client."""
        return BaseSearchService(mock_es_client)
    
    def test_init(self, mock_es_client):
        """Test service initialization."""
        service = BaseSearchService(mock_es_client)
        assert service.es_client == mock_es_client
        assert service.logger is not None
    
    def test_execute_search_success(self, service, mock_es_client):
        """Test successful search execution."""
        mock_response = {
            "hits": {
                "total": {"value": 10},
                "hits": [
                    {"_id": "1", "_source": {"field": "value"}}
                ]
            }
        }
        mock_es_client.search.return_value = mock_response
        
        result = service.execute_search(
            index="test_index",
            query={"match_all": {}},
            size=5,
            from_offset=0
        )
        
        assert "execution_time_ms" in result
        assert result["hits"]["total"]["value"] == 10
        mock_es_client.search.assert_called_once()
    
    def test_execute_search_error(self, service, mock_es_client):
        """Test search execution with error."""
        mock_es_client.search.side_effect = TransportError("Connection error")
        
        with pytest.raises(TransportError):
            service.execute_search(
                index="test_index",
                query={"match_all": {}}
            )
    
    def test_get_document_success(self, service, mock_es_client):
        """Test successful document retrieval."""
        mock_response = {
            "_source": {"field": "value"}
        }
        mock_es_client.get.return_value = mock_response
        
        result = service.get_document("test_index", "doc_1")
        
        assert result == {"field": "value"}
        mock_es_client.get.assert_called_once_with(
            index="test_index",
            id="doc_1"
        )
    
    def test_get_document_not_found(self, service, mock_es_client):
        """Test document retrieval when not found."""
        mock_es_client.get.side_effect = Exception("Not found")
        
        result = service.get_document("test_index", "doc_1")
        
        assert result is None
    
    def test_multi_search_success(self, service, mock_es_client):
        """Test successful multi-search."""
        mock_response = {
            "responses": [
                {"hits": {"total": {"value": 5}}},
                {"hits": {"total": {"value": 3}}}
            ]
        }
        mock_es_client.msearch.return_value = mock_response
        
        searches = [
            ("index1", {"match_all": {}}),
            ("index2", {"term": {"field": "value"}})
        ]
        
        result = service.multi_search(searches)
        
        assert len(result) == 2
        assert result[0]["hits"]["total"]["value"] == 5
        assert result[1]["hits"]["total"]["value"] == 3
    
    def test_validate_index_exists(self, service, mock_es_client):
        """Test index existence validation."""
        mock_es_client.indices = Mock()
        mock_es_client.indices.exists = Mock(return_value=True)
        
        result = service.validate_index_exists("test_index")
        
        assert result is True
        mock_es_client.indices.exists.assert_called_once_with(index="test_index")
    
    def test_handle_search_error(self, service):
        """Test error handling."""
        error = ValueError("Test error")
        
        search_error = service.handle_search_error(error, "test context")
        
        assert search_error.error_type == "ValueError"
        assert "test context" in search_error.message
        assert search_error.details == {"context": "test context"}
    
    def test_extract_highlights(self, service):
        """Test highlight extraction."""
        hit_with_highlights = {
            "highlight": {
                "field1": ["<em>highlighted</em> text"],
                "field2": ["another <em>highlight</em>"]
            }
        }
        
        highlights = service.extract_highlights(hit_with_highlights)
        
        assert highlights is not None
        assert "field1" in highlights
        assert "field2" in highlights
        assert len(highlights["field1"]) == 1
    
    def test_extract_highlights_none(self, service):
        """Test highlight extraction when no highlights."""
        hit_without_highlights = {"_source": {"field": "value"}}
        
        highlights = service.extract_highlights(hit_without_highlights)
        
        assert highlights is None
    
    def test_calculate_total_hits_dict(self, service):
        """Test total hits calculation with dict format."""
        response = {
            "hits": {
                "total": {"value": 100, "relation": "eq"}
            }
        }
        
        total = service.calculate_total_hits(response)
        
        assert total == 100
    
    def test_calculate_total_hits_int(self, service):
        """Test total hits calculation with int format."""
        response = {
            "hits": {
                "total": 50
            }
        }
        
        total = service.calculate_total_hits(response)
        
        assert total == 50
    
    def test_calculate_total_hits_missing(self, service):
        """Test total hits calculation when missing."""
        response = {}
        
        total = service.calculate_total_hits(response)
        
        assert total == 0