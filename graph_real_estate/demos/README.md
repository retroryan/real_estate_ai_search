# Neo4j Graph Demo Queries Guide

This directory contains comprehensive demonstrations of Neo4j graph database queries showcasing the power of graph relationships for real estate intelligence. Each demo illustrates specific graph patterns, traversal algorithms, and relationship analysis techniques that leverage Neo4j's unique capabilities beyond traditional relational or vector databases.

## 📚 Cypher Query Types and Concepts

### Core Query Patterns Explained

#### 1. **Node Pattern Matching**
- **What it is**: Finding nodes based on labels and properties using graph patterns
- **How it works**:
  - Pattern matching syntax: `(variable:Label {property: value})`
  - Labels act as node types/categories (e.g., Property, Neighborhood, Feature)
  - Properties filter within label sets using exact or range matches
  - Variables capture matched nodes for further processing
- **Pattern structure**:
  ```cypher
  (p:Property {property_type: "Condo"})  // Node with label and property
  (n:Neighborhood)                       // Node with just label
  (:Feature)-[:HAS_FEATURE]->(p)        // Anonymous node in relationship
  ```
- **Use case**: Finding specific entities like properties, neighborhoods, or features
- **Performance**: O(log n) with indexes on labels and properties

#### 2. **Relationship Traversal Queries**
- **What it is**: Following connections between nodes to discover related entities
- **How it works**:
  - Relationship patterns: `-[r:TYPE]->` for directed, `-[r:TYPE]-` for undirected
  - Variable-length paths: `-[:TYPE*1..3]->` traverses 1 to 3 hops
  - Path binding captures entire traversal sequences
  - Breadth-first search by default, configurable traversal strategies
- **Traversal patterns**:
  ```cypher
  (p:Property)-[:LOCATED_IN]->(n:Neighborhood)     // Direct relationship
  (p1:Property)-[:SIMILAR_TO*1..2]-(p2:Property)   // Variable-length path
  path = (p:Property)-[*]-(n:Neighborhood)         // Any path between nodes
  ```
- **Use case**: Finding connected entities, relationship chains, network paths
- **Performance**: O(b^d) where b=branching factor, d=depth

#### 3. **Graph Aggregation Queries**
- **What it is**: Statistical analysis across graph relationships and node sets
- **How it works**:
  - `WITH` clauses create processing pipelines
  - Aggregation functions: count(), avg(), sum(), min(), max(), collect()
  - `GROUP BY` implicit through non-aggregated variables in WITH/RETURN
  - Multi-stage aggregations possible through chained WITH clauses
- **Aggregation patterns**:
  ```cypher
  MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
  WITH n, count(p) as property_count, avg(p.listing_price) as avg_price
  RETURN n.name, property_count, avg_price
  ORDER BY property_count DESC
  ```
- **Use case**: Market statistics, distribution analysis, relationship metrics
- **Performance**: O(n) scan with O(1) aggregation operations

#### 4. **Path Finding Queries**
- **What it is**: Discovering optimal paths between nodes using Neo4j's graph algorithms
- **How it works**:
  - Shortest path: Uses Dijkstra's or A* algorithms
  - All paths: Exhaustive search with optional constraints
  - Path predicates filter during traversal
  - Cost functions weight edges for optimal path calculation
- **Path algorithms**:
  ```cypher
  // Shortest path between properties
  MATCH path = shortestPath((p1:Property)-[*]-(p2:Property))
  WHERE p1.id = 1 AND p2.id = 100
  RETURN path, length(path) as hops
  
  // All paths with constraints
  MATCH path = (p1:Property)-[:SIMILAR_TO*1..3]-(p2:Property)
  WHERE ALL(r IN relationships(path) WHERE r.similarity_score > 0.8)
  RETURN path
  ```
- **Use case**: Connection discovery, optimal routes, influence paths
- **Performance**: O((b^d)/2) for bidirectional search

#### 5. **Neighborhood Subgraph Queries**
- **What it is**: Extracting connected components and local graph structures
- **How it works**:
  - Expands from seed nodes to specified depth
  - Collects nodes and relationships into subgraphs
  - Optional filtering during expansion
  - Returns complete neighborhood structures
