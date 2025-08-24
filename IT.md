# Integration Testing Plan for ChromaDB Correlation

## Executive Summary

This document outlines a comprehensive integration testing strategy for validating the correlation functionality between source data and ChromaDB embeddings in the `common_ingest` module. The tests will use real test data from `common_embeddings/evaluate_data/bronze_articles.json` to ensure the system correctly enriches data with embeddings from existing ChromaDB collections.

## Testing Philosophy

**"Test the real thing, not mocks"**

- Use actual ChromaDB collections created by `common_embeddings`
- Test with real Wikipedia data that has known embeddings
- Verify the complete flow from API request to enriched response
- Keep tests simple, focused, and maintainable

## Test Data

### Bronze Articles Dataset
- **Location**: `common_embeddings/evaluate_data/bronze_articles.json`
- **Contents**: 3 Wikipedia articles with known page_ids
  - San Francisco Peninsula (page_id: 26974)
  - Wayne County, Utah (page_id: 71083)
  - Fillmore District, San Francisco (page_id: 1706289)
- **Why This Data**: Small, manageable dataset with diverse content types and locations

## Prerequisites

### 1. ChromaDB Collections Must Exist
```bash
# Ensure common_embeddings has created collections
cd common_embeddings
python main.py create --collection-name embeddings_nomic-embed-text
```

### 2. Collections Should Contain Test Data Embeddings
The ChromaDB collections must have embeddings for the bronze articles page_ids:
- Embeddings with metadata containing `page_id: 26974`
- Embeddings with metadata containing `page_id: 71083`
- Embeddings with metadata containing `page_id: 1706289`

## Test Scenarios

### Scenario 1: Basic Correlation Verification
**Goal**: Verify that correlation service correctly matches embeddings to source data

```python
def test_basic_correlation():
    """Test that correlation finds embeddings for known Wikipedia articles."""
    
    # Load bronze articles
    with open('common_embeddings/evaluate_data/bronze_articles.json', 'r') as f:
        test_data = json.load(f)
    
    # Initialize services
    embedding_service = EmbeddingService(chromadb_path='./data/chroma_db')
    correlation_service = CorrelationService(embedding_service)
    
    # Test correlation for each article
    for article in test_data['articles']:
        # Create simple dict with page_id for correlation
        wiki_data = [{
            'page_id': article['page_id'],
            'title': article['title'],
            'summary': article['summary']
        }]
        
        # Correlate with embeddings
        results = correlation_service.correlate_wikipedia_with_embeddings(
            wikipedia_data=wiki_data,
            collection_name='embeddings_nomic-embed-text',
            include_vectors=False
        )
        
        # Assertions
        assert len(results) == 1
        assert results[0]['has_embeddings'] == True
        assert results[0]['embedding_count'] > 0
        print(f"✓ Article '{article['title']}' has {results[0]['embedding_count']} embeddings")
```

### Scenario 2: API Endpoint Integration
**Goal**: Test the complete flow through API endpoints

```python
@pytest.mark.asyncio
async def test_api_endpoint_correlation():
    """Test correlation through actual API endpoints."""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test Wikipedia articles endpoint with embeddings
        response = await client.get(
            "/api/v1/wikipedia/articles",
            params={
                "include_embeddings": True,
                "collection_name": "embeddings_nomic-embed-text",
                "page": 1,
                "page_size": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that articles have embedding fields
        for article in data['data']:
            if article['page_id'] in [26974, 71083, 1706289]:
                assert 'embeddings' in article
                assert 'has_embeddings' in article
                assert article['has_embeddings'] == True
                assert article['embedding_count'] > 0
                print(f"✓ API returned embeddings for article {article['page_id']}")
```

### Scenario 3: Multi-Chunk Document Handling
**Goal**: Verify that multi-chunk Wikipedia articles are handled correctly

```python
def test_multi_chunk_correlation():
    """Test that multi-chunk documents are properly correlated."""
    
    # Use a known long article that would be chunked
    wiki_data = [{
        'page_id': 26974,  # San Francisco Peninsula - likely multi-chunk
        'title': 'San Francisco Peninsula',
        'full_text': '...' # Long text that was chunked
    }]
    
    results = correlation_service.correlate_wikipedia_with_embeddings(
        wikipedia_data=wiki_data,
        collection_name='embeddings_nomic-embed-text',
        include_vectors=False
    )
    
    assert len(results) == 1
    result = results[0]
    
    # Check for multiple chunks
    if result['embedding_count'] > 1:
        # Verify chunks are ordered by chunk_index
        chunks = result['embeddings']
        chunk_indices = [e['chunk_index'] for e in chunks if e.get('chunk_index') is not None]
        assert chunk_indices == sorted(chunk_indices)
        print(f"✓ Multi-chunk document has {len(chunks)} ordered chunks")
```

### Scenario 4: Performance Validation
**Goal**: Ensure correlation completes within acceptable time limits

```python
def test_correlation_performance():
    """Test that correlation performs within acceptable limits."""
    
    import time
    
    # Load all bronze articles
    with open('common_embeddings/evaluate_data/bronze_articles.json', 'r') as f:
        test_data = json.load(f)
    
    wiki_data = [
        {'page_id': a['page_id'], 'title': a['title']} 
        for a in test_data['articles']
    ]
    
    # Measure correlation time
    start_time = time.time()
    
    results = correlation_service.correlate_wikipedia_with_embeddings(
        wikipedia_data=wiki_data,
        collection_name='embeddings_nomic-embed-text',
        include_vectors=False  # Exclude vectors for performance
    )
    
    elapsed_time = time.time() - start_time
    
    # Performance assertions
    assert elapsed_time < 2.0  # Should complete in under 2 seconds
    assert len(results) == len(wiki_data)
    
    successful = sum(1 for r in results if r['has_embeddings'])
    print(f"✓ Correlated {successful}/{len(wiki_data)} articles in {elapsed_time:.2f} seconds")
```

