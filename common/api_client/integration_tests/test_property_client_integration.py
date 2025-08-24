"""Integration tests for PropertyAPIClient against running API server."""

import pytest

from property_finder_models import EnrichedProperty, EnrichedNeighborhood

from ..exceptions import NotFoundError, APIError


class TestPropertyAPIClientIntegration:
    """Integration tests for PropertyAPIClient."""
    
    def test_server_available(self, api_server_check, property_api_client):
        """Test that API server is available and client is configured."""
        assert api_server_check is True
        assert property_api_client is not None
        assert str(property_api_client.config.base_url).endswith("/api/v1")
    
    def test_get_properties_basic(self, property_api_client, skip_if_no_data):
        """Test basic property retrieval."""
        properties = skip_if_no_data(
            property_api_client.get_properties,
            page=1,
            page_size=10
        )
        
        assert isinstance(properties, list)
        assert len(properties) <= 10
        
        if properties:
            property_obj = properties[0]
            assert isinstance(property_obj, EnrichedProperty)
            assert property_obj.listing_id is not None
            assert property_obj.price > 0
            assert property_obj.bedrooms >= 0
            assert property_obj.bathrooms >= 0
            assert property_obj.address is not None
            assert property_obj.address.city is not None
            assert property_obj.address.state is not None
    
    def test_get_properties_with_city_filter(self, property_api_client):
        """Test property retrieval with city filter."""
        # Test with known cities that should have data
        test_cities = ["San Francisco", "Park City"]
        
        for city in test_cities:
            try:
                properties = property_api_client.get_properties(
                    city=city,
                    page_size=5
                )
                
                if properties:
                    # Verify all returned properties match the city filter
                    for prop in properties:
                        assert isinstance(prop, EnrichedProperty)
                        assert prop.address.city.lower() == city.lower() or city.lower() in prop.address.city.lower()
                    break  # Found data, test passed
                    
            except APIError:
                # Try next city
                continue
        else:
            pytest.skip("No properties found for any test cities")
    
    def test_get_properties_pagination(self, property_api_client, skip_if_no_data):
        """Test property retrieval pagination."""
        # Get first page
        page1_properties = skip_if_no_data(
            property_api_client.get_properties,
            page=1,
            page_size=5
        )
        
        if len(page1_properties) == 5:
            # Try to get second page
            page2_properties = property_api_client.get_properties(
                page=2,
                page_size=5
            )
            
            # Verify different results if second page exists
            if page2_properties:
                page1_ids = {prop.listing_id for prop in page1_properties}
                page2_ids = {prop.listing_id for prop in page2_properties}
                assert len(page1_ids.intersection(page2_ids)) == 0, "Pages should contain different properties"
    
    def test_get_property_by_id(self, property_api_client, skip_if_no_data):
        """Test retrieving a single property by ID."""
        # First get a list to find a valid ID
        properties = skip_if_no_data(
            property_api_client.get_properties,
            page_size=1
        )
        
        if properties:
            property_id = properties[0].listing_id
            
            # Get the specific property
            single_property = property_api_client.get_property_by_id(property_id)
            
            assert isinstance(single_property, EnrichedProperty)
            assert single_property.listing_id == property_id
            assert single_property.price > 0
            assert single_property.address is not None
    
    def test_get_property_by_invalid_id(self, property_api_client):
        """Test retrieving property with invalid ID raises NotFoundError."""
        with pytest.raises(NotFoundError):
            property_api_client.get_property_by_id("invalid-property-id-12345")
    
    def test_get_all_properties_pagination(self, property_api_client, skip_if_no_data):
        """Test automatic pagination through all properties."""
        # Use small page size to test pagination, but limit to first few pages for testing
        page_count = 0
        max_pages = 5  # Limit test to first 5 pages to avoid long running tests
        all_property_pages = []
        
        for page in property_api_client.get_all_properties(page_size=3):
            all_property_pages.append(page)
            page_count += 1
            if page_count >= max_pages:
                break
        
        if not all_property_pages:
            pytest.skip("No properties available for pagination test")
        
        # Verify we got pages of properties
        assert len(all_property_pages) >= 1
        
        # Verify all items are EnrichedProperty objects
        for page in all_property_pages:
            assert isinstance(page, list)
            for prop in page:
                assert isinstance(prop, EnrichedProperty)
        
        # Verify no duplicate property IDs across pages
        all_property_ids = []
        for page in all_property_pages:
            page_ids = [prop.listing_id for prop in page]
            all_property_ids.extend(page_ids)
        
        unique_ids = set(all_property_ids)
        assert len(all_property_ids) == len(unique_ids), "Found duplicate property IDs across pages"
    
    def test_get_neighborhoods_basic(self, property_api_client):
        """Test basic neighborhood retrieval."""
        try:
            neighborhoods = property_api_client.get_neighborhoods(page_size=10)
            
            if neighborhoods:
                assert isinstance(neighborhoods, list)
                assert len(neighborhoods) <= 10
                
                neighborhood = neighborhoods[0]
                assert isinstance(neighborhood, EnrichedNeighborhood)
                assert neighborhood.name is not None
                assert neighborhood.city is not None
                assert neighborhood.state is not None
            else:
                pytest.skip("No neighborhoods available")
                
        except APIError as e:
            pytest.skip(f"Neighborhoods endpoint not available: {e}")
    
    def test_get_neighborhoods_with_city_filter(self, property_api_client):
        """Test neighborhood retrieval with city filter."""
        test_cities = ["San Francisco", "Park City"]
        
        for city in test_cities:
            try:
                neighborhoods = property_api_client.get_neighborhoods(
                    city=city,
                    page_size=5
                )
                
                if neighborhoods:
                    # Verify all returned neighborhoods match the city filter
                    for neighborhood in neighborhoods:
                        assert isinstance(neighborhood, EnrichedNeighborhood)
                        assert neighborhood.city.lower() == city.lower() or city.lower() in neighborhood.city.lower()
                    break  # Found data, test passed
                    
            except APIError:
                continue
        else:
            pytest.skip("No neighborhoods found for any test cities")
    
    def test_get_neighborhood_by_id(self, property_api_client):
        """Test retrieving a single neighborhood by ID."""
        try:
            # First get a list to find a valid ID
            neighborhoods = property_api_client.get_neighborhoods(page_size=1)
            
            if neighborhoods:
                neighborhood_id = neighborhoods[0].neighborhood_id
                
                # Get the specific neighborhood
                single_neighborhood = property_api_client.get_neighborhood_by_id(neighborhood_id)
                
                assert isinstance(single_neighborhood, EnrichedNeighborhood)
                assert single_neighborhood.neighborhood_id == neighborhood_id
                assert single_neighborhood.name is not None
            else:
                pytest.skip("No neighborhoods available for ID test")
                
        except APIError as e:
            pytest.skip(f"Neighborhood by ID not available: {e}")
    
    def test_batch_get_properties(self, property_api_client, skip_if_no_data):
        """Test batch property retrieval."""
        # First get some properties to use their IDs
        properties = skip_if_no_data(
            property_api_client.get_properties,
            page_size=3
        )
        
        if len(properties) >= 2:
            property_ids = [prop.listing_id for prop in properties[:2]]
            
            # Test batch retrieval
            batch_properties = property_api_client.batch_get_properties(property_ids)
            
            assert isinstance(batch_properties, list)
            assert len(batch_properties) <= len(property_ids)
            
            # Verify all returned properties are in our requested list
            returned_ids = {prop.listing_id for prop in batch_properties}
            requested_ids = set(property_ids)
            assert returned_ids.issubset(requested_ids)
    
    def test_batch_get_properties_with_invalid_ids(self, property_api_client, skip_if_no_data):
        """Test batch property retrieval with mix of valid and invalid IDs."""
        # Get one valid ID
        properties = skip_if_no_data(
            property_api_client.get_properties,
            page_size=1
        )
        
        if properties:
            valid_id = properties[0].listing_id
            invalid_ids = ["invalid-id-1", "invalid-id-2"]
            
            # Mix valid and invalid IDs
            mixed_ids = [valid_id] + invalid_ids
            
            # Should return only the valid property, skip invalid ones
            batch_properties = property_api_client.batch_get_properties(mixed_ids)
            
            assert isinstance(batch_properties, list)
            assert len(batch_properties) == 1  # Only valid property returned
            assert batch_properties[0].listing_id == valid_id
    
    def test_properties_with_embeddings(self, property_api_client):
        """Test property retrieval with embedding inclusion (if supported)."""
        try:
            properties = property_api_client.get_properties(
                page_size=2,
                include_embeddings=True,
                collection_name="test_collection"
            )
            
            if properties:
                # Just verify the request doesn't fail and returns properties
                assert isinstance(properties, list)
                for prop in properties:
                    assert isinstance(prop, EnrichedProperty)
            else:
                pytest.skip("No properties with embeddings available")
                
        except APIError as e:
            # Embedding functionality might not be available, skip gracefully
            pytest.skip(f"Embeddings not available: {e}")
    
    def test_error_handling_invalid_page(self, property_api_client):
        """Test error handling for invalid page numbers."""
        with pytest.raises((APIError, ValueError)):
            property_api_client.get_properties(page=0)  # Invalid page number
    
    def test_error_handling_invalid_page_size(self, property_api_client):
        """Test error handling for invalid page sizes."""
        with pytest.raises((APIError, ValueError)):
            property_api_client.get_properties(page_size=0)  # Invalid page size