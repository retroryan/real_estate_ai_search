# Common Embeddings Module

## Project Overview

A comprehensive evaluation testing toolkit for benchmarking and comparing embedding models in real-world retrieval scenarios. Built with cutting-edge generative AI technologies, this module provides a robust framework for assessing embedding quality across different providers and models.

## Generative AI Technologies

- **LlamaIndex**: Advanced framework for semantic chunking and document processing with built-in RAG capabilities
- **ChromaDB**: High-performance vector database optimized for AI applications with metadata filtering
- **Voyage AI**: State-of-the-art cloud-based embeddings with domain-specific optimization
- **Ollama**: Local LLM inference for privacy-preserving embedding generation
- **OpenAI Embeddings**: Industry-standard text-embedding models with proven performance
- **Google Gemini**: Multi-modal embedding capabilities for diverse content types
- **Cohere**: Specialized embeddings with reranking capabilities

## Quick Start

```bash
# Install the module (from parent directory)
pip install -e common_embeddings/

# Set up environment variables for API keys
echo "VOYAGE_API_KEY=your-key-here" >> .env
echo "OPENAI_API_KEY=your-key-here" >> .env  # Optional

# Run evaluation with sample config
python -m common_embeddings --data-type eval --config common_embeddings/sample_eval_configs/nomic.yaml

# Compare multiple models
python -m common_embeddings.evaluate compare common_embeddings/sample_eval_configs/

# Process real data
python -m common_embeddings --data-type wikipedia --max-articles 10
```

## Data Pipeline Flow

### Processing Pipeline
1. **Data Ingestion**: Load structured data from multiple sources (properties, Wikipedia, neighborhoods)
2. **Semantic Chunking**: Apply LlamaIndex-powered chunking strategies for optimal retrieval
3. **Embedding Generation**: Create vector representations using configured provider
4. **Vector Storage**: Persist embeddings in ChromaDB with comprehensive metadata
5. **Evaluation**: Run standardized benchmarks to assess retrieval quality

### Architecture Overview

```
Data Sources → Text Processing → Embedding Provider → ChromaDB Storage
     ↓              ↓                    ↓                    ↓
 [JSON/CSV]   [LlamaIndex]      [Voyage/Ollama]      [Vector Index]
                                         ↓
                              Evaluation Framework
                                         ↓
                            [Metrics & Comparison Reports]
```

## Evaluation System

The evaluation system provides tools to benchmark and compare different embedding models on standardized datasets.

### Overview

The evaluation workflow consists of three steps:
1. **Create embeddings** - Generate embeddings for evaluation datasets using different models
2. **Run queries** - Test retrieval accuracy with predefined query sets
3. **Compare results** - Analyze metrics and determine the best performing model

### Running Evaluations

First, create your own `eval_configs` directory by copying the samples:

```bash
# Copy sample configs to create your own eval_configs
cp -r common_embeddings/sample_eval_configs common_embeddings/eval_configs

# Edit the configs as needed for your models and datasets
```

Then run evaluations:

```bash
# Run evaluation with a specific config
python -m common_embeddings --data-type eval --config common_embeddings/eval_configs/nomic.yaml

# Compare multiple models (run all configs in a directory)
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/

# Compare specific models
python -m common_embeddings.evaluate compare \
  common_embeddings/eval_configs/nomic.yaml \
  common_embeddings/eval_configs/mxbai.yaml

# Force recreate embeddings
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/ --force-recreate

# Skip comparison step (just create embeddings)
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/ --skip-comparison

# Run comparison on existing collections
python -m common_embeddings.evaluate run
```

### Evaluation Datasets

- **Bronze** (3 articles, 5 queries): Quick testing dataset
- **Gold** (50 articles, 40 queries): Standard evaluation dataset

### Creating Evaluation Configs

Each model needs its own eval config. See `sample_eval_configs/` for examples:

```yaml
# Example: eval_configs/nomic.yaml
embedding:
  provider: ollama
  ollama_model: nomic-embed-text

chromadb:
  persist_directory: ./data/wiki_chroma_db
  collection_name: bronze_ollama_nomic  # Explicit collection name

evaluation_data:
  articles_path: common_embeddings/evaluate_data/bronze_articles.json
  queries_path: common_embeddings/evaluate_data/bronze_queries.json
  dataset_type: bronze
```

Available sample configs in `sample_eval_configs/`:
- `nomic.yaml` - Nomic embeddings via Ollama
- `mxbai.yaml` - MxBai embeddings via Ollama  
- `voyage.yaml` - Voyage AI cloud embeddings
- `eval.config.yaml` - Base configuration template
- `test.config.yaml` - Model comparison configuration

### Model Comparison

After creating embeddings for multiple models, run comparison:

```bash
# Run comparison on existing collections
python -m common_embeddings.evaluate run

# Or run the full pipeline: create embeddings and compare
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/
```

This will:
1. Load embeddings from configured collections
2. Run queries against each model (using the correct embedding model for each)
3. Calculate metrics (Precision, Recall, F1, MAP, MRR)
4. Determine winner based on primary metric
5. Generate comparison report

**Important**: The evaluation framework automatically uses the correct embedding model for generating query embeddings that match each collection's embeddings. This ensures accurate comparisons between models with different dimensions.

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

### Using Voyage AI Embeddings

Voyage AI provides high-quality cloud-based embeddings that outperform local models in many scenarios.

#### Setup