- **Subgraph patterns**:
  ```cypher
  MATCH (p:Property {id: 123})
  CALL apoc.path.subgraphAll(p, {
    maxLevel: 2,
    relationshipFilter: "SIMILAR_TO|HAS_FEATURE"
  })
  YIELD nodes, relationships
  RETURN nodes, relationships
  ```
- **Use case**: Local graph exploration, impact analysis, cluster extraction
- **Performance**: O(b^d) with early termination optimizations

#### 6. **Similarity and Recommendation Queries**
- **What it is**: Finding similar entities based on shared relationships and properties
- **How it works**:
  - Collaborative filtering through shared connections
  - Jaccard similarity on feature sets
  - Weighted similarity scores from multiple factors
  - Vector similarity using stored embeddings
- **Similarity patterns**:
  ```cypher
  // Feature-based similarity
  MATCH (p1:Property)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(p2:Property)
  WHERE p1.id = 123
  WITH p2, count(f) as shared_features, 
       collect(f.name) as features
  RETURN p2, shared_features, 
         shared_features * 1.0 / p2.total_features as jaccard_similarity
  ORDER BY shared_features DESC
  ```
- **Use case**: Property recommendations, similar listings, market comparables
- **Performance**: O(n*m) where n=nodes, m=average connections

#### 7. **Temporal Graph Queries**
- **What it is**: Analyzing changes and patterns over time in graph structures
- **How it works**:
  - Time-based filtering on relationship properties
  - Temporal ordering of events and changes
  - Time-window aggregations
  - Historical path analysis
- **Temporal patterns**:
  ```cypher
  MATCH (p:Property)-[s:SOLD]->(b:Buyer)
  WHERE s.date >= date('2023-01-01')
  WITH p, s.price as sale_price, s.date as sale_date
  ORDER BY sale_date
  RETURN p.address, sale_price, sale_date,
         sale_price - p.original_price as appreciation
  ```
- **Use case**: Market trends, price evolution, seasonal patterns
- **Performance**: O(n log n) with temporal indexes

#### 8. **Graph Pattern Detection**
- **What it is**: Identifying specific structural patterns within the graph
- **How it works**:
  - Complex MATCH patterns define structures
  - WHERE clauses add semantic constraints
  - Pattern comprehension for collection
  - Negative patterns with NOT EXISTS
- **Pattern detection examples**:
  ```cypher
  // Triangle patterns (mutual connections)
  MATCH (p1:Property)-[:SIMILAR_TO]-(p2:Property),
        (p2)-[:SIMILAR_TO]-(p3:Property),
        (p3)-[:SIMILAR_TO]-(p1)
  WHERE p1.id < p2.id < p3.id  // Avoid duplicates
  RETURN p1, p2, p3 as similarity_triangle
  
  // Hub detection (highly connected nodes)
  MATCH (p:Property)-[r:SIMILAR_TO]-()
  WITH p, count(r) as connections
  WHERE connections > 10
  RETURN p as hub_property, connections
  ```
- **Use case**: Community detection, anomaly identification, structural analysis
- **Performance**: O(n^k) for k-node patterns, optimizable with indexes

#### 9. **Hybrid Vector-Graph Queries**
- **What it is**: Combining Neo4j's native vector search with graph relationships
- **How it works**:
  - Vector indexes on node properties (1024-dim embeddings)
  - Cosine similarity for semantic matching
  - Graph boosting adjusts vector scores
  - Relationship-aware reranking
- **Hybrid patterns**:
  ```cypher
  // Vector search with graph boost
  CALL db.index.vector.queryNodes('propertyEmbeddings', 50, $queryVector)
  YIELD node as p, score as vector_score
  MATCH (p)-[r:SIMILAR_TO]-(similar:Property)
  WITH p, vector_score, count(similar) as graph_connections
  RETURN p, vector_score * (1 + log(1 + graph_connections)) as hybrid_score
  ORDER BY hybrid_score DESC
  ```
- **Use case**: Semantic search with relationship context, enhanced recommendations
- **Performance**: O(log n) vector search + O(m) graph traversal

#### 10. **Complex Aggregation Pipelines**
- **What it is**: Multi-stage data processing combining graph traversal with analytics
- **How it works**:
  - Sequential WITH clauses create processing stages
  - Each stage can filter, aggregate, or transform
  - UNWIND expands collections for processing
  - CASE expressions for conditional logic
