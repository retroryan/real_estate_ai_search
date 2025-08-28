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

## �� Configuration Files Detailed Explanation

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
   - Filters: `lowercase`, `stop`, `snowball`
   - Use: Property descriptions, neighborhood descriptions

2. **`address_analyzer`** - For street addresses
   - Tokenizer: `standard`
   - Filters: `lowercase`, `asciifolding`
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

#### Token Filter Definitions:

**Common Filters Explained:**

- **`lowercase`**: Converts all tokens to lowercase
  - Example: "San Francisco" → "san francisco"
  - Purpose: Case-insensitive matching

- **`stop`**: Removes common English stop words
  - Removes: "the", "is", "at", "which", "on", "a", "an", etc.
  - Example: "the beautiful house on the hill" → "beautiful house hill"
  - Purpose: Focuses on meaningful words, reduces index size

- **`snowball`**: Algorithmic stemmer that reduces words to root form
  - Examples: "running" → "run", "houses" → "hous", "beautiful" → "beauti"
  - Purpose: Matches different forms of the same word

- **`asciifolding`**: Converts alphabetic, numeric, and symbolic Unicode characters outside ASCII range to ASCII equivalents
  - Examples: "café" → "cafe", "naïve" → "naive", "Zürich" → "Zurich"
  - Purpose: Handles accented characters, making "José" searchable as "Jose"

- **`shingle`**: Creates word n-grams (consecutive word combinations)
  - With `min_shingle_size: 2` and `max_shingle_size: 3`:
    - Input: "modern luxury home"
    - Output tokens: ["modern", "luxury", "home", "modern luxury", "luxury home", "modern luxury home"]
  - Purpose: Improves phrase matching and relevance

**Normalizers:**
- **`lowercase_normalizer`** - For keyword fields needing case-insensitive exact matching
  - Filters: `lowercase`, `asciifolding`
  - Use: City names, categories, ensuring "San Francisco" = "san francisco"
  - Note: Normalizers only work on keyword fields, not text fields

**Custom Filter Configuration:**
- **`shingle`** filter settings:
  - `min_shingle_size: 2` - Minimum words in a shingle (2 = bigrams)
  - `max_shingle_size: 3` - Maximum words in a shingle (3 = trigrams)
  - Creates overlapping word combinations for better phrase search

### 2. Ingest Pipeline: `pipelines/wikipedia_ingest.json`

This pipeline processes Wikipedia HTML content before indexing. **Status: ACTIVE - Used by the WikipediaEnricher for content enrichment.**

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

#### Understanding Elasticsearch Field Types and Concepts

Before diving into the templates, let's understand key Elasticsearch concepts:

**Field Types Explained:**

- **`keyword`**: Structured content for exact matching, filtering, sorting, and aggregations
  - Stored as-is without analysis (not tokenized)
  - Examples: IDs, email addresses, status codes, zip codes
  - Use cases: Exact matches, terms aggregations, sorting
  - Example mapping: `"listing_id": {"type": "keyword"}`

- **`text`**: Unstructured content for full-text search
  - Analyzed (tokenized, filtered) at index time
  - Examples: Descriptions, reviews, article content
  - Use cases: Full-text search, relevance scoring
  - Example mapping: `"description": {"type": "text", "analyzer": "english"}`

- **`fields` (Multi-fields)**: Store the same value in multiple ways
  - Allows different analysis for different purposes
  - Common pattern: Text field with keyword sub-field
  - Example:
    ```json
    "title": {
      "type": "text",           // For full-text search
      "fields": {
        "keyword": {             // For exact match, sorting
          "type": "keyword",
          "ignore_above": 256    // Don't index if longer than 256 chars
        }
      }
    }
    ```
  - Query usage: `title` for search, `title.keyword` for sorting/aggregations

**Why Use Multi-fields?**
- Single source, multiple purposes: Search "modern home" in description, but also aggregate on exact property descriptions
- Performance: Index once, use many ways
- Flexibility: Can search loosely but sort/filter exactly

**Common Field Type Patterns:**

