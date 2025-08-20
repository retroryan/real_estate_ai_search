# Real Estate Embedding Pipeline

## Brief Overview

The Real Estate Embedding Pipeline is a generative AI system that demonstrates advanced embedding generation, storage, and retrieval techniques for real estate data. Built on **LlamaIndex**, this module showcases how to leverage multiple state-of-the-art embedding models to transform property and neighborhood descriptions into high-dimensional vector representations suitable for semantic search and RAG (Retrieval-Augmented Generation) applications.

### 🤖 Generative AI Technologies

**Core Framework:**
- **LlamaIndex** - Enterprise-grade framework for document processing, embedding generation, and semantic chunking
  - `llama_index.core` for document management and indexing
  - `llama_index.embeddings` for multi-provider embedding support
  - `llama_index.node_parser` for intelligent text segmentation

**Embedding Models & Providers:**
- **Ollama (Local AI)** - Privacy-focused local embedding generation
  - `nomic-embed-text` (768 dimensions) - Optimized for semantic similarity
  - `mxbai-embed-large` (1024 dimensions) - High-capacity multilingual model
- **Google Gemini** - Cloud-based embeddings with `models/embedding-001`
- **VoyageAI** - Specialized embeddings including finance-optimized models
  - `voyage-3`, `voyage-3-lite`, `voyage-finance-2`

**Vector Database:**
- **ChromaDB** - Production-ready vector storage with persistent collections
  - Automatic indexing and similarity search
  - Metadata filtering and hybrid search capabilities

**AI Techniques:**
- **Semantic Chunking** - AI-powered text segmentation using embedding similarity
- **Multi-Model Benchmarking** - Automated comparison of embedding quality
- **RAG-Ready Indexing** - Prepares data for retrieval-augmented generation

## Quick Start

### Prerequisites

1. **Python 3.9+**

2. **Install and start Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Or download from https://ollama.ai
   
   # Start Ollama server
   ollama serve
   ```

3. **Pull embedding models**:
   ```bash
   ollama pull nomic-embed-text
   ollama pull mxbai-embed-large
   ```

### Installation

Install dependencies from the main project directory:
```bash
pip install -r requirements.txt
```

Verify Ollama is running:
```bash
curl http://localhost:11434
# Should return "Ollama is running"
```

### Running the Tool

Navigate to the project root directory and run the commands:

#### 1️⃣ Create Embeddings

Create embeddings (model specified in config.yaml):
```bash
# Edit config.yaml to set ollama_model: nomic-embed-text
python -m real_estate_embed.main create

# To use a different model, edit config.yaml:
# ollama_model: mxbai-embed-large
# Then run:
python -m real_estate_embed.main create
```

To force recreation:
```bash
python -m real_estate_embed.main create --force-recreate
```

#### 2️⃣ Test Model

```bash
python -m real_estate_embed.main test
```

#### 3️⃣ Compare Models

Compare all available embedding collections:
```bash
python -m real_estate_embed.main compare
```

**Advanced Usage:**

Compare specific collections:
```bash
# Compare only specific models
python -m real_estate_embed.main compare --collections embeddings_nomic-embed-text embeddings_gemini_embedding

