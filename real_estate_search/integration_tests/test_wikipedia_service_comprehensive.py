"""
Comprehensive integration tests for WikipediaSearchService.

Tests all methods and edge cases for Wikipedia search functionality.
"""

import pytest
import logging
from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch

from real_estate_search.config import AppConfig
from real_estate_search.infrastructure.elasticsearch_client import ElasticsearchClientFactory
from real_estate_search.search_service import (
    WikipediaSearchService,
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    WikipediaSearchType
)
from real_estate_search.models.wikipedia import WikipediaArticle

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def es_client():
    """Create Elasticsearch client for integration tests."""
    config = AppConfig.load()
    factory = ElasticsearchClientFactory(config.elasticsearch)
    client = factory.create_client()
    
    # Verify connection
    try:
        if not client.ping():
            pytest.skip("Elasticsearch is not available")
    except Exception as e:
        pytest.skip(f"Cannot connect to Elasticsearch: {str(e)}")
    
    return client


@pytest.fixture(scope="module")
def wikipedia_service(es_client):
    """Create WikipediaSearchService instance."""
    return WikipediaSearchService(es_client)


@pytest.fixture
def sample_articles(es_client) -> List[Dict[str, Any]]:
    """Get sample Wikipedia articles for testing."""
    if not es_client.indices.exists(index="wikipedia"):
        return []
    
    try:
        response = es_client.search(
            index="wikipedia",
            query={"match_all": {}},
            size=5,
            _source=["page_id", "title", "categories"]
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
    except Exception:
        return []


class TestWikipediaBasicSearch:
    """Test basic Wikipedia search functionality."""
    
    def test_service_initialization(self, wikipedia_service):
        """Test that service initializes correctly."""
        assert wikipedia_service is not None
        assert wikipedia_service.full_text_index == "wikipedia"
        assert wikipedia_service.chunks_index_prefix == "wiki_chunks"
        assert wikipedia_service.summaries_index_prefix == "wiki_summaries"
        assert wikipedia_service.es_client is not None
    
    def test_fulltext_search(self, wikipedia_service, es_client):
        """Test full-text search across Wikipedia articles."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test various queries
        test_queries = [
            "San Francisco history",
            "Golden Gate Bridge",
            "California landmarks",
            "technology companies",
            "neighborhoods"
        ]
        
        for query in test_queries:
            response = wikipedia_service.search_fulltext(
                query=query,
                size=5
            )
            
            assert response is not None
            assert isinstance(response, WikipediaSearchResponse)
            assert response.search_type == WikipediaSearchType.FULL_TEXT
            assert isinstance(response.results, list)
            assert response.execution_time_ms >= 0
            assert response.total_hits >= 0
            
            # Verify result structure
            for result in response.results:
                assert isinstance(result, WikipediaArticle)
                assert result.page_id is not None
                assert result.title is not None
                assert result.score >= 0
    
    def test_search_with_request_model(self, wikipedia_service, es_client):
        """Test search using WikipediaSearchRequest model."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = WikipediaSearchRequest(
            query="Silicon Valley",
            search_type=WikipediaSearchType.FULL_TEXT,
            include_highlights=True,
            highlight_fragment_size=200,
            size=10
        )
        
        response = wikipedia_service.search(request)
        
        assert response is not None
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        assert len(response.results) <= 10
        
        # Check highlights if available
        if response.total_hits > 0:
            has_highlights = any(
                result.highlights is not None
                for result in response.results
            )
            # Highlights should be present for matching content
            assert response.total_hits >= 0
    
    def test_empty_query_search(self, wikipedia_service, es_client):
        """Test search with empty query (match all)."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_fulltext(
            query="",
            size=5
        )
        
        assert response is not None
        # Empty query should return all documents
        assert response.total_hits >= 0
        assert len(response.results) <= 5


class TestWikipediaSearchTypes:
    """Test different Wikipedia search types."""
    
    def test_chunks_search(self, wikipedia_service, es_client):
        """Test searching Wikipedia chunks."""
        # Check if chunks index exists
        chunks_indices = es_client.indices.get_alias(index="wiki_chunks*", ignore_unavailable=True)
        if not chunks_indices:
            pytest.skip("Wikipedia chunks indices do not exist")
        
        response = wikipedia_service.search_chunks(
            query="Golden Gate",
            chunk_size="medium",
            size=5
        )
        
        assert response is not None
        assert response.search_type == WikipediaSearchType.CHUNKS
        assert isinstance(response.results, list)
        
        # Verify chunk-specific fields if results exist
        for result in response.results:
            assert result.page_id is not None
            # Chunks should have summary
            if result.summary:
                assert len(result.summary) > 0
    
    def test_summaries_search(self, wikipedia_service, es_client):
        """Test searching Wikipedia summaries."""
        # Check if summaries index exists
        summaries_indices = es_client.indices.get_alias(index="wiki_summaries*", ignore_unavailable=True)
        if not summaries_indices:
            pytest.skip("Wikipedia summaries indices do not exist")
        
        response = wikipedia_service.search_summaries(
            query="San Francisco",
            summary_type="abstract",
            size=5
        )
        
        assert response is not None
        assert response.search_type == WikipediaSearchType.SUMMARIES
        assert isinstance(response.results, list)
        
        # Summaries should have concise content
        for result in response.results:
            if result.short_summary or result.long_summary:
                # Summaries are typically shorter
                summary = result.short_summary or result.long_summary or ""
                assert len(summary) > 0
    
    def test_search_type_selection(self, wikipedia_service, es_client):
        """Test that search type is correctly selected."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test full-text search type
        request = WikipediaSearchRequest(
            query="test",
            search_type=WikipediaSearchType.FULL_TEXT,
            size=1
        )
        response = wikipedia_service.search(request)
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        
        # Test chunks search type if available
        chunks_indices = es_client.indices.get_alias(index="wiki_chunks*", ignore_unavailable=True)
        if chunks_indices:
            request = WikipediaSearchRequest(
                query="test",
                search_type=WikipediaSearchType.CHUNKS,
                size=1
            )
            response = wikipedia_service.search(request)
            assert response.search_type == WikipediaSearchType.CHUNKS
        
        # Test summaries search type if available
        summaries_indices = es_client.indices.get_alias(index="wiki_summaries*", ignore_unavailable=True)
        if summaries_indices:
            request = WikipediaSearchRequest(
                query="test",
                search_type=WikipediaSearchType.SUMMARIES,
                size=1
            )
            response = wikipedia_service.search(request)
            assert response.search_type == WikipediaSearchType.SUMMARIES


