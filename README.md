# Real Estate AI Search

This repository provides a comprehensive toolkit for real estate data analysis, Wikipedia content processing, and semantic search using generative AI and embeddings. It demonstrates how to build AI-driven data pipelines for both GraphRAG using Neo4j with knowledge graphs and RAG using Elasticsearch with vector search, showing how to prepare, process, and serve data for generative AI applications using either approach.

### Core AI Capabilities
- **Neo4j GraphRAG Implementation**: Graph-based retrieval system with native vector search, combining knowledge graph relationships with semantic embeddings for enhanced accuracy
- **Elasticsearch RAG Implementation**: RAG pipeline with hybrid text and vector search, faceted filtering, and relevance scoring for scalable retrieval
- **DSPy Content Classification**: Advanced generative AI framework for intelligent content extraction with Chain-of-Thought reasoning
- **Multi-Model Embeddings**: Support for Ollama, OpenAI, Gemini, and Voyage AI models with automated benchmarking
- **LLM Summarization Pipeline**: Structured information extraction from Wikipedia with confidence scoring
- **Hybrid Scoring Algorithm**: Combines vector similarity, graph centrality, and feature richness for optimal search relevance
- **Semantic Chunking**: AI-powered text segmentation using embedding similarity boundaries
- **Real Estate Property Analysis**: Embedding generation and comparison for synthetic property and neighborhood data

## Project Modules

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Generative AI Pipeline                       │
├───────────────┬──────────────┬──────────────┬──────────────────┤
│ Data Sources  │  Processing  │  AI Models   │   Storage        │
├───────────────┼──────────────┼──────────────┼──────────────────┤
│ • Wikipedia   │ • DSPy CoT   │ • Ollama     │ • NEO4J GRAPHRAG │
│ • Real Estate │ • LlamaIndex │ • OpenRouter │ • Elasticsearch  │
│ • User Queries│ • Chunking   │ • Gemini     │ • ChromaDB       │
│               │ • Filtering  │ • VoyageAI   │ • SQLite         │
└───────────────┴──────────────┴──────────────┴──────────────────┘
                              ↓
        ┌─────────────────────────────────────────────┐
        │         NEO4J GRAPHRAG SYSTEM               │
        ├─────────────────────────────────────────────┤
        │ • Knowledge Graph Construction              │
        │ • Native Vector Indexing                    │
        │ • Hybrid Graph + Vector Search             │
        │ • Relationship-Aware Retrieval             │
        │ • Graph Centrality Scoring                 │
        └─────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │   RAG/GraphRAG   │
                    │   Applications   │
                    └──────────────────┘
