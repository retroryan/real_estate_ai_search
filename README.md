# Real Estate AI Search

This repository demonstrates both **GraphRAG** and **RAG** architectures through two production-ready real estate search implementations, alongside comprehensive tools for Wikipedia content processing and semantic search using generative AI and embeddings. The data is ingested via Spark Data Pipelines, providing scalable processing and transformation capabilities. The core modules showcase how to build AI-driven data pipelines for both approaches. GraphRAG uses Neo4j where embeddings are stored as node properties within the graph database for unified hybrid search. RAG leverages Elasticsearch with vector search capabilities. Both implementations demonstrate how to prepare, process, and serve data for generative AI applications.

### Core AI Capabilities
- **Neo4j GraphRAG Implementation**: Graph-based retrieval system with native vector search, combining knowledge graph relationships with semantic embeddings for enhanced accuracy
- **Elasticsearch RAG Implementation**: RAG pipeline with hybrid text and vector search, faceted filtering, and relevance scoring for scalable retrieval
- **ChromaDB Embedding Prototyping**: Rapid prototyping environment for comparing embedding models directly with built-in benchmarking and evaluation metrics
- **DSPy Content Classification**: Advanced generative AI framework for intelligent content extraction with Chain-of-Thought reasoning
- **Multi-Model Embeddings**: Support for Ollama, OpenAI, Gemini, and Voyage AI models with automated benchmarking
- **LLM Summarization Pipeline**: Structured information extraction from Wikipedia with confidence scoring
- **Hybrid Scoring Algorithm**: Combines vector similarity, graph centrality, and feature richness for optimal search relevance
- **Semantic Chunking**: AI-powered text segmentation using embedding similarity boundaries
- **Real Estate Property Analysis**: Embedding generation and comparison for synthetic property and neighborhood data

## Project Modules

### Integration Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              Generative AI Pipeline (Data Preparation)         │
├───────────────┬──────────────┬──────────────┬──────────────────┤
│ Data Sources  │  Processing  │  AI Models   │   Storage        │
├───────────────┼──────────────┼──────────────┼──────────────────┤
│ • Wikipedia   │ • DSPy CoT   │ • Ollama     │ • Parquet        │
│ • Real Estate │ • LlamaIndex │ • OpenRouter │ • ChromaDB       │
│ • User Queries│ • Chunking   │ • Claude     │                  │
│               │ • Filtering  │ • VoyageAI   │                  │
└───────────────┴──────────────┴──────────────┴──────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                      Spark Data Pipeline                       │
├────────────────────────────────────────────────────────────────┤
│ • Distributed Data Processing & Transformation                 │
│ • Scalable ETL Operations                                      │
│ • Data Enrichment & Feature Engineering                        │
│ • Parallel Embedding Generation                                │
│ • Orchestration of All Data Flows                              │
└────────────────────────────────────────────────────────────────┘
                    ↙                       ↘
    ┌──────────────────────────┐   ┌──────────────────────────┐
    │        NEO4J              │   │     ELASTICSEARCH        │
    ├──────────────────────────┤   ├──────────────────────────┤
    │ • Knowledge Graph         │   │ • Full-Text Search       │
    │ • Native Vector Indexing  │   │ • Vector Search          │
    │ • Hybrid Graph + Vector   │   │ • Faceted Filtering      │
    │ • Relationship Retrieval  │   │ • Relevance Scoring      │
    │ • Graph Centrality        │   │ • Aggregations           │
    └──────────────────────────┘   └──────────────────────────┘
                    ↘                       ↙
                    ┌──────────────────┐
                    │   RAG/GraphRAG   │
                    │   Applications   │
                    └──────────────────┘
