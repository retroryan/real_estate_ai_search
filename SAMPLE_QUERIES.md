# Kibana Console Sample Queries for Real Estate Search

## Guide Overview & Boolean Query Primer

This guide demonstrates a broad set of Elasticsearch search & analytics patterns relevant to real estate:
1. Multi-field full‑text relevance search
2. Structured filtering (exact, range, geo, existence)
3. Geographic distance & bounding box queries
4. Aggregations for stats, distributions, and derived metrics
5. Semantic vector (kNN) similarity search
6. Cross-index (federated) search
7. Relationship-style lookups via IDs
8. Faceting & drill-down navigation
9. Advanced boolean composition & scoring / boosting
10. Function score tuning and field value influence
11. Existence / quality control queries
12. Developer tooling & explain / analyze utilities

Below is a quick refresher on bool clauses (still central, but only part of the toolkit):
- **must**: All clauses must match; they contribute to the _score.
- **should**: Optional unless `minimum_should_match` forces requirement; matching clauses boost _score. If there is no must / filter / must_not, at least one should is required by default.
- **filter**: All clauses must match (logical AND). No scoring impact; cache-friendly. Use for strict constraints (term / range / geo / exists / ids).
- **must_not**: Negative clauses (logical NOT). No scoring contribution.

Logical AND vs OR inside filter:
- Multiple objects in the filter array are implicitly ANDed.
- For OR logic, wrap alternatives in a nested bool with should + `"minimum_should_match": 1`, or use a `terms` query for same-field value OR.

Scoring notes:
- Use `filter` for constraints that shouldn't influence ranking.
- Use `must` / `should` for relevance-bearing text / vector / boosting logic.
- Wrap purely filtered results in `constant_score` if you want flat scores.

Performance tips:
- Prefer `.keyword` (or raw keyword fields) for exact matching & aggregations.
- Push selective filters early to minimize expensive scoring set sizes.
- Keep `num_candidates` (kNN) balanced vs latency; then optionally rerank.

The examples below annotate each query with concise intent & key mechanics.

---

## Index Overview

- **real_estate_properties**: Main property listings with embeddings (420 documents)
- **real_estate_neighborhoods**: Neighborhood data (21 documents)  
- **real_estate_wikipedia**: Wikipedia articles related to locations (464 documents)

Note: You can also use the shorter aliases:
- **properties** → real_estate_properties
- **neighborhoods** → real_estate_neighborhoods  
- **wikipedia** → real_estate_wikipedia

## 1. Basic Property Search

### Simple text search across multiple fields
```json
GET real_estate_properties/_search
{
  "query": {
    "multi_match": {
      "query": "modern kitchen pool",
      "fields": ["description^2", "features^1.5", "amenities"],
      "type": "best_fields",
      "fuzziness": "AUTO"
    }
  },
  "size": 5,
  "highlight": {
    "fields": {
      "description": {},
      "features": {}
    }
  }
}
```
Note: Multi-field relevance search boosting description & features; fuzzy matching broadens recall; highlight extracts matched snippets.

### Search properties in a specific city
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "family home",
            "fields": ["description", "features"]
          }
        },
        {
          "term": {
            "city_standardized.keyword": "San Francisco"
          }
        }
      ]
    }
  }
}
```
Note: Combines text relevance (multi_match) with an exact keyword filter via must (filter would also work since the term does not need scoring).

## 2. Property Filter Search

### Filter by property type and price range
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "filter": [
        { "term": { "property_type": "condo" } },
        { "range": { "price": { "gte": 500000, "lte": 1500000 } } },
        { "range": { "bedrooms": { "gte": 2 } } }
      ]
    }
  },
  "sort": [ { "price": { "order": "asc" } } ]
}
```
Note: Pure filtering (no scoring influence) + ascending price sort for deterministic ordered results.

### Complex filter with multiple criteria
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [ { "match": { "features": "parking" } } ],
      "filter": [
        { "terms": { "property_type": ["single-family", "townhome"] } },
        { "range": { "square_feet": { "gte": 2000 } } },
        { "range": { "bathrooms": { "gte": 2.5 } } }
      ]
    }
  },
  "_source": ["listing_id", "property_type", "price", "bedrooms", "bathrooms", "square_feet", "city"]
}
```
Note: Text match (parking) affects score; structural filters narrow by type and size; partial bathroom values imply float mapping.

## 3. Geographic Distance Search

### Find properties within radius of a point
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [ { "match_all": {} } ],
      "filter": [
        { "geo_distance": { "distance": "5km", "address.location": { "lat": 37.7749, "lon": -122.4194 } } }
      ]
    }
  },
  "sort": [
    { "_geo_distance": { "address.location": { "lat": 37.7749, "lon": -122.4194 }, "order": "asc", "unit": "km" } }
  ]
}
```
Note: Geo-distance filter restricts candidates; geo sort orders by proximity for user-facing nearest results.

