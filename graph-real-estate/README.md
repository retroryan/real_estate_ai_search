# Real Estate Graph Builder - Enhanced Edition

A comprehensive GraphRAG system with advanced real estate intelligence, featuring Wikipedia integration, lifestyle-based property discovery, and sophisticated similarity analysis. Built on Neo4j with enhanced schema supporting features, neighborhoods with lifestyle tags, geographic hierarchy (City/County), and property similarity calculations.

## Enhanced Features

- **Enhanced Property Model**: Properties now include features arrays, price-per-square-foot calculations, and enriched descriptions
- **Geographic Hierarchy**: Full City → County relationship modeling with proper geographic organization  
- **Lifestyle-Based Discovery**: Neighborhoods tagged with lifestyle characteristics (tech-friendly, outdoor-recreation, ski-access, etc.)
- **Advanced Similarity**: Calculated property and neighborhood similarities based on multiple factors
- **Rich Analytics**: 26 different query types across 6 categories for comprehensive market analysis
- **Feature Categorization**: 416+ features organized into 8 categories (Interior, Kitchen, Outdoor, View, etc.)
- **Performance Optimized**: 7 constraints and 7 indexes for optimal query performance

## Generative AI Features

- **GraphRAG Architecture**: Combines knowledge graphs with vector embeddings for enhanced retrieval-augmented generation, enabling richer context for LLM applications
- **Multi-Model Embeddings**: Supports Ollama (local), OpenAI, and Google Gemini embedding models with configurable dimensions (768-1536)
- **Semantic Vector Search**: Natural language property search using LlamaIndex-generated embeddings stored in Neo4j's native vector indexes
- **Hybrid Scoring Algorithm**: Intelligent ranking that combines vector similarity, graph centrality, and feature richness for improved results
- **LlamaIndex Integration**: Embedding pipeline with automatic chunking, batching, and error handling
- **Neo4j Vector Indexes**: Native Approximate Nearest Neighbor (ANN) search with HNSW algorithm for sub-100ms query performance
- **Embedding Flexibility**: Easy switching between providers and models through configuration without code changes
- **Pydantic Validation**: All data structures validated with Pydantic models
- **Modular Design**: Clean separation of concerns for easy maintenance
- **Type Safety**: Full type hints throughout the codebase
- **Advanced Filtering**: Price, location, and property detail filters
- **Scalable Architecture**: Ready for future enhancements
- **Neo4j Community Edition**: Uses free version of Neo4j with native vector support

## Graph Data Model

The Neo4j graph database uses a rich, interconnected model that captures the complex relationships between properties, neighborhoods, features, and Wikipedia articles:

**Node Types:**
- **Property**: Enhanced with features array, price_per_sqft, timestamps, and enriched descriptions
- **Neighborhood**: Geographic areas with lifestyle tags, price trends, and enhanced attributes
- **Feature**: Categorized property attributes across 8 categories (Interior, Kitchen, Outdoor, View, Recreation, Technology, Parking, Other)
- **Wikipedia**: Encyclopedia articles with titles, summaries, confidence scores, and relationship types
- **City**: High-level geographic nodes with county relationships
- **County**: Regional organization for geographic hierarchy
- **PriceRange**: Market segmentation nodes for property grouping
- **PropertyType**: Property classification nodes

**Relationship Types:**
- **LOCATED_IN**: Properties to neighborhoods
- **IN_CITY**: Neighborhoods to cities  
- **IN_COUNTY**: Cities to counties
- **HAS_FEATURE**: Properties to their specific features
- **SIMILAR_TO**: Property and neighborhood similarities based on calculated scores
- **NEAR**: Neighborhood proximity relationships within cities
- **IN_PRICE_RANGE**: Properties to price range categories
- **TYPE_OF**: Properties to property types
- **DESCRIBES**: Wikipedia articles to neighborhoods with confidence scores

**Vector Layer:**
- **Property Embeddings**: High-dimensional vector representations of property descriptions stored directly on property nodes
- **Native Vector Index**: Neo4j's HNSW-based similarity search index for efficient nearest neighbor queries
- **Hybrid Attributes**: Each node contains both structured data (for filtering) and unstructured embeddings (for semantic search)

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
Edit `.env` file with your Neo4j credentials:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

