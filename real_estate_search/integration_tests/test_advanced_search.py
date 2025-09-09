"""
Integration tests for advanced search functionality.

Tests the semantic search, multi-entity search, and Wikipedia search capabilities.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from real_estate_search.demo_queries.advanced import (
    SemanticSearchBuilder,
    MultiEntitySearchBuilder,
    WikipediaSearchBuilder,
    AdvancedSearchExecutor,
    AdvancedDemoRunner,
    demo_semantic_search,
    demo_multi_entity_search,
    demo_wikipedia_search,
    SearchRequest,
    MultiIndexSearchRequest,
    WikipediaSearchRequest,
    EntityDiscriminationResult
)
from real_estate_search.models.property import PropertyListing
from real_estate_search.models.address import Address
from real_estate_search.demo_queries.result_models import (
    PropertySearchResult,
    WikipediaSearchResult,
    MixedEntityResult
)
from real_estate_search.models import PropertyListing


class TestSemanticSearchBuilder:
    """Test the semantic search builder."""
    
    def test_build_similarity_search(self):
        """Test building a similarity search query."""
        builder = SemanticSearchBuilder()
        embedding = [0.1] * 1024
        property_id = "test-prop-123"
        
        request = builder.build_similarity_search(
            reference_embedding=embedding,
            reference_property_id=property_id,
            size=5
        )
        
        assert isinstance(request, SearchRequest)
        assert request.size == 5
        assert request.index == "properties"
        assert "knn" in request.query
        assert request.query["knn"]["query_vector"] == embedding
        assert request.query["knn"]["k"] == 6  # size + 1
        
    def test_build_random_property_query(self):
        """Test building a random property query."""
        builder = SemanticSearchBuilder()
        
        request = builder.build_random_property_query(seed=42)
        
        assert isinstance(request, SearchRequest)
        assert request.size == 1
        assert "function_score" in request.query["query"]
        assert request.query["query"]["function_score"]["random_score"]["seed"] == 42
        
    def test_extract_reference_property(self):
        """Test extracting reference property from ES response."""
        builder = SemanticSearchBuilder()
        
        # Test with direct get response
        es_response = {
            "_id": "prop-123",
            "_source": {
                "embedding": [0.1] * 1024,
                "address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102"
                },
                "property_type": "Condo",
                "price": 750000,
                "bedrooms": 2,
                "bathrooms": 2,
                "square_feet": 1200,
                "description": "Beautiful condo"
            }
        }
        
        reference = builder.extract_reference_property(es_response)
        
        assert isinstance(reference, PropertyListing)
        assert reference.listing_id == "prop-123"
        assert isinstance(reference.address, Address)
        assert reference.address.street == "123 Main St"
        assert reference.address.city == "San Francisco"
        assert reference.price == 750000
        
    def test_extract_reference_property_no_embedding(self):
        """Test extracting reference property without embedding."""
        builder = SemanticSearchBuilder()
        
        es_response = {
            "_id": "prop-123",
            "_source": {
                "address": {"street": "123 Main St"},
                "price": 750000
            }
        }
        
        reference = builder.extract_reference_property(es_response)
        assert reference is None


class TestMultiEntitySearchBuilder:
    """Test the multi-entity search builder."""
    
    def test_build_multi_index_search(self):
        """Test building a multi-index search query."""
        builder = MultiEntitySearchBuilder()
        
        request = builder.build_multi_index_search(
            query_text="historic downtown",
            size_per_type=3
        )
        
        assert isinstance(request, MultiIndexSearchRequest)
        assert request.size == 9  # 3 * 3 indices
        assert request.indices == ["properties", "neighborhoods", "wikipedia"]
        assert "multi_match" in request.query["query"]
        assert request.query["query"]["multi_match"]["query"] == "historic downtown"
        assert request.aggregations is not None
        
    def test_build_entity_aggregation(self):
        """Test building entity aggregation."""
        builder = MultiEntitySearchBuilder()
        
        agg = builder.build_entity_aggregation()
        
        assert "by_index" in agg
        assert agg["by_index"]["terms"]["field"] == "_index"
        
    def test_get_field_boost_config(self):
        """Test getting field boost configuration."""
        builder = MultiEntitySearchBuilder()
        
        config = builder.get_field_boost_config()
        
        assert config["title"] == 3.0
        assert config["description"] == 2.0
        assert config["content"] == 1.0


class TestWikipediaSearchBuilder:
    """Test the Wikipedia search builder."""
    
    def test_build_location_search(self):
        """Test building a location-based Wikipedia search."""
        builder = WikipediaSearchBuilder()
        
        request = builder.build_location_search(
            city="San Francisco",
            state="CA",
            topics=["history", "architecture"],
            size=10
        )
        
        assert isinstance(request, WikipediaSearchRequest)
        assert request.size == 10
        assert request.index == "wikipedia"
        assert "bool" in request.query["query"]
        
    def test_build_neighborhood_association_search(self):
        """Test building a neighborhood association search."""
        builder = WikipediaSearchBuilder()
        
        request = builder.build_neighborhood_association_search(
            city="San Francisco",
            state="CA",
            size=5
        )
        
        assert isinstance(request, WikipediaSearchRequest)
        assert request.size == 5
        assert "bool" in request.query["query"]
        assert "filter" in request.query["query"]["bool"]
        
    def test_build_specific_neighborhood_search(self):
        """Test building a specific neighborhood search."""
        builder = WikipediaSearchBuilder()
        
        request = builder.build_specific_neighborhood_search(
            neighborhood_name="Temescal",
            neighborhood_id="oak-temescal-006",
            size=3
        )
        
        assert isinstance(request, WikipediaSearchRequest)
        assert request.size == 3
        assert "should" in request.query["query"]["bool"]
        
    def test_extract_summary(self):
        """Test extracting summary from Wikipedia article."""
        builder = WikipediaSearchBuilder()
        
        article = {
            "short_summary": "This is the short summary",
            "long_summary": "This is the long summary",
            "full_content": "Title\n\nThis is the full content"
        }
        
        # Test with short_summary
        summary = builder.extract_summary(article)
        assert summary == "This is the short summary"
        
        # Test fallback to long_summary
        article_no_short = {"long_summary": "Long summary only"}
        summary = builder.extract_summary(article_no_short)
        assert summary == "Long summary only"
        
        # Test fallback to full_content
        article_content_only = {
            "title": "Title",
            "full_content": "Title\nActual content here"
        }
        summary = builder.extract_summary(article_content_only)
        assert "Actual content here" in summary


class TestAdvancedSearchExecutor:
    """Test the advanced search executor."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        return Mock()
    
    def test_discriminate_entity_type(self, mock_es_client):
        """Test entity type discrimination."""
        executor = AdvancedSearchExecutor(mock_es_client)
        
        # Test properties index
        hit = {"_index": "properties_v1"}
        result = executor._discriminate_entity_type(hit)
        assert isinstance(result, EntityDiscriminationResult)
        assert result.entity_type == "property"
        
        # Test neighborhoods index
        hit = {"_index": "neighborhoods_v2"}
        result = executor._discriminate_entity_type(hit)
        assert result.entity_type == "neighborhood"
        
        # Test wikipedia index
        hit = {"_index": "wikipedia_articles"}
        result = executor._discriminate_entity_type(hit)
        assert result.entity_type == "wikipedia"
        
        # Test unknown index
        hit = {"_index": "unknown_index"}
        result = executor._discriminate_entity_type(hit)
        assert result.entity_type == "unknown"
    
    def test_execute_semantic_search(self, mock_es_client):
        """Test executing semantic search."""
        executor = AdvancedSearchExecutor(mock_es_client)
        
        # Mock ES response
        mock_es_client.search.return_value = {
            "took": 25,
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "prop-1",
                        "_score": 0.95,
                        "_source": {
                            "listing_id": "L001",
                            "property_type": "condo",
                            "price": 500000,
                            "bedrooms": 2,
                            "bathrooms": 2.0,
                            "square_feet": 1000,
                            "year_built": 2010,
                            "address": {
                                "street": "123 Main St",
                                "city": "San Francisco",
                                "state": "CA",
                                "zip": "94102"
                            },
                            "description": "Nice condo",
                            "features": ["parking", "gym"],
                            "listing_type": "sale"
                        }
                    }
                ]
            }
        }
        
        request = SearchRequest(
            query={"knn": {"field": "embedding"}},
            size=10,
            index="properties"
        )
        
        response = executor.execute_semantic(request)
        
        assert response.execution_time_ms == 25
        assert response.total_hits == 2
        assert len(response.results) == 1
        assert response.results[0].listing_id == "L001"
        assert response.results[0].price == 500000
    
    def test_execute_multi_entity_search(self, mock_es_client):
        """Test executing multi-entity search."""
        executor = AdvancedSearchExecutor(mock_es_client)
        
        # Mock ES response with mixed entities
        mock_es_client.search.return_value = {
            "took": 30,
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_index": "properties",
                        "_id": "prop-1",
                        "_score": 0.9,
                        "_source": {
                            "listing_id": "L001",
                            "property_type": "house",
                            "price": 600000,
                            "bedrooms": 3,
                            "bathrooms": 2.5,
                            "square_feet": 1500,
                            "year_built": 2015,
                            "address": {
                                "street": "456 Oak St",
                                "city": "San Francisco",
                                "state": "CA",
                                "zip": "94110"
                            },
                            "description": "Beautiful house",
                            "features": ["garage"],
                            "listing_type": "sale"
                        }
                    },
                    {
                        "_index": "wikipedia",
                        "_id": "wiki-1",
                        "_score": 0.85,
                        "_source": {
                            "page_id": "123",
                            "title": "Historic Downtown",
                            "short_summary": "Downtown area"
                        }
                    },
                    {
                        "_index": "neighborhoods",
                        "_id": "neigh-1",
                        "_score": 0.8,
                        "_source": {
                            "name": "Downtown",
                            "city": "San Francisco"
                        }
                    }
                ]
            },
            "aggregations": {
                "by_index": {
                    "buckets": [
                        {"key": "properties", "doc_count": 1},
                        {"key": "wikipedia", "doc_count": 1},
                        {"key": "neighborhoods", "doc_count": 1}
                    ]
                }
            }
        }
        
        request = MultiIndexSearchRequest(
            query={"multi_match": {"query": "downtown"}},
            indices=["properties", "neighborhoods", "wikipedia"],
            size=10
        )
        
        response = executor.execute_multi_entity(request)
        
        assert response.execution_time_ms == 30
        assert response.total_hits == 3
        assert len(response.property_results) == 1
        assert len(response.wikipedia_results) == 1
        assert len(response.neighborhood_results) == 1
        assert response.property_results[0].listing_id == "L001"
        assert response.wikipedia_results[0].title == "Historic Downtown"


