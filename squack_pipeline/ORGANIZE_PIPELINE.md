# SQUACK Pipeline Organization Plan

## Complete Cut-Over Requirements

* **ALWAYS FIX THE CORE ISSUE!**
* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CALL FUNCTIONS ENHANCED or IMPROVED**: Update the actual methods. For example if there is a class PropertyIndex and we want to improve that do not create a separate ImprovedPropertyIndex and instead just update the actual PropertyIndex
* **ALWAYS USE PYDANTIC**
* **USE MODULES AND CLEAN CODE!**
* **Never name things after the phases or steps of the proposal and process documents**. So never test_phase_2_bronze_layer.py etc.
* **if hasattr should never be used. And never use isinstance**
* **Never cast variables or cast variable names or add variable aliases**
* **If you are using a union type something is wrong**. Go back and evaluate the core issue of why you need a union
* **If it doesn't work don't hack and mock. Fix the core issue**
* **If there is questions please ask me!!!**

## Executive Summary

The SQUACK pipeline currently has mixed concerns across its modules, with processing logic, data models, and orchestration spread throughout various directories. This reorganization plan proposes a clean, stage-based architecture that follows the medallion pattern (Bronze → Silver → Gold) with clear separation of concerns. Each stage will have its own dedicated modules for data processing, transformation, and validation, making the pipeline more maintainable, testable, and scalable.

## Current State Analysis

### Existing Structure Problems

1. **Mixed Responsibilities**: Writers handle both writing and embedding generation, processors handle both transformation and validation
2. **Unclear Stage Boundaries**: Bronze, Silver, and Gold processing logic is scattered across loaders, processors, and orchestrators
3. **Tight Coupling**: Entity-specific logic is intertwined with general pipeline infrastructure
4. **Model Confusion**: Data models are mixed with processing models, making it unclear what structures are used at each stage
5. **Embedded Side Effects**: Embedding generation is buried within writer strategies rather than being a distinct stage

## Main Pipeline Stages

### Stage 1: Bronze Layer (Raw Data Ingestion)
**Purpose**: Load raw data from source files into DuckDB tables with minimal transformation
- Reads JSON/CSV source files
- Creates initial DuckDB tables with raw schema
- Performs basic data validation (nulls, types, required fields)
- Maintains source data fidelity with minimal changes

### Stage 2: Silver Layer (Data Standardization)
**Purpose**: Clean, standardize, and enrich data with consistent schemas
- Normalizes data types and formats
- Standardizes field names and structures
- Adds computed fields (e.g., price per square foot)
- Handles data quality issues (duplicates, inconsistencies)
- Creates relationships between entities

### Stage 3: Gold Layer (Business-Ready Data)
**Purpose**: Create final, enriched datasets ready for consumption
- Combines data from multiple Silver tables
- Adds business logic and derived metrics
- Prepares data for embedding generation
- Creates denormalized views for performance
- Applies final validation rules

### Stage 4: Embeddings (Vector Generation)
**Purpose**: Generate vector embeddings for semantic search
- Converts Gold tier data to text documents
- Chunks long text appropriately
- Generates embeddings using configured provider
- Associates embeddings with source entities

### Stage 5: Output (Data Export)
**Purpose**: Write processed data to external systems
- Exports to Parquet files for archival
- Indexes to Elasticsearch for search
- Writes to any configured destinations
- Handles batching and error recovery

## Proposed Organization Structure

