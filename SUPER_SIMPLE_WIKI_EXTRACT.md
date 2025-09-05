# Wikipedia Location Extraction Integration Proposal

## Complete Cut-Over Requirements
* FOLLOW THE REQUIREMENTS EXACTLY!!! Do not add new features or functionality beyond the specific requirements requested and documented
* ALWAYS FIX THE CORE ISSUE!
* COMPLETE CHANGE: All occurrences must be changed in a single, atomic update
* CLEAN IMPLEMENTATION: Simple, direct replacements only
* NO MIGRATION PHASES: Do not create temporary compatibility periods
* NO PARTIAL UPDATES: Change everything or change nothing
* NO COMPATIBILITY LAYERS or Backwards Compatibility: Do not maintain old and new paths simultaneously
* NO BACKUPS OF OLD CODE: Do not comment out old code "just in case"
* NO CODE DUPLICATION: Do not duplicate functions to handle both patterns
* NO WRAPPER FUNCTIONS: Direct replacements only, no abstraction layers
* DO NOT CALL FUNCTIONS ENHANCED or IMPROVED and change the actual methods
* ALWAYS USE PYDANTIC
* USE MODULES AND CLEAN CODE!
* Never name things after the phases or steps of the proposal
* if hasattr should never be used. And never use isinstance
* Never cast variables or cast variable names or add variable aliases
* If you are using a union type something is wrong. Go back and evaluate the core issue
* If it doesn't work don't hack and mock. Fix the core issue
* If there are questions please ask!!!
* Do not generate mocks or sample data if the actual results are missing

## Executive Summary

Enable Wikipedia search to automatically extract location information from natural language queries using the existing DSPy-powered LocationUnderstandingModule. This will allow users to search for Wikipedia articles with queries like "museums in San Francisco" without manually specifying location parameters.

## Current State

Wikipedia search currently requires explicit location parameters:
- Users must manually specify city and state as separate parameters
- No automatic understanding of location context in queries
- Two separate code paths for demos and MCP server
- Location filtering works but requires structured input

## Proposed Solution

### Phase 1: Basic Location Extraction for Wikipedia Search

**Goal**: Add automatic location extraction to WikipediaSearchService using the existing LocationUnderstandingModule.

**Scope**:
- WikipediaSearchService will use LocationUnderstandingModule to extract locations from query text
- Extracted city and state will be applied as filters automatically
- The cleaned query (with location removed) will be used for text search
- No changes to external APIs or parameters

**Requirements**:
- When a query contains a location, extract it and filter results to that location
- When no location is found, search all Wikipedia articles
- Use the exact same LocationUnderstandingModule that property search uses
- Apply extracted locations as Elasticsearch filters
- All location parameters are now extracted from the query text

**User Experience**:
- Query: "Golden Gate Bridge history" → Extracts "Golden Gate", searches for "Bridge history"
- Query: "parks in Oakland" → Extracts "Oakland", searches for "parks"
- Query: "Temescal neighborhood culture" → Extracts "Temescal", searches for "neighborhood culture"

### Phase 2: Enhanced Location Parameters

**Goal**: Expand location extraction to include neighborhoods and improve location matching.

**Scope**:
- Add neighborhood as an extractable and filterable field
- Support pre-extracted location parameters passed to the service
- Allow combination of extracted and explicit location parameters

**Requirements**:
- WikipediaSearchRequest model accepts optional pre-extracted LocationIntent
- If LocationIntent is provided, skip extraction and use provided values
- Support neighborhood-level filtering in addition to city and state
- Maintain ability to override extraction with explicit parameters

**User Experience**:
- Service accepts either natural language or structured location input
- Can pass pre-extracted location data to avoid re-extraction
- Neighborhood-level searches become possible

### Phase 3: Unified Search Service

**Goal**: Consolidate Wikipedia search implementation for both demos and MCP server.

**Scope**:
- Single WikipediaSearchService used by all consumers
- Consistent location extraction behavior everywhere
- Shared configuration and settings

**Requirements**:
- Demo queries use the same WikipediaSearchService as MCP
- Remove duplicate search implementations
- Maintain all existing functionality
- Single source of truth for Wikipedia search logic

**Benefits**:
- Consistent behavior across all interfaces
- Easier maintenance and updates
- Single point for bug fixes and improvements

## Implementation Status

### Phase 1: COMPLETED ✅
- Created new `demo_wikipedia_location_search` function in `real_estate_search/demo_queries/wikipedia_location_search.py`
- Integrated LocationUnderstandingModule for automatic location extraction
- Successfully extracts cities, states, and neighborhoods from natural language queries
- Applies extracted locations as Elasticsearch filters
- Test results confirm extraction working correctly:
  - "museums in San Francisco" → Extracted City: San Francisco
  - "parks in Oakland" → Extracted City: Oakland
  - "Berkeley campus buildings" → Extracted City: Berkeley, State: California

