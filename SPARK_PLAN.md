# Apache Spark Data Pipeline Implementation Plan

## Overview

This document outlines the phased implementation plan for migrating `common_ingest/` and `common_embeddings/` to a unified `data_pipeline/` module using Apache Spark. The implementation follows **ATOMIC CHANGE REQUIREMENTS** - complete replacements with no migration phases, compatibility layers, or code duplication.

## Core Implementation Principles

### MANDATORY ATOMIC CHANGE REQUIREMENTS

These principles are **NON-NEGOTIABLE** and must be strictly followed:

1. **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update. No incremental migrations.
2. **CLEAN IMPLEMENTATION**: Simple, direct replacements only. No complex migration logic.
3. **NO MIGRATION PHASES**: The entire system switches from old to new instantly. No gradual rollouts.
4. **NO PARTIAL UPDATES**: Change everything or change nothing. No mixed states allowed.
5. **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously. One path only.
6. **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case". Delete it completely.
7. **NO CODE DUPLICATION**: Do not duplicate functions to handle both old and new patterns.
8. **NO WRAPPER FUNCTIONS**: Direct replacements only. No abstraction layers for compatibility.
9. **NO ENHANCED/IMPROVED NAMING**: When updating existing classes, modify them directly. Never create EnhancedPropertyIndex or ImprovedPropertyLoader - just update PropertyIndex and PropertyLoader.
10. **STRICT NAMING CONVENTIONS**: Functions and variables: snake_case, Classes: PascalCase, No camelCase except for JSON field mappings.
11. **PYDANTIC EVERYWHERE**: All data structures must be Pydantic models with full validation.
12. **LOGGING ONLY**: Use Python logging module exclusively. Zero print statements allowed.

### Python Best Practices Requirements

- **Type Hints**: All functions must have complete type annotations
- **Docstrings**: Comprehensive docstrings following Google style
- **Error Handling**: Proper exception handling with custom exception classes
- **Testing**: 100% test coverage for all public methods
- **Code Quality**: Pass mypy, flake8, and black formatting checks
- **Modular Design**: Clear separation of concerns with single responsibility principle
- **Dependency Injection**: Constructor-based dependency injection for testability
- **Immutability**: Use frozen Pydantic models where appropriate
- **Resource Management**: Proper context managers for Spark sessions and file operations

## Phase 1: Foundation Setup (Week 1) ✅ COMPLETED

### Objectives
- Establish Spark development environment
- Create basic project structure
- Implement local Spark setup documentation
- Set up development tools and testing framework

### Deliverables

#### 1.1 Project Structure Creation ✅
- Created `data_pipeline/` directory with proper package structure
- Set up `pyproject.toml` with all required dependencies
- Configured development tools (mypy, flake8, black, pytest)
- Created basic logging configuration

#### 1.2 Local Spark Setup Documentation ✅
- Created `data_pipeline/README.md` with simple local Spark setup
- Documented minimal dependencies and installation steps
- Provided basic "hello world" Spark example
- Included troubleshooting section for common issues

#### 1.3 Core Configuration System ✅
- Implemented `data_pipeline/config/` module with models.py and settings.py
- Created Pydantic models for pipeline configuration
- Set up YAML configuration file loading
- Added environment variable support for sensitive data

#### 1.4 Basic Spark Session Management ✅
- Implemented `data_pipeline/core/spark_session.py`
- Created context manager for Spark session lifecycle
- Added configuration-driven session creation
- Included proper resource cleanup

### Success Criteria
- [x] Local Spark environment running successfully
- [x] Basic project structure created and documented
- [x] Configuration system loads YAML files correctly
- [x] Spark session can be created and destroyed cleanly
- [x] All code passes type checking and linting
- [x] Basic unit tests pass

## Phase 2: Data Ingestion Framework (Week 2) ✅ COMPLETED

### Objectives
- Implement unified data loading system
- Create schema standardization framework
- Build data validation pipeline
- Establish error handling patterns

### Deliverables

#### 2.1 Unified Data Loader ✅
- Implemented `data_pipeline/ingestion/unified_loader.py`
- Created abstract base class for source adapters
- Built JSON file adapter for properties and neighborhoods
- Implemented SQLite adapter for Wikipedia data

#### 2.2 Schema Standardization ✅
- Created `data_pipeline/schemas/unified_schema.py`
- Defined comprehensive DataFrame schema for all entity types
- Implemented schema validation and enforcement
- Added schema evolution support

#### 2.3 Data Validation Framework ✅
- Implemented `data_pipeline/ingestion/data_validation.py`
- Created Pydantic models for input data validation
- Built validation pipeline with error reporting
- Added data quality scoring system