```
squack_pipeline/
│
├── __main__.py                    # Entry point
├── config.yaml                    # Default configuration
│
├── core/                          # Core infrastructure
│   ├── __init__.py
│   ├── connection.py              # DuckDB connection management
│   ├── settings.py                # Configuration models (Pydantic)
│   └── logging.py                 # Logging utilities
│
├── models/                        # All Pydantic data models
│   ├── __init__.py
│   ├── raw/                      # Raw data models (Bronze)
│   │   ├── __init__.py
│   │   ├── property.py
│   │   ├── neighborhood.py
│   │   └── wikipedia.py
│   ├── standardized/              # Standardized models (Silver)
│   │   ├── __init__.py
│   │   ├── property.py
│   │   ├── neighborhood.py
│   │   └── wikipedia.py
│   ├── enriched/                  # Enriched models (Gold)
│   │   ├── __init__.py
│   │   ├── property.py
│   │   ├── neighborhood.py
│   │   └── wikipedia.py
│   └── pipeline/                  # Pipeline metadata models
│       ├── __init__.py
│       ├── metrics.py
│       └── context.py
│
├── bronze/                        # Bronze Layer (Raw Ingestion)
│   ├── __init__.py
│   ├── base.py                   # Base ingestion interface
│   ├── property.py               # Property-specific ingestion
│   ├── neighborhood.py           # Neighborhood-specific ingestion
│   ├── wikipedia.py              # Wikipedia-specific ingestion
│   └── validation.py             # Bronze validation rules
│
├── silver/                        # Silver Layer (Standardization)
│   ├── __init__.py
│   ├── base.py                   # Base transformation interface
│   ├── property.py               # Property standardization
│   ├── neighborhood.py           # Neighborhood standardization
│   ├── wikipedia.py              # Wikipedia standardization
│   └── validation.py             # Silver validation rules
│
├── gold/                          # Gold Layer (Enrichment)
│   ├── __init__.py
│   ├── base.py                   # Base enrichment interface
│   ├── property.py               # Property enrichment
│   ├── neighborhood.py           # Neighborhood enrichment
│   ├── wikipedia.py              # Wikipedia enrichment
│   └── validation.py             # Gold validation rules
│
├── embeddings/                    # Embedding Generation
│   ├── __init__.py
│   ├── generator.py              # Main embedding generator
│   ├── converters/               # Document converters
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── property.py
│   │   ├── neighborhood.py
│   │   └── wikipedia.py
│   ├── providers/                # Embedding providers
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── voyage.py
│   │   ├── openai.py
│   │   └── ollama.py
│   └── chunking.py              # Text chunking strategies
│
├── output/                        # Output Writers
│   ├── __init__.py
│   ├── base.py                   # Base writer interface
│   ├── parquet.py                # Parquet file writer
│   ├── elasticsearch.py         # Elasticsearch indexer
│   └── batch.py                  # Batch processing utilities
│
├── orchestration/                 # Pipeline Orchestration
│   ├── __init__.py
│   ├── pipeline.py               # Main pipeline orchestrator
│   ├── entity.py                 # Entity-specific orchestration
│   └── stage.py                  # Stage coordination
│
├── utils/                         # Utilities
│   ├── __init__.py
│   ├── validation.py             # Common validation functions
│   ├── metrics.py                # Metrics collection
│   └── helpers.py                # Helper functions
│
└── tests/                         # All tests
    ├── unit/                      # Unit tests by module
    ├── integration/               # Integration tests
    └── fixtures/                  # Test data and fixtures
```

## Detailed Implementation Plan

### Phase 1: Core Infrastructure Setup

**Objective**: Establish the foundation for the new structure without breaking existing functionality.

**Requirements**:
- Create new directory structure with proper Python packages
- Set up core module with connection management and settings
- Establish base classes for each pipeline stage
- Ensure all models use Pydantic V2 exclusively
- Create clean interfaces without abstract base classes

**Implementation Details**:
1. Create `core/` module with DuckDB connection management moved from `loaders/connection.py`
2. Consolidate all settings into `core/settings.py` using Pydantic models
3. Move logging utilities to `core/logging.py`
4. Create base processor classes in each stage directory that define clear interfaces
5. Ensure no use of hasattr, isinstance, or union types in interfaces

**Todo List**:
- [ ] Create core module directory structure
- [ ] Move and refactor DuckDBConnectionManager to core/connection.py
- [ ] Consolidate PipelineSettings into core/settings.py with Pydantic
- [ ] Move PipelineLogger to core/logging.py
- [ ] Create base interfaces for Bronze, Silver, Gold stages
- [ ] Set up proper Python packages with __init__.py files
- [ ] Verify all imports work with new structure
- [ ] Update __main__.py to use new core modules
- [ ] Code review and testing

### Phase 2: Data Models Reorganization

**Objective**: Create clear separation between raw, standardized, and enriched data models.

**Requirements**:
- All models must use Pydantic V2
- Clear hierarchy: raw → standardized → enriched
- No mixing of data models with processing models
- Each tier has its own validation rules
- Models should be immutable where appropriate

**Implementation Details**:
1. Move existing models to appropriate tier subdirectories
2. Create raw models that match source data exactly
3. Create standardized models with consistent field names
4. Create enriched models with all computed fields
5. Separate pipeline metadata models from data models

**Todo List**:
- [ ] Create models/raw/ directory with source-matching models
- [ ] Create models/standardized/ directory with cleaned models
- [ ] Create models/enriched/ directory with final models
- [ ] Create models/pipeline/ for metrics and context
- [ ] Migrate existing models to new structure
- [ ] Remove all union types and replace with specific models
- [ ] Add proper validation to each model tier
- [ ] Update all imports throughout codebase
- [ ] Code review and testing

