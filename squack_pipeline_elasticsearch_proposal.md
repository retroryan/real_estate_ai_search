# SQUACK Pipeline Elasticsearch Integration Proposal

## Complete Cut-Over Requirements
* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CALL FUNCTIONS ENHANCED or IMPROVED**: Update the actual methods directly
* **ALWAYS USE PYDANTIC**: All configurations and models must use Pydantic
* **USE MODULES AND CLEAN CODE**: Maintain modular architecture
* **NO hasattr**: Direct attribute access only
* **FIX CORE ISSUES**: Don't hack and mock, fix the root problem
* **ASK QUESTIONS**: If unclear, ask for clarification

## Executive Summary

This proposal outlines the complete restructuring of the SQUACK pipeline to integrate Elasticsearch as an output destination, following the exact patterns established in the data_pipeline. The integration will enable the SQUACK pipeline to write processed property, neighborhood, and Wikipedia data directly to Elasticsearch indices while maintaining its current DuckDB-based processing architecture.

## Current State Analysis

### SQUACK Pipeline Currently:
- Uses DuckDB for data processing through medallion architecture (Bronze/Silver/Gold tiers)
- Writes output only to Parquet files
- Processes properties, neighborhoods, and Wikipedia data
- Generates embeddings using various providers
- Has a single output path through ParquetWriter

### Data Pipeline Pattern:
- Uses Spark for processing
- Supports multiple output destinations (Parquet, Neo4j, Elasticsearch)
- Uses WriterOrchestrator to manage multiple writers
- Implements PipelineFork for output-driven processing paths
- Uses Pydantic models throughout for type safety
- Has modular Elasticsearch writer with separate models, transformations, and orchestrator

## Proposed Architecture

### 1. Configuration Layer

#### Output Configuration Model
The pipeline needs a new output configuration system that mirrors data_pipeline's approach:

**New Configuration Structure:**
- Create `OutputConfig` model with `enabled_destinations` list
- Add `ElasticsearchOutputConfig` for Elasticsearch-specific settings
- Update `PipelineSettings` to include output configuration
- Support configuration via YAML and environment variables

**Elasticsearch Configuration Requirements:**
- Host and port settings
- Authentication credentials (username, password)
- Index prefix for all indices
- Bulk operation size
- Write mode (append/overwrite/upsert)
- SSL/TLS settings
- Connection timeout settings

### 2. Writer Architecture

#### Writer Base Class
Create an abstract base writer that all output writers must implement:
- Abstract methods for entity-specific writes (properties, neighborhoods, Wikipedia)
- Connection validation method
- Writer name identification
- Error handling and result reporting

#### Elasticsearch Writer Components

**Models Module** (`writers/elasticsearch/models.py`):
- `EntityType` enum for supported entities
- `IndexSettings` model for index configuration
- `SchemaTransformation` model for data transformations
- `WriteOperation` model for operation configuration
- `WriteResult` model for operation results
- `ElasticsearchWriterSettings` for writer configuration

**Transformations Module** (`writers/elasticsearch/transformations.py`):
- DuckDB to Elasticsearch data type mapping
- Decimal to double conversion for numeric fields
- Geo-point creation from latitude/longitude
- Array field handling
- ID field mapping
- Field exclusion logic

**Orchestrator Module** (`writers/elasticsearch/orchestrator.py`):
- Main Elasticsearch writer implementation
- Entity-specific write methods
- Connection validation
- Bulk operation management
- Error handling and retry logic

### 3. DuckDB to Elasticsearch Bridge

Since SQUACK uses DuckDB instead of Spark, we need a transformation layer:

**Data Extraction:**
- Query DuckDB tables to extract data as Python dictionaries or Pandas DataFrames
- Handle large datasets with chunking to manage memory
- Preserve data types and handle nulls properly

**Data Transformation:**
- Convert DuckDB data types to Elasticsearch-compatible types
- Handle nested structures and arrays
- Create geo_point fields from coordinates
- Ensure proper ID field mapping

**Bulk Loading:**
- Use Python Elasticsearch client for bulk operations
- Implement batching with configurable batch size
- Handle partial failures with retry logic
- Track successful and failed documents

### 4. Writer Orchestrator

Create a writer orchestrator similar to data_pipeline:

**Responsibilities:**
- Manage multiple output writers
- Coordinate write operations across all entities
- Handle write ordering (neighborhoods before properties for relationships)
- Aggregate results from all writers
- Provide unified error reporting

**Implementation:**
- Accept list of writer instances
- Execute writes in proper sequence
- Collect and report metrics
- Handle failures gracefully

### 5. Pipeline Fork Integration

Implement output-driven processing paths:

**Processing Paths:**
- `lightweight`: Parquet-only output (current behavior)
- `search`: Elasticsearch output (includes document preparation)
- `multi`: Both Parquet and Elasticsearch

**Fork Logic:**
- Determine processing path from enabled destinations
- Prepare data appropriately for each path
- Avoid unnecessary processing for disabled outputs

### 6. Integration with Existing Pipeline

#### Orchestrator Updates
Modify `PipelineOrchestrator` to:
- Initialize writer orchestrator based on configuration
- Create pipeline fork for output routing
- Pass processed data through appropriate writers
- Report metrics from all writers