### Geo bounding box search
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "geo_bounding_box": {
            "address.location": {
              "top_left": { "lat": 37.8, "lon": -122.5 },
              "bottom_right": { "lat": 37.7, "lon": -122.3 }
            }
          }
        }
      ]
    }
  },
  "_source": ["listing_id", "city", "price"]
}
```
Note: Bounding box more efficient than many arbitrary polygon filters; good for map viewport queries.

## 4. Aggregation Queries

### Price distribution by property type
```json
GET real_estate_properties/_search
{
  "size": 0,
  "aggs": {
    "property_types": {
      "terms": { "field": "property_type", "size": 10 },
      "aggs": {
        "price_stats": { "stats": { "field": "price" } },
        "price_ranges": {
          "range": {
            "field": "price",
            "ranges": [
              {"to": 500000},
              {"from": 500000, "to": 1000000},
              {"from": 1000000, "to": 2000000},
              {"from": 2000000}
            ]
          }
        }
      }
    }
  }
}
```
Note: Buckets by property_type then nested stats & manual price bands for UI distribution / facet display.

### Neighborhood statistics
```json
GET real_estate_properties/_search
{
  "size": 0,
  "aggs": {
    "neighborhoods": {
      "terms": { "field": "neighborhood_id.keyword", "size": 20 },
      "aggs": {
        "avg_price": { "avg": { "field": "price" } },
        "property_count": { "value_count": { "field": "listing_id.keyword" } },
        "avg_bedrooms": { "avg": { "field": "bedrooms" } },
        "price_per_sqft": {
          "bucket_script": {
            "buckets_path": { "avgPrice": "avg_price", "avgSqft": "avg_sqft" },
            "script": "params.avgPrice / params.avgSqft"
          }
        },
        "avg_sqft": { "avg": { "field": "square_feet" } }
      }
    }
  }
}
```
Note: Derives price per sqft via pipeline (bucket_script) combining prior metric aggs inside each neighborhood bucket.

## 5. Semantic Similarity Search (KNN)

### Step 1: Get a random property's embedding for similarity search
```json
GET real_estate_properties/_search
{
  "query": {
    "function_score": {
      "query": { "match_all": {} },
      "random_score": {}
    }
  },
  "size": 1,
  "_source": ["listing_id", "property_type", "price", "city", "embedding"]
}
```
Note: Fetches a random property with its embedding. Copy the "embedding" array value to use as query_vector in the next query.

### Step 2: Find similar properties using the embedding from Step 1
```json
GET real_estate_properties/_search
{
  "knn": {
    "field": "embedding",
    "query_vector": [...],  // ← Paste the embedding array from Step 1 here
    "k": 10,
    "num_candidates": 100
  },
  "size": 10,
  "_source": ["listing_id", "property_type", "price", "city", "description"]
}
```
Note: Approximate vector similarity: num_candidates prefilter then selects top k; ensure vector dimension (1024) matches mapping.

### Alternative: Find similar properties excluding the original (manual approach)
```json
GET real_estate_properties/_search
{
  "knn": {
    "field": "embedding", 
    "query_vector": [...],  // ← Paste embedding from Step 1
    "k": 11,  // ← Request one extra to account for the original
    "num_candidates": 100
  },
  "size": 11,
  "_source": ["listing_id", "property_type", "price", "city", "description"]
}
```
Note: Request k+1 results then manually skip the original property in your application code. The highest scoring result will typically be the original property itself (score ≈ 1.0).

## 6. Multi-Index Search

### Search across properties, neighborhoods, and Wikipedia
```json
GET real_estate_properties,real_estate_neighborhoods,real_estate_wikipedia/_search
{
  "query": {
    "multi_match": {
      "query": "historic downtown park",
      "fields": [
        "description^2",
        "features",
        "amenities",
        "name^3",
        "content",
        "title^2"
      ],
      "type": "best_fields"
    }
  },
  "size": 5,
  "_source": { "includes": ["listing_id", "property_type", "price", "name", "title", "_index"] }
}
```
Note: Federated search unifies semantically related docs from heterogeneous indices; boosts entity name/title fields.

## 7. Relationship Queries

### Find properties in a specific neighborhood
```json
GET real_estate_properties/_search
{
  "query": { "term": { "neighborhood_id.keyword": "sf-pacific-heights-001" } },
  "_source": ["listing_id", "city", "price", "property_type"]
}
```
Note: Direct lookup by neighborhood foreign-key style identifier.

### Get neighborhood details with property count
```json
GET real_estate_neighborhoods/_search
{
  "query": { "match_all": {} },
  "size": 10
}

