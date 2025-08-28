"""
Integration test for query embedding service.

Tests the end-to-end functionality of generating query embeddings
for semantic search using the Voyage AI API.
"""

import os
import pytest
from typing import List
import logging
from pathlib import Path

from real_estate_search.config.config import AppConfig
from real_estate_search.embeddings import (
    EmbeddingConfig,
    QueryEmbeddingService,
    ConfigurationError,
    EmbeddingGenerationError
)

# Set up logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEmbeddingServiceIntegration:
    """Integration tests for the query embedding service."""
    
    @pytest.fixture
    def app_config(self):
        """Load the full application configuration including embedding settings."""
        # Try to load from config.yaml with .env override
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            config = AppConfig.from_yaml(config_path)
        else:
            # Fall back to loading from environment only
            config = AppConfig.load()
        
        # Check if API key is available through the config
        try:
            # This will validate the API key is present
            _ = config.embedding.api_key
        except ValueError:
            pytest.skip("VOYAGE_API_KEY not set in .env or environment, skipping integration test")
        
        return config
    
    @pytest.fixture
    def config(self, app_config):
        """Extract embedding configuration from app config."""
        return app_config.embedding
    
    @pytest.fixture
    def service(self, config):
        """Create and initialize embedding service."""
        service = QueryEmbeddingService(config=config)
        service.initialize()
        yield service
        service.close()
    
    def test_service_initialization(self, config):
        """Test that the service initializes correctly with valid config."""
        service = QueryEmbeddingService(config=config)
        assert not service._initialized
        
        service.initialize()
        assert service._initialized
        assert service._embed_model is not None
        
        # Test idempotent initialization
        service.initialize()
        assert service._initialized
        
        service.close()
        assert not service._initialized
        assert service._embed_model is None
    
    def test_single_query_embedding(self, service):
        """Test generating embedding for a single query."""
        query = "modern home with mountain views and open floor plan"
        
        embedding = service.embed_query(query)
        
        # Verify embedding properties
        assert isinstance(embedding, list)
        assert len(embedding) == 1024  # Voyage-3 dimension
        assert all(isinstance(x, float) for x in embedding)
        
        # Verify values are in reasonable range
        assert all(-10 <= x <= 10 for x in embedding)
        
        # Verify different queries produce different embeddings
        query2 = "cozy cottage near the beach"
        embedding2 = service.embed_query(query2)
        assert embedding != embedding2
    
    def test_batch_query_embeddings(self, service):
        """Test generating embeddings for multiple queries."""
        queries = [
            "luxury condo with city views",
            "family home near good schools",
            "investment property with rental potential",
            "fixer-upper in up-and-coming neighborhood"
        ]
        
        embeddings = service.batch_embed_queries(queries)
        
        # Verify batch results
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(queries)
        
        # Verify each embedding
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == 1024
            assert all(isinstance(x, float) for x in embedding)
        
        # Verify embeddings are different
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                assert embeddings[i] != embeddings[j]
    
    def test_semantic_similarity(self, service):
        """Test that semantically similar queries produce similar embeddings."""
        # Similar queries
        query1 = "modern apartment with gym and pool"
        query2 = "contemporary condo with fitness center and swimming pool"
        query3 = "rural farmhouse with acreage"
        
        embedding1 = service.embed_query(query1)
        embedding2 = service.embed_query(query2)
        embedding3 = service.embed_query(query3)
        
        # Calculate cosine similarity
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot_product / (norm_a * norm_b)
        
        sim_12 = cosine_similarity(embedding1, embedding2)
        sim_13 = cosine_similarity(embedding1, embedding3)
        sim_23 = cosine_similarity(embedding2, embedding3)
        
        logger.info(f"Similarity between similar queries (1-2): {sim_12:.3f}")
        logger.info(f"Similarity between different queries (1-3): {sim_13:.3f}")
        logger.info(f"Similarity between different queries (2-3): {sim_23:.3f}")
        
        # Similar queries should have higher similarity
        assert sim_12 > sim_13
        assert sim_12 > sim_23
        
        # All should be valid cosine similarities
        assert -1 <= sim_12 <= 1
        assert -1 <= sim_13 <= 1
        assert -1 <= sim_23 <= 1
    
    def test_empty_query_handling(self, service):
        """Test handling of empty or invalid queries."""
        with pytest.raises(EmbeddingGenerationError) as exc_info:
            service.embed_query("")
        assert "Query cannot be empty" in str(exc_info.value)
        
        with pytest.raises(EmbeddingGenerationError) as exc_info:
            service.embed_query("   ")
        assert "Query cannot be empty" in str(exc_info.value)
    
    def test_batch_with_empty_queries(self, service):
        """Test batch processing with empty queries."""
        # All empty should raise error
        with pytest.raises(EmbeddingGenerationError) as exc_info:
            service.batch_embed_queries(["", "   "])
        assert "No valid queries" in str(exc_info.value)
        
        # Empty list should return empty list
        result = service.batch_embed_queries([])
        assert result == []
    
    def test_context_manager(self, config):
        """Test using service as context manager."""
        with QueryEmbeddingService(config=config) as service:
            assert service._initialized
            embedding = service.embed_query("test query")
            assert len(embedding) == 1024
        
        # Service should be closed after context
        assert not service._initialized
    
    def test_uninitialized_service_error(self, config):
        """Test that using uninitialized service raises proper error."""
        service = QueryEmbeddingService(config=config)
        
        with pytest.raises(Exception) as exc_info:
            service.embed_query("test query")
        assert "not initialized" in str(exc_info.value).lower()
    
    def test_real_estate_queries(self, service):
        """Test with actual real estate search queries."""
        real_estate_queries = [
            "3 bedroom house under 500k",
            "waterfront property with boat dock",
            "downtown loft with parking",
            "historic home in walkable neighborhood",
            "new construction with smart home features",
            "pet-friendly apartment near parks",
            "luxury estate with mountain views",
            "starter home for first-time buyers"
        ]
        
        embeddings = service.batch_embed_queries(real_estate_queries)
        
        # All should generate valid embeddings
        assert len(embeddings) == len(real_estate_queries)
        for embedding in embeddings:
            assert len(embedding) == 1024
        
        logger.info(f"Successfully generated embeddings for {len(real_estate_queries)} real estate queries")


