#!/usr/bin/env python3
"""
Enhance all demo markdown documentation with detailed explanations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

def get_query_type_details(query_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate detailed explanations based on query type.
    """
    query = query_data.get("query", {})
    details = {
        "execution_flow": "",
        "algorithm_explanation": "",
        "performance_notes": "",
        "real_world_example": ""
    }
    
    # Check for different query types
    if "retriever" in query and "rrf" in query.get("retriever", {}):
        # Hybrid search with RRF
        details["execution_flow"] = """
## Complete Query Execution Flow

### Phase 1: Query Preparation (0-5ms)
1. **Parse query structure**: Extract retrievers and parameters
2. **Generate embeddings**: Convert text to vector representation
3. **Prepare filters**: Parse any filter conditions
4. **Plan execution**: Determine parallel execution strategy

### Phase 2: Parallel Retrieval (5-30ms)

Both retrievers execute simultaneously:

#### Standard Retriever Thread:
- Parse text into tokens
- Search inverted index for each token
- Apply filters (if any)
- Calculate BM25 scores
- Sort by relevance
- Return top N results

#### KNN Retriever Thread:
- Load query vector
- Navigate HNSW graph layers
- Apply filters to candidates
- Calculate cosine similarities
- Sort by similarity
- Return top K results

### Phase 3: Fusion (30-35ms)
- Collect results from both retrievers
- Calculate reciprocal rank scores
- Combine scores using RRF formula
- Sort by combined score

### Phase 4: Final Retrieval (35-40ms)
- Fetch top documents
- Apply source filtering
- Format response"""

        details["algorithm_explanation"] = """
## Reciprocal Rank Fusion (RRF) Algorithm

### The RRF Formula
```
RRF_score(d) = Σ(1 / (k + rank_i(d)))
```
Where:
- d = document
- k = rank constant (typically 60)
- rank_i(d) = rank of document d in retriever i

### Why RRF Works
1. **Normalizes different scoring scales**: BM25 vs cosine similarity
2. **Reduces outlier impact**: Top results matter most
3. **Balances contributions**: Each retriever has equal weight
4. **Handles missing results**: Documents not found get rank = ∞

### Example Calculation
Document appears at:
- Rank 3 in text search
- Rank 1 in vector search

RRF Score = 1/(60+3) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323"""

    elif "knn" in query.get("query", {}):
        # Pure vector search
        details["execution_flow"] = """
## Vector Search Execution Flow

### Phase 1: Query Vectorization (0-2ms)
1. **Text preprocessing**: Tokenize input text
2. **Embedding generation**: Convert to vector using AI model
3. **Normalization**: Ensure unit vector for cosine similarity

### Phase 2: HNSW Graph Navigation (2-15ms)
1. **Start at entry point**: Top level of hierarchical graph
2. **Greedy search**: Move to nearest neighbors
3. **Layer descent**: Move to more detailed layers
4. **Candidate collection**: Gather potential matches

### Phase 3: Similarity Calculation (15-20ms)
1. **Cosine similarity**: Calculate for each candidate
2. **Apply filters**: Remove non-matching documents
3. **Sort by similarity**: Order from most to least similar

### Phase 4: Result Retrieval (20-25ms)
1. **Fetch documents**: Load top K results
2. **Apply source filtering**: Return requested fields
3. **Format response**: Structure for client"""

        details["algorithm_explanation"] = """
## HNSW (Hierarchical Navigable Small World) Algorithm

### Graph Structure
```
Level 2:    A ←────→ B         (Highway layer)
            ↓        ↓
Level 1:    A──C──D──B──E      (Regional layer)
            ↓  ↓  ↓  ↓  ↓
Level 0:    A-C-G-D-B-H-E-F    (Local layer)
```

### Search Process
1. **Entry**: Start at top layer entry point
2. **Greedy routing**: Move to nearest neighbor
3. **Layer transition**: When can't get closer, go down
4. **Local search**: Find exact nearest neighbors at bottom

### Cosine Similarity
```
similarity = (A · B) / (||A|| × ||B||)
```
- Result range: [-1, 1] (typically [0, 1] for text)
- 1.0 = identical vectors
- 0.0 = orthogonal (unrelated)"""

    elif "bool" in query.get("query", {}):
        bool_query = query["query"]["bool"]
        if "filter" in bool_query:
            # Filter-based search
            details["execution_flow"] = """
## Filter Query Execution Flow

### Phase 1: Query Analysis (0-1ms)
1. **Parse filters**: Extract all filter conditions
2. **Optimize order**: Arrange by selectivity
3. **Prepare bitsets**: Initialize for intersection

### Phase 2: Filter Execution (1-5ms)
1. **Most selective first**: Apply filter that eliminates most docs
2. **Bitset operations**: AND/OR/NOT operations on document sets
3. **Range checks**: Efficient numeric comparisons
4. **Cache lookup**: Check if filter results are cached

### Phase 3: Document Collection (5-8ms)
1. **Gather matching IDs**: From bitset intersection
2. **Apply sorting**: If specified (e.g., by price)
3. **Pagination**: Skip/limit for result window

### Phase 4: Result Retrieval (8-10ms)
1. **Fetch documents**: Load from document store
2. **Source filtering**: Return only requested fields
3. **Format response**: Structure for client"""

            details["algorithm_explanation"] = """
## Filter Context Optimization

### Bitset Operations
Filters create bitsets where each bit represents a document:
```
property_type filter: [1,0,1,1,0,0,1,1,1,0,...]
price_range filter:   [1,1,0,1,0,1,0,1,1,0,...]
AND operation:        [1,0,0,1,0,0,0,1,1,0,...]
```

### Filter Caching
- Frequently used filters are cached
- Cache key: Hash of filter parameters
- Cache invalidation: On index updates
- Result: Subsequent searches are near-instant

### Execution Order Optimization
1. **Term filters**: O(1) hash lookups
2. **Range filters**: O(log n) tree traversal
3. **Complex filters**: More expensive operations last"""

        elif "must" in bool_query or "should" in bool_query:
            # Scoring query
            details["execution_flow"] = """
## Scoring Query Execution Flow

### Phase 1: Query Analysis (0-2ms)
1. **Parse clauses**: Extract must/should/must_not
2. **Analyze terms**: Process through analyzers
3. **Prepare scorers**: Initialize BM25 scorers

### Phase 2: Index Lookup (2-10ms)
1. **Term lookups**: Find documents containing terms
2. **Position data**: Load for phrase matching
3. **Frequency data**: For TF-IDF calculation

### Phase 3: Scoring (10-15ms)
1. **Calculate BM25**: For each matching document
2. **Apply boosts**: Field and query boosts
3. **Combine scores**: Sum for multiple terms

### Phase 4: Ranking (15-20ms)
1. **Sort by score**: Highest relevance first
2. **Apply filters**: Post-scoring filtering
3. **Return top N**: Based on size parameter"""

            details["algorithm_explanation"] = """
## BM25 Scoring Algorithm

### The BM25 Formula
```
score = Σ(IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl)))
```
Where:
- IDF(qi) = Inverse document frequency of query term i
- f(qi, D) = Frequency of term i in document D
- |D| = Length of document D
- avgdl = Average document length
- k1, b = Tuning parameters (typically 1.2, 0.75)

### Key Concepts
1. **Term Frequency (TF)**: More occurrences = higher score
2. **Document Frequency (DF)**: Rare terms = higher score
3. **Document Length**: Normalizes for document size
4. **Saturation**: Diminishing returns for repeated terms"""

    elif "multi_match" in query.get("query", {}):
        # Multi-match query
        details["execution_flow"] = """
## Multi-Match Query Execution Flow

### Phase 1: Query Preparation (0-2ms)
1. **Parse search text**: Extract search terms
2. **Apply analyzers**: Tokenize, lowercase, stem
3. **Identify fields**: List fields to search
4. **Apply boosts**: Set field importance weights

### Phase 2: Field Search (2-10ms)
For each field:
1. **Token lookup**: Find documents with tokens
2. **Calculate field score**: BM25 per field
3. **Apply field boost**: Multiply by boost factor
4. **Handle fuzziness**: If configured

### Phase 3: Score Combination (10-12ms)
Based on type (best_fields, most_fields, etc.):
1. **Best fields**: Take maximum field score
2. **Most fields**: Sum all field scores
3. **Cross fields**: Treat fields as one big field

### Phase 4: Result Ranking (12-15ms)
1. **Sort by final score**: Highest first
2. **Apply highlighting**: Mark matched terms
3. **Return top results**: Based on size"""

        details["algorithm_explanation"] = """
## Multi-Match Scoring Strategies

### Best Fields (Default)
- Takes the highest scoring field for each document
- Good for: Finding best single field match
- Example: Title OR Description match

### Most Fields
- Sums scores from all matching fields
- Good for: Documents matching multiple fields
- Example: Comprehensive matches

### Cross Fields
- Treats multiple fields as one big field
- Good for: Names, addresses split across fields
- Example: First name + Last name

### Field Boosting
```
"fields": [
  "title^3",      // 3x weight
  "description^2", // 2x weight
  "tags"          // 1x weight (default)
]
```"""

    elif "geo_distance" in str(query):
        # Geo query
        details["execution_flow"] = """
## Geo-Distance Query Execution Flow

### Phase 1: Query Preparation (0-2ms)
1. **Parse coordinates**: Extract lat/lon
2. **Calculate bounding box**: Quick elimination rectangle
3. **Prepare distance calculator**: Haversine formula

### Phase 2: Spatial Filtering (2-8ms)
1. **Geohash prefix matching**: Quick candidates
2. **Bounding box check**: Eliminate distant points
3. **Precise distance calculation**: For remaining

### Phase 3: Distance Sorting (8-10ms)
1. **Calculate distances**: For all matches
2. **Sort by distance**: Nearest first
3. **Apply any filters**: Additional constraints

### Phase 4: Result Retrieval (10-12ms)
1. **Fetch documents**: Load property data
2. **Include distance**: In result metadata
3. **Format response**: With location data"""

        details["algorithm_explanation"] = """
## Geospatial Search Algorithms

### Haversine Formula
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1−a))
distance = R × c (R = Earth's radius)
```

### Geohash Optimization
- Hierarchical spatial indexing
- Each character adds precision
- Example: "9q8yy" covers ~0.6km²
- Prefix matching for area search

### Bounding Box Pre-filter
```
Given: center (lat, lon), radius r
North: lat + (r/111km)
South: lat - (r/111km)
East: lon + (r/(111km × cos(lat)))
West: lon - (r/(111km × cos(lat)))
```"""

    elif "aggs" in query or "aggregations" in query:
        # Aggregation query
        details["execution_flow"] = """
## Aggregation Execution Flow

### Phase 1: Query Execution (0-5ms)
1. **Run main query**: Find matching documents
2. **Collect doc IDs**: For aggregation scope
3. **Prepare collectors**: Initialize aggregation structures

### Phase 2: Data Collection (5-15ms)
1. **Scan documents**: Read values from doc values
2. **Update buckets**: Increment counters/sums
3. **Calculate metrics**: Running statistics

### Phase 3: Post-Processing (15-18ms)
1. **Sort buckets**: By count or key
2. **Apply pipeline aggs**: Derivatives, moving averages
3. **Prune results**: Top N buckets

### Phase 4: Response Building (18-20ms)
1. **Format buckets**: Convert to response structure
2. **Include doc counts**: Per bucket
3. **Add statistics**: Min/max/avg/sum"""

        details["algorithm_explanation"] = """
## Aggregation Algorithms

### Terms Aggregation
- Creates buckets for unique values
- Uses global ordinals for efficiency
- Memory: O(unique_values)
- Time: O(n) where n = matching docs

### Histogram Aggregation
```
bucket_key = floor(value / interval) * interval
```
- Fixed-size buckets
- Efficient for numeric ranges
- Useful for distributions

### Statistics Calculation
- Single pass algorithms
- Welford's method for variance
- T-Digest for percentiles
- HyperLogLog for cardinality"""

    else:
        # Default simple query
        details["execution_flow"] = """
## Query Execution Flow

### Phase 1: Query Parsing (0-2ms)
1. Parse query structure
2. Apply text analysis
3. Prepare execution plan

### Phase 2: Index Search (2-10ms)
1. Search inverted index
2. Collect matching documents
3. Calculate relevance scores

### Phase 3: Ranking (10-12ms)
1. Sort by relevance
2. Apply any filters
3. Limit to requested size

### Phase 4: Response (12-15ms)
1. Fetch documents
2. Apply source filtering
3. Return results"""

    # Add performance notes
    details["performance_notes"] = """
## Performance Optimization

### Caching Strategies
- **Query cache**: Caches entire query results
- **Filter cache**: Caches filter bitsets
- **Field data cache**: Caches field values for sorting/aggregations

### Index Optimizations
- **Inverted index**: O(1) term lookups
- **Doc values**: Columnar storage for aggregations
- **BKD trees**: Efficient range queries
- **Skip lists**: Fast intersection operations

### Scaling Considerations
- **Sharding**: Distribute data across nodes
- **Replicas**: Parallel query execution
- **Routing**: Direct queries to relevant shards
- **Circuit breakers**: Prevent OOM errors"""

    # Add real-world example
    details["real_world_example"] = """
## Real-World Application

### Use Case Example
Consider a user searching for properties:
1. **Initial search**: Broad criteria
2. **Refinement**: Add filters based on results
3. **Comparison**: Side-by-side property analysis
4. **Saved searches**: Alert on new matches

### Query Evolution
```
Stage 1: "modern apartment"
         ↓ (user sees results)
Stage 2: "modern apartment" + price filter
         ↓ (user refines)
Stage 3: "modern apartment" + price + location
         ↓ (user compares)
Stage 4: Save query for alerts
```

### Performance Requirements
- **Search latency**: < 100ms for user satisfaction
- **Throughput**: Handle concurrent users
- **Accuracy**: Relevant results first
- **Scalability**: Growing data volume"""

    return details