1. **ID Fields**: Always use `keyword`
   ```json
   "listing_id": {"type": "keyword"}
   ```

2. **Descriptive Text**: Use `text` with `keyword` sub-field
   ```json
   "description": {
     "type": "text",
     "analyzer": "english",
     "fields": {
       "keyword": {"type": "keyword", "ignore_above": 256}
     }
   }
   ```

3. **Categories/Tags**: Use `keyword` with normalizer
   ```json
   "property_type": {
     "type": "keyword",
     "normalizer": "lowercase_normalizer"
   }
   ```

4. **Numeric Types**: Choose based on range and precision needs
   - `byte`: -128 to 127
   - `short`: -32,768 to 32,767  
   - `integer`: -2^31 to 2^31-1
   - `long`: -2^63 to 2^63-1
   - `float`: Single-precision 32-bit
   - `half_float`: Half-precision 16-bit
   - `double`: Double-precision 64-bit

5. **Boolean**: True/false values
   ```json
   "has_pool": {"type": "boolean"}
   ```

6. **Date**: Date/time values
   ```json
   "listing_date": {"type": "date"}
   ```

7. **Object**: JSON objects (nested structure)
   ```json
   "address": {
     "type": "object",
     "properties": {
       "street": {"type": "text"},
       "city": {"type": "keyword"}
     }
   }
   ```

8. **Nested**: Array of objects that need independent querying
   ```json
   "amenities": {
     "type": "nested",
     "properties": {
       "name": {"type": "keyword"},
       "available": {"type": "boolean"}
     }
   }
   ```

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

5. **Vector Search (KNN-Enabled):**
   - `embedding` (dense_vector, 1024 dims) - For semantic search
   - `embedding_model` (keyword) - Track model version
   - `similarity: "cosine"` - Similarity metric for vectors
   - **Automatic KNN**: Since Elasticsearch 8.0, `index: true` is default for dense_vector fields

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

## 📚 Special Field Configurations

### Important Field Settings

**`ignore_above`**: For keyword fields, don't index strings longer than specified length
```json
"keyword": {
  "type": "keyword",
  "ignore_above": 256  // Strings > 256 chars won't be indexed (still stored)
}
```
- Purpose: Prevents memory issues with very long strings
- Use case: URLs, descriptions that might be unexpectedly long

**`index`**: Controls whether field is searchable
```json
"virtual_tour_url": {
  "type": "keyword",
  "index": false  // Can't search on this field
}
```
- Purpose: Saves disk space and memory for fields you'll never search
- Use case: URLs, IDs only used for retrieval

**`doc_values`**: Controls whether field can be used for sorting/aggregations
```json
"images": {
  "type": "keyword",
  "index": false,
  "doc_values": false  // Can't sort or aggregate on this field
}
```
- Purpose: Saves significant disk space
- Use case: Fields only returned in search results, never sorted/aggregated

**`normalizer`**: Like analyzer but for keyword fields (single token)
```json
"city": {
  "type": "keyword",
  "normalizer": "lowercase_normalizer"
}
```
- Purpose: Normalizes exact values for consistent matching
- Example: "San Francisco" and "san francisco" both match

**`index_options`**: Controls what information is stored for text fields
```json
"full_content": {
  "type": "text",
  "index_options": "offsets"  // Stores term offsets for highlighting
}
```
- Options:
  - `docs`: Only doc numbers (smallest)
  - `freqs`: Doc numbers + term frequencies
  - `positions`: Above + term positions (default)
  - `offsets`: Above + character offsets (for highlighting)

### Object vs Nested Types

**Object Type** (default for JSON objects):
```json
"address": {
  "type": "object",
  "properties": {
    "street": {"type": "text"},
    "city": {"type": "keyword"}
  }
}
```
- Arrays of objects are flattened
- Can't query array items independently

**Nested Type** (for arrays of objects):
```json
"amenities": {
  "type": "nested",
  "properties": {
    "name": {"type": "keyword"},
    "available": {"type": "boolean"}
  }
}
```
- Maintains relationship between fields in array objects
- Allows independent queries on each array item
- Performance cost: Each nested doc is indexed separately