- **Pipeline example**:
  ```cypher
  // Multi-level market analysis
  MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
  WITH c, n, count(p) as properties_in_neighborhood, 
       avg(p.listing_price) as neighborhood_avg_price
  WITH c, collect({
    neighborhood: n.name, 
    count: properties_in_neighborhood,
    avg_price: neighborhood_avg_price
  }) as neighborhoods
  RETURN c.name as city,
         size(neighborhoods) as total_neighborhoods,
         reduce(s = 0, n IN neighborhoods | s + n.count) as total_properties,
         reduce(s = 0.0, n IN neighborhoods | s + n.avg_price) / size(neighborhoods) as city_avg_price
  ORDER BY total_properties DESC
  ```
- **Use case**: Hierarchical analytics, market intelligence, complex reporting
- **Performance**: O(n) with efficient aggregation algorithms

## 📁 Demo Files Overview

### `demo_1_hybrid_search.py` & `demo_1_hybrid_search_simple.py`
**Purpose**: Advanced hybrid search combining semantic vectors with graph intelligence

#### Core Components:

1. **`AdvancedHybridSearchDemo`**
   - **Purpose**: Production-ready hybrid search with graph-boosted scoring
   - **Features**:
     - 1024-dimensional voyage-3 embeddings with Neo4j vector indexes
     - Graph similarity relationships for result reranking
     - Feature correlation analysis for semantic enhancement
     - Lifestyle-based neighborhood matching
     - Multi-criteria scoring with configurable weights
   - **Key Methods**:
     - `search()`: Execute hybrid vector + graph search
     - `_boost_with_graph()`: Apply relationship-based score adjustments
     - `_calculate_similarity()`: Compute multi-factor similarity scores
   
2. **Graph-Boosted Scoring Algorithm**
   ```cypher
   // Vector search baseline
   CALL db.index.vector.queryNodes('propertyEmbeddings', $k, $queryVector)
   YIELD node, score as vector_score
   
   // Graph relationship boost
   MATCH (node)-[r:SIMILAR_TO]-(similar:Property)
   WHERE r.overall_score > 0.7
   WITH node, vector_score, avg(r.overall_score) as avg_similarity
   
   // Feature correlation boost
   MATCH (node)-[:HAS_FEATURE]->(f:Feature)
   WHERE f.name IN $desired_features
   WITH node, vector_score, avg_similarity, count(f) as matching_features
   
   // Combined hybrid score
   RETURN node,
          vector_score * 0.5 +                    // Semantic similarity
          avg_similarity * 0.3 +                  // Graph relationships
          (matching_features * 1.0 / 10) * 0.2    // Feature matching
          as hybrid_score
   ORDER BY hybrid_score DESC
   ```

#### Database Context:
- 420 properties with voyage-3 embeddings (1024-dim)
- 20,000+ property similarity relationships
- 3,257+ feature relationships across 416 features
- 62,380+ geographic proximity relationships
- Vector index with HNSW algorithm for sub-linear search

### `demo_2_graph_analysis.py`
**Purpose**: Deep graph relationship analysis and pattern discovery

#### Analysis Categories:

1. **Property Relationship Networks**
   ```cypher
   // Similarity clusters
   MATCH (p1:Property)-[r:SIMILAR_TO]-(p2:Property)
   WHERE r.overall_score > 0.85
   WITH p1, collect(p2) as similar_properties, avg(r.overall_score) as avg_similarity
   WHERE size(similar_properties) > 5
   RETURN p1 as cluster_center, 
          size(similar_properties) as cluster_size,
          avg_similarity
   ORDER BY cluster_size DESC
   ```

2. **Feature Co-occurrence Analysis**
   ```cypher
   // Feature correlation discovery
   MATCH (f1:Feature)<-[:HAS_FEATURE]-(p:Property)-[:HAS_FEATURE]->(f2:Feature)
   WHERE id(f1) < id(f2)
   WITH f1, f2, count(p) as co_occurrence_count
   WHERE co_occurrence_count > 10
   RETURN f1.name, f2.name, co_occurrence_count,
          co_occurrence_count * 1.0 / 420 as correlation_strength
   ORDER BY co_occurrence_count DESC
   ```