class TestAdvancedDemoRunner:
    """Test the advanced demo runner."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        mock = Mock()
        # Mock a basic response for all searches
        mock.search.return_value = {
            "took": 10,
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        mock.get.return_value = {
            "_id": "prop-123",
            "_source": {
                "embedding": [0.1] * 1024,
                "address": {"street": "123 Main St", "city": "SF"},
                "property_type": "Condo",
                "price": 500000,
                "bedrooms": 2,
                "bathrooms": 2,
                "square_feet": 1000,
                "description": "Test property"
            }
        }
        return mock
    
    def test_run_semantic_search(self, mock_es_client):
        """Test running semantic search demo."""
        runner = AdvancedDemoRunner(mock_es_client)
        
        # Mock getting reference property
        with patch.object(runner.executor, 'get_reference_property') as mock_get_ref:
            mock_get_ref.return_value = PropertyListing(
                listing_id="prop-123",
                property_type="condo",
                embedding=[0.1] * 1024,
                address=Address(street="123 Main St", city="SF"),
                price=500000,
                bedrooms=2,
                bathrooms=2,
                square_feet=1000,
                description="Test property"
            )
            
            # Mock display to prevent console output
            with patch.object(runner.display, 'display_semantic_results'):
                result = runner.run_semantic_search(
                    reference_property_id="prop-123",
                    size=5
                )
        
        assert isinstance(result, PropertySearchResult)
        assert "Semantic Similarity Search" in result.query_name
        assert result.returned_hits == 0  # Based on mock response
    
    def test_run_multi_entity_search(self, mock_es_client):
        """Test running multi-entity search demo."""
        runner = AdvancedDemoRunner(mock_es_client)
        
        # Mock display to prevent console output
        with patch.object(runner.display, 'display_multi_entity_results'):
            result = runner.run_multi_entity_search(
                query_text="downtown parks",
                size=3
            )
        
        assert isinstance(result, MixedEntityResult)
        assert "Multi-Entity Search" in result.query_name
        assert "downtown parks" in result.query_name
    
    def test_run_wikipedia_search(self, mock_es_client):
        """Test running Wikipedia search demo."""
        runner = AdvancedDemoRunner(mock_es_client)
        
        # Mock display to prevent console output
        with patch.object(runner.display, 'display_wikipedia_results'):
            with patch.object(runner.display, 'display_neighborhood_associations'):
                result = runner.run_wikipedia_search(
                    city="Oakland",
                    state="CA",
                    topics=["history"],
                    size=5
                )
        
        assert isinstance(result, WikipediaSearchResult)
        assert "Wikipedia Location & Topic Search" in result.query_name


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_address_model(self):
        """Test Address model validation."""
        # Test with all fields
        addr = Address(
            street="123 Main St",
            city="San Francisco",
            state="ca",
            zip_code="94102"
        )
        assert addr.state == "ca"  # State is stored as provided
        
        # Test with minimal fields
        addr_min = Address()
        assert addr_min.street == ""
        assert addr_min.city == ""
        assert addr_min.state == ""
        assert addr_min.zip_code == ""
    
    def test_property_listing_validation(self):
        """Test PropertyListing validation."""
        # Test valid property
        prop = PropertyListing(
            listing_id="prop-123",
            property_type="condo",
            embedding=[0.1, 0.2, 0.3],
            address=Address(city="SF"),
            price=500000,
            bedrooms=2,
            bathrooms=2,
            square_feet=1000,
            description="Nice place"
        )
        assert prop.price == 500000
        
        # Test that PropertyListing can handle empty embedding
        prop_no_embedding = PropertyListing(
            listing_id="prop-123",
            property_type="condo",
            price=500000,  # price is required field
            embedding=[],  # Empty embedding is now allowed
            address=Address(),
            bedrooms=1,
            bathrooms=1,
            square_feet=800,
            description="Basic property"
        )
        assert prop_no_embedding.embedding == []
    
    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Test with valid size
        req = SearchRequest(
            query={"match_all": {}},
            size=50
        )
        assert req.size == 50
        
        # Test size bounds
        with pytest.raises(ValueError):
            SearchRequest(
                query={"match_all": {}},
                size=0  # Too small
            )
        
        with pytest.raises(ValueError):
            SearchRequest(
                query={"match_all": {}},
                size=101  # Too large
            )
    
    def test_entity_discrimination_validation(self):
        """Test EntityDiscriminationResult validation."""
        # Test valid entity types
        for entity_type in ["property", "neighborhood", "wikipedia", "unknown"]:
            result = EntityDiscriminationResult(
                entity_type=entity_type,
                index_name="test_index",
                confidence=0.9
            )
            assert result.entity_type == entity_type
        
        # Test invalid entity type
        with pytest.raises(ValueError, match="Entity type must be one of"):
            EntityDiscriminationResult(
                entity_type="invalid_type",
                index_name="test_index"
            )
        
        # Test confidence bounds
        with pytest.raises(ValueError):
            EntityDiscriminationResult(
                entity_type="property",
                index_name="test_index",
                confidence=1.5  # Too high
            )


class TestDemoFunctions:
    """Test the public demo functions."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        mock = Mock()
        mock.search.return_value = {
            "took": 10,
            "hits": {"total": {"value": 0}, "hits": []}
        }
        return mock
    
    def test_demo_semantic_search_function(self, mock_es_client):
        """Test the demo_semantic_search function."""
        with patch('real_estate_search.demo_queries.advanced.demo_runner.AdvancedDemoRunner') as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.run_semantic_search.return_value = PropertySearchResult(
                query_name="Test",
                execution_time_ms=10,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={}
            )
            
            result = demo_semantic_search(mock_es_client)
            
            assert isinstance(result, PropertySearchResult)
            MockRunner.assert_called_once_with(mock_es_client)
            mock_instance.run_semantic_search.assert_called_once()
    
    def test_demo_multi_entity_search_function(self, mock_es_client):
        """Test the demo_multi_entity_search function."""
        with patch('real_estate_search.demo_queries.advanced.demo_runner.AdvancedDemoRunner') as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.run_multi_entity_search.return_value = MixedEntityResult(
                query_name="Test",
                execution_time_ms=10,
                total_hits=0,
                returned_hits=0,
                property_results=[],
                wikipedia_results=[],
                neighborhood_results=[],
                query_dsl={}
            )
            
            result = demo_multi_entity_search(mock_es_client, "test query")
            
            assert isinstance(result, MixedEntityResult)
            mock_instance.run_multi_entity_search.assert_called_once_with("test query", 5)
    
    def test_demo_wikipedia_search_function(self, mock_es_client):
        """Test the demo_wikipedia_search function."""
        with patch('real_estate_search.demo_queries.advanced.demo_runner.AdvancedDemoRunner') as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.run_wikipedia_search.return_value = WikipediaSearchResult(
                query_name="Test",
                execution_time_ms=10,
                total_hits=0,
                returned_hits=0,
                results=[],
                query_dsl={}
            )
            
            result = demo_wikipedia_search(
                mock_es_client,
                city="Oakland",
                state="CA",
                topics=["parks"]
            )
            
            assert isinstance(result, WikipediaSearchResult)
            mock_instance.run_wikipedia_search.assert_called_once_with(
                "Oakland", "CA", ["parks"], 10
            )