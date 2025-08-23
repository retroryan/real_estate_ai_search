# COMMON_MODEL.md

## Implementation Status

### Phases Completed ✅
- **Phase 1**: Setup and Model Extraction - COMPLETED
- **Phase 2**: Model Consolidation and Deduplication - COMPLETED

### Phases Remaining
- **Phase 3**: Update common_ingest Module
- **Phase 4**: Update common_embeddings Module  
- **Phase 5**: Integration Testing
- **Phase 6**: Documentation and Cleanup
- **Phase 7**: Final Validation

### Key Deliverables Created
1. **property_finder_models/** - Complete shared models package with:
   - 8 model modules (core, enums, geographic, entities, embeddings, config, api, exceptions)
   - 60+ Pydantic V2 models extracted and consolidated
   - Comprehensive test suite with 50+ test cases
   - Full documentation and usage examples
   - pyproject.toml with proper dependencies

2. **Consolidation Achievements**:
   - Merged duplicate ChromaDBConfig and ProcessingConfig models
   - Unified all enums into single definitions
   - Kept both BaseEnrichedModel and BaseMetadata as they serve different purposes
   - All models use snake_case naming convention
   - No "Enhanced" or "Improved" versions - direct replacements only

## Complete Cut-Over Requirements

### Key Goals
* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CREATE "ENHANCED" VERSIONS**: Update existing classes directly (e.g., modify PropertyIndex, don't create ImprovedPropertyIndex)
* **CONSISTENT NAMING**: Use snake_case throughout (Python standard)
* **PYDANTIC V2 ONLY**: Use latest Pydantic features without backward compatibility
* **USE LOGGING**: Replace all print statements with proper logging
* **HIGH QUALITY DEMO**: Focus on clean, working code without over-engineering
* **NO MONITORING OVERHEAD**: Skip performance monitoring and schema evolution for simplicity

## Executive Summary

This document outlines the architecture and requirements for creating a shared Pydantic models library that serves as the single source of truth for data structures across the property finder ecosystem. This library will unify model definitions currently duplicated between `common_ingest/` and `common_embeddings/` modules while providing type-safe contracts for API consumers.

## Problem Statement

Currently, both `common_ingest/` and `common_embeddings/` modules maintain separate but overlapping Pydantic model definitions, leading to:
- **Duplication**: ChromaDB configurations, processing settings, and entity models are defined multiple times
- **Inconsistency**: Similar models have slightly different field names and validation rules
- **Maintenance Burden**: Changes must be synchronized across multiple codebases
- **Integration Friction**: API consumers cannot easily import and use the same models the server uses
- **Type Safety Gaps**: Downstream consumers must recreate models or work with untyped JSON

## Solution Architecture

### Core Design Principles

**Model-First Development**: All data structures should be defined as Pydantic V2 models first, with JSON schemas and API documentation generated from these canonical definitions.

**Single Source of Truth**: Each concept should have exactly one model definition that all modules import and use, eliminating duplication and ensuring consistency.

**Progressive Enhancement**: Base models provide core fields, with specialized modules extending them through inheritance for domain-specific needs.

**Type Safety Throughout**: From API server to client SDKs, the same Pydantic models ensure compile-time type checking and runtime validation.

**Version Compatibility**: Support incremental migration from existing models while maintaining backward compatibility during the transition period.

### Package Structure

The shared models library should be organized as a namespace package following Python's latest packaging standards:

**Root Package**: `property_finder_models` - The main namespace for all shared models

**Sub-packages by Domain**:
- `property_finder_models.core` - Base models, common configurations, and utilities
- `property_finder_models.geographic` - Location-related models (coordinates, polygons, addresses)
- `property_finder_models.entities` - Business entities (properties, neighborhoods, Wikipedia articles)
- `property_finder_models.embeddings` - Embedding data structures and metadata
- `property_finder_models.api` - API request/response models and pagination
- `property_finder_models.config` - Configuration models for all services
- `property_finder_models.enums` - Shared enumerations and constants
- `property_finder_models.exceptions` - Common exception hierarchy

### Model Categories and Requirements

#### Foundation Models

**BaseEnrichedModel**: The root model class that all enriched entities inherit from. Should provide:
- Common timestamp fields (created_at, updated_at)
- Version tracking for schema evolution
- UUID generation for correlation
- Standard JSON encoding configuration
- Validation mode settings (strict vs. lax)
- Custom serialization for special types

**BaseMetadata**: Core metadata that all embedding-related models require:
- Unique identifiers (embedding_id, entity_id)
- Type classifications (entity_type, source_type)
- Provenance tracking (source_file, creation_timestamp)
- Correlation identifiers for linking embeddings to source data
- Processing metadata (model_name, provider, dimensions)

#### Geographic Models

**GeoLocation**: Validated geographic coordinates with:
- Latitude/longitude with bounds checking (-90 to 90, -180 to 180)
- Optional elevation and accuracy radius
- Coordinate system specification (default WGS84)
- Distance calculation methods
- Bounding box containment checks

**GeoPolygon**: Geographic boundaries for regions:
- Ordered list of coordinates forming a closed polygon
- Validation for minimum points (at least 3)
- Self-intersection detection
- Area and perimeter calculations
- Point-in-polygon testing

**EnrichedAddress**: Normalized address with geocoding:
- Structured address components (street, city, state, postal code, country)
- Geocoded coordinates with confidence scores
- Address normalization and formatting rules
- International address support
- Validation against postal databases

#### Entity Models

**Property Models**:
- EnrichedProperty: Complete property data with all attributes
- PropertySummary: Lightweight version for list views
- PropertyEmbedding: Property with associated vector embedding
- PropertyFilter: Query parameters for property searches
- PropertyUpdate: Partial update model with optional fields

**Neighborhood Models**:
- EnrichedNeighborhood: Full neighborhood data with demographics
- NeighborhoodBoundary: Geographic polygon with metadata
- NeighborhoodEmbedding: Neighborhood with vector representation
- NeighborhoodStatistics: Aggregated metrics and demographics

**Wikipedia Models**:
- EnrichedWikipediaArticle: Full article with extracted metadata
- WikipediaSummary: AI-generated summary with key topics
- WikipediaLocation: Extracted location data with confidence
- WikipediaEmbedding: Article chunks with embeddings

#### Embedding Models

**EmbeddingData**: Universal container for vector embeddings:
- Vector array with dimension validation
- Model and provider identification
- Generation timestamp and version
- Optional preprocessing steps applied
- Similarity metric specification (cosine, euclidean, dot product)

**ChunkMetadata**: For documents split into multiple embeddings:
- Parent document reference
- Chunk index and total chunks
- Character offsets in original document
- Overlap configuration
- Context window size

**EmbeddingProvider**: Configuration for different providers:
- Provider-specific settings (API keys, endpoints)
- Model selection and parameters
- Batch size and rate limiting
- Retry configuration
- Cost tracking metadata

#### API Models

**Pagination Models**:
- PaginationParams: Page number, size, sort fields
- PaginatedResponse: Generic wrapper with metadata
- CursorPagination: For large dataset iteration
- ResponseLinks: HATEOAS navigation links

**Error Models**:
- ErrorResponse: Standard error format with codes
- ValidationError: Field-level validation failures
- ErrorContext: Additional debugging information
- ProblemDetails: RFC 7807 compliant error format

**Request/Response Wrappers**:
- ResponseEnvelope: Standard response wrapper with metadata
- BatchRequest: Bulk operation requests
- AsyncJobResponse: Long-running operation status
- WebhookPayload: Event notification format

#### Configuration Models

**Service Configuration**:
- DatabaseConfig: Connection strings and pool settings
- CacheConfig: Redis/memcached configuration
- LoggingConfig: Structured logging settings
- SecurityConfig: API keys, OAuth settings, CORS

**Processing Configuration**:
- ChunkingConfig: Text splitting parameters
- EmbeddingConfig: Model selection and parameters
- EnrichmentConfig: Data enhancement settings
- ValidationConfig: Business rule configuration

### Distribution and Packaging Requirements

#### Project Structure and pyproject.toml Configuration

**Separate Packages with Local Dependencies** (Recommended Approach)

Each module maintains its own `pyproject.toml` file with the shared models as a local dependency. This provides clear separation of concerns while enabling shared model usage:

```
real_estate_ai_search/
├── property_finder_models/
│   ├── pyproject.toml         # Models package config
│   ├── __init__.py
│   └── property_finder_models/
│       ├── __init__.py
│       ├── core.py
│       ├── geographic.py
│       ├── entities.py
│       ├── embeddings.py
│       ├── api.py
│       ├── config.py
│       ├── enums.py
│       └── exceptions.py
├── common_ingest/
│   ├── pyproject.toml         # Ingest config with local dependency
│   ├── __init__.py
│   └── (module files)
└── common_embeddings/
    ├── pyproject.toml         # Embeddings config with local dependency
    ├── __init__.py
    └── (module files)
```

**property_finder_models/pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "property-finder-models"
version = "1.0.0"
description = "Shared Pydantic models for Property Finder ecosystem"
requires-python = ">=3.9"
dependencies = [
    "pydantic>=2.0",
    "python-dotenv>=1.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["property_finder_models*"]
```

**common_ingest/pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-ingest"
version = "1.0.0"
description = "Data ingestion service for Property Finder"
requires-python = ">=3.9"
dependencies = [
    "property-finder-models @ file:///../property_finder_models",
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "chromadb>=0.4",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["common_ingest*"]
```

**common_embeddings/pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-embeddings"
version = "1.0.0"
description = "Embedding generation pipeline for Property Finder"
requires-python = ">=3.9"
dependencies = [
    "property-finder-models @ file:///../property_finder_models",
    "chromadb>=0.4",
    "ollama>=0.1",
    "numpy>=1.24",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["common_embeddings*"]
```

**Development Setup**:
```bash
# Install shared models in editable mode
cd property_finder_models
pip install -e .

# Install common_ingest with its dependencies
cd ../common_ingest
pip install -e .

# Install common_embeddings with its dependencies
cd ../common_embeddings
pip install -e .
```

This approach provides:
- Clear module boundaries and dependencies
- Independent versioning capability if needed
- Easy testing of individual modules
- Simple import patterns across all modules

#### Package Metadata

The shared library configuration in `pyproject.toml`:

**Build System**: Use setuptools >= 61.0 with namespace package support

**Dependencies**: 
- Pydantic >= 2.0 (required)
- python-dotenv for configuration
- No optional dependencies to keep it simple

**No Version Management Complexity**: 
- Single version for all packages
- Direct updates only, no compatibility matrices

#### Installation and Import Patterns

**For API Server** (`common_ingest`):
The server should install the models package and import directly:
- Full models for database operations
- Response models for API endpoints
- Validation models for input processing

**For Embedding Pipeline** (`common_embeddings`):
The pipeline should use:
- Metadata models for correlation
- Configuration models for settings
- Processing models for batch operations

**For API Consumers**:
External clients should be able to:
- Install the models package via pip
- Import the exact models the API returns
- Use models for request construction
- Leverage built-in validation

### Best Practices Implementation

#### Pydantic V2 Optimization

**Performance Features**:
- Use Rust-based core validation for speed
- Implement lazy validation where appropriate
- Cache computed properties
- Optimize serialization with model_dump strategies

**Type Safety**:
- Provide both BaseModel and TypedDict versions
- Use strict typing with mypy compatibility
- Generate type stubs for better IDE support
- Include runtime type checking

#### Schema Generation and Documentation

**OpenAPI Integration**:
- Automatic OpenAPI 3.1 schema generation from models
- Rich descriptions using Field() with descriptions
- Example values for better documentation
- Discriminated unions for polymorphic models

**JSON Schema Export**:
- Support for JSON Schema Draft 2020-12
- Custom schema modifications via Config
- Schema versioning and evolution
- Backward compatibility validation

#### Model Validation and Business Rules

**Field Validation**:
- Use Pydantic validators for field-level rules
- Implement model-level validation for cross-field dependencies
- Custom validation error messages
- Validation context passing

**Data Transformation**:
- Pre-processing via validators
- Post-processing via serializers
- Custom field types for complex domains
- Automatic data coercion with strict mode option

### Implementation Approach

**Single Atomic Update**: All models will be extracted, consolidated, and replaced in one complete operation:
- Extract all models to the new shared library
- Update all imports in both modules simultaneously
- Remove all old model definitions
- No temporary compatibility layers or gradual migration

### Testing Requirements

**Unit Testing**:
- Test all validators and custom types
- Verify serialization/deserialization
- Check schema generation accuracy
- Validate example data

**Integration Testing**:
- Cross-module compatibility tests
- API contract testing with models
- Database round-trip validation
- Performance benchmarks

**Consumer Testing**:
- SDK generation from models
- Client-server contract tests
- Version compatibility matrix
- Breaking change detection

### Documentation Requirements

**API Documentation**:
- Auto-generated from model docstrings
- Field descriptions and constraints
- Example requests and responses
- Validation error examples

**Developer Guide**:
- Model inheritance patterns
- Custom validator examples
- Performance optimization tips
- Migration from v1 to v2

**Consumer Guide**:
- Installation instructions
- Import patterns and examples
- Type checking setup
- Common use cases


## Detailed Implementation Plan

### Phase 1: Setup and Model Extraction ✅ COMPLETED
**Goal**: Create the shared models package structure and extract all existing models

#### Todo List:
- [x] Create `property_finder_models/` directory structure
- [x] Create `property_finder_models/pyproject.toml` with Pydantic 2.0+ dependency
- [x] Create module files: `core.py`, `geographic.py`, `entities.py`, `embeddings.py`, `api.py`, `config.py`, `enums.py`, `exceptions.py`
- [x] Extract all models from `common_ingest/models/` to appropriate shared modules
- [x] Extract all models from `common_embeddings/models/` to appropriate shared modules
- [x] Create `__init__.py` files with proper exports
- [x] Install `property_finder_models` in editable mode: `pip install -e ./property_finder_models`

#### Review & Testing:
- [x] Verify all models are syntactically correct (no import errors)
- [x] Run `mypy property_finder_models/` for type checking
- [x] Create basic unit tests for model instantiation
- [x] Document which models came from which original module

---

### Phase 2: Model Consolidation and Deduplication ✅ COMPLETED
**Goal**: Merge duplicate models and establish single definitions

#### Todo List:
- [x] Identify duplicate `ChromaDBConfig` models - merge into single definition
- [x] Identify duplicate `ProcessingConfig` models - merge into single definition
- [x] Consolidate `EmbeddingData` from common_ingest with `BaseMetadata` from common_embeddings
- [x] Merge geographic models (`GeoLocation`, `GeoPolygon`) into single definitions
- [x] Unify entity type enums across both modules
- [x] Consolidate API response models (pagination, errors)
- [x] Ensure all field names use snake_case consistently
- [x] Remove any "Enhanced" or "Improved" prefixes - update base classes directly

#### Review & Testing:
- [x] Validate that merged models contain all necessary fields
- [x] Test serialization/deserialization for all consolidated models
- [x] Run basic instantiation tests for each model
- [x] Verify all validators and field constraints work

---

### Phase 3: Update common_ingest Module
**Goal**: Replace all model imports in common_ingest with shared models

#### Todo List:
- [ ] Create `common_ingest/pyproject.toml` with local dependency on property_finder_models
- [ ] Update all imports in `common_ingest/api/` to use shared models
- [ ] Update all imports in `common_ingest/loaders/` to use shared models
- [ ] Update all imports in `common_ingest/utils/` to use shared models
- [ ] Replace all print statements with logging.info/debug/error
- [ ] Remove all model files from `common_ingest/models/`
- [ ] Update `common_ingest/__init__.py` exports
- [ ] Install common_ingest in editable mode: `pip install -e ./common_ingest`

#### Review & Testing:
- [ ] Run existing common_ingest test suite
- [ ] Start API server and verify all endpoints work
- [ ] Test data loading with PropertyLoader and NeighborhoodLoader
- [ ] Verify API response schemas match expected format
- [ ] Check that all logging is working (no print statements remain)

---

### Phase 4: Update common_embeddings Module
**Goal**: Replace all model imports in common_embeddings with shared models

#### Todo List:
- [ ] Create `common_embeddings/pyproject.toml` with local dependency on property_finder_models
- [ ] Update all imports in `common_embeddings/correlation/` to use shared models
- [ ] Update all imports in `common_embeddings/pipeline/` to use shared models
- [ ] Update all imports in `common_embeddings/providers/` to use shared models
- [ ] Replace all print statements with logging.info/debug/error
- [ ] Remove all model files from `common_embeddings/models/`
- [ ] Update `common_embeddings/__init__.py` exports
- [ ] Install common_embeddings in editable mode: `pip install -e ./common_embeddings`

#### Review & Testing:
- [ ] Run existing common_embeddings test suite
- [ ] Test embedding generation with all providers
- [ ] Verify correlation engine works with new models
- [ ] Test batch processing with new metadata models
- [ ] Check that all logging is working (no print statements remain)

---

### Phase 5: Integration Testing
**Goal**: Verify both modules work together with shared models

#### Todo List:
- [ ] Create integration test that uses both modules together
- [ ] Test property data flow: load → enrich → embed → store → retrieve
- [ ] Test Wikipedia data flow: load → summarize → embed → correlate
- [ ] Verify ChromaDB operations work with unified config model
- [ ] Test API endpoints return proper shared model responses
- [ ] Verify embedding metadata correlation works correctly
- [ ] Test all enums and validators are working properly

#### Review & Testing:
- [ ] Run full end-to-end pipeline for properties
- [ ] Run full end-to-end pipeline for Wikipedia articles
- [ ] Load test API with concurrent requests
- [ ] Verify memory usage is reasonable
- [ ] Check for any deprecation warnings

---

### Phase 6: Documentation and Cleanup
**Goal**: Update all documentation and remove legacy code

#### Todo List:
- [ ] Update main README.md with new import patterns
- [ ] Update CLAUDE.md with new architecture description
- [ ] Create property_finder_models/README.md with model documentation
- [ ] Update API documentation with new model schemas
- [ ] Update example code and notebooks
- [ ] Document the new structure for API consumers

#### Review & Testing:
- [ ] Review all documentation for accuracy
- [ ] Test all example code snippets
- [ ] Verify API documentation matches actual responses
- [ ] Check that all imports in documentation are correct
- [ ] Final test run of all test suites

---

### Phase 7: Final Validation
**Goal**: Ensure complete system works as expected

#### Todo List:
- [ ] Run complete test suite for all three modules
- [ ] Verify no old model imports remain (grep for old paths)
- [ ] Check no print statements remain (grep for print())
- [ ] Validate all pyproject.toml files are correct
- [ ] Test fresh installation in new virtual environment
- [ ] Run type checking on entire codebase
- [ ] Generate API client from OpenAPI schema

#### Review & Testing:
- [ ] Code review of all changes
- [ ] Performance comparison (before/after)
- [ ] Memory usage comparison
- [ ] API response time testing
- [ ] Final sign-off checklist

---

### Execution Note
This is a complete cut-over operation. If any phase fails:
1. Fix the issue immediately
2. Continue with the implementation
3. No rollback to old models - only move forward

## Success Metrics

- **Code Reduction**: 40-50% reduction in duplicated model definitions
- **Type Safety**: Full Pydantic V2 validation throughout the system
- **Clean Architecture**: Single source of truth for all data models
- **API Consistency**: Identical models used by server and clients
- **Developer Experience**: Simple, direct imports with full IDE support

## Conclusion

Creating a shared Pydantic models library represents a critical architectural improvement that will enhance consistency, reduce maintenance burden, and provide superior developer experience for both internal teams and API consumers. By following Python packaging best practices and leveraging Pydantic V2's advanced features, this shared library will serve as the foundation for type-safe, well-validated data exchange throughout the property finder ecosystem.