**Example showing the difference:**
```json
// Document with array of objects
{
  "amenities": [
    {"name": "pool", "available": true},
    {"name": "gym", "available": false}
  ]
}

// With object type (flattened):
// This incorrectly matches because values are mixed
{
  "query": {
    "bool": {
      "must": [
        {"match": {"amenities.name": "gym"}},
        {"match": {"amenities.available": true}}
      ]
    }
  }
}

// With nested type (preserved relationships):
// This correctly returns no results
{
  "query": {
    "nested": {
      "path": "amenities",
      "query": {
        "bool": {
          "must": [
            {"match": {"amenities.name": "gym"}},
            {"match": {"amenities.available": true}}
          ]
        }
      }
    }
  }
}
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

## 🚀 KNN Vector Search Configuration

### Dense Vector Fields for Semantic Search

The indexes are configured with **KNN (k-nearest neighbor)** search capability for AI-powered semantic similarity search.

**Configuration in templates:**
```json
"embedding": {
  "type": "dense_vector",
  "dims": 1024,
  "similarity": "cosine"
}
```

**Key Points:**
- **Dimensions**: 1024 (matching voyage-3 embedding model output)
- **Similarity**: Cosine (measures angle between vectors, ideal for semantic similarity)
- **KNN Enabled**: Automatically enabled in Elasticsearch 8.0+ (no need for explicit `"index": true`)
- **Model**: voyage-3 generates the embeddings during data pipeline processing

### How KNN Works

1. **Indexing Phase:**
   - Documents are processed through voyage-3 model to generate 1024-dimensional vectors
   - Vectors are indexed using HNSW (Hierarchical Navigable Small World) algorithm
   - Creates efficient graph structure for fast approximate nearest neighbor search

2. **Search Phase:**
   - Query text is embedded using same voyage-3 model
   - KNN query finds k most similar vectors using cosine similarity
   - Returns documents ranked by vector similarity score

### KNN Query Structure
```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],  // 1024 dimensions
    "k": 10,
    "num_candidates": 100
  }
}
```

**Parameters:**
- `k`: Number of nearest neighbors to return
- `num_candidates`: Number of candidates per shard to consider (higher = more accurate but slower)
- Default algorithm: HNSW with automatic parameter tuning

### Performance Characteristics
- **Speed**: Sub-second search on millions of vectors
- **Accuracy**: ~95% recall with default settings
- **Memory**: ~2GB per million 1024-dim vectors
- **Scaling**: Horizontal scaling via sharding

### Hybrid Search Capability
Combine KNN with traditional text search:
```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [...],
    "k": 50
  },
  "query": {
    "match": {
      "description": "modern home"
    }
  }
}
```
This enables powerful hybrid semantic + keyword search as recommended by Elastic.

## 🔍 Understanding Keyword vs Text Fields

### Practical Differences

**Keyword Field Example:**
```json
// Document
{"property_type": "Single Family Home"}

// Keyword field queries (exact match only):
GET properties/_search
{
  "query": {
    "term": {"property_type": "Single Family Home"}  // ✅ Matches
  }
}

{
  "query": {
    "term": {"property_type": "single family home"}  // ❌ No match (case sensitive)
  }
}

{
  "query": {
    "term": {"property_type": "Family Home"}  // ❌ No match (partial not allowed)
  }
}
```

**Text Field Example:**
```json
// Document
{"description": "Beautiful single family home with pool"}

// Text field queries (analyzed, flexible matching):
GET properties/_search
{
  "query": {
    "match": {"description": "family homes"}  // ✅ Matches (stemmed: homes→home)
  }
}

{
  "query": {
    "match": {"description": "BEAUTIFUL HOME"}  // ✅ Matches (case insensitive)
  }
}

{
  "query": {
    "match": {"description": "house pool"}  // ✅ Partial match (home≈house via synonyms)
  }
}
```

**Multi-field Usage Example:**
```json
// Mapping
"city": {
  "type": "text",
  "fields": {
    "keyword": {"type": "keyword"}
  }
}