3. **Geographic Hierarchy Analysis**
   ```cypher
   // Multi-level geographic aggregation
   MATCH path = (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)-[:IN_COUNTY]->(county:County)
   WITH c, n, count(p) as property_count,
        avg(p.listing_price) as avg_price,
        collect(DISTINCT p.property_type) as property_types
   RETURN c.name as city,
          n.name as neighborhood,
          property_count,
          round(avg_price) as avg_price,
          property_types
   ORDER BY c.name, property_count DESC
   ```

4. **Market Segment Discovery**
   ```cypher
   // Identify market segments through graph patterns
   MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
   WHERE f.category = 'Luxury'
   WITH p, count(f) as luxury_features
   WHERE luxury_features > 5
   MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
   WITH n, count(p) as luxury_property_count, avg(p.listing_price) as avg_luxury_price
   RETURN n.name as neighborhood,
          luxury_property_count,
          round(avg_luxury_price) as avg_price,
          round(avg_luxury_price / luxury_property_count) as price_per_luxury_property
   ORDER BY luxury_property_count DESC
   ```

### `demo_3_market_intelligence.py`
**Purpose**: Advanced market analytics using graph algorithms

#### Intelligence Modules:

1. **Geographic Market Analysis**
   ```cypher
   // City-level market dynamics
   MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
   WITH n.city as city, 
        count(p) as total_properties,
        avg(p.listing_price) as avg_price,
        avg(p.price_per_sqft) as avg_price_per_sqft,
        percentileCont(p.listing_price, 0.5) as median_price,
        stdev(p.listing_price) as price_volatility
   RETURN city,
          total_properties,
          round(avg_price) as avg_price,
          round(median_price) as median_price,
          round(avg_price_per_sqft) as avg_psf,
          round(price_volatility / avg_price * 100) as volatility_percent
   ORDER BY total_properties DESC
   ```

2. **Feature Impact Analysis**
   ```cypher
   // Quantify feature value contribution
   MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
   WITH f, avg(p.listing_price) as avg_price_with_feature, count(p) as properties_with_feature
   MATCH (p2:Property)
   WHERE NOT EXISTS((p2)-[:HAS_FEATURE]->(f))
   WITH f, avg_price_with_feature, properties_with_feature, avg(p2.listing_price) as avg_price_without_feature
   RETURN f.name as feature,
          f.category,
          properties_with_feature,
          round(avg_price_with_feature) as avg_with,
          round(avg_price_without_feature) as avg_without,
          round(avg_price_with_feature - avg_price_without_feature) as premium,
          round((avg_price_with_feature - avg_price_without_feature) / avg_price_without_feature * 100) as premium_percent
   WHERE properties_with_feature > 10
   ORDER BY premium DESC
   ```

3. **Investment Opportunity Discovery**
   ```cypher
   // Find undervalued properties using graph intelligence
   MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
   WITH n, avg(p.listing_price) as neighborhood_avg_price, 
        avg(p.price_per_sqft) as neighborhood_avg_psf
   MATCH (candidate:Property)-[:LOCATED_IN]->(n)
   WHERE candidate.listing_price < neighborhood_avg_price * 0.85
   WITH candidate, n, neighborhood_avg_price, neighborhood_avg_psf,
        (neighborhood_avg_price - candidate.listing_price) as potential_appreciation
   MATCH (candidate)-[:HAS_FEATURE]->(f:Feature)
   WHERE f.category IN ['Luxury', 'Premium']
   WITH candidate, n, potential_appreciation, count(f) as premium_features
   WHERE premium_features > 3
   RETURN candidate.address as address,
          n.name as neighborhood,
          candidate.listing_price as current_price,
          round(potential_appreciation) as upside_potential,
          round(potential_appreciation / candidate.listing_price * 100) as roi_percent,
          premium_features
   ORDER BY roi_percent DESC
   LIMIT 10
   ```

