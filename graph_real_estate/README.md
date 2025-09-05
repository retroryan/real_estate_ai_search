# Graph Real Estate - Demo Searches

A Neo4j database initialization and demonstration module for the real estate knowledge graph system. Its primary purpose is to demonstrate the data stored by the data_pipeline/ Spark processing and is also used to initialize Neo4j. This module handles database schema creation, constraints, indexes, and provides utilities for managing the graph database structure.

The data ingestion is now done via the Spark Data Pipeline that does common data processing and vector embeddings and is in the data_pipeline/ module.

## Purpose

This module is responsible for:
- Demonstrating the data stored by the data_pipeline/ Spark processing
- Initializing the Neo4j database with proper schema
- Creating vector indexes for search
- Creating constraints and indexes for optimal performance
- Providing database management utilities (clear, stats)
- Preparing the database to receive data from the data pipeline

## Vector Embedding Configuration

The module uses the embedding model specified in `config.yaml` to create vector embeddings for semantic search:
- **Current Model**: Voyage-3 (1024 dimensions)
- **Similarity Function**: Cosine similarity
- **Hybrid Search Weights**: 60% vector, 20% graph, 20% features

## Installation

1. **Install Dependencies**
```bash
pip install neo4j python-dotenv
```

2. **Start Neo4j** (Docker)
```bash
docker-compose up -d
```

3. **Configure Environment**
Add to the parent directory `.env` file with your Neo4j credentials:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

4. **Configure Embeddings** (Optional)
To use vector embeddings, add your API key to the `.env` file:
```env
VOYAGE_API_KEY=your_voyage_api_key
```

## Usage

### Running from Parent Directory

The module is designed to run from the parent directory using Python's module execution:

```bash
# Run demonstration queries (requires populated database)

# **Vector Embedding Search Demos**
python -m graph_real_estate demo --demo 1  # Hybrid Search Demo - Combines vector embeddings with graph intelligence
python -m graph_real_estate demo --demo 5  # Pure Vector Search Demo - Semantic search using embeddings only

# Graph and Market Analysis Demos
python -m graph_real_estate demo --demo 2  # Graph Analysis Demo
python -m graph_real_estate demo --demo 3  # Market Intelligence Demo
python -m graph_real_estate demo --demo 4  # Wikipedia Enhanced Demo

# Run demo with verbose output
python -m graph_real_estate demo --demo 1 --verbose

# Initialize database with schema and indexes
python -m graph_real_estate init

# Initialize with database clearing (removes all existing data first)
python -m graph_real_estate init --clear

# Test database connection
python -m graph_real_estate test

# Show database statistics
python -m graph_real_estate stats

# Clear all data from database (interactive confirmation)
python -m graph_real_estate clear
```

### Command Details

#### `init` - Initialize Database
Creates all necessary constraints and indexes for the graph database:
- **Constraints**: Ensures unique identifiers for all node types
- **Indexes**: Optimizes query performance for common access patterns

#### `test` - Test Connection
Verifies that the Neo4j database is accessible and responding.

#### `stats` - Show Statistics
Displays current database statistics including:
- Node counts by type
- Relationship counts by type
- Total nodes and relationships

#### `clear` - Clear Database
Removes all nodes and relationships from the database (requires confirmation).

#### `demo` - Run Demonstrations
Executes demonstration scripts that showcase different aspects of the graph database:

**Vector Embedding Search Capabilities:**
- **Demo 1: Hybrid Search** - Combines vector embeddings with graph intelligence for powerful semantic search with contextual understanding. Uses the configured embedding model (Voyage-3) to perform similarity searches enhanced by graph relationships.
- **Demo 5: Pure Vector Search** - Semantic search using embeddings only. Demonstrates pure vector similarity search capabilities using the configured embedding model for finding semantically similar properties.

**Graph and Analysis Capabilities:**
- **Demo 2: Graph Analysis** - Explores relationships and graph patterns
- **Demo 3: Market Intelligence** - Advanced market analytics and insights
- **Demo 4: Wikipedia Enhanced** - Leverages Wikipedia integration

Note: Demos require a populated database. Run data ingestion first.

