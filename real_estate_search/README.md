# Real Estate Search with Wikipedia Enrichment

A high-quality demonstration of Elasticsearch-powered real estate search enriched with Wikipedia location data, POIs (Points of Interest), and neighborhood context.

## Important: Working Directory

**All commands in this README should be run from the `real_estate_search` directory:**

```bash
cd /path/to/project/real_estate_search
# All commands below assume you are in this directory
```

## Features

- **Full-Text Search**: Search properties by description, features, and amenities
- **Wikipedia Enrichment**: Automatic enrichment with location context from 464+ Wikipedia articles
- **POI Integration**: Discover properties near parks, museums, landmarks, and cultural sites
- **Multiple Search Modes**:
  - Standard: Combined property and Wikipedia search
  - Lifestyle: Focus on amenities and recreational features
  - Cultural: Emphasize museums, arts, and cultural venues
  - Investment: Target tourist areas and rental opportunities
  - POI Proximity: Find properties near specific points of interest
- **Faceted Search**: Filter by price ranges, property types, and POI categories
- **Geo-Location Support**: Properties indexed with coordinates for proximity searches

## Quick Start

### Prerequisites

- Python 3.8+
- Elasticsearch 8.x running locally
- Wikipedia database (included in `/data/wikipedia/`)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Elasticsearch is running
curl -u elastic:elasticpassword localhost:9200
```

### Setup and Index Data

```bash
# From the real_estate_search directory:
# Create index and load properties with Wikipedia enrichment
python scripts/setup_index.py --recreate

# Or with test data only (3 properties)
python scripts/setup_index.py --recreate --test-data

# Output:
# ✅ Index created
# 📄 Loaded 420 properties  
# ✅ Indexed 420/420 properties
```

### Run Demo Searches

```bash
# From the real_estate_search directory:
# Run the full demo showing all search modes
python scripts/demo_search.py

# Demos include:
# 1. Park City Ski Resort Properties (97 results)
# 2. San Francisco Cultural District (87 results)
# 3. Lifestyle-Based Search (117 results)
# 4. POI Proximity Search
# 5. Investment Properties (24 results)
```

## Data Overview

### Property Data
- **420 properties** across two markets:
  - San Francisco Bay Area (220 properties)
  - Park City, Utah (200 properties)
- **Price Range**: $225K - $15.9M
- **Property Types**: Single-family, condos, townhouses, multi-family

### Wikipedia Enrichment
- **464 Wikipedia articles** covering:
  - 57 San Francisco articles
  - 15 Park City articles
  - 10 Oakland articles
  - Additional Bay Area coverage
- **POI Categories**: Parks, museums, schools, transit, landmarks, entertainment
- **100% location coverage**: All properties enriched with Wikipedia context

## Architecture

### Core Components

```
real_estate_search/
├── indexer/          # Elasticsearch indexing with Wikipedia enrichment
│   ├── property_indexer.py   # Main indexing logic
│   ├── mappings.py          # Elasticsearch field mappings
│   └── models.py            # Pydantic data models
├── search/           # Search implementation
│   ├── search_engine.py    # Search with multiple modes
│   ├── models.py           # Request/response models
│   └── enums.py            # Search types and operators
├── wikipedia/        # Wikipedia integration
│   ├── enricher.py         # Property enrichment with Wikipedia data
│   ├── extractor.py        # Wikipedia database queries
│   └── models.py           # Wikipedia data models
└── scripts/          # Demo and setup scripts
    ├── setup_index.py      # Index creation and data loading
    └── demo_search.py      # Search demonstrations
```

### Data Flow

1. **Property Loading**: JSON files → Pydantic models
2. **Wikipedia Enrichment**: 
   - Location lookup (city/state → Wikipedia articles)
   - POI extraction from article topics
   - Neighborhood context when available
3. **Indexing**: Enriched documents → Elasticsearch
4. **Search**: Multi-mode queries → Ranked results

## Search Examples

### Basic Property Search

```python
from real_estate_search.search.search_engine import SearchEngine
from real_estate_search.search.models import SearchRequest, SearchFilters