#### 2.4 Source Adapters ✅
- Created `data_pipeline/ingestion/source_adapters.py`
- Implemented PropertySourceAdapter for JSON properties
- Implemented NeighborhoodSourceAdapter for JSON neighborhoods
- Implemented WikipediaSourceAdapter for SQLite database

### Success Criteria
- [x] All data sources load successfully into Spark DataFrames
- [x] Schema standardization works across all entity types
- [x] Data validation catches and reports quality issues
- [x] Source adapters handle errors gracefully
- [x] Integration tests verify data loading accuracy
- [x] Performance acceptable for development datasets

## Phase 3: Data Enrichment Engine (Week 3) ✅ COMPLETED

### Objectives
- Build distributed data enrichment system
- Implement data quality assurance
- Create derived field calculations
- Add correlation ID generation

### Deliverables

#### 3.1 Enrichment Engine ✅
- Implemented `data_pipeline/processing/enrichment_engine.py`
- Created Spark SQL-based location expansion with broadcast joins
- Built feature normalization and deduplication
- Added derived field calculations (price per sqft, etc.)

#### 3.2 Text Processing Pipeline ✅
- Implemented `data_pipeline/processing/text_processor.py`
- Created content preparation for embedding generation
- Built text cleaning and normalization with Spark SQL functions
- Added metadata for chunking strategies

#### 3.3 Correlation ID Generation ✅
- Created unique correlation ID generation using UUID UDF
- Added UUID generation for tracking entities through pipeline
- Built entity identification system
- Prepared metadata structure for future embedding correlation

### Success Criteria
- [x] Data enrichment works cleanly with Spark SQL
- [x] Text processing prepares content for embeddings correctly
- [x] Correlation IDs are generated for all entities
- [x] Data validation catches obvious issues
- [x] Pipeline runs smoothly end-to-end
- [x] Code is clean and demo-ready

## Phase 4: Embedding Generation System (Week 4)

### Objectives
- Implement simple DataFrame-based embedding generation
- Create provider integration using existing patterns
- Build text chunking system
- Generate embeddings as DataFrame columns (no ChromaDB storage)

### Deliverables

#### 4.1 Simplified Embedding Generation Framework
- **COPY AND PASTE** ONLY provider logic from `common_embeddings/embedding/factory.py` (NOT storage parts)
- Implement `data_pipeline/processing/embedding_generator.py` as simple Spark UDF
- **SKIP** ChromaDB storage, correlation management, and batch storage complexity
- **FOCUS** on clean UDF that takes text and returns embedding arrays
- Create embeddings directly as DataFrame columns

#### 4.2 Provider Integration (Simplified)
- **COPY AND PASTE** provider implementations from `common_embeddings/` (OllamaEmbeddingProvider, VoyageEmbeddingProvider, etc.)
- **SKIP** provider factory complexity and storage integration
- **MAINTAIN** same provider interface for embedding generation only
- Implement clean provider UDFs for Spark DataFrame operations

#### 4.3 Text Chunking with Multiple Strategies
- **COPY AND PASTE** chunking strategies from `common_embeddings/processing/chunking.py`
- **SUPPORT** multiple chunking methods: simple, semantic, sentence (same as existing system)
- **REUSE** existing TextChunker class patterns and chunking algorithms
- **SIMPLIFY** metadata tracking (keep chunk index and basic info, skip complex correlation)
- Implement as configurable Spark UDF based on chunking strategy setting
- **MAINTAIN** same chunking quality as existing system

### Success Criteria
- [ ] Embeddings generate successfully as DataFrame columns
- [ ] Multiple providers work interchangeably (Ollama, Voyage, OpenAI)
- [ ] Multiple chunking strategies work (simple, semantic, sentence)
- [ ] Text chunking works cleanly for different content sizes
- [ ] No ChromaDB storage complexity - embeddings stay in DataFrame
- [ ] Pipeline runs smoothly with embedding generation
- [ ] Code is clean and demo-ready

## Phase 5: Pipeline Orchestration (Week 5)

### Objectives
- Build simple end-to-end pipeline orchestration
- Integrate embeddings directly into DataFrame (no correlation needed)
- Create basic pipeline runner for demo
- Add simple statistics and validation

### Deliverables

#### 5.1 Simple Pipeline Runner
- Implement `data_pipeline/core/pipeline_runner.py`
- Create clean end-to-end pipeline orchestration
- Connect all phases: load → enrich → embed → output
- Add basic progress reporting

