# Unified Elasticsearch Ingestion

This module orchestrates data ingestion for the hybrid search system, combining:
- Real estate properties (keyword/faceted search)
- Wikipedia summaries (semantic search)
- Wikipedia chunks (detailed semantic search)

## Quick Start

```bash
# Full ingestion with index recreation
python -m real_estate_search.ingestion.main --force-recreate

# Update existing indices
python -m real_estate_search.ingestion.main

# Ingest only properties
python -m real_estate_search.ingestion.main --properties-only

# Ingest only Wikipedia data
python -m real_estate_search.ingestion.main --wiki-only
```

## Architecture

The ingestion module reuses existing components:
- `wiki_embed` - Provides embeddings, chunking, and ES management
- `real_estate_search.indexer` - Provides property indexing
- `LlamaIndex` - Handles document processing

Total new code: ~200 lines (just orchestration)

## Configuration

Uses standard `config.yaml` from wiki_embed:

```yaml
vector_store:
  provider: archive_elasticsearch
  elasticsearch:
    host: localhost
    port: 9200

embedding:
  provider: ollama
  ollama_model: nomic-embed-text
```

## Files

- `orchestrator.py` - Main ingestion pipeline
- `main.py` - CLI interface
- Direct imports from existing modules (no duplication)