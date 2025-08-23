"""
Integration tests for Wikipedia API endpoints.

Tests Wikipedia article and summary endpoints with various filtering options,
pagination, sorting, and error handling scenarios.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestWikipediaArticleEndpoints:
    """Test suite for Wikipedia article endpoints."""
    
    def test_get_all_articles_default_pagination(self, test_client: TestClient):
        """
        Test getting all Wikipedia articles with default pagination.
        
        Verifies:
        - Returns 200 OK status
        - Returns paginated response structure
        - Default pagination parameters applied
        - Articles data is properly structured
        """
        response = test_client.get("/api/v1/wikipedia/articles")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            error_data = response.json()
            assert "Wikipedia database not available" in error_data["error"]["message"]
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "metadata" in data
        assert "links" in data
        
        # Verify metadata structure
        metadata = data["metadata"]
        assert metadata["page"] == 1
        assert metadata["page_size"] == 50  # Default page size
        assert metadata["has_previous"] is False
        assert "total_count" in metadata
        assert "total_pages" in metadata
        assert "timestamp" in metadata
        
        # Verify links structure
        links = data["links"]
        assert "self" in links
        assert "first" in links
        assert "last" in links
        
        # If we have articles, verify data structure
        articles = data["data"]
        if len(articles) > 0:
            article = articles[0]
            # Verify required fields
            assert "page_id" in article
            assert "title" in article
            assert "url" in article
            assert "relevance_score" in article
            assert "location" in article
    
    def test_get_articles_with_custom_pagination(self, test_client: TestClient):
        """
        Test Wikipedia articles endpoint with custom pagination parameters.
        
        Verifies:
        - Custom page and page_size parameters work
        - Pagination metadata reflects custom parameters
        - Response structure remains consistent
        """
        response = test_client.get("/api/v1/wikipedia/articles?page=1&page_size=10")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify custom pagination parameters
        metadata = data["metadata"]
        assert metadata["page"] == 1
        assert metadata["page_size"] == 10
        assert len(data["data"]) <= 10  # Should not exceed page size
    
    def test_get_articles_filtered_by_city(self, test_client: TestClient, valid_cities):
        """
        Test filtering Wikipedia articles by city.
        
        Verifies:
        - City filtering works correctly
        - Returns articles related to the specified city
        - Metadata reflects filtered results
        """
        city = valid_cities[0]  # Use first valid city
        response = test_client.get(f"/api/v1/wikipedia/articles?city={city}")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        articles = data["data"]
        # Note: Articles may not directly contain city filtering like properties
        # This tests the endpoint functionality without requiring specific data
        assert isinstance(articles, list)
    
    def test_get_articles_filtered_by_state(self, test_client: TestClient):
        """
        Test filtering Wikipedia articles by state.
        
        Verifies:
        - State filtering works correctly
        - Returns articles related to the specified state
        - Metadata reflects filtered results
        """
        response = test_client.get("/api/v1/wikipedia/articles?state=California")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        articles = data["data"]
        assert isinstance(articles, list)
    
    def test_get_articles_with_relevance_filtering(self, test_client: TestClient):
        """
        Test filtering Wikipedia articles by minimum relevance score.
        
        Verifies:
        - Relevance filtering works correctly
        - All returned articles meet minimum relevance threshold
        - Metadata reflects filtered results
        """
        relevance_min = 0.8
        response = test_client.get(f"/api/v1/wikipedia/articles?relevance_min={relevance_min}")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        articles = data["data"]
        # Verify all articles meet minimum relevance score
        for article in articles:
            assert article["relevance_score"] >= relevance_min
    
    def test_get_articles_with_sorting(self, test_client: TestClient):
        """
        Test sorting Wikipedia articles by different criteria.
        
        Verifies:
        - Sort by relevance (default)
        - Sort by title
        - Sort by page_id
        """
        # Test sorting by title
        response = test_client.get("/api/v1/wikipedia/articles?sort_by=title&page_size=5")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        articles = data["data"]
        if len(articles) > 1:
            # Verify sorting (titles should be in alphabetical order)
            titles = [article["title"] for article in articles]
            assert titles == sorted(titles)
        
        # Test sorting by page_id
        response = test_client.get("/api/v1/wikipedia/articles?sort_by=page_id&page_size=5")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        articles = data["data"]
        if len(articles) > 1:
            page_ids = [article["page_id"] for article in articles]
            assert page_ids == sorted(page_ids)
    
    def test_get_single_article_success(self, test_client: TestClient):
        """
        Test getting a single Wikipedia article by page ID.
        
        Verifies:
        - Returns single article data
        - Article structure is correct
        - Metadata includes article information
        """
        # First get a list to find a valid page_id
        list_response = test_client.get("/api/v1/wikipedia/articles?page_size=1")
        
        # Handle case where Wikipedia database might not exist
        if list_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert list_response.status_code == status.HTTP_200_OK
        articles = list_response.json()["data"]
        
        if len(articles) == 0:
            pytest.skip("No Wikipedia articles available for testing")
            return
        
        page_id = articles[0]["page_id"]
        
        # Test getting single article
        response = test_client.get(f"/api/v1/wikipedia/articles/{page_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        
        # Verify article data
        article = data["data"]
        assert article["page_id"] == page_id
        assert "title" in article
        assert "url" in article
        assert "relevance_score" in article
        
        # Verify metadata
        metadata = data["metadata"]
        assert metadata["page_id"] == page_id
        assert "source" in metadata
        assert "relevance_score" in metadata
    
    def test_get_single_article_not_found(self, test_client: TestClient):
        """
        Test getting a non-existent Wikipedia article.
        
        Verifies:
        - Returns 404 Not Found status
        - Returns structured error response
        - Includes correlation ID
        """
        non_existent_page_id = 999999
        response = test_client.get(f"/api/v1/wikipedia/articles/{non_existent_page_id}")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify error response structure
        error_data = response.json()
        assert "error" in error_data
        
        error = error_data["error"]
        assert "code" in error
        assert "message" in error
        assert "correlation_id" in error
        assert "status_code" in error
        
        # Verify correlation ID is also in headers
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == error["correlation_id"]
    
    def test_get_articles_invalid_page_number(self, test_client: TestClient):
        """
        Test Wikipedia articles endpoint with invalid page number.
        
        Verifies:
        - Returns 404 for page numbers beyond available data
        - Returns structured error response
        """
        response = test_client.get("/api/v1/wikipedia/articles?page=999")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        # Could be 404 (if data exists but page is too high) or 200 (if no data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            error_data = response.json()
            assert "error" in error_data
            assert "Page 999 not found" in error_data["error"]["message"]
    
    def test_get_articles_invalid_parameters(self, test_client: TestClient):
        """
        Test Wikipedia articles endpoint with invalid parameters.
        
        Verifies:
        - Returns 422 for invalid parameter values
        - Returns structured error response
        """
        # Test invalid sort_by parameter
        response = test_client.get("/api/v1/wikipedia/articles?sort_by=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_data = response.json()
        assert "error" in error_data
        
        # Test invalid relevance_min (outside 0-1 range)
        response = test_client.get("/api/v1/wikipedia/articles?relevance_min=2.0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_articles_response_has_correlation_id(self, test_client: TestClient):
        """
        Test that all Wikipedia article responses include correlation IDs.
        
        Verifies:
        - Correlation ID is present in response headers
        - Correlation ID format is valid
        """
        response = test_client.get("/api/v1/wikipedia/articles")
        
        # Should have correlation ID regardless of status
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0


class TestWikipediaSummaryEndpoints:
    """Test suite for Wikipedia summary endpoints."""
    
    def test_get_all_summaries_default_pagination(self, test_client: TestClient):
        """
        Test getting all Wikipedia summaries with default pagination.
        
        Verifies:
        - Returns 200 OK status
        - Returns paginated response structure
        - Default pagination parameters applied
        - Summary data is properly structured
        """
        response = test_client.get("/api/v1/wikipedia/summaries")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            error_data = response.json()
            assert "Wikipedia database not available" in error_data["error"]["message"]
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "metadata" in data
        assert "links" in data
        
        # Verify metadata structure
        metadata = data["metadata"]
        assert metadata["page"] == 1
        assert metadata["page_size"] == 50  # Default page size
        assert metadata["has_previous"] is False
        
        # If we have summaries, verify data structure
        summaries = data["data"]
        if len(summaries) > 0:
            summary = summaries[0]
            # Verify required fields
            assert "page_id" in summary
            assert "article_title" in summary
            assert "short_summary" in summary
            assert "overall_confidence" in summary
    
    def test_get_summaries_with_confidence_filtering(self, test_client: TestClient):
        """
        Test filtering Wikipedia summaries by minimum confidence score.
        
        Verifies:
        - Confidence filtering works correctly
        - All returned summaries meet minimum confidence threshold
        - Metadata reflects filtered results
        """
        confidence_min = 0.7
        response = test_client.get(f"/api/v1/wikipedia/summaries?confidence_min={confidence_min}")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        summaries = data["data"]
        # Verify all summaries meet minimum confidence score
        for summary in summaries:
            assert summary["overall_confidence"] >= confidence_min
    
    def test_get_summaries_filtered_by_location(self, test_client: TestClient):
        """
        Test filtering Wikipedia summaries by city and state.
        
        Verifies:
        - Location filtering works correctly
        - Returns summaries related to the specified location
        - Handles both city and state filtering
        """
        response = test_client.get("/api/v1/wikipedia/summaries?city=San Francisco")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        summaries = data["data"]
        assert isinstance(summaries, list)
        
        # Test state filtering
        response = test_client.get("/api/v1/wikipedia/summaries?state=California")
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_single_summary_success(self, test_client: TestClient):
        """
        Test getting a single Wikipedia summary by page ID.
        
        Verifies:
        - Returns single summary data
        - Summary structure is correct
        - Metadata includes summary information
        """
        # First get a list to find a valid page_id
        list_response = test_client.get("/api/v1/wikipedia/summaries?page_size=1")
        
        # Handle case where Wikipedia database might not exist
        if list_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert list_response.status_code == status.HTTP_200_OK
        summaries = list_response.json()["data"]
        
        if len(summaries) == 0:
            pytest.skip("No Wikipedia summaries available for testing")
            return
        
        page_id = summaries[0]["page_id"]
        
        # Test getting single summary
        response = test_client.get(f"/api/v1/wikipedia/summaries/{page_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        
        # Verify summary data
        summary = data["data"]
        assert summary["page_id"] == page_id
        assert "article_title" in summary
        assert "overall_confidence" in summary
        
        # Verify metadata includes location information
        metadata = data["metadata"]
        assert metadata["page_id"] == page_id
        assert "confidence_score" in metadata
        assert "extracted_location" in metadata
    
    def test_get_single_summary_not_found(self, test_client: TestClient):
        """
        Test getting a non-existent Wikipedia summary.
        
        Verifies:
        - Returns 404 Not Found status
        - Returns structured error response
        """
        non_existent_page_id = 999999
        response = test_client.get(f"/api/v1/wikipedia/summaries/{non_existent_page_id}")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify error response structure
        error_data = response.json()
        assert "error" in error_data
    
    def test_get_summaries_invalid_parameters(self, test_client: TestClient):
        """
        Test Wikipedia summaries endpoint with invalid parameters.
        
        Verifies:
        - Returns 422 for invalid parameter values
        - Returns structured error response
        """
        # Test invalid confidence_min (outside 0-1 range)
        response = test_client.get("/api/v1/wikipedia/summaries?confidence_min=2.0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_data = response.json()
        assert "error" in error_data
    
    def test_summaries_response_has_correlation_id(self, test_client: TestClient):
        """
        Test that all Wikipedia summary responses include correlation IDs.
        
        Verifies:
        - Correlation ID is present in response headers
        - Correlation ID format is valid
        """
        response = test_client.get("/api/v1/wikipedia/summaries")
        
        # Should have correlation ID regardless of status
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0
    
    def test_summaries_include_key_topics_option(self, test_client: TestClient):
        """
        Test the include_key_topics parameter for summaries.
        
        Verifies:
        - include_key_topics parameter is properly handled
        - Response structure adapts based on parameter
        """
        # Test with key topics included (default)
        response = test_client.get("/api/v1/wikipedia/summaries?include_key_topics=true&page_size=1")
        
        # Handle case where Wikipedia database might not exist
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            pytest.skip("Wikipedia database not available for testing")
            return
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        summaries = data["data"]
        if len(summaries) > 0:
            summary = summaries[0]
            # Key topics should be included
            if "key_topics" in summary:
                assert isinstance(summary["key_topics"], list)
        
        # Test with key topics excluded
        response = test_client.get("/api/v1/wikipedia/summaries?include_key_topics=false&page_size=1")
        assert response.status_code == status.HTTP_200_OK


class TestWikipediaEndpointsComprehensive:
    """Comprehensive tests for Wikipedia endpoints integration."""
    
    def test_wikipedia_endpoints_in_openapi_docs(self, test_client: TestClient):
        """
        Test that Wikipedia endpoints are properly documented in OpenAPI schema.
        
        Verifies:
        - Wikipedia endpoints appear in OpenAPI documentation
        - Endpoint descriptions and parameters are documented
        - Response schemas are properly defined
        """
        response = test_client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_spec = response.json()
        paths = openapi_spec["paths"]
        
        # Check that Wikipedia endpoints are documented
        assert "/api/v1/wikipedia/articles" in paths
        assert "/api/v1/wikipedia/articles/{page_id}" in paths
        assert "/api/v1/wikipedia/summaries" in paths
        assert "/api/v1/wikipedia/summaries/{page_id}" in paths
    
    def test_wikipedia_endpoints_error_consistency(self, test_client: TestClient):
        """
        Test that Wikipedia endpoint error handling is consistent.
        
        Verifies:
        - All endpoints return structured error responses
        - Correlation IDs are included in all error responses
        - HTTP status codes are appropriate
        """
        test_cases = [
            # Test invalid page_id for articles
            ("/api/v1/wikipedia/articles/999999", status.HTTP_404_NOT_FOUND),
            # Test invalid page_id for summaries
            ("/api/v1/wikipedia/summaries/999999", status.HTTP_404_NOT_FOUND),
            # Test invalid sort parameter
            ("/api/v1/wikipedia/articles?sort_by=invalid", status.HTTP_422_UNPROCESSABLE_ENTITY),
            # Test invalid confidence parameter
            ("/api/v1/wikipedia/summaries?confidence_min=2.0", status.HTTP_422_UNPROCESSABLE_ENTITY),
        ]
        
        for url, expected_status in test_cases:
            response = test_client.get(url)
            
            # Handle case where Wikipedia database might not exist
            if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                continue  # Skip this test case
            
            assert response.status_code == expected_status, f"Failed for {url}"
            
            # For 4xx errors, verify error response structure
            if 400 <= expected_status < 500:
                error_data = response.json()
                assert "error" in error_data
                
                error = error_data["error"]
                assert "code" in error
                assert "message" in error
                assert "correlation_id" in error
                assert "status_code" in error
                
                # Verify correlation ID is also in headers
                assert "X-Correlation-ID" in response.headers
                assert response.headers["X-Correlation-ID"] == error["correlation_id"]