```

### [1. Wikipedia Summarization](./wiki_summary/README.md)
**Purpose**: Use generative AI with DSPy for Context Engineering and LLM Calling  
**Key Features**:
- **AI Content Classification**: Employs generative AI models to classify and extract relevant content
- **DSPy Pipeline**: Uses DSPy framework for structured Chain-of-Thought reasoning and prompt optimization
- **Dual Processing**: Combines HTML parsing with LLM understanding for accurate extraction
- **Confidence Scoring**: AI-generated confidence scores for location data and topic relevance
- **Key Topic Extraction**: Generative AI identifies and categorizes main topics from articles

---

### [2. Spark Data Pipeline](./data_pipeline/)
**Purpose**: Spark-based distributed data processing and transformation pipeline that adds Vector Embeddings using LlamaIndex  
**Key Features**:
- **Scalable ETL Operations**: Distributed processing of property and location data
- **Data Enrichment**: Feature engineering and data augmentation
- **Parallel Processing**: Leverages Spark for high-performance data transformations
- **Vector Embedding Integration**: Coordinates embedding generation across multiple providers like Voyage, Ollama, OpenAI, and Gemini
- **Output to Multiple Stores**: Writes to Parquet, Neo4j, and Elasticsearch

---

### [3. Neo4j GraphRAG Real Estate Search](./graph-real-estate/)
**Purpose**: Neo4j-based GraphRAG system for intelligent property and Wikipedia search with knowledge graph relationships  
**Key Features**:
- **Neo4j Native Vector Search**: 768-dimensional embeddings with ANN (Approximate Nearest Neighbor) indexing
- **Hybrid Scoring Algorithm**: Combines vector similarity, graph centrality, and feature richness
- **Knowledge Graph Structure**: Properties, neighborhoods, features, and Wikipedia articles connected through semantic relationships
- **Multi-Provider Embeddings**: Support for Ollama, OpenAI, and Gemini models
- **Advanced Graph Queries**: Relationship-aware retrieval using Cypher queries
- **Natural Language Search**: "modern condo with city views", "family home near schools"

---

### [4. Elasticsearch Real Estate RAG](./real_estate_search/)
**Purpose**: Elasticsearch-based RAG real estate and Wikipedia search  
**Key Features**:
- AI-enhanced full-text search with multi-field queries and relevance scoring
- Intelligent geographic radius search with coordinate-based ranking
- AI-driven faceted search and dynamic filtering
- REST API with FastAPI and OpenAPI documentation
- Type-safe Pydantic models with AI validation and comprehensive error handling
- Circuit breaker and retry logic for resilience

---

### [5. Common Embeddings](./common_embeddings/)
**Purpose**: Testing LlamaIndex Semantic Chunking and embedding evaluations using Voyage, Ollama and OpenAI with ChromaDB  
**Key Features**:
- **Semantic Chunking**: LlamaIndex-powered intelligent text segmentation
- **Multi-Provider Comparison**: Benchmarks Voyage, Ollama, and OpenAI embeddings
- **ChromaDB Integration**: Vector storage and retrieval testing
- **Evaluation Metrics**: Comprehensive accuracy and performance analysis
- **Chunking Strategies**: Compare semantic vs fixed-size chunking approaches
- **Retrieval Testing**: End-to-end RAG pipeline evaluation

## Generative AI Technologies

This project leverages an extensive suite of cutting-edge generative AI frameworks, models, and techniques:

### Core AI Frameworks

| Framework | Purpose | Modules Using It |
|-----------|---------|-----------------|
| **LlamaIndex** | Document processing, embedding generation, semantic chunking | `real_estate_embed`, `wiki_embed` |
| **DSPy (Stanford)** | LLM programming, Chain-of-Thought reasoning, prompt optimization | `wiki_summary` |

### Infrastructure & Storage

| System | Purpose | Modules Using It |
|--------|---------|-----------------|
| **Neo4j** | Graph database with native vector indexing for GraphRAG, hybrid search, and relationship-aware retrieval | `graph-real-estate` |
| **Elasticsearch** | Hybrid text/vector search, RAG retrieval layer | `real_estate_search`, `wiki_embed` |
| **ChromaDB** | Vector database for embedding storage and similarity search | `real_estate_embed`, `wiki_embed` |
| **SQLite** | Lightweight relational database for article metadata | `wiki_crawl`, `wiki_summary` |

### Embedding Models & Providers

| Provider | Models | Capabilities | Use Cases |
|----------|--------|--------------|-----------|
| **Ollama (Local)** | `nomic-embed-text` (768d), `mxbai-embed-large` (1024d) | Privacy-preserving, no API costs | Development, sensitive data |
| **Claude (Anthropic)** | Claude 4 Opus, Sonnet | Advanced reasoning, long context, tool calling | Complex analysis, summarization |
| **Google Gemini** | `models/embedding-001` | Cloud-scale, multilingual | Production deployments |
| **VoyageAI** | `voyage-3`, `voyage-finance-2` | Domain-optimized embeddings | Specialized search |
| **OpenAI** | `text-embedding-3-*` | Industry standard | Baseline comparisons |

### Language Models (LLMs)

| Provider | Access Method | Models | Primary Use |
|----------|--------------|--------|-------------|
| **OpenRouter** | API Gateway | GPT-4, Claude, Llama, 100+ models | Content summarization |
| **OpenAI** | Direct API | GPT-4o, GPT-4o-mini | High-quality generation |
| **Google Gemini** | Direct API | Gemini Pro, Gemini Ultra | Multimodal understanding |
| **Ollama** | Local deployment | Llama 3, Mistral, Phi | Privacy-sensitive tasks |

### Advanced AI Techniques Implemented

#### Embedding & Vector Search
- **Semantic Chunking**: AI-powered text segmentation using embedding similarity boundaries
- **Augmented Embeddings**: Enhanced chunks with contextual summaries for better retrieval
- **Hybrid Search**: Combining BM25 text scoring with vector similarity
- **Multi-Model Benchmarking**: Automated comparison across embedding providers

#### AI Content Intelligence
- **Chain-of-Thought (CoT) Reasoning**: Multi-step AI logical analysis for classification
- **AI Structured Data Extraction**: Converting unstructured text to typed schemas using LLMs
- **AI Summarization**: Intelligent content summarization with key information extraction
- **AI Confidence Scoring**: Probabilistic quality assessment of extractions
- **AI Content Classification Pipeline**: Multi-stage AI filtering and categorization

#### RAG & GraphRAG Preparation
- **Document Preprocessing**: Optimized chunking for LLM context windows
- **Metadata Enrichment**: Adding semantic tags for improved retrieval
- **Knowledge Graph Structuring**: Preparing data for Neo4j relationships
- **Relevance Filtering**: Domain-specific content evaluation

## Getting Started

### Installation

#### 1. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

#### 2. Install Dependencies
```bash
# Install all dependencies using pyproject.toml
pip install -e .
```

#### 3. Install and Configure Ollama (for local embeddings)
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull embedding models
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

#### 4. Configure API Keys (optional)
For enhanced functionality with external APIs:

```bash
# Create .env file in project root
cp .env.example .env

