# Elasticsearch Demo Queries Guide

This directory contains demonstration queries showcasing various Elasticsearch search patterns and features. Each query demonstrates specific search concepts, from basic full-text search to complex aggregations and geo-spatial queries.

## 📊 Quick Reference: Demo Queries Overview

| Demo Query | Description | ES Concepts Demonstrated | Code Location |
|------------|-------------|--------------------------|---------------|
| **Basic Property Search** | Multi-field text search with fuzzy matching | `multi_match`, field boosting, fuzzy matching, tokenization | `property_queries.py:demo_basic_property_search()` |
| **Filtered Property Search** | Combined filters for type, price, amenities | `bool` query, `term` filters, `range` queries, filter context | `property_queries.py:demo_filtered_property_search()` |
| **Geo Distance Search** | Find properties within radius of location | `geo_distance`, spatial indexing, distance calculations | `property_queries.py:demo_geo_distance_search()` |
| **Price Range with Stats** | Price filtering with market analytics | `range` query, `stats` aggregation, `histogram` buckets | `property_queries.py:demo_price_range_search()` |
| **Semantic Search (KNN)** | Find similar properties using vectors | `knn` query, dense vectors, cosine similarity, HNSW | `advanced_queries.py:demo_semantic_search()` |
| **Multi-Entity Search** | Unified search across multiple indexes | Multi-index search, unified scoring, index discrimination | `advanced_queries.py:demo_multi_entity_search()` |
| **Wikipedia Complex Query** | Geographic filtering with topic matching | Nested `bool`, `exists` query, multi-level boosting | `advanced_queries.py:demo_wikipedia_search()` |
| **Neighborhood Statistics** | Market analysis by neighborhood | `terms` aggregation, sub-aggregations, stats per bucket | `aggregation_queries.py:demo_neighborhood_stats()` |
| **Price Distribution** | Histogram of property prices | `histogram` aggregation, extended bounds, bucketing | `aggregation_queries.py:demo_price_distribution()` |
| **Historical Events** | Full-text search on Wikipedia | `match` query, English analyzer, stemming, TF-IDF | `wikipedia_fulltext.py` (Historical Events) |
| **Transportation Search** | OR logic with multiple terms | `bool` with `should` clauses, optional matching | `wikipedia_fulltext.py` (Transportation) |
| **Parks & Recreation** | Required + optional terms | `must` + `should` combination, mandatory matching | `wikipedia_fulltext.py` (Parks) |
| **Cultural Venues** | Multi-field matching | `multi_match`, cross-field matching, field weights | `wikipedia_fulltext.py` (Cultural) |
| **Denormalized Search** | Single-index relationship queries | `nested` objects, denormalization patterns, performance optimization | `demo_single_query_relationships.py` |
| **Hybrid Search (RRF)** ⭐ | Modern text + vector fusion with RRF | `retriever.rrf`, parallel retrievers, rank fusion, native ES 8.15+ | `hybrid_search.py:demo_hybrid_search()` |
| **Location-Aware Hybrid** ⭐ | Hybrid search with location extraction | DSPy location extraction, geographic filters, query cleaning | `location_aware_demos.py:HybridSearchEngine.search_with_location()` |
| **Waterfront Luxury** | Location + lifestyle search | City extraction, luxury filtering, semantic understanding | `location_aware_demos.py:demo_location_aware_waterfront_luxury()` |
| **Family Home Schools** | Family-oriented with location | City + state extraction, lifestyle features, school proximity | `location_aware_demos.py:demo_location_aware_family_schools()` |
| **Urban Modern** | Architectural style in city | Urban area understanding, modern architecture filtering | `location_aware_demos.py:demo_location_aware_urban_modern()` |
| **Investment Property** | Market-specific investment search | Investment criteria, market analysis, location targeting | `location_aware_demos.py:demo_location_aware_recreation_mountain()` |
| **Historic Home** | Historic architecture search | Historic features, character properties, city normalization | `location_aware_demos.py:demo_location_aware_historic_urban()` |
| **Affordable Housing** | Budget-constrained search | Price filtering, affordability analysis, location constraints | `location_aware_demos.py:demo_location_aware_beach_proximity()` |
| **Condo Amenities** | Amenity-focused search | Amenity matching, condo features, Silicon Valley context | `location_aware_demos.py:demo_location_aware_investment_market()` |
| **Bay Area Regional** | Regional property search | Region recognition, Bay Area filtering, property type | `location_aware_demos.py:demo_location_aware_luxury_urban_views()` |
| **Townhouse Budget** | Type + price constraints | Property type filter, price range, Oakland market | `location_aware_demos.py:demo_location_aware_suburban_architecture()` |
| **Modern Condo Parking** | Specific amenity requirements | Parking amenity, modern architecture, full location spec | `location_aware_demos.py:demo_location_aware_neighborhood_character()` |

