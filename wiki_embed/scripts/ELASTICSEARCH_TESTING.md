# Elasticsearch Testing Guide

This guide covers testing the Elasticsearch integration for the `wiki_embed` module.

## Phase 3: Basic Elasticsearch Testing

### Prerequisites

1. **Ollama running** with `nomic-embed-text` model:
   ```bash
   ollama serve
   ollama pull nomic-embed-text
   ```

2. **Wikipedia data available** in `./data/wikipedia/pages/`

3. **Docker installed** for Elasticsearch

4. **Environment variables configured** (optional, for authenticated Elasticsearch):
   ```bash
   # Copy sample environment file
   cp wiki_embed/.env.sample wiki_embed/.env
   
   # Edit wiki_embed/.env to add your Elasticsearch credentials:
   # ELASTICSEARCH_USERNAME=elastic
   # ELASTICSEARCH_PASSWORD=your_password_here
   ```

### Step 1: Set Up Elasticsearch

Run the automated setup script from the wiki_embed/scripts directory:

```bash
cd wiki_embed/scripts
./setup_elasticsearch.sh
```

This will:
- Start Elasticsearch in Docker
- Configure it for single-node testing
- Disable security for simplicity
- Verify the connection

**Manual verification:**
```bash
curl http://localhost:9200
```

### Step 2: Run Basic Tests

Execute the basic functionality test from the scripts directory:

```bash
cd wiki_embed/scripts
python test_elasticsearch_basic.py
```

This test will:
- ✅ Verify Elasticsearch connection
- ✅ Create embeddings for 5 articles
- ✅ Test search functionality
- ✅ Validate result format

**Expected output:**
```
🧪 Running Basic Elasticsearch Tests
==================================================

==================== Elasticsearch Connection ====================
🔍 Testing Elasticsearch connection...
✅ Connected to Elasticsearch 8.11.0
✅ Successfully created test index
✅ Successfully deleted test index

Elasticsearch Connection: ✅ PASSED

==================== Embedding Creation ====================
📦 Testing embedding creation with Elasticsearch...
✅ Configuration loaded (max_articles: 5)
✅ Pipeline initialized
✅ Created 45 embeddings in 12.3 seconds

Embedding Creation: ✅ PASSED

==================== Search Functionality ====================
🔍 Testing search functionality...
✅ Query tester initialized
🔍 Running 2 test queries...

  Query 1: parks and recreation in Utah
    ✅ Found 3 results in 0.025s
    📄 Top result: Park City, Utah
    🎯 Page ID: 12345

  Query 2: mountain skiing resort
    ✅ Found 3 results in 0.018s
    📄 Top result: Park City Mountain Resort
    🎯 Page ID: 67890

✅ All search queries completed successfully

Search Functionality: ✅ PASSED

📊 TEST SUMMARY
==================================================
Elasticsearch Connection  ✅ PASSED
Embedding Creation        ✅ PASSED
Search Functionality      ✅ PASSED
ChromaDB Comparison       ✅ PASSED

Overall: 4/4 tests passed
🎉 All tests passed! Elasticsearch integration is working correctly.
```

### Step 3: Compare Vector Stores (Optional)

If you have existing ChromaDB embeddings:

```bash
cd wiki_embed/scripts
python compare_vector_stores.py
```

This will:
- Run identical queries on both ChromaDB and Elasticsearch
- Compare result similarity and performance
- Generate a detailed comparison report

## Phase 4: Full-Scale Testing

### Step 1: Create All Embeddings

**⚠️ Warning:** This will process all Wikipedia articles and may take 30+ minutes.

```bash
cd wiki_embed/scripts
python create_full_elasticsearch_embeddings.py
```

The script will:
1. Check system resources and Elasticsearch health
2. Estimate time and storage requirements
3. Ask for confirmation before proceeding
4. Create embeddings with progress monitoring
5. Save performance statistics

