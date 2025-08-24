# Data Pipeline

A comprehensive Apache Spark data pipeline for processing real estate and Wikipedia data with embeddings generation and multi-destination output support.

## Project Structure

This is a standalone Python module that can be run independently. All configuration and dependencies are self-contained within this directory.

```
data_pipeline/
├── config.yaml          # Main configuration file
├── pyproject.toml       # Project dependencies and metadata
├── README.md            # This file
├── __main__.py          # CLI entry point
├── core/                # Core pipeline components
├── loaders/             # Data loading modules
├── enrichment/          # Data enrichment engines
├── processing/          # Text and embedding processing
├── writers/             # Multi-destination output writers
├── integration_tests/   # Integration test suite
└── tests/               # Unit tests
```

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

### Quick Neo4j Data Load

```bash
# 2. Load sample data to Neo4j (fast test)
python -m data_pipeline --sample-size 50 --output-destination parquet, neo4j

# 3. Load full dataset to Neo4j (requires Spark connector - see setup below)
python -m data_pipeline --output-destination neo4j

# 4. Verify in Neo4j Browser at http://localhost:7474
# Login: neo4j/scott_tiger
# Run: MATCH (n) RETURN labels(n)[0] as type, COUNT(n) as count
```

### Basic Usage

Run from the parent directory:

```bash
# Full pipeline run
python -m data_pipeline

# Run with limited sample size (50 records)
python -m data_pipeline --sample-size 50

# Run with specific output destinations
python -m data_pipeline --output-destination neo4j
python -m data_pipeline --output-destination elasticsearch
python -m data_pipeline --output-destination parquet,neo4j
```

### Quick Testing

```bash
# Test mode (10 records, mock embeddings)
python -m data_pipeline --test-mode

# Quick test with real embeddings (20 records)
python -m data_pipeline --sample-size 20

# Test specific output destination
python -m data_pipeline --sample-size 10 --output-destination neo4j
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
    -e NEO4J_AUTH=neo4j/scott_tiger \
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
# Default credentials: neo4j/scott_tiger
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
python -m data_pipeline --sample-size 100 --output-destination neo4j

# Load specific entity types only
python -m data_pipeline --output-destination neo4j --entities properties,neighborhoods

# Load to both Neo4j and Parquet
python -m data_pipeline --output-destination neo4j,parquet
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

#### 5. Alternative: Direct Neo4j Loading (Without Spark Connector)

If the Spark connector is not available, use the direct Python driver approach:

```bash
# Use the direct Neo4j writer (bypasses Spark connector requirement)
python -m data_pipeline.writers.neo4j.direct_writer

# Or load from existing Parquet files
python -m data_pipeline.tools.parquet_to_neo4j \
    --parquet-path data/entities/ \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password scott_tiger
```

### Neo4j Testing

```bash
# Test Neo4j connection
python -c "from neo4j import GraphDatabase; \
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'scott_tiger')); \
with driver.session() as session: \
    result = session.run('RETURN 1 as test'); \
    print('Neo4j connection successful:', result.single()['test']); \
driver.close()"

# Run pipeline with Neo4j output
python -m data_pipeline --sample-size 50 --output-destination neo4j

# Verify in Neo4j Browser (http://localhost:7474)
MATCH (p:Property) RETURN count(p);
```

### Elasticsearch Testing

```bash
# Run pipeline with Elasticsearch output
python -m data_pipeline --sample-size 50 --output-destination elasticsearch

# Verify data in Elasticsearch
curl -X GET "localhost:9200/_cat/indices?v"
curl -X GET "localhost:9200/properties/_count"
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
  password: "scott_tiger"  # Default password
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
NEO4J_PASSWORD=scott_tiger
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

### Operational Options

```bash
# Show current configuration
python -m data_pipeline --show-config

# Validate configuration without running
python -m data_pipeline --validate-only

# Set logging level
python -m data_pipeline --log-level DEBUG

# Spark cores
python -m data_pipeline --cores 4
```

## Overview

### Architecture

The pipeline processes data through these stages:
1. **Data Loading**: Read properties and Wikipedia articles
2. **Embeddings Generation**: Create vector representations using configured provider
3. **Data Writing**: Output to configured destinations (Parquet, Neo4j, Elasticsearch)

### Supported Data Entities
- **Properties**: Real estate listings with location and features
- **Wikipedia Articles**: Location-based content with summaries
- **Neighborhoods**: Geographic areas with demographic data

### Output Destinations
- **Parquet**: Default file-based storage for analytics
- **Neo4j**: Graph database for relationship queries
- **Elasticsearch**: Search engine for full-text and vector search

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

## Performance Tips

1. **Development**: Use `--sample-size 20-50` for quick iterations
2. **Testing**: Use `--test-mode` for fastest feedback
3. **Production**: Run without sample-size limit
4. **Debugging**: Always add `--log-level DEBUG`
5. **Multiple Destinations**: Test each destination separately first

## Project Structure

```
data_pipeline/
├── config/              # Configuration management
├── core/                # Core pipeline components  
├── loaders/             # Data loading modules
├── enrichment/          # Data enrichment engines
├── processing/          # Text and embedding processing
├── writers/             # Multi-destination output writers
├── integration_tests/   # Integration test suite
├── tests/               # Unit tests
└── examples/            # Usage examples
```

## Next Steps

- Review configuration: `config.yaml`
- Check logs: `logs/pipeline.log`
- Monitor output: `data/processed/entity_datasets/`
- Explore data in target systems (Neo4j Browser, Elasticsearch, Parquet files)