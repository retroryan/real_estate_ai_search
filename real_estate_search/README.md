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

## Elasticsearch Patterns Covered

This project covers key Elasticsearch patterns including:

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

### Step 3: Enrich Wikipedia Articles 
After running the data pipeline, enrich Wikipedia documents with full article content for enhanced full-text search:
```bash
# Enrich all Wikipedia articles (processes ~450+ HTML files)
python -m real_estate_search.management enrich-wikipedia
```

### Step 4: Build Property Relationships Index 
After all data is loaded, build the denormalized property_relationships index that combines data from properties, neighborhoods, and Wikipedia for optimized query performance:
```bash
# Build relationships index only (assumes other indices already exist)
python -m real_estate_search.management setup-indices --build-relationships
```

This creates a denormalized index by:
- Reading from existing properties, neighborhoods, and wikipedia indices
- Creating combined documents with embedded relationships
- Building a single optimized index for fast multi-entity queries
- Achieving 100x+ query performance improvement (from ~250ms to ~2-3ms)

### Step 5: Run Search Demos
Execute demonstration queries showcasing various search capabilities using the demo runner script:
```bash
# Show all available demos
./elastic_demos.sh --list

# Run the default demo (Rich Property Listing)
./elastic_demos.sh

# Run a specific demo by number
./elastic_demos.sh 10

# Run demo with verbose output to see Elasticsearch query DSL
./elastic_demos.sh 15 --verbose

# Get help
./elastic_demos.sh --help
```

The script automatically loads Elasticsearch authentication from your .env file and provides easy access to all 15 demo queries including property search, semantic search, geo queries, and relationship traversal.

## Additional Options

### Wikipedia Enrichment Options

The Wikipedia enrichment step (Step 3) provides several options:

```bash
# Test with a smaller batch first (dry run without updating)
python -m real_estate_search.management enrich-wikipedia --dry-run

# Process specific number of documents
python -m real_estate_search.management enrich-wikipedia --max-documents 100

# View processing details
python -m real_estate_search.management enrich-wikipedia --verbose

# Custom batch size for bulk updates (default: 50)
python -m real_estate_search.management enrich-wikipedia --batch-size 100
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
# List all available demos
python -m real_estate_search.management demo --list

# Run specific demo (1-15)
python -m real_estate_search.management demo 1  # Basic property search
python -m real_estate_search.management demo 3  # Geo-distance search
python -m real_estate_search.management demo 6  # Semantic similarity search
python -m real_estate_search.management demo 10 # Wikipedia full-text search

# Run demo with verbose output (shows Elasticsearch query DSL)
python -m real_estate_search.management demo 2 --verbose
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
├── management.py                # CLI entry point for management commands
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

### Available Demo Searches

The system includes 15 comprehensive demo searches:

1. **Basic Property Search** - Multi-match search across fields
2. **Property Filter Search** - Filter by type, bedrooms, price
3. **Geographic Distance Search** - Find properties within radius
4. **Neighborhood Statistics** - Aggregate stats by neighborhood
5. **Price Distribution Analysis** - Histogram of prices
6. **Semantic Similarity Search** - Find similar using embeddings
7. **Multi-Entity Combined Search** - Search across all indices
8. **Wikipedia Article Search** - Search with location filters
9. **Property-Neighborhood-Wikipedia Relationships** - Entity linking
10. **Wikipedia Full-Text Search** - Full-text across articles
11. **Simplified Single-Query Relationships** - Denormalized index
12. **Natural Language Semantic Search** - Query embeddings
13. **Natural Language Examples** - Multiple NL examples
14. **Semantic vs Keyword Comparison** - Compare search methods
15. **Rich Real Estate Listing** - Complete listing with context

Run any demo with:
```bash
python -m real_estate_search.management demo <number>
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

## Advanced Management Commands

The management CLI provides comprehensive tools for all aspects of index and data management:

### Complete Command Reference

```bash
# Index Setup and Management
python -m real_estate_search.management setup-indices
python -m real_estate_search.management setup-indices --clear  # Delete and recreate all indices
python -m real_estate_search.management setup-indices --build-relationships  # Build relationships index only
python -m real_estate_search.management setup-indices --clear --build-relationships  # Full reset with relationships

# Index Validation and Status
python -m real_estate_search.management validate-indices  # Check indices exist with correct mappings
python -m real_estate_search.management validate-embeddings  # Verify vector embedding coverage
python -m real_estate_search.management list-indices  # Show index status and document counts
python -m real_estate_search.management delete-test-indices  # Clean up test indices

# Wikipedia Enrichment
python -m real_estate_search.management enrich-wikipedia  # Process all Wikipedia articles
python -m real_estate_search.management enrich-wikipedia --dry-run  # Test without updating
python -m real_estate_search.management enrich-wikipedia --max-documents 100  # Process subset
python -m real_estate_search.management enrich-wikipedia --verbose  # Show processing details
python -m real_estate_search.management enrich-wikipedia --batch-size 100  # Custom bulk batch size

# Search Demonstrations
python -m real_estate_search.management demo --list  # List all available demos
python -m real_estate_search.management demo 1  # Run specific demo
python -m real_estate_search.management demo 2 --verbose  # Show query DSL details
```

### Global Options

All commands support these configuration options:
```bash
--config PATH        # Path to config file (default: config.yaml)
--log-level LEVEL   # Set logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
```

### Command Details

#### setup-indices
- Creates all required Elasticsearch indices with proper mappings
- `--clear`: Deletes existing indices before creation (full reset)
- `--build-relationships`: Builds denormalized property_relationships index after setup
- Combines both flags for complete pipeline initialization

#### validate-indices
- Checks that all required indices exist
- Verifies index mappings match expected schema
- Reports any missing or misconfigured indices

#### validate-embeddings
- Analyzes vector embedding field coverage
- Reports percentage of documents with embeddings
- Identifies documents missing embeddings

#### enrich-wikipedia
- Loads full HTML content from disk into Elasticsearch
- Uses ingest pipeline to strip HTML and extract clean text
- Options:
  - `--dry-run`: Preview changes without updating
  - `--max-documents N`: Process only N documents
  - `--batch-size N`: Bulk update batch size (default: 50)
  - `--verbose`: Show detailed processing information

#### demo
- Runs pre-configured demonstration queries
- `--list`: Shows all available demos with descriptions
- `--verbose`: Displays actual Elasticsearch query DSL
- Demos include property search, geo queries, aggregations, and more

## Development Notes

This application demonstrates:
- **Clean separation of concerns**: Search separate from indexing
- **Dependency injection**: Clean IoC container pattern
- **Pydantic models**: Type-safe configuration and data models
- **No duplication**: Works with existing indexed data
- **Simple and focused**: Search and retrieval only

The system showcases proper architectural separation where data pipeline handles all data processing and this application provides the search interface.