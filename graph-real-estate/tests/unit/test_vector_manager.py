"""Unit tests for PropertyVectorManager with mocked dependencies"""

import pytest
from unittest.mock import Mock, MagicMock
import numpy as np
from neo4j import Driver

from src.vectors.vector_manager import PropertyVectorManager
from src.core.query_executor import QueryExecutor


class TestPropertyVectorManager:
    """Test PropertyVectorManager with mocked dependencies"""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver"""
        return Mock(spec=Driver)
    
    @pytest.fixture
    def mock_query_executor(self):
        """Create mock query executor"""
        mock = Mock(spec=QueryExecutor)
        mock.execute_read.return_value = [
            {
                'listing_id': 'prop1',
                'embedding': [0.1] * 384,
                'address': '123 Main St',
                'city': 'San Francisco',
                'neighborhood': 'Downtown',
                'price': 500000,
                'bedrooms': 3,
                'bathrooms': 2,
                'square_feet': 1500,
                'description': 'Nice property'
            },
            {
                'listing_id': 'prop2',
                'embedding': [0.2] * 384,
                'address': '456 Oak Ave',
                'city': 'San Francisco',
                'neighborhood': 'Mission',
                'price': 600000,
                'bedrooms': 2,
                'bathrooms': 1,
                'square_feet': 1200,
                'description': 'Cozy place'
            }
        ]
        mock.execute_write.return_value = [{'id': 'prop1'}]
        return mock
    
    @pytest.fixture
    def vector_manager(self, mock_driver, mock_query_executor):
        """Create PropertyVectorManager with mocked dependencies"""
        return PropertyVectorManager(
            driver=mock_driver,
            query_executor=mock_query_executor
        )
    
    def test_initialization(self, vector_manager, mock_driver, mock_query_executor):
        """Test vector manager is initialized with injected dependencies"""
        assert vector_manager.driver == mock_driver
        assert vector_manager.query_executor == mock_query_executor
    
    def test_vector_search_basic(self, vector_manager, mock_query_executor):
        """Test basic vector search"""
        query_embedding = [0.15] * 384
        results = vector_manager.vector_search(query_embedding, top_k=2)
        
        assert len(results) == 2
        assert results[0]['listing_id'] == 'prop1'
        assert 'score' in results[0]
        assert 0 <= results[0]['score'] <= 1.0
        
        mock_query_executor.execute_read.assert_called_once()
    
    def test_vector_search_with_filters(self, vector_manager, mock_query_executor):
        """Test vector search with filters"""
        query_embedding = [0.1] * 384
        filters = {
            'city': 'San Francisco',
            'price_min': 400000,
            'price_max': 700000,
            'bedrooms_min': 2
        }
        
        results = vector_manager.vector_search(query_embedding, filters=filters)
        
        # Check that filter parameters were included in query
        call_args = mock_query_executor.execute_read.call_args
        params = call_args[0][1]
        assert params['city'] == 'San Francisco'
        assert params['price_min'] == 400000
        assert params['price_max'] == 700000
        assert params['bedrooms_min'] == 2
    
    def test_vector_search_min_score(self, vector_manager, mock_query_executor):
        """Test vector search with minimum score threshold"""
        query_embedding = [0.5] * 384
        results = vector_manager.vector_search(query_embedding, min_score=0.8)
        
        # Only high-scoring results should be returned
        for result in results:
            assert result['score'] >= 0.8 or len(results) == 0
    
    def test_vector_search_empty_results(self, vector_manager, mock_query_executor):
        """Test vector search with no results"""
        mock_query_executor.execute_read.return_value = []
        
        query_embedding = [0.1] * 384
        results = vector_manager.vector_search(query_embedding)
        
        assert len(results) == 0
    
    def test_store_embedding(self, vector_manager, mock_query_executor):
        """Test storing an embedding"""
        success = vector_manager.store_embedding(
            node_id='prop1',
            embedding=[0.1] * 384,
            metadata={'model': 'test', 'version': '1.0'}
        )
        
        assert success == True
        mock_query_executor.execute_write.assert_called_once()
        
        call_args = mock_query_executor.execute_write.call_args
        params = call_args[0][1]
        assert params['node_id'] == 'prop1'
        assert len(params['embedding']) == 384
        assert params['metadata']['model'] == 'test'
    
    def test_store_embedding_failure(self, vector_manager, mock_query_executor):
        """Test handling store embedding failure"""
        mock_query_executor.execute_write.side_effect = Exception("Database error")
        
        success = vector_manager.store_embedding(
            node_id='prop1',
            embedding=[0.1] * 384,
            metadata={}
        )
        
        assert success == False
    
    def test_get_embedding(self, vector_manager, mock_query_executor):
        """Test retrieving an embedding"""
        mock_query_executor.execute_read.return_value = [
            {'embedding': [0.3] * 384}
        ]
        
        embedding = vector_manager.get_embedding('prop1')
        
        assert embedding is not None
        assert len(embedding) == 384
        assert embedding[0] == 0.3
        
        call_args = mock_query_executor.execute_read.call_args
        assert call_args[0][1]['node_id'] == 'prop1'
    
    def test_get_embedding_not_found(self, vector_manager, mock_query_executor):
        """Test retrieving non-existent embedding"""
        mock_query_executor.execute_read.return_value = []
        
        embedding = vector_manager.get_embedding('nonexistent')
        
        assert embedding is None
    
    def test_create_vector_index(self, vector_manager, mock_query_executor):
        """Test creating vector index"""
        success = vector_manager.create_vector_index(dimension=384)
        
        assert success == True
        mock_query_executor.execute_write.assert_called_once()
    
    def test_create_vector_index_failure(self, vector_manager, mock_query_executor):
        """Test handling vector index creation failure"""
        mock_query_executor.execute_write.side_effect = Exception("Index error")
        
        success = vector_manager.create_vector_index()
        
        assert success == False
    
    def test_cosine_similarity(self, vector_manager):
        """Test cosine similarity calculation"""
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([1, 0, 0])
        similarity = vector_manager._cosine_similarity(vec1, vec2)
        assert similarity == 1.0
        
        vec3 = np.array([0, 1, 0])
        similarity = vector_manager._cosine_similarity(vec1, vec3)
        assert similarity == 0.0
        
        vec4 = np.array([1, 1, 0])
        similarity = vector_manager._cosine_similarity(vec1, vec4)
        assert 0.7 < similarity < 0.8  # ~0.707
    
    def test_cosine_similarity_zero_vectors(self, vector_manager):
        """Test cosine similarity with zero vectors"""
        vec1 = np.array([0, 0, 0])
        vec2 = np.array([1, 1, 1])
        
        similarity = vector_manager._cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    def test_find_similar_properties(self, vector_manager, mock_query_executor):
        """Test finding similar properties"""
        # First call gets the property's embedding
        mock_query_executor.execute_read.side_effect = [
            [{'embedding': [0.1] * 384}],  # get_embedding result
            [  # vector_search results
                {
                    'listing_id': 'prop1',  # The query property itself
                    'embedding': [0.1] * 384,
                    'address': '123 Main St',
                    'city': 'SF',
                    'neighborhood': 'Downtown',
                    'price': 500000
                },
                {
                    'listing_id': 'prop2',
                    'embedding': [0.15] * 384,
                    'address': '456 Oak Ave',
                    'city': 'SF',
                    'neighborhood': 'Mission',
                    'price': 600000
                },
                {
                    'listing_id': 'prop3',
                    'embedding': [0.12] * 384,
                    'address': '789 Pine St',
                    'city': 'SF',
                    'neighborhood': 'SOMA',
                    'price': 550000
                }
            ]
        ]
        
        similar = vector_manager.find_similar_properties('prop1', top_k=2)
        
        assert len(similar) == 2
        # Should exclude the property itself
        assert all(r['listing_id'] != 'prop1' for r in similar)
        assert similar[0]['listing_id'] == 'prop2'
    
    def test_find_similar_properties_no_embedding(self, vector_manager, mock_query_executor):
        """Test finding similar properties when no embedding exists"""
        mock_query_executor.execute_read.return_value = []
        
        similar = vector_manager.find_similar_properties('nonexistent')
        
        assert len(similar) == 0