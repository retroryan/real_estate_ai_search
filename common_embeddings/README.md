# Common Embeddings Module

A unified embedding generation and storage system that provides centralized management for embeddings from multiple data sources with comprehensive metadata tracking for correlation.

## Quick Start

### Prerequisites

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Ollama server (required for local embeddings)
ollama serve

# 3. Pull embedding model (if not already available)
ollama pull nomic-embed-text

# 4. Verify Ollama is running
curl http://localhost:11434

# 5. Ensure data directories exist:
# - real_estate_data/    (contains properties_*.json and neighborhoods_*.json)
# - data/wikipedia/pages/ (contains Wikipedia HTML files)
```

### Running Tests (Sample Data)

```bash
# Test with synthetic sample documents to verify pipeline works
cd /path/to/real_estate_ai_search
python -m common_embeddings.test_pipeline

# Expected output:
# INFO - Starting common embeddings pipeline test with SAMPLE data
# INFO - Generated embedding for property: PC001
# INFO - Generated embedding for property: SF001
# INFO - Generated embedding for neighborhood: Marina District
# INFO - Retrieved 3 items from storage
# INFO - Test completed successfully!
```

### Processing Real Data with main.py

#### Basic Usage

```bash
# Navigate to project root
cd /path/to/real_estate_ai_search

# Process only real estate data (properties and neighborhoods)
python -m common_embeddings.main --data-type real_estate

# Process only Wikipedia articles
python -m common_embeddings.main --data-type wikipedia

# Process all data sources
python -m common_embeddings.main --data-type all
```

#### Advanced Options

```bash
# Force recreate embeddings (delete existing and recreate)
python -m common_embeddings.main --data-type all --force-recreate

# Process limited Wikipedia articles for testing
python -m common_embeddings.main --data-type wikipedia --max-articles 10

# Use custom configuration file
python -m common_embeddings.main --config my_config.yaml

# Set logging level
python -m common_embeddings.main --data-type all --log-level DEBUG
```

#### Expected Output (with Progress Indicators)

```bash
# Running: python -m common_embeddings.main --data-type real_estate
============================================================
Common Embeddings - Real Data Processing
============================================================
INFO - Loaded configuration: provider=ollama

--- Processing Real Estate Data ---
INFO - Processing real estate data
INFO - Loading neighborhoods from neighborhoods_sf.json
INFO - Loading neighborhoods from neighborhoods_pc.json  
INFO - Loading properties from properties_sf.json
INFO - Loading properties from properties_pc.json
INFO - Loaded 150 properties and 25 neighborhoods
INFO - Processing 150 properties...
INFO - Starting Processing properties: 0/150 items

Processing properties: [████████░░░░░░░░░░░] 40.0% (60/150) - 12.5 items/sec
INFO - Processing properties: 60/150 (40.0%) - 12.5 items/sec - ETA: 7s

Processing properties: [████████████████████] 100.0% (150/150) - 15.2 items/sec
INFO - Completed Processing properties: 150 items in 9.9s (15.2 items/sec)

INFO - Processing 25 neighborhoods...
INFO - Starting Processing neighborhoods: 0/25 items

Processing neighborhoods: [████████████████████] 100.0% (25/25) - 18.3 items/sec
INFO - Completed Processing neighborhoods: 25 items in 1.4s (18.3 items/sec)

INFO - Storing embeddings in ChromaDB...
INFO - Pipeline Statistics:
INFO -   documents_processed: 175
INFO -   embeddings_created: 175
INFO -   chunks_generated: 350
INFO -   average_chunk_size: 256

============================================================
Processing complete!
============================================================
```

#### Command-Line Help

```bash
# View all available options
python -m common_embeddings.main --help

# Output:
usage: main.py [-h] [--data-type {real_estate,wikipedia,all}]
               [--force-recreate] [--max-articles MAX_ARTICLES]
               [--config CONFIG] [--log-level {DEBUG,INFO,WARNING,ERROR}]

Process real data with common embeddings module

optional arguments:
  -h, --help            show this help message and exit
  --data-type           Type of data to process (default: all)
  --force-recreate      Delete existing embeddings and recreate
  --max-articles        Max Wikipedia articles to process (for testing)
  --config              Path to configuration file (default: common_embeddings/config.yaml)
  --log-level          Logging level (default: INFO)
