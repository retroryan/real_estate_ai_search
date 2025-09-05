# SQUACK Pipeline V2 - DuckDB Medallion Architecture

A clean, efficient data pipeline following DuckDB best practices and medallion architecture principles.

## Overview

SQUACK Pipeline V2 is a complete rewrite of the original pipeline, implementing:
- **Medallion Architecture**: Bronze → Silver → Gold data tiers
- **DuckDB Best Practices**: SQL-first transformations, direct file operations
- **Clean Separation**: Each stage has a single responsibility
- **Type Safety**: Pydantic V2 models for validation at boundaries
- **Efficient Processing**: No row-by-row operations, all set-based SQL

## Architecture

```
Bronze Layer (Raw Ingestion)
    ↓
Silver Layer (Standardization)
    ↓
Gold Layer (Enrichment)
    ↓
Embeddings (Vector Generation)
    ↓
Writers (Parquet/Elasticsearch)
```

## Quick Start

### Installation

```bash
# Ensure you're in the real_estate_ai_search directory
cd real_estate_ai_search

# Install dependencies (if not already installed)
pip install -e .
```

### Basic Usage

```bash
# Run full pipeline
python -m squack_pipeline_v2

# Test with sample data
python -m squack_pipeline_v2 --sample-size 100

# Process specific entities
python -m squack_pipeline_v2 --entities property neighborhood

# View statistics
python -m squack_pipeline_v2 --stats
```

### Advanced Options

```bash
# Skip certain stages (use existing tables)
python -m squack_pipeline_v2 --skip-bronze --skip-silver

# Disable embeddings
python -m squack_pipeline_v2 --no-embeddings

# Export to Elasticsearch
python -m squack_pipeline_v2 --elasticsearch --es-host localhost --es-port 9200

# Validate configuration only
python -m squack_pipeline_v2 --validate-only

# Clean all tables
python -m squack_pipeline_v2 --clean
```

## Key Features

### 1. SQL-First Design
All data transformations are done in SQL, leveraging DuckDB's columnar engine:
```sql
-- Example from Silver layer
CREATE TABLE silver_properties AS
SELECT 
    listing_id as property_id,
    CAST(price AS DECIMAL(12,2)) as price,
    TRIM(UPPER(state)) as state_code
FROM bronze_properties
WHERE price > 0;
```

### 2. Direct File Operations
DuckDB reads and writes files directly without Python intermediates:
```sql
-- Bronze ingestion
CREATE TABLE bronze_properties AS 
SELECT * FROM read_json_auto('data/properties.json');

-- Parquet export
COPY gold_properties TO 'output/properties.parquet' (FORMAT PARQUET);
```

### 3. Pydantic for Validation
Models validate data at system boundaries, not for internal transformations:
```python
class PropertyDocument(BaseModel):
    """Validated property document for Elasticsearch."""
    property_id: str
    price: float = Field(gt=0)
    bedrooms: int = Field(ge=0, le=20)
```

### 4. Clean Layer Separation
- **Bronze**: Raw data ingestion with minimal changes
- **Silver**: Data standardization and cleaning
- **Gold**: Business logic and enrichment
- **Embeddings**: Vector generation for search
- **Writers**: Export to external systems

## Project Structure

```
squack_pipeline_v2/
├── __main__.py              # CLI entry point
├── config.yaml              # Default configuration
├── core/                    # Core infrastructure
│   ├── connection.py        # DuckDB connection manager
│   ├── settings.py          # Pydantic configuration
│   └── logging.py           # Structured logging
├── models/                  # Pydantic data models
│   ├── bronze/              # Raw data models
│   ├── silver/              # Standardized models
│   ├── gold/                # Enriched models
│   └── pipeline/            # Pipeline metrics
├── bronze/                  # Bronze layer (ingestion)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── silver/                  # Silver layer (standardization)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── gold/                    # Gold layer (enrichment)
│   ├── property.py
│   ├── neighborhood.py
│   └── wikipedia.py
├── embeddings/              # Embedding generation
│   ├── generator.py
│   └── providers.py
├── writers/                 # Data export
│   ├── parquet.py          # Parquet writer
│   └── elasticsearch.py    # Elasticsearch writer
└── orchestration/           # Pipeline coordination
    └── pipeline.py
```

## Configuration

### Environment Variables
Create a `.env` file in the parent directory:
```bash
VOYAGE_API_KEY=your-voyage-key
OPENAI_API_KEY=your-openai-key
```

