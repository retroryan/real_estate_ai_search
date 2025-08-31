# Elasticsearch Demo Queries Guide

This directory contains demonstration queries showcasing various Elasticsearch search patterns and features. Each query demonstrates specific search concepts, from basic full-text search to complex aggregations and geo-spatial queries.

## 📚 Query Types and Concepts

### Core Query Types Explained

#### 1. **Full-Text Search Queries**
- **What it is**: Analyzed text search that tokenizes, stems, and scores by relevance
- **How it works**: Text is broken into tokens, analyzed (lowercase, stemming), and matched using TF-IDF or BM25 scoring
- **Use case**: Finding documents containing words or phrases regardless of exact form

#### 2. **Term Queries**
- **What it is**: Exact match queries on non-analyzed fields (keywords)
- **How it works**: No analysis performed - exact byte-for-byte matching
- **Use case**: Filtering by categories, IDs, or exact values

#### 3. **Bool Queries**
- **What it is**: Compound queries combining multiple query clauses
- **Components**:
  - `must`: Clauses that must match (affects score)
  - `filter`: Clauses that must match (no score impact)
  - `should`: Optional clauses that boost score if matched
  - `must_not`: Clauses that must not match
- **Use case**: Complex searches with multiple criteria

#### 4. **Range Queries**
- **What it is**: Find documents with values within specified bounds
- **How it works**: Efficiently uses data structures to find numeric/date ranges
- **Use case**: Price ranges, date ranges, numeric thresholds

#### 5. **Geo Queries**
- **What it is**: Location-based searches using coordinates
- **Types**: geo_distance, geo_bounding_box, geo_polygon
- **Use case**: "Find properties within X miles of location"

#### 6. **Aggregation Queries**
- **What it is**: Analytics and statistics on search results
- **Types**: Metrics (avg, sum, min, max), Buckets (terms, histogram, date_histogram)
- **Use case**: Market analysis, statistics, grouping

#### 7. **Nested Queries**
- **What it is**: Query nested objects maintaining parent-child relationships
- **How it works**: Searches within nested documents independently
- **Use case**: Arrays of objects where relationships matter

#### 8. **KNN (K-Nearest Neighbor) Queries**
- **What it is**: Vector similarity search using dense embeddings
- **How it works**: Finds k most similar vectors using distance metrics (cosine, L2, dot product)
- **Components**:
  - `field`: The dense_vector field to search
  - `query_vector`: The reference vector (1024 dimensions for voyage-3)
  - `k`: Number of nearest neighbors to find
  - `num_candidates`: Candidates per shard (accuracy vs speed tradeoff)
- **Use case**: Semantic similarity, recommendation systems, finding "similar" items

## 📁 Query Files Overview

### `advanced_queries.py`
**Purpose**: Advanced search patterns including KNN vector search and multi-index queries

#### Queries and Features:

1. **`demo_semantic_search()`**
   - **Type**: KNN (k-nearest neighbor) vector search
   - **Features**:
     - `knn` query for efficient vector similarity search
     - Uses 1024-dimensional dense vectors from voyage-3 model
     - Cosine similarity for semantic matching
     - `num_candidates: 100` for accuracy/speed balance
     - Excludes reference property using bool filter
   - **Process**:
     1. Get reference property and its embedding vector
     2. Use KNN to find k most similar properties
     3. Return properties ranked by vector similarity
   - **Example**: Find properties similar to a luxury waterfront home
   - **What happens**: Vectors are compared in 1024-dimensional space, finding semantically similar properties

2. **`demo_multi_entity_search()`**
   - **Type**: Multi-index unified search
   - **Features**:
     - Searches across properties, neighborhoods, and wikipedia indexes
     - Single `multi_match` query across all indexes
     - Field boosting across different entity types
     - Index discrimination in results
     - Aggregations by index
   - **Example**: Search for "historic downtown" across all data
   - **What happens**: Returns mixed results from different indexes, ranked by unified relevance

3. **`demo_wikipedia_search()`**
   - **Type**: Complex bool query with geographic filtering
   - **Features**:
     - Query vs filter context demonstration
     - Nested bool queries for OR within AND logic
     - `exists` query for field presence checking
     - Multi-level boosting strategies
     - Multi-field sorting with null handling
   - **Example**: Find Wikipedia articles about culture in San Francisco
   - **What happens**: Combines location filters with topic matching and quality boosting

### `property_queries.py`
**Purpose**: Core property search patterns

#### Queries and Features:

1. **`demo_basic_property_search()`**
   - **Type**: Multi-field full-text search
   - **Features**:
     - `multi_match` query across description, amenities, address.city
     - Field boosting (description^2 gives 2x weight)
     - Fuzzy matching with `fuzziness: AUTO`
     - Operator: OR (any term matches)
   - **Example**: "modern home with pool"
   - **What happens**: Tokenized to ["modern", "home", "pool"], stems words, finds any matching properties

