# INIT_DB.md

## ALWAYS USE PYDANTIC
## USE MODULES AND CLEAN CODE!

### IMPLEMENTATION PRINCIPLES:
* COMPLETE CHANGE: All occurrences must be changed in a single, atomic update
* CLEAN IMPLEMENTATION: Simple, direct replacements only
* NO MIGRATION PHASES: Do not create temporary compatibility periods
* NO PARTIAL UPDATES: Change everything or change nothing
* NO COMPATIBILITY LAYERS: Do not maintain old and new paths simultaneously
* NO BACKUPS OF OLD CODE: Do not comment out old code "just in case"
* NO CODE DUPLICATION: Do not duplicate functions to handle both patterns
* NO WRAPPER FUNCTIONS: Direct replacements only, no abstraction layers
* DO NOT CALL FUNCTIONS ENHANCED or IMPROVED and change the actual methods

---

## Project Goal

Replace the data ingestion mechanism in graph-real-estate/ with the existing data_pipeline/ module, transforming graph-real-estate into a focused graph database initialization and management utility that consumes data from the pipeline.

## Current State Analysis

### Graph-Real-Estate Module
- Currently handles its own data loading from JSON files
- Performs data validation internally
- Creates graph structures directly from raw data
- Main entry point does too much: loading, validation, and graph building

### Data Pipeline Module
- Already has robust data loading infrastructure using Spark
- Provides validated, enriched data through parquet files
- Handles locations.json and all entity types comprehensively
- Outputs structured data ready for consumption

## Proposed Architecture

### Separation of Concerns

**Data Pipeline Responsibilities:**
- Load all raw data from JSON sources
- Validate and clean data using Spark
- Enrich data with relationships and embeddings
- Output processed data to parquet files
- Handle all data transformation logic

**Graph-Real-Estate Responsibilities:**
- Initialize Neo4j database connection
- Create graph schema and indexes
- Read processed data from parquet files
- Build graph structures from validated data
- Provide graph query utilities

### Data Flow

1. Data Pipeline processes raw JSON files into enriched parquet datasets
2. Graph-Real-Estate reads parquet files as input
3. Graph builder creates nodes and relationships from pre-validated data
4. No duplicate validation or loading logic

## Detailed Requirements

### Module Structure Requirements

**Graph-Real-Estate Module Organization:**
- Move to self-contained module with own pyproject.toml
- Execute from parent directory like data_pipeline
- Clear separation between initialization and graph building
- Remove all direct JSON loading functionality
- Consume only parquet files from data_pipeline output

**Main Entry Point Simplification:**
- Main function only handles database initialization
- Creates schema and indexes
- Optionally clears existing data
- Delegates to graph builder for data population
- No data loading or validation logic

**Graph Builder Relocation:**
- Extract useful functionality from archive/controllers/graph_builder.py
- Place in utils/graph_builder.py as primary implementation
- Remove archive dependencies completely
- Direct parquet file reading instead of JSON

### Data Model Requirements

**Pydantic Models Throughout:**
- Define strict Pydantic models for all graph entities
- Use these models for parquet schema validation
- Ensure type safety at all boundaries
- Models should match data_pipeline output schemas

**Entity Models Required:**
- Property node model with all attributes
- Neighborhood node model
- Location hierarchy models (City, County, State)
- Wikipedia article node model
- Relationship models with typed properties

### Integration Requirements

**Parquet File Reading:**
- Read directly from data_pipeline output directory
- Support all entity types: properties, neighborhoods, locations, wikipedia
- Handle enriched data with embeddings
- Maintain data integrity from pipeline

**Configuration Management:**
- Separate configuration for graph database connection
- Reference data pipeline output paths
- Environment-based configuration support
- No duplication of data source definitions

### Error Handling Requirements

**Robust Error Management:**
- Clear error messages for missing parquet files
- Database connection validation
- Transaction rollback on failures
- Comprehensive logging at all stages

## Implementation Plan

### Phase 1: Module Restructuring

**Objective:** Create self-contained graph-real-estate module structure

**Tasks:**
1. Create pyproject.toml for graph-real-estate module
2. Define module dependencies (neo4j, pydantic, pyarrow, pandas)
3. Establish proper package structure with __init__.py files
4. Configure module to run from parent directory
5. Set up logging configuration

### Phase 2: Pydantic Model Definition

**Objective:** Define comprehensive Pydantic models for all entities

**Tasks:**
1. Create models/base.py with base model definitions
2. Define PropertyNode model matching parquet schema
3. Define NeighborhoodNode model
4. Define LocationNode hierarchy (State, County, City)
5. Define WikipediaNode model
6. Define relationship models with properties
7. Add validation rules and type constraints

### Phase 3: Graph Builder Migration

**Objective:** Extract and refactor graph building logic

**Tasks:**
1. Analyze archive/controllers/graph_builder.py for reusable logic
2. Create utils/graph_builder.py with clean implementation
3. Remove all JSON loading code
4. Implement parquet reading functionality
5. Add batch processing for large datasets
6. Implement node creation methods
7. Implement relationship creation methods
8. Add transaction management

### Phase 4: Database Initialization

**Objective:** Create focused database initialization utilities

**Tasks:**
1. Create utils/db_initializer.py for database setup
2. Implement schema creation methods
3. Implement index creation for all node types
4. Add constraint definitions
5. Implement database clearing functionality
6. Add connection validation

### Phase 5: Main Entry Point Simplification

**Objective:** Reduce main.py to initialization orchestration only

**Tasks:**
1. Remove all data loading logic from main.py
2. Implement simple initialization flow
3. Add command-line argument parsing for options
4. Implement clear, init, and load commands
5. Add configuration loading
6. Implement error handling and logging

