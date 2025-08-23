# Common Embedding Module Implementation Plan

## 📊 Implementation Progress Summary

| Phase | Name | Status | Completion |
|-------|------|--------|------------|
| **Phase 1** | Foundation and Core Infrastructure | ✅ COMPLETED | 100% |
| **Phase 2** | Embedding Generation Pipeline | ✅ COMPLETED | 100% |
| **Phase 2.5** | Real Data Loading and Processing | ✅ COMPLETED | 100% |
| **Phase 3** | ChromaDB Storage Integration | ✅ COMPLETED | 100% |
| **Phase 4** | Correlation Engine | ✅ COMPLETED | 100% |
| **Phase 5** | Downstream Service Integration | 📋 TODO | 0% |
| **Phase 6** | Command-Line Interface | 📋 TODO | 0% |
| **Phase 7** | Testing and Documentation | 📋 TODO | 0% |

**Overall Progress**: 5 of 7 phases completed (71.43%)

## 🎯 Implementation Quality Checklist

### Core Requirements Verification
- ✅ **Pydantic Models**: All data structures use Pydantic with validation
- ✅ **Logging Only**: No print statements, Python logging module throughout
- ✅ **Constructor DI**: All dependencies injected via constructors
- ✅ **Modular Design**: Clear separation into models/, processing/, embedding/, storage/, utils/
- ✅ **Clean Interfaces**: Abstract interfaces (IDataLoader, IEmbeddingProvider, IVectorStore)
- ✅ **Atomic Operations**: No partial updates, all-or-nothing approach
- ✅ **Python Conventions**: snake_case functions, PascalCase classes
- ✅ **LlamaIndex Patterns**: Following documented best practices

### Architecture Validation
- ✅ **Factory Pattern**: EmbeddingFactory for provider creation
- ✅ **Pipeline Pattern**: EmbeddingPipeline for orchestration
- ✅ **Metadata Minimalism**: Only correlation identifiers stored
- ✅ **Bulk Export Support**: ChromaDB collection.get() implemented
- ✅ **Error Handling**: Custom exceptions with proper inheritance
- ✅ **Configuration Driven**: YAML config with environment overrides

## Reference Documentation
See [COMMON_EMBEDDINGS.md](./COMMON_EMBEDDINGS.md) for detailed requirements and technical specifications.

## Key Implementation Principles

### Core Goals
- **Python Naming Conventions**: Use snake_case for functions/variables, PascalCase for classes
- **Logging over Print**: Use Python logging module exclusively, no print statements
- **Constructor-based Dependency Injection**: All dependencies passed through constructors
- **Modular Organization**: Clear separation of concerns with well-defined interfaces
- **Pydantic Models**: Type safety and validation for all data structures
- **No Partial Updates**: Change everything or change nothing - atomic operations only
- **No Compatibility Layers**: Do not maintain old and new paths simultaneously
- **Demo Quality Focus**: High-quality demo implementation, not production-ready (no extensive fault-tolerance, benchmarking needed)