engine = SearchEngine()

# Search luxury homes in Park City
request = SearchRequest(
    query_text="luxury ski resort",
    filters=SearchFilters(
        cities=["park city"],
        min_price=1000000
    ),
    size=10
)

results = engine.search(request)
print(f"Found {results.total} properties")
```

### Lifestyle Search

```python
# Find family-friendly properties near parks
request = SearchRequest(
    query_text="park recreation family",
    search_mode="lifestyle",
    filters=SearchFilters(min_bedrooms=3),
    size=10
)

results = engine.search(request)
```

### Cultural District Search

```python
# Properties near museums and cultural venues
request = SearchRequest(
    query_text="museum arts cultural",
    search_mode="cultural",
    filters=SearchFilters(cities=["san francisco"]),
    size=10
)

results = engine.search(request)
```

## Elasticsearch Mapping

The index uses a comprehensive mapping optimized for demo purposes:

- **Text Fields**: Analyzed with English analyzer for full-text search
- **Keywords**: Exact matching for filters and aggregations
- **Nested Documents**: POIs stored as nested for proximity queries
- **Geo Points**: Location coordinates for distance calculations
- **Custom Analyzers**: Wikipedia content with shingle support

### Key Fields

- `enriched_search_text`: Combined property + Wikipedia content
- `location_context`: Wikipedia article data for the city
- `neighborhood_context`: Neighborhood-specific Wikipedia data
- `nearby_poi`: Nested POI documents with categories and descriptions

## Configuration

### Elasticsearch Settings

```yaml
# config.yaml (in real_estate_search directory)
elasticsearch:
  host: localhost
  port: 9200
  username: elastic
  password: your-password-here
  # api_key: your-api-key-here  # Alternative to username/password
  # cloud_id: your-cloud-id-here  # For Elastic Cloud
  property_index: properties
  batch_size: 100
  request_timeout: 30

embedding:
  provider: ollama
  model_name: nomic-embed-text
  
data:
  wikipedia_db: data/wikipedia/wikipedia.db
  properties_dir: real_estate_data
```

### Environment Variables

```bash
# Optional: Override config with environment variables
export ES_HOST=localhost
export ES_PORT=9200
export ES_USERNAME=elastic
export ES_PASSWORD=elasticpassword
```

## Testing

```bash
# From the real_estate_search directory:
# Run system tests (if available)
python scripts/test_system.py

# Test specific search mode
python -c "
from search.search_engine import SearchEngine
engine = SearchEngine()
# Your test code here
"
```

## Performance

- **Indexing**: ~10 seconds for 420 properties with enrichment
- **Search Response**: < 100ms for most queries
- **Wikipedia Coverage**: 100% of properties enriched
- **POI Extraction**: 3-5 POIs per location

## Troubleshooting

### No Search Results
- Ensure index exists: `curl -u elastic:password localhost:9200/_cat/indices`
- Check document count: `curl -u elastic:password localhost:9200/properties/_count`
- Verify Wikipedia enrichment worked during indexing

### Connection Errors
- Verify Elasticsearch is running: `ps aux | grep elasticsearch`
- Check credentials in `config.yaml` (in real_estate_search directory)
- Ensure port 9200 is accessible

### Missing Wikipedia Data
- Confirm database exists: `ls ../data/wikipedia/wikipedia.db`
- Check Wikipedia article count in database
- Review enrichment logs during indexing

## Development Notes

This is a **high-quality demo** implementation focusing on:
- Clean, modular code with Pydantic models
- Rich Wikipedia integration for location context
- Multiple search modes demonstrating different use cases
- No over-engineering (removed caching, scoring complexity)
- Single index, no sharding needed for 420 documents

The system demonstrates how to combine structured property data with unstructured Wikipedia content for enhanced search experiences.