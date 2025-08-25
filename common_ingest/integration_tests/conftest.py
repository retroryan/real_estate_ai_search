"""
Pytest configuration and fixtures for integration tests.

Provides shared fixtures and configuration for testing the FastAPI application
with real data and proper dependency injection.
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from ..api.app import create_app
from ..utils.logger import setup_logger
from ..services.embedding_service import EmbeddingService
from ..services.correlation_service import CorrelationService

logger = setup_logger(__name__)


@pytest.fixture(scope="session")
def test_app():
    """
    Create a FastAPI application instance for testing.
    
    Uses the same configuration as the production app but in test mode.
    
    Returns:
        FastAPI: Configured FastAPI application for testing
    """
    logger.info("Creating test FastAPI application")
    app = create_app()
    return app


@pytest.fixture(scope="session")
def test_client(test_app):
    """
    Create a test client for making HTTP requests to the API.
    
    Args:
        test_app: FastAPI application fixture
        
    Returns:
        TestClient: FastAPI test client for making HTTP requests
    """
    logger.info("Creating test client")
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="session") 
def sample_property_id():
    """
    Provide a known property ID for testing single property endpoints.
    
    This ID should exist in the test data for reliable testing.
    
    Returns:
        str: A property ID that exists in the test data
    """
    # This will be validated during test execution
    return "prop-oak-125"


@pytest.fixture(scope="session")
def sample_neighborhood_id():
    """
    Provide a known neighborhood ID for testing single neighborhood endpoints.
    
    This ID should exist in the test data for reliable testing.
    
    Returns:
        str: A neighborhood ID that exists in the test data
    """
    # This will be validated during test execution
    return "sf-pac-heights-001"


@pytest.fixture(scope="session")
def valid_cities():
    """
    Provide a list of valid city names for testing city filtering.
    
    Returns:
        list: List of city names that exist in the test data
    """
    return ["San Francisco", "Park City", "Oakland"]


@pytest.fixture(scope="session")
def invalid_city():
    """
    Provide an invalid city name for testing error handling.
    
    Returns:
        str: A city name that should not exist in the test data
    """
    return "NonExistentCity"


@pytest.fixture(scope="session")
def bronze_articles_data():
    """
    Load bronze articles test data for correlation testing.
    
    Returns:
        dict: Bronze articles test data with Wikipedia pages
    """
    bronze_path = Path(__file__).parent.parent.parent / "common_embeddings" / "evaluate_data" / "bronze_articles.json"
    
    if bronze_path.exists():
        with open(bronze_path, 'r') as f:
            return json.load(f)
    else:
        return {
            "articles": [
                {
                    "page_id": 26974,
                    "title": "San Francisco Peninsula",
                    "summary": "The San Francisco Peninsula is a peninsula in the San Francisco Bay Area.",
                    "city": "San Francisco",
                    "state": "California"
                },
                {
                    "page_id": 71083,
                    "title": "Wayne County, Utah",
                    "summary": "Wayne County is a county in the U.S. state of Utah.",
                    "city": "Loa", 
                    "state": "Utah"
                },
                {
                    "page_id": 1706289,
                    "title": "Fillmore District, San Francisco",
                    "summary": "The Fillmore District is a historical neighborhood in San Francisco.",
                    "city": "San Francisco",
                    "state": "California"
                }
            ],
            "metadata": {
                "total_articles": 3,
                "dataset_type": "bronze",
                "description": "Small test dataset for quick evaluation"
            }
        }


@pytest.fixture(scope="session")
def embedding_service():
    """
    Create an embedding service instance for testing.
    
    Returns:
        EmbeddingService: Service for reading ChromaDB collections
    """
    chromadb_path = Path(__file__).parent.parent / "data" / "chroma_db"
    return EmbeddingService(chromadb_path=str(chromadb_path))


@pytest.fixture(scope="session")
def correlation_service(embedding_service):
    """
    Create a correlation service instance for testing.
    
    Args:
        embedding_service: EmbeddingService fixture
        
    Returns:
        CorrelationService: Service for correlating embeddings with source data
    """
    return CorrelationService(embedding_service)


@pytest.fixture(scope="session")
def test_collection_name():
    """
    Provide the ChromaDB collection name for testing.
    
    Returns:
        str: Collection name to use for correlation tests
    """
    return "embeddings_nomic-embed-text"