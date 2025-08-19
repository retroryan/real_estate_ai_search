# Neo4j Query Guide for Real Estate Graph

This guide provides comprehensive Cypher query examples for exploring the real estate graph database. Queries are organized by complexity and use case.

## Table of Contents
1. [Basic Property Queries](#basic-property-queries)
2. [Neighborhood Analytics](#neighborhood-analytics)
3. [Feature-Based Searches](#feature-based-searches)
4. [Similarity Searches](#similarity-searches)
5. [Price Analysis](#price-analysis)
6. [Graph Traversals](#graph-traversals)
7. [Advanced Analytics](#advanced-analytics)
8. [Performance Tips](#performance-tips)

---

## Basic Property Queries

### Find All Properties in a Specific Neighborhood
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood {name: 'Sf-Russian-Hill-002'})
RETURN p.address as Address, 
       p.listing_price as Price, 
       p.bedrooms as Bedrooms,
       p.square_feet as SqFt
ORDER BY p.listing_price DESC
```

### Find Properties by City
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City {name: 'San Francisco'})
RETURN p.address as Address, 
       n.name as Neighborhood,
       p.listing_price as Price
ORDER BY p.listing_price DESC
LIMIT 10
```

### Find Single Property Details
```cypher
MATCH (p:Property {listing_id: 'sf-001'})
OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
RETURN p as Property, 
       n.name as Neighborhood,
       collect(f.name) as Features
```

### Properties by Type
```cypher
MATCH (p:Property)
WHERE p.property_type = 'condo'
RETURN p.address as Address,
       p.listing_price as Price,
       p.square_feet as SqFt,
       p.price_per_sqft as PricePerSqFt
ORDER BY p.listing_price
```

---

## Neighborhood Analytics

### Average Price by Neighborhood
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
RETURN n.name as Neighborhood,
       n.city as City,
       count(p) as PropertyCount,
       avg(p.listing_price) as AvgPrice,
       min(p.listing_price) as MinPrice,
       max(p.listing_price) as MaxPrice
ORDER BY AvgPrice DESC
```

### Most Expensive Neighborhoods
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
WITH n, avg(p.listing_price) as avg_price, count(p) as prop_count
WHERE prop_count >= 2
RETURN n.name as Neighborhood,
       n.city as City,
       prop_count as Properties,
       avg_price as AveragePrice
ORDER BY avg_price DESC
LIMIT 5
```

### Neighborhood Comparison
```cypher
MATCH (n1:Neighborhood)<-[:LOCATED_IN]-(p1:Property)
WHERE n1.name = 'Sf-Pac-Heights-001'
WITH n1, avg(p1.listing_price) as avg1, avg(p1.square_feet) as sqft1
MATCH (n2:Neighborhood)<-[:LOCATED_IN]-(p2:Property)
WHERE n2.name = 'Sf-Russian-Hill-002'
WITH n1, avg1, sqft1, n2, avg(p2.listing_price) as avg2, avg(p2.square_feet) as sqft2
RETURN n1.name as Neighborhood1,
       avg1 as AvgPrice1,
       sqft1 as AvgSqFt1,
       n2.name as Neighborhood2,
       avg2 as AvgPrice2,
       sqft2 as AvgSqFt2,
       avg1 - avg2 as PriceDifference
```

### Connected Neighborhoods
```cypher
MATCH (n1:Neighborhood)-[:NEAR]-(n2:Neighborhood)
WHERE n1.city = 'San Francisco'
RETURN n1.name as Neighborhood, 
       collect(n2.name) as NearbyNeighborhoods
ORDER BY n1.name
```

---

## Feature-Based Searches

### Properties with Specific Features
```cypher
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
WHERE f.name IN ['Pool', 'Hot Tub', 'Sauna']
RETURN DISTINCT p.address as Address,
       p.listing_price as Price,
       collect(f.name) as LuxuryFeatures
ORDER BY p.listing_price DESC
```

### Most Popular Features
```cypher
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
RETURN f.name as Feature,
       f.category as Category,
       count(p) as PropertyCount
ORDER BY PropertyCount DESC
LIMIT 20
```

### Properties with Multiple Premium Features
```cypher
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
WHERE f.category IN ['View', 'Recreation', 'Outdoor']
WITH p, count(DISTINCT f.category) as premium_categories, collect(f.name) as features
WHERE premium_categories >= 2
RETURN p.address as Address,
       p.listing_price as Price,
       premium_categories as PremiumCategories,
       features as Features
ORDER BY p.listing_price DESC
```

### Feature Category Distribution
```cypher
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
RETURN f.category as Category,
       count(DISTINCT f.name) as UniqueFeatures,
       count(p) as PropertyConnections
ORDER BY PropertyConnections DESC
```

---

## Similarity Searches

### Find Similar Properties
```cypher
MATCH (p1:Property {listing_id: 'sf-001'})-[r:SIMILAR_TO]-(p2:Property)
RETURN p2.address as SimilarProperty,
       p2.listing_price as Price,
       p2.bedrooms as Bedrooms,
       p2.square_feet as SqFt,
       r.score as SimilarityScore
ORDER BY r.score DESC
LIMIT 5
```

### Most Similar Property Pairs
```cypher
MATCH (p1:Property)-[r:SIMILAR_TO]->(p2:Property)
WHERE r.score > 0.8
RETURN p1.address as Property1,
       p1.listing_price as Price1,
       p2.address as Property2,
       p2.listing_price as Price2,
       r.score as Similarity
ORDER BY r.score DESC
LIMIT 10
```

### Properties Similar in Price and Size
```cypher
MATCH (target:Property {listing_id: 'sf-001'})
MATCH (p:Property)
WHERE p <> target
  AND abs(p.listing_price - target.listing_price) / target.listing_price < 0.1
  AND abs(p.square_feet - target.square_feet) / target.square_feet < 0.15
RETURN p.address as Address,
       p.listing_price as Price,
       p.square_feet as SqFt,
       abs(p.listing_price - target.listing_price) as PriceDiff,
       abs(p.square_feet - target.square_feet) as SqFtDiff
ORDER BY PriceDiff
```

---

## Price Analysis

### Price Range Distribution
```cypher
MATCH (p:Property)-[:IN_PRICE_RANGE]->(pr:PriceRange)
RETURN pr.range as PriceRange,
       count(p) as PropertyCount,
       avg(p.square_feet) as AvgSqFt,
       avg(p.bedrooms) as AvgBedrooms
ORDER BY pr.range
```

### Properties by Price Range and City
```cypher
MATCH (p:Property)-[:IN_PRICE_RANGE]->(pr:PriceRange)
MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
RETURN c.name as City,
       pr.range as PriceRange,
       count(p) as Count
ORDER BY c.name, pr.range
```

### Price Per Square Foot Analysis
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
WHERE p.price_per_sqft IS NOT NULL
RETURN c.name as City,
       avg(p.price_per_sqft) as AvgPricePerSqFt,
       min(p.price_per_sqft) as MinPricePerSqFt,
       max(p.price_per_sqft) as MaxPricePerSqFt,
       count(p) as PropertyCount
ORDER BY AvgPricePerSqFt DESC
```

### Best Value Properties (Low Price per SqFt)
```cypher
MATCH (p:Property)
WHERE p.price_per_sqft IS NOT NULL
  AND p.square_feet > 1500
RETURN p.address as Address,
       p.listing_price as Price,
       p.square_feet as SqFt,
       p.price_per_sqft as PricePerSqFt,
       p.bedrooms as Bedrooms
ORDER BY p.price_per_sqft
LIMIT 10
```

---

## Graph Traversals

### Property to City Path
```cypher
MATCH path = (p:Property {listing_id: 'sf-001'})-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
RETURN p.address as Property,
       n.name as Neighborhood,
       c.name as City,
       length(path) as PathLength
```

### All Properties in Adjacent Neighborhoods
```cypher
MATCH (p1:Property {listing_id: 'sf-001'})-[:LOCATED_IN]->(n1:Neighborhood)
MATCH (n1)-[:NEAR]-(n2:Neighborhood)
MATCH (p2:Property)-[:LOCATED_IN]->(n2)
RETURN n1.name as SourceNeighborhood,
       n2.name as AdjacentNeighborhood,
       count(p2) as PropertyCount,
       avg(p2.listing_price) as AvgPrice
ORDER BY AvgPrice DESC
```

### Feature Network Analysis
```cypher
MATCH (p:Property)-[:HAS_FEATURE]->(f1:Feature)
WHERE p.listing_id = 'sf-001'
WITH p, collect(f1) as property_features
MATCH (p2:Property)-[:HAS_FEATURE]->(f2:Feature)
WHERE p2 <> p AND f2 IN property_features
WITH p, p2, count(f2) as shared_features
WHERE shared_features >= 3
RETURN p2.address as SimilarProperty,
       p2.listing_price as Price,
       shared_features as SharedFeatures
ORDER BY shared_features DESC
```

---

## Advanced Analytics

### Market Segmentation Query
```cypher
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
WITH c.name as city,
     CASE 
       WHEN p.listing_price < 1000000 THEN 'Entry Level'
       WHEN p.listing_price < 2000000 THEN 'Mid Market'
       WHEN p.listing_price < 3000000 THEN 'Upper Market'
       ELSE 'Luxury'
     END as segment,
     p
RETURN city,
       segment,
       count(p) as count,
       avg(p.square_feet) as avg_sqft,
       avg(p.bedrooms) as avg_bedrooms
ORDER BY city, segment
```

### Property Clustering by Attributes
```cypher
MATCH (p:Property)
WITH p,
     CASE 
       WHEN p.bedrooms <= 1 THEN 'Studio/1BR'
       WHEN p.bedrooms = 2 THEN '2BR'
       WHEN p.bedrooms = 3 THEN '3BR'
       ELSE '4BR+'
     END as bedroom_group,
     CASE
       WHEN p.square_feet < 1000 THEN 'Small'
       WHEN p.square_feet < 2000 THEN 'Medium'
       WHEN p.square_feet < 3000 THEN 'Large'
       ELSE 'Extra Large'
     END as size_group
RETURN bedroom_group,
       size_group,
       count(p) as count,
       avg(p.listing_price) as avg_price
ORDER BY bedroom_group, size_group
```

### Investment Opportunity Finder
```cypher
// Find underpriced properties compared to neighborhood average
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
WITH n, avg(p.listing_price) as neighborhood_avg
MATCH (p2:Property)-[:LOCATED_IN]->(n)
WHERE p2.listing_price < neighborhood_avg * 0.8
RETURN p2.address as Address,
       p2.listing_price as Price,
       neighborhood_avg as NeighborhoodAvg,
       (neighborhood_avg - p2.listing_price) as PotentialUpside,
       ((neighborhood_avg - p2.listing_price) / p2.listing_price * 100) as UpsidePercent
ORDER BY UpsidePercent DESC
```

### Feature Correlation Analysis
```cypher
MATCH (f1:Feature)<-[:HAS_FEATURE]-(p:Property)-[:HAS_FEATURE]->(f2:Feature)
WHERE f1.name < f2.name
WITH f1.name as feature1, f2.name as feature2, count(p) as cooccurrence
WHERE cooccurrence >= 5
RETURN feature1, feature2, cooccurrence
ORDER BY cooccurrence DESC
LIMIT 20
```

---

## Performance Tips

### Using Indexes
Always start your queries with indexed properties:
```cypher
// Good - uses index
MATCH (p:Property {listing_id: 'sf-001'})

// Less efficient - full scan
MATCH (p:Property)
WHERE p.listing_id = 'sf-001'
```

### Query Profile
Use PROFILE to analyze query performance:
```cypher
PROFILE
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
WHERE n.name = 'Sf-Pac-Heights-001'
RETURN p.address, p.listing_price
```

### Limiting Results Early
```cypher
// Efficient - limits early
MATCH (p:Property)
WITH p LIMIT 100
MATCH (p)-[:HAS_FEATURE]->(f:Feature)
RETURN p.address, collect(f.name)

// Less efficient - processes all then limits
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
RETURN p.address, collect(f.name)
LIMIT 100
```

### Using Parameters
For repeated queries, use parameters:
```cypher
// Define parameter
:param neighborhood => 'Sf-Russian-Hill-002'

// Use in query
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood {name: $neighborhood})
RETURN p.address, p.listing_price
```

---

## Running Queries

### From Neo4j Browser
1. Open Neo4j Browser at http://localhost:7474
2. Copy and paste any query from this guide
3. Click the run button or press Ctrl+Enter

### From Python Application
```bash
# Run sample queries
python main.py queries

# Run specific query category
python query_runner.py --category basic
python query_runner.py --category analytics
python query_runner.py --category similarity
```

### From Command Line (using cypher-shell)
```bash
# Connect to database
cypher-shell -u neo4j -p password

# Run query
MATCH (p:Property) RETURN count(p);
```

---

## Query Categories for Testing

The application includes pre-configured query categories:

1. **Basic**: Simple property lookups and counts
2. **Analytics**: Neighborhood and market analysis
3. **Features**: Feature-based searches and analysis
4. **Similarity**: Finding similar properties
5. **Traversal**: Graph path queries
6. **Advanced**: Complex analytical queries

Each category can be run independently for testing and demonstration purposes.