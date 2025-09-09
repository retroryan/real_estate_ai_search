# Implementation Tasks: MCP Server Direct Search Service Integration

**Feature**: MCP Server Direct Search Service Integration  
**Branch**: `001-update-the-real`  
**Created**: 2025-01-07

## Overview

Complete atomic replacement of MCP server's duplicate search implementations with direct search_service integration. No adapters, no compatibility layers, no gradual migration - following constitutional principles.

## Parallel Execution Guide

Tasks marked with [P] can be executed in parallel:
```bash
# Example: Running parallel test tasks
Task agent --parallel T003 T004 T005
Task agent --parallel T008 T009 T010
```

## Task List

### Phase 1: Test Setup (TDD - Tests First)

#### T001: Create Integration Test for Property Search Tool
**File**: `real_estate_search/mcp_server/tests/test_property_tool_integration.py`
**Dependencies**: None
**Description**: Write failing test that expects MCP property tool to use search_service models directly
```python
# Test must verify:
# - Tool uses search_service.models.PropertySearchRequest
# - Tool returns search_service.PropertySearchResponse.model_dump()
# - No adapters or transformations
```

#### T002: Create Integration Test for Wikipedia Search Tool
**File**: `real_estate_search/mcp_server/tests/test_wikipedia_tool_integration.py`
**Dependencies**: None
**Description**: Write failing test that expects MCP Wikipedia tool to use search_service models directly
```python
# Test must verify:
# - Tool uses search_service.models.WikipediaSearchRequest
# - Tool returns search_service.WikipediaSearchResponse.model_dump()
# - Direct service usage
```

#### T003: Create Integration Test for Neighborhood Search Tool [P]
**File**: `real_estate_search/mcp_server/tests/test_neighborhood_tool_integration.py`
**Dependencies**: None
**Description**: Write failing test that expects MCP neighborhood tool to use search_service models directly

#### T004: Create Test for Model Deletion Verification [P]
**File**: `real_estate_search/mcp_server/tests/test_model_deletion.py`
**Dependencies**: None
**Description**: Test that verifies all MCP models are deleted and only search_service models exist

#### T005: Create Test for Service Deletion Verification [P]
**File**: `real_estate_search/mcp_server/tests/test_service_deletion.py`
**Dependencies**: None
**Description**: Test that verifies MCP duplicate services are deleted

### Phase 2: Core Deletion Tasks

#### T006: Delete All MCP Model Files
**Files to Delete**:
- `real_estate_search/mcp_server/models/property.py`
- `real_estate_search/mcp_server/models/wikipedia.py`
- `real_estate_search/mcp_server/models/search.py`
- `real_estate_search/mcp_server/models/hybrid.py`
- `real_estate_search/mcp_server/models/responses.py`
**Dependencies**: T001-T005 (tests must fail first)
**Description**: Complete deletion of all duplicate model files

#### T007: Delete MCP Service Duplicates
**Files to Delete**:
- `real_estate_search/mcp_server/services/property_search.py`
- `real_estate_search/mcp_server/services/wikipedia_search.py`
**Dependencies**: T001-T005 (tests must fail first)
**Description**: Complete deletion of duplicate service implementations

### Phase 3: Import Updates

#### T008: Update Property Tool Imports [P]
**File**: `real_estate_search/mcp_server/tools/property_tools.py`
**Dependencies**: T006, T007
**Changes**:
```python
# OLD (DELETE):
from ..models.property import PropertySearchRequest
from ..services.property_search import PropertySearchService

# NEW (ADD):
from ...search_service.models import PropertySearchRequest, PropertySearchResponse
from ...search_service.properties import PropertySearchService
```

#### T009: Update Wikipedia Tool Imports [P]
**File**: `real_estate_search/mcp_server/tools/wikipedia_tools.py`
**Dependencies**: T006, T007
**Changes**:
```python
# OLD (DELETE):
from ..models.wikipedia import WikipediaSearchRequest
from ..services.wikipedia_search import WikipediaSearchService

# NEW (ADD):
from ...search_service.models import WikipediaSearchRequest, WikipediaSearchResponse
from ...search_service.wikipedia import WikipediaSearchService
```

#### T010: Update Hybrid Search Tool Imports [P]
**File**: `real_estate_search/mcp_server/tools/hybrid_search_tool.py`
**Dependencies**: T006, T007
**Description**: Update all imports to use search_service models and services

### Phase 4: Tool Implementation Updates

