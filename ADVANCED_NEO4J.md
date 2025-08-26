# Advanced Neo4j Relationship Creation Patterns

## Executive Summary

This document details how to migrate all relationship creation logic from Spark DataFrames to Neo4j Cypher queries, following the proven patterns from graph-real-estate. By moving graph operations to Neo4j where they belong, we achieve dramatic simplification, better performance, and maintainable code.

## Core Philosophy

**Neo4j is a graph database. Let it do graph operations.**

Spark should only prepare and clean data. All relationship logic, similarity calculations, geographic matching, and graph traversals should happen in Neo4j using Cypher queries.

## Relationship Migration Patterns

### 1. SIMILAR_TO - Property Similarity Network

#### Current Approach (Failing in Spark)
The current implementation attempts complex DataFrame operations with multiple joins, broadcast operations, and nested conditionals that produce scores below threshold due to logic errors.

#### Neo4j Approach (Proven in graph-real-estate)
Calculate similarity directly in Cypher during relationship creation. The database handles the cross-product efficiently with proper indexing.

**Implementation Pattern:**
```cypher
// Step 1: Create indexes for performance
CREATE INDEX property_city IF NOT EXISTS FOR (p:Property) ON (p.city);
CREATE INDEX property_price IF NOT EXISTS FOR (p:Property) ON (p.listing_price);
CREATE INDEX property_type IF NOT EXISTS FOR (p:Property) ON (p.property_type);

// Step 2: Create SIMILAR_TO relationships with inline calculation
CALL apoc.periodic.iterate(
  // First query: Get all property pairs in same city
  "MATCH (p1:Property), (p2:Property)
   WHERE p1.listing_id < p2.listing_id 
   AND p1.city = p2.city
   RETURN p1, p2",
   
  // Second query: Calculate similarity and create relationship
  "WITH p1, p2,
   
   // Price similarity (40% weight)
   CASE 
     WHEN abs(p1.listing_price - p2.listing_price) / p1.listing_price < 0.2 THEN 0.4
     WHEN abs(p1.listing_price - p2.listing_price) / p1.listing_price < 0.4 THEN 0.2
     ELSE 0.0
   END as price_score,
   
   // Bedroom similarity (30% weight)  
   CASE
     WHEN p1.bedrooms = p2.bedrooms THEN 0.3
     WHEN abs(p1.bedrooms - p2.bedrooms) = 1 THEN 0.15
     ELSE 0.0
   END as bedroom_score,
   
   // Size similarity (30% weight)
   CASE
     WHEN p1.square_feet IS NOT NULL AND p2.square_feet IS NOT NULL THEN
       CASE
         WHEN abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.15 THEN 0.3
         WHEN abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.3 THEN 0.15
         ELSE 0.0
       END
     ELSE 0.15
   END as size_score
   
   WITH p1, p2, (price_score + bedroom_score + size_score) as similarity
   WHERE similarity >= 0.5
   
   CREATE (p1)-[:SIMILAR_TO {score: similarity}]->(p2)
   CREATE (p2)-[:SIMILAR_TO {score: similarity}]->(p1)",
   
  {batchSize: 1000, parallel: true}
)
```

**Key Advantages:**
- Calculation happens where the data lives
- No data movement between systems
- Leverages Neo4j's optimized graph algorithms
- Bidirectional relationships created atomically
- Easy to tune thresholds and weights

**Performance Optimization:**
- Use APOC's periodic.iterate for batching
- Create indexes on comparison fields
- Filter early to reduce cross-product
- Use parallel processing for large datasets

### 2. NEAR - Neighborhood Proximity Network

#### Current Approach (Failing in Spark)
Expects nested coordinate structures and performs complex Haversine distance calculations that fail due to missing coordinate data.

#### Neo4j Approach (Simple and Working)
Connect neighborhoods in the same city. Geographic proximity is implicit in city membership.