# Compare Ollama vs Gemini (if both exist)
python -m real_estate_embed.main compare --collections embeddings_mxbai-embed-large embeddings_gemini_embedding
```

The compare command:
- Automatically detects all embedding collections in ChromaDB
- Tests each model against the same test queries
- Calculates precision, recall, and F1 scores
- Determines the winner based on F1 score
- Saves results to `results/comparison.json`
- Works with any provider (Ollama, Gemini, Voyage) as long as embeddings exist

## 📊 Test Queries

The system tests 10 realistic real estate queries (`data/test_queries.json`):

1. Luxury homes in Pacific Heights
2. Family-friendly neighborhoods with good schools
3. Modern condos downtown
4. Affordable homes under 1 million
5. Neighborhoods with vibrant nightlife
6. Victorian houses with historic architecture
7. Properties near public transportation
8. Quiet residential areas for retirees
9. Investment properties with high rental yield
10. Eco-friendly green homes

Each query has expected result IDs used to calculate accuracy metrics.

## ⚙️ Configuration

The `config.yaml` file in this directory controls all pipeline settings. Here are the available options:

**Embedding Settings:**
- `provider`: Choose between `ollama` (local), `gemini` (Google Cloud), or `voyage` (VoyageAI)
- `ollama_model`: Select `nomic-embed-text` (768 dims) or `mxbai-embed-large` (1024 dims)
- `gemini_model`: Uses `models/embedding-001` (requires GOOGLE_API_KEY environment variable)
- `voyage_model`: Options include `voyage-3`, `voyage-3-lite`, or `voyage-finance-2` (requires VOYAGE_API_KEY)

**ChromaDB Settings:**
- `path`: Directory for storing vector database (default: `./data/real_estate_chroma_db`)
- `collection_prefix`: Naming prefix for collections (default: `embeddings`)

**Data Settings:**
- `source_dir`: Location of JSON property and neighborhood files (default: `./real_estate_data`)

**Chunking Settings:**
- `method`: Choose `simple` for fast splitting or `semantic` for intelligent boundaries
- `chunk_size`: Target size for each chunk in tokens (default: 512)
- `chunk_overlap`: Number of overlapping tokens between chunks (default: 50)
- `breakpoint_percentile`: Similarity threshold for semantic splitting (default: 95)
- `buffer_size`: Context window overlap for semantic chunks (default: 1)

## 📈 How It Works

1. **Data Loading**: Reads JSON files from `real_estate_data/`
2. **Semantic Chunking**: Uses LlamaIndex's `SemanticSplitterNodeParser`
3. **Embedding Generation**: Creates embeddings using Ollama models
4. **Storage**: Stores in ChromaDB (one collection per model)
5. **Query Testing**: Embeds queries and performs similarity search
6. **Metrics**: Compares retrieved vs expected results
7. **Winner**: Model with highest F1 score wins

## 🎯 Performance

- **Setup**: < 2 minutes
- **Embedding creation**: < 5 minutes for sample data
- **Query response**: < 200ms per query
- **Smart caching**: Embeddings reused between runs
- **Storage**: Separate ChromaDB collection per model

## Architecture and Implementation

### System Architecture

The pipeline follows a clean, modular design for embedding creation and comparison:

```
Real Estate JSON Data
        ↓
┌─────────────────┐
│  Data Loading   │
│  (properties +  │
│  neighborhoods) │
└────────┬────────┘
         ↓
┌─────────────────┐
│Semantic Chunking│
│  (LlamaIndex    │
│   Splitter)     │
└────────┬────────┘
         ↓
┌─────────────────┐
│Embedding Models │
├─────────────────┤
│• nomic-embed    │
│• mxbai-embed    │
└────────┬────────┘
         ↓
┌─────────────────┐
│   ChromaDB      │
│  (One collection│
│   per model)    │
└────────┬────────┘
         ↓
