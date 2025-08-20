# Real Estate Graph Builder

A modular Neo4j graph database application for real estate data with Pydantic validation and vector embedding search capabilities.

## Architecture

This application follows a **clean, modular architecture** designed for maintainability and growth:

```
graph-real-estate/
├── src/                    # Source code (modular organization)
│   ├── models/            # Pydantic data models
│   │   ├── property.py    # Property-related models
│   │   ├── graph.py       # Graph node models
│   │   └── relationships.py # Relationship models
│   ├── data/              # Data loading and processing
│   │   └── loader.py      # JSON data loader with validation
│   ├── database/          # Database layer
│   │   └── neo4j_client.py # Neo4j connection and utilities
│   ├── controllers/       # Business logic
│   │   └── graph_builder.py # Main graph building logic
│   └── vectors/           # Vector embeddings and search
│       ├── models.py      # Embedding configuration models
│       ├── vector_manager.py # Neo4j vector index management
│       ├── embedding_pipeline.py # LlamaIndex embedding generation
│       ├── hybrid_search.py # Combined vector + graph search
│       └── config.yaml    # Vector configuration
├── config/                # Configuration
│   └── settings.py        # Application settings
├── main.py               # Entry point for graph building
├── create_embeddings.py  # Generate vector embeddings
├── search_properties.py  # Semantic search interface
├── requirements.txt      # Dependencies
├── .env                  # Environment variables
└── README.md            # This file
```

##  Features

- **Pydantic Validation**: All data structures validated with Pydantic models
- **Modular Design**: Clean separation of concerns for easy maintenance
- **Type Safety**: Full type hints throughout the codebase
- **Vector Embeddings**: Semantic search using LlamaIndex and Neo4j vector indexes
- **Hybrid Search**: Combines vector similarity with graph relationships
- **Multi-Provider Support**: Ollama, OpenAI, and Gemini embedding models
- **Advanced Filtering**: Price, location, and property detail filters
- **Scalable Architecture**: Ready for future enhancements
- **Neo4j Community Edition**: Uses free version of Neo4j with native vector support

##  Data Model

The graph consists of:
- **84 Properties** (44 San Francisco, 40 Park City)
- **387 Features** organized in 8 categories
- **21 Neighborhoods** across 2 cities
- **1,267 Relationships** connecting the data
- **768-dimensional vector embeddings** for each property
- **Neo4j native vector index** for similarity search

##  Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Start Neo4j** (Docker)
```bash
docker-compose up -d
```

3. **Configure Environment**
Edit `.env` file with your Neo4j credentials

4. **Install Ollama** (for local embeddings)
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull embedding model
ollama pull nomic-embed-text
```

## Usage

### 1. Build the Graph Database
```bash
# Run complete setup
python main.py all

# Run individual steps
python main.py setup          # Environment setup & data validation
python main.py schema         # Create core graph schema (nodes & properties)
python main.py relationships  # Create graph relationships

# Utilities
python main.py queries        # Run sample queries
python main.py interactive    # Interactive query mode
python main.py stats          # View database statistics
python main.py clear          # Clear all data
```

### 2. Create Vector Embeddings
```bash
# Generate embeddings for all properties
python create_embeddings.py

# Force recreate embeddings
python create_embeddings.py --force-recreate

# Use different embedding model
python create_embeddings.py --model mxbai-embed-large
```

### 3. Search Properties
```bash
# Natural language search
python search_properties.py "modern condo with city views"

# Search with filters
python search_properties.py "family home" --city "San Francisco" --price-max 2000000 --bedrooms-min 3

# Run demo with multiple queries
python search_properties.py --demo

# Disable graph boost (vector similarity only)
python search_properties.py "luxury property" --no-graph-boost
```

## Vector Search Features

### Hybrid Scoring Algorithm
The search combines multiple signals:
- **Vector Similarity (60%)**: Semantic similarity between query and property descriptions
- **Graph Centrality (20%)**: Importance based on graph connections
- **Feature Richness (20%)**: Number and quality of property features

**Note**: These weights (60/20/20) were implemented as a first-pass estimate. Future work should test and optimize these values using data-driven approaches:
- **A/B Testing** - Compare different weight combinations with real users
- **Reciprocal Rank Fusion (RRF)** - Weight-free ranking combination
- **Grid Search Optimization** - Systematic parameter tuning
- **Learned Weights** - Machine learning based on relevance feedback
- **Query-Adaptive Weights** - Different weights for different query types
- **Bayesian Optimization** - Efficient hyperparameter search

See `HYBRID_SEARCH.md` for detailed implementation proposals.

### Supported Filters
- `--price-min` / `--price-max`: Price range filtering
- `--city`: Filter by city name
- `--neighborhood`: Filter by neighborhood
- `--bedrooms-min`: Minimum number of bedrooms
- `--bathrooms-min`: Minimum number of bathrooms
- `--sqft-min`: Minimum square footage

### Embedding Providers
Configure in `src/vectors/config.yaml`:
- **Ollama** (default): Local embeddings with nomic-embed-text or mxbai-embed-large
- **OpenAI**: Using text-embedding-3-small or text-embedding-3-large
- **Gemini**: Google's embedding models

##  Sample Queries

After building the graph, you can run queries to explore:
- Properties by city
- Most expensive neighborhoods
- Feature distribution
- Similar properties
- Price ranges
- **Semantic search**: "luxury property with mountain views"
- **Lifestyle queries**: "family-friendly home near schools"
- **Investment queries**: "affordable property with rental potential"

##  Why Modular Architecture?

### Benefits:
1. **Separation of Concerns**: Each module has a single responsibility
2. **Testability**: Easy to unit test individual components
3. **Maintainability**: Changes in one module don't affect others
4. **Scalability**: Easy to add new features or data sources
5. **Reusability**: Components can be reused in other projects

### Module Responsibilities:

- **models/**: Data validation and type definitions
- **data/**: Data loading and transformation logic
- **database/**: Database operations and connection management
- **controllers/**: Business logic and orchestration
- **config/**: Centralized configuration management
- **vectors/**: Vector embeddings and semantic search
  - `vector_manager.py`: Neo4j vector index operations
  - `embedding_pipeline.py`: LlamaIndex-based embedding generation
  - `hybrid_search.py`: Combined vector + graph search logic

## Performance

- **Embedding Generation**: ~35 properties/second
- **Search Response**: < 100ms for top-10 results
- **Vector Index**: Native Neo4j ANN (Approximate Nearest Neighbor) search
- **Scalability**: Supports 100K+ properties with efficient indexing

## Future Enhancements

The modular structure makes it easy to add:
- Additional data sources
- New relationship types
- Advanced analytics
- API endpoints
- Caching layers
- Testing suites
- Multi-modal embeddings (images + text)
- Real-time embedding updates
- Personalized search with user preferences

##  License

MIT