**Implementation Pattern:**
```cypher
// Step 1: Ensure indexes exist
CREATE INDEX neighborhood_city IF NOT EXISTS FOR (n:Neighborhood) ON (n.city);

// Step 2: Create NEAR relationships for neighborhoods in same city
MATCH (n1:Neighborhood), (n2:Neighborhood)
WHERE n1.neighborhood_id < n2.neighborhood_id
AND n1.city = n2.city
MERGE (n1)-[:NEAR]->(n2)
MERGE (n2)-[:NEAR]->(n1)
```

**Advanced Pattern with Distance (if coordinates available):**
```cypher
// Only if coordinates exist and distance matters
MATCH (n1:Neighborhood), (n2:Neighborhood)
WHERE n1.neighborhood_id < n2.neighborhood_id
AND n1.city = n2.city
AND n1.latitude IS NOT NULL AND n1.longitude IS NOT NULL
AND n2.latitude IS NOT NULL AND n2.longitude IS NOT NULL
WITH n1, n2,
  point.distance(
    point({latitude: n1.latitude, longitude: n1.longitude}),
    point({latitude: n2.latitude, longitude: n2.longitude})
  ) / 1000 as distance_km
WHERE distance_km <= 5.0
CREATE (n1)-[:NEAR {distance_km: distance_km}]->(n2)
CREATE (n2)-[:NEAR {distance_km: distance_km}]->(n1)
```

### 3. DESCRIBES - Wikipedia to Neighborhood Connections

#### Current Approach (Failing in Spark)
Complex geographic matching with "best_city" fields that don't exist, multiple join strategies, and fallback logic.

#### Neo4j Approach (Direct Matching)
Simple field matching on existing data.

**Implementation Pattern:**
```cypher
// Step 1: Direct neighborhood_id matching (if available in Wikipedia data)
MATCH (w:WikipediaArticle)
WHERE w.neighborhood_id IS NOT NULL
MATCH (n:Neighborhood {neighborhood_id: w.neighborhood_id})
MERGE (w)-[:DESCRIBES {confidence: 0.95, method: 'direct'}]->(n)

// Step 2: City-level matching fallback
MATCH (w:WikipediaArticle)
WHERE w.city IS NOT NULL AND w.neighborhood_id IS NULL
MATCH (n:Neighborhood)
WHERE n.city = w.city
MERGE (w)-[:DESCRIBES {confidence: 0.7, method: 'city_match'}]->(n)

// Step 3: Title matching for specific neighborhoods
MATCH (w:WikipediaArticle)
MATCH (n:Neighborhood)
WHERE w.title CONTAINS n.name
OR n.name CONTAINS w.title
MERGE (w)-[:DESCRIBES {confidence: 0.8, method: 'title_match'}]->(n)
```

### 4. HAS_FEATURE - Property to Feature Connections

#### Current Approach (Working but Complex)
Uses explode operations and broadcast joins in Spark.

#### Neo4j Approach (Simple and Efficient)
Direct relationship creation during property import.

**Implementation Pattern:**
```cypher
// Step 1: Create all features from unique list
UNWIND $features as feature
MERGE (f:Feature {name: feature.name})
SET f.category = feature.category

// Step 2: Connect properties to features
UNWIND $property_features as pf
MATCH (p:Property {listing_id: pf.property_id})
MATCH (f:Feature {name: pf.feature_name})
MERGE (p)-[:HAS_FEATURE]->(f)
```

**Batch Processing Pattern:**
```cypher
CALL apoc.periodic.iterate(
  "UNWIND $batch as row RETURN row",
  "MATCH (p:Property {listing_id: row.property_id})
   MATCH (f:Feature {name: row.feature_name})
   MERGE (p)-[:HAS_FEATURE]->(f)",
  {batchSize: 5000, parallel: true, params: {batch: $property_feature_pairs}}
)
```

### 5. IN_PRICE_RANGE - Price Range Assignment

#### Current Approach (Complex Cross-Join)
Cross-joins all properties with all price ranges and filters.

#### Neo4j Approach (Direct Calculation)
Calculate range during relationship creation.

