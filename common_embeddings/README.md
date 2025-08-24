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

## Running the Pipeline

Run the pipeline as a Python module from the parent directory:

```bash
# Navigate to parent directory (real_estate_ai_search)
cd /path/to/real_estate_ai_search

# Process real estate data only
python -m common_embeddings --data-type real_estate

# Process Wikipedia data only  
python -m common_embeddings --data-type wikipedia

# Process Wikipedia with limited documents (for testing)
python -m common_embeddings --data-type wikipedia --max-articles 10

# Process all data types
python -m common_embeddings --data-type all

# Force recreate embeddings (delete existing)
python -m common_embeddings --data-type all --force-recreate

# Run tests
pytest common_embeddings/

# Type checking
mypy common_embeddings/
```

**Important**: Always use `python -m common_embeddings` to run the pipeline. Direct execution with `python common_embeddings/main.py` is not supported.

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
├── models/             # Local models specific to embeddings
│   ├── __init__.py     # Imports shared models and exports all
│   ├── config.py       # Chunking and processing configurations
│   ├── enums.py        # Embeddings-specific enums
│   ├── exceptions.py   # Embeddings-specific exceptions
│   ├── interfaces.py   # Abstract interfaces for providers
│   ├── metadata.py     # Metadata models for embeddings
│   ├── processing.py   # Processing result models
│   ├── statistics.py   # Statistics models
│   └── correlation.py  # Correlation models
├── pipeline/           # Processing pipeline
├── providers/          # Embedding providers  
├── storage/            # Storage layer
├── processing/         # Text processing components
├── services/           # High-level services
├── loaders/           # Data loaders
├── utils/             # Utility functions
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

This module follows a clean architecture with clear separation of concerns:

### Shared Models (from property_finder_models)
- **Core entity definitions**: BaseMetadata as the foundation for all metadata
- **Common enums**: EntityType, SourceType, EmbeddingProvider
- **Shared configuration**: Config, EmbeddingConfig, ChromaDBConfig
- **Base exceptions**: ConfigurationError, DataLoadingError, StorageError, ValidationError, MetadataError

### Local Models (in models/ directory)
- **Enums** (`models/enums.py`): ChunkingMethod, PreprocessingStep, AugmentationType
- **Config** (`models/config.py`): ChunkingConfig, ProcessingConfig, load_config_from_yaml utility
- **Metadata** (`models/metadata.py`): PropertyMetadata, NeighborhoodMetadata, WikipediaMetadata, ProcessingMetadata
- **Processing** (`models/processing.py`): ProcessingResult, BatchProcessingResult, DocumentBatch, ChunkMetadata
- **Statistics** (`models/statistics.py`): PipelineStatistics, BatchProcessorStatistics, CollectionInfo, SystemStatistics
- **Interfaces** (`models/interfaces.py`): IDataLoader, IEmbeddingProvider, IVectorStore
- **Exceptions** (`models/exceptions.py`): EmbeddingGenerationError, ChunkingError, ProviderError
- **Correlation** (`models/correlation.py`): ChunkGroup, ValidationResult, CollectionHealth, CorrelationMapping

### Architecture Principles
1. **Clean imports**: All models imported through `models/__init__.py` for consistency
2. **Proper logging**: Python logging module throughout, no print statements
3. **Type safety**: Full Pydantic v2 model validation with field validators
4. **Modular design**: Clear separation between shared and local models
5. **Single responsibility**: Each model file has a specific purpose
6. **No duplication**: Shared models used from property_finder_models, no redundancy
7. **Extensibility**: Easy to add new embedding providers or processing methods

### Processing Pipeline
The embedding generation follows this flow:
1. **Data Loading**: Use loaders to read source data (properties, Wikipedia, neighborhoods)
2. **Text Processing**: Apply chunking strategies (simple, semantic, sentence)
3. **Embedding Generation**: Use configured provider (Ollama, OpenAI, etc.)
4. **Storage**: Persist in ChromaDB with comprehensive metadata
5. **Correlation**: Link embeddings back to source data (handled separately)

### Configuration Management
- Base configuration from property_finder_models
- Local extensions for chunking and processing
- YAML configuration support with `load_config_from_yaml` utility
- Environment variable support for API keys

### Error Handling
- Hierarchical exception structure
- Specific exceptions for each failure type
- Comprehensive error logging with stack traces
- Graceful degradation where possible