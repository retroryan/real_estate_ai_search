"""
Integration test for hybrid search functionality.

Tests the end-to-end functionality of hybrid search combining vector and text
search with Elasticsearch RRF.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock

from real_estate_search.config.config import AppConfig
from real_estate_search.demo_queries.hybrid_search import HybridSearchEngine, HybridSearchParams

# Set up logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestHybridSearchIntegration:
    """Integration tests for hybrid search functionality."""
    
    @pytest.fixture
    def app_config(self):
        """Load the full application configuration."""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            config = AppConfig.from_yaml(config_path)
        else:
            config = AppConfig.load()
        
        # Check if API key is available for embedding service
        try:
            _ = config.embedding.api_key
        except ValueError:
            pytest.skip("VOYAGE_API_KEY not set, skipping integration test")
        
        return config
    
    @pytest.fixture
    def mock_es_client(self):
        """Mock Elasticsearch client with sample response."""
        mock_client = Mock()
        
        # Mock successful RRF response
        mock_response = {
            'hits': {
                'total': {'value': 5},
                'hits': [
                    {
                        '_score': 0.95,
                        '_source': {
                            'listing_id': 'prop_001',
                            'property_type': 'single-family',
                            'price': 850000,
                            'bedrooms': 3,
                            'bathrooms': 2.0,
                            'square_feet': 1800,
                            'address': {
                                'street': '123 Main St',
                                'city': 'San Francisco',
                                'state': 'CA'
                            },
                            'description': 'Modern kitchen with stainless steel appliances',
                            'features': ['modern', 'updated'],
                            'amenities': ['kitchen', 'appliances']
                        }
                    },
                    {
                        '_score': 0.87,
                        '_source': {
                            'listing_id': 'prop_002',
                            'property_type': 'condo',
                            'price': 720000,
                            'bedrooms': 2,
                            'bathrooms': 2.0,
                            'square_feet': 1200,
                            'address': {
                                'street': '456 Oak Ave',
                                'city': 'San Francisco',
                                'state': 'CA'
                            },
                            'description': 'Contemporary home with updated kitchen',
                            'features': ['contemporary', 'updated'],
                            'amenities': ['kitchen', 'modern']
                        }
                    }
                ]
            },
            'took': 25
        }
        
        mock_client.search.return_value = mock_response
        return mock_client
    
    def test_hybrid_search_engine_initialization(self, mock_es_client, app_config):
        """Test hybrid search engine initializes correctly."""
        engine = HybridSearchEngine(mock_es_client, app_config)
        
        assert engine.es_client == mock_es_client
        assert engine.config == app_config
        assert engine.embedding_service is not None
    
    def test_hybrid_search_params_validation(self):
        """Test hybrid search parameters validate correctly."""
        # Valid parameters
        params = HybridSearchParams(
            query_text="modern kitchen with appliances",
            size=10,
            rank_constant=60,
            rank_window_size=100
        )
        
        assert params.query_text == "modern kitchen with appliances"
        assert params.size == 10
        assert params.rank_constant == 60
        assert params.rank_window_size == 100
        assert params.text_boost == 1.0
        assert params.vector_boost == 1.0
    
    def test_rrf_query_structure(self, mock_es_client, app_config):
        """Test that RRF query is built with correct structure."""
        engine = HybridSearchEngine(mock_es_client, app_config)
        
        params = HybridSearchParams(
            query_text="modern kitchen",
            size=5,
            rank_constant=60,
            rank_window_size=100
        )
        
        # Mock embedding generation
        mock_vector = [0.1] * 1024
        query = engine._build_rrf_query(params, mock_vector, params.query_text)
        
        # Verify RRF structure
        assert 'retriever' in query
        assert 'rrf' in query['retriever']
        assert 'retrievers' in query['retriever']['rrf']
        
        retrievers = query['retriever']['rrf']['retrievers']
        assert len(retrievers) == 2
        
        # Check text retriever
        text_retriever = retrievers[0]
        assert 'standard' in text_retriever
        assert 'multi_match' in text_retriever['standard']['query']
        
        # Check vector retriever
        vector_retriever = retrievers[1]
        assert 'knn' in vector_retriever
        assert vector_retriever['knn']['field'] == 'embedding'
        assert vector_retriever['knn']['query_vector'] == mock_vector
        
        # Check RRF parameters
        rrf_config = query['retriever']['rrf']
        assert rrf_config['rank_constant'] == 60
        assert rrf_config['rank_window_size'] == 100
    
    @pytest.mark.skip(reason="Requires live Elasticsearch and embedding service")
    def test_end_to_end_hybrid_search(self, mock_es_client, app_config):
        """Test complete hybrid search flow."""
        engine = HybridSearchEngine(mock_es_client, app_config)
        
        params = HybridSearchParams(
            query_text="modern kitchen with stainless steel appliances",
            size=5
        )
        
        result = engine.search(params)
        
        # Verify result structure
        assert result.query == params.query_text
        assert result.total_hits > 0
        assert len(result.results) <= params.size
        assert result.execution_time_ms > 0
        
        # Verify individual results
        for search_result in result.results:
            assert search_result.listing_id is not None
            assert search_result.hybrid_score > 0
            assert search_result.property_data is not None
        
        # Verify metadata
        assert result.search_metadata['rrf_used'] is True
        assert result.search_metadata['total_retrievers'] == 2