def test_api_key_validation():
    """Test that service properly validates API key requirement at initialization.
    
    The EmbeddingConfig allows None for api_key (for flexibility with AppConfig),
    but the QueryEmbeddingService validates the key when initialized.
    """
    # Create config without API key
    config = EmbeddingConfig(api_key=None)
    assert config.api_key is None  # Config allows None
    
    # But service should fail to initialize without key
    service = QueryEmbeddingService(config=config)
    
    with pytest.raises(ConfigurationError) as exc_info:
        service.initialize()
    
    assert "VOYAGE_API_KEY is required" in str(exc_info.value)
    logger.info(f"✓ Service properly validates API key at initialization")


def test_config_from_yaml():
    """Test that configuration loads correctly from YAML and .env."""
    # Try to load the app config which should read from config.yaml and .env
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        pytest.skip("config.yaml not found")
    
    try:
        app_config = AppConfig.from_yaml(config_path)
        
        # Check embedding configuration is loaded
        assert app_config.embedding is not None
        assert app_config.embedding.provider.value == "voyage"
        assert app_config.embedding.model_name == "voyage-3"
        assert app_config.embedding.dimension == 1024
        
        logger.info(f"Successfully loaded config from {config_path}")
        logger.info(f"Embedding provider: {app_config.embedding.provider}")
        logger.info(f"Model: {app_config.embedding.model_name}")
        
        # If API key is present, we can test service creation
        try:
            api_key = app_config.embedding.api_key
            service = QueryEmbeddingService(config=app_config.embedding)
            logger.info("✓ Service can be created with config from YAML + .env")
        except ValueError:
            logger.info("⚠️  API key not set in .env, but config structure is valid")
            
    except Exception as e:
        pytest.fail(f"Failed to load config from YAML: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])