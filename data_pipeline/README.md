# Data Pipeline

A comprehensive Spark-based data pipeline for processing real estate, neighborhood, and Wikipedia data with embedding generation and multi-destination output support.

## Overview

The data pipeline provides:

- **Multi-source data loading**: Properties, neighborhoods, Wikipedia articles, and location reference data
- **Location data integration**: Geographic hierarchy resolution and property-neighborhood linking
- **Entity-specific enrichment**: Data normalization, quality scoring, and correlation ID generation
- **Embedding generation**: Support for multiple providers (Voyage, OpenAI, Gemini, Ollama)
- **Multi-destination output**: Parquet files, Neo4j graph database, Elasticsearch, and ChromaDB
- **Data validation**: Schema validation, completeness checks, and quality metrics
- **Configurable environments**: Development, test, and production configurations

## Quick Start

### Prerequisites

- Python 3.8+ (3.10+ recommended)
- Apache Spark 3.4+
- 4GB+ RAM recommended

### Installation

```bash
# Install from the root directory
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Run the full pipeline with embeddings
python -m data_pipeline

# Run with specific environment
PIPELINE_ENV=test python -m data_pipeline

# Run with data subsetting for testing
DATA_SUBSET_SAMPLE_SIZE=50 python -m data_pipeline

# Run with specific output destinations
OUTPUT_DESTINATIONS=parquet,neo4j python -m data_pipeline
```

### Python API

```python
from data_pipeline.core.pipeline_runner import DataPipelineRunner

# Initialize and run pipeline
runner = DataPipelineRunner()
entity_dataframes = runner.run_full_pipeline_with_embeddings()
runner.write_entity_outputs(entity_dataframes)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PIPELINE_ENV` | Environment (dev/test/prod) | `dev` |
| `DATA_SUBSET_SAMPLE_SIZE` | Sample size for testing | Disabled |
| `OUTPUT_DESTINATIONS` | Comma-separated destinations | `parquet` |
| `OUTPUT_PATH` | Output directory path | `data/processed` |
| `NEO4J_URI` | Neo4j database URI | `bolt://localhost:7687` |
| `ES_HOSTS` | Elasticsearch hosts | `localhost:9200` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Configuration Files

- **`config.yaml`**: Main pipeline configuration
- **`config/pipeline_config.yaml`**: Environment-specific overrides
- **`elasticsearch_config.yaml`**: Elasticsearch-specific settings

### Location Data Integration

Configure location enhancement in `config.yaml`:

```yaml
enrichment:
  location_enhancement:
    enabled: true
    hierarchy_resolution: true
    name_standardization: true
    neighborhood_linking: true
```

- **hierarchy_resolution**: Enable geographic hierarchy (neighborhood → city → county → state)
- **name_standardization**: Use canonical location names
- **neighborhood_linking**: Link properties to neighborhoods via neighborhood_id

## Data Sources

### Input Data
- **Properties**: `real_estate_data/properties_*.json`
- **Neighborhoods**: `real_estate_data/neighborhoods_*.json`
- **Wikipedia**: `data/wikipedia/wikipedia.db`
- **Locations**: `real_estate_data/locations.json`

### Output Destinations

#### Parquet Files
- Path: `data/processed/entity_datasets/`
- Files: `properties.parquet`, `neighborhoods.parquet`, `wikipedia.parquet`
- Features: Snappy compression, optimized partitioning

#### Neo4j Graph Database
- Nodes: Properties, Neighborhoods, Wikipedia articles, Locations
- Relationships: Geographic and semantic connections
- Indexes: Automatic creation for performance

#### Elasticsearch
- Indices: Separate indices per entity type
- Features: Full-text search, embedding vector search
- Mappings: Optimized for search and analytics

#### ChromaDB Vector Database
- Collections: Separate collections per entity type
- Features: Similarity search, metadata filtering
- Embeddings: Multi-provider support

## Pipeline Architecture

### Core Components

1. **Data Loaders**: Entity-specific loaders with validation
2. **Enrichers**: Data normalization and quality scoring
3. **Text Processors**: Content preparation for embeddings
4. **Embedding Generators**: Multi-provider embedding creation
5. **Writers**: Multi-destination output orchestration

### Processing Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Loading  │───▶│   Enrichment    │───▶│ Text Processing │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│ Multi-Output    │◀───│ Embedding Gen   │◀─────────────┘
│ Writing         │    │                 │
└─────────────────┘    └─────────────────┘
```

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest data_pipeline/tests/

# Run with coverage
pytest data_pipeline/tests/ --cov=data_pipeline

# Run specific test file
pytest data_pipeline/tests/test_writer_config.py
```

### Integration Tests

The integration test suite provides comprehensive validation of the entity-specific Parquet writer architecture.

#### Quick Start
```bash
# Run all Parquet validation tests (~75 seconds)
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py -v

# Run quick smoke test (~18 seconds)
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py::test_quick_parquet_smoke -v

# Run with coverage
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py --cov=data_pipeline
```

#### Test Suite Components

**test_parquet_validation.py** - Comprehensive Parquet validation (7 tests)
1. `test_parquet_files_structure` - Validates entity-specific directory structure with partitioning
2. `test_parquet_schema_compliance` - Ensures correct schemas for each entity type
3. `test_parquet_data_completeness` - Verifies all records have embeddings and required fields
4. `test_wikipedia_array_fields_populated` - Validates Wikipedia summary fields
5. `test_embedding_dimensions_consistency` - Ensures consistent 1024-D embeddings
6. `test_parquet_compression_and_size` - Validates file compression and sizes
7. `test_quick_parquet_smoke` - Quick smoke test for basic functionality

#### Key Features

