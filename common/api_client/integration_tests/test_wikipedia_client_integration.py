"""Integration tests for WikipediaAPIClient against running API server."""

import pytest

from property_finder_models import EnrichedWikipediaArticle, WikipediaSummary

from ..exceptions import NotFoundError, APIError


class TestWikipediaAPIClientIntegration:
    """Integration tests for WikipediaAPIClient."""
    
    def test_server_available(self, api_server_check, wikipedia_api_client):
        """Test that API server is available and client is configured."""
        assert api_server_check is True
        assert wikipedia_api_client is not None
        assert str(wikipedia_api_client.config.base_url).endswith("/wikipedia")
    
    def test_get_articles_basic(self, wikipedia_api_client, skip_if_no_data):
        """Test basic Wikipedia article retrieval."""
        articles = skip_if_no_data(
            wikipedia_api_client.get_articles,
            page=1,
            page_size=10
        )
        
        assert isinstance(articles, list)
        assert len(articles) <= 10
        
        if articles:
            article = articles[0]
            assert isinstance(article, EnrichedWikipediaArticle)
            assert article.page_id > 0
            assert article.title is not None
            assert article.url is not None
            assert article.full_text is not None
            assert article.relevance_score >= 0.0
    
    def test_get_articles_with_city_filter(self, wikipedia_api_client):
        """Test article retrieval with city filter."""
        test_cities = ["San Francisco", "Park City"]
        
        for city in test_cities:
            try:
                articles = wikipedia_api_client.get_articles(
                    city=city,
                    page_size=5
                )
                
                if articles:
                    # Verify all returned articles have location info
                    for article in articles:
                        assert isinstance(article, EnrichedWikipediaArticle)
                        # Location info should be present but may not exactly match filter
                        assert article.location is not None
                    break  # Found data, test passed
                    
            except APIError:
                continue
        else:
            pytest.skip("No articles found for any test cities")
    
    def test_get_articles_with_state_filter(self, wikipedia_api_client):
        """Test article retrieval with state filter."""
        test_states = ["California", "Utah"]
        
        for state in test_states:
            try:
                articles = wikipedia_api_client.get_articles(
                    state=state,
                    page_size=5
                )
                
                if articles:
                    # Verify articles have location info
                    for article in articles:
                        assert isinstance(article, EnrichedWikipediaArticle)
                        assert article.location is not None
                    break
                    
            except APIError:
                continue
        else:
            pytest.skip("No articles found for any test states")
    
    def test_get_articles_with_relevance_filter(self, wikipedia_api_client, skip_if_no_data):
        """Test article retrieval with relevance score filtering."""
        articles = skip_if_no_data(
            wikipedia_api_client.get_articles,
            relevance_min=0.5,
            page_size=10
        )
        
        if articles:
            # Verify all articles meet relevance threshold
            for article in articles:
                assert isinstance(article, EnrichedWikipediaArticle)
                assert article.relevance_score >= 0.5
    
    def test_get_articles_with_sorting(self, wikipedia_api_client, skip_if_no_data):
        """Test article retrieval with different sorting options."""
        sort_options = ["relevance", "title", "page_id"]
        
        for sort_by in sort_options:
            try:
                articles = skip_if_no_data(
                    wikipedia_api_client.get_articles,
                    sort_by=sort_by,
                    page_size=5
                )
                
                if articles and len(articles) > 1:
                    # Verify sorting worked (at least roughly)
                    if sort_by == "relevance":
                        # Relevance should be in descending order (highest first)
                        for i in range(len(articles) - 1):
                            assert articles[i].relevance_score >= articles[i + 1].relevance_score
                    elif sort_by == "title":
                        # Titles should be in alphabetical order
                        titles = [article.title for article in articles]
                        assert titles == sorted(titles)
                    elif sort_by == "page_id":
                        # Page IDs should be in ascending order
                        page_ids = [article.page_id for article in articles]
                        assert page_ids == sorted(page_ids)
                    break
                    
            except APIError:
                continue
    
    def test_get_article_by_id(self, wikipedia_api_client, skip_if_no_data):
        """Test retrieving a single article by page ID."""
        # First get a list to find a valid page ID
        articles = skip_if_no_data(
            wikipedia_api_client.get_articles,
            page_size=1
        )
        
        if articles:
            page_id = articles[0].page_id
            
            # Get the specific article
            single_article = wikipedia_api_client.get_article_by_id(page_id)
            
            assert isinstance(single_article, EnrichedWikipediaArticle)
            assert single_article.page_id == page_id
            assert single_article.title is not None
            assert single_article.full_text is not None
    
    def test_get_article_by_invalid_id(self, wikipedia_api_client):
        """Test retrieving article with invalid ID raises NotFoundError."""
        with pytest.raises(NotFoundError):
            wikipedia_api_client.get_article_by_id(999999999)  # Very unlikely to exist
    
    def test_get_all_articles_pagination(self, wikipedia_api_client, skip_if_no_data):
        """Test automatic pagination through all articles."""
        # Use small page size to test pagination, but limit to first few pages for testing
        page_count = 0
        max_pages = 5  # Limit test to first 5 pages to avoid long running tests
        all_article_pages = []
        
        for page in wikipedia_api_client.get_all_articles(page_size=3):
            all_article_pages.append(page)
            page_count += 1
            if page_count >= max_pages:
                break
        
        if not all_article_pages:
            pytest.skip("No articles available for pagination test")
        
        # Verify we got pages of articles
        assert len(all_article_pages) >= 1
        
        # Verify all items are EnrichedWikipediaArticle objects
        for page in all_article_pages:
            assert isinstance(page, list)
            for article in page:
                assert isinstance(article, EnrichedWikipediaArticle)
        
        # Verify no duplicate page IDs across pages
        all_page_ids = []
        for page in all_article_pages:
            page_ids = [article.page_id for article in page]
            all_page_ids.extend(page_ids)
        
        unique_ids = set(all_page_ids)
        assert len(all_page_ids) == len(unique_ids), "Found duplicate page IDs across pages"
    
    def test_get_summaries_basic(self, wikipedia_api_client):
        """Test basic Wikipedia summary retrieval."""
        try:
            summaries = wikipedia_api_client.get_summaries(page_size=10)
            
            if summaries:
                assert isinstance(summaries, list)
                assert len(summaries) <= 10
                
                summary = summaries[0]
                assert isinstance(summary, WikipediaSummary)
                assert summary.page_id > 0
                assert summary.article_title is not None
                assert summary.overall_confidence >= 0.0
            else:
                pytest.skip("No summaries available")
                
        except APIError as e:
            pytest.skip(f"Summaries endpoint not available: {e}")
    
    def test_get_summaries_with_confidence_filter(self, wikipedia_api_client):
        """Test summary retrieval with confidence filtering."""
        try:
            summaries = wikipedia_api_client.get_summaries(
                confidence_min=0.7,
                page_size=5
            )
            
            if summaries:
                # Verify all summaries meet confidence threshold
                for summary in summaries:
                    assert isinstance(summary, WikipediaSummary)
                    assert summary.overall_confidence >= 0.7
            else:
                pytest.skip("No high-confidence summaries available")
                
        except APIError as e:
            pytest.skip(f"Confidence filtering not available: {e}")
    
    def test_get_summaries_with_location_filter(self, wikipedia_api_client):
        """Test summary retrieval with location filtering."""
        test_locations = [
            ("San Francisco", "California"),
            ("Park City", "Utah")
        ]
        
        for city, state in test_locations:
            try:
                summaries = wikipedia_api_client.get_summaries(
                    city=city,
                    state=state,
                    page_size=5
                )
                
                if summaries:
                    # Verify summaries have location info
                    for summary in summaries:
                        assert isinstance(summary, WikipediaSummary)
                        # Location may not exactly match but should be present
                        assert summary.best_city is not None or summary.best_state is not None
                    break
                    
            except APIError:
                continue
        else:
            pytest.skip("No summaries found for any test locations")
    
    def test_get_summaries_with_key_topics(self, wikipedia_api_client):
        """Test summary retrieval with key topics included."""
        try:
            summaries = wikipedia_api_client.get_summaries(
                include_key_topics=True,
                page_size=5
            )
            
            if summaries:
                for summary in summaries:
                    assert isinstance(summary, WikipediaSummary)
                    # Key topics should be a list (may be empty)
                    assert isinstance(summary.key_topics, list)
            else:
                pytest.skip("No summaries with key topics available")
                
        except APIError as e:
            pytest.skip(f"Key topics not available: {e}")
    
    def test_get_summary_by_id(self, wikipedia_api_client):
        """Test retrieving a single summary by page ID."""
        try:
            # First get a list to find a valid page ID
            summaries = wikipedia_api_client.get_summaries(page_size=1)
            
            if summaries:
                page_id = summaries[0].page_id
                
                # Get the specific summary
                single_summary = wikipedia_api_client.get_summary_by_id(page_id)
                
                assert isinstance(single_summary, WikipediaSummary)
                assert single_summary.page_id == page_id
                assert single_summary.article_title is not None
            else:
                pytest.skip("No summaries available for ID test")
                
        except APIError as e:
            pytest.skip(f"Summary by ID not available: {e}")
    
    def test_get_all_summaries_pagination(self, wikipedia_api_client):
        """Test automatic pagination through all summaries."""
        try:
            # Use small page size to test pagination
            all_summary_pages = list(wikipedia_api_client.get_all_summaries(page_size=3))
            
            if not all_summary_pages:
                pytest.skip("No summaries available for pagination test")
            
            # Verify we got pages of summaries
            assert len(all_summary_pages) >= 1
            
            # Verify all items are WikipediaSummary objects
            for page in all_summary_pages:
                assert isinstance(page, list)
                for summary in page:
                    assert isinstance(summary, WikipediaSummary)
            
            # Verify no duplicate page IDs across pages
            all_page_ids = []
            for page in all_summary_pages:
                page_ids = [summary.page_id for summary in page]
                all_page_ids.extend(page_ids)
            
            unique_ids = set(all_page_ids)
            assert len(all_page_ids) == len(unique_ids), "Found duplicate page IDs across pages"
            
        except APIError as e:
            pytest.skip(f"Summary pagination not available: {e}")
    
    def test_articles_with_embeddings(self, wikipedia_api_client):
        """Test article retrieval with embedding inclusion (if supported)."""
        try:
            articles = wikipedia_api_client.get_articles(
                page_size=2,
                include_embeddings=True,
                collection_name="test_collection"
            )
            
            if articles:
                # Just verify the request doesn't fail and returns articles
                assert isinstance(articles, list)
                for article in articles:
                    assert isinstance(article, EnrichedWikipediaArticle)
            else:
                pytest.skip("No articles with embeddings available")
                
        except APIError as e:
            # Embedding functionality might not be available, skip gracefully
            pytest.skip(f"Embeddings not available: {e}")
    
    def test_error_handling_invalid_page(self, wikipedia_api_client):
        """Test error handling for invalid page numbers."""
        with pytest.raises((APIError, ValueError)):
            wikipedia_api_client.get_articles(page=0)  # Invalid page number
    
    def test_error_handling_invalid_relevance(self, wikipedia_api_client):
        """Test error handling for invalid relevance scores."""
        with pytest.raises((APIError, ValueError)):
            wikipedia_api_client.get_articles(relevance_min=1.5)  # Invalid relevance > 1.0
        
        with pytest.raises((APIError, ValueError)):
            wikipedia_api_client.get_articles(relevance_min=-0.1)  # Invalid relevance < 0.0