### Key for ES Concepts:
- **Query Types**: `match`, `multi_match`, `term`, `range`, `bool`, `knn`, `geo_distance`, `nested`, `exists`
- **Aggregations**: `terms`, `stats`, `histogram`, `date_histogram`, sub-aggregations
- **Modern Features**: `retriever.rrf` (ES 8.15+), dense vectors, HNSW indexing
- **Analysis**: Tokenization, stemming, fuzzy matching, English analyzer
- **Scoring**: BM25, field boosting, `should` clauses, filter context
- **Performance**: Denormalization, filter caching, doc values

## 📚 Query Types and Concepts

### Core Query Types Explained

#### 1. **Full-Text Search Queries**
- **What it is**: Analyzed text search that tokenizes, stems, and scores by relevance
- **How it works**: 
  - Text analysis pipeline: tokenization → lowercase → stop word removal → stemming
  - Uses BM25 scoring algorithm (modern replacement for TF-IDF)
  - Inverted index lookup for efficient token matching
  - Relevance scoring considers term frequency, document frequency, field length normalization
- **Analysis process**:
  ```
  "modern luxury home" → ["modern", "luxury", "home"] → BM25 scoring → ranked results
  ```
- **Use case**: Finding documents containing words or phrases regardless of exact form
- **Performance**: O(log n) index lookups, highly optimized for text search

#### 2. **Term Queries**
- **What it is**: Exact match queries on non-analyzed fields (keywords)
- **How it works**: 
  - No analysis performed - exact byte-for-byte matching
  - Uses term dictionary for O(1) lookups
  - Constant score queries (no relevance calculation)
  - Perfect for filtering and exact matching
- **Data structure**: Hash-based term dictionary with posting lists
- **Use case**: Filtering by categories, IDs, status values, exact values
- **Performance**: Extremely fast O(1) lookups

#### 3. **Bool Queries**
- **What it is**: Compound queries combining multiple query clauses using boolean logic
- **Components**:
  - `must`: Clauses that must match (affects score) - AND logic with scoring
  - `filter`: Clauses that must match (no score impact) - AND logic, constant score
  - `should`: Optional clauses that boost score if matched - OR logic with boosting
  - `must_not`: Clauses that must not match - NOT logic, excludes documents
- **Execution order**: Filters first (fastest), then must/should clauses
- **Score calculation**: Combines individual clause scores using Lucene's boolean scoring
- **Use case**: Complex searches with multiple criteria, faceted search, filtered queries
- **Performance**: Optimized with filter caching, early termination

#### 4. **Range Queries**
- **What it is**: Find documents with values within specified bounds
- **How it works**: 
  - Uses specialized data structures (BKD trees for numerics, trie for dates)
  - Binary search trees enable O(log n) range lookups
  - Supports inclusive/exclusive bounds: gte, gt, lte, lt
  - Automatic type coercion and validation
- **Data structures**: 
  - Numeric: Block KD-trees (BKD) for multi-dimensional range queries
  - Dates: Trie-based structures with millisecond precision
- **Use case**: Price ranges, date ranges, numeric thresholds, age filtering
- **Performance**: O(log n) lookups with excellent range scanning

#### 5. **Geo Queries**
- **What it is**: Location-based searches using geographic coordinates and shapes
- **Types**:
  - `geo_distance`: Radial search from a point
  - `geo_bounding_box`: Rectangular area search
  - `geo_polygon`: Custom polygon area search
  - `geo_shape`: Complex geometric shape queries