**Implementation Pattern:**
```cypher
// Step 1: Create price ranges
CREATE (pr1:PriceRange {id: 'under_500k', label: 'Under $500k', min: 0, max: 500000})
CREATE (pr2:PriceRange {id: '500k_1m', label: '$500k-$1M', min: 500000, max: 1000000})
CREATE (pr3:PriceRange {id: '1m_2m', label: '$1M-$2M', min: 1000000, max: 2000000})
CREATE (pr4:PriceRange {id: '2m_5m', label: '$2M-$5M', min: 2000000, max: 5000000})
CREATE (pr5:PriceRange {id: 'over_5m', label: 'Over $5M', min: 5000000, max: 999999999})

// Step 2: Assign properties to ranges
MATCH (p:Property)
WHERE p.listing_price IS NOT NULL
MATCH (pr:PriceRange)
WHERE p.listing_price >= pr.min AND p.listing_price < pr.max
MERGE (p)-[:IN_PRICE_RANGE {
  actual_price: p.listing_price,
  percentile_in_range: (p.listing_price - pr.min) / (pr.max - pr.min)
}]->(pr)
```

### 6. Geographic Hierarchy - LOCATED_IN, IN_CITY, IN_COUNTY

#### Current Approach (Partially Working)
Multiple DataFrames with complex joins.

#### Neo4j Approach (Simple Hierarchy)
Build hierarchy during node creation.

**Implementation Pattern:**
```cypher
// Step 1: Create geographic hierarchy
MERGE (s:State {code: $state_code, name: $state_name})
MERGE (co:County {id: $county_id, name: $county_name})
MERGE (co)-[:IN_STATE]->(s)
MERGE (c:City {id: $city_id, name: $city_name})
MERGE (c)-[:IN_COUNTY]->(co)
MERGE (n:Neighborhood {neighborhood_id: $neighborhood_id, name: $neighborhood_name})
MERGE (n)-[:IN_CITY]->(c)

// Step 2: Connect properties
MATCH (p:Property {listing_id: $listing_id})
MATCH (n:Neighborhood {neighborhood_id: $neighborhood_id})
MERGE (p)-[:LOCATED_IN]->(n)
```

### 7. OF_TYPE - Property Type Classification

#### Current Approach (Working but Over-Complex)
Broadcast joins and multiple transformations.

#### Neo4j Approach (Direct Assignment)
Simple matching during import.

**Implementation Pattern:**
```cypher
// Step 1: Create property types
CREATE (pt1:PropertyType {id: 'single_family', name: 'Single Family'})
CREATE (pt2:PropertyType {id: 'condo', name: 'Condominium'})
CREATE (pt3:PropertyType {id: 'townhouse', name: 'Townhouse'})
CREATE (pt4:PropertyType {id: 'multi_family', name: 'Multi-Family'})

// Step 2: Assign properties to types
MATCH (p:Property)
WHERE p.property_type IS NOT NULL
MATCH (pt:PropertyType)
WHERE pt.name = p.property_type OR pt.id = p.property_type
MERGE (p)-[:OF_TYPE]->(pt)
```

## Batch Import Strategy

### Phase 1: Node Import
Prepare simple CSV files in Spark, then bulk import to Neo4j.

**CSV Preparation in Spark:**
- Clean and standardize fields
- Handle missing values
- Convert data types
- Generate unique IDs

**Neo4j Import:**
```cypher
// Use LOAD CSV for initial import
USING PERIODIC COMMIT 10000
LOAD CSV WITH HEADERS FROM 'file:///properties.csv' AS row
CREATE (p:Property {
  listing_id: row.listing_id,
  listing_price: toFloat(row.listing_price),
  bedrooms: toInteger(row.bedrooms),
  bathrooms: toFloat(row.bathrooms),
  square_feet: toInteger(row.square_feet),
  property_type: row.property_type,
  city: row.city,
  state: row.state,
  neighborhood_id: row.neighborhood_id,
  features: split(row.features, '|')
})
```

