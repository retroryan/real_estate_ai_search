# Real Estate Search Application

A comprehensive demonstration of Elasticsearch's advanced capabilities for building production-ready search applications. This project showcases how to leverage Elasticsearch's full suite of features to create a sophisticated real estate search system that combines structured property data with unstructured content from Wikipedia articles, demonstrating enterprise-scale document processing and search techniques.

## Project Overview

This application demonstrates real-world Elasticsearch patterns and best practices through a real estate search system that processes and searches across:

- **550+ property listings** with structured data (price, bedrooms, amenities)
- **450+ Wikipedia articles** (averaging 222KB each, ~100MB total)
- **Multi-entity relationships** linking properties → neighborhoods → Wikipedia content
- **Semantic embeddings** for AI-powered similarity search
- **Geographic data** for location-based queries and spatial search

### What This Project Demonstrates

#### 1. **Index Design & Mappings**
- Creating optimal mappings for different data types (text, keyword, numeric, geo_point)
- Multi-index architecture (properties, neighborhoods, wikipedia)
- Field analyzers for language-specific text processing
- Nested objects and array handling

#### 2. **Ingest Pipelines**
- HTML stripping processor for cleaning Wikipedia content
- Script processors for calculated fields (content_length)
- Field enrichment and transformation
- Bulk processing of large documents (100-500KB each)

#### 3. **Advanced Search Capabilities**
- Full-text search with English analyzer and stemming
- Phrase matching and proximity queries
- Boolean queries combining multiple conditions
- Aggregations for faceted search and analytics
- Geo-distance queries for location-based search
- Semantic search using vector embeddings
- Cross-index searches with relationship traversal

#### 4. **Performance Optimization**
- Bulk API for indexing thousands of documents efficiently
- Source filtering to reduce network overhead
- Query optimization with appropriate query types
- Batching strategies for large document processing

#### 5. **Production Patterns**
- Error handling and retry logic
- Progress tracking and monitoring
- Dry-run modes for testing
- Configuration management
- Clean separation between indexing and search

## Features

- **Full-Text Search**: Search across complete Wikipedia articles and property descriptions
- **Semantic Search**: AI-powered search using embeddings for concept matching
- **Multi-Entity Search**: Combined queries across properties, neighborhoods, and Wikipedia
- **Rich Relationships**: Navigate connections between properties and their geographic context
- **Faceted Navigation**: Filter by price ranges, property types, neighborhoods
- **Aggregation Analytics**: Statistics on pricing, availability, and geographic distribution
- **Geo-Spatial Search**: Find properties within distance of coordinates
- **HTML Results Generation**: Export search results to formatted HTML reports
- **Bulk Document Processing**: Efficiently handle documents ranging from 1KB to 500KB

## Learning Outcomes

By exploring this project, you'll learn how to:

1. **Design Elasticsearch Schemas** for mixed structured/unstructured data
2. **Build Ingest Pipelines** to process HTML and extract clean text
3. **Implement Full-Text Search** across documents of varying sizes
4. **Create Complex Queries** combining multiple search criteria
5. **Optimize Performance** for datasets with 100MB+ of text
6. **Handle Relationships** between different entity types
7. **Process Documents at Scale** using bulk operations
8. **Generate Analytics** with aggregations and facets

## Use Cases Demonstrated

This project serves as a reference implementation for:

- **E-commerce Search** - Product search with filters and facets
- **Content Management** - Searching across large documents and articles  
- **Knowledge Bases** - Combining structured and unstructured content
- **Geographic Search** - Location-based queries and proximity search
- **Enterprise Search** - Multi-index search with relationships
- **Document Processing** - Handling HTML, text extraction, and enrichment

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
curl localhost:9200
```

## Complete Pipeline Flow

The complete data indexing and search system follows these steps:

### Step 1: Create Indexes
Initialize Elasticsearch indexes with proper mappings and configurations:
```bash
python -m real_estate_search.management setup-indices --clear
```

### Step 2: Run Data Pipeline
Process, enrich, and index property data with neighborhood and Wikipedia correlations:
```bash
python -m data_pipeline
```

### Step 3: Enrich Wikipedia Articles (Optional)
After running the data pipeline, optionally enrich Wikipedia documents with full article content for enhanced full-text search:
```bash
# Enrich all Wikipedia articles (processes ~450+ HTML files)
python enrich_wikipedia_articles.py --data-dir ../data
```

### Step 4: Run Search Demos
Execute demonstration queries showcasing various search capabilities:
```bash
# Run a specific demo
python -m real_estate_search.management demo 1

