# Data Pipeline

## Project Overview

A high-performance data processing pipeline built on Apache Spark for transforming, enriching, and indexing real estate and Wikipedia data with advanced embedding generation capabilities. Designed for scalable AI-powered search and recommendation systems.

## Generative AI Technologies

- **Apache Spark**: Distributed computing framework for processing large-scale datasets with ML capabilities
- **Voyage AI**: State-of-the-art embedding models optimized for semantic search
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
NEO4J_PASSWORD=your-neo4j-password
```

### 2. Run the pipeline
```bash
# Process full dataset
python -m data_pipeline

# Process sample data (for testing)
python -m data_pipeline --sample-size 5
```

## Configuration

All configuration is in `config.yaml`:

- **Embedding provider**: Choose between `voyage`, `openai`, `mock`
- **Output destinations**: Enable `parquet`, `neo4j`, or `elasticsearch`
- **Spark settings**: Memory, parallelism, etc.

## Project Structure

```
data_pipeline/
├── config.yaml              # Main configuration file
├── config/                  # Configuration models
│   ├── models.py           # Pydantic config models
│   └── loader.py           # Config loading logic
├── core/                    # Core pipeline components
│   ├── pipeline_runner.py  # Main orchestrator
│   └── spark_session.py    # Spark session management
├── processing/              # Data processing
│   ├── base_embedding.py   # Base embedding generator
│   └── entity_embeddings.py # Entity-specific embeddings
├── loaders/                 # Data loaders
├── enrichment/              # Data enrichment
├── writers/                 # Output writers
└── integration_tests/       # Integration tests
```

## Testing

```bash
# Run integration tests
python -m pytest data_pipeline/integration_tests/

# Test embeddings with real API
python data_pipeline/integration_tests/test_real_voyage.py
```

## Command Line Options

- `--sample-size N`: Process only N records from each data source (useful for testing)

## Outputs

By default, outputs are written to:
- **Parquet files**: `data/processed/`
- **Neo4j**: Local database at `bolt://localhost:7687`
- **Elasticsearch**: Local instance at `localhost:9200`

Enable/disable outputs in `config.yaml` under `output.enabled_destinations`.


## Processing Pipeline

1. **Data Ingestion**: Load JSON data from multiple sources
2. **Data Enrichment**: Enhance properties with location data
3. **Embedding Generation**: Create vector representations using configured provider
4. **Relationship Discovery**: Identify similarities between entities
5. **Multi-Destination Output**: Write to configured destinations


## Troubleshooting

- **Out of Memory**: Reduce sample size with `--sample-size 10`
- **API Rate Limits**: Reduce batch size in `config.yaml`
- **Connection Issues**: Check services are running (Neo4j: 7687, Elasticsearch: 9200)