### Pipeline Configuration
Edit `config.yaml` for pipeline settings:
```yaml
database:
  path: "pipeline.duckdb"

data_paths:
  properties_file: "../real_estate_data/properties_sf.json"
  neighborhoods_file: "../real_estate_data/neighborhoods_sf.json"
  wikipedia_dir: "../real_estate_data/wikipedia"

embedding:
  enabled: true
  provider: "voyage"
  model_name: "voyage-3"
  dimension: 1024

output:
  parquet_dir: "output/parquet"
```

## DuckDB Best Practices Implemented

1. **SQL-First Transformations**: All data processing uses SQL
2. **Columnar Processing**: Leverages DuckDB's columnar engine
3. **Direct File Operations**: No unnecessary data movement
4. **Batch Processing**: No row-by-row operations
5. **Native COPY Commands**: Efficient import/export
6. **Set-Based Operations**: All transformations are set-based
7. **Minimal Python**: Python only for orchestration and API calls

## Performance

The pipeline processes data efficiently:
- **Bronze Layer**: Direct file reading with `read_json_auto()`
- **Silver Layer**: SQL transformations in DuckDB
- **Gold Layer**: SQL joins and aggregations
- **Embeddings**: Batch processing with configurable size
- **Writers**: Native COPY for Parquet, bulk operations for Elasticsearch

## Testing

```bash
# Run with test data
python -m squack_pipeline_v2 --sample-size 10 --verbose

# Validate configuration
python -m squack_pipeline_v2 --validate-only

# Check table statistics
python -m squack_pipeline_v2 --stats
```

## Migration from V1

The V2 pipeline is completely independent:
1. Lives in separate `squack_pipeline_v2/` directory
2. Uses different table names (prefixed with tier)
3. Can run alongside V1 for validation
4. No changes required to V1 code

## Key Improvements over V1

1. **Clear Architecture**: Medallion pattern with distinct layers
2. **Better Performance**: SQL-first with no Python loops
3. **Maintainable**: Single responsibility per module
4. **Type Safety**: Pydantic V2 throughout
5. **Testable**: Clean interfaces and separation
6. **Extensible**: Easy to add new entity types
7. **Observable**: Comprehensive logging and metrics

## Troubleshooting

### Common Issues

**DuckDB file locked**: Ensure no other process is using the database
```bash
# Use a different database file
python -m squack_pipeline_v2 --database test.duckdb
```

**Embedding API errors**: Check API keys in `.env`
```bash
# Disable embeddings for testing
python -m squack_pipeline_v2 --no-embeddings
```

**Memory issues with large datasets**: Use sampling
```bash
# Process smaller batches
python -m squack_pipeline_v2 --sample-size 1000
```

## Next Steps

1. **Add Integration Tests**: SQL-based testing of transformations
2. **Performance Benchmarks**: Compare with V1 pipeline
3. **Production Validation**: Run parallel with V1 for verification
4. **Documentation**: Expand documentation for each module
5. **Monitoring**: Add metrics collection and dashboards

## Neo4j Graph Database Integration

The SQUACK Pipeline V2 includes comprehensive support for exporting data to Neo4j as a knowledge graph, enabling powerful graph-based queries and relationships analysis.

### Architecture Overview

The Neo4j integration follows the medallion architecture pattern:
1. **Gold Layer**: Graph tables are created in the `gold/graph_builder.py` module
2. **Graph Tables**: Separate node and relationship tables optimized for Neo4j export
3. **Neo4j Writer**: Efficient batch writer in `writers/neo4j.py` using official Neo4j driver

### How It Works

#### 1. Graph Table Preparation (Gold Layer)

The `GoldGraphBuilder` creates specialized tables in DuckDB that are optimized for Neo4j export:

**Node Tables Created:**
- `gold_graph_properties` - Real estate property nodes
- `gold_graph_neighborhoods` - Neighborhood nodes  
- `gold_graph_wikipedia` - Wikipedia article nodes
- `gold_graph_features` - Property feature nodes
- `gold_graph_cities` - City nodes
- `gold_graph_states` - State nodes
- `gold_graph_zip_codes` - ZIP code nodes
- `gold_graph_counties` - County nodes
- `gold_graph_property_types` - Property type category nodes
- `gold_graph_price_ranges` - Price range bucket nodes