```

### Verifying Data Sources

```bash
# Check if real estate data exists
ls -la real_estate_data/*.json

# Expected files:
# - properties_sf.json      # San Francisco properties
# - properties_pc.json      # Park City properties  
# - neighborhoods_sf.json   # San Francisco neighborhoods
# - neighborhoods_pc.json   # Park City neighborhoods

# Check if Wikipedia data exists
ls -la data/wikipedia/pages/*.html | head -5

# Check Wikipedia database
sqlite3 data/wikipedia/wikipedia.db "SELECT COUNT(*) FROM articles;"
```

### Configuration Check

```bash
# View current configuration
cat common_embeddings/config.yaml

# Key settings to verify:
# embedding:
#   provider: ollama           # or openai, gemini, voyage, cohere
#   ollama_model: nomic-embed-text
#   
# chromadb:
#   host: localhost
#   port: 8000
#   persist_directory: ./data/common_embeddings
#   property_collection_pattern: "property_{model}_v{version}"
#   wikipedia_collection_pattern: "wikipedia_{model}_v{version}"
#   neighborhood_collection_pattern: "neighborhood_{model}_v{version}"
#   
# chunking:
#   method: simple             # RECOMMENDED: simple (fast) or semantic (slow but smarter)
#   chunk_size: 800
```

### Chunking Method Performance

⚠️ **Important**: Chunking method affects processing speed significantly:

- **Simple chunking** (`method: simple`): **Recommended for large datasets**
  - Fast processing (~1000 docs/min)
  - Uses fixed-size chunks with overlap
  - Good for most use cases

- **Semantic chunking** (`method: semantic`): **Use with caution on large datasets**
  - Slower processing (~50 docs/min) 
  - Makes embedding API calls during chunking phase
  - Better semantic boundaries but 20x slower
  - Best for small datasets (<100 documents)

```yaml
# For large datasets (400+ documents)
chunking:
  method: simple
  chunk_size: 800
  chunk_overlap: 100

# For small datasets with better semantics  
chunking:
  method: semantic
  breakpoint_percentile: 90
  buffer_size: 2

# Processing configuration
processing:
  batch_size: 100                   # Embedding batch size
  document_batch_size: 20           # Documents per batch during chunking
  show_progress: true               # Enable progress indicators
```

### Batch Processing and Progress Indicators

The module now processes documents in configurable batches with detailed progress tracking:

**During Chunking:**
```
Processing document batch 1/21 (20 documents)
Chunking documents: [██████████████████████████████] 100.0% (420/420) - 15.2 docs/sec
Completed batch 21/21 - Total chunks so far: 1,250
```

**During Embedding Generation:**
```
Processing properties: [████████████████████] 100.0% (1,250/1,250) - 25.8 items/sec
Completed Processing properties: 1,250 items in 48.4s (25.8 items/sec)
```

**Configuration Options:**
- `document_batch_size: 20` - Process 20 documents at a time during chunking
- `batch_size: 100` - Process 100 embeddings at a time
- `show_progress: true` - Enable progress bars and rate monitoring

This makes large dataset processing (400+ documents) much more transparent and allows you to monitor semantic chunking progress in real-time.

## Module Structure

```
common_embeddings/
├── __init__.py              # Package initialization
├── pipeline.py              # Core embedding orchestration
├── main.py                  # CLI interface for real data
├── test_pipeline.py         # Test with sample data
├── config.yaml              # Configuration file
│
├── models/                  # Data models and interfaces
│   ├── __init__.py
│   ├── config.py           # Configuration models
│   ├── enums.py            # Enumeration types
│   ├── metadata.py         # Metadata models for correlation
│   ├── interfaces.py       # Abstract interfaces
│   └── exceptions.py       # Custom exceptions
│
├── embedding/              # Embedding generation
│   ├── __init__.py
│   └── factory.py          # Provider factory (Ollama, OpenAI, etc.)
│
├── processing/             # Document processing
│   ├── __init__.py
│   ├── chunking.py         # Text chunking strategies
│   └── batch_processor.py # Batch processing with progress
│
├── storage/                # Vector storage
│   ├── __init__.py
│   └── chromadb_store.py  # ChromaDB implementation
│
├── loaders/                # Data loading (NEW)
│   ├── __init__.py
│   ├── real_estate_loader.py  # Real estate JSON loader
│   └── wikipedia_loader.py    # Wikipedia HTML loader
│
└── utils/                  # Utilities
    ├── __init__.py
    ├── logging.py          # Logging configuration
    ├── hashing.py          # Text hashing utilities
    ├── validation.py       # Validation helpers
    └── progress.py         # Progress indicators (NEW)
```

## Key Features

### 1. Multiple Embedding Providers
- **Ollama** (local, free)
- **OpenAI** (cloud, requires API key)
- **Gemini** (cloud, requires API key)
- **Voyage** (cloud, requires API key)
- **Cohere** (cloud, requires API key)

### 2. Entity Types Supported
- **Properties** - Real estate listings with address, price, features
- **Neighborhoods** - Area demographics and characteristics
- **Wikipedia Articles** - Location-based encyclopedia content
- **Wikipedia Summaries** - LLM-generated summaries of articles

### 3. Metadata for Correlation
Each embedding includes minimal metadata for correlation with source data:
- `embedding_id` - Unique identifier
- `entity_type` - Type of entity (property, neighborhood, etc.)
- `source_type` - Data source (JSON, SQLite, etc.)
- `source_file` - Path to source data
- `source_timestamp` - When data was last modified
- Entity-specific IDs (`listing_id`, `page_id`, `neighborhood_id`)

### 4. Bulk Export Support
ChromaDB's `collection.get()` enables downstream services to extract ALL embeddings with metadata for correlation:

```python
# Retrieve all data for downstream processing
all_data = store.get_all(include_embeddings=True)
# Returns: {'ids': [...], 'embeddings': [...], 'metadatas': [...], 'documents': [...]}
```

## Configuration

Edit `config.yaml` to configure:

```yaml
embedding:
  provider: ollama  # or openai, gemini, voyage, cohere
  ollama_model: nomic-embed-text
  ollama_base_url: http://localhost:11434

chromadb:
  path: ./data/common_chroma_db
  collection_prefix: embeddings

chunking:
  method: semantic  # or simple
  chunk_size: 512
  chunk_overlap: 50
```

## API Usage

### Basic Pipeline Usage

```python
from common_embeddings import Config, EmbeddingPipeline, EntityType, SourceType
from llama_index.core import Document

# Load configuration
config = Config.from_yaml("config.yaml")

# Create pipeline
pipeline = EmbeddingPipeline(config)

# Create sample documents
documents = [
    Document(
        text="3-bedroom house in Park City with mountain views",
        metadata={"listing_id": "PC001", "price": 850000}
    )
]

# Process documents
for embedding, metadata in pipeline.process_documents(
    documents,
    EntityType.PROPERTY,
    SourceType.PROPERTY_JSON,
    "properties.json"
):
    print(f"Created embedding for {metadata.listing_id}")
```

### Bulk Export for Downstream Services

```python
from common_embeddings import ChromaDBStore, Config

# Initialize store
config = Config.from_yaml("config.yaml")
store = ChromaDBStore(config.chromadb)

# Get ALL data for correlation
all_data = store.get_all(include_embeddings=True)

# Process in downstream service
for i, embedding_id in enumerate(all_data['ids']):
    embedding = all_data['embeddings'][i]
    metadata = all_data['metadatas'][i]
    document = all_data['documents'][i]
    
    # Correlate with source data using metadata
    if metadata['entity_type'] == 'property':
        listing_id = metadata['listing_id']
        # Lookup original property data using listing_id
```

## Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Test
```bash
python -m common_embeddings.test_pipeline
```

### Performance Test
```bash
python -m common_embeddings.main --test-performance
```

## Logging

The module uses Python's logging module exclusively (no print statements). Configure logging level in your application:

```python
from common_embeddings.utils import setup_logging

# Setup logging
setup_logging(level="INFO", log_file="embeddings.log")
```

### Filtered Loggers
To keep output clean, the following loggers are automatically set to WARNING level:
- `httpx` - HTTP request logs (Ollama API calls)
- `httpcore` - HTTP core transport logs  
- `urllib3` - URL library logs
- `chromadb` - ChromaDB internal logs
- `llama_index` - LlamaIndex framework logs

This eliminates verbose logs like:
```
HTTP Request: POST http://localhost:11434/api/embed "HTTP/1.1 200 OK"
```

## Design Principles

1. **Minimal Metadata**: Store only identifiers needed for correlation, not full data
2. **Bulk Export Pattern**: Enable downstream services to extract all data efficiently  
3. **Constructor Injection**: All dependencies injected via constructors
4. **Pydantic Models**: Type safety and validation throughout
5. **Clean Logging**: Python logging only, no print statements
6. **Reuse Patterns**: Leverages proven patterns from wiki_embed and real_estate_embed

## Performance

Typical performance metrics:
- **Embedding Generation**: ~25 chunks/second with Ollama
- **ChromaDB Storage**: ~100 embeddings/second
- **Bulk Export**: ~1000 embeddings/second

## Troubleshooting

### Ollama Connection Error
```bash
# Ensure Ollama is running
ollama serve

# Pull required model
ollama pull nomic-embed-text
```

### ChromaDB Issues
```bash
# Clear ChromaDB data
rm -rf ./data/common_chroma_db

# Recreate embeddings
python -m common_embeddings.main --force-recreate
```

### Memory Issues
- Reduce batch_size in config.yaml
- Process data in smaller chunks
- Use simple chunking instead of semantic

## License

See parent project LICENSE file.