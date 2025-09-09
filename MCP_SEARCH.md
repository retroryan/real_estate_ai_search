# MCP Property Search Enhancement Proposal

## Executive Summary

This proposal outlines the implementation of a dual-approach property search system within the MCP server that provides two distinct search methods:

1. **Structured Filter Search** - Explicit parameter-based searching with precise filters for price, bedrooms, location, etc.
2. **Natural Language Search** - AI-powered semantic understanding that leverages the existing LocationExtractionSignature and HybridSearchEngine

## Current State Analysis

### Existing Infrastructure

The system currently has powerful search capabilities that are not fully exposed:

1. **search_properties_with_filters** - A tool that accepts both a query string and explicit filter parameters (price, bedrooms, city, state, etc.)

2. **HybridSearchEngine** - Advanced search with:
   - Vector embeddings for semantic understanding
   - BM25 text scoring
   - RRF (Reciprocal Rank Fusion) for result merging
   - `search_with_location()` method that extracts locations from natural language

3. **LocationExtractionSignature (DSPy)** - Sophisticated location extraction that:
   - Identifies cities, states, neighborhoods, and ZIP codes
   - Removes location terms from queries
   - Returns cleaned queries with confidence scores
   - Already integrated in `LocationUnderstandingModule`

4. **QueryEmbeddingService** - Generates vector embeddings for natural language queries using Voyage AI

### Gap Analysis

The current implementation has a simple missing component:
- The **hybrid_search_tool** module is referenced but not implemented
- The powerful `HybridSearchEngine.search_with_location()` is not exposed via MCP
- All the infrastructure exists, it just needs to be connected

## Proposed Solution

### Simplified Implementation Using Existing Infrastructure

The solution is straightforward: expose the existing `HybridSearchEngine.search_with_location()` method through the MCP interface. This leverages all the sophisticated infrastructure already built.

### Two Distinct Search Tools

#### 1. Structured Filter Search Tool (Existing)

**Purpose**: For users who know exactly what they want and can specify precise criteria

**Implementation**: Already exists as `search_properties_with_filters`

**Use Cases**:
- "Show me all 3-bedroom houses in San Francisco under $1M"
- "Find condos with 2 bathrooms between $500K-$700K"
- "List properties in Austin, TX with at least 2000 sq ft"

#### 2. Natural Language Search Tool (New)

**Purpose**: For users who describe their needs in conversational language

**Implementation**: Simply expose `HybridSearchEngine.search_with_location()`

**What It Already Does**:
- Uses LocationExtractionSignature (DSPy) to extract cities, states, neighborhoods, ZIP codes
- Automatically removes location terms from the query
- Generates embeddings for the cleaned query
- Applies location filters during search (not post-filtering)
- Combines text and vector search with RRF

**Use Cases**:
- "Modern kitchen in San Francisco" → Extracts "San Francisco", searches for "Modern kitchen"
- "Family home in Salinas California" → Extracts "Salinas, California", searches for "Family home"
- "Condo near downtown Oakland with parking" → Extracts "Oakland", searches for "Condo near downtown with parking"

## Technical Implementation

### The Missing Piece: hybrid_search_tool.py

Create a simple module that connects the existing HybridSearchEngine to the MCP interface:

**Key Components Already Available**:
1. **LocationExtractionSignature** - DSPy-powered location extraction
2. **HybridSearchEngine.search_with_location()** - Complete implementation
3. **QueryEmbeddingService** - Vector generation for semantic search
4. **RRF Query Builder** - Efficient filtered search with proper optimization

**What Needs to Be Done**:
1. Create `mcp_server/tools/hybrid_search_tool.py`
2. Import HybridSearchEngine from existing code
3. Create async wrapper for `search_with_location()`
4. Return results in MCP format

### How Location Extraction Works

The existing LocationExtractionSignature uses DSPy to:
1. Identify location components in natural language
2. Clean the query by removing location terms
3. Return structured location data with confidence scores

Example transformations:
- Input: "Modern kitchen in San Francisco"
  - Output: city="San Francisco", cleaned_query="Modern kitchen"
- Input: "Family home near good schools in Palo Alto"
  - Output: city="Palo Alto", cleaned_query="Family home near good schools"

## Benefits of Dual Approach

### For End Users

1. **Flexibility** - Choose the search method that matches their needs
2. **Precision** - Get exact matches when criteria are specific
3. **Discovery** - Find unexpected matches through natural language
4. **Efficiency** - Quick results for both search types

### For Developers

1. **Clear API Separation** - Distinct tools with specific purposes
2. **Predictable Behavior** - Structured search gives consistent results
3. **Enhanced Capabilities** - Natural language adds AI intelligence
4. **Backward Compatibility** - Existing integrations continue working

### For the System

1. **Optimized Performance** - Each path optimized for its use case
2. **Reduced Complexity** - Separation of concerns
3. **Better Monitoring** - Track usage patterns per search type
4. **Improved Testing** - Test each component independently