### Phase 2: Index Creation
Create all indexes before relationship creation.

```cypher
// Property indexes
CREATE INDEX property_id IF NOT EXISTS FOR (p:Property) ON (p.listing_id);
CREATE INDEX property_neighborhood IF NOT EXISTS FOR (p:Property) ON (p.neighborhood_id);
CREATE INDEX property_city IF NOT EXISTS FOR (p:Property) ON (p.city);
CREATE INDEX property_price IF NOT EXISTS FOR (p:Property) ON (p.listing_price);

// Neighborhood indexes
CREATE INDEX neighborhood_id IF NOT EXISTS FOR (n:Neighborhood) ON (n.neighborhood_id);
CREATE INDEX neighborhood_city IF NOT EXISTS FOR (n:Neighborhood) ON (n.city);

// Feature indexes
CREATE INDEX feature_name IF NOT EXISTS FOR (f:Feature) ON (f.name);

// Wait for indexes to come online
CALL db.awaitIndexes();
```

### Phase 3: Relationship Creation
Execute relationship queries in optimal order.

**Execution Order:**
1. Geographic hierarchy (LOCATED_IN, IN_CITY, IN_COUNTY)
2. Classification relationships (HAS_FEATURE, OF_TYPE, IN_PRICE_RANGE)
3. Computed relationships (SIMILAR_TO, NEAR)
4. Knowledge relationships (DESCRIBES)

## Performance Optimization Techniques

### 1. Use APOC Procedures
APOC provides optimized procedures for batch operations.

```cypher
// Batch relationship creation
CALL apoc.periodic.iterate(
  'MATCH (p:Property) RETURN p',
  'MATCH (pr:PriceRange) 
   WHERE p.listing_price >= pr.min AND p.listing_price < pr.max
   CREATE (p)-[:IN_PRICE_RANGE]->(pr)',
  {batchSize: 1000, parallel: true}
)
```

### 2. Optimize Memory Usage
Configure Neo4j for bulk operations.

```
# neo4j.conf settings for import
dbms.memory.heap.initial_size=4G
dbms.memory.heap.max_size=8G
dbms.memory.pagecache.size=4G
dbms.tx_state.memory_allocation=ON_HEAP
```

### 3. Use Constraints for Data Integrity
Ensure data quality with constraints.

```cypher
CREATE CONSTRAINT property_unique IF NOT EXISTS 
FOR (p:Property) REQUIRE p.listing_id IS UNIQUE;

CREATE CONSTRAINT neighborhood_unique IF NOT EXISTS
FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE;
```

### 4. Monitor Query Performance
Use EXPLAIN and PROFILE to optimize queries.

```cypher
PROFILE
MATCH (p1:Property)-[:SIMILAR_TO]->(p2:Property)
WHERE p1.city = 'San Francisco'
RETURN count(*)
```

## Migration Checklist

### Pre-Migration
- [ ] Back up existing Neo4j database
- [ ] Verify all source data fields exist
- [ ] Create field mapping documentation
- [ ] Test queries on small dataset
- [ ] Optimize Neo4j configuration

### During Migration
- [ ] Import nodes in correct order
- [ ] Create all indexes before relationships
- [ ] Use batch processing for large datasets
- [ ] Monitor memory usage
- [ ] Log all operations

### Post-Migration
- [ ] Verify node counts match source
- [ ] Validate relationship counts
- [ ] Run test queries from demos
- [ ] Check query performance
- [ ] Document any issues

## Query Templates Library

### Template 1: Generic Relationship Creation
```cypher
CALL apoc.periodic.iterate(
  'MATCH (source:SourceLabel), (target:TargetLabel)
   WHERE <filtering_conditions>
   RETURN source, target',
  'CREATE (source)-[:RELATIONSHIP_TYPE {properties}]->(target)',
  {batchSize: 1000, parallel: true}
)
```