**Relationship Tables Created:**
- `gold_graph_rel_located_in` - Properties located in neighborhoods
- `gold_graph_rel_has_feature` - Properties with specific features
- `gold_graph_rel_part_of` - Neighborhoods part of cities
- `gold_graph_rel_in_county` - Neighborhoods in counties
- `gold_graph_rel_describes` - Wikipedia articles describing neighborhoods
- `gold_graph_rel_of_type` - Properties of specific types
- `gold_graph_rel_in_price_range` - Properties in price ranges
- `gold_graph_rel_in_zip_code` - Properties/neighborhoods in ZIP codes
- `gold_graph_geographic_hierarchy` - Geographic containment relationships

#### 2. Neo4j Write Process

The `Neo4jWriter` class handles the export to Neo4j using Cypher queries:

##### Node Creation Process

For each node type, the writer:
1. Reads all records from the DuckDB table
2. Uses `MERGE` statements to create/update nodes
3. Sets all properties from the table columns

Example Cypher query for property nodes:
```cypher
UNWIND $nodes AS node
MERGE (p:Property {listing_id: node.listing_id})
SET p += node
```

**Understanding the UNWIND Query Pattern:**

- **`UNWIND $nodes AS node`**: UNWIND is a Cypher clause that transforms a list into individual rows. It takes the `$nodes` parameter (a list of property records from DuckDB) and processes each element one at a time, binding it to the variable `node`. Think of it like a foreach loop that "unwinds" or "unpacks" a list.
  
  For example, if `$nodes` contains:
  ```json
  [
    {"listing_id": "123", "price": 500000, "bedrooms": 3},
    {"listing_id": "456", "price": 750000, "bedrooms": 4}
  ]
  ```
  UNWIND creates two rows, each with one `node` object.

- **`MERGE (p:Property {listing_id: node.listing_id})`**: MERGE is like an "upsert" operation. It looks for a Property node with the specified listing_id. If found, it binds it to variable `p`. If not found, it creates a new Property node with that listing_id. This prevents duplicate nodes from being created.

- **`SET p += node`**: This sets all properties from the `node` object onto the Property node `p`. The `+=` operator means "add all properties from the right side to the left side". So all fields from the DuckDB record (price, bedrooms, location, etc.) are added as properties to the Neo4j node. Existing properties are overwritten, new ones are added.

##### Relationship Creation Process

For each relationship type:
1. Reads relationship records from DuckDB tables
2. Matches source and target nodes by ID
3. Creates relationships using `MERGE`

Example Cypher query for LOCATED_IN relationships:
```cypher
UNWIND $rels AS rel
MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})
MATCH (n:Neighborhood {neighborhood_id: REPLACE(rel.to_id, 'neighborhood:', '')})
MERGE (p)-[:LOCATED_IN]->(n)
```

**Understanding the Relationship Creation Pattern:**

- **`UNWIND $rels AS rel`**: Similar to node creation, UNWIND takes a list of relationship records from DuckDB and processes each one individually. Each `rel` object contains `from_id` and `to_id` fields that identify the source and target nodes.

- **`MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})`**: This finds the source Property node. The `REPLACE` function strips the 'property:' prefix from the ID. For example, if `rel.from_id` is 'property:123', it becomes '123' to match the property's listing_id. MATCH will fail if the node doesn't exist, ensuring we only create relationships between existing nodes.

- **`MATCH (n:Neighborhood {neighborhood_id: REPLACE(rel.to_id, 'neighborhood:', '')})`**: Similarly, this finds the target Neighborhood node by removing the 'neighborhood:' prefix from the ID. Both nodes must exist for the relationship to be created.

- **`MERGE (p)-[:LOCATED_IN]->(n)`**: This creates a directed relationship of type LOCATED_IN from the Property to the Neighborhood. MERGE ensures the relationship is only created once - if it already exists, it won't create a duplicate. The arrow `->` indicates direction: properties are located IN neighborhoods.

