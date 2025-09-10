# Demo Inventory - Phase 1 Documentation

## Complete Demo Registry (28 Demos)

### Core Search Demos (1-14)

#### Demo 1: Basic Property Search
- **Purpose**: Multi-match search across property fields
- **Query Type**: Multi-match full-text search
- **Index**: properties
- **Dependencies**: 
  - Elasticsearch running on port 9200
  - Properties index populated with data
- **Expected Output**: PropertySearchResult with list of matching properties
- **Success Criteria**: Returns at least 1 property with relevant fields (title, address, price, bedrooms, bathrooms)

#### Demo 2: Property Filter Search  
- **Purpose**: Filter properties by type, bedrooms, price, and location
- **Query Type**: Boolean query with multiple filters
- **Index**: properties
- **Dependencies**:
  - Properties index with proper field mappings
- **Expected Output**: PropertySearchResult with filtered properties
- **Success Criteria**: Properties match all filter criteria (type, price range, bedrooms, bathrooms)

#### Demo 3: Geographic Distance Search
- **Purpose**: Find properties within radius of a geographic point
- **Query Type**: Geo-distance query
- **Index**: properties  
- **Dependencies**:
  - Properties index with geo_point field mapping for location
  - Valid latitude/longitude coordinates in data
- **Expected Output**: PropertySearchResult with nearby properties sorted by distance
- **Success Criteria**: Properties within specified radius (default 5km), distance included in results

#### Demo 4: Neighborhood Statistics
- **Purpose**: Aggregate property statistics by neighborhood
- **Query Type**: Terms aggregation with sub-aggregations
- **Index**: properties
- **Dependencies**:
  - Properties index with neighborhood field
- **Expected Output**: AggregationSearchResult with stats per neighborhood
- **Success Criteria**: Returns aggregated data (avg price, property count) grouped by neighborhood

#### Demo 5: Price Distribution Analysis  
- **Purpose**: Histogram of prices by property type
- **Query Type**: Histogram aggregation with terms sub-aggregation
- **Index**: properties
- **Dependencies**:
  - Properties index with price and property_type fields
- **Expected Output**: AggregationSearchResult with price distribution buckets
- **Success Criteria**: Price histogram buckets with document counts per property type

#### Demo 6: Semantic Similarity Search
- **Purpose**: Find similar properties using embeddings
- **Query Type**: KNN vector search
- **Index**: properties
- **Dependencies**:
  - Properties index with vector embeddings
  - Embedding dimension matches index mapping (1024 for Voyage)
  - API key for embedding provider (Voyage/OpenAI/Gemini)
- **Expected Output**: PropertySearchResult with semantically similar properties
- **Success Criteria**: Returns properties with similarity scores, ordered by relevance

#### Demo 7: Multi-Entity Combined Search
- **Purpose**: Search across all entity types (properties, neighborhoods, Wikipedia)
- **Query Type**: Multi-index search
- **Indices**: properties, neighborhoods, wiki_*
- **Dependencies**:
  - All indices populated with data
  - Consistent field mappings across indices
- **Expected Output**: Combined results from multiple indices
- **Success Criteria**: Results from at least 2 different index types

#### Demo 8: Wikipedia Article Search
- **Purpose**: Search Wikipedia with location filters
- **Query Type**: Full-text search with geo-filtering
- **Index**: wikipedia
- **Dependencies**:
  - Wikipedia index populated with articles
  - Location fields (city, state) indexed
- **Expected Output**: WikipediaSearchResult with articles
- **Success Criteria**: Wikipedia articles with location metadata

#### Demo 9: Wikipedia Full-Text Search
- **Purpose**: Full-text search across Wikipedia articles
- **Query Type**: Match query on content field
- **Index**: wikipedia
- **Dependencies**:
  - Wikipedia index with full article content
  - Text analysis pipeline configured
- **Expected Output**: WikipediaSearchResult with matching articles
- **Success Criteria**: Articles matching search terms with relevance scores

#### Demo 10: Property Relationships via Denormalized Index
- **Purpose**: Single-query retrieval using denormalized index
- **Query Type**: Single document retrieval with nested data
- **Index**: properties_with_amenities_neighborhoods
- **Dependencies**:
  - Denormalized index with relationship data
  - Property-neighborhood-amenity relationships built
- **Expected Output**: Complete property data with related entities
- **Success Criteria**: Property with embedded neighborhood and amenity data

#### Demo 11: Natural Language Semantic Search
- **Purpose**: Convert natural language queries to embeddings for semantic search
- **Query Type**: KNN vector search from natural language
- **Index**: properties
- **Dependencies**:
  - Embedding API key configured
  - Properties index with vector embeddings
  - Embedding service accessible
- **Expected Output**: PropertySearchResult from natural language query
- **Success Criteria**: Relevant properties from conversational query

