# Graph Real Estate - Database Initialization Module

A Neo4j database initialization module for the real estate knowledge graph system. This module handles database schema creation, constraints, indexes, and provides utilities for managing the graph database structure.

## Purpose

This module is responsible for:
- Initializing the Neo4j database with proper schema
- Creating constraints and indexes for optimal performance
- Providing database management utilities (clear, stats)
- Preparing the database to receive data from the data pipeline

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
Create `.env` file with your Neo4j credentials:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

## Usage

### Running from Parent Directory

The module is designed to run from the parent directory using Python's module execution:

```bash
# Initialize database with schema and indexes
python -m graph-real-estate init

# Initialize with database clearing (removes all existing data first)
python -m graph-real-estate init --clear

# Test database connection
python -m graph-real-estate test

# Show database statistics
python -m graph-real-estate stats

# Clear all data from database (interactive confirmation)
python -m graph-real-estate clear

# Run demonstration queries (requires populated database)
python -m graph-real-estate demo --demo 1  # Hybrid Search Demo
python -m graph-real-estate demo --demo 2  # Graph Analysis Demo
python -m graph-real-estate demo --demo 3  # Market Intelligence Demo
python -m graph-real-estate demo --demo 4  # Wikipedia Enhanced Demo
python -m graph-real-estate demo --demo 5  # Pure Vector Search Demo

# Run demo with verbose output
python -m graph-real-estate demo --demo 1 --verbose
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
- **Demo 1**: Hybrid Search - Combines vector embeddings with graph intelligence
- **Demo 2**: Graph Analysis - Explores relationships and graph patterns
- **Demo 3**: Market Intelligence - Advanced market analytics and insights
- **Demo 4**: Wikipedia Enhanced - Leverages Wikipedia integration
- **Demo 5**: Pure Vector Search - Semantic search using embeddings only

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
graph-real-estate/
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

## Next Steps

After database initialization:
1. Run the data pipeline to generate enriched parquet files
2. Use graph loading utilities to import the processed data
3. Create vector embeddings for semantic search capabilities
4. Run analytics and queries on the populated graph

## License

MIT