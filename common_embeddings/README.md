# Common Embeddings Module

A unified embedding generation and storage system that provides centralized management for embeddings from multiple data sources using shared Property Finder models.

## Installation

### Prerequisites
- Python 3.9+
- property_finder_models package installed
- Ollama server running (for local embeddings)

### Setup

```bash
# Install shared models first (from project root)
cd property_finder_models
pip install -e .

# Install common_embeddings (from project root)
cd ../common_embeddings
pip install -e .

# For development with additional tools
pip install -e ".[dev,viz]"

# For all provider support
pip install -e ".[providers]"
```

### Verify Installation

```bash
# From common_embeddings directory
cd common_embeddings
python -c "import common_embeddings; print('Installation successful!')"
```

## Running the Pipeline

**IMPORTANT**: All commands MUST be run from the `common_embeddings/` directory:

```bash
# Navigate to common_embeddings directory
cd /path/to/project/common_embeddings

# Create embeddings (from common_embeddings/)
python -m pipeline.main create --entity-type property

# Or with full module path (from common_embeddings/)
python pipeline/main.py create --entity-type property

# Run tests (from common_embeddings/)
pytest

# Type checking (from common_embeddings/)
mypy .
```

**Note**: The module is designed to work ONLY when run from the `common_embeddings/` directory. Running from parent or other directories will cause import errors.

## Configuration

Create a `config.yaml` file in the common_embeddings directory:

```yaml
embedding:
  provider: ollama  # Options: ollama, openai, gemini, voyage, cohere
  ollama_model: nomic-embed-text  # or mxbai-embed-large

chromadb:
  persist_directory: "./data/common_embeddings"
  
# Processing settings configured per-module as needed
```

## Directory Structure

```
common_embeddings/
├── pyproject.toml       # Package configuration
├── config.yaml          # Module configuration
├── README.md           # This file
├── pipeline/           # Processing pipeline
├── providers/          # Embedding providers
├── storage/            # Storage layer
├── models_local.py     # Local models specific to embeddings
└── tests/              # Test suite
```

## Features

- Multiple embedding provider support (Ollama, OpenAI, Gemini, Voyage, Cohere)
- Unified storage with ChromaDB
- Batch processing for efficiency
- Comprehensive metadata tracking
- Entity type support (properties, neighborhoods, Wikipedia articles)

## Environment Variables

For API-based providers, set the appropriate environment variables:

```bash
# For OpenAI
export OPENAI_API_KEY=your-key

# For Gemini
export GOOGLE_API_KEY=your-key

# For Voyage
export VOYAGE_API_KEY=your-key

# For Cohere
export COHERE_API_KEY=your-key
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=common_embeddings

# Run specific test
pytest tests/test_pipeline.py
```

## Troubleshooting

### Ollama Connection Error
```bash
# Ensure Ollama is running
ollama serve

# Verify connection
curl http://localhost:11434
```

### Missing Model
```bash
# Pull required models
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

### Import Errors
- Ensure you're running commands from the `common_embeddings/` directory
- Verify property_finder_models is installed: `pip list | grep property-finder-models`

## Module Design

This module uses shared models from `property_finder_models` for:
- Entity definitions (EnrichedProperty, EnrichedNeighborhood, etc.)
- Configuration models (Config, EmbeddingConfig, ChromaDBConfig)
- Common enums (EntityType, SourceType, EmbeddingProvider)
- Base exceptions

Local models specific to embedding pipeline operations are kept in `models_local.py`.