2. **`demo_filtered_property_search()`**
   - **Type**: Bool query with exact filters
   - **Features**:
     - `term` query for exact property_type (keyword field)
     - `range` queries for price, bedrooms, bathrooms
     - `match` queries for amenities (analyzed)
     - All in `filter` context (no scoring)
   - **Example**: Condos between $200k-$500k with 2+ bedrooms
   - **What happens**: Applies hard filters, returns only matching properties

3. **`demo_geo_distance_search()`**
   - **Type**: Geo-spatial query
   - **Features**:
     - `geo_distance` filter with radius
     - Optional price range filter
     - Distance unit specification (km, miles)
   - **Example**: Properties within 10km of coordinates
   - **What happens**: Calculates distance from point, filters by radius

4. **`demo_price_range_search()`**
   - **Type**: Range query with aggregations
   - **Features**:
     - `range` query on price field
     - Multiple aggregations:
       - `stats`: min, max, avg, count
       - `terms`: top property types
       - `histogram`: price distribution buckets
   - **Example**: Properties $400k-$800k with market statistics
   - **What happens**: Filters by range, computes analytics on results

### `wikipedia_fulltext.py`
**Purpose**: Full-text search patterns on Wikipedia content

#### Key Queries:

1. **Historical Events Search**
   - **Type**: Single field match query
   - **Features**:
     - `match` query on full_content field
     - English analyzer (stemming, stop words)
     - Natural language query
   - **Example**: "1906 earthquake fire San Francisco reconstruction"
   - **Scoring**: TF-IDF based on term frequency and document frequency

2. **Transportation Infrastructure**
   - **Type**: Bool query with should clauses
   - **Features**:
     - Multiple `should` clauses (OR logic)
     - Each clause can match independently
     - Higher score for multiple matches
   - **Example**: Finds articles mentioning cable cars OR BART OR public transit

3. **Parks and Recreation**
   - **Type**: Nested bool with must + should
   - **Features**:
     - `must`: Required term "park"
     - `should`: Optional related terms boost relevance
     - Combines mandatory and optional matching
   - **Example**: Must contain "park", scores higher if also mentions "hiking" or "wildlife"

4. **Cultural Venues**
   - **Type**: Multi-match query
   - **Features**:
     - Single query string across multiple fields
     - Can specify field weights
     - Cross-field matching
   - **Example**: "museum theater cultural arts gallery" matches any field

### `aggregation_queries.py`
**Purpose**: Analytics and statistics queries

#### Key Aggregations:

1. **`demo_neighborhood_stats()`**
   - **Type**: Terms aggregation with sub-aggregations
   - **Features**:
     - Groups by neighborhood (terms agg)
     - Calculates stats per neighborhood:
       - Average price
       - Property count
       - Price range (min/max)
     - Sorted by average price
   - **Use case**: Market analysis by neighborhood

2. **`demo_price_distribution()`**
   - **Type**: Histogram aggregation
   - **Features**:
     - Bucketed price ranges
     - Extended bounds for consistent buckets
     - Nested aggregations per bucket
   - **Use case**: Price distribution visualization

### `demo_single_query_relationships.py`
**Purpose**: Denormalized index queries for performance

#### Key Patterns:

1. **Single Index Denormalized Search**
   - **Type**: Nested object queries
   - **Features**:
     - Single query instead of multiple
     - Nested Wikipedia articles within property documents
     - Trade storage for query performance
   - **Benefits**: 
     - No client-side joining
     - Atomic consistency
     - Better performance for read-heavy workloads

## 🎯 Query Feature Showcase

### Text Analysis Features

| Feature | Query Type | File | Example |
|---------|------------|------|---------|
| **Tokenization** | match, multi_match | property_queries.py | "modern home" → ["modern", "home"] |
| **Stemming** | match with english analyzer | wikipedia_fulltext.py | "running" matches "run", "runs", "ran" |
| **Fuzzy Matching** | match with fuzziness | property_queries.py | "hose" matches "house" (1 edit distance) |
| **Phrase Matching** | match_phrase | wikipedia_fulltext.py | "San Francisco" as exact phrase |
| **Stop Words** | analyzed text fields | All files | "the", "a", "is" removed from queries |

### Scoring and Relevance

| Feature | Query Type | File | Example |
|---------|------------|------|---------|
| **Field Boosting** | multi_match with ^ | property_queries.py | description^2 (2x weight) |
| **Should Boosting** | bool with should | advanced_queries.py | Optional clauses increase score |
| **Constant Score** | filter context | property_queries.py | Filters don't affect relevance |
| **Function Score** | function_score | Not shown | Custom scoring functions |

### Filtering and Exact Matching

