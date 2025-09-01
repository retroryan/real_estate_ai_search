# Hybrid Search MCP Tool Proposal

## Complete Cut-Over Requirements

**CRITICAL: These requirements must be followed exactly without exception:**

* **FOLLOW THE REQUIREMENTS EXACTLY!!!** Do not add new features or functionality beyond the specific requirements requested and documented
* **ALWAYS FIX THE CORE ISSUE!** Address root causes, not symptoms
* **COMPLETE CHANGE:** All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION:** Simple, direct replacements only
* **NO MIGRATION PHASES:** Do not create temporary compatibility periods
* **NO PARTIAL UPDATES:** Change everything or change nothing
* **NO COMPATIBILITY LAYERS:** Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE:** Do not comment out old code "just in case"
* **NO CODE DUPLICATION:** Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS:** Direct replacements only, no abstraction layers
* **DO NOT CALL FUNCTIONS ENHANCED or IMPROVED** and change the actual methods. For example if there is a class PropertyIndex and we want to improve that do not create a separate ImprovedPropertyIndex and instead just update the actual PropertyIndex
* **ALWAYS USE PYDANTIC** for all data models and validation
* **USE MODULES AND CLEAN CODE!** Proper separation of concerns
* **Never name things after the phases or steps** of the proposal and process documents. So never test_phase_2_bronze_layer.py etc.
* **if hasattr should never be used.** And never use isinstance
* **Never cast variables** or cast variable names or add variable aliases
* **If you are using a union type something is wrong.** Go back and evaluate the core issue of why you need a union
* **If it doesn't work don't hack and mock.** Fix the core issue
* **If there are questions please ask me!!!**
* **Do not generate mocks or sample data** if the actual results are missing. Find out why the data is missing and if still not found ask

---

## Executive Summary

This proposal outlines the addition of a new MCP (Model Context Protocol) tool to expose the recently refactored hybrid search functionality through the existing MCP server infrastructure. The tool will provide a clean, simple interface for AI models to perform location-aware hybrid property searches combining semantic vector search, traditional text search, and geographic filtering using Elasticsearch's native RRF (Reciprocal Rank Fusion).

## Background and Context

The real estate search system recently underwent a complete refactoring that created a clean hybrid search module at `real_estate_search/hybrid/`. This module provides:

- **Hybrid Search Engine**: Combines vector and text search with RRF
- **Location Understanding**: DSPy-based location extraction from natural language
- **Geographic Filtering**: Elasticsearch filters based on extracted location intent
- **Structured Results**: Pydantic models for type safety and validation

Currently, this powerful search functionality is only accessible through internal demo scripts. To maximize its utility, we need to expose it through the MCP server so AI models can leverage these capabilities directly.

## Problem Statement

**Core Issue**: The advanced hybrid search capabilities are not accessible to AI models through the MCP interface, limiting their practical utility for real-world applications.

**Specific Problems**:
1. No MCP tool exists for hybrid property search
2. Location-aware search capabilities are not exposed
3. AI models cannot leverage the semantic + text + geographic search fusion
4. The investment in the hybrid search refactoring is not fully utilized

## Requirements

### Functional Requirements

**Primary Functionality**:
- Accept natural language property search queries through MCP interface
- Automatically extract location information from queries using existing DSPy module
- Perform hybrid search combining semantic vectors, text matching, and location filtering
- Return structured property results with relevance scores
- Support configurable result limits (default 10, maximum 50)

**Query Processing**:
- Process natural language queries like "luxury waterfront condo in San Francisco"
- Automatically identify location components (city, state, neighborhood, ZIP)
- Clean query text for optimal property feature matching
- Apply appropriate geographic filters when location is detected

**Result Format**:
- Return structured property data including address, price, features, description
- Include hybrid relevance scores for result ranking
- Provide execution metadata (timing, hit counts, location extraction results)
- Format results in MCP-compliant JSON structure

**Error Handling**:
- Graceful handling of malformed queries
- Proper error responses for Elasticsearch connectivity issues
- Fallback behavior when location extraction fails
- Clear error messages for debugging

### Non-Functional Requirements

**Simplicity**:
- Single MCP tool with straightforward interface
- No complex configuration options or multiple search modes
- Clean parameter validation using Pydantic models
- Minimal cognitive overhead for AI model usage

