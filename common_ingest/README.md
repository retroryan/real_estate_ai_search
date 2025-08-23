# Common Ingestion Module

A unified data loading and enrichment module for real estate and Wikipedia data, providing consistent Pydantic models with built-in data validation and enrichment.

## Overview

The `common_ingest` module provides a standardized way to load and enrich data from multiple sources:
- **Property data** from JSON files
- **Neighborhood data** from JSON files  
- **Wikipedia articles and summaries** from SQLite databases
- **Vector embeddings** from ChromaDB (future implementation)

All data is returned as fully validated and enriched Pydantic models with:
- Automatic city/state name expansion (SF → San Francisco, CA → California)
- Feature normalization and deduplication
- Coordinate validation
- UUID generation for embedding correlation
- Type safety and validation

## Quick Start

### Installation

```bash
# Install dependencies
pip install pydantic pydantic-settings fastapi uvicorn

# Optional: Install ChromaDB for embedding support (future feature)
pip install chromadb
```

### Running the Data Loading Module

```bash
# Run the ingestion pipeline and view summary statistics
python -m common_ingest

# The module will:
# 1. Load all property data from JSON files
# 2. Load all neighborhood data from JSON files
# 3. Load Wikipedia articles and summaries from SQLite
# 4. Apply automatic enrichment (city/state expansion, feature normalization)
# 5. Display comprehensive statistics and sample data
```

### Running the REST API Server

```bash
# Start the FastAPI server
python common_ingest/api_main.py

# Or with uvicorn directly
uvicorn common_ingest.api_main:app --reload --host 0.0.0.0 --port 8000
```

The API server will start on http://localhost:8000 with:
- **Interactive API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/v1/health
- **API root**: http://localhost:8000/

### API Usage Examples

```bash
# Get all properties with pagination
curl "http://localhost:8000/api/v1/properties?page=1&page_size=10"

# Filter properties by city
curl "http://localhost:8000/api/v1/properties?city=San Francisco"

# Get a specific property
curl "http://localhost:8000/api/v1/properties/prop-oak-125"

# Get all neighborhoods
curl "http://localhost:8000/api/v1/neighborhoods"

# Filter neighborhoods by city
curl "http://localhost:8000/api/v1/neighborhoods?city=Park City"
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

### Running Tests

```bash
# Run all tests
python common_ingest/tests/test_models.py
python common_ingest/tests/test_loaders.py
python common_ingest/tests/test_enrichers.py

# Or run specific test suites
cd common_ingest
python tests/test_models.py    # Test Pydantic models
python tests/test_loaders.py   # Test data loaders
python tests/test_enrichers.py # Test enrichment utilities
```

### Data Models

All data is returned as Pydantic models with full type safety:

```python
from common_ingest.models.property import EnrichedProperty, PropertyType

# Access property data with IDE autocomplete and type checking
for property in properties:
    print(f"Property: {property.listing_id}")
    print(f"Address: {property.address.street}, {property.address.city}")
    print(f"Price: ${property.price:,}")
    print(f"Type: {property.property_type.value}")
    
    # Features are automatically normalized and deduplicated
    print(f"Features: {', '.join(property.features)}")
    
    # Coordinates are validated
    if property.address.coordinates:
        print(f"Location: {property.address.coordinates.lat}, {property.address.coordinates.lon}")
```

## Features

### 🔄 Automatic Data Enrichment

- **City Name Expansion**: `SF` → `San Francisco`, `PC` → `Park City`
- **State Code Expansion**: `CA` → `California`, `UT` → `Utah`
- **Feature Normalization**: Lowercase, deduplicate, and sort
- **Property Type Mapping**: `single_family` → `PropertyType.HOUSE`
- **Coordinate Validation**: Ensures lat/lon are within valid ranges

### 📊 Pydantic Models

All data structures use Pydantic for:
- **Type Safety**: Full typing support with IDE autocomplete
- **Validation**: Automatic validation of all fields
- **Serialization**: Easy conversion to/from JSON
- **Documentation**: Self-documenting with field descriptions

### 🗂️ Supported Data Sources

#### Property Data (JSON)
- Files: `properties_sf.json`, `properties_pc.json`
- Model: `EnrichedProperty`
- Features: Address enrichment, feature normalization, property type mapping

#### Neighborhood Data (JSON)
- Files: `neighborhoods_sf.json`, `neighborhoods_pc.json`
- Model: `EnrichedNeighborhood`
- Features: Boundary polygons, POI counts, demographic data

#### Wikipedia Data (SQLite)
- Database: `wikipedia.db`
- Models: `EnrichedWikipediaArticle`, `WikipediaSummary`
- Features: Location extraction, key topic normalization, confidence scores

## Module Structure

```
common_ingest/
├── __init__.py           # Module exports
├── models/               # Pydantic data models
│   ├── base.py          # Base model classes
│   ├── property.py      # Property and neighborhood models
│   ├── wikipedia.py     # Wikipedia article models
│   └── embedding.py     # Embedding data models
├── loaders/             # Data loading classes
│   ├── base.py          # Abstract base loader
│   ├── property_loader.py
│   ├── neighborhood_loader.py
│   └── wikipedia_loader.py
├── enrichers/           # Data enrichment utilities
│   ├── address_utils.py # Address normalization
│   └── feature_utils.py # Feature extraction
├── utils/               # Utility functions
│   ├── config.py        # Configuration management
│   └── logger.py        # Logging setup
└── tests/               # Test suite
    ├── test_models.py   # Model validation tests
    ├── test_loaders.py  # Loader functionality tests
    └── test_enrichers.py # Enrichment utilities tests
```

## Running Tests

```bash
# Run all tests
python -m pytest common_ingest/tests/