// Document
{"city": "San Francisco"}

// Full-text search on city
GET properties/_search
{
  "query": {
    "match": {"city": "francisco"}  // ✅ Matches (partial text search)
  }
}

// Exact aggregation on city.keyword
GET properties/_search
{
  "aggs": {
    "cities": {
      "terms": {"field": "city.keyword"}  // Returns exact "San Francisco"
    }
  }
}

// Sorting on city.keyword
GET properties/_search
{
  "sort": [{"city.keyword": "asc"}]  // Sorts by exact city names
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

**Current Status:** The `wikipedia_ingest` pipeline is **ACTIVE** and used in production.

### Active Usage Details

#### 1. Wikipedia Content Enrichment (`real_estate_search/enrich_wikipedia_articles.py`)

The WikipediaEnricher class actively uses the pipeline when loading Wikipedia HTML content:

```python
# In WikipediaEnricher._perform_bulk_updates() at line 238
response = bulk(
    self.es,
    batch,
    pipeline=self.config.pipeline_name,  # Uses 'wikipedia_ingest_pipeline'
    stats_only=True,
    raise_on_error=False
)
```

**How it works:**
1. The enricher scans Wikipedia documents missing the `content_loaded` flag
2. Reads corresponding HTML files from disk (e.g., `../data/wikipedia_content/123456.html`)
3. Sends documents through the pipeline during bulk update
4. Pipeline automatically:
   - Strips HTML tags from `full_content`
   - Trims whitespace
   - Sets `content_loaded=true` and `content_loaded_at` timestamp
   - Calculates `content_length` from cleaned text

**Command-line usage:**
```bash
# Enrich all Wikipedia documents needing content
python real_estate_search/enrich_wikipedia_articles.py

# Specify custom pipeline
python real_estate_search/enrich_wikipedia_articles.py --pipeline custom_pipeline

# Dry run to preview changes
python real_estate_search/enrich_wikipedia_articles.py --dry-run
```

#### 2. Pipeline Configuration Location

- **Definition:** `elasticsearch/pipelines/wikipedia_ingest.json`
- **Default name:** `wikipedia_ingest_pipeline`
- **Index:** Applied to `wikipedia` index documents

#### 3. Pipeline must be created in Elasticsearch before use:

```bash
# Create the pipeline (one-time setup)
curl -X PUT "localhost:9200/_ingest/pipeline/wikipedia_ingest_pipeline" \
  -H 'Content-Type: application/json' \
  -d @real_estate_search/elasticsearch/pipelines/wikipedia_ingest.json
```

### Other Potential Usage Points

**Where pipelines could also be used:**
1. During initial bulk indexing in `data_pipeline/writers/elasticsearch/`
2. When updating documents through REST API endpoints
3. During real-time document updates

**To use in other code:**
```python
# Single document indexing with pipeline
es.index(
    index="wikipedia",
    document=doc,
    pipeline="wikipedia_ingest_pipeline"
)

# Bulk indexing with pipeline
bulk(es, actions, pipeline="wikipedia_ingest_pipeline")
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

## 🧬 What Happens Internally When You Add an Index Like `properties.json`

When you create an index in Elasticsearch using a mapping like `properties.json`, Elasticsearch (backed by Apache Lucene) builds a set of internal data structures for each field, optimized for different query types. Here’s what happens under the hood:

### 1. Inverted Index (Sparse Index)
- **Purpose:** Fast full-text search and filtering.
- **How it works:** For each token (word) in a text field, Lucene stores a list of document IDs where that token appears. This is called a *postings list*.
- **Sparse:** Most tokens appear in only a few documents, so the index is sparse (lots of empty space).
- **Used for:** `text` fields, `keyword` fields (for term queries), and any field with `index: true`.

### 2. Doc Values (Columnar Store)
- **Purpose:** Fast sorting, aggregations, and script access.
- **How it works:** Lucene stores each field’s value for all documents in a column-oriented format (like a table column), which is highly efficient for operations that need to scan all values of a field.
- **Default:** Enabled for `keyword`, numeric, date, and geo fields. Disabled for `text` fields unless explicitly enabled.
- **Columnar:** All values for a field are stored together, making it fast to access all values for a field across many documents.
- **Used for:** Sorting, aggregations, and accessing field values in scripts.

### 3. Norms (Optional, for Text Fields)
- **Purpose:** Improve relevance scoring in full-text search.
- **How it works:** Stores a small value per document per field, encoding information like field length and field-level boosts. This helps Elasticsearch score shorter fields higher (since a match in a short field is more significant).
- **Optional:** Enabled by default for `text` fields, can be disabled to save space if you don’t need scoring (e.g., for log data).
- **Used for:** BM25 and other relevance algorithms.

### 4. Dense Vector vs. Sparse Index
- **Dense Vector:**
  - **Purpose:** Semantic search (KNN, similarity search with ML embeddings).
  - **How it works:** Stores a fixed-length array (e.g., 1024 floats) per document. These are not indexed in the traditional inverted index, but in a special structure (HNSW graph) for fast nearest neighbor search.
  - **Columnar:** Stored as a block of floats per document, not as tokens.
  - **Use case:** AI-powered search, semantic similarity, hybrid search.
- **Sparse (Inverted) Index:**
  - **Purpose:** Traditional keyword and full-text search.
  - **How it works:** Stores only the terms that appear in each document, and which documents they appear in.
  - **Use case:** Filtering, keyword search, aggregations.

### 5. Storage and Performance Implications
- **Each field type adds its own internal structure:**
  - `text` fields: Inverted index + optional norms.
  - `keyword` fields: Inverted index + doc values (columnar store).
  - Numeric/date/geo fields: Doc values (columnar) + sometimes a small inverted index for range queries.
  - `dense_vector`: Special vector block, not part of the inverted index.
  - `nested` fields: Each nested object is stored as a hidden Lucene document, grouped with its parent.
- **Multi-fields:** If you define both `text` and `keyword` for a field, Elasticsearch stores both representations, increasing index size but enabling both full-text and exact-match queries.

### 6. Example: What Happens for a Field Like `description`
```json
"description": {
  "type": "text",
  "analyzer": "property_analyzer",
  "fields": {
    "keyword": {
      "type": "keyword",
      "ignore_above": 256
    }
  }
}
```
- **description (text):**
  - Indexed in the inverted index for full-text search.
  - Norms are stored for scoring.
  - Not stored in doc values (can’t sort/aggregate on this field).
- **description.keyword (keyword):**
  - Indexed for exact match.
  - Stored in doc values for sorting/aggregations.

### 7. Dense Vector Example
```json
"embedding": {
  "type": "dense_vector",
  "dims": 1024,
  "similarity": "cosine"
}
```
- **embedding:**
  - Stored as a block of 1024 floats per document.
  - Indexed using HNSW for fast KNN search.
  - Not part of the inverted index or doc values.

### 8. Summary Table
| Field Type      | Inverted Index | Doc Values (Columnar) | Norms | Dense Vector Block |
|-----------------|:-------------:|:---------------------:|:-----:|:------------------:|
| text            |      Yes      |          No           | Yes   |        No          |
| keyword         |      Yes      |         Yes           |  No   |        No          |
| numeric/date    |      No*      |         Yes           |  No   |        No          |
| geo_point       |      No*      |         Yes           |  No   |        No          |
| dense_vector    |      No       |          No           |  No   |       Yes          |
| nested          |      N/A      |         N/A           | N/A   |       N/A          |

*Numeric/date/geo fields may use a small BKD-tree index for range/geo queries, not a traditional inverted index.

### 9. Why This Matters
- **Query performance:** Each structure is optimized for different query types (text search, sorting, KNN, etc.).
- **Storage:** More fields and multi-fields increase disk usage, but enable more flexible queries.
- **Design tip:** Only add multi-fields or dense vectors if you need them for your queries.

