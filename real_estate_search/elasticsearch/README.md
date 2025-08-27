# Elasticsearch Configuration Guide

This directory contains all the Elasticsearch configuration files needed for the Real Estate AI Search application. This guide serves as a comprehensive tutorial for understanding and setting up Elasticsearch indexes, pipelines, and analyzers.

## 📁 Directory Structure

```
elasticsearch/
├── pipelines/          # Ingest pipelines for data processing
│   └── wikipedia_ingest.json
├── settings/           # Index settings and analyzer configurations
│   └── analyzers.json
└── templates/          # Index mappings for different entity types
    ├── neighborhoods.json
    ├── properties.json
    ├── property_relationships.json
    └── wikipedia.json
```

## 🎯 Overview

This project uses Elasticsearch as its primary search engine, implementing:
- **Custom analyzers** for text processing
- **Ingest pipelines** for data transformation
- **Index templates** for structured data mapping
- **Dense vectors** for semantic search capabilities
- **Geo-spatial** features for location-based queries

## 📋 Configuration Files Detailed Explanation

### 1. Settings: `settings/analyzers.json`

This file defines custom analyzers, normalizers, and index settings that are shared across all indexes.

#### Key Components:

**Index Settings:**
- `number_of_shards: 1` - Single shard for development/small datasets
- `number_of_replicas: 0` - No replicas to save resources in dev
- `refresh_interval: "1s"` - Documents searchable after 1 second

**Custom Analyzers:**

1. **`property_analyzer`** - For property descriptions
   - Tokenizer: `standard` (splits on whitespace and punctuation)
   - Filters: `lowercase`, `stop` (removes common words), `snowball` (stems words)
   - Use: Property descriptions, neighborhood descriptions

2. **`address_analyzer`** - For street addresses
   - Tokenizer: `standard`
   - Filters: `lowercase`, `asciifolding` (converts accented chars)
   - Use: Street names, maintaining searchability with/without accents

3. **`feature_analyzer`** - For property features/amenities
   - Tokenizer: `keyword` (treats entire input as single token)
   - Filters: `lowercase`
   - Use: Exact matching on features like "swimming pool", "garage"

4. **`wikipedia_analyzer`** - For Wikipedia content
   - Tokenizer: `standard`
   - Filters: `lowercase`, `stop`, `snowball`, `shingle`
   - Special: Includes shingles for phrase matching (2-3 word combinations)
   - Use: Rich text content from Wikipedia articles

**Normalizers:**
- **`lowercase_normalizer`** - For keyword fields needing case-insensitive exact matching
  - Filters: `lowercase`, `asciifolding`
  - Use: City names, categories, ensuring "San Francisco" = "san francisco"

**Custom Filters:**
- **`shingle`** - Creates n-grams of 2-3 words
  - Improves phrase matching in searches
  - Example: "modern luxury home" → ["modern luxury", "luxury home", "modern luxury home"]

### 2. Ingest Pipeline: `pipelines/wikipedia_ingest.json`

This pipeline processes Wikipedia HTML content before indexing. **Note: Currently not actively used in the codebase but configured for future use.**

#### Pipeline Processors:

1. **`html_strip`** processor
   - Removes HTML tags from `full_content` field
   - `ignore_missing: true` - Continues if field doesn't exist
   - Converts: `<p>Text</p>` → `Text`

2. **`trim`** processor
   - Removes leading/trailing whitespace
   - Cleans up content after HTML stripping

3. **`script`** processor (Painless script)
   - Adds metadata when content is loaded:
     - `content_loaded: true` - Flag indicating content exists
     - `content_loaded_at: new Date()` - Timestamp of processing
     - `content_length` - Character count for analytics

#### Error Handling:
- `on_failure` - Captures any processing errors
- Sets `ingest_error` field with error message
- Allows document to be indexed even if pipeline fails

#### How to Use:
```bash
# Create the pipeline
PUT _ingest/pipeline/wikipedia_ingest

# Index a document using the pipeline
POST wikipedia/_doc?pipeline=wikipedia_ingest
{
  "title": "San Francisco",
  "full_content": "<html><body>Content here</body></html>"
}
```

### 3. Index Templates

#### `templates/properties.json` - Real Estate Properties

**Purpose:** Main index for property listings with rich location context and vector embeddings.

**Key Field Groups:**

