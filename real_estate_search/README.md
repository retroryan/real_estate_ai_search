# Real Estate Search Application

A high-quality demonstration of Elasticsearch-powered real estate search enriched with Wikipedia location data, POIs (Points of Interest), and neighborhood context.

## Features

- **Full-Text Search**: Search properties by description, features, and amenities
- **Wikipedia Enrichment**: Properties enriched with location context from Wikipedia
- **POI Integration**: Discover properties near parks, museums, landmarks, and cultural sites
- **Multiple Search Capabilities**: Combined property and context-aware search
- **Faceted Search**: Filter by price ranges, property types, and categories
- **Geo-Location Support**: Properties indexed with coordinates for proximity searches

## Quick Start

### Prerequisites

- Python 3.8+
- Elasticsearch 8.x running locally
- Data indexed via data_pipeline
- Wikipedia database (included in `/data/wikipedia/`)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Elasticsearch is running
curl localhost:9200

# Verify data is indexed
python main.py --mode demo
```

## Usage


### Setup Indexes

```bash
python -m real_estate_search.management setup-indices --clear
```

### Ingest the data from the data pipeline

```bash
python -m data_pipeline
````

### Run the Demos Mode 

Run demonstration searches on pre-indexed data:

```bash
# Run full demo
python -m real_estate_search.main
```

### Search Mode

Execute specific search queries:

```bash
# Search for properties
python main.py --mode search --query "ski resort properties"
python main.py --mode search --query "family home near parks"
python main.py --mode search --query "downtown condo with amenities"
python main.py --mode search --query "historic neighborhood"
```

### Configuration Options

```bash
# Use custom configuration
python main.py --config custom-config.yaml

# Set logging level
python main.py --log-level DEBUG

# Get help
python main.py --help
```

## Index Management

Use the management CLI to check index status:

```bash
# Validate indices exist and have correct mappings
python -m real_estate_search.management validate-indices

# List index status and document counts
python -m real_estate_search.management list-indices

# Check embedding coverage
python -m real_estate_search.management validate-embeddings
```

## Configuration

### config.yaml

```yaml
# Configuration for Real Estate Search
elasticsearch:
  host: localhost
  port: 9200
  property_index: properties
  request_timeout: 30

# Wikipedia data location
data:
  wikipedia_db: ../data/wikipedia/wikipedia.db

# Search settings
demo_mode: true
log_level: INFO
```

### Environment Variables (Optional)

```bash
# Elasticsearch authentication
export ELASTICSEARCH_USERNAME="elastic"
export ELASTICSEARCH_PASSWORD="your-password"
```

## Architecture

The application is a clean search interface that works with pre-indexed data:

```
real_estate_search/
├── main.py              # CLI entry point (search and demo modes)
├── container.py         # Dependency injection container
├── config/              # Configuration management
│   └── config.py        # Pydantic configuration models
├── services/            # Business logic layer
│   ├── search_service.py       # Search operations
│   ├── indexing_service.py     # Index management
│   └── enrichment_service.py   # Wikipedia enrichment lookups
├── repositories/        # Data access layer
│   ├── property_repository.py  # Elasticsearch operations
│   └── wikipedia_repository.py # Wikipedia database queries
├── search/              # Search implementation
│   ├── models.py        # Request/response models
│   └── query_builder.py # Query construction
└── management.py        # Index management CLI
```

### Data Flow

1. **Pre-indexed Data**: Data pipeline creates enriched documents in Elasticsearch
2. **Search Request**: User query → Search service → Query builder
3. **Query Execution**: Elasticsearch query → Ranked results
4. **Response**: Formatted results with enrichment data

## Data Pipeline Integration

### Complete Data Pipeline Flow

The system follows a three-phase data pipeline architecture:

#### Phase 1: Index Setup (real_estate_search)
- **Purpose**: Create and configure Elasticsearch indexes with proper mappings
- **Location**: `real_estate_search/management.py`
- **Command**: `python -m real_estate_search.management setup-indices --clear`
- **Creates**: Properties, neighborhoods, and Wikipedia article indexes with defined mappings
- **Templates**: Index mappings located in `real_estate_search/elasticsearch/templates/`

#### Phase 2: Data Ingestion (data_pipeline)
- **Purpose**: Load, enrich, and index data into Elasticsearch
- **Location**: `data_pipeline/`
- **Command**: `python -m data_pipeline`
- **Process**:
  1. Loads raw property data from JSON files
  2. Enriches with neighborhood and Wikipedia correlations
  3. Generates embeddings for semantic search
  4. Writes enriched documents to Elasticsearch indexes
- **Output**: Fully indexed and enriched documents in Elasticsearch

#### Phase 3: Search Operations (real_estate_search)
- **Purpose**: Query and retrieve indexed data
- **Location**: `real_estate_search/`
- **Command**: `python -m real_estate_search.main`
- **Features**: Full-text search, semantic search, filtering, and faceted navigation

### Execution Order

```bash
# 1. Setup Elasticsearch indexes with mappings
python -m real_estate_search.management setup-indices --clear

# 2. Run data pipeline to ingest and enrich data
python -m data_pipeline

# 3. Search the indexed data
python -m real_estate_search.main --mode demo
```

The separation ensures:
- Clean architecture with single responsibility
- Data pipeline handles all ETL and enrichment
- Search application focuses on query and retrieval
- Index mappings are defined before data ingestion

## Search Examples

### Property Types
```bash
python main.py --mode search --query "single family home"
python main.py --mode search --query "luxury condo"
python main.py --mode search --query "townhouse"
```

### Location Features
```bash
python main.py --mode search --query "near parks"
python main.py --mode search --query "downtown location"
python main.py --mode search --query "mountain views"
```

### Amenities
```bash
python main.py --mode search --query "swimming pool"
python main.py --mode search --query "modern kitchen"
python main.py --mode search --query "garage parking"
```

## Troubleshooting

### No Data Found

If the demo reports no data:

1. **Run data_pipeline first**:
   ```bash
   cd ../
   python -m data_pipeline
   ```

2. **Check Elasticsearch**:
   ```bash
   curl localhost:9200/properties/_count
   ```

3. **Verify index exists**:
   ```bash
   python -m real_estate_search.management list-indices
   ```

### Connection Errors

- Verify Elasticsearch is running: `ps aux | grep elasticsearch`
- Check configuration in `config.yaml`
- Ensure port 9200 is accessible

### Search Not Working

- Ensure data is indexed: Run data_pipeline
- Check index health: `python -m real_estate_search.management validate-indices`
- Verify embeddings: `python -m real_estate_search.management validate-embeddings`

## Performance

- **Search Response**: < 100ms for most queries
- **No indexing overhead**: All indexing done by data_pipeline
- **Efficient queries**: Optimized Elasticsearch queries with proper field mappings

## Development Notes

This application demonstrates:
- **Clean separation of concerns**: Search separate from indexing
- **Dependency injection**: Clean IoC container pattern
- **Pydantic models**: Type-safe configuration and data models
- **No duplication**: Works with existing indexed data
- **Simple and focused**: Search and retrieval only

The system showcases proper architectural separation where data pipeline handles all data processing and this application provides the search interface.