## Database Schema

### Node Types
The database is prepared to handle the following node types:
- **Property**: Real estate properties
- **Neighborhood**: Geographic neighborhoods
- **City**: City entities
- **County**: County entities
- **State**: State entities
- **Wikipedia**: Wikipedia article references
- **Feature**: Property features
- **PriceRange**: Price range categories
- **PropertyType**: Property type classifications

### Constraints Created
- `property_id`: Unique listing_id for properties
- `neighborhood_id`: Unique identifier for neighborhoods
- `city_id`: Unique identifier for cities
- `county_id`: Unique identifier for counties
- `state_id`: Unique identifier for states
- `wikipedia_id`: Unique page_id for Wikipedia articles
- `feature_name`: Unique name for features
- `price_range`: Unique range for price categories
- `property_type`: Unique name for property types

### Indexes Created
Performance indexes for:
- Property: price, type, bedrooms, city, state
- Neighborhood: city, state, walkability_score
- Wikipedia: relationship_type, confidence
- Geographic: city.state, county.state

## Architecture

```
graph_real_estate/
├── __init__.py           # Module initialization
├── __main__.py           # Entry point for python -m execution
├── main.py               # Main application logic
├── pyproject.toml        # Package configuration
├── utils/
│   ├── __init__.py       # Utils module initialization
│   ├── database.py       # Neo4j connection utilities
│   └── graph_builder.py  # Database initialization logic
├── archive/              # Legacy code for reference
├── config/               # Configuration files
├── demos/                # Demo scripts
└── tests/                # Test suite
```

## Integration with Data Pipeline

This module prepares the database structure for data that will be loaded from the `data_pipeline` module. After initialization:

1. Run the data pipeline to process and enrich data:
   ```bash
   python -m data_pipeline
   ```

2. Load the processed parquet files into the graph database

3. The schema and indexes ensure optimal performance for queries

## Sample Queries

### Vector Embedding Analysis

Once your database is populated with properties containing vector embeddings, you can use these Cypher queries to analyze and search the data:

#### 1. Basic Embedding Information
```cypher
// Get overview of embeddings in the database
MATCH (p:Property) 
WHERE p.embedding IS NOT NULL
RETURN 
    COUNT(p) as total_properties_with_embeddings,
    AVG(size(p.embedding)) as avg_embedding_dimensions,
    p.embedding_model as model_used,
    COUNT(DISTINCT p.city) as unique_cities,
    COUNT(DISTINCT p.state) as unique_states
```
**Query Explanation:** This query provides a high-level overview of vector embeddings in your database. It counts properties with embeddings, calculates the average vector dimension size (e.g., 1024 for Voyage-3), identifies which embedding model was used, and shows geographic distribution across cities and states.

#### 2. Properties by Location with Embedding Info
```cypher
// Properties grouped by location with embedding metadata
MATCH (p:Property)
WHERE p.embedding IS NOT NULL
RETURN 
    p.state,
    p.city,
    COUNT(p) as property_count,
    AVG(p.listing_price) as avg_price,
    AVG(p.square_feet) as avg_sqft,
    AVG(p.embedding_dimension) as embedding_dims,
    COLLECT(p.listing_id)[0..3] as sample_ids
ORDER BY property_count DESC
LIMIT 10
```
**Query Explanation:** Groups properties by geographic location to analyze market characteristics. Shows property counts, average prices, and square footage per city. The `COLLECT()[0..3]` syntax takes the first 3 listing IDs as examples. Useful for understanding which locations have the most embedded property data.

#### 3. Find Similar Properties by Embedding Text
```cypher
// Properties with similar embedding text (useful for debugging)
MATCH (p:Property)
WHERE p.embedding IS NOT NULL 
  AND p.embedding_text CONTAINS "mountain views"
RETURN 
    p.listing_id,
    p.city + ", " + p.state as location,
    p.bedrooms,
    p.bathrooms,
    p.square_feet,
    p.listing_price,
    p.embedding_text[0..100] + "..." as embedding_text_preview,
    size(p.embedding) as embedding_size
ORDER BY p.listing_price
LIMIT 5
```
**Query Explanation:** Searches for properties based on the text used to generate embeddings. The `CONTAINS` operator performs text search on the embedding source text. String concatenation (`+`) combines city and state. The `[0..100]` slice shows first 100 characters of text. Useful for debugging what content was embedded.