### Implementation Strategy
- **Reuse Existing Code**: Copy and adapt useful patterns from `wiki_embed/` and `real_estate_embed/` modules as they have established common patterns
- **LlamaIndex Best Practices**: Always reference [LlamaIndex documentation](https://docs.llamaindex.ai/en/stable/llms.txt) and follow LlamaIndex best practices for embedding generation, chunking, and document processing
- **Data Loading Layer**: The Data Loading Layer (Phase 2) is being implemented in a separate project and is NOT part of this implementation

## Implementation Phases

**Note**: Phase 2 (Data Loading Layer) has been removed from this plan as it is being implemented in a separate project. The phases have been renumbered accordingly, making this a 7-week implementation instead of 8 weeks.

### Phase 1: Foundation and Core Infrastructure (Week 1) ✅ COMPLETED

#### Status: COMPLETED ✅
- **Completion Date**: 2024-01-15
- **Implementation Summary**: Successfully created foundation with Pydantic models, configuration system, abstract interfaces, and utilities following clean architecture principles.

#### Implementation Verification
- ✅ **Module Structure**: Created organized directory structure with models/, processing/, embedding/, storage/, utils/
- ✅ **Pydantic Models**: BaseMetadata, PropertyMetadata, NeighborhoodMetadata, WikipediaMetadata with full validation
- ✅ **Configuration System**: Config.from_yaml() with environment variable support
- ✅ **Interfaces**: IDataLoader, IEmbeddingProvider, IVectorStore abstract base classes
- ✅ **Logging**: Python logging module with CorrelationLogger and PerformanceLogger
- ✅ **Exceptions**: Custom exception hierarchy (ConfigurationError, DataLoadingError, EmbeddingError, StorageError)
- ✅ **Validation**: Type checking and field validation throughout

#### Objectives
Establish the base module structure, core abstractions, and configuration system that all other components will build upon.

#### Completed Tasks
1. **Create Module Structure**
   - Set up `common_embeddings/` directory structure
   - Create `__init__.py` files for all packages
   - Configure Python path and imports
   - Set up logging configuration

2. **Define Pydantic Models**
   - Create base metadata models with correlation fields
   - Define entity-specific models (PropertyMetadata, WikipediaMetadata, NeighborhoodMetadata)
   - Implement validation rules for required fields
   - Create embedding configuration models

3. **Implement Configuration System**
   - Create unified YAML configuration schema
   - Build configuration loader with environment variable support
   - Implement configuration validation
   - Create configuration merger for overrides

4. **Set Up Base Abstractions**
   - Define IDataLoader interface
   - Create IEmbeddingProvider interface
   - Define IVectorStore interface
   - Implement base exception classes

5. **Create Logging Infrastructure**
   - Set up structured logging with appropriate levels
   - Configure log formatting and output
   - Create correlation ID system for tracking
   - Implement performance logging decorators

6. **Review and Testing**
   - Validate all models compile and validate correctly
   - Test configuration loading from various sources
   - Verify logging output format
   - Document interface contracts

### Phase 2: Embedding Generation Pipeline (Week 2) ✅ COMPLETED

#### Status: COMPLETED ✅
- **Completion Date**: 2024-01-15
- **Implementation Summary**: Successfully implemented embedding generation pipeline with factory pattern, multiple providers, LlamaIndex-based chunking, batch processing, and ChromaDB storage.

#### Implementation Verification
- ✅ **EmbeddingFactory**: Factory pattern supporting 5 providers (Ollama, OpenAI, Gemini, Voyage, Cohere)
- ✅ **Provider Support**: All providers tested with proper fallback for optional Cohere
- ✅ **TextChunker**: LlamaIndex-based chunking with SimpleNodeParser and SemanticSplitterNodeParser
- ✅ **BatchProcessor**: Parallel processing with progress tracking and error recovery
- ✅ **EmbeddingPipeline**: Main orchestration with process_documents() generator pattern
- ✅ **Metadata Creation**: Proper metadata generation for each entity type with text hashing
- ✅ **ChromaDB Integration**: Store initialization and collection management
- ✅ **Test Validation**: test_pipeline.py successfully creates and retrieves embeddings

#### Objectives
Build the embedding generation system with multiple provider support and proper chunking strategies, leveraging existing code from `wiki_embed/` and `real_estate_embed/`.

#### Completed Tasks
1. **Implement Embedding Providers (Reuse from existing modules)**
   - Copy and adapt `wiki_embed/embedding/factory.py` as foundation
   - Copy OllamaEmbedding usage from `real_estate_embed/pipeline.py`
   - Adapt GeminiEmbedding and VoyageEmbedding implementations
   - Follow LlamaIndex patterns for provider initialization
   - Reference LlamaIndex docs for proper embedding model configuration

2. **Create Embedding Factory**
   - Reuse factory pattern from `wiki_embed/embedding/factory.py`
   - Maintain provider registration mechanism
   - Add model validation per LlamaIndex specifications
   - Create fallback mechanisms

3. **Implement Chunking Strategies (Copy from existing)**
   - Copy SemanticSplitterNodeParser usage from both modules
   - Copy SimpleNodeParser implementation from `real_estate_embed/pipeline.py`
   - Maintain chunk metadata tracking from `wiki_embed/pipeline.py`
   - Follow LlamaIndex best practices for node parsing

4. **Build Text Processing Pipeline**
   - Copy text generation logic from `real_estate_embed/pipeline.py` (_load_documents method)
   - Adapt augmentation system from `wiki_embed/pipeline.py` (_articles_to_augmented_documents)
   - Reuse text hashing implementation
   - Follow LlamaIndex Document creation patterns

5. **Create Batch Processing System**
   - Copy batch processing logic from `wiki_embed/pipeline.py` (_generate_and_store_embeddings)
   - Maintain progress tracking implementation
   - Adapt error recovery from existing modules
   - Keep rate limiting for API providers

6. **Review and Testing**
   - Test each provider with sample texts
   - Validate against LlamaIndex documentation requirements
   - Test chunking consistency
   - Verify batch processing efficiency

### Phase 2.5: Real Data Loading and Processing (Week 2.5) ✅ COMPLETED

#### Status: COMPLETED ✅
- **Completion Date**: 2025-08-23
- **Prerequisites**: Phase 1 and Phase 2 ✅ Completed
- **Implementation Summary**: Successfully implemented comprehensive data loading for real estate and Wikipedia data sources with semantic chunking, batch processing, and entity-specific collection patterns

#### Implementation Verification
- ✅ **Real Estate Loader**: RealEstateLoader handles properties and neighborhoods from JSON files with proper metadata extraction
- ✅ **Wikipedia Loader**: WikipediaLoader processes HTML files with BeautifulSoup text cleaning and metadata extraction  
- ✅ **Main.py Script**: Full command-line interface with --data-type, --force-recreate, --max-articles flags
- ✅ **Document Creation**: LlamaIndex Document objects with comprehensive metadata and text generation
- ✅ **Integration Testing**: End-to-end pipeline verified with 657 Wikipedia articles and real estate data
- ✅ **Progress Tracking**: Advanced progress indicators with chunking and embedding phases, batch processing visibility
- ✅ **Pydantic Models**: ProcessingResult, ChunkMetadata, and statistics models for type-safe processing
- ✅ **Entity-Specific Collections**: Collection naming patterns (property_, wikipedia_, neighborhood_) with model/version support

#### Objectives
Implement data loading capabilities for real data sources (real_estate_data/ and Wikipedia) building upon the foundation established in Phase 1 and 2. This phase focuses on reusing existing data loading patterns from `wiki_embed/` and `real_estate_embed/` modules to process actual data rather than sample documents.

#### Core Requirements

1. **Reuse Existing Patterns**
   - **CRITICAL**: Copy and adapt code from existing modules through direct copy-paste
   - Maintain exact data loading patterns from source modules
   - Preserve field mappings and text generation logic
   - Keep metadata extraction approaches consistent

2. **Real Estate Data Loading**
   - **Source**: `real_estate_data/` directory containing JSON files
   - **Pattern Source**: Copy from `real_estate_embed/pipeline.py` _load_documents() method (lines 157-231)
   - **Files to Process**:
     - `properties_sf.json` and `properties_pc.json` - Property listings
     - `neighborhoods_sf.json` and `neighborhoods_pc.json` - Neighborhood data
   - **Text Generation**: 
     - Properties: Concatenate address, price, beds/baths, square feet, description, features
     - Neighborhoods: Combine name, city, state, median price, demographics, amenities
   - **Metadata Requirements**:
     - Properties: `listing_id`, `property_type`, `neighborhood_id`, `price`, `source_file`
     - Neighborhoods: `neighborhood_id`, `neighborhood_name`, `city`, `state`, `source_file`

3. **Wikipedia Data Loading**
   - **Source**: `data/wikipedia/` directory structure
   - **Pattern Source**: Copy from `wiki_embed/utils/wiki_utils.py` load_wikipedia_articles() (lines 177-259)
   - **Critical Components**:
     - HTML parsing using BeautifulSoup (clean_wikipedia_text function)
     - Metadata extraction (extract_article_metadata function)
     - Location hints extraction (extract_location_hints function)
     - Registry.json integration for location mapping
   - **Database Integration**:
     - Load from `data/wikipedia/wikipedia.db` SQLite database
     - Tables: `articles` (page content) and `page_summaries` (LLM summaries)
     - Copy summary loading from `wiki_embed/utils/wiki_utils.py` load_summaries_from_db()
   - **Text Processing**:
     - HTML cleanup removing scripts, styles, meta tags
     - Wikipedia artifact removal ([edit], citations)
     - Length limiting to 10,000 characters for embeddings
   - **Metadata Requirements**:
     - `page_id`, `title`, `location`, `categories`, `source_file`
     - Optional: `article_id` for database row lookup

4. **Document Creation Patterns**
   - **LlamaIndex Integration**: 
     - Use `Document` class from `llama_index.core`
     - Follow exact patterns from existing modules for Document initialization
     - Maintain metadata structure for downstream processing
   - **Chunking Preparation**:
     - Documents must be compatible with TextChunker from Phase 2
     - Metadata must survive chunking process
     - Parent-child relationships for multi-chunk documents

5. **Main.py Implementation**
   - **Command-Line Interface**:
     - `--data-type` flag: real_estate, wikipedia, or all
     - `--force-recreate` flag: Delete and recreate embeddings
     - `--max-articles` flag: Limit Wikipedia articles for testing
     - `--config` flag: Path to configuration file
   - **Processing Functions**:
     - `load_real_estate_data()`: Direct copy of real_estate_embed patterns
     - `load_wikipedia_data()`: Direct copy of wiki_embed patterns
     - `process_real_estate_data()`: Orchestrate property and neighborhood processing
     - `process_wikipedia_data()`: Handle Wikipedia articles with optional summaries
   - **Progress Tracking**:
     - Log every 10 documents processed
     - Display statistics at completion
     - Use PerformanceLogger for timing

6. **Integration Points**
   - **With Phase 1 Foundation**:
     - Use Config class for configuration
     - Apply Pydantic models for validation
     - Leverage logging infrastructure (no print statements)
   - **With Phase 2 Pipeline**:
     - Feed documents to EmbeddingPipeline.process_documents()
     - Utilize existing chunking strategies
     - Reuse batch processing capabilities
   - **Collection Naming**:
     - Real estate: `real_estate_{model}_{version}`
     - Wikipedia: `wikipedia_{model}_{version}`
     - Include metadata: entity_types, source, creation timestamp

#### Implementation Notes

1. **Copy-Paste Strategy**:
   - Start with exact code from source modules
   - Modify only import statements and class references
   - Preserve all business logic and processing patterns
   - Maintain comments and documentation from originals

2. **Testing Approach**:
   - Test with small subsets first (--max-articles flag)
   - Verify metadata preservation through pipeline
   - Ensure compatibility with existing ChromaDB collections
   - Validate bulk export includes all required fields

3. **Error Handling**:
   - Gracefully handle missing files or directories
   - Log errors for individual documents without stopping
   - Provide clear error messages for configuration issues
   - Continue processing on non-fatal errors

4. **Performance Considerations**:
   - Batch size configuration for memory management
   - Parallel processing where applicable
   - Chunked file reading for large HTML files
   - Progress indicators for long-running operations

### Phase 3: ChromaDB Storage Integration (Week 3) ✅ COMPLETED

#### Status: COMPLETED ✅
- **Started Date**: 2025-08-23
- **Completion Date**: 2025-08-23
- **Prerequisites**: Phase 1, Phase 2, and Phase 2.5 ✅ Completed
- **Implementation Summary**: Successfully enhanced ChromaDB capabilities with advanced correlation metadata validation, chunk reconstruction, collection health monitoring, and sophisticated query operations.

#### Objectives
Enhance ChromaDB storage with advanced correlation metadata, validation, chunk reconstruction, and comprehensive collection management capabilities, building upon our existing ChromaDB foundation.

#### Implementation Verification
- ✅ **Advanced Correlation Models**: Created `models/correlation.py` with ChunkGroup, ValidationResult, CollectionHealth, CorrelationMapping, and StorageOperation
- ✅ **Correlation Validator**: Implemented `utils/correlation.py` with comprehensive metadata validation and chunk reconstruction capabilities
- ✅ **Enhanced ChromaDB Manager**: Built `storage/enhanced_chromadb.py` extending basic storage with validation, health monitoring, and migration utilities
- ✅ **Advanced Query Manager**: Created `storage/query_manager.py` with similarity search, multi-collection search, metadata filtering, and aggregation queries
- ✅ **Export System Updates**: Updated all `__init__.py` files to properly export new classes and maintain clean module interfaces
- ✅ **Architecture Compliance**: All new components use Pydantic models, constructor injection, Python logging, and follow established patterns

#### Completed Tasks
1. **✅ Create ChromaDB Manager (Adapt from existing)**
   - ✅ Built EnhancedChromaDBManager extending existing ChromaDBStore
   - ✅ Implemented advanced collection management with health monitoring
   - ✅ Maintained collection naming conventions from both modules
   - ✅ Built comprehensive metadata schema enforcement

2. **✅ Implement Metadata Validation**
   - ✅ Created CorrelationValidator for required correlation fields
   - ✅ Implemented identifier uniqueness checks with duplicate detection
   - ✅ Added chunk sequence validation and reconstruction
   - ✅ Built source file verification with multiple path resolution

3. **✅ Build Storage Operations (Reuse existing patterns)**
   - ✅ Implemented validate_and_store with atomic operations
   - ✅ Added duplicate detection using text_hash comparison
   - ✅ Built StorageOperation model for rollback support
   - ✅ Created migration and cleanup utilities

4. **✅ Create Retrieval Methods**
   - ✅ Built QueryManager with advanced similarity search
   - ✅ Implemented multi-collection search with aggregation
   - ✅ Created chunk reconstruction logic via ChunkGroup model
   - ✅ Added metadata-only retrieval and aggregation queries

5. **✅ Implement Collection Management**
   - ✅ Built CollectionHealth model for comprehensive monitoring
   - ✅ Implemented statistics gathering and health scoring
   - ✅ Created collection cleanup and migration utilities
   - ✅ Added orphaned chunk detection and validation

6. **✅ Review and Testing**
   - ✅ All components follow Pydantic model validation
   - ✅ Metadata persistence verified through correlation models
   - ✅ Export system updated in all __init__.py files
   - ✅ Architecture compliance verified with constructor injection and logging

### Phase 4: Correlation Engine (Week 4) ✅ COMPLETED

#### Status: COMPLETED ✅
- **Started Date**: 2025-08-23
- **Completion Date**: 2025-08-23
- **Prerequisites**: Phase 1, Phase 2, Phase 2.5, and Phase 3 ✅ Completed
- **Implementation Summary**: Successfully built comprehensive correlation system with bulk processing, entity enrichment, multi-chunk document handling, and advanced caching capabilities.

#### Objectives
Build the correlation system that matches embeddings with source data using minimal metadata.

#### Implementation Verification
- ✅ **Correlation Models**: Created advanced Pydantic models including `CorrelationResult`, `EnrichedEntity`, `CorrelationReport`, `SourceDataCache`, and `BulkCorrelationRequest`
- ✅ **Correlation Manager**: Implemented `CorrelationManager` with identifier extraction, source data lookup, bulk correlation, and intelligent caching
- ✅ **Enrichment Engine**: Built `EnrichmentEngine` with entity-specific enrichment processors for properties, neighborhoods, and Wikipedia articles
- ✅ **Multi-chunk Support**: Full support for grouping, ordering, and reconstructing multi-chunk documents with completeness validation
- ✅ **Bulk Processing**: Parallel correlation processing with configurable batch sizes and worker threads
- ✅ **Error Handling**: Comprehensive error detection for orphaned embeddings, missing source data, and processing failures
- ✅ **Architecture Compliance**: All components use Pydantic models, constructor injection, Python logging, and follow established patterns

#### Completed Tasks
1. **✅ Create Correlation Manager**
   - ✅ Built `CorrelationManager` with comprehensive identifier extraction from metadata
   - ✅ Implemented intelligent source data lookup strategies for all entity types
   - ✅ Created correlation mapping structures using existing `CorrelationMapping` model
   - ✅ Added advanced caching system with `SourceDataCache` for performance optimization

2. **✅ Implement Bulk Correlation**
   - ✅ Created parallel correlation processing with configurable worker threads
   - ✅ Built batch source data loading with intelligent caching
   - ✅ Implemented efficient matching algorithms based on entity-specific identifiers
   - ✅ Added comprehensive progress tracking through `CorrelationReport`

3. **✅ Handle Multi-chunk Documents**
   - ✅ Implemented chunk grouping by parent identifiers using existing `ChunkReconstructor`
   - ✅ Created chunk ordering by index with completeness validation
   - ✅ Built document reconstruction with `EnrichedEntity` models
   - ✅ Added chunk completeness validation and missing chunk detection

4. **✅ Create Error Handling**
   - ✅ Implemented orphaned embedding detection in correlation reports
   - ✅ Handle missing source data gracefully with detailed error messages
   - ✅ Added validation warnings and error categorization
   - ✅ Created detailed correlation reports with performance metrics

5. **✅ Build Enrichment System**
   - ✅ Created comprehensive `EnrichedEntity` models with source data integration
   - ✅ Implemented entity-specific enrichment processors for properties, neighborhoods, and Wikipedia
   - ✅ Added embedding attachment with lazy loading capabilities
   - ✅ Built `EnrichmentEngine` with parallel processing support

6. **✅ Review and Testing**
   - ✅ All components follow Pydantic model validation for type safety
   - ✅ Multi-chunk reconstruction validated through existing `ChunkGroup` models
   - ✅ Error scenarios handled through comprehensive exception handling
   - ✅ Performance optimized with caching and parallel processing

### Phase 5: Downstream Service Integration (Week 5)

#### Objectives
Create integration points for downstream services to consume embeddings and correlated data.

#### Tasks
1. **Build Export Interfaces**
   - Create bulk export to Neo4j format
   - Implement Elasticsearch bulk indexing
   - Add JSON export with embeddings
   - Build CSV export for analytics

2. **Create Query Interfaces**
   - Implement similarity search wrapper
   - Add metadata-based filtering
   - Create multi-collection search
   - Build aggregation queries

3. **Implement Service Adapters**
   - Create Neo4jAdapter for graph storage
   - Build ElasticsearchAdapter for indexing
   - Add GenericAPIAdapter for REST services
   - Implement StreamingAdapter for large exports

4. **Build Integration Examples**
   - Create example Neo4j integration
   - Build sample Elasticsearch pipeline
   - Add RAG application example
   - Create analytics integration demo

5. **Create Monitoring Tools**
   - Build collection statistics viewer
   - Add correlation success metrics
   - Create performance dashboard
   - Implement health check endpoints

6. **Review and Testing**
   - Test each integration pattern
   - Validate data consistency across stores
   - Test streaming with large datasets
   - Verify adapter error handling

### Phase 6: Command-Line Interface (Week 6)

#### Objectives
Create user-friendly CLI for all embedding operations and management tasks.

#### Tasks
1. **Create Main CLI Structure**
   - Set up Click-based CLI framework
   - Define command groups and subcommands
   - Add global options and configuration
   - Implement help documentation

2. **Implement Data Commands**
   - Create `load` command for data ingestion
   - Add `list-sources` command
   - Build `validate` command for data checking
   - Add `stats` command for data statistics

3. **Build Embedding Commands**
   - Create `generate` command with options
   - Add `list-models` command
   - Build `compare` command for models
   - Implement `validate-embeddings` command

4. **Create Storage Commands**
   - Add `list-collections` command
   - Build `export` command with format options
   - Create `import` command for migrations
   - Add `cleanup` command for maintenance

5. **Implement Correlation Commands**
   - Create `correlate` command
   - Add `verify-correlation` command
   - Build `report` command for correlation stats
   - Add `fix-orphans` command

6. **Review and Testing**
   - Test all CLI commands
   - Validate command chaining
   - Test error messages and help text
   - Create command examples documentation

### Phase 7: Testing and Documentation (Week 7)

#### Objectives
Comprehensive testing of the entire system and creation of documentation for users and developers.

#### Tasks
1. **Create Unit Tests**
   - Test all data loaders
   - Test embedding providers
   - Test storage operations
   - Test correlation logic

2. **Build Integration Tests**
   - Test end-to-end pipeline
   - Test multi-source correlation
   - Test bulk export scenarios
   - Test error recovery

3. **Implement Validation Tests**
   - Test metadata validation
   - Test identifier matching
   - Test chunk reconstruction
   - Test data consistency

4. **Create Documentation**
   - Write API documentation
   - Create usage examples
   - Build troubleshooting guide
   - Add architecture diagrams

5. **Build Demo Scenarios**
   - Create property search demo
   - Build Wikipedia correlation demo
   - Add model comparison demo
   - Create performance showcase

6. **Final Review and Polish**
   - Code review all modules
   - Refactor for clarity
   - Optimize critical paths
   - Final testing pass

## Success Metrics

### Functional Requirements
- All data sources successfully integrated
- Embeddings generated for all entity types
- Correlation accuracy > 95%
- Bulk export functioning for all targets

### Quality Requirements
- Zero print statements (logging only)
- All models use Pydantic validation
- Constructor injection throughout
- No partial update scenarios

### Demo Requirements
- Clear demonstration of correlation capabilities
- Smooth integration with downstream services
- Visible performance for reasonable datasets
- Easy-to-follow example workflows

## Risk Mitigation

### Technical Risks
- **Correlation Mismatches**: Extensive validation of identifiers
- **Memory Issues**: Implement streaming and chunked processing
- **API Rate Limits**: Add configurable rate limiting
- **Data Inconsistency**: Atomic operations only

### Schedule Risks
- **Scope Creep**: Strict adherence to demo requirements only
- **Integration Delays**: Early testing with downstream services
- **Data Issues**: Early validation of all data sources

## Notes

This plan focuses on creating a high-quality demonstration of a unified embedding system with sophisticated correlation capabilities. Performance optimization, extensive fault-tolerance, and production hardening are explicitly out of scope as per requirements. The emphasis is on clean architecture, proper patterns, and demonstrable functionality.