**Reliability**:
- Robust error handling without system crashes
- Proper logging for debugging and monitoring
- Consistent response format regardless of query complexity
- Graceful degradation when services are unavailable

**Integration**:
- Seamless integration with existing MCP server infrastructure
- Use existing hybrid search module without modification
- Leverage existing Elasticsearch and embedding service connections
- Maintain compatibility with current MCP tool patterns

### Excluded Requirements

**Explicitly NOT Included**:
- Performance optimization or benchmarking features
- Multiple search algorithms or modes
- Complex result post-processing or ranking adjustments
- Advanced configuration options or tuning parameters
- Batch search capabilities or bulk operations
- Search analytics or usage tracking
- Custom embedding model selection
- Search result caching mechanisms

## Technical Approach

### Architecture Overview

The new MCP tool will follow the established pattern of existing MCP tools in the system:

**Tool Structure**:
- Single MCP tool class inheriting from base MCP tool interface
- Pydantic models for request/response validation
- Direct integration with `real_estate_search.hybrid` module
- Standard MCP error handling and logging patterns

**Data Flow**:
1. AI model sends natural language query via MCP
2. Tool validates input parameters using Pydantic
3. HybridSearchEngine processes query with location extraction
4. Elasticsearch returns ranked results via RRF
5. Tool formats results into MCP response structure
6. AI model receives structured property data

**Integration Points**:
- MCP Server: Register new tool with existing server instance
- Hybrid Module: Use HybridSearchEngine and LocationUnderstandingModule
- Configuration: Leverage existing Elasticsearch and embedding configurations
- Logging: Use established logging patterns for consistency

### Input Parameters

**Required Parameters**:
- `query`: Natural language property search query (string, max 500 characters)

**Optional Parameters**:
- `size`: Number of results to return (integer, default 10, range 1-50)
- `include_location_extraction`: Whether to include location extraction details in response (boolean, default false)

**Parameter Validation**:
- Query string cannot be empty or only whitespace
- Size parameter must be within allowed range
- All parameters validated via Pydantic models before processing

### Output Structure

**Response Format**:
```
{
  "results": [
    {
      "listing_id": "string",
      "property_type": "string", 
      "address": {
        "street": "string",
        "city": "string",
        "state": "string",
        "zip_code": "string"
      },
      "price": number,
      "bedrooms": number,
      "bathrooms": number,
      "square_feet": number,
      "description": "string",
      "features": ["string"],
      "hybrid_score": number
    }
  ],
  "metadata": {
    "query": "string",
    "total_hits": number,
    "returned_hits": number,
    "execution_time_ms": number,
    "location_extracted": {
      "city": "string",
      "state": "string", 
      "has_location": boolean,
      "cleaned_query": "string"
    }
  }
}
```

**Metadata Inclusion**:
- Always include basic execution metadata (timing, hit counts)
- Conditionally include location extraction details based on parameter
- Preserve original query for reference and debugging
- Include hybrid search specific information (RRF usage, etc.)

## Implementation Plan

### Phase 1: Core MCP Tool Foundation

**Objective**: Establish the basic MCP tool structure and integration framework

**Deliverables**:
- Create base MCP tool class with proper inheritance
- Define Pydantic models for request and response validation
- Implement basic parameter validation and error handling
- Set up proper logging integration with existing patterns

**Todo List**:
1. Create `real_estate_search/mcp_server/tools/hybrid_search_tool.py`
2. Define `HybridSearchRequest` Pydantic model with query and size parameters
3. Define `HybridSearchResponse` Pydantic model matching output structure
4. Implement `HybridSearchTool` class inheriting from base MCP tool
5. Add parameter validation with appropriate error messages
6. Set up logging using established patterns from existing tools
7. Create basic tool registration structure for MCP server integration

### Phase 2: Hybrid Search Engine Integration

**Objective**: Connect the MCP tool to the hybrid search functionality

**Deliverables**:
- Integration with HybridSearchEngine from hybrid module
- Location extraction processing using LocationUnderstandingModule
- Query parameter mapping to HybridSearchParams
- Basic search execution with error handling

