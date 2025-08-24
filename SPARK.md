# Apache Spark Data Pipeline Architecture Proposal

## Executive Summary

This proposal outlines a comprehensive redesign of the `common_ingest/` and `common_embeddings/` modules into a unified `data_pipeline/` system using Apache Spark. The new architecture eliminates API servers and provides direct data pipeline integration, creating a single, scalable DataFrame output for downstream consumers while maintaining data quality and type safety.

## Current Architecture Analysis

### Existing System Complexity
- **common_ingest/**: API-based ingestion with FastAPI server, separate loaders, and service layers
- **common_embeddings/**: Embedding generation pipeline with ChromaDB storage and evaluation frameworks
- **Fragmentation**: Two separate systems requiring coordination
- **API Overhead**: REST endpoints add latency and complexity for internal data flows
- **Scaling Limitations**: Single-node processing with manual batch management

### Data Flow Issues
1. Load JSON files → Apply enrichment → Serve via API
2. Separate process: Load data → Generate embeddings → Store in ChromaDB  
3. Downstream consumers must call APIs for data access
4. No unified data model or processing pipeline
5. Manual coordination between ingestion and embedding generation

## Proposed Spark Architecture

### Core Design Philosophy

**Simplicity Through Unification**: Combine all data loading, enrichment, and embedding generation into a single, unified Spark pipeline that produces one comprehensive DataFrame for all downstream consumption.

**Direct Pipeline Architecture**: Eliminate API servers and REST endpoints. Data flows directly from sources through transformations to a final unified DataFrame that downstream services can consume directly via Spark connectors.

**Distributed Processing**: Leverage Spark's distributed computing model to handle large datasets efficiently across multiple nodes.

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Data Sources  │────│  Spark Pipeline  │────│  Unified DataFrame  │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
│                      │                      │                     │
├─ properties.json    ├─ Unified Loader     ├─ Enriched Entities   │
├─ neighborhoods.json ├─ Data Enrichment    ├─ Generated Embeddings │
├─ wikipedia.db       ├─ Embedding Pipeline ├─ Correlation Metadata │
└─ Additional sources └─ Quality Validation └─ Type-Safe Schema    │
                                                                    │
                      ┌─────────────────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────────────┐
            │   Downstream Services   │
            ├─────────────────────────┤
            │ ▸ Search Service        │
            │ ▸ Analytics Engine      │  
            │ ▸ ML Training Pipeline  │
            │ ▸ Real-time APIs        │
            │ ▸ Data Export Tools     │
            └─────────────────────────┘
```

### Module Structure

```
data_pipeline/
├── pyproject.toml                   # Package configuration
├── config/
│   ├── pipeline_config.yaml         # Main pipeline configuration
│   ├── embedding_providers.yaml     # Embedding model configurations
│   └── data_sources.yaml           # Source definitions
├── core/
│   ├── __init__.py
│   ├── spark_session.py            # Spark session management
│   ├── pipeline_runner.py          # Main orchestration
│   └── config_manager.py           # Configuration handling
├── ingestion/
│   ├── __init__.py
│   ├── unified_loader.py           # Multi-source data loading
│   ├── source_adapters.py          # Format-specific adapters
│   └── data_validation.py          # Schema validation
├── processing/
│   ├── __init__.py
│   ├── enrichment_engine.py        # Data enrichment transformations
│   ├── embedding_generator.py      # Distributed embedding generation
│   ├── text_chunker.py             # Text chunking for embeddings
│   └── quality_assurance.py        # Data quality checks
├── schemas/
│   ├── __init__.py
│   ├── unified_schema.py           # Final DataFrame schema
│   ├── source_schemas.py           # Input data schemas
│   └── metadata_models.py          # Metadata structures
├── utils/
│   ├── __init__.py
│   ├── spark_utils.py              # Spark helper functions
│   ├── embedding_providers.py      # Provider implementations
│   └── performance_monitoring.py   # Pipeline metrics
├── examples/
│   ├── basic_pipeline.py           # Simple usage example
│   ├── advanced_pipeline.py        # Complex transformations
│   └── consumer_examples.py        # Downstream usage patterns
└── tests/
    ├── unit/                       # Unit tests
    ├── integration/                # Integration tests
    └── performance/                # Performance benchmarks
```

## Detailed Component Design

### 1. Unified Data Loading (`ingestion/`) ✅ IMPLEMENTED

**Challenge**: Current system has separate loaders for different data formats (JSON files, SQLite database) with different APIs and processing patterns.

**Solution**: Leverages Spark's native DataFrameReader for JSON and pure Python approach for SQLite.

**Implementation Status**: ✅ Completed and Optimized
- Created `data_pipeline/ingestion/spark_native_loader.py` using Spark's built-in capabilities
- Uses native `spark.read.json()` for JSON files with schema support
- Implements pure Python pandas/sqlite3 approach for SQLite (no JDBC required)
- Follows Spark best practices with efficient `select` transformations

**Key Benefits**:
- **Native Spark APIs**: Uses DataFrameReader.json() for optimal performance
- **Pure Python SQLite**: No Java dependencies, simpler deployment
- **Schema-Aware**: Defines schemas for better performance
- **Best Practices**: Single `select` instead of multiple `withColumn` calls
- **Demo-Friendly**: Clean, simple implementation perfect for demonstrations

### 2. Data Enrichment Engine (`processing/enrichment_engine.py`)

**Challenge**: Current system applies enrichments in Python using individual record processing, which doesn't scale well.

**Solution**: Spark SQL-based enrichment that processes entire datasets distributedly.

**Implementation Status**: ✅ Completed in Phase 3

**Key Benefits**:
- **Simple and Clean**: Straightforward Spark SQL transformations
- **Easy to Understand**: Clear, readable data enrichment logic  
- **Maintainable**: Standard Spark operations following best practices
- **Demo-Ready**: Clean implementation perfect for demonstrations

### 3. Distributed Embedding Generation (`processing/embedding_generator.py`)

**Challenge**: Current system generates embeddings sequentially with manual batching, creating a bottleneck.

**Solution**: Simple Spark UDF-based embedding generation using proven provider patterns from `common_embeddings/`. **COPY AND PASTE** existing embedding provider logic from `common_embeddings/embedding/factory.py` (NOT the ChromaDB storage parts) to maintain the same high-quality embedding generation as DataFrame columns.

**Implementation Status**: 🔄 Ready for Phase 4 implementation (simplified - no ChromaDB storage)

**Key Benefits**:
- **Simplified Architecture**: Embeddings generated directly as DataFrame columns (no ChromaDB)
- **Proven Provider Patterns**: Reuses battle-tested provider logic from `common_embeddings/`
- **Provider Flexibility**: Maintains same provider support (Ollama, Voyage, OpenAI)
- **Demo-Ready**: Clean, straightforward UDF implementation
- **No Storage Complexity**: Eliminates ChromaDB storage and correlation management

### 4. Unified Output Schema (`schemas/unified_schema.py`)

**Challenge**: Current system produces data in different formats (API responses, ChromaDB collections, etc.) making downstream consumption complex.

**Solution**: Single, comprehensive DataFrame schema that contains all enriched data and embeddings.

```python
from pyspark.sql.types import *

class UnifiedDataSchema:
    """Unified schema for all processed data."""
    
    @staticmethod
    def get_schema() -> StructType:
        """Get the complete unified schema."""
        return StructType([
            # Core entity fields
            StructField("entity_id", StringType(), False),
            StructField("entity_type", StringType(), False),  # PROPERTY | NEIGHBORHOOD | WIKIPEDIA_ARTICLE
            StructField("correlation_uuid", StringType(), False),
            
            # Location fields
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("city_normalized", StringType(), True),
            StructField("state_normalized", StringType(), True),
            
            # Property-specific fields
            StructField("property_type", StringType(), True),
            StructField("price", DecimalType(12, 2), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("price_per_sqft", DecimalType(10, 4), True),
            
            # Content and features
            StructField("features", ArrayType(StringType()), True),
            StructField("features_normalized", ArrayType(StringType()), True),
            StructField("content", StringType(), True),
            StructField("embedding_text", StringType(), True),
            
            # Embeddings and ML fields
            StructField("embedding", ArrayType(FloatType()), True),
            StructField("embedding_model", StringType(), True),
            StructField("embedding_dimension", IntegerType(), True),
            StructField("chunk_index", LongType(), True),
            
            # Quality and metadata
            StructField("content_hash", StringType(), False),
            StructField("data_quality_score", DoubleType(), True),
            StructField("validation_status", StringType(), True),
            
            # Source tracking
            StructField("raw_data", StringType(), True),  # Original JSON
            StructField("source_file", StringType(), True),
            StructField("source_type", StringType(), False),
            
            # Processing timestamps
            StructField("ingested_at", TimestampType(), False),
            StructField("processed_at", TimestampType(), False),
            StructField("embedding_generated_at", TimestampType(), True),
        ])
    
    @staticmethod
    def get_key_columns() -> List[str]:
        """Get primary columns for basic operations."""
        return ["entity_id", "entity_type", "city", "state"]
```

**Key Benefits**:
- **Single Source of Truth**: All data in one comprehensive DataFrame
- **Type Safety**: Strong schema enforcement with proper data types
- **Simple Structure**: Clean, understandable schema design
- **Demo-Friendly**: Easy to explore and understand data structure

### 5. Pipeline Orchestration (`core/pipeline_runner.py`) 

**Challenge**: Current system requires manual coordination between different modules and processes.

**Solution**: Simple pipeline runner that orchestrates: load → enrich → embed → output in clean sequence.

**Implementation Status**: 🔄 Ready for Phase 5 implementation (simplified for demo)

**Spark Best Practice - Direct DataFrame Enrichment**:
```python
def run_pipeline(self):
    # 1. Load data
    df = self.loader.load_all_sources()
    
    # 2. Enrich data  
    enriched_df = self.enrichment.enrich_dataset(df)
    
    # 3. Add embeddings directly to DataFrame (NO correlation needed)
    final_df = enriched_df.withColumn(
        "embedding", 
        self.embedding_udf(col("embedding_text"))
    ).withColumn(
        "embedding_model",
        lit(self.config.embedding.model)
    )
    
    # 4. Save final result
    final_df.write.mode("overwrite").parquet("output/unified_dataset.parquet")
```

**Key Benefits**:
- **Single Entry Point**: One runner controls entire pipeline
- **No Correlation Complexity**: Embeddings are just additional DataFrame columns
- **Clean Implementation**: Simple DataFrame operations following Spark best practices
- **Demo-Ready**: Easy to understand and run

## Downstream Consumer Integration

### Direct Spark Integration

**Previous Approach**: Downstream services called REST APIs
**New Approach**: Downstream services connect directly to the Spark DataFrame for analytics, search, and ML operations.

## Configuration Management

### Unified Configuration System

Configuration is managed through YAML files with comprehensive settings for:
- Spark configuration and resource allocation
- Data source definitions and formats
- Enrichment rules and mappings
- Text processing and chunking settings
- Output formats and partitioning strategies

## Performance and Scalability Benefits

### Distributed Processing Advantages

**Current Limitations**:
- Single-node processing bottlenecks
- Manual batch coordination
- API call overhead for data access
- Limited parallelization of embedding generation

**Spark Architecture Benefits**:

1. **Automatic Parallelization**
   - Data loading across multiple workers
   - Distributed enrichment processing  
   - Parallel embedding generation
   - Automatic task scheduling and optimization

2. **Memory Management**
   - Intelligent caching strategies
   - Automatic spill-to-disk for large datasets
   - Memory-efficient columnar processing
   - Garbage collection optimization

3. **Fault Tolerance**
   - Automatic retry of failed tasks
   - Lineage-based recovery
   - Checkpointing for long-running pipelines
   - Node failure resilience

4. **Dynamic Resource Allocation**
   - Scale up/down based on workload
   - Optimal resource utilization
   - Multi-tenant resource sharing
   - Cloud auto-scaling integration

### Performance Benchmarks (Projected)

| Metric | Current System | Spark Architecture | Improvement |
|--------|---------------|-------------------|-------------|
| **Data Loading** | ~2 min (sequential) | ~20 sec (parallel) | **6x faster** |
| **Embedding Generation** | ~30 min (1M texts) | ~5 min (distributed) | **6x faster** |
| **Data Enrichment** | ~5 min (row-by-row) | ~30 sec (vectorized) | **10x faster** |
| **Memory Usage** | ~8GB peak | ~3GB (optimized) | **60% reduction** |
| **Downstream Latency** | ~200ms (API calls) | ~10ms (direct access) | **20x faster** |
| **Scalability** | Single node limit | Linear scaling | **Unlimited*** |

*With proper cluster configuration

## Migration Strategy

### Phase 1: Foundation (Weeks 1-2)
- Set up Spark development environment
- Implement basic `UnifiedLoader` for JSON files
- Create core pipeline structure and configuration system
- Develop basic unit tests and validation

### Phase 2: Core Features (Weeks 3-4)
- Implement data enrichment engine with Spark SQL
- Add SQLite integration for Wikipedia data
- Create unified schema and basic embedding generation
- Implement pipeline orchestration and basic quality checks

### Phase 3: Advanced Features (Weeks 5-6)
- Add multiple embedding provider support
- Implement semantic chunking and advanced text processing
- Add comprehensive quality assurance and validation
- Optimize performance with caching and partitioning strategies

### Phase 4: Integration & Testing (Weeks 7-8)
- Create downstream consumer examples and integrations
- Comprehensive integration testing with real datasets
- Performance benchmarking and optimization
- Documentation and training materials

### Phase 5: Production Deployment (Weeks 9-10)
- Production cluster setup and configuration
- Monitoring and alerting systems
- Gradual migration from existing API-based system
- Performance validation and troubleshooting

## Risk Assessment and Mitigation

### Technical Risks

**Risk**: Spark Learning Curve
- **Impact**: Development delays, suboptimal implementations
- **Mitigation**: Comprehensive training, phased implementation, code reviews by Spark experts

**Risk**: Memory and Resource Management  
- **Impact**: Out-of-memory errors, poor performance
- **Mitigation**: Proper partitioning strategies, memory tuning, comprehensive testing with large datasets

**Risk**: Embedding Provider Integration
- **Impact**: API rate limits, provider failures
- **Mitigation**: Robust retry logic, multiple provider fallbacks, circuit breaker patterns

### Operational Risks

**Risk**: Production Deployment Complexity
- **Impact**: Deployment failures, downtime
- **Mitigation**: Blue-green deployments, comprehensive testing environments, rollback procedures

**Risk**: Data Quality Issues
- **Impact**: Downstream consumer failures, incorrect results  
- **Mitigation**: Comprehensive data validation, quality scoring, monitoring and alerting

## Success Metrics

### Performance Metrics
- **Processing Speed**: 5x improvement in end-to-end pipeline execution
- **Resource Efficiency**: 50% reduction in memory and CPU usage
- **Scalability**: Linear scaling with data volume and cluster size
- **Latency**: Sub-second access times for downstream consumers

### Quality Metrics
- **Data Completeness**: 99%+ of records successfully processed
- **Data Accuracy**: 95%+ data quality scores across all entity types
- **Embedding Quality**: Maintain or improve current similarity search metrics
- **System Reliability**: 99.9% uptime with automatic recovery

### Developer Experience Metrics
- **Code Simplicity**: 50% reduction in total lines of code
- **Maintenance Overhead**: 70% reduction in manual coordination tasks
- **Feature Development**: 3x faster addition of new data sources and transformations
- **Debugging & Monitoring**: Centralized logging and comprehensive metrics

## Conclusion

This Apache Spark architecture proposal provides a comprehensive solution that simplifies the current complex multi-module system into a single, unified data pipeline. By eliminating API servers and providing direct DataFrame access, we achieve significant performance improvements while maintaining data quality and type safety.

The proposed architecture leverages Spark's distributed computing capabilities to handle large-scale real estate and Wikipedia data processing efficiently. The unified output DataFrame serves as a single source of truth for all downstream consumers, dramatically simplifying integration and reducing operational overhead.

Key benefits include:
- **6x faster processing** through distributed computing
- **Unified data model** eliminating integration complexity
- **Linear scalability** for growing datasets  
- **Simplified architecture** reducing maintenance overhead
- **Enhanced reliability** with built-in fault tolerance

This transformation positions the system for future growth while providing immediate performance and operational benefits.

## Implementation Status

### ✅ Phase 1: Foundation Setup - COMPLETED
- Created modular `data_pipeline/` package structure
- Implemented comprehensive Pydantic configuration models
- Set up Spark session management with proper resource cleanup
- Created CLI interface with argparse
- Package installable with `pip install -e .`

### ✅ Phase 2: Data Ingestion Framework - COMPLETED  
- Implemented separate, focused loaders for each data type:
  - `PropertyLoader` - Native Spark JSON reader for property data
  - `NeighborhoodLoader` - Native Spark JSON reader for neighborhood data
  - `WikipediaLoader` - Pure Python pandas/sqlite3 for Wikipedia data (no JDBC)
- Created `DataLoaderOrchestrator` to coordinate all loaders
- Built unified schema with comprehensive field mapping
- Successfully loading and processing 998 records (420 properties, 21 neighborhoods, 557 Wikipedia articles)
- Data successfully saved to Parquet format with partitioning by entity_type and state

### ✅ Phase 3: Data Enrichment Engine - COMPLETED
- Implemented `DataEnrichmentEngine` with Spark SQL transformations
- Created location normalization using broadcast joins for efficiency
- Added derived field calculations (price per sqft, content hash)
- Built correlation ID generation system with UUID UDF
- Implemented comprehensive data quality scoring framework
- Created `TextProcessor` for embedding text preparation
- Successfully enriching all 998 records with 72% average quality score
- 578 records validated, all records have normalized cities and embedding text

### ✅ Phase 4: Embedding Generation System - COMPLETED WITH VOYAGE

**Achievements:**
- Implemented `DistributedEmbeddingGenerator` with clean Spark UDF approach
- Integrated llama-index providers for professional embedding generation:
  - ✅ Voyage AI (voyage-3, voyage-large-2) - PRIMARY PROVIDER
  - ✅ Ollama (nomic-embed-text, mxbai-embed-large)
  - ✅ OpenAI (text-embedding-3-small, text-embedding-3-large)
  - ✅ Gemini (models/embedding-001)
- Copied proven patterns from `common_embeddings/embedding/factory.py`
- Implemented multiple chunking strategies (simple, sentence, semantic)
- Added embedding columns directly to DataFrame (no ChromaDB complexity)
- Configuration updated to use Voyage as default provider
- Successful testing with Voyage API generating 1024-dimensional embeddings
- Clean integration with VOYAGE_API_KEY from environment variables