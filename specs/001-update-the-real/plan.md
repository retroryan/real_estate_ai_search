# Implementation Plan: MCP Server Direct Search Service Integration

**Branch**: `001-update-the-real` | **Date**: 2025-01-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-update-the-real/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Direct integration of MCP server with search_service by replacing all MCP models and service implementations with search_service components. This is a complete atomic change that updates the MCP server to use search_service models directly, eliminating all duplicate code and compatibility layers.

## Technical Context
**Language/Version**: Python 3.10+  
**Primary Dependencies**: FastMCP, Elasticsearch Python client, Pydantic  
**Storage**: Elasticsearch (for search indices)  
**Testing**: pytest with integration tests  
**Target Platform**: Linux/macOS server running MCP protocol  
**Project Type**: single - Python service with MCP protocol interface  
**Performance Goals**: Not specified (marked as NOT REQUIRED in spec)  
**Constraints**: Direct replacement - no backward compatibility required per constitution  
**Scale/Scope**: 3 search types (properties, neighborhoods, wikipedia), multiple demo scenarios for validation

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 1 (single Python project - direct integration)
- Using framework directly? YES (FastMCP, Elasticsearch client used directly)
- Single data model? YES (search_service models only, no duplicates)
- Avoiding patterns? YES (direct service usage, no adapters or wrappers)

**Architecture**:
- EVERY feature as library? YES (search_service is the library)
- Libraries listed: 
  - search_service: Unified search functionality for all entities
  - mcp_server: MCP protocol interface using search_service directly
- CLI per library: MCP server provides tool interface via protocol
- Library docs: Will maintain existing documentation

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? YES (tests will be written first)
- Git commits show tests before implementation? YES
- Order: Contract→Integration→E2E→Unit strictly followed? YES
- Real dependencies used? YES (actual Elasticsearch, no mocks)
- Integration tests for: YES (mcp_demos provide integration testing)
- FORBIDDEN: Implementation before test, skipping RED phase - UNDERSTOOD

**Observability**:
- Structured logging included? YES (existing logging infrastructure)
- Frontend logs → backend? N/A (MCP protocol only)
- Error context sufficient? YES (FR-009 requires logging all requests/responses)

**Versioning**:
- Version number assigned? Will use existing versioning
- BUILD increments on every change? Follow existing practice
- Breaking changes handled? N/A - Complete replacement per constitution

## Project Structure

### Documentation (this feature)
```
specs/001-update-the-real/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Direct replacement structure
real_estate_search/
├── search_service/      # Common search service (already exists)
│   ├── models.py       # Unified Pydantic models
│   ├── base.py         # Base search functionality
│   ├── properties.py   # Property search
│   ├── wikipedia.py    # Wikipedia search
│   └── neighborhoods.py # Neighborhood search
│
└── mcp_server/         # MCP protocol interface
    ├── main.py         # Updated to use search_service directly
    ├── tools/          # Updated to use search_service models
    └── settings.py     # Configuration management
```

**Structure Decision**: Option 1 (Single project) - Direct integration within existing codebase

## Phase 0: Outline & Research
1. **Analyze the core issue**:
   - Current MCP server duplicates search_service functionality
   - Models are duplicated between MCP and search_service
   - Solution: Direct replacement, no adapters

2. **Research requirements**:
   - How search_service models differ from MCP models
   - What MCP tools expect vs what search_service provides
   - Direct path to unification

3. **Consolidate findings** in `research.md`:
   - Decision: Direct model replacement
   - Rationale: Constitution requires clean implementation
   - No alternatives - direct replacement only

**Output**: research.md with direct replacement strategy

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Define unified data model** → `data-model.md`:
   - Use search_service models as the single source of truth
   - Document how MCP tools will use these models directly
   - No duplicate models, no adapters

2. **Generate service contracts** from requirements:
   - MCP tools will call search_service methods directly
   - Response format matches search_service output
   - No transformation layers

3. **Generate contract tests**:
   - Test MCP tools with search_service responses
   - Verify direct integration works
   - Tests must fail initially (TDD)

4. **Create quickstart guide**:
   - Steps to validate direct integration
   - No mention of compatibility or migration

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks for direct replacement:
  1. Update MCP models to import from search_service
  2. Replace MCP service classes with search_service imports
  3. Update MCP tools to use search_service directly
  4. Remove all duplicate code
  5. Update tests for new structure
  6. Validate with MCP demos

**Ordering Strategy**:
- TDD order: Tests before implementation
- Complete replacement: All changes in single update
- No gradual migration or compatibility phases

**Estimated Output**: 15-20 tasks for complete replacement

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No violations - this plan follows all constitutional principles:
- Direct replacement only
- No adapters or compatibility layers
- Single atomic change
- Clean implementation

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none - clean implementation)

---
*Based on Constitution v2.0.0 - See `/memory/constitution.md`*