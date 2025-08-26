# SQUACK Pipeline

A modern data processing pipeline using DuckDB and Pydantic V2 for real estate data analysis with **complete Medallion Architecture**.

## Quick Start

### Phase 1 - Foundation (✅ Complete)

**Test the foundation components:**

```bash
# Test models and configuration
python squack_pipeline/test_phase1.py

# Test CLI interface
python squack_pipeline/test_cli.py
```

### Phase 2 - Data Loading (✅ Complete)

**Test the data loading pipeline:**
```bash
# Run all pipeline tests
python squack_pipeline/test_pipeline.py

# Test with sample data (dry run)
python -m squack_pipeline run --sample-size 10 --dry-run

# Process real data  
python -m squack_pipeline run --sample-size 50
```

### Phase 3 - Medallion Architecture (✅ Complete)

**Test the complete Bronze → Silver → Gold pipeline:**

```bash
# Test complete medallion architecture
python squack_pipeline/test_phase3.py

# Run medallion pipeline
python -m squack_pipeline run --sample-size 5

# Full pipeline with geographic enrichment
python -m squack_pipeline run --sample-size 10 --verbose
```

## Architecture

```
squack_pipeline/
├── models/          # Pydantic V2 data models
├── config/          # Configuration management
├── loaders/         # Data loading with DuckDB
├── processors/      # Data processing pipeline
├── embeddings/      # LlamaIndex integration
├── writers/         # Parquet output
├── orchestrator/    # Pipeline coordination
└── utils/           # Logging and validation
```

## Key Features

- **Pydantic V2**: 4-50x faster validation with Rust backend
- **DuckDB**: Modern OLAP database for fast data processing
- **Structured Logging**: Observability with loguru
- **Type Safety**: Complete type hints throughout
- **Configuration**: Environment-based settings management
- **CLI Interface**: Easy-to-use command-line tools

## Configuration

Create a `.env` file or set environment variables:

```bash
# Required for embedding generation
VOYAGE_API_KEY=your_api_key

# Optional settings
DUCKDB_MEMORY_LIMIT=8GB
DUCKDB_THREADS=4
LOG_LEVEL=INFO
PIPELINE_ENV=development
```

## Development Status

- ✅ **Phase 1**: Foundation (Pydantic models, config, logging, CLI)
- ✅ **Phase 2**: Data Loading (DuckDB integration, property loader, orchestrator)
- ✅ **Phase 3**: Processing Pipeline (Complete Medallion architecture, data enrichment, geographic analysis)  
- ⏳ **Phase 4**: Embedding Integration (LlamaIndex with Voyage AI)

## Testing

Run the test scripts to verify each phase:

```bash
# Phase 1 foundation tests
python squack_pipeline/test_phase1.py

# CLI interface tests  
python squack_pipeline/test_cli.py

# Phase 2 pipeline tests
python squack_pipeline/test_pipeline.py

# Phase 3 medallion architecture tests
python squack_pipeline/test_phase3.py
```

## Requirements

- Python 3.11+
- Dependencies managed via requirements (install as needed):
  - `pydantic>=2.5.0` (data validation)
  - `pydantic-settings` (configuration)
  - `loguru>=0.7.2` (structured logging)
  - `typer>=0.9.0` (CLI framework)
  - `duckdb>=1.0.0` (database engine)
  - `llama-index>=0.10.0` (embedding framework)

## Support

This pipeline follows modern Python best practices (2024-2025):
- Clean, modular architecture
- Type safety with mypy compatibility
- Comprehensive error handling
- Performance optimizations
- Production-ready logging