```

### [1. Real Estate Embedding Pipeline](./real_estate_embed/)
**Purpose**: Use generative AI to create, store, and benchmark semantic embeddings for synthetic real estate data  
**Key Features**:
- **AI Embedding Generation**: Uses generative AI models to create semantic embeddings from synthetic property descriptions
- **Multi-Model Support**: Compare embeddings from nomic-embed-text, mxbai-embed-large, and other AI models
- **Vector Storage**: Stores AI-generated embeddings in ChromaDB for efficient similarity search
- **RAG Preparation**: Prepares embeddings for use in retrieval-augmented generation pipelines
- **Performance Metrics**: Evaluates retrieval accuracy with precision, recall, and F1 scores
- **Realistic Testing**: Tests with 10 real-world property search queries on synthetic data

**Quick Start**: `python -m real_estate_embed.main compare`

---

### [2. Wikipedia Crawler](./wiki_crawl/)
**Purpose**: Acquire Wikipedia data for location-based analysis  
**Key Features**:
- BFS crawling with depth control
- Relevance scoring for location articles
- Multiple output formats (SQLite, CSV, JSON, HTML)
- Neighborhood-specific search capabilities

**Quick Start**: `python wiki_crawl/wikipedia_location_crawler.py crawl "Park City" "Utah"`

---

### [3. Wikipedia Summarization](./wiki_summary/)
**Purpose**: Use generative AI with DSPy for intelligent content classification and summarization  
**Key Features**:
- **AI Content Classification**: Employs generative AI models to classify and extract relevant content
- **DSPy Pipeline**: Uses DSPy framework for structured Chain-of-Thought reasoning and prompt optimization
- **Dual Processing**: Combines HTML parsing with LLM understanding for accurate extraction
- **Confidence Scoring**: AI-generated confidence scores for location data and topic relevance
- **Key Topic Extraction**: Generative AI identifies and categorizes main topics from articles

**Quick Start**: `python wiki_summary/summarize_main.py`

---

### [4. Wikipedia Embedding System](./wiki_embed/)
**Purpose**: Generate and store AI embeddings from Wikipedia articles for semantic search  
**Key Features**:
- **Generative AI Embeddings**: Creates semantic embeddings using multiple AI providers (Ollama, Gemini, Voyage, OpenAI)
- **Vector Database Storage**: Stores AI-generated embeddings in ChromaDB for fast similarity search
- **RAG Integration**: Prepares embeddings for retrieval-augmented generation workflows
- **Multi-Query Testing**: Tests 6 query types (geographic, landmark, historical, recreational, cultural, administrative)
- **AI Model Comparison**: Benchmarks different embedding models for optimal retrieval performance
- **Location-Aware Retrieval**: Uses AI to understand spatial and semantic relationships

**Quick Start**: `python -m wiki_embed.main create`

---

### [5. AI-Enhanced Real Estate Search Engine](./real_estate_search/)
**Purpose**: AI-powered Elasticsearch-based property search system for synthetic data  
**Key Features**:
- AI-enhanced full-text search with multi-field queries and relevance scoring
- Intelligent geographic radius search with coordinate-based ranking
- AI-driven faceted search and dynamic filtering
- REST API with FastAPI and OpenAPI documentation
- Type-safe Pydantic models with AI validation and comprehensive error handling
- Circuit breaker and retry logic for resilience

**Quick Start**: `python scripts/setup_index.py --data-dir ../real_estate_data && python real_estate_search/api/run.py`

---

### [6. Neo4j GraphRAG Real Estate Search](./graph-real-estate/)
**Purpose**: Neo4j-based GraphRAG system for intelligent property search with knowledge graph relationships  
**Key Features**:
- **Neo4j Native Vector Search**: 768-dimensional embeddings with ANN (Approximate Nearest Neighbor) indexing
- **Hybrid Scoring Algorithm**: Combines vector similarity, graph centrality, and feature richness
- **Knowledge Graph Structure**: 84 properties, 387 features, 21 neighborhoods, 1,267 relationships
- **Multi-Provider Embeddings**: Support for Ollama, OpenAI, and Gemini models
- **Advanced Graph Queries**: Relationship-aware retrieval using Cypher queries
- **Performance**: < 100ms search response, supports 100K+ properties
- **Natural Language Search**: "modern condo with city views", "family home near schools"

**Quick Start**: 
```bash
# Build graph and create embeddings
python graph-real-estate/main.py all
python graph-real-estate/create_embeddings.py

# Search properties
python graph-real-estate/search_properties.py "luxury property with mountain views"
```


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
- **AI Confidence Scoring**: Probabilistic quality assessment of extractions
- **AI Content Classification Pipeline**: Multi-stage AI filtering and categorization

#### RAG & GraphRAG Preparation
- **Document Preprocessing**: Optimized chunking for LLM context windows
- **Metadata Enrichment**: Adding semantic tags for improved retrieval
- **Knowledge Graph Structuring**: Preparing data for Neo4j relationships
- **Relevance Filtering**: Domain-specific content evaluation

### Performance & Optimization

| Technique | Implementation  |
|-----------|---------------|-------|
| **Semantic Caching** | Content-hash based LLM response caching |
| **Batch Processing** | Parallel embedding generation |
| **Smart Chunking** | Embedding-based boundaries |
| **Model Selection** | Automated A/B testing |


## Getting Started

### System Requirements

- **Python**: 3.8+ (3.9+ recommended)
- **Memory**: 4GB RAM minimum
- **Storage**: 5GB free space for data and models
- **OS**: macOS, Linux, Windows (WSL recommended)
- **Elasticsearch**: 8.x (optional, for real estate search engine)

### Installation

#### 2. Set Up Python Environment
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

#### 3. Install Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt
```

#### 4. Install and Configure Ollama (for local embeddings)
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

#### 5. Configure API Keys (optional)
For enhanced functionality with external APIs:

```bash
# Create .env file in project root
cp .env.example .env

# Edit .env and add your API keys:
# OPENAI_API_KEY=your-key-here
# OPENROUTER_API_KEY=your-key-here
# GEMINI_API_KEY=your-key-here
# VOYAGE_API_KEY=your-key-here
```

## Data Organization