- **How it works**:
  - Uses geohash encoding for efficient spatial indexing
  - Haversine formula for accurate distance calculations
  - BKD trees for multi-dimensional geo data
  - Supports various distance units (km, miles, meters)
- **Use case**: "Find properties within X miles of location", area-based searches
- **Performance**: Logarithmic complexity with spatial indexing optimizations

#### 6. **Aggregation Queries**
- **What it is**: Analytics and statistics computation on search results or entire datasets
- **Types**:
  - **Metric Aggregations**: Single-value calculations (avg, sum, min, max, stats, cardinality)
  - **Bucket Aggregations**: Group data (terms, date_histogram, histogram, range)
  - **Pipeline Aggregations**: Operate on other aggregations (moving_avg, derivative)
  - **Matrix Aggregations**: Multi-field statistics (matrix_stats)
- **How it works**:
  - Post-query aggregation phase
  - Uses doc values (columnar storage) for performance
  - Distributed aggregation across shards with result merging
  - Memory-efficient streaming aggregations
- **Use case**: Market analysis, statistics, grouping, dashboards, analytics
- **Performance**: Optimized with doc values, approximate algorithms for large datasets

#### 7. **Nested Queries**
- **What it is**: Query nested objects maintaining parent-child relationships within documents
- **How it works**: 
  - Nested documents stored as separate Lucene documents
  - Special join queries maintain parent-child relationships
  - Independent scoring for nested matches
  - Supports nested aggregations and sorting
- **Document structure**: Flattened arrays lose relationships; nested preserves them
- **Use case**: Arrays of objects where relationships matter (product variants, contact info)
- **Performance**: Higher memory usage but maintains data integrity

#### 8. **KNN (K-Nearest Neighbor) Queries**
- **What it is**: Vector similarity search using dense embeddings for semantic matching
- **How it works**: 
  - HNSW (Hierarchical Navigable Small World) algorithm for approximate nearest neighbor search
  - Distance metrics: cosine similarity, L2 (Euclidean), dot product
  - Multi-layer graph structure for O(log n) search complexity
  - Approximate search with configurable accuracy/speed tradeoffs
- **Components**:
  - `field`: The dense_vector field to search (e.g., 1024-dimensional vectors)
  - `query_vector`: The reference embedding vector
  - `k`: Number of nearest neighbors to return
  - `num_candidates`: Candidates per shard (higher = more accurate, slower)
- **Vector generation**: Uses embedding models (voyage-3, OpenAI, etc.) to convert text → vectors
- **Use case**: Semantic similarity, "find similar" recommendations, cross-lingual search
- **Performance**: Sub-linear O(log n) with HNSW, highly scalable

#### 9. **Hybrid Search Queries** ⭐ **NEW**
- **What it is**: Advanced search combining semantic vector search with traditional text search using RRF (Reciprocal Rank Fusion)
- **How it works**: 
  - **Step 1**: Execute parallel retrievers - text search (BM25) + vector search (KNN)
  - **Step 2**: Apply RRF algorithm to merge rankings from different retrievers
  - **Step 3**: Rerank results using reciprocal rank fusion formula
  - **RRF Formula**: `score = Σ(1 / (k + rank_i))` where k is rank_constant
- **Modern Implementation**:
  ```json
  {
    "retriever": {
      "rrf": {
        "retrievers": [
          {"standard": {"query": {"multi_match": {"query": "text", "fields": ["field1^2", "field2"]}}}},
          {"knn": {"field": "embedding", "query_vector": [0.1, 0.2, ...], "k": 50}}
        ],
        "rank_constant": 60,
        "rank_window_size": 100
      }
    }
  }
  ```
- **Benefits**:
  - **Precision + Recall**: Combines exact keyword matching with semantic understanding
  - **Relevance**: RRF balances different ranking signals optimally
  - **Robustness**: Handles queries that work better with either text or vector search
  - **Modern**: Uses Elasticsearch 8.15+ native retriever syntax
- **Use case**: Best-of-both-worlds search, handling diverse query types, production search systems
- **Performance**: Parallel execution with efficient result merging