def enhance_markdown_file(md_file: Path, json_file: Path) -> str:
    """
    Enhance a markdown file with detailed explanations.
    """
    # Read existing markdown
    with open(md_file, 'r') as f:
        content = f.read()
    
    # Read corresponding JSON
    with open(json_file, 'r') as f:
        query_data = json.load(f)
    
    # Get detailed explanations based on query type
    details = get_query_type_details(query_data)
    
    # Find where to insert the new content (after existing content)
    # Look for where we can add our enhancements
    if "## Performance Notes" in content:
        # Already has some structure, enhance it
        insertion_point = content.find("## Performance Notes")
        before = content[:insertion_point]
        
        # Build enhanced content
        enhanced = before
        enhanced += details["execution_flow"] + "\n\n"
        enhanced += details["algorithm_explanation"] + "\n\n"
        enhanced += details["performance_notes"] + "\n\n"
        enhanced += details["real_world_example"] + "\n"
        
    else:
        # Add new sections at the end
        enhanced = content.rstrip() + "\n\n"
        enhanced += details["execution_flow"] + "\n\n"
        enhanced += details["algorithm_explanation"] + "\n\n"
        enhanced += details["performance_notes"] + "\n\n"
        enhanced += details["real_world_example"] + "\n"
    
    return enhanced