### Phase 3: Bronze Layer Implementation

**Objective**: Create clean ingestion layer that loads raw data into DuckDB.

**Requirements**:
- Single responsibility: load raw data
- No business logic or transformations
- Basic validation only (schema, nulls)
- Entity-specific loaders inherit from base
- Clear error handling and logging

**Implementation Details**:
1. Move loader logic from `loaders/` to `bronze/`
2. Create BronzeIngester base class with common functionality
3. Implement entity-specific ingesters for Property, Neighborhood, Wikipedia
4. Move validation logic to bronze/validation.py
5. Ensure clean separation from transformation logic

**Todo List**:
- [ ] Create bronze/ module structure
- [ ] Implement BronzeIngester base class
- [ ] Move PropertyLoader logic to bronze/property.py
- [ ] Move NeighborhoodLoader logic to bronze/neighborhood.py
- [ ] Move WikipediaLoader logic to bronze/wikipedia.py
- [ ] Create bronze/validation.py with ingestion rules
- [ ] Remove old loaders/ directory
- [ ] Update orchestrators to use new bronze module
- [ ] Code review and testing

### Phase 4: Silver Layer Implementation

**Objective**: Create standardization layer that cleans and normalizes data.

**Requirements**:
- Transform Bronze data to standardized format
- Handle data quality issues
- Create relationships between entities
- Add computed fields
- Consistent field naming

**Implementation Details**:
1. Move processor logic from `processors/*_silver_processor.py` to `silver/`
2. Create SilverTransformer base class
3. Implement entity-specific transformers
4. Consolidate validation rules in silver/validation.py
5. Ensure transformations are idempotent

**Todo List**:
- [ ] Create silver/ module structure
- [ ] Implement SilverTransformer base class
- [ ] Move PropertySilverProcessor to silver/property.py
- [ ] Move NeighborhoodSilverProcessor to silver/neighborhood.py
- [ ] Move WikipediaSilverProcessor to silver/wikipedia.py
- [ ] Create silver/validation.py with quality rules
- [ ] Remove old processor files
- [ ] Update orchestrators to use new silver module
- [ ] Code review and testing

### Phase 5: Gold Layer Implementation

**Objective**: Create enrichment layer that produces business-ready data.

**Requirements**:
- Combine data from multiple Silver tables
- Apply business logic
- Create denormalized views
- Prepare data for embeddings
- Final validation before output

**Implementation Details**:
1. Move gold processor logic to `gold/` module
2. Create GoldEnricher base class
3. Implement entity-specific enrichers
4. Add cross-entity enrichment capabilities
5. Ensure data is ready for downstream consumption

**Todo List**:
- [ ] Create gold/ module structure
- [ ] Implement GoldEnricher base class
- [ ] Move PropertyGoldProcessor to gold/property.py
- [ ] Move NeighborhoodGoldProcessor to gold/neighborhood.py
- [ ] Move WikipediaGoldProcessor to gold/wikipedia.py
- [ ] Create gold/validation.py with business rules
- [ ] Add cross-entity enrichment logic
- [ ] Remove old processor files
- [ ] Update orchestrators to use new gold module
- [ ] Code review and testing

### Phase 6: Embeddings Module Refactoring

**Objective**: Extract embedding generation into a dedicated, clean module.

**Requirements**:
- Separate embedding from writing concerns
- Support multiple embedding providers
- Clean document conversion pipeline
- Efficient batching and chunking
- Provider-agnostic interface

**Implementation Details**:
1. Move embedding logic from writers to dedicated module
2. Create clean provider interface without abstract classes
3. Implement converters for each entity type
4. Add intelligent chunking strategies
5. Ensure embeddings can be generated independently

**Todo List**:
- [ ] Create embeddings/ module structure
- [ ] Implement EmbeddingGenerator main class
- [ ] Move document converters to embeddings/converters/
- [ ] Create provider implementations in embeddings/providers/
- [ ] Implement chunking strategies in embeddings/chunking.py
- [ ] Remove embedding logic from writers
- [ ] Update pipeline to use new embeddings module
- [ ] Add embedding-specific configuration
- [ ] Code review and testing

### Phase 7: Output Module Consolidation

**Objective**: Create clean output layer for all data destinations.

**Requirements**:
- Single responsibility: write data
- No transformation or enrichment
- Support multiple output formats
- Efficient batching
- Error recovery

**Implementation Details**:
1. Consolidate all writers into `output/` module
2. Create OutputWriter base class
3. Implement Parquet and Elasticsearch writers
4. Add batch processing utilities
5. Remove writer strategies pattern

