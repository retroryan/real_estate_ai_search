"""Configuration and fixtures for API client integration tests."""

import os
import logging
from pathlib import Path

import pytest
import httpx

from ..config import APIClientConfig  
from ..config_loader import ConfigLoader
from ..property_client import PropertyAPIClient
from ..wikipedia_client import WikipediaAPIClient


@pytest.fixture(scope="session")
def api_base_url():
    """Get API base URL from environment or default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session") 
def api_timeout():
    """Get API timeout from environment or default."""
    return int(os.getenv("API_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def integration_logger():
    """Create logger for integration tests."""
    logger = logging.getLogger("integration_tests")
    logger.setLevel(logging.INFO)
    
    # Add console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


@pytest.fixture(scope="session")
def property_api_config(api_base_url, api_timeout):
    """Create configuration for Property API client."""
    return APIClientConfig(
        base_url=f"{api_base_url}/api/v1",
        timeout=api_timeout
    )


@pytest.fixture(scope="session") 
def wikipedia_api_config(api_base_url, api_timeout):
    """Create configuration for Wikipedia API client."""
    return APIClientConfig(
        base_url=f"{api_base_url}/api/v1/wikipedia",
        timeout=api_timeout
    )


@pytest.fixture(scope="session")
def property_api_client(property_api_config, integration_logger):
    """Create Property API client for integration tests."""
    return PropertyAPIClient(property_api_config, integration_logger)


@pytest.fixture(scope="session")
def wikipedia_api_client(wikipedia_api_config, integration_logger):
    """Create Wikipedia API client for integration tests."""
    return WikipediaAPIClient(wikipedia_api_config, integration_logger)


@pytest.fixture(scope="session")
def api_server_check(api_base_url):
    """Check that API server is running before tests."""
    try:
        response = httpx.get(f"{api_base_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"API server not available at {api_base_url} (status: {response.status_code})")
    except Exception as e:
        pytest.skip(f"API server not available at {api_base_url}: {e}")
    
    return True


@pytest.fixture
def skip_if_no_data():
    """Skip test if no data available in the API."""
    def _skip_if_no_data(client_method, *args, **kwargs):
        try:
            result = client_method(*args, **kwargs)
            if not result:
                pytest.skip("No data available for this test")
            return result
        except Exception as e:
            pytest.skip(f"Data not available: {e}")
    
    return _skip_if_no_data