#### T011: Update Property Tool to Use Search Service Directly
**File**: `real_estate_search/mcp_server/tools/property_tools.py`
**Dependencies**: T008
**Changes**:
- Remove all transformation/adapter code
- Use PropertySearchRequest from search_service directly
- Return response.model_dump() directly
- No backward compatibility handling

#### T012: Update Wikipedia Tool to Use Search Service Directly
**File**: `real_estate_search/mcp_server/tools/wikipedia_tools.py`
**Dependencies**: T009
**Changes**:
- Remove all transformation/adapter code
- Use WikipediaSearchRequest from search_service directly
- Return response.model_dump() directly

#### T013: Update Neighborhood Tool Implementation
**File**: `real_estate_search/mcp_server/tools/hybrid_search_tool.py` or create `neighborhood_tools.py`
**Dependencies**: T010
**Description**: Implement neighborhood search using search_service.neighborhoods.NeighborhoodSearchService

### Phase 5: Main Server Updates

#### T014: Update MCP Server Main Initialization
**File**: `real_estate_search/mcp_server/main.py`
**Dependencies**: T011, T012, T013
**Changes**:
```python
# Update service initialization to use search_service directly:
from elasticsearch import Elasticsearch
from real_estate_search.search_service.properties import PropertySearchService
from real_estate_search.search_service.wikipedia import WikipediaSearchService
from real_estate_search.search_service.neighborhoods import NeighborhoodSearchService

# Initialize with raw ES client
es_client = Elasticsearch(hosts=[config.elasticsearch.host])
property_service = PropertySearchService(es_client)
wikipedia_service = WikipediaSearchService(es_client)
neighborhood_service = NeighborhoodSearchService(es_client)
```

#### T015: Update Any Remaining Import References
**Files**: Search and update any remaining files in mcp_server/
**Dependencies**: T014
**Description**: Find and update any remaining imports that reference deleted models/services

### Phase 6: Demo Updates

#### T016: Update MCP Demo Property Search Expectations [P]
**File**: `real_estate_search/mcp_demos/demos/property_search.py`
**Dependencies**: T011
**Description**: Update to expect search_service response format

#### T017: Update MCP Demo Wikipedia Search Expectations [P]
**File**: `real_estate_search/mcp_demos/demos/wikipedia_search.py`
**Dependencies**: T012
**Description**: Update to expect search_service response format

#### T018: Update MCP Demo Multi-Entity Expectations [P]
**File**: `real_estate_search/mcp_demos/demos/multi_entity.py`
**Dependencies**: T013
**Description**: Update neighborhood search expectations

### Phase 7: Validation

#### T019: Run All Integration Tests
**Command**: `pytest real_estate_search/mcp_server/tests/`
**Dependencies**: T001-T018
**Description**: Verify all tests pass with direct integration

#### T020: Run MCP Demos End-to-End
**Command**: `cd real_estate_search/mcp_demos && python run_all_demos.py`
**Dependencies**: T019
**Description**: Validate complete integration with demos

#### T021: Verify No Adapter Code Remains
**Script**: Create verification script to check for adapter patterns
**Dependencies**: T020
**Description**: Scan codebase to ensure no adapter/conversion code remains

### Phase 8: Cleanup

#### T022: Remove Old Test Files for Deleted Models [P]
**Files**: Any test files for deleted MCP models/services
**Dependencies**: T019
**Description**: Delete tests for removed MCP components

#### T023: Update Documentation [P]
**Files**: Update any documentation referencing old MCP models
**Dependencies**: T019
**Description**: Update docs to reflect direct search_service usage

#### T024: Final Atomic Commit
**Command**: `git add -A && git commit -m "feat: Complete atomic replacement of MCP search with direct search_service integration"`
**Dependencies**: T001-T023
**Description**: Single commit for entire replacement per constitution

## Summary

Total Tasks: 24
- Test Tasks (TDD): T001-T005
- Deletion Tasks: T006-T007
- Import Updates: T008-T010
- Implementation: T011-T015
- Demo Updates: T016-T018
- Validation: T019-T021
- Cleanup: T022-T024

Parallel Execution Opportunities:
- Phase 1: T003, T004, T005 can run in parallel
- Phase 3: T008, T009, T010 can run in parallel
- Phase 6: T016, T017, T018 can run in parallel
- Phase 8: T022, T023 can run in parallel

## Critical Path

1. Tests first (T001-T005) - Must fail before implementation
2. Delete duplicate code (T006-T007)
3. Update imports and implementations (T008-T015)
4. Update demos (T016-T018)
5. Validate (T019-T021)
6. Cleanup and commit (T022-T024)

This is a complete atomic change with no backward compatibility, following constitutional principles.