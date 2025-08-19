# Wikipedia Embedding Pipeline

A state-of-the-art generative AI system for creating, storing, and querying semantic embeddings from Wikipedia content. This pipeline showcases advanced vector search techniques using **LlamaIndex** and multiple embedding providers, demonstrating how to build production-ready RAG (Retrieval-Augmented Generation) data infrastructure.

## 🤖 Generative AI Technologies

**Core AI Frameworks:**
- **LlamaIndex** - Leading framework for building LLM-powered applications
  - `llama_index.core` for document processing and indexing
  - `llama_index.embeddings` for multi-provider embedding generation
  - `llama_index.node_parser` for intelligent text chunking
  - Semantic splitter with embedding-based boundary detection

**Embedding Models & Providers:**
- **Ollama (Local AI)** - Privacy-preserving local embeddings
  - `nomic-embed-text` (768 dimensions) - Optimized for semantic search
  - Real-time embedding generation without API dependencies
- **Google Gemini** - Cloud-based embeddings
  - `models/embedding-001` - Google's latest embedding model
- **VoyageAI** - Specialized domain embeddings
  - `voyage-3`, `voyage-3-lite` - General purpose
  - `voyage-finance-2` - Finance-optimized embeddings
- **OpenAI** - Industry-standard embeddings (via config)

**Vector Databases & Search:**
- **ChromaDB** - High-performance vector database
  - Persistent storage with automatic indexing
  - Metadata filtering and hybrid search
  - Collection management with versioning
- **Elasticsearch** - Production-scale vector search
  - KNN (k-nearest neighbors) queries
  - Hybrid text and vector search
  - Distributed architecture support

**AI Techniques:**
- **Semantic Chunking** - AI-powered document segmentation using embedding similarity
- **Augmented Embeddings** - Enhanced chunks with contextual summaries
- **Multi-Model Benchmarking** - Automated comparison across embedding providers
- **RAG-Optimized Indexing** - Pre-structured for retrieval-augmented generation

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Install and start Ollama (for local embeddings)
brew install ollama  # macOS
ollama serve
ollama pull nomic-embed-text
```

### Create and Evaluate Embeddings

```bash
# 1. Create embeddings (reuses existing if available)
python -m wiki_embed.main create

# 2. Force recreate embeddings from scratch
python -m wiki_embed.main create --force-recreate

# 3. Test retrieval accuracy
python -m wiki_embed.main test

# 4. Compare different embedding models
python -m wiki_embed.main compare
```

## Overview

The Wikipedia Embedding Pipeline transforms unstructured Wikipedia content into high-dimensional vector representations suitable for semantic search, question answering, and RAG applications. Built on LlamaIndex, it provides a complete solution for embedding generation, storage, and retrieval with support for multiple AI providers and vector databases.

### ✅ Current Status
- **2,262 embeddings** successfully created and indexed in ChromaDB
- **Embedding model**: nomic-embed-text (768 dimensions)
- **Vector store**: ChromaDB with persistent storage
- **Performance**: ~5% F1 score on 20 test queries (tuning needed)

## 📁 Project Structure

```
wiki_embed/
├── models.py           # Pydantic models for type safety
├── pipeline.py         # Main embedding pipeline
├── query.py           # Query testing and evaluation
├── vector_stores.py   # ChromaDB and Elasticsearch implementations
├── settings.py        # Global configuration management
├── main.py            # CLI interface
├── utils.py           # Wikipedia HTML parsing utilities
├── summary_utils.py   # SQLite summary loading
├── config.yaml        # Configuration file
└── test_eval.py       # Quick evaluation script

data/
├── wikipedia/
│   ├── pages/         # 333+ Wikipedia HTML files
│   └── wikipedia.db   # SQLite database with summaries
├── wiki_test_queries.json    # 20 test queries
└── wiki_chroma_db/           # ChromaDB vector storage
```

## 🔧 Configuration

Edit `wiki_embed/config.yaml`:

```yaml
embedding:
  provider: ollama              # or gemini, voyage
  ollama_model: nomic-embed-text

vector_store:
  provider: chromadb            # or elasticsearch
  chromadb:
    path: "./data/wiki_chroma_db"
    collection_prefix: "wiki_embeddings"
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "wiki_embeddings"

chunking:
  method: semantic              # or simple
  chunk_size: 800              # for simple method
  embedding_method: traditional # or augmented, both
```

## Architecture

### System Components

```
Wikipedia HTML Files
        ↓
┌──────────────────┐
│  HTML Parser     │ → Extract clean text from HTML
│  (BeautifulSoup) │
└────────┬─────────┘
         ↓
┌──────────────────┐
│  Text Chunking   │ → Split into semantic chunks
│  (LlamaIndex)    │
└────────┬─────────┘
         ↓
┌──────────────────────┐
│  Embedding Models    │ → Generate vector embeddings
├──────────────────────┤
│ • Ollama (local)     │
│ • Gemini (API)       │
│ • Voyage (API)       │
└────────┬─────────────┘
         ↓
┌──────────────────────┐
│   Vector Stores      │ → Store and index embeddings
├──────────────────────┤
│ • ChromaDB           │
│ • Elasticsearch      │
└────────┬─────────────┘
         ↓