**Todo List**:
1. Import and initialize HybridSearchEngine within tool class
2. Map MCP request parameters to HybridSearchParams model
3. Implement query execution using search_with_location method
4. Add error handling for Elasticsearch connectivity issues
5. Add error handling for embedding service failures
6. Handle location extraction failures gracefully
7. Implement timeout handling for long-running searches
8. Add logging for search execution steps and timing

### Phase 3: Response Processing and Formatting

**Objective**: Transform hybrid search results into proper MCP response format

**Deliverables**:
- Result transformation from HybridSearchResult to MCP format
- Metadata extraction and formatting
- Error response standardization
- Location extraction details processing

**Todo List**:
1. Implement result transformation from SearchResult objects to response format
2. Extract and format property data fields (address, price, features, etc.)
3. Include hybrid scores and relevance information
4. Build metadata section with execution timing and hit counts
5. Format location extraction results based on include_location_extraction parameter
6. Implement proper error response formatting for various failure modes
7. Add result validation to ensure response matches expected schema
8. Handle edge cases like empty results or malformed property data

### Phase 4: MCP Server Registration and Integration

**Objective**: Register the tool with the MCP server and ensure proper operation

**Deliverables**:
- Tool registration with MCP server
- Integration testing with existing server infrastructure
- Configuration validation and setup
- Documentation for tool usage

**Todo List**:
1. Register HybridSearchTool with existing MCP server instance
2. Update MCP server tool discovery to include hybrid search tool
3. Verify tool appears in MCP server tool listings
4. Test tool invocation through MCP protocol
5. Validate configuration loading and dependency resolution
6. Add tool metadata and description for MCP clients
7. Create usage examples and basic documentation
8. Verify integration with existing logging and monitoring systems

### Phase 5: Testing and Validation

**Objective**: Comprehensive testing of the new MCP tool functionality

**Deliverables**:
- Unit tests for tool functionality
- Integration tests with live data
- Error handling validation
- Performance baseline establishment

**Todo List**:
1. Create unit tests for parameter validation and error handling
2. Create integration tests with real Elasticsearch data
3. Test various query types (location-aware, generic, edge cases)
4. Validate response format compliance with schema
5. Test error scenarios (network failures, invalid queries, etc.)
6. Verify logging output and error reporting
7. Test with different result sizes and parameter combinations
8. Validate location extraction accuracy with test queries
9. Perform end-to-end testing through MCP protocol
10. **Code review and final testing validation**

## Success Criteria

**Functional Success**:
- MCP tool successfully processes natural language property queries
- Location extraction works correctly for queries containing geographic references
- Hybrid search returns relevant, ranked property results
- Tool integrates seamlessly with existing MCP server infrastructure
- Error handling provides clear, actionable feedback

**Quality Success**:
- Code follows established patterns and conventions from existing MCP tools
- All functionality covered by appropriate tests
- Response format is consistent and well-structured
- Tool performs reliably under normal usage conditions
- Integration does not impact existing MCP server functionality

**Simplicity Success**:
- Tool has minimal configuration requirements
- Interface is intuitive for AI model consumption
- Implementation follows clean code principles
- No unnecessary complexity or over-engineering
- Documentation is clear and concise

## Risk Assessment

**Low Risks**:
- Integration complexity (existing patterns provide clear guidance)
- Parameter validation (standard Pydantic approach)
- Error handling (established MCP patterns available)

**Medium Risks**:
- Elasticsearch connectivity issues during searches
- Embedding service availability impacting vector search
- Large result sets causing response formatting issues

**Mitigation Strategies**:
- Robust error handling with fallback responses
- Appropriate timeouts and circuit breaker patterns
- Result size limits to prevent oversized responses
- Comprehensive testing with various failure scenarios

## Conclusion

This proposal provides a clear, simple path to expose the powerful hybrid search capabilities through the MCP interface. By following the established patterns and leveraging the recently refactored hybrid search module, we can deliver a high-quality demo tool that showcases the full potential of the location-aware, semantic property search capabilities.

The implementation plan ensures a systematic approach with proper validation at each phase, culminating in comprehensive testing and code review. The focus on simplicity and clean implementation aligns with the project's quality standards while avoiding unnecessary complexity or over-engineering.