**Todo List**:
- [ ] Create output/ module structure
- [ ] Implement OutputWriter base class
- [ ] Move ParquetWriter to output/parquet.py
- [ ] Move ElasticsearchWriter to output/elasticsearch.py
- [ ] Create output/batch.py for batch utilities
- [ ] Remove old writers/ directory
- [ ] Update pipeline to use new output module
- [ ] Simplify writer configuration
- [ ] Code review and testing

### Phase 8: Orchestration Simplification

**Objective**: Create simple, clear orchestration layer.

**Requirements**:
- Coordinate pipeline stages
- Handle entity-specific flows
- Manage stage transitions
- Collect metrics
- Simple, readable code

**Implementation Details**:
1. Simplify orchestrator pattern
2. Remove complex inheritance hierarchies
3. Create clear stage progression
4. Add metrics collection at each stage
5. Ensure orchestration logic is minimal

**Todo List**:
- [ ] Create orchestration/ module structure
- [ ] Implement MainPipeline class
- [ ] Create EntityOrchestrator for entity flows
- [ ] Add StageCoordinator for stage management
- [ ] Move metrics collection to orchestration
- [ ] Remove old orchestrator/ directory
- [ ] Update __main__.py to use new orchestration
- [ ] Simplify configuration passing
- [ ] Code review and testing

### Phase 9: Testing Infrastructure

**Objective**: Reorganize tests to match new structure.

**Requirements**:
- Unit tests for each module
- Integration tests for stage transitions
- End-to-end pipeline tests
- Fixture management
- Fast test execution

**Implementation Details**:
1. Reorganize tests to mirror source structure
2. Create fixtures for each data tier
3. Add stage-specific integration tests
4. Ensure tests use new module structure
5. Remove obsolete test files

**Todo List**:
- [ ] Create tests/unit/ directory structure
- [ ] Organize unit tests by module
- [ ] Create tests/integration/ for stage tests
- [ ] Add tests/fixtures/ for test data
- [ ] Update all test imports
- [ ] Add tests for new base classes
- [ ] Ensure 100% critical path coverage
- [ ] Remove obsolete test files
- [ ] Code review and testing

### Phase 10: Final Cleanup and Documentation

**Objective**: Remove all legacy code and update documentation.

**Requirements**:
- No dead code remains
- All imports are clean
- Documentation reflects new structure
- Configuration is simplified
- Pipeline runs successfully

**Implementation Details**:
1. Remove all old directories and files
2. Update all configuration files
3. Ensure no compatibility layers remain
4. Update README and documentation
5. Verify complete pipeline execution

**Todo List**:
- [ ] Remove all legacy directories
- [ ] Clean up unused imports
- [ ] Update configuration files
- [ ] Update README.md
- [ ] Add module documentation
- [ ] Run full pipeline test
- [ ] Performance benchmarking
- [ ] Create migration guide
- [ ] Code review and testing

## Key Design Principles

### 1. Single Responsibility
Each module has one clear purpose. Bronze loads, Silver standardizes, Gold enriches, Embeddings vectorize, Output writes.

### 2. Clean Interfaces
No abstract base classes. Use simple Python classes with clear method signatures. Let duck typing work.

### 3. Pydantic Everywhere
All data structures use Pydantic V2 for validation, serialization, and type safety.

### 4. No Intermediate States
Data flows cleanly from one stage to the next without temporary compatibility layers.

### 5. Explicit Over Implicit
Clear method names, obvious data flow, no hidden side effects.

### 6. Testability
Each module can be tested in isolation with clear inputs and outputs.

## Success Criteria

1. **Clean Separation**: Each stage operates independently with clear interfaces
2. **No Coupling**: Modules can be modified without affecting others
3. **Testability**: Each module has comprehensive unit tests
4. **Performance**: Pipeline execution time remains the same or improves
5. **Maintainability**: New developers can understand the flow immediately
6. **Extensibility**: New entity types can be added easily
7. **Reliability**: Error handling is consistent and recovery is possible

## Risk Mitigation

1. **Data Loss**: All changes preserve existing data processing logic
2. **Performance**: Benchmark each phase against current implementation
3. **Compatibility**: Ensure output formats remain identical
4. **Testing**: Each phase includes comprehensive testing before moving on
5. **Rollback**: Version control allows reverting if issues arise

## Conclusion

This reorganization will transform the SQUACK pipeline from a mixed-concern architecture into a clean, stage-based system that follows data engineering best practices. The medallion architecture will be clearly reflected in the code structure, making it easier to understand, maintain, and extend. By following the implementation plan phase by phase, we can ensure a smooth transition without breaking existing functionality.