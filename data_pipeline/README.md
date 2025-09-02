# Data Pipeline

## Project Overview

A high-performance data processing pipeline built on Apache Spark for transforming, enriching, and indexing real estate and Wikipedia data with advanced embedding generation capabilities. Features an **output-driven architecture** that automatically determines processing paths based on enabled destinations.

## Architecture

### Output-Driven Processing Paths

The pipeline uses an intelligent fork system that determines processing complexity based on your configured output destinations:

- **🗂️ Lightweight Path** (parquet-only): Minimal processing for basic data storage
- **📊 Graph Path** (neo4j + parquet): Entity extraction and relationship building for graph databases
- **🔍 Search Path** (elasticsearch + parquet): Document preparation and indexing for search engines

Processing paths are **automatically selected** based on `enabled_destinations` - no separate configuration needed!

## Generative AI Technologies

- **Apache Spark**: Distributed computing framework for processing large-scale datasets with ML capabilities
- **Voyage AI**: State-of-the-art embedding models optimized for semantic search (`voyage-3`, `voyage-large-2`)
- **Ollama**: Local LLM inference for privacy-preserving embedding generation
- **OpenAI Embeddings**: Industry-standard text embeddings with proven performance
- **Neo4j**: Graph database with vector similarity search and GDS algorithms
- **Elasticsearch**: Full-text and vector search with hybrid scoring capabilities
- **LlamaIndex**: Document processing and semantic chunking for optimal retrieval

## Quick Start

### 1. Set up environment variables
Create a `.env` file in the project root with your API keys:
```bash
VOYAGE_API_KEY=your-voyage-api-key
# Optional: Add these if using other providers
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
NEO4J_PASSWORD=your-neo4j-password
ES_PASSWORD=your-elastic-password
```

### 2. Run the pipeline
```bash
# Process full dataset with default config
python -m data_pipeline

# Process sample data (for testing)
python -m data_pipeline --sample-size 5

# Use custom configuration file
python -m data_pipeline --config path/to/custom.config.yaml

# Neo4j-only processing with sample data
python -m data_pipeline --config data_pipeline/neo4j.config.yaml --sample-size 2
```

### 3. Verify Elasticsearch
```bash
# Verify Elasticsearch indices and data
python data_pipeline/scripts/verify_elasticsearch.py

# Run Elasticsearch integration tests
python -m pytest data_pipeline/integration_tests/test_elasticsearch_writer.py -v
```

### 4. Verify Neo4j
```bash
# Verify Neo4j nodes and relationships
python -m graph_real_estate verify-nodes

# Run Neo4j integration tests
python -m pytest data_pipeline/integration_tests/test_neo4j_writer.py -v
```

## Configuration

### Configuration Files

The pipeline supports multiple configuration files for different use cases:

- **`config.yaml`** - Default configuration with parquet + elasticsearch output
- **`neo4j.config.yaml`** - Neo4j-only configuration for graph processing
- **Custom configs** - Use `--config path/to/custom.yaml` for your specific setup

All configurations use a **clean, hierarchical structure**:

### Output Destinations (determines processing paths automatically)

```yaml
output:
  enabled_destinations:
    - parquet          # Always recommended
    - elasticsearch    # Enables search path
    - neo4j           # Enables graph path
  
  # Parquet configuration
  parquet:
    base_path: data/processed
    compression: snappy
  
  # Neo4j configuration (if neo4j enabled)
  neo4j:
    uri: bolt://localhost:7687
    database: neo4j
    username: neo4j
    # Password from NEO4J_PASSWORD environment variable
  
  # Elasticsearch configuration (if elasticsearch enabled)
  elasticsearch:
    hosts:
      - localhost:9200
    username: elastic
    bulk_size: 1000
    # Password from ES_PASSWORD environment variable
```

### Embedding Configuration

```yaml
embedding:
  provider: voyage  # Options: voyage, openai, ollama, gemini, mock
  model_name: voyage-3  # voyage-3, voyage-large-2, voyage-code-2
  batch_size: 10    # Smaller for API rate limits
  dimension: 1024   # voyage-3: 1024, voyage-large-2: 1536
  # API keys loaded from environment variables
```