4. **Lifestyle Market Segmentation**
   ```cypher
   // Analyze lifestyle preferences and market segments
   MATCH (n:Neighborhood)
   WHERE size(n.lifestyle_tags) > 0
   UNWIND n.lifestyle_tags as lifestyle
   WITH lifestyle, collect(n) as neighborhoods
   MATCH (p:Property)-[:LOCATED_IN]->(n)
   WHERE n IN neighborhoods
   WITH lifestyle, count(DISTINCT p) as property_count, 
        avg(p.listing_price) as avg_price,
        collect(DISTINCT n.name) as neighborhood_names
   RETURN lifestyle,
          property_count,
          round(avg_price) as avg_price,
          size(neighborhood_names) as neighborhoods_count,
          neighborhood_names[0..3] as sample_neighborhoods
   ORDER BY property_count DESC
   ```

### `demo_4_wikipedia_enhanced.py`
**Purpose**: Enriching property data with Wikipedia knowledge graphs

#### Knowledge Integration Patterns:

1. **Geographic Knowledge Enhancement**
   ```cypher
   // Link properties to Wikipedia geographic articles
   MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
   MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n)
   WHERE w.relationship_type = 'primary'
   RETURN p.address as property,
          n.name as neighborhood,
          w.title as wikipedia_article,
          w.summary as area_description,
          w.categories as knowledge_categories
   ```

2. **Cultural Context Integration**
   ```cypher
   // Find cultural venues near properties
   MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
   MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n)
   WHERE ANY(cat IN w.categories WHERE cat CONTAINS 'Museums' OR cat CONTAINS 'Culture')
   WITH p, collect({
     title: w.title,
     type: CASE 
       WHEN 'Museums' IN w.categories THEN 'Museum'
       WHEN 'Theaters' IN w.categories THEN 'Theater'
       ELSE 'Cultural Venue'
     END,
     summary: substring(w.summary, 0, 200)
   }) as cultural_venues
   WHERE size(cultural_venues) > 0
   RETURN p.address, p.listing_price, cultural_venues
   ORDER BY size(cultural_venues) DESC
   ```

### `demo_5_pure_vector_search.py`
**Purpose**: Native Neo4j vector search capabilities

#### Vector Search Patterns:

1. **Semantic Property Search**
   ```cypher
   // Pure vector similarity search
   CALL db.index.vector.queryNodes(
     'propertyEmbeddings',     // Index name
     10,                        // Number of results
     $queryEmbedding           // 1024-dimensional query vector
   )
   YIELD node as property, score
   RETURN property.address,
          property.description,
          property.listing_price,
          score as similarity_score
   ORDER BY score DESC
   ```

2. **Vector Search with Filters**
   ```cypher
   // Filtered vector search
   CALL db.index.vector.queryNodes('propertyEmbeddings', 50, $queryVector)
   YIELD node as p, score
   WHERE p.listing_price >= 500000 AND p.listing_price <= 1000000
   AND p.property_type = 'Condo'
   MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
   WHERE n.city = 'San Francisco'
   RETURN p, score, n.name as neighborhood
   ORDER BY score DESC
   LIMIT 10
   ```

### `demo_6_advanced_path_search.py`
**Purpose**: Complex path finding and graph traversal algorithms

#### Path Finding Patterns:

1. **Multi-Hop Similarity Paths**
   ```cypher
   // Find connection paths between properties
   MATCH path = (p1:Property)-[:SIMILAR_TO*1..3]-(p2:Property)
   WHERE p1.id = $source_id AND p2.id = $target_id
   WITH path, relationships(path) as rels
   WHERE ALL(r IN rels WHERE r.overall_score > 0.7)
   RETURN path,
          length(path) as hops,
          reduce(score = 1.0, r IN rels | score * r.overall_score) as path_score
   ORDER BY path_score DESC
   LIMIT 5
   ```

2. **Influence Propagation Analysis**
   ```cypher
   // Analyze how property changes affect the market
   MATCH (source:Property {id: $property_id})
   CALL apoc.path.expandConfig(source, {
     relationshipFilter: "SIMILAR_TO",
     minLevel: 1,
     maxLevel: 3,
     uniqueness: "NODE_GLOBAL"
   })
   YIELD path
   WITH path, last(nodes(path)) as influenced_property,
        reduce(score = 1.0, r IN relationships(path) | score * r.overall_score) as influence_score
   WHERE influence_score > 0.5
   RETURN influenced_property.address,
          length(path) as degrees_of_separation,
          round(influence_score * 100) as influence_percent
   ORDER BY influence_score DESC
   ```

## 🎯 Query Pattern Showcase

### Graph Traversal Patterns