#### 10. **Location-Aware Hybrid Search** ⭐ **NEW**
- **What it is**: Intelligent hybrid search with automatic location extraction and geographic filtering
- **How it works**: 
  - **Step 1**: Natural language processing extracts location intent (city, state, regions)
  - **Step 2**: Applies geographic filters to both text and vector retrievers
  - **Step 3**: Uses cleaned query (location terms removed) for better semantic matching
  - **Step 4**: Combines location filtering with hybrid RRF search
- **Location Understanding**:
  - Uses DSPy modules for location entity recognition
  - Extracts cities, states, neighborhoods, regions
  - Builds appropriate Elasticsearch geo/term filters
  - Handles ambiguous locations and multi-location queries
- **Query Processing**:
  ```
  Input: "luxury condo in San Francisco with city views"
  Location Extraction: city="San Francisco", state="California"
  Cleaned Query: "luxury condo with city views" 
  Geo Filters: address.city="San Francisco", address.state="California"
  ```
- **Use case**: Real estate search, local business discovery, geo-targeted content
- **Performance**: Efficient filtering with geo-optimized indexes

## 📁 Query Files Overview

### `hybrid_search.py` ⭐ **NEW**
**Purpose**: Modern hybrid search implementation combining vector and text search with RRF

#### Core Classes:

1. **`HybridSearchEngine`**
   - **Purpose**: Production-ready hybrid search with location awareness
   - **Features**:
     - Native Elasticsearch RRF using retriever syntax (8.15+)
     - Location intent extraction and geographic filtering
     - Configurable rank constants and window sizes
     - Parallel text and vector retriever execution
     - Support for 1024-dimensional voyage-3 embeddings
   - **Method**: `search_with_location()` - Full location-aware hybrid search
   - **Architecture**: 
     ```
     Query → Location Extraction → Text + Vector Retrievers → RRF Fusion → Results
     ```

2. **`HybridSearchParams`**
   - **Purpose**: Comprehensive search configuration
   - **Parameters**:
     - `rank_constant`: RRF k parameter (default: 60)
     - `rank_window_size`: RRF window size (default: 100) 
     - `text_boost`: Text retriever boost factor
     - `vector_boost`: Vector retriever boost factor
     - `location_intent`: Optional geographic constraints

#### Key Queries and Features:

1. **`demo_hybrid_search()`**
   - **Type**: RRF-based hybrid search with parallel retrievers
   - **Features**:
     - Native Elasticsearch retriever syntax
     - Multi-field text search with field boosting
     - KNN vector search with configurable candidates
     - RRF fusion with rank_constant=60
     - Source field filtering for performance
   - **Query Structure**:
     ```json
     {
       "retriever": {
         "rrf": {
           "retrievers": [
             {"standard": {"query": {"multi_match": {...}}}},
             {"knn": {"field": "embedding", "query_vector": [...], "k": 50}}
           ],
           "rank_constant": 60,
           "rank_window_size": 100
         }
       }
     }
     ```
   - **Process**:
     1. Generate query embedding using voyage-3 model
     2. Build text search with boosted fields (description^2, features^1.5)
     3. Execute parallel retrievers with RRF fusion
     4. Return ranked results with hybrid scores
   - **Example**: "modern kitchen with stainless steel appliances"
   - **Benefits**: Combines keyword precision with semantic understanding

### `location_aware_demos.py` ⭐ **NEW**
**Purpose**: Location-intelligent hybrid search with 10 diverse real-world scenarios

#### Core Classes:

1. **`LocationAwareSearchExample`**
   - **Purpose**: Structured demo configuration with metadata
   - **Components**:
     - Natural language query with location
     - Location understanding features demonstrated
     - Property search features highlighted
     - Rich console formatting specifications

2. **`LocationAwareDisplayFormatter`**
   - **Purpose**: Rich console display for location search results
   - **Features**:
     - Location information parsing and styling
     - Hybrid score visualization with progress bars
     - Property details formatting
     - Geographic metadata display

#### 10 Location-Aware Demo Scenarios:

1. **`demo_location_aware_waterfront_luxury()`**
   - **Query**: "Luxury waterfront condo in San Francisco"
   - **Features**: City extraction, luxury filtering, waterfront proximity
   - **Location Logic**: city="San Francisco" → term filter on address.city
   - **Property Logic**: semantic understanding of "luxury" + "waterfront"