#### Demo 12: Natural Language Examples
- **Purpose**: Multiple examples of natural language property search
- **Query Type**: Multiple KNN searches from various queries
- **Index**: properties
- **Dependencies**:
  - Same as Demo 11
  - Multiple example queries configured
- **Expected Output**: List of DemoQueryResults
- **Success Criteria**: Each example returns relevant results

#### Demo 13: Semantic vs Keyword Comparison
- **Purpose**: Compare semantic embedding search with traditional keyword search
- **Query Type**: Both KNN and match queries
- **Index**: properties
- **Dependencies**:
  - Properties index with both text and vector fields
  - Embedding service for semantic search
- **Expected Output**: Comparison of semantic vs keyword results
- **Success Criteria**: Both search types return results, differences highlighted

#### Demo 14: Rich Real Estate Listing
- **Purpose**: Complete property listing with neighborhood and Wikipedia data
- **Query Type**: Multi-get with enrichment
- **Index**: properties_with_amenities_neighborhoods
- **Dependencies**:
  - Denormalized index fully populated
  - All relationship data built
- **Expected Output**: Rich property listing with all related data
- **Success Criteria**: Complete property details with neighborhood stats and Wikipedia context

### Hybrid & Location-Aware Demos (15-28)

#### Demo 15: Hybrid Search with RRF
- **Purpose**: Combines semantic vector search with text search using Reciprocal Rank Fusion
- **Query Type**: Hybrid query with RRF
- **Index**: properties
- **Dependencies**:
  - Elasticsearch 8.9+ for RRF support
  - Properties with both text and vector fields
- **Expected Output**: HybridSearchResult with combined ranking
- **Success Criteria**: Results combining both search methods with RRF scores

#### Demo 16: Location Understanding
- **Purpose**: Extract location information from natural language using DSPy
- **Query Type**: NLP location extraction
- **Dependencies**:
  - DSPy framework installed
  - LLM API key configured (OpenAI/Anthropic)
- **Expected Output**: Extracted location entities
- **Success Criteria**: Correctly identifies cities, neighborhoods, landmarks

#### Demo 17: Location-Aware: Waterfront Luxury
- **Purpose**: Luxury waterfront property search with city-specific filtering
- **Query Type**: Combined semantic and geo-filtering
- **Index**: properties
- **Dependencies**:
  - Location extraction service
  - Properties with waterfront amenities
- **Expected Output**: LocationAwareResult with waterfront properties
- **Success Criteria**: High-end waterfront properties in specified location

#### Demo 18: Location-Aware: Family Schools
- **Purpose**: Family-oriented search with school proximity
- **Query Type**: Geo-proximity to schools with family filters
- **Index**: properties
- **Dependencies**:
  - School location data
  - Family-friendly property attributes
- **Expected Output**: Properties near good schools
- **Success Criteria**: Family homes with school proximity scores

#### Demo 19: Location-Aware: Urban Modern
- **Purpose**: Modern urban property search with neighborhood understanding
- **Query Type**: Urban area filtering with style matching
- **Index**: properties
- **Dependencies**:
  - Urban neighborhood classifications
  - Modern property style tags
- **Expected Output**: Modern properties in urban areas
- **Success Criteria**: Contemporary properties in city centers

#### Demo 20: Location-Aware: Recreation Mountain
- **Purpose**: Recreation-focused property search in mountain areas
- **Query Type**: Geographic elevation with recreation amenities
- **Index**: properties
- **Dependencies**:
  - Mountain/elevation data
  - Recreation amenity tags
- **Expected Output**: Mountain properties with recreation access
- **Success Criteria**: Properties near ski resorts, hiking trails

#### Demo 21: Location-Aware: Historic Urban
- **Purpose**: Historic property search in urban neighborhoods
- **Query Type**: Historic designation with urban filtering
- **Index**: properties
- **Dependencies**:
  - Historic property data
  - Urban neighborhood boundaries
- **Expected Output**: Historic properties in cities
- **Success Criteria**: Properties with historic significance in urban areas

#### Demo 22: Location-Aware: Beach Proximity
- **Purpose**: Beach property search with proximity-based location understanding
- **Query Type**: Coastal geo-proximity search
- **Index**: properties
- **Dependencies**:
  - Coastal geography data
  - Beach proximity calculations
- **Expected Output**: Properties near beaches
- **Success Criteria**: Properties within specified distance of beaches

#### Demo 23: Location-Aware: Investment Market
- **Purpose**: Investment property search with market-specific targeting
- **Query Type**: Investment criteria with market analysis
- **Index**: properties
- **Dependencies**:
  - Market trend data
  - Investment property indicators
- **Expected Output**: Investment opportunities by market
- **Success Criteria**: Properties with positive ROI potential

