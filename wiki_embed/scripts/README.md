# Wiki Embed Scripts

This directory contains testing and utility scripts for the wiki_embed Elasticsearch integration.

## Files

### Setup Scripts
- **`setup_elasticsearch.sh`** - Automated Elasticsearch setup using Docker
  - Starts single-node Elasticsearch instance
  - Configures for development/testing
  - Includes health checks and verification

### Testing Scripts
- **`test_elasticsearch_basic.py`** - Basic functionality testing
  - Tests small dataset (5 articles)
  - Verifies embedding creation and search
  - Quick validation of Elasticsearch integration

- **`compare_vector_stores.py`** - ChromaDB vs Elasticsearch comparison
  - Side-by-side performance testing
  - Result similarity analysis
  - Detailed comparison reports

- **`create_full_elasticsearch_embeddings.py`** - Full-scale embedding creation
  - Processes entire Wikipedia dataset
  - Resource monitoring and progress tracking
  - Performance statistics collection

### Documentation
- **`ELASTICSEARCH_TESTING.md`** - Comprehensive testing guide
  - Step-by-step instructions
  - Expected outputs and timings
  - Troubleshooting guide

## Usage

All scripts should be run from this directory:

```bash
cd wiki_embed/scripts
```

### Quick Test Sequence

1. **Setup Elasticsearch:**
   ```bash
   ./setup_elasticsearch.sh
   ```

2. **Run basic tests:**
   ```bash
   python test_elasticsearch_basic.py
   ```

3. **Compare vector stores (optional):**
   ```bash
   python compare_vector_stores.py
   ```

4. **Create full embeddings (production):**
   ```bash
   python create_full_elasticsearch_embeddings.py
   ```

## Prerequisites

- **Docker** - For Elasticsearch setup
- **Ollama** - With `nomic-embed-text` model
- **Python packages** - All wiki_embed dependencies installed
- **Wikipedia data** - Available in `../../data/wikipedia/pages/`
- **Environment variables** (optional) - For Elasticsearch authentication:
  ```bash
  cp ../wiki_embed/.env.sample ../wiki_embed/.env
  # Edit .env file to add ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
  ```

## Directory Structure

```
wiki_embed/scripts/
├── README.md                              # This file
├── ELASTICSEARCH_TESTING.md               # Testing guide
├── setup_elasticsearch.sh                 # Elasticsearch setup
├── test_elasticsearch_basic.py            # Basic tests
├── compare_vector_stores.py               # Comparison tool
└── create_full_elasticsearch_embeddings.py # Full-scale creation
```

## Important Notes

- **Path Handling**: Scripts are designed to work from this directory and reference data files using relative paths (`../../data/`)
- **Import Handling**: Scripts add the project root to Python path for importing wiki_embed modules
- **Configuration**: Scripts create temporary configuration files for testing
- **Self-Contained**: This directory contains everything needed for Elasticsearch testing

## Troubleshooting

If scripts fail to import wiki_embed modules:
```bash
# Ensure you're in the correct directory
pwd  # Should end with /wiki_embed/scripts

# Check project structure
ls ../../  # Should show wiki_embed directory
```

If Elasticsearch connection fails:
```bash
# Check if Elasticsearch is running
docker ps | grep elasticsearch

# Restart if needed
./setup_elasticsearch.sh
```

For detailed troubleshooting, see `ELASTICSEARCH_TESTING.md`.