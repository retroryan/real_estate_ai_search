# Spark Data Pipeline

## Project Overview

A high-performance data processing pipeline built on Apache Spark for transforming, enriching, and indexing real estate and Wikipedia data with advanced embedding generation capabilities. Designed for scalable AI-powered search and recommendation systems.

## Generative AI Technologies

- **LlamaIndex**: Document processing and semantic chunking for optimal retrieval
- **Neo4j**: Graph database with HNSW-based vector indexes for KNN search, cosine/euclidean similarity, and Graph Data Science algorithms
- **Elasticsearch**: Dense vector search with HNSW algorithm, int8/int4 quantization, and hybrid BM25+KNN scoring
- **Voyage AI**: State-of-the-art embedding models optimized for semantic search
- **Ollama**: Local LLM inference for privacy-preserving embedding generation
- **OpenAI Embeddings**: Industry-standard text embeddings with proven performance

## Quick Start

### Installation

From the parent directory (real_estate_ai_search):

```bash
pip install -e data_pipeline/
```

Or from within this directory:

```bash
pip install -e .
```

```bash
# Install the module (from parent directory)
pip install -e data_pipeline/

# Run test pipeline (10 records, mock embeddings)
python -m data_pipeline --test-mode

# Process with real embeddings (50 records)
python -m data_pipeline --sample-size 50

# Load to Neo4j graph database
python -m data_pipeline --sample-size 100 --output-destination neo4j

# Load to Elasticsearch for search
python -m data_pipeline --sample-size 100 --output-destination elasticsearch

# Full pipeline with all destinations
python -m data_pipeline --output-destination parquet,neo4j,elasticsearch
```

## Integration Testing

### Parquet Testing

```bash
# Run quick smoke test
pytest data_pipeline/integration_tests/test_parquet_validation.py::test_quick_parquet_smoke -v

# Run all parquet tests
pytest data_pipeline/integration_tests/test_parquet_validation.py -v
```

### Neo4j Setup and Data Loading

#### 1. Start Neo4j Database

```bash
# Using Docker (recommended)
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    -v $HOME/neo4j/data:/data \
    -v $HOME/neo4j/logs:/logs \
    neo4j:latest

# Or if you have docker-compose in graph-real-estate/
cd ../graph-real-estate
docker-compose up -d neo4j

# Verify Neo4j is running
curl http://localhost:7474
# Access Neo4j Browser at http://localhost:7474
# Default credentials: neo4j/password
```

#### 2. Install Neo4j Spark Connector (Required for Spark Integration)

```bash
# Download the Neo4j Spark Connector JAR
wget https://github.com/neo4j/neo4j-spark-connector/releases/download/5.2.0/neo4j-connector-apache-spark_2.12-5.2.0_for_spark_3.jar

# Create jars directory in data_pipeline
mkdir -p data_pipeline/jars

# Move the JAR file
mv neo4j-connector-apache-spark_2.12-5.2.0_for_spark_3.jar data_pipeline/jars/

# Alternative: Install via pip (if available)
pip install pyspark-neo4j
```

#### 3. Load Full Dataset to Neo4j

```bash
# Load complete dataset (all properties, neighborhoods, and Wikipedia articles)
python -m data_pipeline --output-destination neo4j

# Load with sample data for testing (faster)
python -m data_pipeline --sample-size 5 --output-destination neo4j

# Load specific entity types only
python -m data_pipeline --output-destination neo4j --entities properties,neighborhoods

# Load to both Neo4j and Parquet
python -m data_pipeline --output-destination neo4j,elasticsearch,parquet
```

#### 4. Verify Data in Neo4j

```cypher
-- Count all nodes
MATCH (n) RETURN labels(n)[0] as NodeType, COUNT(n) as Count;

-- Sample properties
MATCH (p:Property) RETURN p LIMIT 5;

-- Properties with neighborhoods
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
RETURN p.address, n.name, p.price LIMIT 10;

-- Wikipedia articles describing locations
MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n:Neighborhood)
RETURN w.title, n.name LIMIT 10;

-- Property similarity relationships
MATCH (p1:Property)-[s:SIMILAR_TO]->(p2:Property)
WHERE s.similarity_score > 0.8
RETURN p1.address, p2.address, s.similarity_score LIMIT 10;
```

## Configuration

### Configuration File

The pipeline uses `config.yaml` in this directory for all settings:

- **data_subset**: Control data sampling
- **embedding**: Provider and model settings (Voyage, Ollama, OpenAI)
- **spark**: Session and resource settings
- **output_destinations**: Configure Neo4j, Elasticsearch, Parquet outputs

### Environment Setup

#### Neo4j Configuration
The pipeline is pre-configured for Neo4j. Current settings in `config.yaml`:
```yaml
neo4j:
  enabled: false  # Change to true to enable
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "password"
  database: "neo4j"
```

To enable Neo4j output:
1. Edit `data_pipeline/config.yaml`
2. Set `neo4j.enabled: true`
3. Or add "neo4j" to `enabled_destinations` list