#### 5.2 Direct Embedding Integration
- **ELIMINATE CORRELATION**: Enrich DataFrame with embeddings directly using Spark operations
- Use simple DataFrame operations to add embedding columns to existing data
- **NO SEPARATE CORRELATION SYSTEM**: Embeddings are just additional columns
- Follow Spark best practices for DataFrame enrichment

#### 5.3 Basic Output Management
- Create final enriched DataFrame with all data and embeddings
- Save to Parquet format for downstream consumption
- Add simple data validation and statistics
- Create demo-ready outputs

### Success Criteria
- [ ] Complete pipeline runs end-to-end successfully
- [ ] Embeddings integrated directly into DataFrame (no correlation complexity)
- [ ] Final output contains all data and embeddings in single DataFrame
- [ ] Pipeline produces clean demo-ready results
- [ ] Basic error handling works correctly
- [ ] System ready for demonstration

## Phase 6: Integration and Optimization (Week 6)

### Objectives
- Optimize DataFrame operations for performance
- Implement caching and partitioning strategies
- Create downstream consumer integration
- Add configuration tuning capabilities

### Deliverables

#### 6.1 Simple Output Management
- Create unified DataFrame output system
- Implement basic Parquet file saving
- Add simple caching for demo usage
- Create clean output format for downstream consumers

#### 6.2 Consumer Integration Examples
- Create simple analytics service example
- Build basic search service example
- Implement straightforward ML pipeline example
- Add clean API integration example

#### 6.3 Configuration Validation
- Create simple configuration validation
- Build basic configuration templates
- Add environment variable support
- Implement clean error handling

#### 6.4 Embedding Evaluation System (Optional - Post-Demo)
- **COPY AND PASTE** evaluation framework from `common_embeddings/evaluate/` 
- **REUSE** existing evaluation patterns from `common_embeddings/evaluate/evaluation_runner.py`
- **ADOPT** metrics calculation from `common_embeddings/evaluate/metrics_calculator.py`
- **MAINTAIN** model comparison logic from `common_embeddings/evaluate/model_comparator.py`
- Adapt evaluation to work with DataFrame-based embeddings

#### 6.5 Demo Preparation
- Create comprehensive demo dataset
- Build simple usage examples
- Add clear documentation
- Prepare presentation-ready outputs

### Success Criteria
- [ ] Pipeline runs cleanly end-to-end
- [ ] Output DataFrames are easy to query and explore
- [ ] Downstream integration examples work correctly  
- [ ] Configuration system is simple and clear
- [ ] Code is clean and demo-ready
- [ ] Documentation is comprehensive and clear

## Phase 7: Production Features (Week 7) - Optional Post-Demo

### Objectives
- Add production-quality features after demo is complete
- Implement performance monitoring and comprehensive logging
- Build checkpoint and recovery systems
- Create advanced monitoring and alerting

### Deliverables

#### 7.1 Performance Monitoring (Optional)
- Implement `data_pipeline/utils/performance_monitoring.py`
- Create execution time tracking and memory usage monitoring
- Add throughput measurement and bottleneck identification
- Build performance dashboards and reporting

#### 7.2 Comprehensive Logging (Optional)
- Enhance logging throughout all components with structured logging
- Create log aggregation and analysis systems
- Build error tracking and alerting mechanisms
- Add centralized logging configuration

#### 7.3 Checkpoint and Recovery (Optional)
- Build checkpoint and recovery system for long-running pipelines
- Implement state persistence and resume functionality
- Add automatic retry mechanisms and failure recovery
- Create backup and rollback procedures

### Success Criteria
- [ ] Production monitoring provides actionable insights
- [ ] Comprehensive logging enables effective debugging
- [ ] Checkpoint system enables pipeline recovery
- [ ] System ready for production deployment

## Phase 8: Atomic Migration Implementation (Week 8)

### Objectives
- **COMPLETE REPLACEMENT**: Atomically replace old system with new
- Remove all `common_ingest/` and `common_embeddings/` code
- Update all import statements and references
- Ensure zero downtime migration

### Deliverables

#### 7.1 Complete System Replacement
- **DELETE** entire `common_ingest/` directory
- **DELETE** entire `common_embeddings/` directory  
- **UPDATE** all import statements to use `data_pipeline/`
- **MODIFY** all configuration files to point to new system

#### 7.2 Reference Updates
- Update all scripts and tools to use new pipeline
- Modify documentation to reflect new architecture
- Change all example code and tutorials
- Update CI/CD pipelines for new module

#### 7.3 Validation of Complete Migration
- Ensure no references to old modules remain
- Verify all functionality works with new system
- Confirm no import errors or missing dependencies
- Validate that output format matches expectations