#### Data Flow:
1. Load raw data (Bronze tier) - unchanged
2. Process to Silver tier - unchanged
3. Process to Gold tier - unchanged
4. Geographic enrichment - unchanged
5. Embedding generation - unchanged
6. **NEW: Fork based on output destinations**
7. **NEW: Write to configured destinations (Parquet/Elasticsearch)**

## Entity-Specific Implementation

### Properties
- Index name: `{prefix}_properties`
- ID field: `listing_id`
- Special handling: geo_point from lat/lng, price as double
- Required transformations: decimal to double, array flattening

### Neighborhoods
- Index name: `{prefix}_neighborhoods`
- ID field: `neighborhood_id`
- Special handling: geo_point from centroid, statistics as nested objects
- Required transformations: nested object handling

### Wikipedia
- Index name: `{prefix}_wikipedia`
- ID field: `page_id` (cast to string)
- Special handling: text content, categories as arrays
- Required transformations: text field optimization

## Error Handling Strategy

### Connection Failures
- Validate connection before processing
- Implement exponential backoff for retries
- Fail fast if connection cannot be established
- Log detailed error information

### Data Transformation Errors
- Validate data before transformation
- Handle type conversion failures gracefully
- Log problematic records for debugging
- Continue processing remaining data

### Bulk Operation Failures
- Handle partial bulk failures
- Retry failed documents with smaller batches
- Track and report failed document IDs
- Provide detailed failure statistics

## Validation Requirements

### Pre-write Validation
- Verify Elasticsearch cluster is accessible
- Ensure indices can be created/accessed
- Validate data schema compatibility
- Check authentication and permissions

### Post-write Validation
- Verify document counts match expectations
- Sample documents to ensure proper transformation
- Check index mappings are correct
- Validate geo_point fields if applicable

## Testing Strategy

### Unit Tests
- Test each writer component in isolation
- Mock DuckDB connections and Elasticsearch client
- Test data transformation logic
- Verify error handling

### Integration Tests
- Test full pipeline with test data
- Verify data flows correctly to Elasticsearch
- Test with multiple output destinations
- Validate error recovery

### Performance Tests
- Test with various data sizes
- Measure bulk operation performance
- Optimize batch sizes
- Monitor memory usage

## Implementation Plan

### Phase 1: Configuration and Models (Day 1-2)
1. Create output configuration models using Pydantic
2. Update PipelineSettings to include output configuration
3. Add Elasticsearch configuration to YAML schema
4. Implement configuration validation

### Phase 2: Elasticsearch Writer Core (Day 3-5)
1. Create writer base class
2. Implement Elasticsearch models
3. Build DuckDB to Elasticsearch transformation layer
4. Create Elasticsearch orchestrator

### Phase 3: Writer Orchestrator (Day 6-7)
1. Implement WriterOrchestrator class
2. Add entity-specific write methods
3. Integrate error handling and reporting
4. Add metrics collection

### Phase 4: Pipeline Fork (Day 8-9)
1. Create PipelineFork class
2. Implement processing path determination
3. Add data routing logic
4. Integrate with pipeline orchestrator

### Phase 5: Pipeline Integration (Day 10-11)
1. Update PipelineOrchestrator
2. Wire up writer orchestrator
3. Connect pipeline fork
4. Update metrics and logging

### Phase 6: Testing and Validation (Day 12-14)
1. Write comprehensive unit tests
2. Create integration tests
3. Perform end-to-end testing
4. Document test results

### Phase 7: Code Review and Final Testing (Day 15)
1. Conduct thorough code review
2. Run full test suite
3. Performance testing
4. Fix any identified issues
5. Update documentation

## Success Criteria

1. **Functional Requirements:**
   - Successfully write all entity types to Elasticsearch
   - Support multiple output destinations simultaneously
   - Maintain data integrity through transformations
   - Handle errors gracefully without data loss

2. **Performance Requirements:**
   - Process and write 100,000+ documents efficiently
   - Bulk operations complete within reasonable time
   - Memory usage remains within limits
   - No performance degradation of existing functionality

3. **Code Quality Requirements:**
   - All models use Pydantic for type safety
   - Clean, modular architecture
   - Comprehensive error handling
   - Full test coverage for new code
   - No code duplication or wrapper functions

4. **Integration Requirements:**
   - Seamless integration with existing pipeline
   - No breaking changes to current functionality
   - Configuration backward compatible
   - Clear migration path for users

## Risks and Mitigation

### Risk 1: DuckDB to Elasticsearch Data Type Incompatibility
**Mitigation:** Create comprehensive type mapping table and test with all data types

### Risk 2: Memory Issues with Large Datasets
**Mitigation:** Implement chunking and streaming for large result sets

### Risk 3: Elasticsearch Connection/Authentication Issues
**Mitigation:** Implement robust connection validation and clear error messages

### Risk 4: Performance Degradation
**Mitigation:** Profile code, optimize bulk operations, implement parallel processing where possible

## Questions to Resolve

1. Should we support custom index mappings or use dynamic mapping?
2. What should be the default bulk operation size?
3. Should we implement index lifecycle management?
4. Do we need to support multiple Elasticsearch clusters?
5. Should we add support for OpenSearch as well?

## Conclusion

This proposal provides a complete blueprint for integrating Elasticsearch into the SQUACK pipeline following the patterns established in data_pipeline. The implementation maintains clean architecture, uses Pydantic throughout, and ensures a complete atomic update without migration phases or compatibility layers. The modular design allows for easy testing and future enhancements while maintaining the existing DuckDB-based processing capabilities.