#### 4. Properties by Price Range with Embedding Analysis
```cypher
// Analyze embeddings across different price ranges
MATCH (p:Property)
WHERE p.embedding IS NOT NULL AND p.listing_price IS NOT NULL
WITH p, 
     CASE 
        WHEN p.listing_price < 300000 THEN "Under $300K"
        WHEN p.listing_price < 600000 THEN "$300K-$600K" 
        WHEN p.listing_price < 1000000 THEN "$600K-$1M"
        ELSE "Over $1M"
     END as price_category
RETURN 
    price_category,
    COUNT(p) as property_count,
    AVG(p.listing_price) as avg_price,
    AVG(p.square_feet) as avg_sqft,
    AVG(p.property_quality_score) as avg_quality,
    AVG(size(p.embedding)) as avg_embedding_dims,
    COLLECT(DISTINCT p.property_type)[0..3] as common_types
ORDER BY avg_price
```
**Query Explanation:** Uses a `CASE` expression to bucket properties into price ranges, then analyzes each bucket. The `WITH` clause creates the price categories before aggregation. Shows market segmentation with average metrics per price tier. `COLLECT(DISTINCT)` gets unique property types per range.

#### 5. Embedding Quality and Completeness Check
```cypher
// Check embedding quality and data completeness
MATCH (p:Property)
RETURN 
    COUNT(p) as total_properties,
    SUM(CASE WHEN p.embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embeddings,
    SUM(CASE WHEN p.embedding_text IS NOT NULL THEN 1 ELSE 0 END) as with_embedding_text,
    AVG(CASE WHEN p.embedding_text_length IS NOT NULL THEN p.embedding_text_length ELSE 0 END) as avg_text_length,
    COUNT(DISTINCT p.embedding_model) as embedding_models_used,
    COLLECT(DISTINCT p.embedding_model) as models_list
```
**Query Explanation:** Data quality audit query using conditional aggregation. `SUM(CASE...)` counts properties meeting specific conditions. Helps identify data gaps - how many properties have embeddings vs. just text. Shows if multiple embedding models were used (important for consistency).

#### 6. Properties with Rich Feature Sets
```cypher
// Find properties with rich descriptions and features (best for embeddings)
MATCH (p:Property)
WHERE p.embedding IS NOT NULL 
  AND p.embedding_text_length > 200
  AND size(p.features) >= 3
RETURN 
    p.listing_id,
    p.city + ", " + p.state as location,
    p.property_type,
    p.bedrooms + " bed, " + toString(p.bathrooms) + " bath" as bed_bath,
    p.square_feet as sqft,
    "$" + toString(p.listing_price) as price,
    size(p.features) as feature_count,
    p.features[0..3] as top_features,
    p.embedding_text_length as text_length,
    size(p.embedding) as embedding_dims
ORDER BY p.embedding_text_length DESC
LIMIT 10
```
**Query Explanation:** Identifies properties with rich content that produce high-quality embeddings. Filters by text length (>200 chars) and feature count (≥3). `toString()` converts numbers to strings for concatenation. `size()` gets array length. These properties are best for semantic search since they have more descriptive content.

#### 7. Vector Search Preparation Query
```cypher
// Prepare data for vector similarity search (extract embeddings as arrays)
MATCH (p:Property)
WHERE p.embedding IS NOT NULL
  AND p.city = "San Francisco"  // Filter by location
  AND p.bedrooms >= 2
RETURN 
    p.listing_id as id,
    p.embedding as vector,
    {
        city: p.city,
        bedrooms: p.bedrooms,
        bathrooms: p.bathrooms,
        sqft: p.square_feet,
        price: p.listing_price,
        type: p.property_type,
        features: p.features,
        description: p.description_cleaned
    } as metadata
LIMIT 50
```
**Query Explanation:** Formats data for external vector similarity calculations. Returns embeddings as raw vectors alongside metadata in a map/dictionary structure using `{}` syntax. The metadata object contains all property details needed after similarity matching. This format is ideal for feeding into vector search libraries.