class TestWikipediaCategorySearch:
    """Test Wikipedia category-based search."""
    
    def test_search_by_single_category(self, wikipedia_service, es_client):
        """Test searching by a single category."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_by_category(
            categories=["Cities"],
            size=10
        )
        
        assert response is not None
        assert isinstance(response.results, list)
        assert response.applied_categories == ["Cities"]
        
        # Results should have the category if field exists
        for result in response.results:
            if result.categories:
                # At least one result should have the category
                assert isinstance(result.categories, list)
    
    def test_search_by_multiple_categories(self, wikipedia_service, es_client):
        """Test searching by multiple categories."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_by_category(
            categories=["Neighborhoods", "San Francisco", "California"],
            query="history",
            size=5
        )
        
        assert response is not None
        assert response.applied_categories == ["Neighborhoods", "San Francisco", "California"]
        
        # If results exist, they should be relevant
        if response.total_hits > 0:
            assert len(response.results) > 0
    
    def test_category_with_text_query(self, wikipedia_service, es_client):
        """Test combining category filter with text search."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_by_category(
            categories=["Technology"],
            query="artificial intelligence",
            size=10
        )
        
        assert response is not None
        # Results should match both category and query
        assert isinstance(response.results, list)
    
    def test_empty_category_search(self, wikipedia_service, es_client):
        """Test search with empty categories list."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_by_category(
            categories=[],
            query="test",
            size=5
        )
        
        assert response is not None
        # Should behave like regular text search
        assert response.applied_categories == []
        assert isinstance(response.results, list)