┌─────────────────┐
│  Query Testing  │
│  & Evaluation   │
└─────────────────┘
```

### Core Components

#### 1. Pipeline Module (`pipeline.py`)
- **Purpose**: Orchestrates the embedding creation workflow from data loading to storage
- **Key Classes**: `EmbeddingPipeline`, `DocumentLoader`, `ChunkCreator`
- **Description**: Manages the complete pipeline for loading real estate data, creating semantic chunks using LlamaIndex, generating embeddings through various providers, and storing them in ChromaDB collections

#### 2. Query Module (`query.py`)
- **Purpose**: Tests and evaluates embedding retrieval accuracy with precision, recall, and F1 metrics
- **Key Classes**: `QueryEngine`, `MetricsCalculator`
- **Description**: Executes test queries against embedded collections, retrieves similar documents, and calculates performance metrics by comparing retrieved results with expected ground truth

#### 3. Models Module (`models.py`)
- **Purpose**: Provides type-safe data structures with full validation for the entire system
- **Key Classes**: `Property`, `Neighborhood`, `TestQuery`, `QueryResult`
- **Description**: Defines Pydantic models that validate real estate listings, neighborhood data, test queries with expected results, and query performance metrics

#### 4. Main CLI (`main.py`)
- **Purpose**: Provides a clean command-line interface for all embedding operations
- **Key Classes**: `CLI` with commands for `create`, `test`, and `compare`
- **Description**: Implements a Click-based CLI that orchestrates embedding creation, single model testing, and multi-model comparison with progress tracking and result visualization

### Key Algorithms

#### Semantic Chunking Algorithm
- **Purpose**: Splits documents into semantically coherent chunks for better embedding quality
- **Key Classes**: `SemanticSplitterNodeParser` from LlamaIndex
- **Description**: Uses embedding similarity to identify natural break points in text, maintaining semantic boundaries with a 95th percentile threshold for similarity and a buffer size of 1 for context overlap between chunks

#### Embedding Caching Strategy
- **Purpose**: Efficiently manages embedding storage and reuse across multiple runs
- **Key Classes**: ChromaDB collection management utilities
- **Description**: Checks for existing embeddings in ChromaDB collections before creating new ones, automatically loads cached embeddings when available, and creates new embeddings only when necessary, saving significant computation time

#### Model Comparison Logic
- **Purpose**: Evaluates and compares multiple embedding models on the same test set
- **Key Classes**: Model evaluator and metrics aggregator
- **Description**: Iterates through available models to create embeddings if needed, runs standardized test queries against each model, calculates precision/recall/F1 metrics, and determines the best performing model based on F1 score

### Data Processing Pipeline

1. **Document Loading**
   - Reads JSON files from `real_estate_data/` directory
   - Merges properties and neighborhoods into unified dataset
   - Creates structured documents with metadata including ID, type, and location

2. **Text Preparation**
   - Formats property listings with address, features, and price information
   - Structures neighborhood data with name, description, and amenities
   - Generates searchable text representations optimized for embedding

3. **Chunk Creation**
   - Uses LlamaIndex's `SemanticSplitterNodeParser` for intelligent splitting
   - Creates semantically coherent chunks maintaining context
   - Preserves metadata (ID, type, location) for each chunk

4. **Embedding Generation**
   - Connects to Ollama API for local model processing
   - Performs batch processing with progress tracking
   - Generates embeddings at approximately 0.5 seconds per chunk

5. **Storage**
   - Saves to ChromaDB with persistent storage capabilities
   - Creates separate collection for each embedding model
   - Implements metadata indexing for efficient filtering and retrieval

### Performance Characteristics

| Component | Performance |
|-----------|------------|
| Document Loading | < 100ms |
| Chunk Creation | ~500ms for 100 docs |
| Embedding Generation | ~0.5s per chunk |
| ChromaDB Storage | ~50ms per chunk |
| Query Execution | < 200ms |
| Full Pipeline | < 5 minutes for sample data |

### Configuration System

The `config.yaml` structure:
```yaml
embedding:
  provider: ollama          # Options: ollama, gemini, voyage
  ollama_base_url: "http://localhost:11434"
  ollama_model: nomic-embed-text      # 768 dimensions
  # Alternative: mxbai-embed-large    # 1024 dimensions

chromadb:
  path: "./data/real_estate_chroma_db"
  collection_prefix: "embeddings"

chunking:
  method: simple            # or semantic
  chunk_size: 512
  chunk_overlap: 50
  breakpoint_percentile: 95
  buffer_size: 1

data:
  source_dir: "./real_estate_data"
```

### Test Query Design

Each test query targets specific retrieval capabilities:

1. **Luxury Homes**: Tests price and feature understanding
2. **Family-Friendly**: Tests amenity and demographic matching
3. **Modern Condos**: Tests property type filtering
4. **Affordable Homes**: Tests price range queries
5. **Nightlife**: Tests lifestyle and entertainment features
6. **Historic**: Tests architectural style matching
7. **Transit**: Tests location and amenity proximity
8. **Quiet Areas**: Tests demographic preferences
9. **Investment**: Tests financial metrics
10. **Eco-Friendly**: Tests feature-specific search

### Error Handling

- **Ollama Connection**: Graceful failure with helpful messages
- **Model Not Found**: Clear instructions to pull models
- **Empty Data**: Validation before processing
- **ChromaDB Issues**: Automatic collection creation

### Memory Management

- Streaming document processing
- Batch embedding generation
- Efficient ChromaDB queries
- Garbage collection between models

## 🏗️ Architecture Highlights

- **Direct LlamaIndex Usage**: No unnecessary abstractions
- **Type Safety**: Full Pydantic validation
- **Smart Caching**: ChromaDB collections persist
- **Clean CLI**: Just 3 commands - create, test, compare
- **Simple Code**: ~623 lines total

## 📦 Data Sources

### Real Estate Data
The `real_estate_data/` directory contains synthetic data:
- `neighborhoods_sf.json` - San Francisco neighborhoods
- `neighborhoods_pc.json` - Park City neighborhoods  
- `properties_sf.json` - San Francisco property listings
- `properties_pc.json` - Park City property listings

Each neighborhood includes demographics, amenities, lifestyle tags, median prices, and ratings.
Each property includes address, price, bedrooms/bathrooms, square footage, and features.

## 🚧 Future Enhancements

This tool provides a foundation for:
- Adding more embedding models
- Testing on different datasets
- Building a full RAG system on top
- Implementing hybrid search strategies
- Adding more sophisticated metrics

## 📝 License

MIT License for the code.