## Implementation Status

**Phases 1-3 COMPLETED** ✅

The natural language property search is now fully implemented and integrated into the MCP server. The implementation:

1. **Created hybrid_search_tool.py** - Connects HybridSearchEngine to MCP interface
2. **Tool Registration** - Already configured in tool_registry.py
3. **Response Format** - Properly transforms HybridSearchResult to PropertySearchResponse

The system now supports two distinct search approaches:
- **Structured Filter Search**: `search_properties_with_filters` for explicit parameters
- **Natural Language Search**: `search_properties` using DSPy location extraction and hybrid search

## Implementation Plan

### Phase 1: Create Missing Module ✅ COMPLETED

**Objective**: Create the hybrid_search_tool.py module to expose existing functionality

**Tasks**:
- [x] Create `mcp_server/tools/hybrid_search_tool.py` file
- [x] Import HybridSearchEngine from `real_estate_search.hybrid`
- [x] Create async wrapper function `search_properties_hybrid`
- [x] Handle context and service initialization
- [x] Transform HybridSearchResult to MCP response format
- [x] Add error handling with proper MCP error responses
- [x] Code review and testing

### Phase 2: Update Tool Registry ✅ COMPLETED

**Objective**: Register the new natural language search tool in MCP

**Tasks**:
- [x] Import hybrid_search_tool in tool_registry.py (already present)
- [x] Add registration for `search_properties` tool (natural language) (already configured)
- [x] Set appropriate tool description and tags (already set)
- [x] Configure tool parameters (query, size, include_location_extraction) (already configured)
- [x] Update existing references to hybrid_search_tool (already correct)
- [x] Test tool registration (verified import works)
- [x] Code review and testing

### Phase 3: Response Format Alignment ✅ COMPLETED

**Objective**: Ensure consistent response format between both search types

**Tasks**:
- [x] Map HybridSearchResult to PropertySearchResponse format (implemented in hybrid_search_tool.py)
- [x] Include location extraction details in response metadata (added as optional field)
- [x] Add confidence scores for location extraction (included in location_extraction response)
- [x] Ensure error responses match existing patterns (using SearchError model)
- [x] Validate response schemas (using Pydantic models)
- [x] Code review and testing

### Phase 4: Integration Testing

**Objective**: Verify both search tools work correctly

**Tasks**:
- [ ] Test natural language queries with location extraction
- [ ] Test queries without location information
- [ ] Test structured filter search remains unchanged
- [ ] Verify both tools can be called independently
- [ ] Test error scenarios and edge cases
- [ ] Performance testing for location extraction
- [ ] Code review and testing

### Phase 5: Documentation

**Objective**: Document the dual search approach

**Tasks**:
- [ ] Update MCP tool descriptions
- [ ] Create usage examples for both tools
- [ ] Document when to use each search type
- [ ] Add location extraction examples
- [ ] Update API documentation
- [ ] Code review and testing

## Success Metrics

1. **Search Accuracy**
   - Structured search: 100% precision for exact matches
   - Natural language: >85% relevance for top 5 results

2. **Performance**
   - Structured search: <100ms response time
   - Natural language: <500ms response time

3. **User Adoption**
   - 30% of searches using natural language within 3 months
   - Reduced support tickets for search-related issues

4. **Developer Experience**
   - Clear documentation with >90% satisfaction
   - Easy integration with existing systems

## Risk Mitigation

1. **Performance Degradation**
   - Solution: Implement caching for embeddings
   - Solution: Use async processing where possible

2. **Natural Language Ambiguity**
   - Solution: Provide clarification prompts
   - Solution: Show interpreted filters to users

3. **Integration Complexity**
   - Solution: Maintain backward compatibility
   - Solution: Provide migration tools

4. **Resource Requirements**
   - Solution: Optimize embedding generation
   - Solution: Implement rate limiting

## Key Insight

The system already has all the sophisticated components needed for natural language property search:
- DSPy-powered location extraction (LocationExtractionSignature)
- Hybrid search with RRF (HybridSearchEngine)
- Efficient filtered vector search
- Modular architecture with proper separation of concerns

The only missing piece is a simple connector module (`hybrid_search_tool.py`) to expose this functionality through the MCP interface. This is not a complex AI implementation project - it's a straightforward integration task that leverages existing, well-tested infrastructure.

## Conclusion

The dual search approach provides clear value with minimal implementation effort. By simply exposing the existing `HybridSearchEngine.search_with_location()` method, we enable natural language property searches that automatically:
1. Extract location information using DSPy
2. Clean queries for better semantic matching
3. Apply filters efficiently during search (not post-filtering)
4. Combine text and vector search with RRF

This enhancement requires no changes to the core search infrastructure, maintains backward compatibility, and can be implemented in a single focused development effort.