# Complete Guide to Reciprocal Rank Fusion (RRF)

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
    """
    Combine multiple rankings using RRF.
    
    Args:
        rankings: List of lists, each containing document IDs in rank order
        k: Constant parameter (default 60)
    
    Returns:
        List of (doc_id, score) tuples sorted by score
    """
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
    """
    Weighted version of RRF.
    
    Args:
        rankings: List of lists, each containing document IDs
        weights: List of weights for each ranking system
        k: Constant parameter
    
    Returns:
        List of (doc_id, score) tuples
    """
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
    """
    RRF that first converts scores to ranks.
    
    Args:
        results_with_scores: List of [(doc_id, score)] lists
        k: Constant parameter
    
    Returns:
        Combined ranking
    """
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
    """
    Find optimal k value for your data.
    """
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
    """
    RRF with rank window size limit.
    """
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
    """
    Adjust weights based on historical performance.
    """
    # Calculate weights based on past performance
    weights = calculate_adaptive_weights(performance_history)
    return weighted_rrf(rankings, weights, k)

def calculate_adaptive_weights(performance_history):
    """
    Derive weights from historical click-through rates.
    """
    total_clicks = sum(performance_history.values())
    weights = [clicks / total_clicks for clicks in performance_history.values()]
    return weights
```

### Cascaded RRF

```python
def cascaded_rrf(rankings_groups, k_values):
    """
    Multiple stages of RRF with different k values.
    
    Args:
        rankings_groups: List of ranking groups for each stage
        k_values: k value for each stage
    """
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
    """
    RRF with diversity promotion.
    """
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
    """
    Search multiple fields and combine with RRF.
    """
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
    """
    Search in multiple languages and combine.
    """
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