| Pattern | Query Type | Demo File | Example |
|---------|------------|-----------|---------|
| **Direct Relationships** | Single-hop traversal | demo_2_graph_analysis.py | `(p:Property)-[:LOCATED_IN]->(n:Neighborhood)` |
| **Variable-Length Paths** | Multi-hop traversal | demo_6_advanced_path_search.py | `(p1)-[:SIMILAR_TO*1..3]-(p2)` |
| **Path Finding** | Shortest path algorithms | demo_6_advanced_path_search.py | `shortestPath((p1)-[*]-(p2))` |
| **Subgraph Extraction** | Neighborhood expansion | demo_2_graph_analysis.py | `apoc.path.subgraphAll()` |
| **Pattern Detection** | Structural matching | demo_2_graph_analysis.py | Triangle/hub patterns |

### Aggregation and Analytics

| Pattern | Query Type | Demo File | Example |
|---------|------------|-----------|---------|
| **Multi-Level Aggregation** | Hierarchical grouping | demo_3_market_intelligence.py | City → Neighborhood → Property |
| **Statistical Analysis** | Distribution metrics | demo_3_market_intelligence.py | percentiles, stdev, correlation |
| **Time-Series Analysis** | Temporal patterns | demo_3_market_intelligence.py | Price trends over time |
| **Graph Metrics** | Centrality, clustering | demo_2_graph_analysis.py | Degree centrality, clustering coefficient |

### Hybrid Search Patterns

| Pattern | Query Type | Demo File | Example |
|---------|------------|-----------|---------|
| **Vector + Graph** | Hybrid scoring | demo_1_hybrid_search.py | Vector similarity with relationship boost |
| **Semantic + Features** | Multi-modal search | demo_1_hybrid_search.py | Embeddings plus feature matching |
| **Location-Aware Vector** | Geo-filtered semantic | demo_5_pure_vector_search.py | Vector search within geographic bounds |
| **Graph-Boosted Ranking** | Relationship reranking | demo_1_hybrid_search.py | Adjust scores based on connections |

### Advanced Neo4j Features

| Feature | Query Function | Demo File | Use Case |
|---------|---------------|-----------|----------|
| **Vector Indexes** | `db.index.vector.queryNodes()` | demo_5_pure_vector_search.py | Semantic similarity search |
| **APOC Procedures** | `apoc.path.*` | demo_6_advanced_path_search.py | Advanced path operations |
| **Graph Data Science** | `gds.*` | Not shown | Community detection, PageRank |
| **Full-Text Search** | `db.index.fulltext.queryNodes()` | Not shown | Text search across properties |

## 🚀 Query Execution Flow

### 1. Pattern Matching Phase
```
MATCH pattern:
(p:Property {property_type: "Condo"})-[:LOCATED_IN]->(n:Neighborhood)
         ↓ Label Index Lookup
    Scan Property nodes where property_type = "Condo"
         ↓ Relationship Traversal  
    Follow LOCATED_IN edges to Neighborhood nodes
         ↓ Pattern Validation
    Verify complete pattern matches
```

### 2. Filtering and Projection
```
WHERE clauses:
p.listing_price > 500000 AND n.city = "San Francisco"
         ↓ Property Filter
    Filter properties by price predicate
         ↓ Traversal Filter
    Filter neighborhoods by city
         ↓ Result Projection
    Keep only matching subgraphs
```

### 3. Aggregation Pipeline
```
WITH aggregations:
WITH n, count(p) as property_count, avg(p.listing_price) as avg_price
         ↓ Grouping
    Group by neighborhood (n)
         ↓ Aggregation Functions
    Count properties, calculate average
         ↓ Pipeline Output
    Pass results to next stage
```

## 🧠 Neo4j Vector Search Architecture

### Vector Index Creation
```cypher
// Create vector index for property embeddings
CALL db.index.vector.createNodeIndex(
  'propertyEmbeddings',           // Index name
  'Property',                      // Node label
  'embedding',                     // Property name
  1024,                           // Vector dimensions
  'cosine'                        // Similarity function
)
```

