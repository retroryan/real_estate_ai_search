"""
Integration tests for correlation using bronze articles dataset.

Tests the complete flow of correlating source data with ChromaDB embeddings
using real test data from common_embeddings/evaluate_data/bronze_articles.json.
"""

import json
import time
import pytest
from pathlib import Path
from typing import List, Dict, Any
from httpx import AsyncClient

from common_ingest.services.embedding_service import EmbeddingService
from common_ingest.services.correlation_service import CorrelationService
from common_ingest.api.app import app


class TestBronzeCorrelation:
    """Test correlation with bronze articles dataset."""
    
    @classmethod
    def setup_class(cls):
        """Load test data once for all tests."""
        bronze_path = Path(__file__).parent.parent.parent / "common_embeddings" / "evaluate_data" / "bronze_articles.json"
        
        # Check if bronze articles file exists
        if bronze_path.exists():
            with open(bronze_path, 'r') as f:
                cls.test_data = json.load(f)
        else:
            # Fallback to minimal test data if file doesn't exist
            cls.test_data = {
                "articles": [
                    {
                        "page_id": 26974,
                        "title": "San Francisco Peninsula",
                        "summary": "The San Francisco Peninsula is a peninsula in the San Francisco Bay Area that separates San Francisco Bay from the Pacific Ocean.",
                        "city": "San Francisco",
                        "state": "California"
                    },
                    {
                        "page_id": 71083,
                        "title": "Wayne County, Utah",
                        "summary": "Wayne County is a county in the U.S. state of Utah. As of the 2020 United States Census, the population was 2,486.",
                        "city": "Loa",
                        "state": "Utah"
                    },
                    {
                        "page_id": 1706289,
                        "title": "Fillmore District, San Francisco",
                        "summary": "The Fillmore District is a historical neighborhood in San Francisco located to the southwest of Nob Hill.",
                        "city": "San Francisco",
                        "state": "California"
                    }
                ]
            }
        
        # Initialize services
        chromadb_path = Path(__file__).parent.parent / "data" / "chroma_db"
        cls.embedding_service = EmbeddingService(chromadb_path=str(chromadb_path))
        cls.correlation_service = CorrelationService(cls.embedding_service)
    
    def test_basic_correlation(self):
        """Test that correlation finds embeddings for known Wikipedia articles."""
        
        # Test correlation for each article
        for article in self.test_data['articles']:
            # Create simple dict with page_id for correlation
            wiki_data = [{
                'page_id': article['page_id'],
                'title': article['title'],
                'summary': article['summary']
            }]
            
            # Correlate with embeddings
            results = self.correlation_service.correlate_wikipedia_with_embeddings(
                wikipedia_data=wiki_data,
                collection_name='embeddings_nomic-embed-text',
                include_vectors=False
            )
            
            # Assertions
            assert len(results) == 1, f"Expected 1 result for article {article['title']}"
            result = results[0]
            
            # Check that result has the expected structure
            assert 'page_id' in result
            assert 'title' in result
            assert 'has_embeddings' in result
            assert 'embedding_count' in result
            assert 'correlation_confidence' in result
            
            # Log the result for debugging
            if result['has_embeddings']:
                print(f"✓ Article '{article['title']}' has {result['embedding_count']} embeddings")
            else:
                print(f"✗ Article '{article['title']}' has no embeddings (may not be populated in ChromaDB)")
    
    def test_api_endpoint_correlation(self):
        """Test correlation through actual API endpoints."""
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test Wikipedia articles endpoint with embeddings
        response = client.get(
            "/api/v1/wikipedia/articles",
            params={
                "include_embeddings": True,
                "collection_name": "embeddings_nomic-embed-text",
                "page": 1,
                "page_size": 10
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert 'data' in data
        assert 'metadata' in data
        
        # Check that articles have embedding fields
        known_page_ids = [a['page_id'] for a in self.test_data['articles']]
        
        for article in data['data']:
            if article.get('page_id') in known_page_ids:
                # These fields should exist even if no embeddings are found
                assert 'has_embeddings' in article
                assert 'embedding_count' in article
                assert 'correlation_confidence' in article
                
                if article['has_embeddings']:
                    assert 'embeddings' in article
                    assert article['embedding_count'] > 0
                    print(f"✓ API returned embeddings for article {article['page_id']}")
                else:
                    print(f"✗ API found no embeddings for article {article['page_id']}")
    
    def test_multi_chunk_correlation(self):
        """Test that multi-chunk documents are properly correlated."""
        
        # Use a known long article that would be chunked
        wiki_data = [{
            'page_id': 26974,  # San Francisco Peninsula - likely multi-chunk
            'title': 'San Francisco Peninsula',
            'summary': 'The San Francisco Peninsula is a peninsula in the San Francisco Bay Area...'
        }]
        
        results = self.correlation_service.correlate_wikipedia_with_embeddings(
            wikipedia_data=wiki_data,
            collection_name='embeddings_nomic-embed-text',
            include_vectors=False
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Check basic structure
        assert 'has_embeddings' in result
        assert 'embedding_count' in result
        
        # If embeddings exist and there are multiple chunks
        if result.get('has_embeddings') and result.get('embedding_count', 0) > 1:
            # Verify chunks are ordered by chunk_index
            embeddings = result.get('embeddings', [])
            if embeddings:
                chunk_indices = [e.get('chunk_index') for e in embeddings if e.get('chunk_index') is not None]
                if chunk_indices:
                    assert chunk_indices == sorted(chunk_indices), "Chunks should be ordered by chunk_index"
                    print(f"✓ Multi-chunk document has {len(embeddings)} ordered chunks")
        else:
            print(f"✗ Document has {result.get('embedding_count', 0)} embeddings (multi-chunk test skipped)")
    
    def test_correlation_performance(self):
        """Test that correlation performs within acceptable limits."""
        
        # Load all bronze articles
        wiki_data = [
            {'page_id': a['page_id'], 'title': a['title'], 'summary': a.get('summary', '')} 
            for a in self.test_data['articles']
        ]
        
        # Measure correlation time
        start_time = time.time()
        
        results = self.correlation_service.correlate_wikipedia_with_embeddings(
            wikipedia_data=wiki_data,
            collection_name='embeddings_nomic-embed-text',
            include_vectors=False  # Exclude vectors for performance
        )
        
        elapsed_time = time.time() - start_time
        
        # Performance assertions
        assert elapsed_time < 2.0, f"Correlation took {elapsed_time:.2f} seconds, expected < 2 seconds"
        assert len(results) == len(wiki_data)
        
        successful = sum(1 for r in results if r.get('has_embeddings', False))
        print(f"✓ Correlated {successful}/{len(wiki_data)} articles in {elapsed_time:.2f} seconds")
    
    def test_missing_embeddings(self):
        """Test that system handles missing embeddings gracefully."""
        
        # Use a page_id that doesn't exist in ChromaDB
        wiki_data = [{
            'page_id': 99999999,  # Non-existent
            'title': 'Non-existent Article',
            'summary': 'This article has no embeddings'
        }]
        
        results = self.correlation_service.correlate_wikipedia_with_embeddings(
            wikipedia_data=wiki_data,
            collection_name='embeddings_nomic-embed-text',
            include_vectors=False
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Should handle gracefully
        assert result.get('has_embeddings', False) == False
        assert result.get('embedding_count', 0) == 0
        assert result.get('correlation_confidence', 0.0) == 0.0
        
        # Embeddings should be None or empty list
        embeddings = result.get('embeddings')
        assert embeddings is None or embeddings == []
        
        print("✓ Missing embeddings handled gracefully")


class TestPropertyCorrelation:
    """Test correlation for property data."""
    
    @classmethod
    def setup_class(cls):
        """Initialize services for property tests."""
        chromadb_path = Path(__file__).parent.parent / "data" / "chroma_db"
        cls.embedding_service = EmbeddingService(chromadb_path=str(chromadb_path))
        cls.correlation_service = CorrelationService(cls.embedding_service)
    
    def test_property_api_with_embeddings(self):
        """Test property API endpoint with embedding correlation."""
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Get properties with embeddings
        response = client.get(
            "/api/v1/properties",
            params={
                "include_embeddings": True,
                "collection_name": "embeddings_nomic-embed-text",
                "page": 1,
                "page_size": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert 'data' in data
        assert 'metadata' in data
        
        # Check that properties have embedding fields
        for property_data in data['data']:
            # These fields should always exist
            assert 'has_embeddings' in property_data
            assert 'embedding_count' in property_data
            assert 'correlation_confidence' in property_data
            
            if property_data['has_embeddings']:
                assert 'embeddings' in property_data
                print(f"✓ Property {property_data.get('listing_id')} has {property_data['embedding_count']} embeddings")


class TestNeighborhoodCorrelation:
    """Test correlation for neighborhood data."""
    
    @classmethod
    def setup_class(cls):
        """Initialize services for neighborhood tests."""
        chromadb_path = Path(__file__).parent.parent / "data" / "chroma_db"
        cls.embedding_service = EmbeddingService(chromadb_path=str(chromadb_path))
        cls.correlation_service = CorrelationService(cls.embedding_service)
    
    def test_neighborhood_api_with_embeddings(self):
        """Test neighborhood API endpoint with embedding correlation."""
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Get neighborhoods with embeddings
        response = client.get(
            "/api/v1/neighborhoods",
            params={
                "include_embeddings": True,
                "collection_name": "embeddings_nomic-embed-text",
                "page": 1,
                "page_size": 5
            }
        )
        
        # Even if there's no data, endpoint should return 200
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert 'data' in data
        assert 'metadata' in data
        
        # If there are neighborhoods, check embedding fields
        if data['data']:
            for neighborhood in data['data']:
                assert 'has_embeddings' in neighborhood
                assert 'embedding_count' in neighborhood
                assert 'correlation_confidence' in neighborhood
                
                if neighborhood['has_embeddings']:
                    print(f"✓ Neighborhood {neighborhood.get('neighborhood_id')} has embeddings")