2. **`demo_location_aware_family_schools()`**
   - **Query**: "Family home near good schools in San Jose California"
   - **Features**: City + state extraction, lifestyle-oriented search
   - **Location Logic**: city="San Jose", state="California" → compound filters
   - **Property Logic**: family home features + school district considerations

3. **`demo_location_aware_urban_modern()`**
   - **Query**: "Modern apartment in Oakland"  
   - **Features**: Urban area understanding, architectural style
   - **Location Logic**: city="Oakland", Bay Area context
   - **Property Logic**: modern architecture + apartment lifestyle

4. **`demo_location_aware_recreation_mountain()`**
   - **Query**: "Investment property in Salinas California"
   - **Features**: Investment focus, market-specific targeting
   - **Location Logic**: city="Salinas", state="California"
   - **Property Logic**: investment criteria + market analysis

5. **`demo_location_aware_historic_urban()`**
   - **Query**: "Historic home in San Francisco CA"
   - **Features**: Historic architecture, city + state extraction
   - **Location Logic**: city="San Francisco", state="CA" normalization
   - **Property Logic**: historic features + character properties

6. **`demo_location_aware_beach_proximity()`**
   - **Query**: "Affordable house in Oakland California"
   - **Features**: Budget constraints, city + state targeting
   - **Location Logic**: geographic filtering for Oakland, CA
   - **Property Logic**: affordability + house type preferences

7. **`demo_location_aware_investment_market()`**
   - **Query**: "Condo with amenities in San Jose"
   - **Features**: Amenity focus, Silicon Valley context
   - **Location Logic**: San Jose tech market understanding
   - **Property Logic**: condo amenities + modern living features

8. **`demo_location_aware_luxury_urban_views()`**
   - **Query**: "Single family home in San Francisco Bay Area"
   - **Features**: Regional search, property type emphasis
   - **Location Logic**: Bay Area region recognition
   - **Property Logic**: single-family characteristics

9. **`demo_location_aware_suburban_architecture()`**
   - **Query**: "Townhouse in Oakland under 800k"
   - **Features**: Price constraints, property type specificity
   - **Location Logic**: Oakland market + price filtering
   - **Property Logic**: townhouse features + value assessment

10. **`demo_location_aware_neighborhood_character()`**
    - **Query**: "Modern condo with parking in San Francisco California"
    - **Features**: Specific amenity requirements, full location specification
    - **Location Logic**: Complete city + state extraction
    - **Property Logic**: modern architecture + parking amenity matching

#### Advanced Features:

- **Location Intent Processing**: DSPy-powered extraction of cities, states, regions
- **Query Cleaning**: Removes location terms for better semantic matching
- **Geographic Filtering**: Builds appropriate Elasticsearch filters
- **Rich Display**: Console formatting with location visualization
- **Showcase Mode**: Runs multiple demos with performance comparison

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
| **Hybrid Search (RRF)** | retriever.rrf | hybrid_search.py | Native RRF fusion of text + vector |
| **Location-Aware Hybrid** | rrf + location filters | location_aware_demos.py | Geographic + semantic + text search |

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

## 🔄 Hybrid Search Execution Flow (RRF)

### Modern Hybrid Search Architecture

#### 1. Query Preparation Phase
```
Input Query: "modern kitchen stainless appliances"
         ↓
Location Extraction: [None] (no location detected)
         ↓
Cleaned Query: "modern kitchen stainless appliances" 
         ↓
Embedding Generation: voyage-3 → [0.123, -0.456, 0.789, ...] (1024-dim)
```

#### 2. Parallel Retriever Execution
```
Text Retriever (BM25):                    Vector Retriever (KNN):
multi_match query on:                      knn query on:
- description^2.0                         - field: "embedding"  
- features^1.5                            - query_vector: [0.123, ...]
- amenities^1.5                           - k: 50
- address.street                          - num_candidates: 100
- address.city                            
- neighborhood.name                       

Results: [doc1, doc3, doc7, doc2, ...]    Results: [doc2, doc1, doc9, doc4, ...]
BM25 Scores: [2.5, 1.8, 1.6, 1.2, ...]   Cosine Scores: [0.85, 0.82, 0.78, ...]
```