#### Demo 24: Location-Aware: Luxury Urban Views
- **Purpose**: Luxury urban property search emphasizing premium views
- **Query Type**: High-end filters with view amenities
- **Index**: properties
- **Dependencies**:
  - View quality data
  - Luxury property indicators
- **Expected Output**: Luxury properties with views
- **Success Criteria**: High-end properties with city/water views

#### Demo 25: Location-Aware: Suburban Architecture
- **Purpose**: Architectural style search in suburban markets
- **Query Type**: Style matching in suburban areas
- **Index**: properties
- **Dependencies**:
  - Architectural style classifications
  - Suburban area definitions
- **Expected Output**: Properties by architectural style
- **Success Criteria**: Specific architectural styles in suburbs

#### Demo 26: Location-Aware: Neighborhood Character
- **Purpose**: Neighborhood character search with architectural details
- **Query Type**: Neighborhood analysis with style matching
- **Index**: properties, neighborhoods
- **Dependencies**:
  - Neighborhood character data
  - Architectural detail fields
- **Expected Output**: Properties matching neighborhood character
- **Success Criteria**: Properties consistent with neighborhood aesthetics

#### Demo 27: Location-Aware Search Showcase
- **Purpose**: Run multiple location-aware demos to showcase capabilities
- **Query Type**: Multiple combined queries
- **Index**: properties, neighborhoods, wikipedia
- **Dependencies**:
  - All location-aware features functional
  - All indices populated
- **Expected Output**: List of results from multiple demos
- **Success Criteria**: Each sub-demo returns valid results

#### Demo 28: Wikipedia Location Search
- **Purpose**: Wikipedia search with automatic location extraction from natural language
- **Query Type**: NLP location extraction + Wikipedia search
- **Index**: wikipedia
- **Dependencies**:
  - Location extraction service
  - Wikipedia index with location data
- **Expected Output**: Wikipedia articles for extracted location
- **Success Criteria**: Relevant Wikipedia articles for identified locations

## Result Structure Types

### 1. PropertySearchResult
- `query_name`: Demo name
- `execution_time_ms`: Query execution time
- `total_hits`: Total matching documents
- `returned_hits`: Documents returned
- `results`: List of PropertyListing objects
- `query_dsl`: Elasticsearch query DSL

### 2. WikipediaSearchResult  
- Same base fields as PropertySearchResult
- `results`: List of WikipediaArticle objects

### 3. AggregationSearchResult
- Same base fields
- `aggregations`: Dictionary of aggregation results
- `top_properties`: Sample properties if included

### 4. HybridSearchResult
- Extends PropertySearchResult
- `rrf_scores`: Reciprocal rank fusion scores
- `semantic_scores`: Vector similarity scores
- `text_scores`: BM25 text relevance scores

### 5. LocationAwareResult
- Extends PropertySearchResult
- `extracted_locations`: Identified location entities
- `location_confidence`: Confidence scores for extraction

## Common Dependencies

### Required Services
1. **Elasticsearch** (localhost:9200)
   - Version 8.11+ for RRF support
   - Security disabled for local development

2. **API Keys** (in .env file)
   - Embedding provider (Voyage/OpenAI/Gemini)
   - LLM provider for DSPy (OpenAI/Anthropic)

3. **Indices**
   - properties
   - neighborhoods
   - wikipedia
   - wiki_chunks
   - wiki_summaries
   - properties_with_amenities_neighborhoods

### Data Requirements
- Properties with complete fields (price, location, type, bedrooms, bathrooms)
- Geo-coordinates for all properties
- Vector embeddings (1024 dimensions for Voyage)
- Wikipedia articles with location metadata
- Neighborhood boundary and statistical data

## Baseline Success Criteria

### Minimum Requirements for All Demos
1. **No Exceptions**: Demo executes without errors
2. **Non-Empty Results**: Returns at least 1 result (except aggregations)
3. **Valid Response Structure**: Response matches expected model
4. **Reasonable Performance**: Execution time < 5000ms
5. **Relevant Results**: Results match query intent

### Quality Indicators
- **Text Search**: BM25 scores > 1.0
- **Vector Search**: Similarity scores > 0.7
- **Geo Search**: Distance calculations correct
- **Aggregations**: Buckets contain data
- **Multi-Index**: Results from multiple indices

## Phase 1 Completion Status

✅ **Task 1**: Listed all 28 available demos
✅ **Task 2**: Documented each demo's purpose and expected output
✅ **Task 3**: Identified demo dependencies (indices, data sources, APIs)
✅ **Task 4**: Mapped demo numbers to query types and search strategies
✅ **Task 5**: Documented expected result structure for each demo type
✅ **Task 6**: Created baseline success criteria for each demo

## Next Steps for Phase 2

1. Execute each demo sequentially (1-28)
2. Capture output and result counts
3. Identify demos returning zero results
4. Document specific failure modes
5. Create failure categorization report