**Expected flow:**
```
🔧 Full-Scale Elasticsearch Embedding Creation
============================================================
🔍 Pre-flight Checks:
💻 System Resources Check:
   RAM: 8.2GB available / 16.0GB total
   Disk: 45.3GB available / 250.0GB total
   CPU: 8 cores

🔍 Elasticsearch Health Check:
   Status: green
   Nodes: 1
   Current indices size: 0.12GB

📊 Estimating Requirements:
   Counting Wikipedia articles...
   Total articles: 1,247
   Estimated chunks: 9,976
   Estimated storage: 32.1MB
   Estimated time: 33.3 minutes

📋 Ready to create embeddings:
   Articles: ~1,247
   Estimated chunks: ~9,976
   Estimated time: ~33 minutes
   Estimated storage: ~32MB

❓ Continue with embedding creation? (y/N): y

🚀 Starting Full-Scale Embedding Creation
============================================================
✅ Configuration loaded
   Provider: ollama
   Vector Store: elasticsearch
   Embedding Method: traditional
✅ Pipeline initialized

🕐 Starting embedding creation at: 2024-01-15 14:30:25
   Initial memory usage: 45.2%

[Progress updates during creation...]

============================================================
✅ EMBEDDING CREATION COMPLETE!
============================================================
📊 Final Statistics:
   Total embeddings: 9,823
   Total time: 28.7 minutes
   Average rate: 5.7 embeddings/second
   Memory change: 45.2% → 52.1%
📈 Statistics saved to: elasticsearch_embedding_stats.json

🔍 Validating Created Embeddings
========================================
   📄 wiki_embeddings_nomic-embed-text_traditional: 9,823 documents (145.2mb)

✅ Total embeddings: 9,823
✅ Search test successful
🎉 Full-scale embedding creation completed successfully!
```

### Step 2: Test Full Dataset

Run the existing wiki_embed test suite:

```bash
# Update config to use Elasticsearch (from project root)
sed -i '' 's/provider: chromadb/provider: elasticsearch/' wiki_embed/config.yaml

# Run tests (from project root)
python -m wiki_embed.main test
```

## Troubleshooting

### Elasticsearch Connection Issues

```bash
# Check if Elasticsearch is running
docker ps | grep elasticsearch

# Check Elasticsearch logs
docker logs elasticsearch-test

# Restart Elasticsearch
docker restart elasticsearch-test
```

### Memory Issues

```bash
# Check memory usage
docker stats elasticsearch-test

# Increase Docker memory if needed (Docker Desktop > Settings > Resources)
```

### Index Issues

```bash
# List all indices
curl http://localhost:9200/_cat/indices

# Delete test indices
curl -X DELETE http://localhost:9200/test_*
curl -X DELETE http://localhost:9200/wiki_embeddings*
```

### Ollama Issues

```bash
# Check if Ollama is running
curl http://localhost:11434

# Check available models
ollama list

# Pull model if missing
ollama pull nomic-embed-text
```

## Configuration Switching

To switch between ChromaDB and Elasticsearch, update `wiki_embed/config.yaml`:

**For ChromaDB:**
```yaml
vector_store:
  provider: chromadb
  chromadb:
    path: "./data/wiki_chroma_db"
    collection_prefix: "wiki_embeddings"
```

**For Elasticsearch (without authentication):**
```yaml
vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "wiki_embeddings"
```

**For Elasticsearch (with authentication):**
```yaml
vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "wiki_embeddings"
    # Authentication will be loaded from environment variables:
    # ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
```

## Authentication Configuration

### Environment Variables
The easiest way to configure Elasticsearch authentication is using environment variables:

1. **Copy the sample environment file:**
   ```bash
   cp wiki_embed/.env.sample wiki_embed/.env
   ```

2. **Edit `wiki_embed/.env` to add your credentials:**
   ```env
   # Elasticsearch authentication
   ELASTICSEARCH_USERNAME=elastic
   ELASTICSEARCH_PASSWORD=your_password_here
   ```

3. **The credentials will be automatically loaded** when the module starts.

### Direct Configuration (Not Recommended)
You can also specify credentials directly in the config file, but this is not recommended for security reasons:

```yaml
vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "wiki_embeddings"
    username: "elastic"
    password: "your_password_here"  # Not recommended for production
```

## Quick Start

To run the basic test:

```bash
# Navigate to scripts directory
cd wiki_embed/scripts

# 1. Set up Elasticsearch
./setup_elasticsearch.sh

# 2. Run basic tests
python test_elasticsearch_basic.py

# 3. Compare vector stores (if ChromaDB exists)
python compare_vector_stores.py

# 4. Create full embeddings (when ready)
python create_full_elasticsearch_embeddings.py
```

## Performance Expectations

### Basic Test (5 articles):
- Embedding creation: ~10-30 seconds
- Search latency: ~20-50ms per query
- Storage: ~1-5MB

### Full Dataset (~1,200 articles):
- Embedding creation: ~20-40 minutes
- Storage: ~30-100MB
- Memory usage: ~200-500MB additional

### Comparison with ChromaDB:
- **Setup**: Elasticsearch requires Docker, ChromaDB is file-based
- **Performance**: Similar embedding creation speed, slightly higher search latency
- **Storage**: Comparable storage requirements
- **Accuracy**: Should achieve >80% result similarity