#### 3. RRF (Reciprocal Rank Fusion) Algorithm
```
RRF Formula: score = Σ(1 / (rank_constant + rank_i))

Text Rankings:        Vector Rankings:      RRF Combination:
doc1: rank=1         doc2: rank=1          doc1: 1/(60+1) + 1/(60+2) = 0.032
doc3: rank=2         doc1: rank=2          doc2: 1/(60+4) + 1/(60+1) = 0.032  
doc7: rank=3         doc9: rank=3          doc3: 1/(60+2) + 0 = 0.016
doc2: rank=4         doc4: rank=4          doc7: 1/(60+3) + 0 = 0.016

Final Ranking: [doc1, doc2, doc3, doc7, doc9, doc4, ...]
```

#### 4. Modern Retriever Syntax (Elasticsearch 8.15+)
```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "multi_match": {
                "query": "modern kitchen stainless appliances",
                "fields": ["description^2.0", "features^1.5", "amenities^1.5"]
              }
            }
          }
        },
        {
          "knn": {
            "field": "embedding",
            "query_vector": [0.123, -0.456, 0.789, ...],
            "k": 50,
            "num_candidates": 100
          }
        }
      ],
      "rank_constant": 60,
      "rank_window_size": 100
    }
  },
  "size": 10
}
```

### Location-Aware Hybrid Search Flow

#### 1. Enhanced Query Processing
```
Input: "luxury waterfront condo in San Francisco"
         ↓ DSPy Location Extraction
Location Intent: {
  "has_location": true,
  "city": "San Francisco", 
  "state": "California",
  "confidence": 0.95
}
         ↓ Query Cleaning
Cleaned Query: "luxury waterfront condo"
         ↓ Filter Generation  
Location Filters: [
  {"term": {"address.city": "San Francisco"}},
  {"term": {"address.state": "California"}}
]
```

#### 2. Location-Filtered Parallel Execution
```
Text Retriever + Location Filters:        Vector Retriever + Location Filters:
{                                         {
  "bool": {                                "field": "embedding",
    "must": {                              "query_vector": [...],
      "multi_match": {                     "k": 50,
        "query": "luxury waterfront condo", "filter": [
        "fields": ["description^2", ...]     {"term": {"address.city": "San Francisco"}}
      }                                    ]
    },                                   }
    "filter": [
      {"term": {"address.city": "San Francisco"}}
    ]
  }
}
```

#### 3. Geographic-Aware RRF Fusion
```
Both retrievers return only San Francisco properties
         ↓ RRF Algorithm Applied
Combined results maintain location constraints
         ↓ Final Results
Hybrid-ranked San Francisco luxury waterfront condos
```

### Performance Characteristics

| Search Type | Execution Time | Recall | Precision | Use Case |
|-------------|---------------|--------|-----------|----------|
| **Text Only** | ~10ms | High (keywords) | Medium | Exact term matching |
| **Vector Only** | ~15ms | High (semantic) | Medium | Conceptual similarity |
| **Hybrid RRF** | ~25ms | Very High | High | Best of both worlds |
| **Location-Aware Hybrid** | ~35ms | High (filtered) | Very High | Geographic precision |

### RRF Parameter Tuning

#### rank_constant (k) Effects:
- **Low (10-30)**: More aggressive fusion, emphasizes top results
- **Medium (50-70)**: Balanced fusion (recommended default: 60)
- **High (80-100)**: Conservative fusion, preserves original rankings

#### rank_window_size Effects:
- **Small (50)**: Faster but potentially less accurate
- **Medium (100)**: Good balance (recommended default)  
- **Large (200+)**: More thorough but slower

## 💡 Best Practices Demonstrated

1. **Use Appropriate Query Types**
   - Full-text search: `match`, `multi_match`
   - Exact filtering: `term`, `terms`  
   - Complex logic: `bool` query
   - Semantic search: `knn` with dense vectors
   - Best results: `retriever.rrf` hybrid search

