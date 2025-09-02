"""
Integration tests for location-aware hybrid search.

Tests the complete integration of location understanding with hybrid search,
ensuring location filters are properly applied to both text and vector search.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from elasticsearch import Elasticsearch

from real_estate_search.demo_queries.hybrid_search import (
    HybridSearchEngine,
    HybridSearchParams,
    HybridSearchResult,
    SearchResult
)
from real_estate_search.demo_queries.location_understanding import (
    LocationIntent,
    LocationUnderstandingModule,
    LocationFilterBuilder
)
from real_estate_search.config import AppConfig

logger = logging.getLogger(__name__)


class TestLocationHybridIntegration:
    """Test suite for location-aware hybrid search integration."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        mock = Mock(spec=Elasticsearch)
        # Mock successful search response
        mock.search.return_value = {
            'hits': {
                'total': {'value': 2},
                'hits': [
                    {
                        '_score': 0.95,
                        '_source': {
                            'listing_id': 'prop-001',
                            'property_type': 'single-family',
                            'price': 750000,
                            'bedrooms': 4,
                            'bathrooms': 3,
                            'square_feet': 2500,
                            'address': {
                                'street': '123 Main St',
                                'city': 'Park City',
                                'state': 'Utah',
                                'zip_code': '84060'
                            },
                            'description': 'Beautiful family home',
                            'features': ['garage', 'pool'],
                            'amenities': ['gym', 'spa'],
                            'neighborhood': {'name': 'Old Town'}
                        }
                    },
                    {
                        '_score': 0.85,
                        '_source': {
                            'listing_id': 'prop-002',
                            'property_type': 'condo',
                            'price': 550000,
                            'bedrooms': 3,
                            'bathrooms': 2,
                            'square_feet': 1800,
                            'address': {
                                'street': '456 Oak Ave',
                                'city': 'Park City',
                                'state': 'Utah',
                                'zip_code': '84098'
                            },
                            'description': 'Modern condo',
                            'features': ['balcony'],
                            'amenities': ['concierge'],
                            'neighborhood': {'name': 'Deer Valley'}
                        }
                    }
                ]
            },
            'took': 50
        }
        return mock
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        with patch('real_estate_search.demo_queries.hybrid_search.AppConfig') as mock_config_class:
            mock_config = Mock(spec=AppConfig)
            mock_config.embedding = Mock()
            mock_config.embedding.api_key = 'test-key'
            mock_config_class.load.return_value = mock_config
            return mock_config
    
    def test_direct_query_building(self):
        """Test that query building creates native Elasticsearch queries directly."""
        with patch('real_estate_search.demo_queries.hybrid_search.QueryEmbeddingService') as mock_embedding:
            mock_embedding_instance = Mock()
            mock_embedding_instance.embed_query.return_value = [0.1] * 1024
            mock_embedding.return_value = mock_embedding_instance
            
            engine = HybridSearchEngine(Mock(spec=Elasticsearch), Mock())
            
            # Test direct query building
            params = HybridSearchParams(
                query_text="modern home with pool",
                size=10,
                location_intent=LocationIntent(
                    city="Park City",
                    has_location=True,
                    cleaned_query="modern home with pool",
                    confidence=0.95
                )
            )
            
            query_dict = engine._build_rrf_query(params, [0.1] * 1024, "modern home with pool")
            
            # Verify native Elasticsearch structure
            assert "retriever" in query_dict
            assert "rrf" in query_dict["retriever"]
            assert "retrievers" in query_dict["retriever"]["rrf"]
            assert len(query_dict["retriever"]["rrf"]["retrievers"]) == 2
            assert query_dict["size"] == 10
            assert "_source" in query_dict
    
    def test_search_with_location_extraction(self, mock_es_client, mock_config):
        """Test complete flow with location extraction."""
        with patch('real_estate_search.demo_queries.hybrid_search.QueryEmbeddingService') as mock_embedding:
            # Mock embedding service
            mock_embedding_instance = Mock()
            mock_embedding_instance.embed_query.return_value = [0.1] * 1024
            mock_embedding.return_value = mock_embedding_instance
            
            # Mock location module to return Park City
            with patch.object(LocationUnderstandingModule, '__call__') as mock_location:
                mock_location.return_value = LocationIntent(
                    city="Park City",
                    state="Utah",
                    has_location=True,
                    cleaned_query="modern home with pool",
                    confidence=0.95
                )
                
                # Create engine and search
                engine = HybridSearchEngine(mock_es_client, mock_config)
                result = engine.search_with_location("modern home with pool in Park City")
                
                # Verify location was extracted
                mock_location.assert_called_once_with("modern home with pool in Park City")
                
                # Verify search was executed
                mock_es_client.search.assert_called_once()
                
                # Check the query structure
                call_args = mock_es_client.search.call_args
                query_body = call_args.kwargs['body']
                
                # Verify RRF structure exists
                assert 'retriever' in query_body
                assert 'rrf' in query_body['retriever']
                assert 'retrievers' in query_body['retriever']['rrf']
                
                # Verify result structure
                assert isinstance(result, HybridSearchResult)
                assert result.total_hits == 2
                assert len(result.results) == 2
    
    def test_location_filters_applied_to_both_retrievers(self, mock_es_client, mock_config):
        """Test that location filters are applied to both text and vector retrievers."""
        with patch('real_estate_search.demo_queries.hybrid_search.QueryEmbeddingService') as mock_embedding:
            mock_embedding_instance = Mock()
            mock_embedding_instance.embed_query.return_value = [0.1] * 1024
            mock_embedding.return_value = mock_embedding_instance
            
            engine = HybridSearchEngine(mock_es_client, mock_config)
            
            # Create params with location intent
            params = HybridSearchParams(
                query_text="luxury condo in San Francisco",
                size=10,
                location_intent=LocationIntent(
                    city="San Francisco",
                    state="California",
                    has_location=True,
                    cleaned_query="luxury condo",
                    confidence=0.9
                )
            )
            
            # Execute search
            result = engine.search(params)
            
            # Get the query that was sent to Elasticsearch
            call_args = mock_es_client.search.call_args
            query_body = call_args.kwargs['body']
            
            # Check that both retrievers exist
            retrievers = query_body['retriever']['rrf']['retrievers']
            assert len(retrievers) == 2
            
            # Check text retriever has filters
            text_retriever = retrievers[0]['standard']['query']
            assert 'bool' in text_retriever
            assert 'filter' in text_retriever['bool']
            
            # Check vector retriever has filters
            vector_retriever = retrievers[1]['knn']
            assert 'filter' in vector_retriever
    
    def test_no_location_no_filters(self, mock_es_client, mock_config):
        """Test that no filters are applied when no location is detected."""
        with patch('real_estate_search.demo_queries.hybrid_search.QueryEmbeddingService') as mock_embedding:
            mock_embedding_instance = Mock()
            mock_embedding_instance.embed_query.return_value = [0.1] * 1024
            mock_embedding.return_value = mock_embedding_instance
            
            engine = HybridSearchEngine(mock_es_client, mock_config)
            
            # Create params without location intent
            params = HybridSearchParams(
                query_text="modern kitchen with stainless steel appliances",
                size=10,
                location_intent=LocationIntent(
                    has_location=False,
                    cleaned_query="modern kitchen with stainless steel appliances",
                    confidence=0.0
                )
            )
            
            # Execute search
            result = engine.search(params)
            
            # Get the query that was sent to Elasticsearch
            call_args = mock_es_client.search.call_args
            query_body = call_args.kwargs['body']
            
            # Check that retrievers don't have filters
            retrievers = query_body['retriever']['rrf']['retrievers']
            
            # Text retriever should not have bool wrapper
            text_retriever = retrievers[0]['standard']['query']
            assert 'multi_match' in text_retriever
            assert 'bool' not in text_retriever
            
            # Vector retriever should not have filter
            vector_retriever = retrievers[1]['knn']
            assert 'filter' not in vector_retriever
    
    def test_filter_builder_integration(self):
        """Test LocationFilterBuilder creates correct Elasticsearch filters."""
        builder = LocationFilterBuilder()
        
        # Test with full location
        intent = LocationIntent(
            city="Seattle",
            state="Washington",
            neighborhood="Capitol Hill",
            zip_code="98102",
            has_location=True,
            cleaned_query="condo",
            confidence=0.95
        )
        
        filters = builder.build_filters(intent)
        
        # Should have 4 filters
        assert len(filters) == 4
        
        # Check each filter type
        filter_types = {f['term'].get(list(f['term'].keys())[0]) for f in filters}
        assert "Seattle" in filter_types
        assert "Washington" in filter_types
        assert "Capitol Hill" in filter_types
        assert "98102" in filter_types
    
    def test_cleaned_query_used_for_search(self, mock_es_client, mock_config):
        """Test that cleaned query is used for text and vector search."""
        with patch('real_estate_search.demo_queries.hybrid_search.QueryEmbeddingService') as mock_embedding:
            mock_embedding_instance = Mock()
            mock_embedding_instance.embed_query.return_value = [0.1] * 1024
            mock_embedding.return_value = mock_embedding_instance
            
            engine = HybridSearchEngine(mock_es_client, mock_config)
            
            # Create params with location that should be removed
            params = HybridSearchParams(
                query_text="2 bedroom apartment in Downtown Seattle",
                size=5,
                location_intent=LocationIntent(
                    city="Seattle",
                    neighborhood="Downtown",
                    has_location=True,
                    cleaned_query="2 bedroom apartment",
                    confidence=0.85
                )
            )
            
            # Execute search
            result = engine.search(params)
            
            # Verify embedding was created with cleaned query
            mock_embedding_instance.embed_query.assert_called_once_with("2 bedroom apartment")
            
            # Get the query sent to Elasticsearch
            call_args = mock_es_client.search.call_args
            query_body = call_args.kwargs['body']
            
            # Check text retriever uses cleaned query
            text_query = query_body['retriever']['rrf']['retrievers'][0]['standard']['query']
            multi_match = text_query['bool']['must']['multi_match'] if 'bool' in text_query else text_query['multi_match']
            assert multi_match['query'] == "2 bedroom apartment"