┌──────────────────┐
│  Query Testing   │ → Evaluate retrieval accuracy
│  & Evaluation    │
└──────────────────┘
```

### Core Classes

#### VectorStore Abstract Base Classes
- **VectorStore**: Interface for store creation and management
- **VectorSearcher**: Interface for similarity search operations

#### Implementations
- **ChromaDBStore/ChromaDBSearcher**: ChromaDB implementation
- **ElasticsearchStore/ElasticsearchSearcher**: Elasticsearch implementation

#### Pipeline Components
- **WikipediaEmbeddingPipeline**: Main pipeline orchestrator
- **WikipediaQueryTester**: Query evaluation and metrics
- **WikiEmbedSettings**: Global configuration management

### Key Features

1. **Multiple Vector Stores**
   - ChromaDB for local development
   - Elasticsearch for production scale
   - Clean abstraction for easy extension

2. **Multiple Embedding Providers**
   - Ollama (local, no API needed)
   - Gemini (Google Cloud)
   - Voyage (specialized embeddings)

3. **Flexible Chunking**
   - Semantic: Preserves topic boundaries
   - Simple: Fixed-size chunks with overlap

4. **Comprehensive Testing**
   - 20 location-based test queries
   - 6 query types (geographic, landmark, historical, etc.)
   - Precision, recall, and F1 metrics

## 📊 Performance Metrics

### Current Results (nomic-embed-text)
```
Average Precision: 0.046
Average Recall:    0.067
Average F1 Score:  0.053
```

### Results by Query Type
| Type | Precision | Recall | F1 Score | Count |
|------|-----------|--------|----------|-------|
| Geographic | 0.062 | 0.125 | 0.083 | 4 |
| Administrative | 0.083 | 0.125 | 0.100 | 4 |
| Cultural | 0.111 | 0.111 | 0.111 | 3 |
| Recreational | 0.000 | 0.000 | 0.000 | 4 |
| Landmark | 0.000 | 0.000 | 0.000 | 2 |
| Historical | 0.000 | 0.000 | 0.000 | 3 |

*Note: Low scores indicate need for tuning - embeddings are working but retrieval parameters need optimization*

## 🎯 Query Types

The system tests six categories of location-based queries:

1. **Geographic**: Terrain features, mountains, coastlines
2. **Landmark**: Specific buildings, monuments, bridges
3. **Historical**: Historical events, settlements, founding
4. **Recreational**: Parks, sports venues, tourism
5. **Cultural**: Technology companies, institutions
6. **Administrative**: Government, counties, municipalities

## 💡 Implementation Details

### Text Processing Pipeline

1. **HTML Loading**
   - Reads `.html` files from `data/wikipedia/pages/`
   - Extracts page_id from filename
   - Parses HTML structure

2. **Text Extraction**
   - Removes navigation, sidebars, references
   - Extracts main article content
   - Preserves paragraph structure

3. **Chunking Strategy**
   - **Semantic**: Detects natural boundaries (recommended)
     - Breakpoint percentile: 90 (conservative splits)
     - Buffer size: 2 (context window)
   - **Simple**: Fixed-size chunks
     - Chunk size: 800 words
     - Overlap: 100 words

4. **Embedding Generation**
   - Batch processing with progress tracking
   - Model-specific optimizations
   - Dimension validation (768 for nomic-embed-text)

5. **Storage**
   - Collection naming: `{prefix}_{model}_{method}`
   - Metadata indexing (page_id, title, location)
   - Efficient similarity search

### Error Handling

- **HTML Parse Errors**: Skip malformed files with logging
- **Embedding Failures**: Retry with exponential backoff
- **Vector Store Issues**: Automatic collection creation
- **Missing Files**: Graceful skip with warning

## 🔬 Testing

### Quick Evaluation
```bash
python -m wiki_embed.test_eval
```

### Full Test Suite
```bash
# Test with all queries
python -m wiki_embed.main test

# Test specific method
python -m wiki_embed.main test --method traditional

# Compare models
python -m wiki_embed.main compare
```

## 🚀 Advanced Usage

### Using Elasticsearch

1. Install and start Elasticsearch:
```bash
docker run -d -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  elasticsearch:8.11.0
```

2. Update config.yaml:
```yaml
vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
```

3. Create embeddings:
```bash
python -m wiki_embed.main create --force-recreate
```

### Using Different Embedding Models

#### Gemini
```yaml
embedding:
  provider: gemini
  gemini_api_key: ${GOOGLE_API_KEY}
```

#### Voyage
```yaml
embedding:
  provider: voyage
  voyage_api_key: ${VOYAGE_API_KEY}
```

### Programmatic Usage

```python
from wiki_embed.models import Config
from wiki_embed.pipeline import WikipediaEmbeddingPipeline
from wiki_embed.settings import configure_from_config

# Load configuration
config = Config.from_yaml("wiki_embed/config.yaml")

# Configure global settings
configure_from_config(config)

# Create pipeline
pipeline = WikipediaEmbeddingPipeline(config)

# Create embeddings
num_embeddings = pipeline.create_embeddings(force_recreate=False)
print(f"Created {num_embeddings} embeddings")
```

## 🚧 Known Issues

1. **Low retrieval scores**: Current configuration needs tuning for better precision/recall
2. **Summary loading error**: "no such column: summary" - summaries table structure mismatch
3. **Large chunks warning**: Some chunks exceed configured limits (informational only)

## 🔄 Recent Updates

- ✅ Successfully created 2,262 embeddings from Wikipedia articles
- ✅ Implemented ChromaDB and Elasticsearch support
- ✅ Added multiple embedding provider support
- ✅ Created comprehensive test suite with 20 queries
- ✅ Added semantic chunking for better context preservation

## 📄 License

MIT License - See parent project for details

## 🙏 Acknowledgments

- LlamaIndex for the embedding framework
- Ollama for local embeddings
- ChromaDB for vector storage
- Wikipedia for content (CC BY-SA 3.0)