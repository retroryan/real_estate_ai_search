# Elasticsearch Indexer Module

This module provides specialized indexers for managing document ingestion, processing, and indexing into Elasticsearch. It handles complex pipeline operations, bulk indexing, and document enrichment.

## Architecture Overview

The indexer module separates concerns between:
- **Document Processing**: Loading and preparing documents
- **Pipeline Management**: Elasticsearch ingest pipeline configuration
- **Bulk Operations**: Efficient batch indexing with error handling
- **Enrichment Logic**: Document enhancement with additional content

## Wikipedia Indexer

The `WikipediaIndexer` class manages the enrichment of Wikipedia articles with full HTML content.

### Pipeline Processing Flow

```
1. Query Phase
   ↓
   Find documents with article_filename but no content_loaded
   ↓
2. Load Phase
   ↓
   Read HTML files from disk (data/wikipedia/pages/)
   ↓
3. Transform Phase
   ↓
   Process through wikipedia_ingest_pipeline
   ↓
4. Index Phase
   ↓
   Bulk update documents with processed content
```

### Elasticsearch Ingest Pipeline

The `wikipedia_ingest_pipeline` executes server-side during bulk indexing:

#### Pipeline Definition
Location: `elasticsearch/pipelines/wikipedia_ingest.json`

```json
{
  "description": "Pipeline for processing Wikipedia HTML content",
  "processors": [
    {
      "html_strip": {
        "field": "full_content",
        "ignore_missing": true
      }
    },
    {
      "trim": {
        "field": "full_content",
        "ignore_missing": true
      }
    },
    {
      "script": {
        "lang": "painless",
        "source": "if (ctx.full_content != null && ctx.full_content.length() > 0) { 
                    ctx.content_loaded = true; 
                    ctx.content_loaded_at = new Date(); 
                    ctx.content_length = ctx.full_content.length(); 
                  }"
      }
    }
  ]
}
```

#### Pipeline Processors Explained

1. **HTML Strip Processor**
   - Removes all HTML tags from `full_content`
   - Preserves text while removing markup
   - Handles nested tags and HTML entities

2. **Trim Processor**
   - Removes leading/trailing whitespace
   - Ensures clean text for indexing

3. **Script Processor**
   - Sets `content_loaded = true`
   - Records `content_loaded_at` timestamp
   - Calculates `content_length` for processed text

### How the Pipeline Works

The pipeline is applied **server-side** during bulk indexing:

```python
# Client sends documents with raw HTML
bulk(
    es_client,
    actions,
    pipeline="wikipedia_ingest_pipeline",  # Applied server-side
    stats_only=True
)
```

**Key Benefits:**
- Processing happens on Elasticsearch nodes, not client
- Distributed computation across cluster
- Atomic transformations per document
- Reduced network traffic (no round trips)

### Usage Examples

#### Basic Enrichment
```python
from elasticsearch import Elasticsearch
from real_estate_search.indexer import WikipediaIndexer
from real_estate_search.indexer.wikipedia_indexer import WikipediaEnrichmentConfig

es = Elasticsearch(['localhost:9200'])
config = WikipediaEnrichmentConfig(
    batch_size=100,
    max_documents=1000,
    dry_run=False
)

indexer = WikipediaIndexer(es, config)
result = indexer.enrich_documents()

print(f"Enriched {result.documents_enriched} documents")
print(f"Failed: {result.documents_failed}")
print(f"Execution time: {result.execution_time_ms}ms")
```

#### Dry Run Mode
```python
config = WikipediaEnrichmentConfig(
    batch_size=50,
    max_documents=10,
    dry_run=True  # No actual updates
)

indexer = WikipediaIndexer(es, config)
result = indexer.enrich_documents()
```

#### Pipeline Management
```python
# Verify pipeline exists
if not indexer.verify_pipeline_exists():
    # Create from definition
    with open('pipelines/wikipedia_ingest.json') as f:
        pipeline_def = json.load(f)
    indexer.create_pipeline(pipeline_def)

# Get pipeline statistics
stats = indexer.get_pipeline_stats()
print(f"Documents processed: {stats.get('count', 0)}")
```

