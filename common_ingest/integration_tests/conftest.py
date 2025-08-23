"""
Pytest configuration and fixtures for integration tests.

Provides shared fixtures and configuration for testing the FastAPI application
with real data and proper dependency injection.
"""

import pytest
from fastapi.testclient import TestClient

from ..api.app import create_app
from ..utils.logger import setup_logger

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