### Data Sources

```yaml
data_sources:
  properties_files:
    - real_estate_data/properties_sf.json
    - real_estate_data/properties_pc.json
  neighborhoods_files:
    - real_estate_data/neighborhoods_sf.json
    - real_estate_data/neighborhoods_pc.json
  wikipedia_db_path: data/wikipedia/wikipedia.db
  locations_file: real_estate_data/locations.json
```

### Spark Configuration

```yaml
spark:
  app_name: RealEstateDataPipeline
  master: local[*]
  driver_memory: 4g
  executor_memory: 2g
```

## Project Structure

```
data_pipeline/
├── config.yaml              # Main configuration file
├── neo4j.config.yaml        # Neo4j-only configuration
├── config/                  # Configuration models
│   ├── models.py           # Pydantic config models (hierarchical)
│   └── loader.py           # Config loading with environment secrets
├── core/                    # Core pipeline components
│   ├── pipeline_runner.py  # Main orchestrator
│   ├── pipeline_fork.py    # Output-driven processing paths
│   └── spark_session.py    # Spark session management
├── processing/              # Data processing
│   ├── base_embedding.py   # Base embedding generator
│   └── entity_embeddings.py # Entity-specific embeddings
├── loaders/                 # Data loaders
├── enrichment/              # Data enrichment & entity extraction
│   ├── property_enricher.py
│   ├── neighborhood_enricher.py
│   ├── wikipedia_enricher.py
│   ├── entity_extractors.py # Feature/type/price extraction
│   └── score_calculator.py  # Relationship scoring
├── writers/                 # Output writers
│   ├── parquet_writer.py
│   ├── orchestrator.py       # Writer orchestration
│   ├── base.py              # Base writer classes
│   ├── neo4j/               # Neo4j writer implementation
│   └── archive_elasticsearch/  # Elasticsearch writer (archived pattern)
├── models/                  # Data models
│   ├── graph_models.py     # Neo4j node/relationship models
│   └── spark_converter.py   # Spark DataFrame conversion
├── tests/                   # Unit tests
└── integration_tests/       # Integration tests
```

## Elasticsearch Setup

### Required JAR Installation

The pipeline requires the **Elasticsearch-Spark connector** for Spark 3.x compatibility. Here's how to install it:

```bash
# Download the correct Elasticsearch-Spark connector for Spark 3.x + Scala 2.12
cd lib/
curl -O https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-spark-30_2.12/9.0.0/elasticsearch-spark-30_2.12-9.0.0.jar
```

**Critical**: Do not use older connectors like:
- ❌ `elasticsearch-hadoop-8.15.2.jar` (Scala version incompatibility) 
- ❌ `elasticsearch-spark-20_2.11-8.15.2.jar` (Spark 2.x only)

**Required**: 
- ✅ `elasticsearch-spark-30_2.12-9.0.0.jar` (Spark 3.x + Scala 2.12)

### Authentication Setup

Elasticsearch requires authentication. Set your credentials:

```bash
export ES_PASSWORD=your-elastic-password
```

Or add to your `.env` file:
```
ES_PASSWORD=your-elastic-password
```

### Verification

Test the connection:
```bash
# Test with small sample
python -m data_pipeline --sample-size 2
```

You should see successful connection validation instead of:
- ❌ `Failed to find the data source: es` 
- ❌ `java.lang.NoClassDefFoundError: scala.Product$class`

## Processing Path Examples

### Lightweight Processing (parquet-only)
```yaml
output:
  enabled_destinations: [parquet]
```
- ✅ Minimal processing for data storage
- ✅ Fastest execution time
- ✅ No external service dependencies

### Graph Processing (neo4j + parquet)  
```yaml
output:
  enabled_destinations: [neo4j, parquet]
```
- ✅ Entity extraction (features, property types, price ranges, counties, topics)  
- ✅ Node creation in Neo4j (properties, neighborhoods, wikipedia, etc.)
- ✅ Graph database optimization
- ⚠️ **Note**: Relationships are created separately using `python -m graph_real_estate build-relationships`

