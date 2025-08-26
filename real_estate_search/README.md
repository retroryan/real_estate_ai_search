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

## Index Management Commands

Before using the search system, you must set up Elasticsearch indices. The management system provides comprehensive tools for index operations.

### Available Commands

```bash
# Set up all indices (first time setup)
python -m real_estate_search.management setup-indices

# Reset everything for clean demo 
python -m real_estate_search.management setup-indices --clear

# Validate index health and mappings
python -m real_estate_search.management validate-indices

# Check vector embedding coverage (after data pipeline)
python -m real_estate_search.management validate-embeddings

# List detailed index status
python -m real_estate_search.management list-indices

# Clean up test indices
python -m real_estate_search.management delete-test-indices
```

### Embedding Validation

The `validate-embeddings` command is essential for semantic search functionality:

```bash
python -m real_estate_search.management validate-embeddings
```

### Required Environment Variables

```bash
# Elasticsearch authentication
export ELASTIC_PASSWORD="your-elasticsearch-password"

# Embedding providers (choose one)
export OPENAI_API_KEY="your-openai-key"        # For OpenAI embeddings
export VOYAGE_API_KEY="your-voyage-key"        # For Voyage AI embeddings  
export GEMINI_API_KEY="your-gemini-key"        # For Google Gemini embeddings
```

## Usage

The application now uses a unified `main.py` entry point with three operation modes:

### 1. Full Demo Mode (Recommended)

Run the complete demonstration including indexing and searches:

```bash
# From the real_estate_search directory:
python main.py --mode demo

# This will:
# 1. Create/recreate the property index
# 2. Ingest all properties with Wikipedia enrichment
# 3. Run demo searches showing different capabilities
```

### 2. Data Ingestion Mode

Index properties with Wikipedia enrichment:

```bash
# Ingest data (preserves existing index)
python main.py --mode ingest

# Force recreate index before ingestion
python main.py --mode ingest --recreate

# Output example:
# ✅ Index created/updated
# 📄 Ingestion complete: 420 properties indexed, 0 failed
```

### 3. Search Mode

Execute individual search queries:

```bash
# Search for specific properties
python main.py --mode search --query "ski resort properties"
python main.py --mode search --query "family home near parks"
python main.py --mode search --query "downtown condo with amenities"

# Results show top 5 matches with location context
```

### Configuration Options

```bash
# Use custom configuration file
python main.py --config custom-config.yaml --mode demo

# Set logging level
python main.py --mode demo --log-level DEBUG

# Get help
python main.py --help
```

### Legacy Scripts (Still Available)

```bash
# Direct index setup (legacy)
python scripts/setup_index.py --recreate

# Direct demo searches (legacy)
python scripts/demo_search.py
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

The application has a unified main entry point with clean modular structure:

```
real_estate_search/
├── main.py           # Unified CLI entry point with 3 modes
├── container.py      # Dependency injection container
├── config/           # Configuration management
│   ├── config.py    # Configuration classes
│   └── settings.py  # Settings validation
├── services/         # Business logic layer
│   ├── indexing_service.py    # Property indexing with enrichment
│   ├── search_service.py      # Search operations
│   └── enrichment_service.py  # Wikipedia data enrichment
├── repositories/     # Data access layer  
│   ├── property_repository.py    # Property data loading
│   └── wikipedia_repository.py  # Wikipedia database queries
├── ingestion/        # Data ingestion orchestration
│   └── orchestrator.py         # Coordinates ingestion pipeline
├── indexer/          # Elasticsearch indexing
│   ├── property_indexer.py    # Core indexing logic
│   ├── mappings.py           # Elasticsearch field mappings
│   └── models.py             # Pydantic data models
├── search/           # Search implementation
│   ├── search_engine.py      # Multi-mode search engine
│   ├── models.py            # Request/response models
│   └── query_builder.py     # Elasticsearch query construction
├── wikipedia/        # Wikipedia integration
│   ├── enricher.py          # Property enrichment logic
│   ├── extractor.py         # Data extraction from Wikipedia
│   └── models.py            # Wikipedia data models
└── scripts/          # Legacy scripts (still functional)
    ├── setup_index.py       # Direct index setup
    └── demo_search.py       # Direct search demos
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

### Command Line Usage

```bash
# Demo mode - runs complete demonstration
python main.py --mode demo

# Search mode - individual queries  
python main.py --mode search --query "luxury ski resort properties"
python main.py --mode search --query "family home near parks"
python main.py --mode search --query "downtown condo with cultural attractions"

# Ingestion mode - index data
python main.py --mode ingest --recreate
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
- Single `main.py` entry point with 3 operation modes
- No over-engineering (removed caching, scoring complexity)
- Single index, no sharding needed for 420 documents

The system demonstrates how to combine structured property data with unstructured Wikipedia content for enhanced search experiences.