def main():
    """
    Enhance all markdown documentation files.
    """
    json_dir = Path("demo_queries_json")
    
    # Get all markdown files (except README and already enhanced ones)
    md_files = sorted(json_dir.glob("demo_*_query_*.md"))
    
    # Skip the ones we've already manually enhanced
    skip_demos = [1, 2, 3, 19]  # These have detailed manual enhancements
    
    enhanced_count = 0
    
    for md_file in md_files:
        # Extract demo number
        demo_num = int(md_file.stem.split('_')[1])
        
        if demo_num in skip_demos:
            print(f"Skipping demo {demo_num} (already enhanced)")
            continue
        
        # Find corresponding JSON file
        json_file = md_file.with_suffix('.json')
        
        if not json_file.exists():
            print(f"No JSON file for {md_file.name}")
            continue
        
        print(f"Enhancing {md_file.name}...")
        
        try:
            # Enhance the markdown
            enhanced_content = enhance_markdown_file(md_file, json_file)
            
            # Write back
            with open(md_file, 'w') as f:
                f.write(enhanced_content)
            
            enhanced_count += 1
            print(f"  ✓ Enhanced {md_file.name}")
            
        except Exception as e:
            print(f"  ✗ Error enhancing {md_file.name}: {e}")
    
    print(f"\nEnhanced {enhanced_count} documentation files!")
    
    # Create a detailed guide for vector search
    create_vector_search_guide()
    
    # Create a detailed guide for RRF
    create_rrf_guide()
    
    print("Created additional detailed guides!")


