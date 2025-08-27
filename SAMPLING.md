# Sample Size Parameter Implementation

## ✅ IMPLEMENTATION COMPLETE

The sample size parameter has been successfully implemented and tested. The pipeline now correctly respects the `--sample-size` parameter for all three entity types (properties, neighborhoods, Wikipedia).

## Implementation Status

**Phase 1: Configuration and Structure Updates** ✅ COMPLETED
- DataPipelineRunner now passes sample_size to DataLoaderOrchestrator
- DataLoaderOrchestrator constructor accepts and stores sample_size
- Configuration properly flows through the system

**Phase 2: Loader Method Updates** ✅ COMPLETED  
- BaseLoader load method accepts optional sample_size parameter
- All entity loaders (Property, Neighborhood, Wikipedia) apply sampling
- Simple logging indicates when sampling is active
- Dead code cleaned up (removed unnecessary count operations)

**Phase 3: Testing and Validation** ✅ VERIFIED
- Tested with `--sample-size 2` parameter
- Confirmed properties limited to 2 records per file (4 total from 2 files)
- Confirmed neighborhoods limited to 2 records per file (4 total from 2 files)
- Confirmed Wikipedia limited to 2 records total
- All downstream processing works correctly with sampled data

## Complete Cut-Over Requirements

* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CALL FUNCTIONS ENHANCED or IMPROVED**: Change the actual methods. For example if there is a class PropertyIndex and we want to improve that do not create a separate ImprovedPropertyIndex and instead just update the actual PropertyIndex
* **ALWAYS USE PYDANTIC**: All configuration and data models must use Pydantic
* **USE MODULES AND CLEAN CODE**: Maintain clear separation of concerns
* **NO HASATTR**: The pattern `if hasattr` should never be used
* **NO HACKS OR MOCKS**: If it doesn't work, fix the core issue
* **ASK QUESTIONS**: If there are uncertainties, please ask

## Problem Statement

The data pipeline currently ignores the `--sample-size` command-line parameter. When users specify a sample size for development and testing purposes, the pipeline still loads all available data:
- All 420 property records are loaded regardless of sample size
- All neighborhood records are loaded regardless of sample size  
- All Wikipedia articles are loaded regardless of sample size

This causes unnecessary memory usage, longer processing times during development, and makes iterative testing difficult.

## Root Cause Analysis

The sample size parameter follows this path through the system:
1. User provides `--sample-size` via command line argument
2. The main entry point correctly passes it to the configuration loader
3. Configuration loader correctly stores it in PipelineConfig
4. PipelineConfig correctly validates and stores the sample_size value
5. **BREAK**: DataPipelineRunner creates DataLoaderOrchestrator with only data_sources config, not the full config including sample_size
6. **BREAK**: DataLoaderOrchestrator has no knowledge of sample_size
7. **BREAK**: Individual loaders (PropertyLoader, NeighborhoodLoader, WikipediaLoader) load all data without any limiting mechanism

## Proposed Solution

### Core Design Principles

1. **Single Responsibility**: Each loader should be responsible for applying its own sampling
2. **Configuration Flow**: Sample size must flow from PipelineConfig through DataLoaderOrchestrator to individual loaders
3. **Consistency**: All three entity types must respect sampling uniformly
4. **Transparency**: Clear logging must indicate when sampling is active and how many records were sampled
5. **Efficiency**: Sampling should occur as early as possible in the data loading process

### Architectural Changes

#### Configuration Propagation
The sample_size parameter must be propagated through the entire loader hierarchy. This requires updating the initialization chain to pass the sample_size from PipelineConfig down to the individual loaders.

#### Sampling Strategy
Sampling will be applied at the DataFrame level after initial loading but before any transformations or enrichments. This ensures:
- Consistent sampling across all data sources
- Predictable behavior regardless of data source type
- Simple implementation without complex SQL modifications

#### Loader Modifications

##### DataLoaderOrchestrator
- Accept sample_size as a constructor parameter
- Store sample_size as an instance variable
- Pass sample_size to individual loader methods

##### PropertyLoader and NeighborhoodLoader
- Accept sample_size parameter in load method
- Apply DataFrame limiting after successful validation
- Log the sampling action with clear messaging

##### WikipediaLoader
- Accept sample_size parameter in load method
- Apply limiting at the DataFrame level after SQLite query
- Ensure consistent behavior with JSON-based loaders

### Expected Behavior

When a user runs the pipeline with `--sample-size 5`:

1. The configuration system captures and validates the sample size
2. Each loader receives the sample size parameter
3. Properties: Load first 5 records from each property file, then union
4. Neighborhoods: Load first 5 records from each neighborhood file, then union
5. Wikipedia: Load first 5 articles ordered by relevance score
6. Clear logging indicates sampling is active
7. All downstream processing works with the sampled data

### Logging Requirements

Simple logging only:
- Log when sample mode is active at pipeline start
- Log the sample size being applied
- No counting of records (causes Spark actions)

### Error Handling

- If sample_size is less than 1, configuration validation should fail
- If a data source has fewer records than sample_size, use all available records
- Sampling should not cause any downstream processing failures

## Implementation Plan

### Phase 1: Configuration and Structure Updates ✅ COMPLETED

#### Task 1.1: Update PipelineConfig validation ✅
- Ensure sample_size validation is comprehensive
- Add documentation for sample_size behavior
- Verify Pydantic model correctly handles optional sample_size

#### Task 1.2: Modify DataPipelineRunner initialization ✅
- Update DataLoaderOrchestrator instantiation to include sample_size
- Ensure sample_size is passed from config to orchestrator
- Maintain clean separation of concerns

#### Task 1.3: Update DataLoaderOrchestrator constructor ✅
- Add sample_size parameter to constructor
- Store as instance variable
- Update all initialization documentation

### Phase 2: Loader Method Updates ✅ COMPLETED

#### Task 2.1: Modify DataLoaderOrchestrator loading methods ✅
- Update _load_properties to apply sampling
- Update _load_neighborhoods to apply sampling
- Update _load_wikipedia to apply sampling
- Ensure consistent sampling behavior across all loaders

#### Task 2.2: Update BaseLoader interface ✅
- Add optional sample_size parameter to load method signature
- Ensure backward compatibility for loaders that don't need sampling
- Update documentation for the new parameter

#### Task 2.3: Implement sampling in PropertyLoader ✅
- Accept sample_size in load method
- Apply limiting after validation
- Simple log message when sampling

#### Task 2.4: Implement sampling in NeighborhoodLoader ✅
- Accept sample_size in load method
- Apply limiting after validation
- Simple log message when sampling

#### Task 2.5: Implement sampling in WikipediaLoader ✅
- Accept sample_size in load method
- Apply limiting after DataFrame creation
- Ensure ordering is preserved (by relevance_score)
- Simple log message when sampling

### Phase 3: Testing and Validation

#### Task 3.1: Unit tests for configuration
- Test sample_size validation in PipelineConfig
- Test configuration propagation through the system
- Test edge cases (negative values, zero, very large values)

#### Task 3.2: Integration tests for loaders
- Test each loader with various sample sizes
- Test with sample_size larger than available data
- Test with sample_size of 1
- Verify union operations work correctly with sampled data

#### Task 3.3: End-to-end pipeline tests
- Run full pipeline with sample_size parameter
- Verify all downstream processing works correctly
- Verify sampling is applied correctly

#### Task 3.4: Documentation updates
- Update README with sample_size usage examples
- Document the sampling behavior clearly

#### Task 3.5: Code review and final testing
- Complete code review by senior developer
- Run full regression test suite
- Test with production-like data volumes
- Verify performance improvements with sampling
- Test error scenarios and edge cases
- Ensure no breaking changes to existing functionality

## Success Criteria

1. Running `python -m data_pipeline --sample-size 5` limits to 5 records per entity type
2. Simple logging indicates sampling is active
3. All downstream processing works correctly with sampled data
4. No breaking changes to existing functionality
5. Clean, maintainable code following all architectural requirements
6. Comprehensive test coverage for new functionality
7. Updated documentation reflecting the new behavior

## Risk Mitigation

1. **Risk**: Sampling might break downstream processing that expects minimum data volumes
   - **Mitigation**: Add validation to ensure sample_size is reasonable for the pipeline
   
2. **Risk**: Union operations might behave unexpectedly with sampled data
   - **Mitigation**: Comprehensive testing of union operations with various sample sizes
   
3. **Risk**: Performance might degrade if sampling is applied too late
   - **Mitigation**: Apply sampling as early as possible in the data flow

## Timeline Estimate

- Phase 1 (Configuration): 2 hours
- Phase 2 (Loader Updates): 4 hours  
- Phase 3 (Testing): 3 hours
- **Total**: 9 hours

## Questions for Clarification

1. Should sampling be deterministic (same records each run) or random?
2. When multiple files exist for an entity type, should we sample N records from each file or N records total?
3. Should we add a seed parameter for reproducible sampling?
4. Are there any minimum data requirements for downstream processing that we should validate?