4. **Configure Embeddings** (`config.yaml`)
The system supports three embedding providers. Edit `config.yaml` to configure:

```yaml
embedding:
  provider: ollama  # Options: ollama (local), openai, gemini
  
  # For Ollama (default - no API key needed)
  ollama_model: "nomic-embed-text"  # 768 dimensions
  # Alternative: "mxbai-embed-large" (1024 dimensions)
  
  # For OpenAI (requires OPENAI_API_KEY env var)
  openai_model: "text-embedding-3-small"  # 1536 dimensions
  
  # For Gemini (requires GEMINI_API_KEY env var)  
  gemini_model: "models/embedding-001"  # 768 dimensions

search:
  use_graph_boost: true  # Enable hybrid search
  vector_weight: 0.6     # 60% semantic similarity
  graph_weight: 0.2      # 20% graph relationships
  features_weight: 0.2   # 20% property features
```

5. **Install Ollama** (for local embeddings - recommended)
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

**Note**: Ollama provides free, local embeddings with no API limits. OpenAI and Gemini require API keys and have usage costs.

## Usage

### 1. Build the Knowledge Graph Database

The application uses a phased approach to build the knowledge graph:

```bash
# Run complete graph load (all phases) - RECOMMENDED
python main.py load

# Or run individual phases:
python main.py validate       # Phase 1: Validate data sources
python main.py geographic     # Phase 2: Load geographic foundation (States, Counties, Cities)
python main.py wikipedia      # Phase 3: Load Wikipedia knowledge layer
python main.py neighborhoods  # Phase 4: Load neighborhoods with correlations

# Utility commands:
python main.py verify         # Verify graph integrity after loading
python main.py stats          # Show database statistics
python main.py clear          # Clear all data
```

**Note**: The application has been refactored with a modular architecture using Pydantic models for type safety. The old commands (`setup`, `schema`, `relationships`) are deprecated but still recognized for backward compatibility.

### 2. Create Vector Embeddings
```bash
# Generate embeddings using config.yaml settings
python -m src.scripts.create_embeddings

# Force recreate all embeddings (delete existing and regenerate)
python -m src.scripts.create_embeddings --force-recreate
```

**Note**: All embedding settings (provider, model, dimensions) are configured in `config.yaml`. To use a different model like `mxbai-embed-large`, update the `ollama_model` setting in `config.yaml`.

## Quick Start - Running Demos

```bash
# Build the knowledge graph database with Wikipedia integration
python main.py load

# Create embeddings (required for demos 1, 3, and 5)
python -m src.scripts.create_embeddings

# Run advanced demonstration scripts (from src/demos/)
python -m src.demos.demo_1_hybrid_search      # Advanced hybrid search
python -m src.demos.demo_2_graph_analysis     # Graph relationship analysis
python -m src.demos.demo_3_market_intelligence # Market intelligence
python -m src.demos.demo_4_wikipedia_enhanced  # Wikipedia-enhanced listings
python -m src.demos.demo_5_pure_vector_search  # Pure vector embedding search
```