This pattern ensures data integrity by:
1. Only creating relationships between existing nodes (MATCH fails if nodes don't exist)
2. Preventing duplicate relationships (MERGE is idempotent)
3. Maintaining consistent relationship direction for graph traversal

#### 3. Graph Schema

The resulting Neo4j graph follows this schema:

**Core Entity Nodes:**
- `(:Property)` - Real estate listings with price, bedrooms, location, etc.
- `(:Neighborhood)` - Neighborhoods with demographics and statistics
- `(:Wikipedia)` - Wikipedia articles with content and summaries

**Dimension Nodes:**
- `(:City)`, `(:State)`, `(:County)`, `(:ZipCode)` - Geographic entities
- `(:PropertyType)` - Property categories (house, condo, etc.)
- `(:PriceRange)` - Price buckets for analysis
- `(:Feature)` - Property features (pool, garage, etc.)

**Relationships:**
- `(:Property)-[:LOCATED_IN]->(:Neighborhood)` - Property location
- `(:Property)-[:HAS_FEATURE]->(:Feature)` - Property features
- `(:Property)-[:OF_TYPE]->(:PropertyType)` - Property categorization
- `(:Property)-[:IN_PRICE_RANGE]->(:PriceRange)` - Price categorization
- `(:Property)-[:IN_ZIP_CODE]->(:ZipCode)` - ZIP code location
- `(:Neighborhood)-[:PART_OF]->(:City)` - City containment
- `(:Neighborhood)-[:IN_COUNTY]->(:County)` - County containment
- `(:Wikipedia)-[:DESCRIBES]->(:Neighborhood)` - Article associations
- Geographic hierarchy relationships for navigation

### Query Examples

Once loaded into Neo4j, you can run powerful graph queries:

#### Find Similar Properties
```cypher
MATCH (p1:Property {listing_id: 'prop_123'})-[:HAS_FEATURE]->(f:Feature)
MATCH (p2:Property)-[:HAS_FEATURE]->(f)
WHERE p1 <> p2
RETURN p2, COUNT(f) as shared_features
ORDER BY shared_features DESC
LIMIT 10
```

**Query Explanation:**
- **Line 1**: `MATCH (p1:Property {listing_id: 'prop_123'})-[:HAS_FEATURE]->(f:Feature)` - Finds the target property (prop_123) and all features it has. The pattern `()-[:HAS_FEATURE]->()` traverses the HAS_FEATURE relationship to find all Feature nodes connected to this property.
- **Line 2**: `MATCH (p2:Property)-[:HAS_FEATURE]->(f)` - Finds other properties that share the same features. By reusing the variable `f` from line 1, we're matching properties that have at least one feature in common with prop_123.
- **Line 3**: `WHERE p1 <> p2` - Excludes the original property from results (we don't want to recommend the same property to itself).
- **Line 4**: `RETURN p2, COUNT(f) as shared_features` - Returns each matching property and counts how many features it shares with the target.
- **Line 5-6**: Results are sorted by most shared features first, limited to top 10 matches. This creates a "similarity score" based on shared amenities.

#### Neighborhood Analysis
```cypher
MATCH (n:Neighborhood {name: 'Mission District'})
MATCH (p:Property)-[:LOCATED_IN]->(n)
MATCH (p)-[:IN_PRICE_RANGE]->(pr:PriceRange)
RETURN pr.range_label, COUNT(p) as property_count
ORDER BY property_count DESC
```

**Query Explanation:**
- **Line 1**: `MATCH (n:Neighborhood {name: 'Mission District'})` - Finds the specific neighborhood node by name.
- **Line 2**: `MATCH (p:Property)-[:LOCATED_IN]->(n)` - Finds all properties in that neighborhood. The pattern uses the `n` variable from line 1 to ensure we only get properties in Mission District.
- **Line 3**: `MATCH (p)-[:IN_PRICE_RANGE]->(pr:PriceRange)` - For each property, finds which price range bucket it belongs to.
- **Line 4**: `RETURN pr.range_label, COUNT(p) as property_count` - Groups properties by price range and counts them. This aggregation shows the price distribution.
- **Line 5**: Results are ordered by count, showing which price ranges are most common in the neighborhood. This helps understand the neighborhood's market composition.

#### Geographic Navigation
```cypher
MATCH path = (p:Property)-[:LOCATED_IN]->(:Neighborhood)
  -[:PART_OF]->(:City)-[:IN_STATE]->(:State)
WHERE p.listing_id = 'prop_456'
RETURN path
```

**Query Explanation:**
- **Line 1-2**: `MATCH path = (p:Property)-[:LOCATED_IN]->(:Neighborhood)-[:PART_OF]->(:City)-[:IN_STATE]->(:State)` - Defines a path pattern that traverses the geographic hierarchy. The `path =` assignment captures the entire traversal as a path object.
- The pattern chains multiple relationships: Property → Neighborhood → City → State
- Anonymous nodes like `(:Neighborhood)` match any node of that type (we don't need to bind them to variables)
- **Line 3**: `WHERE p.listing_id = 'prop_456'` - Filters to a specific property as the starting point.
- **Line 4**: `RETURN path` - Returns the complete path, which Neo4j can visualize as a connected graph showing the property's full geographic context.
- This query demonstrates graph traversal across multiple relationship types to understand entity hierarchies.

#### Wikipedia-Enhanced Search
```cypher
MATCH (w:Wikipedia)-[:DESCRIBES]->(n:Neighborhood)<-[:LOCATED_IN]-(p:Property)
WHERE w.content CONTAINS 'historic district'
AND p.price < 1000000
RETURN p.listing_id, p.price, n.name, w.title
```

**Query Explanation:**
- **Line 1**: `MATCH (w:Wikipedia)-[:DESCRIBES]->(n:Neighborhood)<-[:LOCATED_IN]-(p:Property)` - Complex pattern matching that finds properties in neighborhoods that have Wikipedia articles. Note the bidirectional pattern:
  - `(w)-[:DESCRIBES]->(n)` - Wikipedia articles describing neighborhoods (forward direction)
  - `(n)<-[:LOCATED_IN]-(p)` - Properties located in those neighborhoods (reverse direction, note the `<-`)
  - This creates a triangle: Wikipedia → Neighborhood ← Property
- **Line 2**: `WHERE w.content CONTAINS 'historic district'` - Filters to Wikipedia articles mentioning "historic district" in their content. This enables semantic search based on neighborhood characteristics.
- **Line 3**: `AND p.price < 1000000` - Additional filter for affordability, combining text search with numeric filters.
- **Line 4**: Returns property details along with neighborhood name and Wikipedia article title, providing context for why each property matched.
- This query showcases the power of graph databases: combining structured data (price) with unstructured text (Wikipedia content) through relationships.

### Configuration

Neo4j configuration in `config.yaml`:
```yaml
neo4j:
  enabled: true
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "your-password"
  database: "neo4j"
```

### Running Neo4j Export

```bash
# Run pipeline with Neo4j export
python -m squack_pipeline_v2 --neo4j

# Neo4j export only (requires Gold tables exist)
python -m squack_pipeline_v2 --skip-bronze --skip-silver --neo4j

# Configure Neo4j connection
python -m squack_pipeline_v2 --neo4j \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --neo4j-password mypassword
```

### Performance Optimizations

The Neo4j writer implements several optimizations:

1. **Batch Processing**: Records are sent to Neo4j in batches
2. **MERGE Operations**: Prevents duplicate nodes/relationships
3. **Constraint Creation**: Ensures uniqueness and improves performance
4. **Direct DuckDB Access**: No pandas conversion, uses native iteration
5. **Parallel Potential**: Node types can be loaded in parallel

### Constraints and Indexes

The writer automatically creates these constraints:
- `Property(listing_id)` - Unique property IDs
- `Neighborhood(neighborhood_id)` - Unique neighborhood IDs
- `Wikipedia(wikipedia_id)` - Unique article IDs
- `Feature(feature_id)` - Unique feature IDs
- And similar constraints for all dimension nodes

### Monitoring and Metadata

The writer provides detailed metadata about the export:
- Number of nodes created per type
- Number of relationships created per type
- Time taken for each operation
- Total nodes and relationships
- Success/failure status

Example output:
```
Neo4j write complete: 5000 nodes, 12000 relationships in 45.2s
- Property nodes: 1000 created
- Neighborhood nodes: 50 created
- LOCATED_IN relationships: 1000 created
- HAS_FEATURE relationships: 8000 created
```

### Troubleshooting Neo4j Export

**Connection Issues:**
```bash
# Test Neo4j connection
cypher-shell -u neo4j -p password "RETURN 1"
```

**Memory Issues with Large Datasets:**
```bash
# Process in smaller batches
python -m squack_pipeline_v2 --sample-size 1000 --neo4j
```

**Constraint Violations:**
```cypher
// Check for duplicate IDs in Neo4j
MATCH (p:Property)
WITH p.listing_id as id, COUNT(*) as count
WHERE count > 1
RETURN id, count
```

**Clear Neo4j Database:**
```cypher
// WARNING: Deletes all data
MATCH (n) DETACH DELETE n
```

## License

Same as parent project.