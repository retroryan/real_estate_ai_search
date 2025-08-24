# Common Ingestion Module

A unified data loading and enrichment module for real estate and Wikipedia data, providing consistent Pydantic models with built-in data validation and enrichment.

## Overview

The `common_ingest` module provides a standardized way to load and enrich data from multiple sources:
- **Property data** from JSON files
- **Neighborhood data** from JSON files  
- **Wikipedia articles and summaries** from SQLite databases

All data is returned as fully validated and enriched Pydantic models with:
- Automatic city/state name expansion (SF → San Francisco, CA → California)
- Feature normalization and deduplication
- Coordinate validation
- UUID generation for embedding correlation
- Type safety and validation

## Quick Start

### Prerequisites

- Python 3.9+
- property_finder_models package (shared models)

### Installation

```bash
# Install shared models first (from project root)
cd property_finder_models && pip install -e .

# Install common_ingest (from project root) 
cd ../common_ingest && pip install -e .

# For development (includes testing and linting tools)
pip install -e ".[dev]"
```

### Running the Data Loading Module

```bash
# Run the ingestion pipeline using the parent-level script
python common_ingest_main.py

# Or run as module 
python -m common_ingest
```

The module will:
1. Load all property data from JSON files (420 properties)
2. Load all neighborhood data from JSON files (21 neighborhoods)
3. Load Wikipedia articles and summaries from SQLite (557 articles, 464 summaries)
4. Apply automatic enrichment (city/state expansion, feature normalization)
5. Display comprehensive statistics and sample data

### Running the REST API Server

```bash
# Use convenience scripts (can be run from any directory)
./common_ingest/start_api.sh
./common_ingest/stop_api.sh

# View server logs
tail -f /tmp/common_ingest_api.log
```

The API server will start with:
- **Interactive API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/v1/health
- **API root**: http://localhost:8000/

### Interactive API Documentation

The fastest way to explore and test the API is through the interactive documentation:

```bash
# Start the API server and open in browser:
./common_ingest/start_api.sh
open http://localhost:8000/docs
```

The interactive documentation provides:
- **Complete API reference** with all endpoints and parameters
- **Try it out** buttons to test endpoints directly from the browser
- **Request/response examples** with sample data
- **Schema documentation** for all Pydantic models

### Command Line Examples

```bash
# Get all properties with pagination
curl "http://localhost:8000/api/v1/properties?page=1&page_size=10"

# Filter properties by city
curl "http://localhost:8000/api/v1/properties?city=San Francisco"

# Get a specific property
curl "http://localhost:8000/api/v1/properties/prop-oak-125"

# Get all neighborhoods
curl "http://localhost:8000/api/v1/neighborhoods"

# Wikipedia articles with filtering
curl "http://localhost:8000/api/v1/wikipedia/articles?city=Park City&relevance_min=0.7"

# Statistics and analytics
curl "http://localhost:8000/api/v1/stats/summary"

# System health check
curl "http://localhost:8000/api/v1/health"
```

### Running Tests

```bash
# Run all unit AND integration tests (no arguments)
./run_tests.sh

# Run specific test modules
./run_tests.sh tests/test_models.py
./run_tests.sh integration_tests/
```

## Advanced Usage Guide

### Service Layer Architecture

The module uses a clean service layer architecture for business logic:

```python
from common_ingest.services import PropertyService, NeighborhoodService, WikipediaService
from common_ingest.loaders import PropertyLoader
from common_ingest.utils.config import get_settings

# Initialize with constructor dependency injection
settings = get_settings()
property_loader = PropertyLoader(settings.data_paths.get_property_data_path())
property_service = PropertyService(property_loader)

# Use service for business logic with pagination
properties, total_count, total_pages = property_service.get_properties(
    city="San Francisco",
    page=1,
    page_size=50
)
```

### Data Enrichment Features

#### Automatic Enrichment
- **City Name Expansion**: `SF` → `San Francisco`, `PC` → `Park City`
- **State Code Expansion**: `CA` → `California`, `UT` → `Utah`
- **Feature Normalization**: Lowercase, deduplicate, and sort
- **Property Type Mapping**: `single_family` → `PropertyType.HOUSE`
- **Coordinate Validation**: Ensures lat/lon are within valid ranges

#### Custom Filtering

```python
# Filter by multiple criteria
properties = property_loader.load_by_filter(city="San Francisco")
neighborhoods = neighborhood_loader.load_by_filter(city="Park City")
articles = wikipedia_loader.load_by_filter(
    city="San Francisco",
    state="California", 
    relevance_min=0.8
)
```

### Configuration Management

Configuration is managed via `common_ingest/config.yaml`:

```yaml
# Data source paths
data_paths:
  base_path: "/path/to/real_estate_ai_search"
  property_data_dir: "real_estate_data"
  wikipedia_db_path: "data/wikipedia/wikipedia.db"

# FastAPI server configuration
api:
  host: "0.0.0.0"
  port: 8000
  reload: true
  debug: false

# Data enrichment settings
enrichment:
  city_abbreviations:
    SF: "San Francisco"
    PC: "Park City"
  normalize_features_to_lowercase: true
```

### Module Structure

```
common_ingest/
├── __main__.py          # Data loading entry point
├── api_main.py          # FastAPI server entry point
├── api/                 # REST API implementation
│   ├── app.py           # FastAPI application factory
│   ├── dependencies.py  # Service dependency injection
│   └── routers/         # API route handlers
├── services/            # Business logic layer
│   ├── property_service.py
│   ├── neighborhood_service.py
│   └── wikipedia_service.py
├── loaders/             # Data loading classes
│   ├── property_loader.py
│   ├── neighborhood_loader.py
│   └── wikipedia_loader.py
├── enrichers/           # Data enrichment utilities
├── utils/               # Configuration and logging
├── tests/               # Unit test suite
└── integration_tests/   # Integration test suite
```

### API Response Format

All API responses follow a consistent structure:

```json
{
  "data": [...],
  "metadata": {
    "total_count": 420,
    "page": 1,
    "page_size": 50,
    "total_pages": 9,
    "timestamp": 1692789012.123,
    "has_next": true,
    "has_previous": false
  },
  "links": {
    "self": "/api/v1/properties?page=1",
    "next": "/api/v1/properties?page=2",
    "first": "/api/v1/properties?page=1",
    "last": "/api/v1/properties?page=9"
  }
}
```

### Design Principles

1. **Type Safety First**: All data structures use Pydantic models
2. **Service Layer Architecture**: Business logic separated from data access
3. **Constructor Dependency Injection**: Clean dependency management
4. **Automatic Enrichment**: Data is enriched during loading
5. **Comprehensive Logging**: Every operation is logged for debugging
6. **Clean Method Naming**: Standardized `load_by_filter()` methods

## Contributing

This module follows Python best practices:
- PEP 8 naming conventions
- Type hints for all functions
- Comprehensive docstrings
- No print statements (logging only)
- 100% test coverage for public APIs