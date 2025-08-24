"""End-to-end integration tests for realistic API client usage scenarios."""

import pytest

from property_finder_models import EnrichedProperty, EnrichedWikipediaArticle

from ..exceptions import APIError, NotFoundError


class TestEndToEndScenarios:
    """End-to-end integration tests for real-world usage patterns."""
    
    def test_property_search_workflow(self, property_api_client, api_server_check, skip_if_no_data):
        """Test a complete property search workflow."""
        assert api_server_check is True
        
        # 1. Search for properties in a specific city
        san_francisco_properties = []
        try:
            san_francisco_properties = property_api_client.get_properties(
                city="San Francisco",
                page_size=5
            )
        except APIError:
            pass
        
        # 2. If no SF properties, try Park City
        if not san_francisco_properties:
            try:
                park_city_properties = property_api_client.get_properties(
                    city="Park City",
                    page_size=5
                )
                if park_city_properties:
                    san_francisco_properties = park_city_properties
            except APIError:
                pass
        
        # 3. If still no properties, get any available properties
        if not san_francisco_properties:
            san_francisco_properties = skip_if_no_data(
                property_api_client.get_properties,
                page_size=5
            )
        
        # 4. Get detailed information for each property
        detailed_properties = []
        for prop in san_francisco_properties[:3]:  # Limit to first 3
            try:
                detailed_prop = property_api_client.get_property_by_id(prop.listing_id)
                detailed_properties.append(detailed_prop)
            except NotFoundError:
                # Property might have been removed, skip
                continue
        
        # 5. Verify we got detailed property information
        assert len(detailed_properties) > 0, "Should have retrieved detailed property information"
        
        for prop in detailed_properties:
            assert isinstance(prop, EnrichedProperty)
            assert prop.listing_id is not None
            assert prop.price > 0
            assert prop.address is not None
            assert prop.address.city is not None
    
    def test_wikipedia_research_workflow(self, wikipedia_api_client, api_server_check):
        """Test a complete Wikipedia research workflow."""
        assert api_server_check is True
        
        # 1. Search for articles about a specific location
        location_articles = []
        test_locations = [
            ("San Francisco", "California"),
            ("Park City", "Utah"),
            (None, "California"),  # Just state filter
            (None, None)  # No filter
        ]
        
        for city, state in test_locations:
            try:
                articles = wikipedia_api_client.get_articles(
                    city=city,
                    state=state,
                    page_size=5,
                    sort_by="relevance"
                )
                
                if articles:
                    location_articles = articles
                    break
            except APIError:
                continue
        
        if not location_articles:
            pytest.skip("No Wikipedia articles available for location research")
        
        # 2. Get high-relevance articles only
        high_relevance_articles = []
        try:
            high_relevance_articles = wikipedia_api_client.get_articles(
                relevance_min=0.7,
                page_size=3,
                sort_by="relevance"
            )
        except APIError:
            pass
        
        # 3. Get detailed information for specific articles
        detailed_articles = []
        articles_to_detail = high_relevance_articles if high_relevance_articles else location_articles[:2]
        
        for article in articles_to_detail:
            try:
                detailed_article = wikipedia_api_client.get_article_by_id(article.page_id)
                detailed_articles.append(detailed_article)
            except NotFoundError:
                continue
        
        # 4. Try to get summaries for the same articles
        summaries = []
        try:
            for article in detailed_articles[:2]:  # Limit to first 2
                try:
                    summary = wikipedia_api_client.get_summary_by_id(article.page_id)
                    summaries.append(summary)
                except (NotFoundError, APIError):
                    continue
        except APIError:
            pass
        
        # 5. Verify we got useful research data
        assert len(detailed_articles) > 0, "Should have retrieved detailed articles"
        
        for article in detailed_articles:
            assert isinstance(article, EnrichedWikipediaArticle)
            assert article.page_id > 0
            assert article.title is not None
            assert len(article.full_text) > 100, "Article should have substantial content"
    
    def test_cross_platform_data_correlation(self, property_api_client, wikipedia_api_client, api_server_check):
        """Test correlating data between property and Wikipedia APIs."""
        assert api_server_check is True
        
        # 1. Get properties from a specific city
        city_properties = []
        test_cities = ["San Francisco", "Park City"]
        
        for city in test_cities:
            try:
                properties = property_api_client.get_properties(
                    city=city,
                    page_size=3
                )
                
                if properties:
                    city_properties = properties
                    target_city = city
                    break
            except APIError:
                continue
        
        if not city_properties:
            pytest.skip("No city properties available for correlation test")
        
        # 2. Get Wikipedia articles for the same city
        city_articles = []
        try:
            city_articles = wikipedia_api_client.get_articles(
                city=target_city,
                page_size=5
            )
        except APIError:
            pass
        
        # 3. Verify we can work with data from both sources
        assert len(city_properties) > 0, "Should have properties for correlation"
        
        # Extract common location information
        property_locations = set()
        for prop in city_properties:
            if prop.address and prop.address.city:
                property_locations.add(prop.address.city.lower())
        
        # If we have articles, check for location overlap
        if city_articles:
            article_locations = set()
            for article in city_articles:
                if article.location and article.location.city:
                    article_locations.add(article.location.city.lower())
            
            # There might be some overlap in city names
            common_locations = property_locations.intersection(article_locations)
            # Don't require overlap since location data might be formatted differently
        
        # 4. Demonstrate we can access detailed information from both sources
        if city_properties:
            detailed_property = property_api_client.get_property_by_id(city_properties[0].listing_id)
            assert detailed_property.address is not None
        
        if city_articles:
            detailed_article = wikipedia_api_client.get_article_by_id(city_articles[0].page_id)
            assert detailed_article.full_text is not None
    
    def test_pagination_across_large_dataset(self, property_api_client, api_server_check):
        """Test pagination functionality with larger datasets."""
        assert api_server_check is True
        
        try:
            # Get all properties with small page size to test pagination
            all_pages = list(property_api_client.get_all_properties(page_size=5))
            
            if not all_pages:
                pytest.skip("No properties available for pagination test")
            
            # Verify we got multiple pages or one complete page
            total_properties = sum(len(page) for page in all_pages)
            assert total_properties > 0, "Should have retrieved properties"
            
            # If we got multiple pages, verify they don't overlap
            if len(all_pages) > 1:
                all_property_ids = []
                for page in all_pages:
                    page_ids = [prop.listing_id for prop in page]
                    all_property_ids.extend(page_ids)
                
                unique_ids = set(all_property_ids)
                assert len(all_property_ids) == len(unique_ids), "No duplicate properties across pages"
            
            # Verify all properties are valid
            for page in all_pages:
                for prop in page:
                    assert isinstance(prop, EnrichedProperty)
                    assert prop.listing_id is not None
                    assert prop.price > 0
                    
        except APIError as e:
            pytest.skip(f"Pagination test not possible: {e}")
    
    def test_error_recovery_and_graceful_degradation(self, property_api_client, wikipedia_api_client, api_server_check):
        """Test error handling and graceful degradation in real scenarios."""
        assert api_server_check is True
        
        # 1. Test graceful handling of non-existent resources
        try:
            property_api_client.get_property_by_id("definitely-does-not-exist-12345")
            assert False, "Should have raised NotFoundError"
        except NotFoundError:
            # Expected behavior
            pass
        except APIError:
            # Also acceptable - might be different error format
            pass
        
        # 2. Test handling of invalid parameters
        with pytest.raises((APIError, ValueError)):
            property_api_client.get_properties(page=0)  # Invalid page
        
        with pytest.raises((APIError, ValueError)):
            wikipedia_api_client.get_articles(relevance_min=2.0)  # Invalid relevance
        
        # 3. Test batch operations with mixed valid/invalid IDs
        try:
            # Get one valid property ID
            valid_properties = property_api_client.get_properties(page_size=1)
            
            if valid_properties:
                valid_id = valid_properties[0].listing_id
                mixed_ids = [valid_id, "invalid-id-1", "invalid-id-2"]
                
                # Should return only valid properties, gracefully skip invalid ones
                batch_result = property_api_client.batch_get_properties(mixed_ids)
                
                assert len(batch_result) <= len(mixed_ids)
                assert all(isinstance(prop, EnrichedProperty) for prop in batch_result)
                
                # Should include the valid property
                returned_ids = {prop.listing_id for prop in batch_result}
                assert valid_id in returned_ids
                
        except APIError:
            pytest.skip("Batch operations not available for error recovery test")
    
    def test_performance_and_responsiveness(self, property_api_client, wikipedia_api_client, api_server_check):
        """Test that API responses are reasonably fast."""
        assert api_server_check is True
        
        import time
        
        # Test property API responsiveness
        start_time = time.time()
        try:
            properties = property_api_client.get_properties(page_size=5)
            property_response_time = time.time() - start_time
            
            # Should respond within reasonable time (adjust as needed)
            assert property_response_time < 10.0, f"Property API too slow: {property_response_time:.2f}s"
            
        except APIError:
            pass  # Skip if no properties available
        
        # Test Wikipedia API responsiveness
        start_time = time.time()
        try:
            articles = wikipedia_api_client.get_articles(page_size=5)
            wikipedia_response_time = time.time() - start_time
            
            # Should respond within reasonable time
            assert wikipedia_response_time < 10.0, f"Wikipedia API too slow: {wikipedia_response_time:.2f}s"
            
        except APIError:
            pass  # Skip if no articles available
        
        # Test individual resource retrieval
        try:
            properties = property_api_client.get_properties(page_size=1)
            if properties:
                start_time = time.time()
                detailed_prop = property_api_client.get_property_by_id(properties[0].listing_id)
                detail_response_time = time.time() - start_time
                
                assert detail_response_time < 5.0, f"Property detail too slow: {detail_response_time:.2f}s"
                
        except (APIError, NotFoundError):
            pass  # Skip if not available