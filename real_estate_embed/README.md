# Real Estate Embedding Pipeline

## Brief Overview

The Real Estate Embedding Pipeline is a sophisticated generative AI system that demonstrates advanced embedding generation, storage, and retrieval techniques for real estate data. Built on **LlamaIndex**, the leading framework for LLM applications, this module showcases how to leverage multiple state-of-the-art embedding models to transform property and neighborhood descriptions into high-dimensional vector representations suitable for semantic search and RAG (Retrieval-Augmented Generation) applications.

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

Expected output:
```
============================================================
EMBEDDING CREATION
============================================================
Loading configuration...
Provider: ollama
Model: nomic-embed-text

Loading documents from ./real_estate_data...
Loaded X documents
Creating semantic chunks...
Created Y chunks
Generating embeddings...
  Progress: 10/Y embeddings created
  ...
✓ Created Y embeddings

✅ Done! Y embeddings ready
```

**Note**: Embeddings are cached! Running again will show:
```
✓ Using existing Y embeddings
```

To force recreation:
```bash
python -m real_estate_embed.main create --force-recreate
```

#### 2️⃣ Test Model

```bash
python -m real_estate_embed.main test
```

Output shows metrics for each query:
```
=== Testing nomic-embed-text ===

Testing query 1/10: luxury homes in Pacific Heights...
  Precision: 0.667, Recall: 0.500
...

--- Results for nomic-embed-text ---
Average Precision: 0.725
Average Recall:    0.580
Average F1 Score:  0.644
```

#### 3️⃣ Compare Models

Compare all available embedding collections:
```bash
python -m real_estate_embed.main compare
```

Output shows comparison of all models:
```
============================================================
MODEL COMPARISON
============================================================

Available collections: embeddings_mxbai-embed-large, embeddings_nomic-embed-text
Comparing: embeddings_mxbai-embed-large, embeddings_nomic-embed-text

--- Testing mxbai-embed-large ---
Found 63 embeddings in embeddings_mxbai-embed-large
...

--- Testing nomic-embed-text ---
Found 63 embeddings in embeddings_nomic-embed-text
...

============================================================
FINAL COMPARISON
============================================================

mxbai-embed-large:
  Precision: 0.090
  Recall:    0.500
  F1 Score:  0.149

nomic-embed-text:
  Precision: 0.110
  Recall:    0.600
  F1 Score:  0.183

🏆 Winner: nomic-embed-text (F1: 0.183)

Results saved to: results/comparison.json
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

Edit `config.yaml` in this directory to adjust settings:

```yaml
embedding:
  provider: ollama  # Options: ollama, gemini, voyage
  # Ollama settings
  ollama_base_url: "http://localhost:11434"
  ollama_model: nomic-embed-text  # Options: nomic-embed-text, mxbai-embed-large
  # Gemini settings (set GOOGLE_API_KEY env variable)
  gemini_model: "models/embedding-001"
  # Voyage settings (set VOYAGE_API_KEY env variable)
  voyage_model: "voyage-3"

chromadb:
  path: "./data/real_estate_chroma_db"
  collection_prefix: "embeddings"

data:
  source_dir: "./real_estate_data"

chunking:
  method: simple  # Options: simple (fast), semantic (slow but better boundaries)
  chunk_size: 512
  chunk_overlap: 50
  breakpoint_percentile: 95
  buffer_size: 1
```

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

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Ollama connection error | Run `ollama serve` |
| Model not found | Run `ollama pull nomic-embed-text` |
| No documents loaded | Check `real_estate_data/` has JSON files |
| Collection not found | Run create command first |

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
- **Purpose**: Orchestrates embedding creation workflow
- **Key Classes**:
  - `EmbeddingPipeline`: Main pipeline controller
  - `DocumentLoader`: Loads and merges JSON data
  - `ChunkCreator`: Semantic text splitting
- **Implementation**:
  ```python
  class EmbeddingPipeline:
      def create_embeddings(self, model_name: str):
          # 1. Load documents
          docs = self.load_documents()
          # 2. Create semantic chunks  
          chunks = self.create_chunks(docs)
          # 3. Generate embeddings
          embeddings = self.embed_chunks(chunks, model_name)
          # 4. Store in ChromaDB
          self.store_embeddings(embeddings, model_name)
  ```

#### 2. Query Module (`query.py`)
- **Purpose**: Tests retrieval accuracy
- **Metrics Calculation**:
  ```python
  def calculate_metrics(retrieved, expected):
      precision = len(retrieved ∩ expected) / len(retrieved)
      recall = len(retrieved ∩ expected) / len(expected)
      f1 = 2 * (precision * recall) / (precision + recall)
      return precision, recall, f1
  ```
- **Query Types**: 10 realistic real estate queries testing different aspects

#### 3. Models Module (`models.py`)
- **Pydantic Models**:
  - `Property`: Real estate listing with validation
  - `Neighborhood`: Area demographics and features
  - `TestQuery`: Query with expected results
  - `QueryResult`: Metrics and retrieved documents
- **Type Safety**: Full validation for all data structures

#### 4. Main CLI (`main.py`)
- **Commands**:
  - `create`: Generate embeddings for a model
  - `test`: Evaluate a single model
  - `compare`: Compare all configured models
- **Implementation**: Clean Click-based CLI with progress bars

### Key Algorithms

#### Semantic Chunking Algorithm
```python
def create_semantic_chunks(documents):
    splitter = SemanticSplitterNodeParser(
        breakpoint_percentile=95,  # High similarity threshold
        buffer_size=1,              # Context overlap
        embed_model=embedding_model
    )
    return splitter.get_nodes_from_documents(documents)
```

#### Embedding Caching Strategy
```python
def get_or_create_embeddings(model_name):
    collection_name = f"embeddings_{model_name}"
    
    # Check if collection exists
    if collection_exists(collection_name):
        print(f"✓ Using existing {count} embeddings")
        return load_collection(collection_name)
    
    # Create new embeddings
    embeddings = create_embeddings(model_name)
    save_to_chromadb(embeddings, collection_name)
    return embeddings
```

#### Model Comparison Logic
```python
def compare_models(models):
    results = {}
    for model in models:
        # Create embeddings if needed
        create_embeddings(model)
        # Run test queries
        metrics = test_model(model)
        results[model] = metrics
    
    # Determine winner by F1 score
    winner = max(results.items(), key=lambda x: x[1]['f1'])
    return results, winner
```

### Data Processing Pipeline

1. **Document Loading**:
   - Reads JSON files from `real_estate_data/`
   - Merges properties and neighborhoods
   - Creates structured documents with metadata

2. **Text Preparation**:
   ```python
   def prepare_document_text(item):
       if item.type == "property":
           return f"{item.address}, {item.features}, ${item.price}"
       else:  # neighborhood
           return f"{item.name}: {item.description}, {item.amenities}"
   ```

3. **Chunk Creation**:
   - Uses LlamaIndex's `SemanticSplitterNodeParser`
   - Creates semantically coherent chunks
   - Preserves metadata (ID, type, location)

4. **Embedding Generation**:
   - Uses Ollama API for local models
   - Batch processing with progress tracking
   - ~0.5 seconds per chunk

5. **Storage**:
   - ChromaDB with persistent storage
   - Separate collection per model
   - Metadata indexing for filtering

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