1. **Basic Property Info:**
   - `listing_id` (keyword) - Unique identifier
   - `property_type` (keyword + normalizer) - House, Condo, etc.
   - `price` (float), `bedrooms` (short), `bathrooms` (half_float)
   - `square_feet` (integer), `year_built` (short)

2. **Address & Location:**
   - `address.street` (text + keyword multi-field) - Searchable and sortable
   - `address.location` (geo_point) - For distance queries
   - `address.city` (keyword + normalizer) - Case-insensitive matching

3. **Neighborhood Context:**
   - Embedded neighborhood data for denormalized search
   - `walkability_score` (byte: 0-100)
   - `school_rating` (half_float)

4. **Wikipedia Enrichment Fields:**
   - `location_context` - City-level Wikipedia data
   - `neighborhood_context` - Neighborhood Wikipedia data
   - `nearby_poi` (nested) - Points of interest with Wikipedia links
   - `landmarks` (nested) - Notable landmarks with distance

5. **Vector Search:**
   - `embedding` (dense_vector, 1024 dims) - For semantic search
   - `embedding_model` (keyword) - Track model version
   - `similarity: "cosine"` - Similarity metric for vectors

**Advanced Features:**
- **Multi-fields:** Many text fields have `.keyword` sub-field for exact matching/aggregations
- **Nested objects:** For arrays of complex objects (POIs, landmarks)
- **Non-indexed fields:** URLs and images (`index: false`) to save space
- **Optimized numeric types:** `byte` for 0-255, `half_float` for precision

#### `templates/neighborhoods.json` - Neighborhood Data

**Purpose:** Neighborhood information with demographic data and Wikipedia correlations.

**Special Features:**

1. **Demographics Object:**
   ```json
   "demographics": {
     "age_distribution": ["18-25: 20%", "26-35: 30%"],
     "education_level": ["Bachelor's: 45%"],
     "income_brackets": ["50k-75k: 25%"]
   }
   ```

2. **Wikipedia Correlations:**
   - `primary_wiki_article` - Main Wikipedia article
   - `related_wiki_articles` - Related articles
   - `confidence` scores for relevance
   - `parent_geography` - Links to city/state Wikipedia

3. **Search Optimization:**
   - Uses same analyzers as properties for consistency
   - Embeddings for semantic neighborhood search

#### `templates/wikipedia.json` - Wikipedia Articles

**Purpose:** Full Wikipedia articles with multiple content fields for different use cases.

**Content Fields Strategy:**
- `short_summary` - Quick overview (analyzed)
- `long_summary` - Detailed summary (analyzed)
- `full_content` - Complete article HTML (analyzed + exact)
  - `.exact` sub-field uses standard analyzer for precise matching

**Search Features:**
- `english` analyzer for all content fields
- `index_options: "offsets"` on full_content for highlighting
- `content_loaded` boolean to track enrichment status

**Location Mapping:**
- `best_city`, `best_state` - Normalized location extraction
- `location` (geo_point) - For geo-queries
- `key_topics` - Extracted topics as keywords

#### `templates/property_relationships.json` - Denormalized Search Index

**Purpose:** Combines properties, neighborhoods, and Wikipedia data for efficient single-query searches.

**Design Philosophy:**
- **Denormalization** - All related data in one document
- **Optimized for read** - No joins needed at query time
- **Trade-off** - Larger index size for faster queries

**Key Features:**

1. **Complete Property Data** - All fields from properties index

2. **Embedded Neighborhood** - Full neighborhood object inline

3. **Wikipedia Articles Array** (nested):
   ```json
   "wikipedia_articles": [{
     "page_id": "12345",
     "title": "Golden Gate Park",
     "relationship_type": "nearby_landmark",
     "confidence": 0.95,
     "relevance_score": 0.87
   }]
   ```

4. **Enriched Search Text:**
   - Concatenated searchable content from all sources
   - Uses `wikipedia_analyzer` for rich text search

5. **Tracking Fields:**
   - `relationship_updated` - When relationships were built
   - `data_version` - For cache invalidation

## 🚀 Setup Guide

### Step 1: Create Index Settings

First, create a base index template with shared settings:

```bash
PUT _index_template/real_estate_base
{
  "index_patterns": ["properties*", "neighborhoods*", "wikipedia*", "property_relationships*"],
  "template": {
    "settings": <contents of settings/analyzers.json>
  },
  "priority": 1
}
```

### Step 2: Create Specific Index Templates

For each entity type:

```bash
# Properties Index
PUT _index_template/properties_template
{
  "index_patterns": ["properties*"],
  "template": {
    "mappings": <contents of templates/properties.json>
  },
  "priority": 10
}

# Repeat for neighborhoods, wikipedia, property_relationships
```

### Step 3: Create Ingest Pipeline (Optional)

```bash
PUT _ingest/pipeline/wikipedia_ingest
<contents of pipelines/wikipedia_ingest.json>
```

### Step 4: Create Indexes

```bash
PUT properties
PUT neighborhoods
PUT wikipedia
PUT property_relationships
```

## 📊 Data Types Optimization

### Numeric Type Selection:
- **byte**: 0-127 (walkability scores)
- **short**: -32,768 to 32,767 (bedrooms, year_built)
- **integer**: Standard 32-bit (square_feet, population)
- **long**: 64-bit (tax_assessed_value)
- **half_float**: 16-bit float (ratings, small decimals)
- **float**: 32-bit (prices, coordinates)

### Text Field Patterns:
```json
{
  "field_name": {
    "type": "text",              // For full-text search
    "analyzer": "custom_analyzer",
    "fields": {
      "keyword": {                // For exact match, sorting, aggs
        "type": "keyword",
        "ignore_above": 256       // Don't index long strings
      }
    }
  }
}
```

## 🔍 Query Examples

### 1. Multi-field Search
```json
GET properties/_search
{
  "query": {
    "multi_match": {
      "query": "modern home pool",
      "fields": ["description^2", "features", "amenities"]
    }
  }
}
```

### 2. Geo-distance Query
```json
GET properties/_search
{
  "query": {
    "geo_distance": {
      "distance": "10km",
      "address.location": {
        "lat": 37.7749,
        "lon": -122.4194
      }
    }
  }
}
```

### 3. Vector Similarity Search
```json
GET properties/_search
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],
    "k": 10,
    "num_candidates": 100
  }
}
```

### 4. Nested Query for POIs
```json
GET properties/_search
{
  "query": {
    "nested": {
      "path": "nearby_poi",
      "query": {
        "bool": {
          "must": [
            {"match": {"nearby_poi.category": "school"}},
            {"range": {"nearby_poi.distance_miles": {"lte": 2}}}
          ]
        }
      }
    }
  }
}
```

## 🔧 Pipeline Usage Status

**Current Status:** The `wikipedia_ingest` pipeline is configured but **not actively used** in the current codebase.

**Where pipelines could be used:**
1. During bulk indexing in `data_pipeline/writers/elasticsearch/`
2. In the enrichment script `real_estate_search/enrich_wikipedia_articles.py`
3. When updating documents through the API

**To enable pipeline usage:**
```python
# In your indexing code
es.index(
    index="wikipedia",
    document=doc,
    pipeline="wikipedia_ingest"  # Add this parameter
)
```

## 📈 Performance Considerations

1. **Shard Configuration**: Single shard works for <50GB data. Scale horizontally for larger datasets.

2. **Refresh Interval**: 1s is good for development. Consider 30s-60s for production to improve indexing speed.

3. **Dense Vectors**: 1024 dimensions is substantial. Consider dimension reduction for very large datasets.

4. **Nested Fields**: Have performance cost. Use sparingly and only when needed for independent object queries.

5. **Multi-fields**: Each additional field increases index size. Balance search flexibility with storage.

## 🎓 Learning Resources

- **Analyzers**: How text is processed for search
- **Mappings**: Define how documents and fields are stored and indexed
- **Ingest Pipelines**: Server-side data transformation
- **Dense Vectors**: Enable ML-powered semantic search
- **Geo Queries**: Location-based search capabilities

## 💡 Best Practices

1. **Use appropriate data types** - Saves space and improves performance
2. **Design for your queries** - Structure data how you'll search it
3. **Denormalize when appropriate** - Trade space for query speed
4. **Version your mappings** - Track changes with data_version fields
5. **Monitor pipeline errors** - Check ingest_error fields
6. **Test analyzers** - Use `_analyze` API to verify text processing

## 🔄 Future Enhancements

1. **Activate ingest pipelines** for automatic data enrichment
2. **Add more pipelines** for different data types
3. **Implement pipeline chains** for complex transformations
4. **Add ML inference pipelines** for real-time predictions
5. **Configure ILM policies** for data lifecycle management

This configuration provides a robust foundation for a production-ready Elasticsearch implementation with support for complex real estate searches, geographic queries, and semantic search capabilities.