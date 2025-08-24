# Data Pipeline - Apache Spark Processing

A multi-entity data pipeline for processing real estate and Wikipedia data with embeddings generation.

## Installation

From the project root directory:

```bash
pip install -e .
```

### Neo4j Setup

1. **Ensure Neo4j is running locally**:
   - Neo4j should be accessible at `bolt://localhost:7687`
   - Web interface available at `http://localhost:7474`

2. **Configure credentials**:
   - Add Neo4j credentials to `/Users/ryanknight/projects/temporal/.env`:
   ```
   NEO4J_PASSWORD=your_password_here
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_DATABASE=neo4j
   ```

3. **Neo4j Spark Connector**:
   - The connector JAR is already included in `lib/`
   - Using: `neo4j-connector-apache-spark_2.13-5.3.8_for_spark_3.jar`

## Quick Start

### Test Mode (Fastest - 10 records)
```bash
python -m data_pipeline --test-mode
```

### Development Mode (Default - 20 records)
```bash
python -m data_pipeline
```


## Command Line Options

### Data Subsetting
Control the amount of data processed for faster testing:

```bash
# Enable subsetting with default sample size
python -m data_pipeline --subset

# Specify exact sample size
python -m data_pipeline --subset --sample-size 50

# Choose sampling method
python -m data_pipeline --subset --sample-size 30 --sample-method random
```

### Embedding Models
Select different embedding providers and models:

```bash
# Use Voyage AI (default)
python -m data_pipeline --embedding-provider voyage

# Use local Ollama
python -m data_pipeline --embedding-provider ollama --embedding-model nomic-embed-text

# Use OpenAI
python -m data_pipeline --embedding-provider openai --embedding-model text-embedding-3-small

# Use mock embeddings for testing (no API calls)
python -m data_pipeline --embedding-provider mock
```

### Spark Configuration
Control Spark resource usage:

```bash
# Use specific number of cores
python -m data_pipeline --cores 4

# Use 2 cores with custom memory (set in config)
python -m data_pipeline --cores 2
```

### Output Options
Specify where results are saved:

```bash
# Custom output path
python -m data_pipeline --output /path/to/results

# Override output format via environment
OUTPUT_FORMAT=json python -m data_pipeline

# Write to Neo4j (when configured)
python -m data_pipeline --output-destination neo4j

# Write to multiple destinations
python -m data_pipeline --output-destination parquet,neo4j
```

### Operational Commands

```bash
# Show current configuration and exit
python -m data_pipeline --show-config

# Validate configuration without running
python -m data_pipeline --validate-only

# Set logging level
python -m data_pipeline --log-level DEBUG
```

## Environment-Based Configuration

The pipeline automatically adjusts settings based on environment:

### Development (default)
- Data subsetting: Enabled (20 records)
- Spark: local[2]
- Memory: 2GB
- Debug logging available


## Common Usage Patterns

### Quick Testing
```bash
# Fastest test with mock embeddings
python -m data_pipeline --test-mode --embedding-provider mock

# Test with 5 records using Voyage
python -m data_pipeline --subset --sample-size 5

# Test with specific cores
python -m data_pipeline --test-mode --cores 2
```

### Development Workflow
```bash
# Check configuration
python -m data_pipeline --show-config

# Validate setup
python -m data_pipeline --validate-only

# Run with debug logging
python -m data_pipeline --subset --sample-size 20 --log-level DEBUG
```


## Configuration

The pipeline uses a comprehensive configuration system:

- **Config file**: `data_pipeline/config.yaml`
- **Environment variables**: Override any setting
- **CLI arguments**: Highest priority

### Key Configuration Sections

- **data_subset**: Control data sampling for testing
- **embedding**: Configure embedding providers and models
- **spark**: Spark session settings
- **processing**: Quality checks and performance options
- **output**: Format and destination settings
- **output_destinations**: Configure multiple output destinations (Neo4j, Elasticsearch, Parquet)

## Environment Variables

Override configuration via environment variables:

```bash
# Data subsetting
export DATA_SUBSET_ENABLED=true
export DATA_SUBSET_SAMPLE_SIZE=50

# Embedding provider
export EMBEDDING_PROVIDER=voyage
export VOYAGE_API_KEY=your-key-here

# Neo4j settings (loaded from parent .env)
export NEO4J_PASSWORD=your-password
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j

# Spark settings
export SPARK_MASTER=local[4]

# Run with overrides
python -m data_pipeline
```

## Troubleshooting

### Check Configuration
```bash
python -m data_pipeline --show-config
```

### Validate Environment
```bash
python -m data_pipeline --validate-only
```

### Debug Mode
```bash
python -m data_pipeline --log-level DEBUG --test-mode
```

### Common Issues

**Out of Memory**: Reduce batch size or use fewer cores
```bash
python -m data_pipeline --cores 2 --subset --sample-size 10
```

**API Rate Limits**: Use mock provider for testing
```bash
python -m data_pipeline --embedding-provider mock
```

**Slow Processing**: Enable subsetting
```bash
python -m data_pipeline --subset --sample-size 20
```

**Neo4j Connection Issues**: Verify Neo4j is running and credentials are correct
```bash
# Test Neo4j connection
python -m data_pipeline.tests.test_neo4j_basic

# Check Neo4j is accessible
curl http://localhost:7474

# Verify credentials in .env file
cat /Users/ryanknight/projects/temporal/.env | grep NEO4J
```

**Spark/Scala Version Mismatch**: Ensure using correct Neo4j connector JAR
- Spark 4.0 requires Scala 2.13 version
- JAR should be: `neo4j-connector-apache-spark_2.13-5.3.8_for_spark_3.jar`

## Performance Tips

1. **For Testing**: Always use `--test-mode` or `--subset`
2. **For Development**: Use default settings (20 records)
3. **For Full Data**: Disable subsetting in config.yaml
4. **For Debugging**: Add `--log-level DEBUG`
5. **For Speed**: Use `--embedding-provider mock` during development

## Neo4j Testing

### Run Basic Neo4j Test
Test the Neo4j connection and write sample properties:

```bash
# Run the basic Neo4j test (writes 5 sample properties)
python -m data_pipeline.tests.test_neo4j_basic

# Expected output:
# ✅ Neo4j connection successful
# ✅ Successfully wrote 5 property nodes
# ✅ Read 5 property nodes from Neo4j
```

### Verify in Neo4j Browser
1. Open http://localhost:7474
2. Login with your configured credentials
3. Run Cypher queries:
   ```cypher
   // Count all Property nodes
   MATCH (p:Property) RETURN count(p);
   
   // View sample properties
   MATCH (p:Property) RETURN p LIMIT 10;
   
   // See property details
   MATCH (p:Property) 
   RETURN p.id, p.address, p.city, p.price 
   ORDER BY p.price DESC;
   ```

### Clear Neo4j Database
For testing, you may want to clear the database:

```bash
# Using Cypher in Neo4j Browser
MATCH (n) DETACH DELETE n;
```

## Examples

### Minimal Test Run
```bash
python -m data_pipeline --test-mode --embedding-provider mock
```

### Standard Development Run
```bash
python -m data_pipeline --subset --sample-size 30
```

### Full Data Run
```bash
python -m data_pipeline --cores 8
```

### Neo4j Pipeline Run
```bash
# Write to Neo4j with subset of data
python -m data_pipeline \
  --subset --sample-size 50 \
  --output-destination neo4j

# Write to both Parquet and Neo4j
python -m data_pipeline \
  --subset --sample-size 100 \
  --output-destination parquet,neo4j
```

### Custom Configuration
```bash
python -m data_pipeline \
  --subset --sample-size 100 \
  --embedding-provider voyage \
  --embedding-model voyage-3 \
  --cores 4 \
  --output ./results/test_run
```

## Next Steps

- Review configuration: `data_pipeline/config.yaml`
- Check logs: `logs/pipeline.log`
- Monitor output: `data/processed/entity_datasets/`
- Validate results: Use `--validate-only` before production runs