2. **Optimize for Performance**
   - Use `filter` context for non-scoring clauses
   - Denormalize for read-heavy workloads
   - Use appropriate field types (keyword vs text)
   - Configure vector dimensions for your use case
   - Tune RRF parameters for your data

3. **Enhance Relevance**
   - Boost important fields (description^2)
   - Use should clauses for optional matches  
   - Configure appropriate analyzers
   - Combine text precision with semantic recall
   - Apply location filtering when relevant

4. **Hybrid Search Best Practices**
   - Use native Elasticsearch RRF (8.15+) over manual fusion
   - Set rank_constant=60 for balanced fusion
   - Configure num_candidates based on accuracy needs
   - Apply filters to both retrievers for consistency
   - Monitor retriever performance separately

5. **Location-Aware Search**
   - Extract location intent before search execution
   - Clean queries by removing location terms
   - Apply geographic filters to all retrievers
   - Handle location ambiguity gracefully
   - Validate extracted locations against known places

6. **Structure for Maintainability**
   - Separate query building from execution
   - Use typed models for responses
   - Document query purposes and RRF parameters
   - Abstract embedding generation into services
   - Test different retriever combinations

## 🎓 Learning Path

1. **Start Simple**: property_queries.py - Basic searches and filtering
2. **Add Logic**: Learn bool queries and complex matching
3. **Explore Text**: wikipedia_fulltext.py - Full-text analysis features  
4. **Analyze Data**: aggregation_queries.py - Statistics and analytics
5. **Go Semantic**: advanced_queries.py - KNN vector search
6. **Master Hybrid**: hybrid_search.py - RRF fusion techniques ⭐
7. **Add Geography**: location_aware_demos.py - Location intelligence ⭐
8. **Optimize**: demo_single_query_relationships.py - Performance patterns

### Recommended Hybrid Search Learning Sequence:

1. **Foundation**: Understand text search and vector search independently
2. **Basic Hybrid**: Start with simple RRF fusion using `hybrid_search.py`
3. **Location Awareness**: Learn geographic query enhancement 
4. **Parameter Tuning**: Experiment with rank_constant and window_size
5. **Production Ready**: Implement error handling and monitoring
6. **Advanced**: Custom retriever combinations and filtering strategies

## 📊 Query Performance Tips

### General Performance
- **Filters before queries**: Apply filters in filter context
- **Limit field count**: Fewer fields to search = faster
- **Use source filtering**: Return only needed fields
- **Cache aggregations**: For repeated analytics
- **Profile queries**: Use `"profile": true` to analyze

### Hybrid Search Optimization
- **Tune num_candidates**: Balance accuracy vs speed (50-200 range)
- **Optimize field boosting**: Test different boost values for your data
- **Filter early**: Apply geographic/category filters to both retrievers
- **Monitor retriever latency**: Text vs vector performance separately
- **Batch embeddings**: Generate query embeddings efficiently
- **Index optimization**: Ensure proper vector field configuration

### Location-Aware Search Tuning  
- **Cache location extraction**: Reuse DSPy results for repeated queries
- **Validate extractions**: Confirm locations against known places
- **Optimize geo filters**: Use appropriate geographic query types
- **Location hierarchies**: Handle city/state/region relationships efficiently

## 🏆 Advanced Hybrid Search Patterns

This demonstration suite provides a comprehensive overview of Elasticsearch query capabilities, from simple text matching to advanced hybrid search with RRF fusion and location intelligence. The hybrid search implementations represent current best practices for production search systems combining:

- **Traditional IR**: BM25 text search with proven relevance
- **Modern AI**: Dense vector embeddings for semantic understanding  
- **Geographic Intelligence**: Location extraction and filtering
- **Optimal Fusion**: Native Elasticsearch RRF for result combination

### Key Innovations Demonstrated:

1. **Native RRF Integration**: Uses Elasticsearch 8.15+ retriever syntax
2. **Location-Aware Processing**: DSPy-powered geographic entity extraction
3. **Production Architecture**: Proper error handling and monitoring
4. **Performance Optimization**: Tuned parameters and filtering strategies
5. **Rich Display**: Console visualization and result formatting

This represents the current state-of-the-art in search technology, combining the precision of traditional search with the intelligence of modern AI systems.