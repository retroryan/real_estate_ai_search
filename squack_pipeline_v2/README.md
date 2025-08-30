# SQUACK Pipeline V2 - DuckDB Medallion Architecture

A clean, efficient data pipeline following DuckDB best practices and medallion architecture principles.

## Overview

SQUACK Pipeline V2 is a complete rewrite of the original pipeline, implementing:
- **Medallion Architecture**: Bronze → Silver → Gold data tiers
- **DuckDB Best Practices**: SQL-first transformations, direct file operations
- **Clean Separation**: Each stage has a single responsibility
- **Type Safety**: Pydantic V2 models for validation at boundaries
- **Efficient Processing**: No row-by-row operations, all set-based SQL

## Architecture

```
Bronze Layer (Raw Ingestion)
    ↓
Silver Layer (Standardization)
    ↓
Gold Layer (Enrichment)
    ↓
Embeddings (Vector Generation)
    ↓
Writers (Parquet/Elasticsearch)
```

## Quick Start

### Installation

```bash
# Ensure you're in the real_estate_ai_search directory
cd real_estate_ai_search

# Install dependencies (if not already installed)
pip install -e .
```

### Basic Usage

```bash
# Run full pipeline
python -m squack_pipeline_v2

# Test with sample data
python -m squack_pipeline_v2 --sample-size 100

# Process specific entities
python -m squack_pipeline_v2 --entities property neighborhood

# View statistics
python -m squack_pipeline_v2 --stats
```

### Advanced Options

```bash
# Skip certain stages (use existing tables)
python -m squack_pipeline_v2 --skip-bronze --skip-silver

# Disable embeddings
python -m squack_pipeline_v2 --no-embeddings

# Export to Elasticsearch
python -m squack_pipeline_v2 --elasticsearch --es-host localhost --es-port 9200

# Validate configuration only
python -m squack_pipeline_v2 --validate-only

# Clean all tables
python -m squack_pipeline_v2 --clean
```

## Key Features

### 1. SQL-First Design
All data transformations are done in SQL, leveraging DuckDB's columnar engine:
```sql
-- Example from Silver layer
CREATE TABLE silver_properties AS
SELECT 
    listing_id as property_id,
    CAST(price AS DECIMAL(12,2)) as price,
    TRIM(UPPER(state)) as state_code
FROM bronze_properties
WHERE price > 0;
```

### 2. Direct File Operations
DuckDB reads and writes files directly without Python intermediates:
```sql
-- Bronze ingestion
CREATE TABLE bronze_properties AS 
SELECT * FROM read_json_auto('data/properties.json');

-- Parquet export
COPY gold_properties TO 'output/properties.parquet' (FORMAT PARQUET);
```

### 3. Pydantic for Validation
Models validate data at system boundaries, not for internal transformations:
```python
class PropertyDocument(BaseModel):
    """Validated property document for Elasticsearch."""
    property_id: str
    price: float = Field(gt=0)
    bedrooms: int = Field(ge=0, le=20)
```

### 4. Clean Layer Separation
- **Bronze**: Raw data ingestion with minimal changes
- **Silver**: Data standardization and cleaning
- **Gold**: Business logic and enrichment
- **Embeddings**: Vector generation for search
- **Writers**: Export to external systems

## Project Structure

```
squack_pipeline_v2/
├── __main__.py              # CLI entry point
├── config.yaml              # Default configuration
├── core/                    # Core infrastructure
│   ├── connection.py        # DuckDB connection manager
│   ├── settings.py          # Pydantic configuration
│   └── logging.py           # Structured logging
├── models/                  # Pydantic data models
│   ├── bronze/              # Raw data models
│   ├── silver/              # Standardized models
│   ├── gold/                # Enriched models
│   └── pipeline/            # Pipeline metrics
├── bronze/                  # Bronze layer (ingestion)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── silver/                  # Silver layer (standardization)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── gold/                    # Gold layer (enrichment)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── embeddings/              # Embedding generation
│   ├── generator.py
│   └── providers.py
├── writers/                 # Data export
│   ├── parquet.py          # Parquet writer
│   └── elasticsearch.py    # Elasticsearch writer
└── orchestration/           # Pipeline coordination
    └── pipeline.py
```

## Configuration

### Environment Variables
Create a `.env` file in the parent directory:
```bash
VOYAGE_API_KEY=your-voyage-key
OPENAI_API_KEY=your-openai-key
```

### Pipeline Configuration
Edit `config.yaml` for pipeline settings:
```yaml
database:
  path: "pipeline.duckdb"

data_paths:
  properties_file: "../real_estate_data/properties_sf.json"
  neighborhoods_file: "../real_estate_data/neighborhoods_sf.json"
  wikipedia_dir: "../real_estate_data/wikipedia"

embedding:
  enabled: true
  provider: "voyage"
  model_name: "voyage-3"
  dimension: 1024

output:
  parquet_dir: "output/parquet"
```

## DuckDB Best Practices Implemented

1. **SQL-First Transformations**: All data processing uses SQL
2. **Columnar Processing**: Leverages DuckDB's columnar engine
3. **Direct File Operations**: No unnecessary data movement
4. **Batch Processing**: No row-by-row operations
5. **Native COPY Commands**: Efficient import/export
6. **Set-Based Operations**: All transformations are set-based
7. **Minimal Python**: Python only for orchestration and API calls

## Performance

The pipeline processes data efficiently:
- **Bronze Layer**: Direct file reading with `read_json_auto()`
- **Silver Layer**: SQL transformations in DuckDB
- **Gold Layer**: SQL joins and aggregations
- **Embeddings**: Batch processing with configurable size
- **Writers**: Native COPY for Parquet, bulk operations for Elasticsearch

## Testing

```bash
# Run with test data
python -m squack_pipeline_v2 --sample-size 10 --verbose

# Validate configuration
python -m squack_pipeline_v2 --validate-only

# Check table statistics
python -m squack_pipeline_v2 --stats
```

## Migration from V1

The V2 pipeline is completely independent:
1. Lives in separate `squack_pipeline_v2/` directory
2. Uses different table names (prefixed with tier)
3. Can run alongside V1 for validation
4. No changes required to V1 code

## Key Improvements over V1

1. **Clear Architecture**: Medallion pattern with distinct layers
2. **Better Performance**: SQL-first with no Python loops
3. **Maintainable**: Single responsibility per module
4. **Type Safety**: Pydantic V2 throughout
5. **Testable**: Clean interfaces and separation
6. **Extensible**: Easy to add new entity types
7. **Observable**: Comprehensive logging and metrics

## Troubleshooting

### Common Issues

**DuckDB file locked**: Ensure no other process is using the database
```bash
# Use a different database file
python -m squack_pipeline_v2 --database test.duckdb
```

**Embedding API errors**: Check API keys in `.env`
```bash
# Disable embeddings for testing
python -m squack_pipeline_v2 --no-embeddings
```

**Memory issues with large datasets**: Use sampling
```bash
# Process smaller batches
python -m squack_pipeline_v2 --sample-size 1000
```

## Next Steps

1. **Add Integration Tests**: SQL-based testing of transformations
2. **Performance Benchmarks**: Compare with V1 pipeline
3. **Production Validation**: Run parallel with V1 for verification
4. **Documentation**: Expand documentation for each module
5. **Monitoring**: Add metrics collection and dashboards

## License

Same as parent project.