#### 7.4 Cleanup and Finalization
- Remove old configuration files
- Delete old test files and fixtures
- Clean up any remaining temporary code
- Finalize documentation updates

### Success Criteria
- [ ] **ZERO** references to old `common_ingest/` or `common_embeddings/` remain
- [ ] All imports use `data_pipeline/` module exclusively
- [ ] Complete system works end-to-end with no errors
- [ ] Output quality matches or exceeds old system
- [ ] Performance improvements are measurable
- [ ] No code duplication between old and new systems

## Phase 8: Comprehensive Testing and Validation (Week 8)

### Objectives
- Execute comprehensive test suite
- Validate data quality and accuracy
- Perform integration testing
- Conduct performance benchmarking

### Deliverables

#### 8.1 Unit Test Suite
- Complete unit tests for all public methods
- Mock all external dependencies properly
- Test error conditions and edge cases
- Achieve 100% code coverage

#### 8.2 Integration Testing
- End-to-end pipeline testing with real data
- Cross-component integration validation
- Error recovery and fault tolerance testing
- Configuration validation testing

#### 8.3 Data Quality Validation
- Validate output data accuracy against known baselines
- Test data enrichment correctness
- Verify embedding generation quality
- Confirm schema compliance

#### 8.4 Performance Benchmarking
- Measure processing speed improvements
- Validate memory usage efficiency
- Test scalability with larger datasets
- Compare performance against old system

### Success Criteria
- [ ] 100% test coverage achieved
- [ ] All integration tests pass
- [ ] Data quality meets or exceeds previous system
- [ ] Performance improvements documented and verified
- [ ] Error handling covers all failure modes
- [ ] System ready for production deployment

## Review and Final Validation

### Code Review Checklist
- [ ] All code follows Python best practices
- [ ] Type hints are complete and accurate
- [ ] Docstrings are comprehensive and helpful
- [ ] Error handling is robust and informative
- [ ] Logging is appropriate and structured
- [ ] Tests are thorough and maintainable

### Architecture Review Checklist  
- [ ] Modular design with clear separation of concerns
- [ ] Dependency injection used throughout
- [ ] Pydantic models used for all data structures
- [ ] Configuration system is flexible and validated
- [ ] Performance requirements are met
- [ ] Scalability considerations are addressed

### Migration Validation Checklist
- [ ] **COMPLETE REPLACEMENT**: No old code remains
- [ ] **NO COMPATIBILITY LAYERS**: Single code path only
- [ ] **NO CODE DUPLICATION**: Clean, direct implementation
- [ ] **ATOMIC CHANGE**: Everything switched simultaneously
- [ ] All functionality preserved or improved
- [ ] Documentation updated completely

## Success Metrics

### Functional Metrics
- **Data Processing**: 100% of records processed successfully
- **Data Quality**: 99%+ quality scores across all entity types
- **Feature Parity**: All original functionality preserved or improved
- **Integration**: All downstream consumers work without modification

### Performance Metrics  
- **Processing Speed**: Noticeable improvement in end-to-end execution
- **Memory Usage**: Efficient resource utilization
- **Throughput**: Good processing speed for demo datasets
- **Usability**: Easy to run and understand for demonstrations

### Quality Metrics
- **Test Coverage**: 100% unit test coverage
- **Type Safety**: Zero mypy errors
- **Code Quality**: Zero flake8 warnings
- **Documentation**: Complete API documentation with examples

## Risk Mitigation

### Technical Risks
- **Spark Learning Curve**: Keep implementation simple and well-documented
- **Resource Management**: Use basic Spark operations and simple caching
- **Provider Integration**: Copy proven patterns from existing `common_embeddings/`

### Migration Risks  
- **Data Loss**: Comprehensive backup and validation procedures
- **Functionality Regression**: Thorough integration testing before deployment
- **Performance Degradation**: Continuous benchmarking throughout development

### Operational Risks
- **Deployment Complexity**: Keep deployment simple with clear instructions
- **Understanding**: Comprehensive documentation and clean code
- **Demo Readiness**: Ensure system is easy to demonstrate and understand

## Final Deliverables

1. **Complete `data_pipeline/` module** with clean, simple implementation
2. **Comprehensive documentation** including setup guide and usage examples
3. **Full test suite** with 100% coverage and integration tests
4. **Demo validation** confirming system works end-to-end
5. **Migration validation report** confirming successful replacement
6. **Simple deployment guide** with clear instructions
7. **Usage examples** showing how to use the system
8. **Demo preparation** with sample data and presentation materials

This implementation plan ensures a clean, atomic migration to the new Spark-based architecture while maintaining the highest standards of code quality and system reliability.