### Search Processing (elasticsearch + parquet)
```yaml
output:
  enabled_destinations: [elasticsearch, parquet]
```
- ✅ Document preparation for search
- ✅ Full-text and vector indexing
- ✅ Search optimization

### Full Processing (all destinations)
```yaml
output:
  enabled_destinations: [parquet, neo4j, elasticsearch]
```
- ✅ Maximum functionality with both graph and search paths
- ✅ Enriched parquet files with all extracted entities

## Testing

```bash
# Run unit tests
python -m pytest data_pipeline/tests/ -v

# Run integration tests  
python -m pytest data_pipeline/integration_tests/ -v

# Test output-driven architecture specifically
python -m pytest data_pipeline/integration_tests/test_output_driven_integration.py -v

# Test pipeline fork logic
python -m pytest data_pipeline/tests/test_pipeline_fork.py -v

# Test with real API (requires VOYAGE_API_KEY)
python data_pipeline/integration_tests/test_real_voyage.py
```

## Command Line Options

- `--config PATH`: Specify custom configuration file (default: searches for config.yaml)
- `--sample-size N`: Process only N records from each data source (useful for testing)

All other configuration is handled via YAML files and environment variables for clean separation of concerns.

### Neo4j-Specific Workflow

For Neo4j graph processing, use the provided configuration:

```bash
# Step 1: Process and create nodes in Neo4j
python -m data_pipeline --config data_pipeline/neo4j.config.yaml --sample-size 5

# Step 2: Create relationships (future phase)
# python -m graph_real_estate build-relationships
```

The `neo4j.config.yaml` file:
- Enables **only** Neo4j output destination
- Sets `clear_before_write: true` to reset database
- Optimized for node-only creation (relationships handled separately)

## Outputs

Default output locations (configurable in `config.yaml`):
- **Parquet files**: `data/processed/`
- **Neo4j**: Local database at `bolt://localhost:7687` 
- **Elasticsearch**: Local instance at `localhost:9200`

The pipeline **automatically determines processing complexity** based on your enabled destinations:
- Enable only `parquet` → Lightweight path (fastest)
- Enable `neo4j` → Graph path (adds entity extraction)
- Enable `elasticsearch` → Search path (adds document preparation)
- Enable multiple → Multiple paths executed

## Processing Pipeline Flow

1. **Configuration Loading**: Load and validate `config.yaml` with environment secrets
2. **Path Determination**: Automatically select processing paths from output destinations
3. **Data Ingestion**: Load JSON data from multiple sources with Spark
4. **Data Enrichment**: Enhance properties with location data
5. **Embedding Generation**: Create vector representations using configured provider
6. **Path-Specific Processing**:
   - **Graph Path**: Entity extraction, relationship discovery
   - **Search Path**: Document preparation, indexing optimization  
   - **Lightweight Path**: Minimal processing for storage
7. **Output Writing**: Write to all configured destinations with optimized schemas

## Troubleshooting

### Performance Issues
- **Out of Memory**: Reduce sample size with `--sample-size 10`
- **Slow Processing**: Check if unnecessary destinations are enabled
- **API Rate Limits**: Reduce `embedding.batch_size` in `config.yaml`

### Connection Issues  
- **Neo4j**: Check service is running on port 7687, verify NEO4J_PASSWORD
- **Elasticsearch**: Check service is running on port 9200, verify ES_PASSWORD
- **API Keys**: Verify VOYAGE_API_KEY/OPENAI_API_KEY environment variables

### Configuration Issues
- **Invalid Config**: Check `config.yaml` syntax and required fields
- **Missing Files**: Check data source file paths in `data_sources` section  
- **Wrong Paths**: Check if paths are relative to correct working directory

### Path Selection
- Want faster processing? Use `enabled_destinations: [parquet]` only
- Need graph features? Add `neo4j` to destinations
- Need search features? Add `elasticsearch` to destinations
- The pipeline automatically optimizes processing based on your choices!