# Then get properties for a specific neighborhood
GET real_estate_properties/_count
{
  "query": { "term": { "neighborhood_id.keyword": "sf-pacific-heights-001" } }
}
```
Note: Two-step pattern: fetch neighborhood metadata then count associated listings via term filter.

## 8. Full-Text Search on Wikipedia

### Search Wikipedia articles
```json
GET real_estate_wikipedia/_search
{
  "query": { "match": { "content": "golden gate bridge history" } },
  "highlight": {
    "fields": { "content": { "fragment_size": 150, "number_of_fragments": 3 } }
  },
  "_source": ["title", "page_id", "location"]
}
```
Note: Standard match query with highlighting for snippet preview; fragment sizing tuned for summary panels.

### Wikipedia articles for a specific city
```json
GET real_estate_wikipedia/_search
{
  "query": {
    "bool": {
      "must": [ { "match": { "content": "park recreation" } } ],
      "filter": [ { "term": { "location.city.keyword": "San Francisco" } } ]
    }
  }
}
```
Note: Text relevance restricted to a city via keyword filter; supports local contextual info enrichment.

## 9. Complex Boolean Queries

### Combined must, should, and filter
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [ { "multi_match": { "query": "modern", "fields": ["description", "features"] } } ],
      "should": [ { "match": { "amenities": "pool" } }, { "match": { "features": "view" } } ],
      "filter": [
        { "range": { "price": { "lte": 3000000 } } },
        { "terms": { "property_type": ["single-family", "condo"] } }
      ],
      "minimum_should_match": 1
    }
  }
}
```
Note: Forces baseline relevance on modern while requiring at least one of pool/view; price/type constraints unscored; classic hybrid ranking pattern.

## 10. Faceted Search with Aggregations

### Get search results with facets for filtering
```json
GET real_estate_properties/_search
{
  "query": { "match_all": {} },
  "size": 0,
  "aggs": {
    "property_type_facet": { "terms": { "field": "property_type" } },
    "city_facet": { "terms": { "field": "city_standardized.keyword" } },
    "price_ranges_facet": {
      "range": {
        "field": "price",
        "ranges": [
          {"key": "Under 500k", "to": 500000},
            {"key": "500k-1M", "from": 500000, "to": 1000000},
            {"key": "1M-2M", "from": 1000000, "to": 2000000},
            {"key": "Over 2M", "from": 2000000}
        ]
      }
    },
    "bedroom_facet": { "terms": { "field": "bedrooms" } }
  }
}
```
Note: Simultaneously returns sample hits plus facet buckets enabling UI-driven refinements without extra round trip. Excludes the large embedding vector from hits to reduce payload size.

## 11. Scoring and Boosting

### Custom scoring with function score
```json
GET real_estate_properties/_search
{
  "query": {
    "function_score": {
      "query": { "multi_match": { "query": "luxury home", "fields": ["description", "features"] } },
      "functions": [
        { "filter": { "term": { "property_type": "single-family" } }, "weight": 2 },
        { "gauss": { "price": { "origin": 1500000, "scale": 500000 } } },
        { "field_value_factor": { "field": "square_feet", "factor": 0.0001, "modifier": "sqrt" } }
      ],
      "score_mode": "sum",
      "boost_mode": "multiply"
    }
  }
}
```
Note: Base textual relevance blended with discrete boost, distance decay on price proximity, and size scaling; final multiply amplifies combined score.

## 12. Exists and Missing Queries

### Find properties with embeddings
```json
GET real_estate_properties/_search
{
  "query": { "exists": { "field": "embedding" } },
  "size": 0
}
```
Note: Quality / coverage check counting docs containing stored vector field.

### Find properties missing neighborhood assignment
```json
GET real_estate_properties/_search
{
  "query": { "bool": { "must_not": [ { "exists": { "field": "neighborhood_id" } } ] } },
  "_source": ["listing_id", "city"]
}
```
Note: Identifies orphan listings lacking neighborhood linkage for data hygiene.

## Tips for Kibana Console

1. **Autocomplete**: Use Ctrl+Space for autocomplete suggestions
2. **Format**: Use the wrench icon to auto-format your query
3. **History**: Access previous queries with up/down arrows
4. **Comments**: Add comments with // or /* */
5. **Variables**: Define variables at the top of your session

## Authentication

If your Elasticsearch cluster requires authentication, configure it in Kibana:
- Go to Stack Management → Security → API Keys
- Or use basic auth in the Elasticsearch URL

## Useful Dev Tools Commands

```
# Get cluster health
GET _cluster/health

# Get index mapping
GET real_estate_properties/_mapping

# Get index settings
GET real_estate_properties/_settings

# Analyze text
GET real_estate_properties/_analyze
{
  "text": "modern luxury home",
  "analyzer": "standard"
}

# Explain score
GET real_estate_properties/_explain/prop-sf-001
{
  "query": {
    "match": { "description": "modern" }
  }
}
```
Note: Handy admin & debugging commands: mapping/settings inspection, analyzer breakdown, and detailed scoring explanation.