```
property_finder/
├── data/                      # Shared data directory
│   ├── real_estate_chroma_db/ # Embeddings for real estate
│   ├── wiki_chroma_db/        # Embeddings for Wikipedia
│   ├── wikipedia/             # Wikipedia articles and pages
│   │   ├── pages/            # HTML files
│   │   └── wikipedia.db      # SQLite database
│   └── test_queries.json      # Test queries for evaluation
│
├── graph-real-estate/         # Neo4j GraphRAG module
│   ├── src/                  # Source code
│   │   ├── models/          # Pydantic models
│   │   ├── vectors/         # Embedding pipeline
│   │   └── database/        # Neo4j client
│   ├── main.py              # Graph builder
│   ├── create_embeddings.py # Vector generation
│   └── search_properties.py # Hybrid search
│
├── real_estate_data/          # Synthetic property data (AI-generated for demo purposes)
│   ├── properties_sf.json    # Synthetic San Francisco properties
│   ├── properties_pc.json    # Synthetic Park City properties
│   ├── neighborhoods_sf.json # Synthetic SF neighborhoods
│   └── neighborhoods_pc.json # Synthetic PC neighborhoods
│
└── results/                   # Evaluation results
    └── comparison.json        # Model comparison metrics
```

## Common Workflows

### Neo4j GraphRAG Pipeline
Build a complete GraphRAG system with Neo4j:

```bash
# 1. Setup Neo4j with Docker
docker-compose up -d

# 2. Build the knowledge graph
python graph-real-estate/main.py all

# 3. Generate vector embeddings
python graph-real-estate/create_embeddings.py

# 4. Test hybrid search
python graph-real-estate/search_properties.py "modern condo with city views" --demo
```

### Complete Wikipedia Pipeline
Process Wikipedia data from crawling to searchable embeddings:

```bash
# 1. Crawl Wikipedia for a location
python wiki_crawl/wikipedia_location_crawler.py crawl "Park City" "Utah" --depth 2

# 2. Generate summaries with LLM
python wiki_summary/summarize_main.py --limit 50

# 3. Create embeddings for search
python -m wiki_embed.main create

# 4. Test retrieval accuracy
python -m wiki_embed.main test
```

### Real Estate Analysis
Compare embedding models on synthetic property data:

```bash
# Create embeddings for both models
python -m real_estate_embed.main create --model nomic-embed-text
python -m real_estate_embed.main create --model mxbai-embed-large

# Compare performance
python -m real_estate_embed.main compare
```

### Neighborhood Research
Find Wikipedia pages for specific neighborhoods:

```bash
# Search for neighborhood pages
python wiki_crawl/wikipedia_location_crawler.py search real_estate_data/neighborhoods_sf.json

# Quick preview
python wiki_crawl/wikipedia_location_crawler.py quick real_estate_data/neighborhoods_pc.json
```

## 📝 Dependencies

Core dependencies (see `requirements.txt` for complete list):

```txt
# Graph Database
neo4j>=5.0.0

# LLM and Embeddings
llama-index>=0.9.0
ollama>=0.1.0
openai>=1.0.0
dspy-ai>=2.0.0

# Vector Storage
chromadb>=0.4.0

# Data Processing
beautifulsoup4>=4.12.0
pydantic>=2.0.0
pandas>=2.0.0

# Wikipedia API
requests>=2.31.0
wikipedia-api>=0.5.0

# Utilities
python-dotenv>=1.0.0
tqdm>=4.65.0
click>=8.1.0
```

## 🧪 Testing

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

## Documentation

For detailed documentation on each module:
- [Neo4j GraphRAG Documentation](./graph-real-estate/README.md)
- [Real Estate Embeddings Documentation](./real_estate_embed/README.md)
- [Wikipedia Crawler Documentation](./wiki_crawl/README.md)
- [Wikipedia Summarization Documentation](./wiki_summary/README.md)
- [Wikipedia Embeddings Documentation](./wiki_embed/README.md)
- [Real Estate Search Engine Documentation](./real_estate_search/README.md)

## Troubleshooting

### Common Issues

**Ollama Connection Error**
```bash
# Ensure Ollama is running
ollama serve

# Verify connection
curl http://localhost:11434
```

**Missing Model**
```bash
# Pull required models
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

**Memory Issues**
- Reduce batch sizes in configuration files
- Process fewer articles at once
- Use `--limit` flags where available

**API Key Issues**
- Check `.env` file exists and contains valid keys
- Ensure environment variables are loaded
- Verify API quotas and limits

## 📮 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review module-specific READMEs