**Entity-Specific Architecture**:
- Separate Parquet files for properties, neighborhoods, and Wikipedia entities
- Partitioning by state for properties and neighborhoods
- Type-safe Pydantic models for all configurations
- No unified dataset approach - clean separation of concerns

**Test Configuration**:
- Uses temporary directories for isolation
- Configuration override support via `config_override` parameter
- No environment variable dependency for output paths
- Automatic cleanup after test completion

**Validation Capabilities**:
- Schema validation against entity-specific schemas
- Partitioned file structure validation (e.g., `state=California/part-*.parquet`)
- Embedding dimension consistency checks
- Data completeness verification
- File size and compression validation

#### Running Specific Tests

```bash
# Test file structure with partitioning
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py::TestParquetValidation::test_parquet_files_structure -v

# Test schema compliance
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py::TestParquetValidation::test_parquet_schema_compliance -v

# Test data completeness
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py::TestParquetValidation::test_parquet_data_completeness -v
```

#### Test Output Example

```
============================= test session starts ==============================
collecting ... collected 7 items

test_parquet_validation.py::TestParquetValidation::test_parquet_files_structure PASSED [ 14%]
test_parquet_validation.py::TestParquetValidation::test_parquet_schema_compliance PASSED [ 28%]
test_parquet_validation.py::TestParquetValidation::test_parquet_data_completeness PASSED [ 42%]
test_parquet_validation.py::TestParquetValidation::test_wikipedia_array_fields_populated PASSED [ 57%]
test_parquet_validation.py::TestParquetValidation::test_embedding_dimensions_consistency PASSED [ 71%]
test_parquet_validation.py::TestParquetValidation::test_parquet_compression_and_size PASSED [ 85%]
test_parquet_validation.py::test_quick_parquet_smoke PASSED [100%]

================== 7 passed in 73.28s ==================
```

#### Integration with CI/CD

```bash
# For CI pipelines - quick validation
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py::test_quick_parquet_smoke

# For release validation - full suite
PYTHONPATH=$PWD:$PYTHONPATH python -m pytest data_pipeline/integration_tests/test_parquet_validation.py -v --tb=short
```

## Performance and Scaling

### Optimization Tips

- **Data Subsetting**: Use `DATA_SUBSET_SAMPLE_SIZE` for development
- **Spark Configuration**: Adjust memory and cores in `config.yaml`
- **Embedding Batch Size**: Tune based on API rate limits
- **Partitioning**: Enable Parquet partitioning for large datasets

### Resource Requirements

| Dataset Size | Memory | Cores | Time |
|--------------|--------|-------|------|
| Small (1K records) | 4GB | 2 | 2-5 min |
| Medium (10K records) | 8GB | 4 | 10-15 min |
| Large (100K+ records) | 16GB+ | 8+ | 30+ min |

## Monitoring and Debugging

### Logging

The pipeline provides structured logging at multiple levels:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python -m data_pipeline

# Log to file
LOG_LEVEL=INFO python -m data_pipeline > pipeline.log 2>&1
```

### Health Checks

```bash
# Validate configuration
python data_pipeline/examples/test_configuration.py

# Test database connections
python -c "from data_pipeline.core.pipeline_runner import DataPipelineRunner; runner = DataPipelineRunner(); print('✓ Configuration valid')"
```

### Common Issues

**Spark Memory Errors**
```bash
# Increase driver memory
export SPARK_DRIVER_MEMORY=8g
python -m data_pipeline
```

**API Rate Limits**
```yaml
# Reduce batch size in config.yaml
embedding:
  batch_size: 10
  retry_delay: 2.0
```

**Column Ambiguity Warnings**
- These are non-fatal Spark SQL warnings
- Pipeline continues to execute successfully
- Can be ignored for current functionality

## Development

## Architecture

### Entity-Specific Design Philosophy

The data pipeline follows a **strict entity-specific architecture** with these core principles:

1. **No Unified Datasets**: Each entity type (properties, neighborhoods, Wikipedia) maintains its own separate processing pipeline and output structure
2. **Type Safety First**: Pydantic models provide compile-time type checking and runtime validation
3. **Modular Writers**: Each destination (Parquet, Neo4j, Elasticsearch) has dedicated orchestrators with entity-aware logic
4. **Clean Separation**: Entity-specific processors, enrichers, and schemas ensure no cross-contamination of logic

### Key Architectural Benefits

- **Maintainability**: Changes to one entity type don't affect others
- **Scalability**: Each entity can be scaled independently
- **Testing**: Entity-specific tests are simpler and more focused
- **Type Safety**: Strong typing prevents runtime errors
- **Flexibility**: Easy to add new entity types or destinations

### Project Structure

```
data_pipeline/
├── config/          # Configuration management
├── core/           # Core pipeline components  
├── loaders/        # Data loading modules
├── enrichment/     # Data enrichment engines
├── processing/     # Text and embedding processing
├── writers/        # Multi-destination output writers
├── integration_tests/  # Integration test suite
├── tests/          # Unit tests
└── examples/       # Usage examples
```

### Adding New Features

1. **New Data Sources**: Extend `loaders/`
2. **New Enrichments**: Add to `enrichment/`
3. **New Output Destinations**: Implement in `writers/`
4. **New Tests**: Add to `integration_tests/` or `tests/`

### Configuration Schema

The pipeline uses Pydantic models for configuration validation. See `config/models.py` for the complete schema.

## Contributing

1. Follow existing code patterns and naming conventions
2. Add tests for new functionality
3. Update documentation for new features
4. Ensure integration tests pass before submitting changes

```bash
# Run full test suite before contributing
python data_pipeline/integration_tests/run_tests.py full
pytest data_pipeline/tests/ --cov=data_pipeline
```

## License

This project is part of the Property Finder real estate data analysis suite.