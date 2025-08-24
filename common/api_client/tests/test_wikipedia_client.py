"""Tests for WikipediaAPIClient."""

import logging
from unittest.mock import Mock

import pytest

from property_finder_models import EnrichedWikipediaArticle, WikipediaSummary, LocationInfo

from ..config import APIClientConfig
from ..exceptions import NotFoundError, APIError
from ..wikipedia_client import WikipediaAPIClient


class TestWikipediaAPIClient:
    """Tests for WikipediaAPIClient."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return APIClientConfig(
            base_url="http://test-wikipedia-api.example.com",
            timeout=30
        )
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger("test")
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock()
    
    @pytest.fixture
    def client(self, config, logger, mock_http_client):
        """Create test Wikipedia API client."""
        return WikipediaAPIClient(config, logger)
    
    @pytest.fixture
    def sample_article(self):
        """Create sample Wikipedia article data."""
        return {
            "page_id": 12345,
            "article_id": 1,
            "title": "Test Article",
            "url": "https://en.wikipedia.org/wiki/Test_Article",
            "full_text": "This is a test Wikipedia article.",
            "relevance_score": 0.85,
            "location": {
                "city": "Test City",
                "state": "California",
                "country": "United States"
            }
        }
    
    @pytest.fixture
    def sample_summary(self):
        """Create sample Wikipedia summary data."""
        return {
            "page_id": 12345,
            "article_title": "Test Article",
            "short_summary": "Short summary of the test article",
            "long_summary": "Long summary of the test article with more details",
            "key_topics": ["topic1", "topic2"],
            "best_city": "Test City",
            "best_state": "California",
            "overall_confidence": 0.9
        }
    
    def test_initialization(self, config, logger, mock_http_client):
        """Test client initialization."""
        client = WikipediaAPIClient(config, logger)
        
        assert client.config == config
        assert client.logger == logger
    
    def test_get_articles_success(self, client, sample_article):
        """Test successful articles retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_article],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_articles()
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], EnrichedWikipediaArticle)
        assert result[0].title == "Test Article"
        
        # Verify API call
        client.get.assert_called_once_with(
            "/articles", 
            params={"page": 1, "page_size": 50, "sort_by": "relevance"}
        )
    
    def test_get_articles_with_filters(self, client, sample_article):
        """Test articles retrieval with filters."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_article],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 25,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method with filters
        result = client.get_articles(
            city="Test City",
            state="California",
            relevance_min=0.7,
            sort_by="title",
            include_embeddings=True,
            collection_name="test_collection",
            page=1,
            page_size=25
        )
        
        # Verify result
        assert len(result) == 1
        
        # Verify API call with filters
        client.get.assert_called_once_with(
            "/articles", 
            params={
                "page": 1, 
                "page_size": 25,
                "sort_by": "title",
                "city": "Test City",
                "state": "California",
                "relevance_min": 0.7,
                "include_embeddings": True,
                "collection_name": "test_collection"
            }
        )
    
    def test_get_article_by_id_success(self, client, sample_article):
        """Test successful single article retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": sample_article,
            "metadata": {}
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_article_by_id(12345)
        
        # Verify result
        assert isinstance(result, EnrichedWikipediaArticle)
        assert result.title == "Test Article"
        
        # Verify API call
        client.get.assert_called_once_with("/articles/12345", params=None)
    
    def test_get_article_by_id_not_found(self, client):
        """Test article retrieval when article not found."""
        # Mock the underlying get method to raise NotFoundError
        client.get = Mock(side_effect=NotFoundError("Article not found"))
        
        # Call method and expect exception
        with pytest.raises(NotFoundError):
            client.get_article_by_id(99999)
    
    def test_get_summaries_success(self, client, sample_summary):
        """Test successful summaries retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_summary],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_summaries()
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], WikipediaSummary)
        assert result[0].article_title == "Test Article"
        
        # Verify API call
        client.get.assert_called_once_with(
            "/summaries", 
            params={"page": 1, "page_size": 50, "include_key_topics": True}
        )
    
    def test_get_summaries_with_filters(self, client, sample_summary):
        """Test summaries retrieval with filters."""
        # Mock HTTP response
        mock_response = {
            "data": [sample_summary],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 25,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method with filters
        result = client.get_summaries(
            city="Test City",
            state="California",
            confidence_min=0.8,
            include_key_topics=False,
            page=1,
            page_size=25
        )
        
        # Verify result
        assert len(result) == 1
        
        # Verify API call with filters
        client.get.assert_called_once_with(
            "/summaries", 
            params={
                "page": 1, 
                "page_size": 25,
                "include_key_topics": False,
                "city": "Test City",
                "state": "California",
                "confidence_min": 0.8
            }
        )
    
    def test_get_summary_by_id_success(self, client, sample_summary):
        """Test successful single summary retrieval."""
        # Mock HTTP response
        mock_response = {
            "data": sample_summary,
            "metadata": {}
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        result = client.get_summary_by_id(12345)
        
        # Verify result
        assert isinstance(result, WikipediaSummary)
        assert result.article_title == "Test Article"
        
        # Verify API call
        client.get.assert_called_once_with(
            "/summaries/12345", 
            params={"include_key_topics": True}
        )
    
    def test_get_all_articles_single_page(self, client, sample_article):
        """Test get_all_articles with single page."""
        # Mock HTTP response - less than page_size indicates last page
        mock_response = {
            "data": [sample_article],
            "metadata": {
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            },
            "links": None
        }
        
        # Mock the underlying get method
        client.get = Mock(return_value=mock_response)
        
        # Call method
        pages = list(client.get_all_articles(page_size=50))
        
        # Verify result
        assert len(pages) == 1
        assert len(pages[0]) == 1
        assert pages[0][0].title == "Test Article"
    
    def test_get_all_summaries_multiple_pages(self, client, sample_summary):
        """Test get_all_summaries with multiple pages."""
        # Create multiple summary responses
        summary2 = sample_summary.copy()
        summary2["page_id"] = 67890
        summary2["article_title"] = "Test Article 2"
        
        # Page 1 - full page (should continue)
        page1_response = {
            "data": [sample_summary, sample_summary],  # Full page of 2 items
            "metadata": {
                "total_count": 3,
                "page": 1,
                "page_size": 2,
                "total_pages": 2,
                "has_next": True,
                "has_previous": False
            }
        }
        
        # Page 2 - partial page (should stop after this)
        page2_response = {
            "data": [summary2],  # Only 1 item (less than page_size of 2)
            "metadata": {
                "total_count": 3,
                "page": 2,
                "page_size": 2,
                "total_pages": 2,
                "has_next": False,
                "has_previous": True
            }
        }
        
        # Mock the underlying get method to return different responses
        client.get = Mock(side_effect=[page1_response, page2_response])
        
        # Call method
        pages = list(client.get_all_summaries(page_size=2))
        
        # Verify result
        assert len(pages) == 2
        assert len(pages[0]) == 2  # Full page
        assert len(pages[1]) == 1  # Partial page (should stop here)
        assert pages[0][0].article_title == "Test Article"
        assert pages[1][0].article_title == "Test Article 2"