Alternative: Use command line (overrides config):
```bash
python -m data_pipeline --output-destination neo4j
```

Parent `.env` file (`/Users/ryanknight/projects/temporal/.env`):
```bash
NEO4J_PASSWORD=password
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_DATABASE=neo4j
```

#### Elasticsearch
Default connection (no auth required for local) - Elasticsearch should be running on `localhost:9200`

#### API Keys
Add to `.env` for embeddings:
```bash
VOYAGE_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

## Command Line Options

### Core Options

```bash
# Sample size control
python -m data_pipeline --sample-size 100

# Test mode (10 records, mock embeddings)
python -m data_pipeline --test-mode

# Output destinations
python -m data_pipeline --output-destination neo4j
python -m data_pipeline --output-destination elasticsearch
python -m data_pipeline --output-destination parquet,neo4j,elasticsearch

# Custom output path
python -m data_pipeline --output /path/to/results
```

## Spark Data Pipeline Flow

### Processing Pipeline
1. **Data Ingestion**: Load JSON/CSV data from multiple sources using Spark DataFrames
2. **Data Enrichment**: Enhance properties with location data, calculate derived features
3. **Embedding Generation**: Create vector representations using configured AI provider
4. **Relationship Discovery**: Identify similarities and connections between entities
5. **Multi-Destination Output**: Write to Parquet, Neo4j, and Elasticsearch simultaneously

### Architecture Overview

```
Data Sources → Spark Processing → Enrichment → Embeddings → Output Writers
     ↓              ↓                ↓            ↓              ↓
[JSON/CSV]    [DataFrames]    [Location]   [Voyage/Ollama]  [Storage]
                                    ↓                           ↓
                              [Features]                   [Neo4j Graph]
                                                           [Elasticsearch]
                                                           [Parquet Files]
```

### Supported Data Entities
- **Properties**: Real estate listings with addresses, prices, features, and amenities
- **Wikipedia Articles**: Location-based content with geographic context
- **Neighborhoods**: Geographic boundaries with demographic and statistical data

### Output Destinations
- **Parquet**: Columnar storage for analytics and data science workflows
- **Neo4j**: Graph database for relationship traversal and similarity search
- **Elasticsearch**: Full-text and vector search with faceted filtering

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest data_pipeline/tests/

# Run with coverage
pytest data_pipeline/tests/ --cov=data_pipeline
```

### Integration Tests

```bash
# Quick validation test
pytest data_pipeline/integration_tests/test_parquet_validation.py::test_quick_parquet_smoke -v

# Full integration test suite
pytest data_pipeline/integration_tests/ -v
```

## Troubleshooting

### Common Issues

**Out of Memory**
```bash
python -m data_pipeline --cores 2 --sample-size 10
```

**API Rate Limits**
```bash
# Use mock provider for testing
python -m data_pipeline --test-mode
```

**Neo4j Connection Issues**
```bash
# Test connection
python -m data_pipeline.tests.test_neo4j_basic

# Check Neo4j is running
curl http://localhost:7474
```

**Elasticsearch Connection Issues**
```bash
# Check Elasticsearch is running
curl http://localhost:9200

# Test with small dataset
python -m data_pipeline --sample-size 5 --output-destination elasticsearch
```

### Debug Commands

```bash
# Maximum debugging
python -m data_pipeline --log-level DEBUG --test-mode

# Check logs
tail -f logs/pipeline.log
```

## Output Validation

### Parquet Files
```bash
# Check output files
ls -la data/processed/entity_datasets/*.parquet

# Validate with pandas
python -c "import pandas as pd; df = pd.read_parquet('data/processed/entity_datasets/properties.parquet'); print(df.info())"
```

### Neo4j Data
```cypher
-- Count nodes by type
MATCH (n) RETURN labels(n), count(n);

-- Sample property data
MATCH (p:Property) RETURN p LIMIT 5;
```

### Elasticsearch Data
```bash
# Check indices
curl -X GET "localhost:9200/_cat/indices?v"

# Sample search
curl -X GET "localhost:9200/properties/_search?q=city:Seattle&size=5"
```

## Advanced Usage

### Configuration Management

```yaml
# config.yaml - Key settings
data_subset:
  enabled: true
  sample_size: 100  # Limit data for testing

embedding:
  provider: voyage  # or ollama, openai
  batch_size: 100
  
output_destinations:
  enabled_destinations:
    - parquet
    - neo4j
    - elasticsearch
```

### Environment Variables

```bash
# Set API keys in .env file
VOYAGE_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
NEO4J_PASSWORD=your-password
```

### Batch Processing

```bash
# Process in batches with checkpointing
python -m data_pipeline \
  --batch-size 1000 \
  --checkpoint-dir /tmp/spark-checkpoint
```

### Additional Commands

```bash
# Show current configuration
python -m data_pipeline --show-config

# Validate configuration only
python -m data_pipeline --validate-only

# Set logging level
python -m data_pipeline --log-level DEBUG

# Specify CPU cores
python -m data_pipeline --cores 4
```