#### 8. Neighborhoods with Embedding Statistics
```cypher
// Analyze neighborhoods by embedding coverage and property characteristics
MATCH (p:Property)
WHERE p.embedding IS NOT NULL
WITH p.neighborhood as neighborhood, 
     p.city + ", " + p.state as location,
     COLLECT(p) as properties
RETURN 
    neighborhood,
    location,
    size(properties) as property_count,
    AVG([prop IN properties | prop.listing_price]) as avg_price,
    AVG([prop IN properties | prop.square_feet]) as avg_sqft,
    AVG([prop IN properties | size(prop.features)]) as avg_features,
    AVG([prop IN properties | prop.embedding_text_length]) as avg_text_length,
    [prop IN properties | prop.property_type][0..3] as property_types_sample
ORDER BY property_count DESC
LIMIT 15
```
**Query Explanation:** Groups properties by neighborhood using `COLLECT()` to create lists. List comprehension syntax `[item IN list | expression]` extracts values from collected properties for aggregation. This pattern allows complex aggregations on grouped data. Shows neighborhood-level market analysis with embedding coverage.

#### 9. Time-based Embedding Analysis
```cypher
// Analyze when embeddings were created
MATCH (p:Property)
WHERE p.embedding IS NOT NULL AND p.embedded_at IS NOT NULL
RETURN 
    date(p.embedded_at) as embedding_date,
    COUNT(p) as properties_embedded,
    AVG(size(p.embedding)) as avg_dimensions,
    COUNT(DISTINCT p.embedding_model) as models_used,
    COLLECT(DISTINCT p.embedding_model) as models
ORDER BY embedding_date DESC
```
**Query Explanation:** Tracks embedding generation over time. The `date()` function extracts just the date part from timestamps. Useful for monitoring batch processing or identifying when different models were used. Helps track pipeline runs and model version changes.

#### 10. Properties Ready for Hybrid Search
```cypher
// Find properties that are well-suited for hybrid search (good embeddings + rich graph connections)
MATCH (p:Property)
WHERE p.embedding IS NOT NULL 
  AND p.embedding_text_length > 150
  AND p.features IS NOT NULL
  AND size(p.features) >= 2
OPTIONAL MATCH (p)-[r]-()
WITH p, COUNT(r) as relationship_count
RETURN 
    p.listing_id,
    p.city + ", " + p.state as location,
    p.bedrooms + "BR/" + toString(p.bathrooms) + "BA" as layout,
    p.square_feet as sqft,
    p.listing_price as price,
    size(p.features) as feature_count,
    p.embedding_text_length as text_length,
    size(p.embedding) as embedding_dims,
    relationship_count,
    p.property_quality_score as quality_score
ORDER BY (relationship_count * 0.3 + p.property_quality_score * 0.4 + size(p.features) * 0.3) DESC
LIMIT 20
```
**Query Explanation:** Identifies properties ideal for hybrid search combining vectors and graph. `OPTIONAL MATCH` finds relationships without filtering out nodes that lack them. The `(p)-[r]-()` pattern matches any relationship type in any direction. The ORDER BY uses a weighted formula to rank by multiple factors. These properties have both good embeddings and rich graph context for optimal search results.

### Usage Tips

- **Performance**: Always filter by `p.embedding IS NOT NULL` when working with vector data
- **Debugging**: Use the embedding text queries to understand what text was used to generate embeddings
- **Analysis**: The completeness check helps identify data quality issues
- **Search**: The vector search preparation query formats data for similarity calculations

### Running Queries

Execute these queries in:
- **Neo4j Browser**: `http://localhost:7474`
- **Python**: Using the `neo4j` driver
- **Demo Scripts**: Available in the `demos/` directory

## Next Steps

After database initialization:
1. Run the data pipeline to generate enriched parquet files
2. Use graph loading utilities to import the processed data
3. Create vector embeddings for semantic search capabilities
4. Run analytics and queries on the populated graph

## License

MIT