## Implementation Plan

### Phase 1 Implementation Steps

**Modify WikipediaSearchService**:

1. Import LocationUnderstandingModule
2. Add location extraction step before building filters
3. Update query processing to use cleaned query text
4. Modify filter building to use extracted locations
5. Remove old explicit location parameters

**Update Dependencies**:
1. Ensure DSPy configuration is accessible to WikipediaSearchService
2. Verify LocationUnderstandingModule can be instantiated
3. Check that all required environment variables are available

**Data Flow**:
1. Receive search request with natural language query
2. Extract location using LocationUnderstandingModule
3. Build filters from extracted location
4. Use cleaned query for text search
5. Return filtered results

**Todo List - Phase 1**:
- [x] Create new demo_wikipedia_location_search function
- [x] Import LocationUnderstandingModule and LocationFilterBuilder
- [x] Implement location extraction from natural language queries
- [x] Apply extracted locations as Elasticsearch filters
- [x] Use cleaned query text for search
- [x] Add logging for extraction process
- [x] Test with various location-based queries
- [x] Verify extraction accuracy
- [x] Export new function in demo_queries module
- [x] Code review and testing

### Phase 2 Implementation Steps

**Extend WikipediaSearchRequest Model**:
1. Add optional LocationIntent field
2. Add neighborhood as optional parameter
3. Update validation logic

**Update WikipediaSearchService**:
1. Check for pre-extracted LocationIntent
2. Skip extraction if LocationIntent provided
3. Add neighborhood to filter building
4. Support combination of extracted and explicit values

**Todo List - Phase 2**:
- [ ] Update WikipediaSearchRequest Pydantic model
- [ ] Add LocationIntent as optional field
- [ ] Add neighborhood parameter
- [ ] Update service to check for pre-extracted location
- [ ] Modify filter builder to include neighborhood
- [ ] Handle parameter precedence logic
- [ ] Write tests for pre-extracted location handling
- [ ] Write tests for neighborhood filtering
- [ ] Update API documentation
- [ ] Code review and testing

### Phase 3 Implementation Steps

**Consolidate Search Services**:
1. Identify all Wikipedia search implementations
2. Update demos to use WikipediaSearchService
3. Remove duplicate search logic
4. Unify configuration handling

**Update Demo Queries**:
1. Replace custom search logic with service calls
2. Update result processing to match service output
3. Maintain existing demo functionality

**Todo List - Phase 3**:
- [ ] Audit all Wikipedia search implementations
- [ ] Update demo queries to use WikipediaSearchService
- [ ] Remove duplicate search functions
- [ ] Consolidate configuration settings
- [ ] Update imports and dependencies
- [ ] Verify all demos still work correctly
- [ ] Test MCP server functionality
- [ ] Performance testing and optimization
- [ ] Documentation updates
- [ ] Code review and testing

## Testing Strategy

### Phase 1 Testing
- Test location extraction accuracy with various query formats
- Verify filtering works correctly with extracted locations
- Ensure queries without locations work as before
- Test that all location filtering uses extraction

### Phase 2 Testing
- Test pre-extracted location handling
- Verify neighborhood filtering works
- Test parameter precedence and override logic
- Ensure all combinations of parameters work

### Phase 3 Testing
- Full regression testing of all demos
- MCP server functionality testing
- Performance comparison before and after consolidation
- End-to-end integration testing

## Success Criteria

### Phase 1
- Natural language queries with locations work automatically
- No degradation in search quality
- Clean atomic replacement of old location filtering
- 90%+ accuracy in location extraction

### Phase 2
- Pre-extracted locations eliminate redundant processing
- Neighborhood-level search works correctly
- Flexible parameter handling implemented
- All tests passing

### Phase 3
- Single search service handles all use cases
- No duplicate code remains
- All existing functionality preserved
- Improved maintainability achieved

## Risk Mitigation

### Risks
1. DSPy extraction might slow down search
2. Location extraction accuracy might be insufficient
3. All callers must be updated atomically
4. Configuration complexity increases

### Mitigations
1. Cache extraction results where possible
2. Monitor and improve extraction model
3. Update all callers in single commit
4. Keep configuration simple and well-documented

## Timeline Estimate

- **Phase 1**: 2-3 days
  - Day 1: Implementation
  - Day 2: Testing and refinement
  - Day 3: Documentation and review

- **Phase 2**: 2 days
  - Day 1: Model updates and implementation
  - Day 2: Testing and integration

- **Phase 3**: 3-4 days
  - Day 1-2: Consolidation and refactoring
  - Day 3: Testing and verification
  - Day 4: Documentation and deployment

## Conclusion

This proposal provides a simple, direct path to adding location intelligence to Wikipedia search. By reusing the existing LocationUnderstandingModule and following a phased approach, we minimize risk while delivering immediate value. The solution maintains simplicity, uses existing proven components, and sets up a foundation for future enhancements.