### Vector Search Pipeline
```
1. Query Embedding Generation:
   "modern waterfront home" → voyage-3 model → [0.123, -0.456, ...] (1024-dim)

2. Neo4j Vector Index Search:
   CALL db.index.vector.queryNodes('propertyEmbeddings', 10, $queryVector)
   ↓ HNSW Algorithm (Hierarchical Navigable Small World)
   ↓ Approximate Nearest Neighbor Search
   ↓ Cosine Similarity Scoring

3. Graph-Enhanced Reranking:
   Vector Results → Graph Relationships → Boosted Scores → Final Ranking
```

### Why Neo4j for Graph + Vector?

1. **Unified Data Model**: Properties, relationships, and vectors in one database
2. **Graph Context**: Vector results enhanced with relationship intelligence
3. **Complex Traversals**: Combine semantic search with graph algorithms
4. **ACID Compliance**: Transactional consistency for all operations
5. **Native Storage**: Optimized for both graph traversal and vector operations

## 🔄 Graph-Enhanced Hybrid Search

### Multi-Stage Hybrid Pipeline

#### Stage 1: Vector Retrieval
```cypher
// Initial semantic search
CALL db.index.vector.queryNodes('propertyEmbeddings', 50, $queryVector)
YIELD node as p, score as vector_score
WITH p, vector_score
```

#### Stage 2: Graph Intelligence Layer
```cypher
// Enhance with relationship data
MATCH (p)-[sim:SIMILAR_TO]-(similar:Property)
WHERE sim.overall_score > 0.8
WITH p, vector_score, avg(sim.overall_score) as relationship_score, 
     count(similar) as connection_count
```

#### Stage 3: Feature Correlation
```cypher
// Boost based on matching features
MATCH (p)-[:HAS_FEATURE]->(f:Feature)
WHERE f.name IN $desired_features
WITH p, vector_score, relationship_score, connection_count,
     count(f) as matching_features
```

#### Stage 4: Hybrid Scoring
```cypher
// Combine all signals
WITH p,
     vector_score * 0.4 +                                    // Semantic similarity
     relationship_score * 0.3 +                              // Graph relationships
     (matching_features * 1.0 / $total_features) * 0.2 +    // Feature matching
     (log(1 + connection_count) / 10) * 0.1                 // Network effect
     as hybrid_score
RETURN p, hybrid_score
ORDER BY hybrid_score DESC
```

### Performance Characteristics

| Operation | Complexity | Optimization | Use Case |
|-----------|------------|--------------|----------|
| **Node Lookup** | O(log n) | Label & property indexes | Fast entity retrieval |
| **Relationship Traversal** | O(b^d) | Relationship indexes, early termination | Path finding |
| **Vector Search** | O(log n) | HNSW algorithm | Semantic similarity |
| **Aggregation** | O(n) | Parallel execution | Analytics |
| **Path Finding** | O(b^d/2) | Bidirectional search | Shortest paths |
| **Pattern Matching** | O(n^k) | Index-backed traversal | Structure detection |

## 💡 Best Practices Demonstrated

### 1. **Query Optimization**
   - Use indexes for starting points: `CREATE INDEX ON :Property(id)`
   - Limit traversal depth: `[:SIMILAR_TO*1..3]` not `[:SIMILAR_TO*]`
   - Filter early in the query: WHERE clauses before MATCH when possible
   - Use PROFILE to analyze query plans: `PROFILE MATCH ...`

### 2. **Relationship Design**
   - Store computed scores in relationships: `SIMILAR_TO.overall_score`
   - Use relationship properties for filtering: `WHERE r.score > 0.8`
   - Design for traversal patterns: directed vs undirected relationships
   - Create specific relationship types: `LOCATED_IN` vs generic `RELATED_TO`

### 3. **Aggregation Patterns**
   - Use WITH for multi-stage processing pipelines
   - Collect before complex operations: `collect(p) as properties`
   - Leverage reduce() for accumulation: `reduce(s = 0, x IN list | s + x)`
   - Use UNWIND for array processing: `UNWIND $batch as item`

### 4. **Vector Integration**
   - Maintain embedding consistency: same model for all vectors
   - Index high-dimensional vectors: 1024-dim voyage-3 embeddings
   - Combine vector and graph scores: hybrid ranking algorithms
   - Pre-filter for efficiency: apply constraints before vector search