### Scenario 5: Missing Embeddings Handling
**Goal**: Verify graceful handling when embeddings don't exist

```python
def test_missing_embeddings():
    """Test that system handles missing embeddings gracefully."""
    
    # Use a page_id that doesn't exist in ChromaDB
    wiki_data = [{
        'page_id': 99999999,  # Non-existent
        'title': 'Non-existent Article',
        'summary': 'This article has no embeddings'
    }]
    
    results = correlation_service.correlate_wikipedia_with_embeddings(
        wikipedia_data=wiki_data,
        collection_name='embeddings_nomic-embed-text',
        include_vectors=False
    )
    
    assert len(results) == 1
    result = results[0]
    
    # Should handle gracefully
    assert result['has_embeddings'] == False
    assert result['embedding_count'] == 0
    assert result['correlation_confidence'] == 0.0
    assert result['embeddings'] is None or result['embeddings'] == []
    
    print("✓ Missing embeddings handled gracefully")
```

## Test Execution Plan

### 1. Setup Phase
```bash
# Ensure ChromaDB collections exist
cd common_embeddings
python main.py create --collection-name embeddings_nomic-embed-text

# Verify bronze articles are embedded
python evaluate.py --dataset bronze --collection embeddings_nomic-embed-text
```

### 2. Run Integration Tests
```bash
# Run all integration tests
cd common_ingest
pytest integration_tests/test_correlation_bronze.py -v

# Run with coverage
pytest integration_tests/test_correlation_bronze.py --cov=services --cov-report=html
```

### 3. Manual Verification
```bash
# Start the API server
uvicorn common_ingest.api.app:app --reload

# Test with curl
curl "http://localhost:8000/api/v1/wikipedia/articles?include_embeddings=true&collection_name=embeddings_nomic-embed-text&page_size=3"
```

## Expected Outcomes

### Success Criteria
- ✅ All bronze articles successfully correlate with their embeddings
- ✅ API endpoints return enriched data with embeddings when requested
- ✅ Multi-chunk documents are properly reconstructed
- ✅ Performance is under 2 seconds for small datasets
- ✅ Missing embeddings are handled gracefully

### Sample Expected Response
```json
{
  "data": [{
    "page_id": 26974,
    "title": "San Francisco Peninsula",
    "summary": "...",
    "embeddings": [
      {
        "embedding_id": "emb_26974_0",
        "metadata": {"page_id": 26974, "chunk_index": 0},
        "chunk_index": 0
      }
    ],
    "embedding_count": 1,
    "has_embeddings": true,
    "correlation_confidence": 1.0
  }],
  "metadata": {
    "total_count": 3,
    "page": 1,
    "page_size": 10
  }
}
```

## Implementation File Structure

```
common_ingest/
├── integration_tests/
│   ├── test_correlation_bronze.py   # Main integration test file
│   ├── fixtures/
│   │   └── test_data.py            # Test data fixtures
│   └── conftest.py                 # Pytest configuration
```

## Key Implementation Details

### test_correlation_bronze.py
```python
"""
Integration tests for correlation using bronze articles dataset.

Tests the complete flow of correlating source data with ChromaDB embeddings
using real test data from common_embeddings/evaluate_data/bronze_articles.json.
"""

import json
import pytest
from pathlib import Path
from httpx import AsyncClient

from common_ingest.services.embedding_service import EmbeddingService
from common_ingest.services.correlation_service import CorrelationService
from common_ingest.api.app import app


class TestBronzeCorrelation:
    """Test correlation with bronze articles dataset."""
    
    @classmethod
    def setup_class(cls):
        """Load test data once for all tests."""
        bronze_path = Path("../common_embeddings/evaluate_data/bronze_articles.json")
        with open(bronze_path, 'r') as f:
            cls.test_data = json.load(f)
        
        # Initialize services
        cls.embedding_service = EmbeddingService(chromadb_path='./data/chroma_db')
        cls.correlation_service = CorrelationService(cls.embedding_service)
    
    def test_all_bronze_articles_correlate(self):
        """Test that all bronze articles correlate with embeddings."""
        # Implementation here
        pass
    
    @pytest.mark.asyncio
    async def test_api_endpoint_with_bronze_data(self):
        """Test API endpoint returns enriched bronze articles."""
        # Implementation here
        pass
```

## Benefits of This Approach

1. **Real Data Testing**: Uses actual Wikipedia articles with known content
2. **End-to-End Validation**: Tests the complete flow from API to ChromaDB
3. **Simple and Focused**: Small dataset makes tests fast and maintainable
4. **Demo Quality**: Shows the system working with real, meaningful data
5. **No Mocks**: Tests against actual ChromaDB collections

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| ChromaDB collections don't exist | Setup script ensures collections are created |
| Test data not embedded | Verify embeddings exist before running tests |
| Performance issues with large embeddings | Exclude vectors from correlation for tests |
| Test data changes | Use versioned bronze_articles.json file |

## Conclusion

This integration testing plan provides a comprehensive approach to validating the correlation functionality using real test data. By using the bronze articles dataset and actual ChromaDB collections, we ensure that our tests reflect real-world usage while remaining simple and maintainable for demo purposes.

The tests focus on:
- **Correctness**: Embeddings are properly correlated with source data
- **Completeness**: All expected embeddings are found and returned
- **Performance**: Correlation completes within acceptable time limits
- **Robustness**: System handles edge cases gracefully

This approach ensures high confidence that the correlation functionality works correctly in a real-world scenario.