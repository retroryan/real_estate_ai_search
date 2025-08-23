"""Unit tests for HybridPropertySearch with mocked dependencies"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from src.vectors.hybrid_search import HybridPropertySearch, SearchResult
from src.core.query_executor import QueryExecutor
from src.core.config import SearchConfig
from src.vectors.embedding_pipeline import PropertyEmbeddingPipeline
from src.vectors.vector_manager import PropertyVectorManager


class TestHybridPropertySearch:
    """Test HybridPropertySearch with mocked dependencies"""
    
    @pytest.fixture
    def mock_query_executor(self):
        """Create mock query executor"""
        mock = Mock(spec=QueryExecutor)
        mock.execute_read.return_value = [
            {
                'similarity_connections': 5,
                'neighborhood_connections': 25,
                'feature_connections': 10,
                'feature_count': 8,
                'proximity_connections': 15
            }
        ]
        return mock
    
    @pytest.fixture
    def mock_embedding_pipeline(self):
        """Create mock embedding pipeline"""
        mock = Mock(spec=PropertyEmbeddingPipeline)
        mock.embed_model = Mock()
        mock.embed_model.get_text_embedding.return_value = [0.1] * 384
        return mock
    
    @pytest.fixture
    def mock_vector_manager(self):
        """Create mock vector manager"""
        mock = Mock(spec=PropertyVectorManager)
        mock.vector_search.return_value = [
            {
                'listing_id': 'prop1',
                'score': 0.85,
                'address': '123 Main St',
                'city': 'San Francisco',
                'neighborhood': 'Downtown',
                'price': 500000,
                'bedrooms': 3,
                'bathrooms': 2,
                'square_feet': 1500,
                'description': 'Beautiful property'
            },
            {
                'listing_id': 'prop2',
                'score': 0.75,
                'address': '456 Oak Ave',
                'city': 'San Francisco',
                'neighborhood': 'Mission',
                'price': 600000,
                'bedrooms': 2,
                'bathrooms': 1,
                'square_feet': 1200,
                'description': 'Cozy apartment'
            }
        ]
        return mock
    
    @pytest.fixture
    def mock_config(self):
        """Create mock search config"""
        config = Mock(spec=SearchConfig)
        config.default_top_k = 10
        config.use_graph_boost = True
        config.min_similarity = 0.5
        config.vector_weight = 0.6
        config.graph_weight = 0.3
        config.features_weight = 0.1
        return config
    
    @pytest.fixture
    def hybrid_search(self, mock_query_executor, mock_embedding_pipeline, 
                     mock_vector_manager, mock_config):
        """Create HybridPropertySearch with mocked dependencies"""
        return HybridPropertySearch(
            query_executor=mock_query_executor,
            embedding_pipeline=mock_embedding_pipeline,
            vector_manager=mock_vector_manager,
            config=mock_config
        )
    
    def test_initialization(self, hybrid_search, mock_query_executor, mock_config):
        """Test hybrid search is initialized with injected dependencies"""
        assert hybrid_search.query_executor == mock_query_executor
        assert hybrid_search.embedding_pipeline is not None
        assert hybrid_search.vector_manager is not None
        assert hybrid_search.config == mock_config
    
    def test_search_basic(self, hybrid_search, mock_embedding_pipeline, mock_vector_manager):
        """Test basic search functionality"""
        results = hybrid_search.search("3 bedroom house in San Francisco")
        
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        assert results[0].listing_id == 'prop1'
        assert results[0].vector_score == 0.85
        
        mock_embedding_pipeline.embed_model.get_text_embedding.assert_called_once()
        mock_vector_manager.vector_search.assert_called_once()
    
    def test_search_with_filters(self, hybrid_search, mock_vector_manager):
        """Test search with filters"""
        filters = {
            'city': 'San Francisco',
            'price_min': 400000,
            'price_max': 700000
        }
        
        results = hybrid_search.search("modern apartment", filters=filters)
        
        # Verify filters were passed to vector search
        call_args = mock_vector_manager.vector_search.call_args
        assert call_args[1]['filters'] == filters
    
    def test_search_custom_top_k(self, hybrid_search, mock_vector_manager):
        """Test search with custom top_k"""
        results = hybrid_search.search("house", top_k=5)
        
        # Results should be limited to 5
        assert len(results) <= 5
    
    def test_graph_metrics_calculation(self, hybrid_search, mock_query_executor):
        """Test graph metrics are properly calculated"""
        metrics = hybrid_search._get_graph_metrics('prop1')
        
        assert 'centrality_score' in metrics
        assert metrics['similarity_connections'] == 5
        assert metrics['neighborhood_connections'] == 25
        assert metrics['feature_count'] == 8
        assert 0 <= metrics['centrality_score'] <= 1.0
        
        mock_query_executor.execute_read.assert_called()
    
    def test_combined_score_calculation(self, hybrid_search):
        """Test combined score calculation"""
        graph_metrics = {
            'feature_count': 10,
            'neighborhood_connections': 35,
            'similarity_connections': 7
        }
        
        score = hybrid_search._calculate_combined_score(
            vector_score=0.8,
            graph_score=0.6,
            graph_metrics=graph_metrics
        )
        
        # Score should be boosted due to high connections
        assert score > 0.7  # Base combined score
        assert score <= 1.0  # Capped at 1.0
    
    def test_get_similar_properties(self, hybrid_search, mock_query_executor):
        """Test getting similar properties"""
        mock_query_executor.execute_read.return_value = [
            {'listing_id': 'prop2'},
            {'listing_id': 'prop3'},
            {'listing_id': 'prop4'}
        ]
        
        similar = hybrid_search._get_similar_properties('prop1', limit=3)
        
        assert len(similar) == 3
        assert 'prop2' in similar
        assert 'prop3' in similar
        mock_query_executor.execute_read.assert_called()
    
    def test_get_property_features(self, hybrid_search, mock_query_executor):
        """Test getting property features"""
        mock_query_executor.execute_read.return_value = [
            {'feature': 'pool'},
            {'feature': 'garage'},
            {'feature': 'fireplace'}
        ]
        
        features = hybrid_search._get_property_features('prop1')
        
        assert len(features) == 3
        assert 'pool' in features
        assert 'garage' in features
        mock_query_executor.execute_read.assert_called()
    
    def test_search_no_results(self, hybrid_search, mock_vector_manager):
        """Test search when no results found"""
        mock_vector_manager.vector_search.return_value = []
        
        results = hybrid_search.search("nonexistent property")
        
        assert len(results) == 0
    
    def test_search_without_graph_boost(self, hybrid_search, mock_vector_manager):
        """Test search without graph boosting"""
        results = hybrid_search.search("house", use_graph_boost=False)
        
        # Combined score should equal vector score when boost is off
        assert results[0].combined_score == results[0].vector_score