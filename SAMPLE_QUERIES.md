# Kibana Console Sample Queries for Real Estate Search

This document contains sample Elasticsearch queries that can be run directly in Kibana Console.
These queries are based on the demo queries in the real_estate_search system.

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
            "address.city.keyword": "San Francisco"
          }
        }
      ]
    }
  }
}
```

## 2. Property Filter Search

### Filter by property type and price range
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "property_type.keyword": "condo"
          }
        },
        {
          "range": {
            "price": {
              "gte": 500000,
              "lte": 1500000
            }
          }
        },
        {
          "range": {
            "bedrooms": {
              "gte": 2
            }
          }
        }
      ]
    }
  },
  "sort": [
    {
      "price": {
        "order": "asc"
      }
    }
  ]
}
```

### Complex filter with multiple criteria
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "features": "parking"
          }
        }
      ],
      "filter": [
        {
          "terms": {
            "property_type.keyword": ["single-family", "townhome"]
          }
        },
        {
          "range": {
            "square_feet": {
              "gte": 2000
            }
          }
        },
        {
          "range": {
            "bathrooms": {
              "gte": 2.5
            }
          }
        }
      ]
    }
  },
  "_source": ["listing_id", "property_type", "price", "bedrooms", "bathrooms", "square_feet", "address"]
}
```

## 3. Geographic Distance Search

### Find properties within radius of a point
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "match_all": {}
        }
      ],
      "filter": [
        {
          "geo_distance": {
            "distance": "5km",
            "address.location": {
              "lat": 37.7749,
              "lon": -122.4194
            }
          }
        }
      ]
    }
  },
  "sort": [
    {
      "_geo_distance": {
        "address.location": {
          "lat": 37.7749,
          "lon": -122.4194
        },
        "order": "asc",
        "unit": "km"
      }
    }
  ]
}
```

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
              "top_left": {
                "lat": 37.8,
                "lon": -122.5
              },
              "bottom_right": {
                "lat": 37.7,
                "lon": -122.3
              }
            }
          }
        }
      ]
    }
  },
  "_source": ["listing_id", "address", "price"]
}
```

## 4. Aggregation Queries

### Price distribution by property type
```json
GET real_estate_properties/_search
{
  "size": 0,
  "aggs": {
    "property_types": {
      "terms": {
        "field": "property_type.keyword",
        "size": 10
      },
      "aggs": {
        "price_stats": {
          "stats": {
            "field": "price"
          }
        },
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

### Neighborhood statistics
```json
GET real_estate_properties/_search
{
  "size": 0,
  "aggs": {
    "neighborhoods": {
      "terms": {
        "field": "neighborhood_id.keyword",
        "size": 20
      },
      "aggs": {
        "avg_price": {
          "avg": {
            "field": "price"
          }
        },
        "property_count": {
          "value_count": {
            "field": "listing_id.keyword"
          }
        },
        "avg_bedrooms": {
          "avg": {
            "field": "bedrooms"
          }
        },
        "price_per_sqft": {
          "bucket_script": {
            "buckets_path": {
              "avgPrice": "avg_price",
              "avgSqft": "avg_sqft"
            },
            "script": "params.avgPrice / params.avgSqft"
          }
        },
        "avg_sqft": {
          "avg": {
            "field": "square_feet"
          }
        }
      }
    }
  }
}
```

## 5. Semantic Similarity Search (KNN)

### Find properties similar to a specific property using embeddings
```json
GET real_estate_properties/_search
{
  "knn": {
    "field": "embedding",
    "query_vector": [...],  // Replace with actual 1024-dimension vector
    "k": 10,
    "num_candidates": 100
  },
  "size": 10,
  "_source": ["listing_id", "property_type", "price", "address", "description"]
}
```

### Get a property's embedding for similarity search
```json
GET real_estate_properties/_doc/prop-sf-001
{
  "_source": ["embedding"]
}
```

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
  "_source": {
    "includes": ["listing_id", "property_type", "price", "name", "title", "_index"]
  }
}
```

## 7. Relationship Queries

### Find properties in a specific neighborhood
```json
GET real_estate_properties/_search
{
  "query": {
    "term": {
      "neighborhood_id.keyword": "pacific-heights"
    }
  },
  "_source": ["listing_id", "address", "price", "property_type"]
}
```

### Get neighborhood details with property count
```json
GET real_estate_neighborhoods/_search
{
  "query": {
    "match_all": {}
  },
  "size": 10
}

# Then get properties for a specific neighborhood
GET real_estate_properties/_count
{
  "query": {
    "term": {
      "neighborhood_id.keyword": "pacific-heights"
    }
  }
}
```

## 8. Full-Text Search on Wikipedia

### Search Wikipedia articles
```json
GET real_estate_wikipedia/_search
{
  "query": {
    "match": {
      "content": "golden gate bridge history"
    }
  },
  "highlight": {
    "fields": {
      "content": {
        "fragment_size": 150,
        "number_of_fragments": 3
      }
    }
  },
  "_source": ["title", "page_id", "location"]
}
```

### Wikipedia articles for a specific city
```json
GET real_estate_wikipedia/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "content": "park recreation"
          }
        }
      ],
      "filter": [
        {
          "term": {
            "location.city.keyword": "San Francisco"
          }
        }
      ]
    }
  }
}
```

## 9. Complex Boolean Queries

### Combined must, should, and filter
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "modern",
            "fields": ["description", "features"]
          }
        }
      ],
      "should": [
        {
          "match": {
            "amenities": "pool"
          }
        },
        {
          "match": {
            "features": "view"
          }
        }
      ],
      "filter": [
        {
          "range": {
            "price": {
              "lte": 3000000
            }
          }
        },
        {
          "terms": {
            "property_type.keyword": ["single-family", "condo"]
          }
        }
      ],
      "minimum_should_match": 1
    }
  }
}
```

## 10. Faceted Search with Aggregations

### Get search results with facets for filtering
```json
GET real_estate_properties/_search
{
  "query": {
    "match_all": {}
  },
  "size": 10,
  "aggs": {
    "property_type_facet": {
      "terms": {
        "field": "property_type.keyword"
      }
    },
    "city_facet": {
      "terms": {
        "field": "address.city.keyword"
      }
    },
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
    "bedroom_facet": {
      "terms": {
        "field": "bedrooms"
      }
    }
  }
}
```

## 11. Scoring and Boosting

### Custom scoring with function score
```json
GET real_estate_properties/_search
{
  "query": {
    "function_score": {
      "query": {
        "multi_match": {
          "query": "luxury home",
          "fields": ["description", "features"]
        }
      },
      "functions": [
        {
          "filter": {
            "term": {
              "property_type.keyword": "single-family"
            }
          },
          "weight": 2
        },
        {
          "gauss": {
            "price": {
              "origin": 1500000,
              "scale": 500000
            }
          }
        },
        {
          "field_value_factor": {
            "field": "square_feet",
            "factor": 0.0001,
            "modifier": "sqrt"
          }
        }
      ],
      "score_mode": "sum",
      "boost_mode": "multiply"
    }
  }
}
```

## 12. Exists and Missing Queries

### Find properties with embeddings
```json
GET real_estate_properties/_search
{
  "query": {
    "exists": {
      "field": "embedding"
    }
  },
  "size": 0
}
```

### Find properties missing neighborhood assignment
```json
GET real_estate_properties/_search
{
  "query": {
    "bool": {
      "must_not": [
        {
          "exists": {
            "field": "neighborhood_id"
          }
        }
      ]
    }
  },
  "_source": ["listing_id", "address"]
}
```

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
    "match": {
      "description": "modern"
    }
  }
}
```