### Template 2: Similarity Calculation
```cypher
WITH source, target,
  <similarity_calculation> as similarity
WHERE similarity >= $threshold
CREATE (source)-[:SIMILAR {score: similarity}]->(target)
```

### Template 3: Hierarchical Relationships
```cypher
MERGE (parent:ParentType {id: $parent_id})
MERGE (child:ChildType {id: $child_id})
MERGE (child)-[:BELONGS_TO]->(parent)
```

### Template 4: Conditional Relationships
```cypher
MATCH (source:Source)
WITH source,
  CASE
    WHEN condition1 THEN 'type1'
    WHEN condition2 THEN 'type2'
    ELSE 'default'
  END as rel_type
MATCH (target:Target {type: rel_type})
CREATE (source)-[:RELATES_TO {type: rel_type}]->(target)
```

## Common Patterns and Solutions

### Pattern: Many-to-Many Relationships
**Problem**: Properties have multiple features, features belong to multiple properties.
**Solution**: Use intermediate traversal or collection operations.

```cypher
// Find properties with specific feature combinations
MATCH (p:Property)-[:HAS_FEATURE]->(f1:Feature {name: 'Pool'})
MATCH (p)-[:HAS_FEATURE]->(f2:Feature {name: 'View'})
RETURN p
```

### Pattern: Avoid Cartesian Products
**Problem**: Cross-joining large sets causes memory issues.
**Solution**: Filter early and use indexes.

```cypher
// Bad: Creates massive cross-product
MATCH (p1:Property), (p2:Property)
WHERE p1.city = p2.city

// Good: Filter early
MATCH (p1:Property {city: 'San Francisco'})
MATCH (p2:Property {city: 'San Francisco'})
WHERE p1.listing_id < p2.listing_id
```

### Pattern: Bidirectional Relationships
**Problem**: Need relationships traversable in both directions.
**Solution**: Create both directions atomically.

```cypher
CREATE (a)-[:CONNECTS]->(b)
CREATE (b)-[:CONNECTS]->(a)
```

## Troubleshooting Guide

### Issue: Slow Relationship Creation
**Symptoms**: Queries take minutes or hours.
**Solutions**:
- Check for missing indexes
- Reduce batch size
- Disable parallel processing if memory constrained
- Increase heap memory

### Issue: Out of Memory Errors
**Symptoms**: Heap space errors during import.
**Solutions**:
- Reduce batch size to 100-500
- Increase heap allocation
- Use PERIODIC COMMIT
- Process in smaller chunks

### Issue: Duplicate Relationships
**Symptoms**: Multiple relationships between same nodes.
**Solutions**:
- Use MERGE instead of CREATE
- Add uniqueness constraints
- Check for duplicate source data

### Issue: Missing Relationships
**Symptoms**: Expected relationships not created.
**Solutions**:
- Verify field names match
- Check for null values
- Validate WHERE conditions
- Review data types

## Best Practices

### 1. Always Use Transactions
Wrap operations in explicit transactions for consistency.

```cypher
:begin
CREATE (...);
CREATE (...);
:commit
```

### 2. Parameterize Queries
Use parameters for security and performance.

```cypher
MATCH (p:Property {listing_id: $property_id})
RETURN p
```

### 3. Index Before Import
Create indexes before bulk operations, not after.

### 4. Monitor and Log
Track progress and performance metrics.

```cypher
MATCH (p:Property)
RETURN count(p) as property_count
```

### 5. Test on Subsets
Validate queries on small datasets first.

```cypher
MATCH (p:Property)
WITH p LIMIT 100
// Test your query logic here
```

## Conclusion

Moving relationship creation from Spark to Neo4j dramatically simplifies the architecture while improving performance and maintainability. The patterns documented here, proven in graph-real-estate, demonstrate that complex graph operations belong in the graph database, not in distributed computing frameworks.

By following these patterns, the data_pipeline can be reduced to a simple ETL tool that prepares clean data for Neo4j, while Neo4j handles all the sophisticated graph operations it was designed for. This approach aligns with the fundamental principle: use the right tool for the right job.