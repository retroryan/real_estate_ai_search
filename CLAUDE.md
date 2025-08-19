# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Property Finder is a comprehensive suite of tools for real estate data analysis, Wikipedia content processing, and semantic search using embeddings. It contains four specialized modules that work together or independently for location-based information retrieval and analysis.

## Critical Architecture Components

### DSPy Framework (CRITICAL - DO NOT REMOVE)
**IMPORTANT**: The wiki_summary module's use of DSPy is **fundamental to this demo**. DSPy is an amazing framework that provides:
- Declarative language model programming with automatic prompt optimization
- Type-safe structured outputs with Pydantic integration
- Chain-of-Thought reasoning for complex extraction tasks
- Signature-based abstractions that make LLM interactions maintainable
- Automatic retry and error handling for robust processing

The DSPy implementation in `wiki_summary/summarize/extract_agent.py` showcases advanced AI engineering patterns and is a **core demonstration feature**. Any refactoring must preserve and enhance the DSPy patterns, not replace them.

## System Requirements

- **Python**: 3.8+ (3.9+ recommended)
- **Memory**: 4GB RAM minimum
- **Storage**: 5GB free space for data and models
- **OS**: macOS, Linux, Windows (WSL recommended)

## Installation

### Setup Python Environment
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

### Install Dependencies
```bash
# Main project dependencies
pip install -r requirements.txt

# For development features (testing, type checking, visualization)
pip install -e ".[dev,viz]"
```

### Ollama Setup (Required for Local Embeddings)
```bash
# Install Ollama
brew install ollama  # macOS
curl -fsSL https://ollama.ai/install.sh | sh  # Linux

# Start Ollama server (keep running in background)
ollama serve

# Pull required embedding models
ollama pull nomic-embed-text
ollama pull mxbai-embed-large

# Verify Ollama is running
curl http://localhost:11434
```

### Configure API Keys (Optional)
```bash
# Create .env file in project root
cp .env.example .env

# Edit .env and add your API keys:
# OPENAI_API_KEY=your-key-here
# OPENROUTER_API_KEY=your-key-here  
# GEMINI_API_KEY=your-key-here
# VOYAGE_API_KEY=your-key-here
```

## Module Commands

### 1. Real Estate Embedding Pipeline
Benchmarks and compares embedding models on real estate data.

```bash
# Create embeddings (edit config.yaml for model selection)
python -m real_estate_embed.main create
python -m real_estate_embed.main create --force-recreate  # Force recreation

# Test a single model
python -m real_estate_embed.main test

# Compare all available models
python -m real_estate_embed.main compare

# Compare specific models
python -m real_estate_embed.main compare --collections embeddings_nomic-embed-text embeddings_gemini_embedding
```

### 2. Wikipedia Crawler
Acquires Wikipedia data for location-based analysis.

```bash
# Deep crawl for a location
python wiki_crawl/wikipedia_location_crawler.py crawl "Park City" "Utah" --depth 2 --max-articles 20

# Search for neighborhood Wikipedia pages
python wiki_crawl/wikipedia_location_crawler.py search real_estate_data/neighborhoods_sf.json --limit 10

# Quick preview of neighborhoods
python wiki_crawl/wikipedia_location_crawler.py quick real_estate_data/neighborhoods_pc.json --limit 5

# Analyze crawled data
python wiki_crawl/wikipedia_location_crawler.py analyze data/Park_City_Utah_wikipedia.db

# List existing crawls
python wiki_crawl/wikipedia_location_crawler.py list

# Generate attribution files
python wiki_crawl/wikipedia_location_crawler.py attribution --data-dir data
```

### 3. Wikipedia Summarization
Generates structured summaries from Wikipedia HTML pages using LLM.

```bash
# Process all unprocessed Wikipedia pages
python wiki_summary/summarize_main.py

# Process with limits
python wiki_summary/summarize_main.py --limit 10 --batch-size 5

# Force reprocess existing summaries
python wiki_summary/summarize_main.py --force-reprocess

# Run validation
python wiki_summary/validation.py quick
python wiki_summary/validation.py single --page "Park City, Utah"
python wiki_summary/validation.py full
```

### 4. Wikipedia Embedding System
Creates searchable embeddings from Wikipedia articles.

```bash
# Create embeddings from Wikipedia articles
python -m wiki_embed.main create

# Test retrieval accuracy
python -m wiki_embed.main test

# Compare embedding models
python -m wiki_embed.main compare

# Quick evaluation on subset
python -m wiki_embed.test_eval
```

## Common Workflows

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
Compare embedding models on property data:

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

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test module
pytest tests/unit/test_agent.py

# Run with verbose output
pytest -v

# Type checking
mypy src/