def create_vector_search_guide():
    """
    Create a comprehensive guide for vector search.
    """
    guide = """# Complete Guide to Vector Search in Elasticsearch

## Introduction to Vector Search

Vector search, also known as semantic search or similarity search, uses machine learning to understand the meaning and context of search queries rather than just matching keywords.

## How Embeddings Work

### The Embedding Process

1. **Text Input Processing**
   ```
   "luxury waterfront property" 
   → Tokenization → ["luxury", "waterfront", "property"]
   → Subword tokens → ["lux", "##ury", "water", "##front", "property"]
   ```

2. **Neural Network Transformation**
   ```
   Tokens → Embedding Layer → Transformer Layers → Output Vector
           (learned representations) (context) (final embedding)
   ```

3. **Dimensional Representation**
   - Each dimension captures different semantic aspects
   - Typical sizes: 384, 768, 1024, 1536 dimensions
   - Higher dimensions = more nuanced understanding

### Understanding Vector Space

Imagine a 3D space (simplified from 1024D):

```
              Luxury Axis
                   ↑
                   │
    Suburban ──────┼────── Urban
                   │
                   ↓
              Affordable

Your query "luxury waterfront" maps to coordinates like:
[0.8, 0.3, 0.9] = [high luxury, slightly urban, very waterfront]
```

## The HNSW Algorithm Deep Dive

### Graph Construction

HNSW builds a multi-layer graph during indexing:

```python
def build_hnsw(vectors, M=16, ef_construction=200):
    layers = []
    for vector in vectors:
        # Assign layer with exponential decay probability
        layer = floor(-log(random()) * ml)
        
        # Insert at each layer from 0 to assigned layer
        for lc in range(layer + 1):
            # Find M nearest neighbors at this layer
            neighbors = find_nearest(vector, layers[lc], M)
            # Connect bidirectionally
            connect(vector, neighbors)
```

### Search Algorithm

```python
def search_hnsw(query, ef=100, k=10):
    # Start at top layer
    entry_points = get_layer_entry_points(top_layer)
    
    # Search from top to bottom
    for layer in reversed(range(num_layers)):
        # Greedy search at this layer
        candidates = greedy_search(query, entry_points, ef)
        # Best candidates become entry points for next layer
        entry_points = get_closest(candidates, 1)
    
    # Final layer: careful search
    final_candidates = greedy_search(query, entry_points, ef)
    return get_closest(final_candidates, k)
```

### Performance Characteristics

- **Build time**: O(N * log(N)) where N = number of vectors
- **Search time**: O(log(N))
- **Memory**: O(N * M) where M = connections per node
- **Accuracy**: 95-99% recall with proper parameters

## Similarity Metrics

### Cosine Similarity (Most Common)

```python
def cosine_similarity(a, b):
    dot_product = sum(a[i] * b[i] for i in range(len(a)))
    norm_a = sqrt(sum(a[i]**2 for i in range(len(a))))
    norm_b = sqrt(sum(b[i]**2 for i in range(len(b))))
    return dot_product / (norm_a * norm_b)
```

**Interpretation:**
- 1.0 = Identical meaning
- 0.8-0.9 = Very similar
- 0.6-0.8 = Related
- 0.4-0.6 = Somewhat related
- < 0.4 = Different concepts

### Euclidean Distance

```python
def euclidean_distance(a, b):
    return sqrt(sum((a[i] - b[i])**2 for i in range(len(a))))
```

**When to use:**
- When magnitude matters
- For clustering applications
- When vectors aren't normalized

### Dot Product

```python
def dot_product(a, b):
    return sum(a[i] * b[i] for i in range(len(a)))
```

**When to use:**
- Maximum speed required
- Vectors are pre-normalized
- Ranking more important than absolute scores

## Embedding Models

### Popular Models and Their Characteristics

1. **OpenAI text-embedding-3**
   - Dimensions: 1536 (small) or 3072 (large)
   - Excellent general-purpose performance
   - Cost: ~$0.00002 per 1K tokens

2. **Voyage AI voyage-3**
   - Dimensions: 1024
   - Optimized for search
   - Better domain-specific performance

3. **Cohere embed-v3**
   - Dimensions: 1024
   - Multilingual support
   - Good for diverse content

4. **Open Source (Sentence Transformers)**
   - all-MiniLM-L6-v2: 384 dimensions, fast
   - all-mpnet-base-v2: 768 dimensions, accurate
   - Free to run, requires infrastructure

### Choosing an Embedding Model

Consider:
- **Latency requirements**: Smaller models are faster
- **Accuracy needs**: Larger models are more accurate
- **Language support**: Some models are multilingual
- **Cost**: API vs self-hosted
- **Domain specificity**: Fine-tuned vs general

## Indexing Strategies

### Dense Vector Indexing

```json
{
  "mappings": {
    "properties": {
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine",
        "index_options": {
          "type": "hnsw",
          "m": 16,
          "ef_construction": 100
        }
      }
    }
  }
}
```

### Hybrid Indexing (Text + Vector)

```json
{
  "mappings": {
    "properties": {
      "title": {"type": "text"},
      "description": {"type": "text"},
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

## Query Strategies

### Pure Vector Search

```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],
    "k": 10,
    "num_candidates": 100
  }
}
```

### Filtered Vector Search

```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],
    "k": 10,
    "num_candidates": 100,
    "filter": {
      "term": {"category": "luxury"}
    }
  }
}
```

### Hybrid Search with RRF

```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {"match": {"title": "waterfront"}}
          }
        },
        {
          "knn": {
            "field": "embedding",
            "query_vector": [0.1, 0.2, ...],
            "k": 50
          }
        }
      ]
    }
  }
}
```

## Performance Optimization

### Indexing Optimization

1. **Batch Processing**
   ```python
   # Good: Batch embeddings
   embeddings = model.encode(texts, batch_size=100)
   
   # Bad: One at a time
   for text in texts:
       embedding = model.encode([text])
   ```

2. **Parallel Indexing**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(index_batch, batch) 
                  for batch in batches]
   ```

3. **Index Settings**
   ```json
   {
     "settings": {
       "index": {
         "number_of_shards": 2,
         "number_of_replicas": 0,  // During indexing
         "refresh_interval": "-1"   // Disable refresh
       }
     }
   }
   ```

### Search Optimization

1. **Parameter Tuning**
   - `num_candidates`: Higher = more accurate but slower
   - `k`: Number of results needed
   - Rule of thumb: `num_candidates = 10 * k`

2. **Caching**
   - Cache frequently used embeddings
   - Use query cache for repeated searches
   - Implement application-level caching

3. **Approximate vs Exact**
   - HNSW: Fast approximate search
   - Script score: Exact but slow
   - Choose based on requirements

## Common Pitfalls and Solutions

### Pitfall 1: Inconsistent Embeddings
**Problem**: Using different models for indexing and searching
**Solution**: Always use the same model and version

### Pitfall 2: Not Normalizing Vectors
**Problem**: Cosine similarity assumes normalized vectors
**Solution**: 
```python
def normalize(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector
```

### Pitfall 3: Poor Recall
**Problem**: Missing relevant results
**Solution**: Increase `num_candidates` and `ef_search`

### Pitfall 4: Slow Indexing
**Problem**: Taking too long to index documents
**Solution**: Use batch processing and disable refresh

### Pitfall 5: Memory Issues
**Problem**: Running out of memory with large indices
**Solution**: Reduce HNSW `m` parameter or use fewer dimensions

## Monitoring and Debugging

### Key Metrics to Track

1. **Search Latency**
   - P50, P95, P99 percentiles
   - Target: < 100ms for P95

2. **Recall**
   - Compare with exact search periodically
   - Target: > 95% recall

3. **Index Size**
   - Monitor growth rate
   - Plan capacity accordingly

4. **Cache Hit Rate**
   - Query cache effectiveness
   - Target: > 80% for common queries

### Debugging Techniques

1. **Explain API**
   ```json
   {
     "explain": true,
     "knn": {
       "field": "embedding",
       "query_vector": [...],
       "k": 1
     }
   }
   ```

2. **Profile API**
   ```json
   {
     "profile": true,
     "knn": {...}
   }
   ```

3. **Validate Embeddings**
   ```python
   # Check embedding quality
   def validate_embedding(text, embedding):
       assert len(embedding) == expected_dims
       assert -1 <= min(embedding) <= 1
       assert -1 <= max(embedding) <= 1
       assert abs(np.linalg.norm(embedding) - 1.0) < 0.01
   ```

## Advanced Techniques

### Fine-Tuning Embeddings

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# Load base model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Prepare training data
train_examples = [
    InputExample(texts=['luxury property', 'high-end real estate'], label=0.9),
    InputExample(texts=['affordable housing', 'luxury property'], label=0.2),
]

# Fine-tune
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=10)
```

### Multi-Vector Representations

```json
{
  "properties": {
    "title_embedding": {"type": "dense_vector", "dims": 768},
    "description_embedding": {"type": "dense_vector", "dims": 768},
    "image_embedding": {"type": "dense_vector", "dims": 512}
  }
}
```

### Hierarchical Search

```python
def hierarchical_search(query, coarse_index, fine_index):
    # Stage 1: Coarse search (small embeddings)
    coarse_results = search(query, coarse_index, k=100)
    
    # Stage 2: Re-rank with fine embeddings
    fine_results = rerank(query, coarse_results, fine_index, k=10)
    
    return fine_results
```

## Conclusion

Vector search is powerful but requires careful consideration of:
- Model selection
- Index configuration
- Query strategy
- Performance optimization
- Monitoring and maintenance

The key to success is understanding the trade-offs and choosing the right approach for your specific use case.
"""
    
    with open("demo_queries_json/VECTOR_SEARCH_GUIDE.md", "w") as f:
        f.write(guide)