# Run specific test module
python common_ingest/tests/test_models.py
python common_ingest/tests/test_loaders.py
python common_ingest/tests/test_enrichers.py

# Run with verbose output
python common_ingest/tests/test_models.py -v
```

## API Reference

### PropertyLoader

```python
class PropertyLoader(BaseLoader[EnrichedProperty]):
    def __init__(self, data_path: Path)
    def load_all(self) -> List[EnrichedProperty]
    def load_by_filter(city: Optional[str] = None) -> List[EnrichedProperty]
    def load_properties_by_city(city: str) -> List[EnrichedProperty]
```

### NeighborhoodLoader

```python
class NeighborhoodLoader(BaseLoader[EnrichedNeighborhood]):
    def __init__(self, data_path: Path)
    def load_all(self) -> List[EnrichedNeighborhood]
    def load_by_filter(city: Optional[str] = None) -> List[EnrichedNeighborhood]
    def load_neighborhoods_by_city(city: str) -> List[EnrichedNeighborhood]
```

### WikipediaLoader

```python
class WikipediaLoader(BaseLoader[Union[EnrichedWikipediaArticle, WikipediaSummary]]):
    def __init__(self, database_path: Path)
    def load_all(self) -> List[EnrichedWikipediaArticle]
    def load_by_filter(city: Optional[str], state: Optional[str]) -> List[EnrichedWikipediaArticle]
    def load_summaries(self) -> List[WikipediaSummary]
    def load_summaries_by_location(city: Optional[str], state: Optional[str]) -> List[WikipediaSummary]
```

## Data Models

### EnrichedProperty

```python
class EnrichedProperty(BaseEnrichedModel):
    listing_id: str
    property_type: PropertyType
    price: Decimal
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int]
    address: EnrichedAddress
    features: List[str]  # Normalized and deduplicated
    amenities: List[str]  # Normalized and deduplicated
    status: PropertyStatus
    embedding_id: Optional[str]  # Auto-generated UUID
```

### EnrichedNeighborhood

```python
class EnrichedNeighborhood(BaseEnrichedModel):
    neighborhood_id: str
    name: str
    city: str  # Expanded from abbreviations
    state: str  # Expanded from codes
    boundaries: Optional[GeoPolygon]
    center_point: Optional[GeoLocation]
    characteristics: List[str]  # Normalized
    poi_count: int
    embedding_id: Optional[str]  # Auto-generated UUID
```

### EnrichedWikipediaArticle

```python
class EnrichedWikipediaArticle(BaseEnrichedModel):
    page_id: int
    article_id: int
    title: str
    url: str  # Automatically formatted as full Wikipedia URL
    full_text: str
    relevance_score: float
    location: LocationInfo
    embedding_id: Optional[str]  # Auto-generated UUID
```

### WikipediaSummary

```python
class WikipediaSummary(BaseEnrichedModel):
    page_id: int
    article_title: str
    short_summary: str
    long_summary: str
    key_topics: List[str]  # Normalized and deduplicated
    best_city: Optional[str]
    best_state: Optional[str]  # Expanded from codes
    overall_confidence: float
    embedding_id: Optional[str]  # Auto-generated UUID
```

## Configuration

The module uses a YAML-based configuration system following the pattern from `common_embeddings/`:

### Configuration File

The main configuration is stored in `common_ingest/config.yaml`:

```yaml
# Data source paths
data_paths:
  base_path: "/Users/ryanknight/projects/temporal/real_estate_ai_search"
  property_data_dir: "real_estate_data"
  wikipedia_db_path: "data/wikipedia/wikipedia.db"

# Data enrichment settings
enrichment:
  city_abbreviations:
    SF: "San Francisco"
    PC: "Park City"
  normalize_features_to_lowercase: true
  
# Processing settings
processing:
  batch_size: 100
  max_workers: 4
```

### Using Configuration in Code

```python
from common_ingest.utils.config import get_settings

settings = get_settings()
print(f"Module version: {settings.metadata.version}")
print(f"Data path: {settings.data_paths.get_property_data_path()}")
print(f"Log level: {settings.logging.level}")
print(f"Batch size: {settings.processing.batch_size}")
```

### Creating Custom Configuration

```python
from common_ingest.utils.config import Settings

# Load from custom YAML file
settings = Settings.from_yaml("my_config.yaml")

# Save current settings to YAML
settings.to_yaml("backup_config.yaml")
```

## Logging

All operations are logged with structured logging:

```python
from common_ingest.utils.logger import setup_logger

logger = setup_logger("my_app")
logger.info("Loading properties...")
```

Logs include:
- Operation tracking with decorators
- Item counts for bulk operations
- Enrichment statistics
- Error handling with context

## Design Principles

1. **Type Safety First**: All data structures use Pydantic models
2. **Automatic Enrichment**: Data is enriched during loading, not as a separate step
3. **No Partial Updates**: Operations are atomic - complete or fail
4. **Constructor Dependency Injection**: All dependencies passed through constructors
5. **Comprehensive Logging**: Every operation is logged for debugging
6. **Clean Abstractions**: Clear separation between loading, enrichment, and models

## Future Enhancements

- **Embedding Integration**: Load and correlate vector embeddings from ChromaDB
- **Streaming Support**: Add streaming APIs for large datasets
- **Caching Layer**: Add caching for frequently accessed data
- **Additional Enrichers**: More enrichment strategies (geocoding, demographics)
- **Performance Optimization**: Bulk loading optimizations

## Contributing

This module follows Python best practices:
- PEP 8 naming conventions (snake_case for functions, PascalCase for classes)
- Type hints for all functions
- Comprehensive docstrings
- No print statements (logging only)
- 100% test coverage for public APIs

## License

This is a demo module for showcasing Python development best practices.