# Module-specific tests
python -m real_estate_embed.main test --model nomic-embed-text
python wiki_summary/validation.py quick
python -m wiki_embed.test_eval
```

## Architecture Details

### Module Structure

- **real_estate_embed/**: Embedding pipeline for real estate data
  - Compares models: nomic-embed-text vs mxbai-embed-large
  - Evaluates with precision, recall, F1 scores
  - Tests on 10 realistic property search queries

- **wiki_crawl/**: Wikipedia data acquisition
  - BFS crawling with depth control
  - Relevance scoring for location articles
  - Multiple output formats (SQLite, CSV, JSON, HTML)
  - CC BY-SA 3.0 attribution generation

- **wiki_summary/**: LLM-powered summarization
  - Dual extraction: HTML parsing + LLM understanding
  - DSPy Chain-of-Thought reasoning
  - Location data with confidence scores
  - ~2 seconds per page processing

- **wiki_embed/**: Wikipedia embedding system
  - Multiple providers: Ollama, Gemini, Voyage
  - 6 query types: geographic, landmark, historical, recreational, cultural, administrative
  - Retrieval accuracy evaluation

### Data Organization

⚠️ **IMPORTANT**: All Wikipedia-related data MUST be stored under `data/wikipedia/`. Never write directly to `data/pages/` - always use `data/wikipedia/pages/` for HTML files and `data/wikipedia/wikipedia.db` for the database.

```
property_finder/
├── data/                      # Shared data directory
│   ├── real_estate_chroma_db/ # Real estate embeddings
│   ├── wiki_chroma_db/        # Wikipedia embeddings
│   ├── wikipedia/             # Wikipedia articles (REQUIRED PATH)
│   │   ├── pages/            # HTML files (use data/wikipedia/pages/, NOT data/pages/)
│   │   └── wikipedia.db      # SQLite database
│   └── test_queries.json      # Test queries
│
├── real_estate_data/          # Synthetic property data
│   ├── properties_sf.json    # San Francisco properties
│   ├── properties_pc.json    # Park City properties
│   ├── neighborhoods_sf.json # SF neighborhoods
│   └── neighborhoods_pc.json # PC neighborhoods
│
└── results/                   # Evaluation results
    └── comparison.json        # Model comparison metrics
```

### Key Design Patterns

- **Pydantic Models**: Full type safety and validation
- **Pipeline Pattern**: Each module has a main pipeline class
- **Configuration-Driven**: YAML configs for each module
- **Smart Caching**: Embeddings persist in ChromaDB
- **Modular CLI**: Each module has its own CLI interface
- **Error Recovery**: Automatic retry with exponential backoff
- **Resume Capability**: Continue from last successful operation

### Database Schemas

#### ChromaDB Collections
- Named as `{prefix}_{model_name}` (e.g., "embeddings_nomic-embed-text")
- Metadata: page_id, title, location, chunk_index, source_file

#### SQLite (Wikipedia)
```sql
-- Articles table
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    page_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    url TEXT,
    full_text TEXT,
    depth INTEGER,
    relevance_score REAL,
    latitude REAL,
    longitude REAL
);

-- Page summaries table
CREATE TABLE page_summaries (
    page_id INTEGER PRIMARY KEY,
    article_id INTEGER NOT NULL,
    summary TEXT NOT NULL,
    key_topics TEXT,
    best_city TEXT,
    best_state TEXT,
    overall_confidence REAL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

## Performance Benchmarks

| Module | Metric | Performance |
|--------|--------|------------|
| Real Estate Embed | F1 Score | 64.4% (nomic-embed-text) |
| Wiki Crawler | Articles/min | ~20 with depth=2 |
| Wiki Summary | Pages/min | ~30 with OpenRouter |
| Wiki Embed | Chunks/sec | ~25 with Ollama |

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

### Memory Issues
- Reduce batch sizes in configuration files
- Process fewer articles at once
- Use `--limit` flags where available

### API Key Issues
- Check `.env` file exists and contains valid keys
- Ensure environment variables are loaded
- Verify API quotas and limits

## Configuration Files

### real_estate_embed/config.yaml
```yaml
embedding:
  provider: ollama  # Options: ollama, gemini, voyage
  ollama_model: nomic-embed-text  # or mxbai-embed-large

chromadb:
  path: "./data/real_estate_chroma_db"
  collection_prefix: "embeddings"

chunking:
  method: simple  # or semantic
  chunk_size: 512
  chunk_overlap: 50
```

### wiki_embed/config.yaml
```yaml
embedding:
  provider: ollama  # or gemini, voyage
  ollama_model: nomic-embed-text

testing:
  top_k: 5
  min_similarity: 0.3
```

### .env (for LLM APIs)
```env
# Model selection
LLM_MODEL=openrouter/openai/gpt-4o-mini
OPENROUTER_API_KEY=your-key

# Optional API keys
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key
VOYAGE_API_KEY=your-key
```