1. **Get API Key**: Sign up at [Voyage AI](https://dash.voyageai.com) to get your API key

2. **Add to .env file**: Create or update the `.env` file in the project root:
```bash
# .env file in project root
VOYAGE_API_KEY=your-voyage-api-key-here
```

The framework automatically loads the `.env` file when running, so no need to export manually.

3. **Configure Provider**: Update your config to use Voyage:

```yaml
# config.yaml or eval config
embedding:
  provider: voyage
  voyage_model: voyage-3  # 1024 dimensions, optimized for semantic similarity
  # Other options: voyage-large-2 (1536 dims), voyage-code-2 (for code)

processing:
  rate_limit_delay: 0.1  # Add small delay to respect API rate limits
```

#### Available Voyage Models

- **voyage-3**: Latest general-purpose model (1024 dims) - Recommended
- **voyage-large-2**: Higher dimension model (1536 dims) for maximum accuracy
- **voyage-code-2**: Optimized for code and technical content
- **voyage-2**: Previous generation model (1024 dims)

#### Running with Voyage

```bash
# Copy sample config for Voyage
cp common_embeddings/sample_eval_configs/voyage.yaml common_embeddings/eval_configs/

# Create embeddings with Voyage (API key loaded from .env automatically)
python -m common_embeddings --data-type eval --config common_embeddings/eval_configs/voyage.yaml

# Compare Voyage with other models
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/

# Use Voyage for production data
python -m common_embeddings --data-type wikipedia --force-recreate
```

#### Performance Comparison

Based on our evaluation on the gold dataset:

| Model | Provider | Dimensions | F1 Score | MRR | Best For |
|-------|----------|------------|----------|-----|----------|
| voyage-3 | Voyage AI | 1024 | 0.406 | 0.866 | Semantic, Historical, Landmarks |
| nomic-embed-text | Ollama | 768 | 0.373 | 0.727 | Administrative queries |
| mxbai-embed-large | Ollama | 1024 | 0.366 | 0.756 | Geographic queries |

Voyage-3 shows superior performance for most query types, particularly excelling at semantic understanding and historical/landmark identification.

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


## Testing

### Unit Tests

```bash
# Run all unit tests
pytest

# Run with coverage
pytest --cov=common_embeddings

# Run specific test
pytest tests/test_pipeline.py
```

### Integration Tests

The integration tests use fixed test data for reproducible results. They test the complete embedding pipeline with real Wikipedia articles and predefined queries.

```bash
# Run comprehensive integration tests (recommended)
python common_embeddings/integration_tests/test_fixed_data.py
```

**Integration Test Coverage:**
- ✅ Document creation from fixed test articles
- ✅ Pipeline initialization (standard and LlamaIndex-optimized)
- ✅ Embedding generation with semantic chunking
- ✅ Statistics tracking and metrics collection
- ✅ Collection management operations
- ✅ Query retrieval with fixed test queries

**Test Data:**
- **5 Wikipedia articles**: Diverse geographic locations and content types
- **10 test queries**: Cover geographic, recreational, historical, and cultural queries
- **Fixed results**: Consistent, reproducible test outcomes

The integration tests automatically:
1. Load fixed test articles from `integration_tests/fixed_test_articles.json`
2. Create temporary ChromaDB collections for testing
3. Generate embeddings using the configured provider (default: Ollama nomic-embed-text)
4. Test retrieval accuracy with predefined queries
5. Clean up all temporary data after completion

**Prerequisites for Integration Tests:**
- Ollama server running with `nomic-embed-text` model
- Sufficient disk space for temporary ChromaDB collections
- Network access for embedding generation

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

**"attempted relative import with no known parent package"**
```bash
# ❌ WRONG: Running directly from common_embeddings/
cd common_embeddings
python main.py  # This fails!

# ✅ CORRECT: Running as module from parent directory
cd /path/to/real_estate_ai_search  # Parent directory
python -m common_embeddings        # This works!
```

**Other import issues:**
- Verify common is installed: `pip list | grep common`
- Ensure you're in the correct parent directory with `pwd`
- Check that `common_embeddings/__main__.py` exists

## Advanced Usage

### Batch Processing Configuration

Configure batch processing for large datasets with rate limiting:

```yaml
# config.yaml
processing:
  batch_size: 100
  rate_limit_delay: 0.1  # seconds between API calls
  max_retries: 3
  timeout: 30
```

### Multi-Model Comparison

Run comprehensive model comparisons across different providers:

```bash
# Compare all models in directory
python -m common_embeddings.evaluate compare common_embeddings/eval_configs/ --force-recreate

# Generate detailed comparison report
python -m common_embeddings.evaluate run --output-format html
```

### LlamaIndex Semantic Chunking

Use LlamaIndex's advanced chunking for better retrieval:

```bash
# Enable semantic chunking in config
python -m common_embeddings --data-type wikipedia --chunking-method semantic
```

### ChromaDB Query Filtering

Query with metadata filters for precise retrieval:

```bash
# Query specific entity types
python -m common_embeddings.query \
  --collection bronze_ollama_nomic \
  --filter '{"entity_type": "wikipedia"}' \
  --query "San Francisco landmarks"
```

## Module Design

This module follows a clean architecture with clear separation of concerns:

### Shared Models (from common)
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
6. **No duplication**: Shared models used from common, no redundancy
7. **Extensibility**: Easy to add new embedding providers or processing methods

### Processing Pipeline
The embedding generation follows this flow:
1. **Data Loading**: Use loaders to read source data (properties, Wikipedia, neighborhoods)
2. **Text Processing**: Apply chunking strategies (simple, semantic, sentence)
3. **Embedding Generation**: Use configured provider (Ollama, OpenAI, etc.)
4. **Storage**: Persist in ChromaDB with comprehensive metadata
5. **Correlation**: Link embeddings back to source data (handled separately)

### Configuration Management
- Base configuration from common
- Local extensions for chunking and processing
- YAML configuration support with `load_config_from_yaml` utility
- Environment variable support for API keys

### Error Handling
- Hierarchical exception structure
- Specific exceptions for each failure type
- Comprehensive error logging with stack traces
- Graceful degradation where possible