### Command Line Usage

The indexer is integrated with the management CLI:

```bash
# Enrich all documents needing content
python -m real_estate_search.management enrich-wikipedia

# Process specific number of documents
python -m real_estate_search.management enrich-wikipedia --max-documents 100

# Dry run to preview changes
python -m real_estate_search.management enrich-wikipedia --dry-run

# Custom batch size for performance tuning
python -m real_estate_search.management enrich-wikipedia --batch-size 200
```

### Index Mapping

The Wikipedia index uses the following mapping for enriched fields:

```json
{
  "full_content": {
    "type": "text",
    "analyzer": "english",
    "index_options": "offsets",
    "fields": {
      "exact": {
        "type": "text",
        "analyzer": "standard"
      }
    }
  },
  "content_loaded": {
    "type": "boolean"
  },
  "content_loaded_at": {
    "type": "date"
  },
  "content_length": {
    "type": "integer"
  }
}
```

### Performance Considerations

1. **Batch Size**: Optimal range 50-200 documents
   - Smaller batches: More network overhead
   - Larger batches: Memory pressure, timeout risk

2. **Scroll API**: Used for large result sets
   - Efficient cursor-based pagination
   - Prevents memory overflow for large queries

3. **Pipeline Processing**: Server-side execution
   - Distributed across Elasticsearch nodes
   - No client-side HTML processing overhead

4. **Error Handling**: Partial failure tolerance
   - Individual document failures don't stop batch
   - Failed documents tracked and reported

### Monitoring and Debugging

#### Check Pipeline Status
```bash
curl -X GET "localhost:9200/_ingest/pipeline/wikipedia_ingest_pipeline?pretty"
```

#### View Pipeline Statistics
```bash
curl -X GET "localhost:9200/_nodes/stats/ingest?pretty"
```

#### Query Enrichment Status
```bash
# Count documents needing enrichment
curl -X GET "localhost:9200/wikipedia/_count?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        {"exists": {"field": "article_filename"}},
        {"term": {"content_loaded": false}}
      ]
    }
  }
}'
```

#### View Enriched Document
```bash
curl -X GET "localhost:9200/wikipedia/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "term": {"content_loaded": true}
  },
  "_source": ["title", "content_length", "content_loaded_at"],
  "size": 1
}'
```

### Error Recovery

Common issues and solutions:

1. **Pipeline Not Found**
   ```python
   # Auto-create pipeline if missing
   if not indexer.verify_pipeline_exists():
       indexer.create_pipeline(pipeline_definition)
   ```

2. **File Not Found**
   - Check `result.files_not_found` list
   - Verify data directory path
   - Ensure article_filename paths are correct

3. **Bulk Indexing Failures**
   - Check `result.documents_failed` count
   - Review `result.errors` list for details
   - Common causes: mapping conflicts, field validation

4. **Memory Issues**
   - Reduce batch_size
   - Use max_documents to limit scope
   - Monitor Elasticsearch heap usage

### Future Enhancements

Potential improvements to the indexer:

1. **Content Extraction**
   - Add NLP processors for entity extraction
   - Generate automatic summaries
   - Extract key topics and categories

2. **Parallel Processing**
   - Multi-threaded file reading
   - Concurrent bulk operations
   - Async document processing

3. **Incremental Updates**
   - Track file modification times
   - Re-process only changed documents
   - Versioning support

4. **Advanced Pipelines**
   - Language detection
   - Sentiment analysis
   - Cross-reference linking

## Contributing

When adding new indexers:

1. Follow the `WikipediaIndexer` pattern
2. Include comprehensive docstrings
3. Implement error handling and logging
4. Add configuration classes with Pydantic
5. Create unit and integration tests
6. Document pipeline definitions
7. Update CLI commands as needed