# Edit .env and add your API keys:
# OPENAI_API_KEY=your-key-here
# OPENROUTER_API_KEY=your-key-here
# GEMINI_API_KEY=your-key-here
# VOYAGE_API_KEY=your-key-here
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password
```

## Data Organization

```
real_estate_ai_search/
├── data/                      # Shared data directory
│   ├── parquet/              # Parquet files for Spark processing
│   ├── chroma_db/            # ChromaDB vector storage
│   ├── wikipedia/            # Wikipedia articles and pages
│   │   ├── pages/           # HTML files
│   │   └── wikipedia.db     # SQLite database
│   └── embeddings/          # Generated embeddings
│
├── data_pipeline/            # Spark Data Pipeline
│   ├── core/                # Core pipeline components
│   ├── loaders/            # Data loaders
│   ├── enrichment/         # Enrichment processors
│   └── outputs/            # Output writers
│
├── graph-real-estate/        # Neo4j GraphRAG module
│   ├── src/                # Source code
│   │   ├── models/        # Pydantic models
│   │   ├── vectors/       # Embedding pipeline
│   │   └── database/      # Neo4j client
│   └── search_properties.py # Hybrid search
│
├── real_estate_search/       # Elasticsearch RAG module
│   ├── api/                # FastAPI endpoints
│   ├── models/             # Data models
│   └── search/             # Search logic
│
├── common_embeddings/        # Embedding evaluation
│   ├── chunkers/           # Semantic chunking
│   ├── embedders/          # Multi-provider embeddings
│   └── evaluators/         # Performance metrics
│
└── real_estate_data/         # Source data
    ├── properties_*.json    # Property datasets
    └── neighborhoods_*.json # Neighborhood datasets
```

## Common Workflows

### Spark Data Pipeline
Run the complete data pipeline with output to multiple destinations:

```bash
# Run Spark pipeline with outputs to Neo4j, Elasticsearch, and Parquet
python -m data_pipeline --output-destination neo4j,archive_elasticsearch,parquet

# Run with specific configuration
python -m data_pipeline --config config/production.yaml

# Run in test mode with sample data
python -m data_pipeline --test-mode --sample-size 100
```

### Neo4j GraphRAG Pipeline
Build a complete GraphRAG system with Neo4j:

```bash
# 1. Setup Neo4j with Docker
docker-compose up -d

# 2. Run Spark pipeline to populate Neo4j
python -m data_pipeline --output-destination neo4j

# 3. Test hybrid search
python graph-real-estate/search_properties.py "modern condo with city views" --demo
```

### Elasticsearch RAG Pipeline
Set up Elasticsearch-based RAG system:

```bash
# 1. Start Elasticsearch
docker-compose up archive_elasticsearch -d

# 2. Run Spark pipeline to populate Elasticsearch
python -m data_pipeline --output-destination archive_elasticsearch

# 3. Start the search API
uvicorn real_estate_search.api:app --reload
```

### Complete Wikipedia Pipeline
Process Wikipedia data from crawling to searchable embeddings:

```bash
# 1. Generate summaries with DSPy
python wiki_summary/summarize_main.py --limit 50

# 2. Run Spark pipeline for Wikipedia data
python -m data_pipeline --data-type wikipedia

# 3. Test embeddings with LlamaIndex
python -m common_embeddings.main evaluate
```

### Neighborhood Research
Find Wikipedia pages for specific neighborhoods:

```bash
# Search for neighborhood pages
python wiki_crawl/wikipedia_location_crawler.py search real_estate_data/neighborhoods_sf.json

# Quick preview
python wiki_crawl/wikipedia_location_crawler.py quick real_estate_data/neighborhoods_pc.json
```

## Testing

Each module includes its own test suite:

```bash
# Test real estate embeddings
python -m real_estate_embed.main test --model nomic-embed-text

# Test Wikipedia summarization
python wiki_summary/validation.py quick

# Test Wikipedia embeddings
python -m wiki_embed.test_eval

# Run all unit tests
python -m pytest tests/
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License for code. Wikipedia content is under CC BY-SA 3.0.

## Acknowledgments

- **LlamaIndex**: For the embedding framework
- **Ollama**: For local LLM support
- **ChromaDB**: For vector storage
- **Wikipedia**: For content (CC BY-SA 3.0)
- **DSPy**: For structured LLM interactions