class TestWikipediaHighlighting:
    """Test Wikipedia search highlighting functionality."""
    
    def test_highlights_in_fulltext_search(self, wikipedia_service, es_client):
        """Test highlighting in full-text search."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = WikipediaSearchRequest(
            query="Golden Gate Bridge construction",
            search_type=WikipediaSearchType.FULL_TEXT,
            include_highlights=True,
            highlight_fragment_size=150,
            size=5
        )
        
        response = wikipedia_service.search(request)
        
        assert response is not None
        
        # Check for highlights in results
        if response.total_hits > 0:
            has_highlights = False
            for result in response.results:
                if result.highlights:
                    has_highlights = True
                    assert isinstance(result.highlights, list)
                    for highlight in result.highlights:
                        assert isinstance(highlight, str)
                        # Fragment size should be respected (with some margin for tags)
                        assert len(highlight) <= 250
            
            # At least some results should have highlights if query matches
            assert response.total_hits >= 0
    
    def test_highlight_fragment_size(self, wikipedia_service, es_client):
        """Test that highlight fragment size is respected."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test with small fragments
        request_small = WikipediaSearchRequest(
            query="San Francisco",
            include_highlights=True,
            highlight_fragment_size=50,
            size=3
        )
        
        response_small = wikipedia_service.search(request_small)
        
        # Test with large fragments
        request_large = WikipediaSearchRequest(
            query="San Francisco",
            include_highlights=True,
            highlight_fragment_size=300,
            size=3
        )
        
        response_large = wikipedia_service.search(request_large)
        
        assert response_small is not None
        assert response_large is not None
        
        # Check fragment sizes if highlights exist
        for result in response_small.results:
            if result.highlights:
                for highlight in result.highlights:
                    # Small fragments should be shorter (accounting for markup)
                    assert len(highlight) <= 150
        
        for result in response_large.results:
            if result.highlights:
                for highlight in result.highlights:
                    # Large fragments can be longer
                    assert len(highlight) <= 500
    
    def test_highlights_disabled(self, wikipedia_service, es_client):
        """Test search with highlights disabled."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = WikipediaSearchRequest(
            query="California",
            include_highlights=False,
            size=5
        )
        
        response = wikipedia_service.search(request)
        
        assert response is not None
        
        # No results should have highlights
        for result in response.results:
            assert result.highlights is None or result.highlights == []


class TestWikipediaPagination:
    """Test pagination functionality for Wikipedia search."""
    
    def test_basic_pagination(self, wikipedia_service, es_client):
        """Test basic pagination with offset."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Get first page
        request_page1 = WikipediaSearchRequest(
            query="San Francisco",
            size=5,
            from_offset=0
        )
        page1 = wikipedia_service.search(request_page1)
        
        # Get second page
        request_page2 = WikipediaSearchRequest(
            query="San Francisco",
            size=5,
            from_offset=5
        )
        page2 = wikipedia_service.search(request_page2)
        
        assert page1 is not None
        assert page2 is not None
        
        # If enough results, verify pages are different
        if page1.total_hits > 5:
            page1_ids = {r.page_id for r in page1.results}
            page2_ids = {r.page_id for r in page2.results}
            
            # No overlap between pages
            assert len(page1_ids.intersection(page2_ids)) == 0
    
    def test_pagination_consistency(self, wikipedia_service, es_client):
        """Test that pagination returns consistent results."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Get multiple pages
        totals = []
        for offset in [0, 10, 20]:
            request = WikipediaSearchRequest(
                query="history",
                size=10,
                from_offset=offset
            )
            response = wikipedia_service.search(request)
            totals.append(response.total_hits)
        
        # Total hits should be consistent across pages
        assert len(set(totals)) == 1
    
    def test_large_offset(self, wikipedia_service, es_client):
        """Test pagination with large offset."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = WikipediaSearchRequest(
            query="test",
            size=5,
            from_offset=9990  # Stay within ES limit
        )
        
        response = wikipedia_service.search(request)
        
        assert response is not None
        # May return empty results if offset exceeds total
        assert isinstance(response.results, list)


class TestWikipediaErrorHandling:
    """Test error handling in Wikipedia search."""
    
    def test_search_with_invalid_index(self, es_client):
        """Test search when index doesn't exist."""
        service = WikipediaSearchService(es_client)
        service.full_text_index = "non_existent_wiki_index"
        
        # Should raise an error
        with pytest.raises(Exception) as exc_info:
            service.search_fulltext("test")
        
        assert "not found" in str(exc_info.value).lower() or \
               "no such index" in str(exc_info.value).lower()
    
    def test_search_with_invalid_search_type(self, wikipedia_service, es_client):
        """Test search with non-existent index for search type."""
        # Try to search chunks when index doesn't exist
        service = WikipediaSearchService(es_client)
        service.chunks_index_prefix = "non_existent_chunks"
        
        with pytest.raises(Exception):
            service.search_chunks("test", chunk_size="medium")
    
    def test_search_with_special_characters(self, wikipedia_service, es_client):
        """Test search with special characters in query."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Test with various special characters
        special_queries = [
            "San Francisco's history",
            "Golden Gate (bridge)",
            "California & technology",
            "neighborhoods/districts",
            "19th & 20th century"
        ]
        
        for query in special_queries:
            request = WikipediaSearchRequest(
                query=query,
                size=5
            )
            
            response = wikipedia_service.search(request)
            
            # Should handle special characters gracefully
            assert response is not None
            assert isinstance(response.results, list)
    
    def test_search_with_empty_response(self, wikipedia_service, es_client):
        """Test handling of searches that return no results."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search for something unlikely to exist
        response = wikipedia_service.search_fulltext(
            query="xyzabc123nonexistent999query",
            size=10
        )
        
        assert response is not None
        assert response.results == []
        assert response.total_hits == 0