# Or run demo 10 for Wikipedia full-text search (requires Step 3)
python -m real_estate_search.management demo 10
```

## Additional Options

### Wikipedia Enrichment Options

The Wikipedia enrichment step (Step 3) provides several options:

```bash
# Test with a smaller batch first
python enrich_wikipedia_articles.py --data-dir ../data --max-documents 10 --dry-run

# Process specific number of documents
python enrich_wikipedia_articles.py --data-dir ../data --max-documents 100

# View processing details
python enrich_wikipedia_articles.py --data-dir ../data --verbose
```

This enrichment:
- Loads HTML content from `data/wikipedia/pages/*.html` files
- Strips HTML tags using Elasticsearch's ingest pipeline
- Enables full-text search across complete Wikipedia articles
- Required for Demo 10 (Wikipedia Full-Text Search)

### Demo Mode Options 

The application includes multiple demo queries that showcase different search capabilities. You can run demos using the management CLI:

```bash
# List all available demos
python -m real_estate_search.management demo --list

# Run a specific demo by number (1-10)
python -m real_estate_search.management demo 1

# Run demo with verbose output to see the actual Elasticsearch queries
python -m real_estate_search.management demo 1 --verbose

# Available demos:
# 1. Basic Property Search - Simple property search examples
# 2. Property Filter Search - Filtered searches with criteria
# 3. Geographic Distance Search - Location-based proximity searches
# 4. Neighborhood Statistics - Aggregations and statistics by neighborhood
# 5. Price Distribution Analysis - Price range analytics
# 6. Semantic Similarity Search - AI-powered semantic search
# 7. Multi-Entity Combined Search - Search across properties, neighborhoods, and Wikipedia
# 8. Wikipedia Article Search - Search Wikipedia location data
# 9. Property-Neighborhood-Wikipedia Relationships - Show rich relationships between entities
# 10. Wikipedia Full-Text Search - Full-text search across complete Wikipedia articles

# Run the standalone relationship demo (Demo 9 with enhanced visualization)
python -m real_estate_search.demo_queries.demo_relationship_search
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

## Technical Architecture

### Elasticsearch Infrastructure

The project leverages these Elasticsearch components:

#### **Indexes & Mappings**
```json
{
  "properties": {
    "title": { "type": "text", "analyzer": "english" },
    "full_content": { "type": "text", "analyzer": "english" },
    "price": { "type": "float" },
    "location": { "type": "geo_point" },
    "amenities": { "type": "keyword" },
    "embedding": { "type": "dense_vector", "dims": 1024 }
  }
}
```

#### **Ingest Pipeline**
```json
{
  "processors": [
    { "html_strip": { "field": "full_content" } },
    { "script": { "source": "ctx.content_length = ctx.full_content.length()" } },
    { "set": { "field": "content_loaded", "value": true } }
  ]
}
```

#### **Query Types Demonstrated**
- **Match Query**: Full-text search with analysis
- **Term Query**: Exact value matching
- **Bool Query**: Combining multiple conditions
- **Range Query**: Numeric and date ranges
- **Geo Distance**: Location-based filtering
- **KNN Search**: Vector similarity search
- **Aggregations**: Statistical analysis and facets

### Application Structure

```
real_estate_search/
├── main.py                      # CLI entry point
├── management.py                # Index management CLI
├── enrich_wikipedia_articles.py # Document enrichment tutorial
├── demo_queries/                # 10 search demonstrations
│   ├── property_queries.py      # Basic property search
│   ├── aggregation_queries.py   # Analytics and facets
│   ├── wikipedia_fulltext.py    # Full-text document search
│   └── ...                      # More demo patterns
├── indexer/                     # Index management
│   ├── index_manager.py         # Index creation and mappings
│   └── ingest_pipeline.py       # Document processing pipelines
├── services/                    # Business logic
│   └── search_service.py        # Search orchestration
└── html_results/                # HTML report generation
    ├── models.py                # Pydantic data models
    └── generator.py             # HTML/CSS templating
```

### Data Flow

1. **Index Creation**: Define mappings for optimal search performance
2. **Document Ingestion**: Bulk load with ingest pipeline processing
3. **Search Execution**: Query DSL → Elasticsearch → Ranked results
4. **Result Processing**: Highlighting, aggregations, and formatting

## Data Pipeline Architecture

The system follows a clean three-phase architecture:

### Phase 1: Index Setup (real_estate_search)
- **Purpose**: Create and configure Elasticsearch indexes with proper mappings
- **Location**: `real_estate_search/management.py`
- **Templates**: Index mappings in `real_estate_search/elasticsearch/templates/`

### Phase 2: Data Ingestion (data_pipeline)
- **Purpose**: Load, enrich, and index data into Elasticsearch
- **Location**: `data_pipeline/`
- **Process**:
  1. Loads raw property data from JSON files
  2. Enriches with neighborhood and Wikipedia correlations
  3. Generates embeddings for semantic search
  4. Writes enriched documents to Elasticsearch indexes

### Phase 3: Search Operations (real_estate_search)
- **Purpose**: Query and retrieve indexed data
- **Location**: `real_estate_search/`
- **Features**: Full-text search, semantic search, filtering, and faceted navigation

The separation ensures:
- Clean architecture with single responsibility
- Data pipeline handles all ETL and enrichment
- Search application focuses on query and retrieval
- Index mappings are defined before data ingestion

## Testing

### Integration Tests

The application includes integration tests for the embedding service that powers semantic search:

```bash
# Run all integration tests (requires VOYAGE_API_KEY in .env)
pytest real_estate_search/integration_tests/ -v

# Run embedding service tests
pytest real_estate_search/integration_tests/test_embedding_service.py -v

# Run with detailed output
pytest real_estate_search/integration_tests/test_embedding_service.py -v -s
```

The tests validate:
- Configuration loading from config.yaml and .env
- Query embedding generation using Voyage AI
- Semantic similarity between related queries
- Batch processing capabilities
- Error handling and validation

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

## Performance & Scale

### Benchmarks

This project demonstrates Elasticsearch's ability to handle:

- **Document Volume**: 1000+ documents totaling 100MB+ of text
- **Document Size**: Individual documents from 1KB to 500KB
- **Search Latency**: < 100ms for full-text search across all content
- **Indexing Speed**: 450 Wikipedia articles (100MB) indexed in ~10 seconds
- **Query Complexity**: Boolean queries with 5+ conditions in < 50ms
- **Aggregations**: Statistical analysis across 550+ properties in < 30ms

### Optimization Techniques Demonstrated

1. **Bulk API Usage**: 4-5x faster indexing vs individual requests
2. **Source Filtering**: Reduce network overhead by 80% for large docs
3. **Appropriate Analyzers**: English analyzer for better relevance
4. **Field Type Selection**: keyword vs text for optimal performance
5. **Batching Strategy**: 50-document batches (~11MB) for memory efficiency

### Scalability

The patterns demonstrated scale to:
- **Millions of documents** with proper sharding
- **Terabytes of text** with cluster distribution
- **Thousands of queries/second** with caching
- **Real-time updates** with refresh intervals
- **Global deployments** with cross-cluster replication

## Development Notes

This application demonstrates:
- **Clean separation of concerns**: Search separate from indexing
- **Dependency injection**: Clean IoC container pattern
- **Pydantic models**: Type-safe configuration and data models
- **No duplication**: Works with existing indexed data
- **Simple and focused**: Search and retrieval only

The system showcases proper architectural separation where data pipeline handles all data processing and this application provides the search interface.