### 5. **Performance Tuning**
   - Batch operations: `UNWIND $batch AS item CREATE (p:Property) SET p = item`
   - Use EXPLAIN to understand query plans without execution
   - Leverage query caching for repeated patterns
   - Monitor with query logging: `dbms.logs.query.enabled=true`

### 6. **Graph Algorithm Usage**
   - Use built-in algorithms when available: `shortestPath()`, `allShortestPaths()`
   - Consider APOC for advanced operations: `apoc.path.expandConfig()`
   - Implement custom algorithms with Cypher: PageRank, community detection
   - Use Graph Data Science library for ML: node embeddings, link prediction

## 🎓 Learning Path

1. **Start with Basics**: demo_2_graph_analysis.py - Fundamental traversals
2. **Learn Aggregations**: demo_3_market_intelligence.py - Analytics patterns
3. **Explore Paths**: demo_6_advanced_path_search.py - Graph algorithms
4. **Add Vectors**: demo_5_pure_vector_search.py - Semantic search
5. **Master Hybrid**: demo_1_hybrid_search.py - Combined intelligence
6. **Knowledge Graphs**: demo_4_wikipedia_enhanced.py - External data integration

### Recommended Neo4j Learning Sequence:

1. **Foundation**: Node and relationship patterns, basic MATCH queries
2. **Traversals**: Variable-length paths, path finding algorithms
3. **Aggregations**: WITH pipelines, statistical functions
4. **Optimization**: Indexes, query planning, performance tuning
5. **Vectors**: Creating indexes, similarity search, hybrid patterns
6. **Advanced**: APOC procedures, Graph Data Science, custom algorithms

## 📊 Query Performance Guidelines

### Index Strategy
```cypher
// Essential indexes for performance
CREATE INDEX property_id FOR (p:Property) ON (p.id);
CREATE INDEX property_type FOR (p:Property) ON (p.property_type);
CREATE INDEX neighborhood_name FOR (n:Neighborhood) ON (n.name);
CREATE INDEX feature_name FOR (f:Feature) ON (f.name);
CREATE INDEX feature_category FOR (f:Feature) ON (f.category);

// Composite indexes for complex queries
CREATE INDEX property_location FOR (p:Property) ON (p.city, p.property_type);

// Vector index for semantic search
CALL db.index.vector.createNodeIndex(
  'propertyEmbeddings', 'Property', 'embedding', 1024, 'cosine'
);
```

### Query Optimization Checklist

- ✅ **Use parameters**: `$param` instead of literal values for query caching
- ✅ **Limit result sets**: Add LIMIT clauses to prevent large returns
- ✅ **Profile queries**: Use PROFILE to identify bottlenecks
- ✅ **Index backing**: Ensure starting points use indexes
- ✅ **Avoid cartesian products**: Use directed traversals
- ✅ **Filter early**: Apply WHERE clauses as soon as possible
- ✅ **Batch operations**: Process multiple items in single transactions

### Memory Management
```cypher
// Configure heap memory for large graph operations
dbms.memory.heap.initial_size=4g
dbms.memory.heap.max_size=8g
dbms.memory.pagecache.size=4g

// Query memory limits
dbms.memory.transaction.global_max_size=2g
cypher.query_max_allocations=1000000000
```

## 🏆 Advanced Graph Patterns

This demonstration suite showcases Neo4j's unique capabilities for real estate intelligence:

### Key Innovations:

1. **Graph-Native Design**: Relationships as first-class citizens
2. **Vector Integration**: Native support for high-dimensional embeddings
3. **Hybrid Intelligence**: Combining structural and semantic understanding
4. **Performance at Scale**: Optimized for millions of nodes and relationships
5. **Complex Analytics**: Multi-hop traversals and graph algorithms
6. **Knowledge Integration**: Connecting property data with external knowledge

### Why Neo4j for Real Estate?

- **Relationship Complexity**: Model complex property relationships naturally
- **Pattern Discovery**: Find hidden connections and market patterns
- **Semantic Understanding**: Combine graph structure with AI embeddings
- **Real-Time Analysis**: Fast traversals for interactive applications
- **Flexible Schema**: Evolve data model without migrations
- **Graph Algorithms**: Built-in algorithms for recommendations and analysis

This represents the cutting edge of graph database technology for real estate, combining the mathematical rigor of graph theory with the intelligence of modern AI systems.