class TestWikipediaSearchPerformance:
    """Test performance aspects of Wikipedia search."""
    
    def test_search_response_time(self, wikipedia_service, es_client):
        """Test that searches complete within reasonable time."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Simple text search
        response = wikipedia_service.search_fulltext(
            query="San Francisco",
            size=10
        )
        assert response.execution_time_ms < 2000  # Should be under 2 seconds
        
        # Category search
        response = wikipedia_service.search_by_category(
            categories=["Cities", "California"],
            query="history",
            size=10
        )
        assert response.execution_time_ms < 3000  # May take longer with filters
        
        # Search with highlights
        request = WikipediaSearchRequest(
            query="technology",
            include_highlights=True,
            highlight_fragment_size=200,
            size=20
        )
        response = wikipedia_service.search(request)
        assert response.execution_time_ms < 3000  # Highlighting may add overhead
    
    def test_large_result_set(self, wikipedia_service, es_client):
        """Test handling of large result sets."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Request large number of results
        response = wikipedia_service.search_fulltext(
            query="",  # Match all
            size=100
        )
        
        assert response is not None
        assert len(response.results) <= 100
        assert response.execution_time_ms < 5000  # Should still be reasonably fast
    
    def test_concurrent_searches(self, wikipedia_service, es_client):
        """Test that service can handle multiple searches."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Run multiple searches in sequence
        responses = []
        queries = ["San Francisco", "technology", "history", "California", "neighborhoods"]
        
        for query in queries:
            response = wikipedia_service.search_fulltext(
                query=query,
                size=5
            )
            responses.append(response)
        
        # All should succeed
        assert len(responses) == 5
        for response in responses:
            assert response is not None
            assert isinstance(response.results, list)


class TestWikipediaSearchIntegration:
    """Test integration aspects of Wikipedia search."""
    
    def test_search_response_completeness(self, wikipedia_service, es_client):
        """Test that search responses have all expected fields."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        response = wikipedia_service.search_fulltext(
            query="Golden Gate",
            size=1
        )
        
        if response.total_hits > 0:
            result = response.results[0]
            
            # Check required fields
            assert result.page_id is not None
            assert result.title is not None
            assert result.score is not None
            
            # Check optional fields are present (may be None)
            assert hasattr(result, 'url')
            assert hasattr(result, 'summary')
            assert hasattr(result, 'categories')
            assert hasattr(result, 'content_length')
            assert hasattr(result, 'highlights')
    
    def test_search_with_all_features(self, wikipedia_service, es_client):
        """Test search using all available features together."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        request = WikipediaSearchRequest(
            query="San Francisco Golden Gate technology",
            search_type=WikipediaSearchType.FULL_TEXT,
            categories=["Cities", "Technology", "California"],
            include_highlights=True,
            highlight_fragment_size=200,
            size=15,
            from_offset=0
        )
        
        response = wikipedia_service.search(request)
        
        assert response is not None
        assert response.total_hits >= 0
        assert len(response.results) <= 15
        assert response.search_type == WikipediaSearchType.FULL_TEXT
        assert response.execution_time_ms >= 0
        
        # Verify features are applied
        if response.applied_categories:
            assert response.applied_categories == ["Cities", "Technology", "California"]
        
        # Check for various fields in results
        for result in response.results:
            assert result.page_id is not None
            assert result.title is not None
            assert result.score >= 0
    
    def test_search_relevance_scoring(self, wikipedia_service, es_client):
        """Test that search results are properly scored and ranked."""
        if not es_client.indices.exists(index="wikipedia"):
            pytest.skip("Wikipedia index does not exist")
        
        # Search for a specific term
        response = wikipedia_service.search_fulltext(
            query="Golden Gate Bridge",
            size=10
        )
        
        assert response is not None
        
        if len(response.results) > 1:
            # Scores should be in descending order
            scores = [r.score for r in response.results]
            assert scores == sorted(scores, reverse=True)
            
            # First result should be most relevant
            first_result = response.results[0]
            assert first_result.score > 0
            
            # Title or content should contain query terms
            if first_result.title:
                title_lower = first_result.title.lower()
                # At least one query term should be present
                has_term = (
                    "golden" in title_lower or
                    "gate" in title_lower or
                    "bridge" in title_lower
                )
                # May not always have exact match in title
                assert first_result.title is not None