### Phase 6: Parquet Integration

**Objective:** Connect to data pipeline output

**Tasks:**
1. Create readers/parquet_reader.py for data access
2. Implement entity-specific reading methods
3. Add schema validation against Pydantic models
4. Handle missing or corrupt files gracefully
5. Implement data streaming for large files

### Phase 7: Configuration Management

**Objective:** Establish proper configuration structure

**Tasks:**
1. Create config.yaml for graph database settings
2. Add environment variable support
3. Reference data pipeline output paths
4. Add runtime configuration validation
5. Implement configuration loading in main

### Phase 8: Testing Infrastructure

**Objective:** Ensure reliability and correctness

**Tasks:**
1. Create unit tests for Pydantic models
2. Test parquet reading functionality
3. Test graph builder methods
4. Test database initialization
5. Create integration tests with sample data
6. Add performance benchmarks

## Detailed Todo List

### Setup and Structure
- [ ] Create graph-real-estate/pyproject.toml with project metadata and dependencies
- [ ] Add pydantic, neo4j-driver, pyarrow, pandas to dependencies
- [ ] Create proper package structure with __init__.py files
- [ ] Set up module to run as `python -m graph_real_estate` from parent
- [ ] Configure structured logging with proper formatters

### Pydantic Models
- [ ] Create graph_real_estate/models/__init__.py
- [ ] Create graph_real_estate/models/base.py with BaseNode and BaseRelationship
- [ ] Define PropertyNode model with all required fields
- [ ] Define NeighborhoodNode model with geographic attributes
- [ ] Define StateNode, CountyNode, CityNode models
- [ ] Define WikipediaArticleNode model
- [ ] Define relationship models (LOCATED_IN, NEARBY, MENTIONED_IN)
- [ ] Add field validators for data integrity
- [ ] Add model configuration for JSON serialization

### Graph Builder Implementation
- [ ] Create graph_real_estate/utils/__init__.py
- [ ] Create graph_real_estate/utils/graph_builder.py
- [ ] Extract node creation logic from archive
- [ ] Extract relationship creation logic from archive
- [ ] Remove all JSON file reading code
- [ ] Implement batch node creation with transactions
- [ ] Implement batch relationship creation
- [ ] Add progress tracking for large datasets
- [ ] Implement error recovery mechanisms

### Database Initialization
- [ ] Create graph_real_estate/utils/db_initializer.py
- [ ] Implement Neo4j connection management
- [ ] Create schema definition methods
- [ ] Implement index creation for each node type
- [ ] Add unique constraints on identifiers
- [ ] Implement database clearing with confirmation
- [ ] Add connection health checks
- [ ] Implement retry logic for transient failures

### Parquet Reader Implementation
- [ ] Create graph_real_estate/readers/__init__.py
- [ ] Create graph_real_estate/readers/parquet_reader.py
- [ ] Implement read_properties() method
- [ ] Implement read_neighborhoods() method
- [ ] Implement read_locations() method
- [ ] Implement read_wikipedia() method
- [ ] Add schema validation against Pydantic models
- [ ] Implement streaming for large files
- [ ] Add file existence validation

### Main Entry Point
- [ ] Simplify graph_real_estate/main.py to initialization only
- [ ] Remove all data loading logic
- [ ] Implement argument parser with clear/init/load commands
- [ ] Add --clear flag for database reset
- [ ] Add --schema-only flag for structure without data
- [ ] Implement orchestration flow
- [ ] Add comprehensive error handling
- [ ] Implement graceful shutdown

### Configuration
- [ ] Create graph_real_estate/config.yaml
- [ ] Define Neo4j connection settings
- [ ] Add parquet input path configuration
- [ ] Reference data_pipeline output directory
- [ ] Add batch size configurations
- [ ] Implement environment variable overrides
- [ ] Create configuration loader
- [ ] Add configuration validation

### Integration Points
- [ ] Verify parquet schema compatibility
- [ ] Ensure data pipeline output paths are correct
- [ ] Validate entity relationships are preserved
- [ ] Confirm embedding data is accessible
- [ ] Test end-to-end data flow

### Documentation
- [ ] Update README with new architecture
- [ ] Document Pydantic model schemas
- [ ] Create usage examples
- [ ] Document configuration options
- [ ] Add troubleshooting guide

### Testing
- [ ] Create tests/__init__.py
- [ ] Write unit tests for each Pydantic model
- [ ] Test parquet reader with sample files
- [ ] Test graph builder node creation
- [ ] Test graph builder relationship creation
- [ ] Test database initialization
- [ ] Create integration test with full pipeline
- [ ] Add performance benchmarks
- [ ] Test error handling paths

### Code Review and Testing
- [ ] Review all Pydantic models for completeness
- [ ] Verify no JSON loading code remains
- [ ] Ensure all archive dependencies are removed
- [ ] Validate module runs from parent directory
- [ ] Check logging is comprehensive
- [ ] Verify error messages are helpful
- [ ] Run full integration test suite
- [ ] Performance test with full dataset
- [ ] Document any discovered issues
- [ ] Final code review and testing

## Success Criteria

1. Graph-real-estate no longer reads any JSON files directly
2. All data comes from data_pipeline parquet output
3. Main function only handles initialization
4. All models use Pydantic for validation
5. Module is self-contained with its own pyproject.toml
6. Can be run as `python -m graph_real_estate` from parent
7. Clear separation between data processing and graph building
8. No duplicate data validation logic
9. Comprehensive error handling throughout
10. All tests pass with full dataset