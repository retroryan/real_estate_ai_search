"""Test fixtures for SQUACK Pipeline V2."""

from pathlib import Path
import json
import tempfile
from typing import Generator
import pytest


@pytest.fixture
def sample_properties_data() -> list[dict]:
    """Sample property data for testing."""
    return [
        {
            "listing_id": "prop_001",
            "listing_price": 850000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 1800,
            "lot_size": 5000,
            "year_built": 1995,
            "property_type": "Single Family",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "description": "Beautiful home in great neighborhood"
        },
        {
            "listing_id": "prop_002",
            "listing_price": 1200000,
            "bedrooms": 4,
            "bathrooms": 3,
            "square_feet": 2400,
            "lot_size": 6000,
            "year_built": 2005,
            "property_type": "Condo",
            "address": "456 Oak Ave",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94103",
            "latitude": 37.7751,
            "longitude": -122.4180,
            "description": "Modern condo with city views"
        }
    ]


@pytest.fixture
def sample_neighborhoods_data() -> list[dict]:
    """Sample neighborhood data for testing."""
    return [
        {
            "neighborhood_id": "nhood_001",
            "name": "Mission District",
            "city": "San Francisco",
            "state": "CA",
            "population": 45000,
            "median_income": 85000,
            "median_home_price": 950000,
            "crime_rate": "low",
            "walkability_score": 95,
            "description": "Vibrant neighborhood with great food"
        },
        {
            "neighborhood_id": "nhood_002",
            "name": "Pacific Heights",
            "city": "San Francisco",
            "state": "CA",
            "population": 23000,
            "median_income": 150000,
            "median_home_price": 2500000,
            "crime_rate": "very_low",
            "walkability_score": 88,
            "description": "Upscale residential neighborhood"
        }
    ]


@pytest.fixture
def sample_wikipedia_data() -> list[dict]:
    """Sample Wikipedia article data for testing."""
    return [
        {
            "page_id": "wiki_001",
            "title": "San Francisco",
            "summary": "San Francisco is a city in California",
            "content": "San Francisco, officially the City and County of San Francisco...",
            "categories": ["Cities in California", "San Francisco Bay Area"],
            "url": "https://en.wikipedia.org/wiki/San_Francisco"
        },
        {
            "page_id": "wiki_002",
            "title": "Golden Gate Bridge",
            "summary": "The Golden Gate Bridge is a suspension bridge",
            "content": "The Golden Gate Bridge is a suspension bridge spanning the Golden Gate...",
            "categories": ["Bridges in California", "San Francisco landmarks"],
            "url": "https://en.wikipedia.org/wiki/Golden_Gate_Bridge"
        }
    ]


@pytest.fixture
def temp_json_file() -> Generator[Path, None, None]:
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def properties_json_file(temp_json_file: Path, sample_properties_data: list[dict]) -> Path:
    """Create a temporary properties JSON file."""
    with open(temp_json_file, 'w') as f:
        json.dump(sample_properties_data, f)
    return temp_json_file


@pytest.fixture
def neighborhoods_json_file(temp_json_file: Path, sample_neighborhoods_data: list[dict]) -> Path:
    """Create a temporary neighborhoods JSON file."""
    with open(temp_json_file, 'w') as f:
        json.dump(sample_neighborhoods_data, f)
    return temp_json_file


@pytest.fixture
def wikipedia_json_file(temp_json_file: Path, sample_wikipedia_data: list[dict]) -> Path:
    """Create a temporary Wikipedia JSON file."""
    with open(temp_json_file, 'w') as f:
        json.dump(sample_wikipedia_data, f)
    return temp_json_file