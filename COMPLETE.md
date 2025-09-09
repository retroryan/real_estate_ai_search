# Real Estate Search - Request Flow Architecture

## Overview
This document describes the complete request flow when executing `./es-manager.sh demo` command, tracing through all search layers and services.

## High-Level Request Flow

```
User --> es-manager.sh --> Python Management CLI --> Demo Runner --> Search Services --> Elasticsearch
                                                          |
                                                          v
                                                    Query Building
                                                          |
                                                          v
                                                  Embedding Generation
                                                          |
                                                          v
                                                    Hybrid Search
                                                          |
                                                          v
                                                    Result Fusion
```

## Detailed Layer-by-Layer Flow

### 1. Shell Script Entry Point (`es-manager.sh`)

```
User executes: ./es-manager.sh demo [number]
                        |
                        v
            Activates Python virtual environment
                        |
                        v
        Executes: python -m real_estate_search.management demo [number]
```

**Key Operations:**
- Validates environment setup
- Activates virtual environment
- Passes control to Python management module

### 2. Python Management CLI Layer

```
real_estate_search.management.__main__.py
                |
                v
        cli.py::main()
                |
                v
        Parse CLI arguments
                |
                v
        Load configuration (config.yaml)
                |
                v
        Create DemoCommand instance
                |
                v
        command.execute()
```

**Components:**
- **CLIParser**: Parses command-line arguments
- **AppConfig**: Loads configuration from YAML files
- **DemoCommand**: Coordinates demo execution

### 3. Demo Runner Layer

```
DemoCommand
    |
    v
DemoRunner (demo_runner.py)
    |
    v
Demo Registry (maps demo numbers to functions)
    |
    v
Execute specific demo function (e.g., demo_rich_property_listing)
```

**Demo Registry Structure:**
- Demo 1-14: Core search demos
- Demo 15-27: Hybrid and location-aware demos
- Each demo maps to a specific query function

### 4. Search Service Layer

```
Demo Function (e.g., demo_rich_property_listing)
                    |
                    v
        HybridSearchEngine.search()
                    |
        +-----------+-----------+
        |                       |
        v                       v
QueryEmbeddingService    LocationUnderstanding
        |                       |
        v                       v
Generate embeddings      Extract location intent
        |                       |
        +-----------+-----------+
                    |
                    v
            Build RRF Query
```

**Key Services:**
- **HybridSearchEngine**: Orchestrates hybrid search with RRF
- **QueryEmbeddingService**: Generates vector embeddings for semantic search
- **LocationUnderstandingModule**: Extracts geographic intent from queries
- **LocationFilterBuilder**: Builds Elasticsearch geo filters

### 5. Query Building Layer

```
HybridSearchEngine._build_rrf_query()
            |
            v
    Create RRF Retriever
            |
    +-------+-------+
    |               |
    v               v
Text Retriever  KNN Retriever
    |               |
    v               v
BM25 Scoring   Vector Similarity
    |               |
    +-------+-------+
            |
            v
    Reciprocal Rank Fusion
```

**Query Components:**
- **Text Retriever**: Traditional keyword search using BM25
- **KNN Retriever**: Vector similarity search using embeddings
- **RRF Parameters**: rank_constant=60, window_size=100

### 6. Elasticsearch Execution Layer

```
Elasticsearch Query
        |
        v
Index Selection (properties, neighborhoods, wikipedia)
        |
        v
Query Execution
        |
        +-----------+-----------+
        |           |           |
        v           v           v
    Text Search  Vector     Geo Filters
    (BM25)      Search      (if applicable)
        |           |           |
        +-----------+-----------+
                    |
                    v
            Result Ranking (RRF)
                    |
                    v
            Return Results
```

**Elasticsearch Operations:**
- Multi-index search across properties, neighborhoods, wikipedia
- Native RRF implementation for result fusion
- Geo-spatial filtering for location-based queries

### 7. Result Processing Layer

```
Raw Elasticsearch Results
            |
            v
    HybridSearchResult
            |
            v
    Format for Display
            |
            v
    Demo Output Formatter
            |
            v
    Console Display
```

**Result Components:**
- Total hits count
- Individual search results with scores
- Source data (property details, neighborhood info, etc.)
- Execution metadata (query time, index used)

## Data Flow Example: Demo 14 (Rich Property Listing)

```
1. User: ./es-manager.sh demo 14
            |
2. Shell: python -m real_estate_search.management demo 14
            |
3. CLI: DemoCommand(demo_number=14).execute()
            |
4. Runner: demo_rich_property_listing()
            |
5. Query Build:
   - Text: "luxury waterfront property San Francisco"
   - Embedding: [0.123, -0.456, ...] (1024 dimensions)
   - Location: {city: "San Francisco", state: "CA"}
            |
6. Elasticsearch RRF Query:
   {
     "retriever": {
       "rrf": {
         "retrievers": [
           {"standard": {"query": {...}}},  // Text search
           {"knn": {"field": "embedding", ...}}  // Vector search
         ],
         "rank_constant": 60
       }
     }
   }
            |
7. Results:
   - Property data
   - Neighborhood demographics
   - Wikipedia articles
   - Combined relevance scores
            |
8. Display: Formatted console output with property details
```

## Service Dependencies

```
                    AppConfig
                        |
        +---------------+---------------+
        |               |               |
        v               v               v
ElasticsearchClient  EmbeddingService  LocationModule
        |               |               |
        +---------------+---------------+
                        |
                        v
                HybridSearchEngine
                        |
                        v
                    DemoRunner
                        |
                        v
                    CLI Output
```

## Configuration Flow

```
.env (API Keys)
    |
    v
config.yaml (Main config)
    |
    +--> Elasticsearch settings
    +--> Embedding provider config
    +--> Index configurations
    +--> Search parameters
```

## Key Configuration Files:
- `/real_estate_search/.env`: API keys for embedding providers
- `/real_estate_search/config.yaml`: Elasticsearch and search settings
- `/squack_pipeline/config.yaml`: Pipeline and data processing settings

## Performance Optimizations

1. **Connection Pooling**: Reuses Elasticsearch connections
2. **Embedding Caching**: Caches frequently used query embeddings
3. **Batch Processing**: Processes multiple documents in batches
4. **Index Optimization**: Uses appropriate mappings and settings
5. **RRF Window Size**: Limits initial retrieval to top 100 docs per retriever

## Error Handling Flow

```
Any Layer Error
    |
    v
Exception Caught
    |
    v
Log Error Details
    |
    v
Return OperationStatus(success=False)
    |
    v
Display Error to User
```

## Summary

The `./es-manager.sh demo` command initiates a sophisticated multi-layer search pipeline that:

1. **Orchestrates** search operations through Python management CLI
2. **Generates** semantic embeddings for query understanding
3. **Extracts** location intent for geographic filtering
4. **Executes** hybrid search combining text and vector retrieval
5. **Fuses** results using Reciprocal Rank Fusion
6. **Returns** enriched property data with neighborhood and Wikipedia context

This architecture enables powerful semantic search capabilities while maintaining the precision of traditional keyword search, all unified through Elasticsearch's native RRF implementation.