| Feature | Query Type | File | Example |
|---------|------------|------|---------|
| **Exact Term** | term | property_queries.py | property_type: "Condo" (exact) |
| **Range Filter** | range | property_queries.py | price: {gte: 200000, lte: 500000} |
| **Exists Check** | exists | Not shown | Check if field has value |
| **Geo Filter** | geo_distance | property_queries.py | Within radius of point |

### Complex Queries

| Feature | Query Type | File | Example |
|---------|------------|------|---------|
| **Compound Logic** | bool | All files | Combine must/filter/should/must_not |
| **Nested Objects** | nested | demo_single_query_relationships.py | Query array items independently |
| **Multi-Index** | msearch | advanced_queries.py | Search multiple indexes |
| **Aggregations** | aggs | aggregation_queries.py | Statistics and grouping |
| **KNN Vector Search** | knn | advanced_queries.py | Semantic similarity with embeddings |
| **Hybrid Search** | knn + match | advanced_queries.py | Combine vector and text search |

## 🚀 Query Execution Flow

### 1. Analysis Phase
```
Input: "beautiful homes near parks"
         ↓ Tokenization
    ["beautiful", "homes", "near", "parks"]
         ↓ Lowercase
    ["beautiful", "homes", "near", "parks"]
         ↓ Stop word removal
    ["beautiful", "homes", "parks"]
         ↓ Stemming
    ["beauti", "home", "park"]
```

### 2. Matching Phase
```
Query Terms: ["beauti", "home", "park"]
         ↓
Document 1: ["modern", "home", "garden"] → Match on "home"
Document 2: ["beauti", "hous", "park"] → Match on "beauti", "park"
Document 3: ["apartment", "near", "park"] → Match on "park"
```

### 3. Scoring Phase
```
Document 2: 2 matches × field weight = highest score
Document 1: 1 match × field weight = medium score
Document 3: 1 match × field weight = medium score
```

## 🧠 KNN Vector Search Flow

### Semantic Search Pipeline

#### 1. Embedding Generation (Indexing)
```
Property Description: "Luxury waterfront home with panoramic ocean views"
         ↓ voyage-3 model
    1024-dimensional vector: [0.123, -0.456, 0.789, ...]
         ↓ Store in dense_vector field
    Indexed with HNSW algorithm for fast retrieval
```

#### 2. Query Embedding (Search Time)
```
Query: "beachfront property with sea views"
         ↓ Same voyage-3 model
    Query vector: [0.111, -0.444, 0.777, ...]
```

#### 3. KNN Search
```
knn: {
  field: "embedding",
  query_vector: [0.111, -0.444, 0.777, ...],
  k: 10,
  num_candidates: 100
}
         ↓ HNSW graph traversal
    Find 10 nearest vectors by cosine similarity
         ↓ Score by similarity (0-1 range)
    Return documents ranked by semantic similarity
```

#### 4. Hybrid Scoring (Optional)
```
Combine KNN score with text relevance:
- KNN Score: 0.95 (very similar vectors)
- Text Match Score: 0.75 (keyword matches)
         ↓ Weighted combination
    Final Score: 0.85
```

### Why KNN is Superior for Semantic Search

1. **Efficiency**: HNSW algorithm provides sub-linear search time
2. **Accuracy**: Approximate search with ~95% recall
3. **Scalability**: Works with millions of vectors
4. **Language Understanding**: Captures semantic meaning, not just keywords
5. **No Training Required**: Pre-trained voyage-3 model works out-of-box

## 💡 Best Practices Demonstrated

1. **Use Appropriate Query Types**
   - Full-text search: `match`, `multi_match`
   - Exact filtering: `term`, `terms`
   - Complex logic: `bool` query

2. **Optimize for Performance**
   - Use `filter` context for non-scoring clauses
   - Denormalize for read-heavy workloads
   - Use appropriate field types (keyword vs text)

3. **Enhance Relevance**
   - Boost important fields
   - Use should clauses for optional matches
   - Configure appropriate analyzers

4. **Structure for Maintainability**
   - Separate query building from execution
   - Use typed models for responses
   - Document query purposes

## 🎓 Learning Path

1. **Start Simple**: property_queries.py - Basic searches
2. **Add Filters**: Learn bool queries and exact matching
3. **Explore Text**: wikipedia_fulltext.py - Full-text features
4. **Analyze Data**: aggregation_queries.py - Statistics
5. **Go Complex**: advanced_queries.py - Multi-index search
6. **Optimize**: demo_single_query_relationships.py - Denormalization

## 📊 Query Performance Tips

- **Filters before queries**: Apply filters in filter context
- **Limit field count**: Fewer fields to search = faster
- **Use source filtering**: Return only needed fields
- **Cache aggregations**: For repeated analytics
- **Profile queries**: Use `"profile": true` to analyze

This demonstration suite provides a comprehensive overview of Elasticsearch query capabilities, from simple text matching to complex multi-index searches with aggregations.