def create_rrf_guide():
    """
    Create a comprehensive guide for RRF.
    """
    guide = """# Complete Guide to Reciprocal Rank Fusion (RRF)

## What is RRF?

Reciprocal Rank Fusion is a method for combining results from multiple search systems or ranking algorithms. It was designed to merge rankings without requiring score calibration between different systems.

## The Mathematics of RRF

### Basic Formula

```
RRF(d) = Σᵢ 1/(k + rankᵢ(d))
```

Where:
- `d` is a document
- `i` iterates over different ranking systems
- `rankᵢ(d)` is the rank of document d in system i
- `k` is a constant (typically 60)

### Extended Formula for Weighted RRF

```
RRF(d) = Σᵢ wᵢ/(k + rankᵢ(d))
```

Where `wᵢ` is the weight for ranking system i.

## Why RRF Works

### Problem: Score Incompatibility

Different search systems produce incompatible scores:

```
BM25 Score Range: [0, 15+]
Cosine Similarity: [0, 1]
PageRank: [0, 10]

Simple addition would be dominated by BM25!
```

### Solution: Rank-Based Fusion

RRF converts scores to ranks, making them comparable:

```
System A Scores: [15.2, 12.1, 8.7, 5.3, 2.1]
System A Ranks:  [1,    2,    3,   4,   5]

System B Scores: [0.95, 0.87, 0.76, 0.65, 0.54]
System B Ranks:  [1,    2,    3,    4,    5]

Now comparable!
```

## Step-by-Step RRF Calculation

### Example Scenario

Query: "modern waterfront property"

**Text Search Results:**
1. "Waterfront villa with modern amenities" (BM25: 12.5)
2. "Modern beachfront property" (BM25: 11.2)
3. "Contemporary waterside home" (BM25: 9.8)
4. "Luxury property near water" (BM25: 8.3)
5. "Modern urban apartment" (BM25: 7.1)

**Vector Search Results:**
1. "Contemporary waterside home" (Similarity: 0.92)
2. "Oceanview modern residence" (Similarity: 0.89)
3. "Waterfront villa with modern amenities" (Similarity: 0.86)
4. "Sleek coastal property" (Similarity: 0.83)
5. "Modern beachfront property" (Similarity: 0.81)

### Calculation with k=60

**Document: "Contemporary waterside home"**
- Text Search Rank: 3
- Vector Search Rank: 1
- RRF Score = 1/(60+3) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323

**Document: "Waterfront villa with modern amenities"**
- Text Search Rank: 1
- Vector Search Rank: 3
- RRF Score = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323

**Document: "Modern beachfront property"**
- Text Search Rank: 2
- Vector Search Rank: 5
- RRF Score = 1/(60+2) + 1/(60+5) = 0.0161 + 0.0154 = 0.0315

**Document: "Oceanview modern residence"**
- Text Search Rank: ∞ (not in top results)
- Vector Search Rank: 2
- RRF Score = 0 + 1/(60+2) = 0.0161

**Final Ranking:**
1. Contemporary waterside home (0.0323)
2. Waterfront villa with modern amenities (0.0323)
3. Modern beachfront property (0.0315)
4. Oceanview modern residence (0.0161)

## The Role of the k Parameter

### Understanding k's Impact

The parameter k controls how much weight is given to top-ranked items:

```python
import matplotlib.pyplot as plt
import numpy as np

ranks = np.arange(1, 101)
k_values = [10, 30, 60, 100]

for k in k_values:
    scores = 1 / (k + ranks)
    plt.plot(ranks[:20], scores[:20], label=f'k={k}')

plt.xlabel('Rank')
plt.ylabel('RRF Contribution')
plt.legend()
plt.title('RRF Score Contribution by Rank for Different k Values')
```

### Choosing k Value

**Small k (10-30):**
- Top ranks heavily weighted
- Large score differences
- Good for high-precision tasks
- Example: Finding exact matches

**Medium k (40-70):** ← Default
- Balanced weighting
- Moderate score differences
- Good for general search
- Example: Regular document retrieval

**Large k (80-100+):**
- More uniform weighting
- Small score differences
- Good for high-recall tasks
- Example: Discovery/exploration

### Mathematical Analysis

```
For k=60:
Rank 1:  1/61 = 0.0164 (100% baseline)
Rank 2:  1/62 = 0.0161 (98.2% of rank 1)
Rank 5:  1/65 = 0.0154 (93.9% of rank 1)
Rank 10: 1/70 = 0.0143 (87.2% of rank 1)
Rank 20: 1/80 = 0.0125 (76.2% of rank 1)
Rank 50: 1/110 = 0.0091 (55.5% of rank 1)

For k=10:
Rank 1:  1/11 = 0.0909 (100% baseline)
Rank 2:  1/12 = 0.0833 (91.7% of rank 1)
Rank 5:  1/15 = 0.0667 (73.3% of rank 1)
Rank 10: 1/20 = 0.0500 (55.0% of rank 1)
```

## Implementation in Elasticsearch

### Basic RRF Query

```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "match": {
                "description": "waterfront property"
              }
            }
          }
        },
        {
          "knn": {
            "field": "embedding",
            "query_vector": [...],
            "k": 50,
            "num_candidates": 100
          }
        }
      ],
      "rank_constant": 60,
      "rank_window_size": 100
    }
  }
}
```

### Advanced RRF with Multiple Retrievers

```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "multi_match": {
                "query": "modern waterfront",
                "fields": ["title^2", "description"]
              }
            }
          }
        },
        {
          "knn": {
            "field": "title_embedding",
            "query_vector": [...],
            "k": 30
          }
        },
        {
          "knn": {
            "field": "description_embedding",
            "query_vector": [...],
            "k": 30
          }
        },
        {
          "standard": {
            "query": {
              "more_like_this": {
                "fields": ["description"],
                "like": "luxury coastal living"
              }
            }
          }
        }
      ],
      "rank_constant": 60,
      "rank_window_size": 200
    }
  }
}
```

## Python Implementation

### Basic RRF Implementation

```python
def reciprocal_rank_fusion(rankings, k=60):
    \"\"\"
    Combine multiple rankings using RRF.
    
    Args:
        rankings: List of lists, each containing document IDs in rank order
        k: Constant parameter (default 60)
    
    Returns:
        List of (doc_id, score) tuples sorted by score
    \"\"\"
    doc_scores = {}
    
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1):
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
            doc_scores[doc_id] += 1 / (k + rank)
    
    return sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
```

### Weighted RRF Implementation

```python
def weighted_rrf(rankings, weights=None, k=60):
    \"\"\"
    Weighted version of RRF.
    
    Args:
        rankings: List of lists, each containing document IDs
        weights: List of weights for each ranking system
        k: Constant parameter
    
    Returns:
        List of (doc_id, score) tuples
    \"\"\"
    if weights is None:
        weights = [1.0] * len(rankings)
    
    doc_scores = {}
    
    for ranking, weight in zip(rankings, weights):
        for rank, doc_id in enumerate(ranking, 1):
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
            doc_scores[doc_id] += weight / (k + rank)
    
    return sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
```

### RRF with Score Normalization

```python
def rrf_with_scores(results_with_scores, k=60):
    \"\"\"
    RRF that first converts scores to ranks.
    
    Args:
        results_with_scores: List of [(doc_id, score)] lists
        k: Constant parameter
    
    Returns:
        Combined ranking
    \"\"\"
    rankings = []
    
    for result_list in results_with_scores:
        # Sort by score and extract doc_ids
        sorted_results = sorted(result_list, key=lambda x: x[1], reverse=True)
        ranking = [doc_id for doc_id, _ in sorted_results]
        rankings.append(ranking)
    
    return reciprocal_rank_fusion(rankings, k)
```

## Optimizing RRF Performance

### Parameter Tuning

```python
def evaluate_rrf_parameters(ground_truth, rankings, k_values):
    \"\"\"
    Find optimal k value for your data.
    \"\"\"
    results = {}
    
    for k in k_values:
        fused = reciprocal_rank_fusion(rankings, k)
        # Calculate metrics (e.g., NDCG, MAP)
        ndcg = calculate_ndcg(fused, ground_truth)
        results[k] = ndcg
    
    return results

# Example usage
k_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
best_k = evaluate_rrf_parameters(ground_truth, rankings, k_values)
```

### Rank Window Size Optimization

The `rank_window_size` parameter limits how many results from each system to consider:

```python
def windowed_rrf(rankings, k=60, window_size=100):
    \"\"\"
    RRF with rank window size limit.
    \"\"\"
    # Truncate each ranking to window_size
    truncated_rankings = [ranking[:window_size] for ranking in rankings]
    return reciprocal_rank_fusion(truncated_rankings, k)
```

**Choosing Window Size:**
- Small (50-100): Fast, may miss relevant results
- Medium (100-200): Balanced performance/quality
- Large (200+): Better recall, slower performance

## Advanced RRF Techniques

### Adaptive RRF

```python
def adaptive_rrf(rankings, performance_history, k=60):
    \"\"\"
    Adjust weights based on historical performance.
    \"\"\"
    # Calculate weights based on past performance
    weights = calculate_adaptive_weights(performance_history)
    return weighted_rrf(rankings, weights, k)

def calculate_adaptive_weights(performance_history):
    \"\"\"
    Derive weights from historical click-through rates.
    \"\"\"
    total_clicks = sum(performance_history.values())
    weights = [clicks / total_clicks for clicks in performance_history.values()]
    return weights
```

### Cascaded RRF

```python
def cascaded_rrf(rankings_groups, k_values):
    \"\"\"
    Multiple stages of RRF with different k values.
    
    Args:
        rankings_groups: List of ranking groups for each stage
        k_values: k value for each stage
    \"\"\"
    current_ranking = rankings_groups[0]
    
    for rankings, k in zip(rankings_groups[1:], k_values[1:]):
        # Combine current ranking with next group
        all_rankings = [current_ranking] + rankings
        fused = reciprocal_rank_fusion(all_rankings, k)
        current_ranking = [doc_id for doc_id, _ in fused]
    
    return current_ranking
```

### RRF with Diversity

```python
def diverse_rrf(rankings, k=60, lambda_diversity=0.5):
    \"\"\"
    RRF with diversity promotion.
    \"\"\"
    doc_scores = {}
    doc_sources = {}
    
    # Calculate RRF scores and track sources
    for system_id, ranking in enumerate(rankings):
        for rank, doc_id in enumerate(ranking, 1):
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_sources[doc_id] = set()
            doc_scores[doc_id] += 1 / (k + rank)
            doc_sources[doc_id].add(system_id)
    
    # Adjust scores based on source diversity
    for doc_id in doc_scores:
        diversity_bonus = len(doc_sources[doc_id]) / len(rankings)
        doc_scores[doc_id] *= (1 + lambda_diversity * diversity_bonus)
    
    return sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
```

## Common Patterns and Best Practices

### Pattern 1: Text + Vector Hybrid

```python
def text_vector_hybrid(query_text, query_vector, es_client):
    # Text search
    text_results = es_client.search(
        body={"query": {"match": {"content": query_text}}}
    )
    
    # Vector search
    vector_results = es_client.search(
        body={"knn": {"field": "embedding", "query_vector": query_vector}}
    )
    
    # Extract rankings
    text_ranking = [hit['_id'] for hit in text_results['hits']['hits']]
    vector_ranking = [hit['_id'] for hit in vector_results['hits']['hits']]
    
    # Fuse with RRF
    return reciprocal_rank_fusion([text_ranking, vector_ranking])
```

### Pattern 2: Multi-Field RRF

```python
def multi_field_rrf(query, fields, es_client):
    \"\"\"
    Search multiple fields and combine with RRF.
    \"\"\"
    rankings = []
    
    for field in fields:
        results = es_client.search(
            body={"query": {"match": {field: query}}}
        )
        ranking = [hit['_id'] for hit in results['hits']['hits']]
        rankings.append(ranking)
    
    return reciprocal_rank_fusion(rankings)
```

### Pattern 3: Cross-Language RRF

```python
def cross_language_rrf(query, languages, es_client):
    \"\"\"
    Search in multiple languages and combine.
    \"\"\"
    rankings = []
    
    for lang in languages:
        # Translate query
        translated_query = translate(query, target_lang=lang)
        
        # Search in language-specific field
        results = es_client.search(
            body={"query": {"match": {f"content_{lang}": translated_query}}}
        )
        
        ranking = [hit['_id'] for hit in results['hits']['hits']]
        rankings.append(ranking)
    
    return reciprocal_rank_fusion(rankings)
```

## Troubleshooting RRF

### Issue 1: Poor Result Quality

**Symptoms:** Fused results worse than individual systems

**Diagnosis:**
```python
def diagnose_rrf_quality(rankings, ground_truth):
    # Check individual system performance
    for i, ranking in enumerate(rankings):
        score = calculate_metric(ranking, ground_truth)
        print(f"System {i}: {score}")
    
    # Check fusion performance
    fused = reciprocal_rank_fusion(rankings)
    fused_score = calculate_metric(fused, ground_truth)
    print(f"Fused: {fused_score}")
    
    # Check overlap
    overlap = len(set(rankings[0]) & set(rankings[1]))
    print(f"Overlap: {overlap}/{len(rankings[0])}")
```

**Solutions:**
- Adjust k parameter
- Use weighted RRF
- Filter poor-performing systems

### Issue 2: Performance Problems

**Symptoms:** Slow fusion process

**Solutions:**
```python
# Use early termination
def fast_rrf(rankings, k=60, top_n=100):
    # Only process top_n from each ranking
    truncated = [r[:top_n] for r in rankings]
    return reciprocal_rank_fusion(truncated, k)

# Use approximate RRF
def approximate_rrf(rankings, k=60, sample_rate=0.5):
    # Sample rankings for speed
    sampled = [r[:int(len(r) * sample_rate)] for r in rankings]
    return reciprocal_rank_fusion(sampled, k)
```

### Issue 3: Inconsistent Rankings

**Symptoms:** Same query produces different results

**Diagnosis:**
```python
def check_consistency(query_func, n_runs=10):
    results = []
    for _ in range(n_runs):
        ranking = query_func()
        results.append(ranking)
    
    # Check variance
    for i in range(1, n_runs):
        similarity = calculate_ranking_similarity(results[0], results[i])
        print(f"Run {i} similarity: {similarity}")
```

**Solutions:**
- Ensure deterministic ranking
- Fix random seeds
- Use stable sorting

## Evaluation Metrics for RRF

### NDCG (Normalized Discounted Cumulative Gain)

```python
def calculate_ndcg(ranking, relevance_scores, k=10):
    dcg = 0
    for i, doc_id in enumerate(ranking[:k]):
        rel = relevance_scores.get(doc_id, 0)
        dcg += (2**rel - 1) / np.log2(i + 2)
    
    # Calculate ideal DCG
    ideal_ranking = sorted(relevance_scores.items(), 
                          key=lambda x: x[1], reverse=True)
    idcg = 0
    for i, (_, rel) in enumerate(ideal_ranking[:k]):
        idcg += (2**rel - 1) / np.log2(i + 2)
    
    return dcg / idcg if idcg > 0 else 0
```

### MAP (Mean Average Precision)

```python
def calculate_map(rankings, relevant_docs):
    ap_scores = []
    
    for ranking in rankings:
        hits = 0
        sum_precision = 0
        
        for i, doc_id in enumerate(ranking):
            if doc_id in relevant_docs:
                hits += 1
                precision = hits / (i + 1)
                sum_precision += precision
        
        ap = sum_precision / len(relevant_docs) if relevant_docs else 0
        ap_scores.append(ap)
    
    return np.mean(ap_scores)
```

## Conclusion

RRF is a powerful and elegant solution for combining multiple ranking systems. Its key advantages:

1. **No score calibration needed** - Works with ranks, not scores
2. **Simple to implement** - Just a few lines of code
3. **Empirically effective** - Proven in many applications
4. **Flexible** - Can be adapted for various use cases

The key to success with RRF is understanding:
- How the k parameter affects fusion
- When to use weighted vs. unweighted RRF
- How to optimize for your specific use case
- How to evaluate and monitor performance

With proper tuning and implementation, RRF can significantly improve search quality by combining the strengths of different ranking systems.
"""
    
    with open("demo_queries_json/RRF_COMPLETE_GUIDE.md", "w") as f:
        f.write(guide)


if __name__ == "__main__":
    main()