See [Advanced Demo Scripts](#advanced-demo-scripts-) section below for detailed information about each demo.

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

### 4. Utility Commands
```bash
# View database statistics
python main.py stats

# Run enhanced demo queries (26 query types)
python main.py queries

# Interactive query mode
python main.py interactive

# Clear all data
python main.py clear
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

## Enhanced Query System

The system includes **26 different query types** across **6 categories**:

### Query Categories & Examples

**Basic Queries (6 types):**
- Properties by city and geographic hierarchy  
- Enhanced properties overview with feature statistics
- Property type and bedroom distributions

**Neighborhood Analytics (5 types):**
- Most expensive neighborhoods with comprehensive stats
- Lifestyle-based neighborhood discovery  
- Neighborhood similarity analysis with lifestyle matching

**Feature Analysis (4 types):**
- Popular features across 8 categories
- Luxury feature combinations
- Feature category performance analysis

**Price Analytics (3 types):**
- Price range distributions and market segmentation
- Price per square foot analysis by city
- Best value properties (lowest price/sqft)

**Similarity Analysis (2 types):**  
- Property similarity scores and perfect matches
- Advanced similarity analysis with multiple factors

**Advanced Analytics (6 types):**
- Market segmentation (Entry Level, Mid Market, Upper Market, Luxury)
- Investment opportunities (underpriced vs neighborhood average)
- Feature correlation analysis
- Lifestyle property analysis
- Comprehensive property profiles with all enhancements

### Sample Query Results
```bash
python main.py queries
# Lifestyle Neighborhoods: tech-friendly (11), urban (11), outdoor-recreation (10)
# Most Expensive: Deer Valley $10.2M avg, Promontory $5.1M avg
# Popular Features: Mountain views (89), City views (85), Bike storage (83)
# Property Similarities: 812 high-similarity pairs (>0.8 score)
```

## Architecture

This application follows a **clean, modular architecture** designed for maintainability and growth.

### Project Structure

```
graph-real-estate/
├── config.yaml            # Embedding and search configuration
├── src/                    # Source code (enhanced modular organization)
│   ├── models/            # Pydantic data models (enhanced)
│   │   ├── property.py    # Enhanced property models with features
│   │   ├── graph.py       # Graph node models + lifestyle/geographic
│   │   └── relationships.py # Relationship models + similarities
│   ├── data_loader/       # Enhanced data loading
│   │   ├── loader.py      # Enhanced JSON loader with Wikipedia support
│   │   └── __init__.py    # Enhanced data loading functions
│   ├── database/          # Enhanced database layer
│   │   ├── neo4j_client.py # Neo4j connection and utilities
│   │   ├── connection.py   # Enhanced connection management
│   │   └── transaction_manager.py # Transaction handling
│   ├── controllers/       # Enhanced business logic
│   │   └── graph_builder.py # Enhanced graph builder with 8 steps
│   ├── queries/           # NEW: Comprehensive query system
│   │   ├── query_library.py # 26 queries across 6 categories
│   │   ├── query_runner.py  # Query execution engine
│   │   └── __init__.py     # Query system exports
│   ├── demos/             # NEW: Enhanced demonstrations
│   │   ├── demo_queries.py  # Enhanced demo with new analytics
│   │   └── __init__.py     # Demo exports
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

## Performance & Scale

**Enhanced Database Metrics:**
- **Total Nodes**: 867 (up from basic schema)
- **Total Relationships**: 6,447 (comprehensive connections)
- **Query Performance**: All queries execute <100ms with proper indexing
- **Feature Processing**: 3,257 property-feature relationships
- **Similarity Calculations**: 1,707 relationships with scoring
- **Schema Optimization**: 7 constraints + 7 indexes for optimal performance

**Build Performance:**
- **Schema Creation**: ~2 seconds for complete enhanced schema
- **Data Import**: 420 properties with all features in ~5 seconds  
- **Relationship Creation**: 6,447 relationships calculated in ~10 seconds
- **Similarity Analysis**: Property and neighborhood similarities in ~8 seconds
- **Total Build Time**: Complete enhanced database in ~30 seconds

## Wikipedia Integration

The enhanced graph database now includes **full Wikipedia integration**, transforming static property listings into rich, contextual narratives:

### Wikipedia Features
- **131 Wikipedia Articles**: Integrated as nodes in the graph database
- **235 DESCRIBES Relationships**: Connecting Wikipedia articles to neighborhoods
- **100+ Enriched Properties**: Properties with Wikipedia-powered descriptions
- **Multiple Relationship Types**: primary, cultural, park, landmark, transit, school
- **Confidence Scoring**: Each Wikipedia relationship has a confidence score (0.0-1.0)

### Wikipedia Data Model
```cypher
// Wikipedia Node
(w:Wikipedia {
  page_id: INTEGER,        // Wikipedia page ID
  title: STRING,           // Article title
  summary: STRING,         // Short summary (500 chars)
  url: STRING,             // Wikipedia URL (stored but not fetched)
  confidence: FLOAT,       // Confidence score (0.0-1.0)
  is_synthetic: BOOLEAN,   // True if confidence < 0.5
  relationship_type: STRING // Type of relationship to neighborhood
})

// DESCRIBES Relationship
(w:Wikipedia)-[:DESCRIBES {
  confidence: FLOAT,
  discovered_via: STRING
}]->(n:Neighborhood)
```

### Wikipedia Enhancement Process
1. **Data Source**: Wikipedia data from `data/wikipedia/wikipedia.db`
2. **Automatic Import**: During `python main.py all`, Wikipedia articles are imported
3. **Relationship Creation**: Articles linked to neighborhoods based on geographic relevance
4. **Property Enrichment**: Property descriptions enhanced with neighborhood Wikipedia context
5. **URL Storage**: Wikipedia URLs stored for reference (content is in database, not fetched)

### Using Wikipedia Features
```python
# Find properties near cultural landmarks
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
WHERE w.relationship_type = 'cultural'
RETURN p, n, w.title

# Get neighborhood Wikipedia context
MATCH (n:Neighborhood {name: 'Pacific Heights'})<-[:DESCRIBES]-(w:Wikipedia)
RETURN w.title, w.relationship_type, w.confidence
ORDER BY w.confidence DESC

# Properties with rich Wikipedia context
MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
MATCH (n)<-[:DESCRIBES]-(w:Wikipedia)
WITH p, n, count(w) as wiki_count
WHERE wiki_count > 5
RETURN p, n, wiki_count
```

## Advanced Demo Scripts

The system includes **five comprehensive demonstration scripts** that showcase the full power of vector embeddings, hybrid search, Neo4j graph relationships, and Wikipedia integration for professional-grade real estate market intelligence.

### Demo 1: Advanced Hybrid Search (`demo_1_hybrid_search.py`)

**Purpose**: Demonstrates sophisticated search capabilities combining vector embeddings with graph intelligence for property discovery.

**Key Features:**
- **Semantic Understanding**: Natural language queries like "waterfront luxury with investment potential"
- **Graph Intelligence**: Leverages property similarity networks and neighborhood relationships
- **Feature Correlations**: Discovers properties through complex feature co-occurrence patterns
- **Multi-Criteria Search**: Combines price, location, lifestyle, and semantic factors
- **Geographic Intelligence**: Understands regional preferences and market positioning

**Demo Sections:**
1. **Basic Semantic Search** - Natural language property discovery
2. **Graph-Enhanced Search** - Similarity network exploration
3. **Feature-Based Discovery** - Complex feature combination queries
4. **Multi-Criteria Analysis** - Investment-focused property discovery
5. **Geographic Market Intelligence** - Location-based market insights


**Use Cases:**
- Real estate agents discovering unique property combinations
- Investors finding properties with specific investment characteristics
- Buyers with complex, multi-faceted requirements

---

### Demo 2: Graph Relationship Analysis (`demo_2_graph_analysis.py`)

**Purpose**: Explores the deep relationship networks within the graph database to uncover hidden patterns and market insights.

**Key Features:**
- **Similarity Networks**: Analyzes property and neighborhood similarity clusters
- **Feature Co-occurrence**: Discovers which features commonly appear together
- **Geographic Hierarchies**: Explores city-neighborhood-property relationships
- **Lifestyle Communities**: Identifies lifestyle-based market segments
- **Investment Patterns**: Uncovers investment opportunity patterns
- **Complex Graph Traversals**: Multi-hop relationship analysis

**Demo Sections:**
1. **Property Similarity Networks** - Clusters of highly similar properties
2. **Feature Co-occurrence Analysis** - Feature combination patterns and market impact
3. **Geographic Relationship Mapping** - City-neighborhood-property hierarchies
4. **Lifestyle Community Discovery** - Lifestyle tag-based market segmentation
5. **Investment Pattern Analysis** - ROI and market opportunity discovery
6. **Complex Graph Traversals** - Multi-hop relationship exploration


**Use Cases:**
- Market researchers analyzing property relationship patterns
- Developers understanding feature combinations that create value
- Investors identifying emerging market clusters

---

### Demo 3: Market Intelligence (`demo_3_market_intelligence.py`)

**Purpose**: Provides comprehensive market analysis capabilities using graph relationships and vector embeddings for professional real estate intelligence.

**Key Features:**
- **Geographic Market Analysis** - City and neighborhood performance metrics
- **Price Prediction & Trends** - Feature-based pricing intelligence
- **Investment Opportunity Discovery** - ROI analysis and market gap identification
- **Lifestyle Market Segmentation** - Demographic and preference analysis
- **Feature Impact Analysis** - Quantifying feature value and market impact
- **Competitive Intelligence** - Property positioning and market dynamics

**Demo Sections:**
1. **Geographic Market Analysis**
   - City-level market overview and performance metrics
   - Neighborhood market segmentation (Ultra-Luxury, Luxury, Premium, Mid-Market, Affordable)
   - Geographic arbitrage opportunities across neighborhoods

2. **Price Prediction & Trends Analysis**
   - Feature value impact analysis with premium calculations
   - Property type pricing intelligence across markets
   - Pricing anomaly detection using statistical analysis

3. **Investment Opportunity Discovery**
   - Undervalued market segments (high features, lower prices)
   - Emerging market indicators (diversity and growth potential)
   - AI-powered investment portfolio recommendations

4. **Lifestyle Market Segmentation**
   - Lifestyle preference market analysis
   - Lifestyle-feature correlation matrix
   - Market size calculations by lifestyle segment

5. **Feature Impact Analysis**
   - Feature category performance analysis
   - Feature co-occurrence network analysis with lift calculations
   - Feature rarity and exclusivity analysis

6. **Competitive Market Intelligence**
   - Competitive property cluster analysis
   - Market positioning intelligence
   - Market gap analysis and opportunity identification


**Use Cases:**
- Real estate professionals conducting market research
- Investment firms analyzing market opportunities
- Property developers identifying market gaps
- Market analysts creating comprehensive reports

---

### Demo 4: Wikipedia-Enhanced Listings (`demo_4_wikipedia_enhanced.py`)

**Purpose**: Showcases how Wikipedia integration transforms static property listings into rich, contextual narratives with cultural and historical insights.

**Key Features:**
- **Property Enhancement**: Listings enriched with Wikipedia neighborhood context
- **Cultural Intelligence**: Properties near cultural and historical landmarks
- **Neighborhood Profiles**: Deep neighborhood analysis using Wikipedia data
- **Investment Insights**: Market opportunities based on Wikipedia significance
- **Lifestyle Discovery**: Match properties to lifestyle preferences via Wikipedia
- **Comparative Analysis**: Compare neighborhoods using Wikipedia-derived intelligence

**Demo Sections:**
1. **Basic Wikipedia Enhancement** - Properties with enriched descriptions
2. **Cultural & Historical Context** - Landmarks and cultural significance
3. **Neighborhood Intelligence** - Comprehensive profiles from Wikipedia
4. **Investment Insights** - Wikipedia density and market opportunities
5. **Lifestyle Discovery** - Urban cultural, nature, historic preferences
6. **Comparative Market Analysis** - Neighborhood comparison matrix


**Use Cases:**
- Real estate agents providing rich context to clients
- Buyers seeking culturally significant neighborhoods
- Investors identifying historically important areas
- Lifestyle-focused property searches

---

### Demo 5: Pure Vector Embedding Search (`demo_5_pure_vector_search.py`)

**Purpose**: Demonstrates pure vector similarity search without graph boosting, showing the raw power of semantic embeddings for property discovery.

**Key Features:**
- **Pure Semantic Search**: Natural language queries using only embeddings
- **Semantic Understanding**: Shows how embeddings capture meaning beyond keywords
- **Cross-Domain Similarity**: Finding properties through abstract descriptions
- **Threshold Analysis**: Understanding similarity scores and quality
- **Vector vs Hybrid**: Direct comparison with graph-enhanced results
- **Embedding Space**: Exploration of property clusters in vector space

**Demo Sections:**
1. **Basic Semantic Search** - Natural language property queries
2. **Semantic Understanding** - Demonstrating meaning capture
3. **Cross-Domain Similarity** - Abstract and metaphorical queries
4. **Similarity Thresholds** - Score analysis and quality metrics
5. **Vector vs Hybrid Comparison** - Pure vs graph-enhanced results
6. **Embedding Space Exploration** - Property clustering analysis

**Key Insights:**
- Embeddings understand semantic meaning, not just keywords
- Similarity scores >0.8 indicate excellent matches
- Abstract queries like "James Bond style bachelor pad" work
- Properties naturally cluster in embedding space
- Hybrid search adds graph intelligence for better results

**Use Cases:**
- Understanding what embeddings alone can achieve
- Semantic search without graph dependencies
- Finding properties through creative descriptions
- Benchmarking embedding model performance

---


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