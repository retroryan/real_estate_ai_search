# MCP Server for Real Estate Search - Technical Proposal

* **ALWAYS CHECK FOR BEST PRACTICES AT https://gofastmcp.com/llms.txt**
* **ALWAYS USE PYDANTIC**
* **USE MODULES AND CLEAN CODE!**
* **Never name things after the phases or steps of the proposal and process documents**
* **if hasattr should never be used**
* **Never cast variables or cast variable names or add variable aliases**
* **If it doesn't work don't hack and mock. Fix the core issue**
* **If there are questions please ask!!!**

## Executive Summary

This proposal outlines the development of a Model Context Protocol (MCP) server for the Real Estate Search system, enabling natural language semantic search capabilities across property listings and Wikipedia articles. The server will leverage FastMCP framework to provide a clean, extensible interface for AI models to query and interact with the existing Elasticsearch infrastructure.

## Core Objectives

### Primary Goals
- Enable natural language queries against property listings using semantic search
- Provide semantic search capabilities for Wikipedia articles enriching location context
- Create a high-quality demonstration of MCP integration with Elasticsearch
- Establish a clean, modular architecture that can be extended in the future

### Non-Goals (Out of Scope)
- Full production deployment with all endpoints
- Complete test coverage of every possible query combination
- Authentication and authorization systems
- Real-time data ingestion or updates
- Query caching or performance optimization

## Architecture Overview

### System Components

#### MCP Server Layer
The MCP server acts as an intelligent intermediary between AI models and Elasticsearch, translating natural language queries into optimized search operations. It provides context-aware responses that combine semantic understanding with structured data retrieval.

#### Elasticsearch Integration
The server connects to existing Elasticsearch indices containing property listings and Wikipedia articles, both enriched with 1024-dimensional embeddings using the Voyage-3 model for semantic similarity searches.

#### Data Models
All data structures use Pydantic models to ensure type safety, validation, and clear documentation of the data flowing through the system.

### Key Design Principles

#### Modularity
Each component operates independently with clear interfaces, allowing for easy testing, maintenance, and future extensions.

#### Type Safety
Pydantic models provide runtime validation and clear contracts between components, preventing type-related errors and improving developer experience.

#### Clean Separation of Concerns
Business logic, data access, and protocol handling remain strictly separated to maintain clarity and testability.

## Technical Requirements

### Functional Requirements

#### Semantic Property Search
- Accept natural language queries describing desired property characteristics
- Combine semantic vector search with traditional filters
- Return ranked results with relevance scores
- Include property metadata and enriched location context

#### Semantic Wikipedia Search
- Process natural language queries about locations and topics
- Search across full article content and summaries
- Return relevant article sections with highlights
- Provide location-based context for geographic queries

#### Response Formatting
- Structure responses with clear metadata about search execution
- Include relevance scores and ranking information
- Provide pagination support for large result sets
- Format data for easy consumption by AI models

### Non-Functional Requirements

#### Performance
- Response times under 2 seconds for typical queries
- Support concurrent query processing
- Efficient memory usage for embedding operations

#### Reliability
- Graceful error handling with informative messages
- Connection pooling for Elasticsearch clients
- Retry logic for transient failures

#### Maintainability
- Clear module boundaries and interfaces
- Comprehensive logging for debugging
- Self-documenting code through type hints and docstrings

## System Design

### Module Structure

#### Configuration Module
Manages all configuration settings including Elasticsearch connection parameters, embedding model settings, and search defaults. Uses Pydantic settings for environment variable integration and validation.

#### Models Module
Contains all Pydantic models representing properties, Wikipedia articles, search requests, and search responses. Ensures data consistency throughout the application.

#### Search Service Module
Implements the core search logic, translating natural language queries into Elasticsearch DSL, managing embedding generation, and orchestrating hybrid search strategies.

#### Elasticsearch Client Module
Provides a clean abstraction over the Elasticsearch Python client, handling connection management, query execution, and result parsing.

#### MCP Server Module
Implements the FastMCP server with tool definitions for property and Wikipedia searches, managing the protocol-level interactions.

### Data Flow

#### Query Processing Pipeline
1. Natural language query received via MCP protocol
2. Query parsed and validated using Pydantic models
3. Embedding generated for semantic search
4. Elasticsearch query constructed combining vector and text search
5. Results retrieved and ranked
6. Response formatted and returned via MCP

#### Error Handling Strategy
- Input validation errors return clear messages about requirements
- Elasticsearch connection issues trigger retry with exponential backoff
- Embedding service failures fall back to text-only search
- All errors logged with context for debugging

## Implementation Plan

### Phase 1: Foundation and Infrastructure

#### Objective
Establish the core infrastructure and basic connectivity to existing systems.

#### TODO List:
- [ ] Create directory structure at `real_estate_search/mcp_server/`
- [ ] Set up configuration module with Pydantic settings for Elasticsearch and embedding services
- [ ] Implement Elasticsearch client wrapper with connection pooling
- [ ] Create base Pydantic models for properties and Wikipedia articles
- [ ] Establish logging configuration with structured output
- [ ] Write health check endpoint to verify Elasticsearch connectivity
- [ ] Create development environment setup script
- [ ] Document environment variables and configuration options
- [ ] Implement connection retry logic with exponential backoff
- [ ] Add connection pool management for Elasticsearch
- [ ] Code review and testing
- [ ] Create integration tests in real_estate_search/mcp_integration_tests/ following MCP_TESTING.md guidelines

### Phase 2: Search Service Implementation

#### Objective
Build the core search functionality for both property and Wikipedia queries.

#### TODO List:
- [ ] Implement embedding service integration using Voyage API
- [ ] Create property search query builder with vector and text components
- [ ] Implement Wikipedia search query builder with content field targeting
- [ ] Develop result ranking algorithm combining scores
- [ ] Add search request validation models with field constraints
- [ ] Create search response models with metadata
- [ ] Implement pagination support for large result sets
- [ ] Add query preprocessing for better semantic matching
- [ ] Create search execution pipeline with error handling
- [ ] Implement result post-processing and formatting
- [ ] Code review and testing
- [ ] Create integration tests in real_estate_search/mcp_integration_tests/ following MCP_TESTING.md guidelines

### Phase 3: MCP Server Integration

#### Objective
Integrate the search services with FastMCP to expose them via the Model Context Protocol.

#### TODO List:
- [ ] Set up FastMCP server with basic configuration
- [ ] Implement property search tool with natural language interface
- [ ] Implement Wikipedia search tool with content-aware responses
- [ ] Create tool descriptions and parameter schemas
- [ ] Add context management for conversation state
- [ ] Implement streaming responses for large result sets
- [ ] Create error response formatting for MCP protocol
- [ ] Add request logging and monitoring
- [ ] Implement graceful shutdown handling
- [ ] Create server startup and initialization logic
- [ ] Code review and testing
- [ ] Create integration tests in real_estate_search/mcp_integration_tests/ following MCP_TESTING.md guidelines

### Phase 4: Enhanced Search Capabilities

#### Objective
Add advanced search features to improve result quality and relevance.

#### TODO List:
- [ ] Implement hybrid search combining vector and BM25 scoring
- [ ] Add filter support for property attributes (price, bedrooms, location)
- [ ] Create geographic search capabilities using geo_point fields
- [ ] Implement query expansion for better semantic coverage
- [ ] Add support for multi-field boosting in searches
- [ ] Create relevance tuning configuration
- [ ] Implement search result explanation for debugging
- [ ] Add support for aggregations in property searches
- [ ] Create search templates for common query patterns
- [ ] Optimize embedding batch processing
- [ ] Code review and testing
- [ ] Create integration tests in real_estate_search/mcp_integration_tests/ following MCP_TESTING.md guidelines

### Phase 5: Demo and Documentation

#### Objective
Create a compelling demonstration and comprehensive documentation.

#### TODO List:
- [ ] Create demo script showcasing property search capabilities
- [ ] Develop Wikipedia search demonstration scenarios
- [ ] Write integration guide for AI models
- [ ] Document API endpoints and parameters
- [ ] Create example queries and expected responses
- [ ] Write troubleshooting guide for common issues
- [ ] Develop performance benchmarking suite
- [ ] Create visualization of search results for demo
- [ ] Write deployment instructions for local testing
- [ ] Record demo video showing capabilities
- [ ] Code review and testing
- [ ] Create integration tests in real_estate_search/mcp_integration_tests/ following MCP_TESTING.md guidelines

## Testing Strategy

### Unit Testing
Each module will have comprehensive unit tests covering:
- Pydantic model validation and serialization
- Search query construction logic
- Result parsing and formatting
- Error handling paths

### Integration Testing
End-to-end tests validating:
- MCP protocol communication
- Elasticsearch query execution
- Embedding service integration
- Complete query processing pipeline

All integration tests will be located in `real_estate_search/mcp_integration_tests/` and follow the guidelines defined in MCP_TESTING.md. Each phase will include dedicated integration tests to validate the functionality implemented in that phase before proceeding to the next.

### Demo Validation
Manual testing scenarios including:
- Natural language property searches
- Location-based Wikipedia queries
- Error condition handling
- Performance under concurrent load

## Success Metrics

### Functional Success
- Accurate semantic search results for property queries
- Relevant Wikipedia article retrieval
- Consistent response times under 2 seconds
- Zero runtime type errors due to Pydantic validation

### Quality Metrics
- Clean module separation with no circular dependencies
- All functions with type hints and docstrings
- No use of hasattr or variable casting
- Error messages that clearly indicate root causes

### Demo Effectiveness
- Compelling demonstrations of semantic search capabilities
- Clear advantage over traditional keyword search
- Smooth integration with AI model interactions
- Positive user feedback on search relevance

## Risk Mitigation

### Technical Risks

#### Embedding Service Availability
- **Risk**: Voyage API may be unavailable or rate-limited
- **Mitigation**: Implement caching of embeddings and fallback to text search

#### Elasticsearch Performance
- **Risk**: Complex vector searches may be slow
- **Mitigation**: Optimize query structure and implement pagination

#### Data Consistency
- **Risk**: Mismatch between embedding dimensions or models
- **Mitigation**: Validate embedding compatibility on startup

### Implementation Risks

#### Scope Creep
- **Risk**: Adding features beyond demo requirements
- **Mitigation**: Strict adherence to defined phases and objectives

#### Integration Complexity
- **Risk**: FastMCP integration may have unexpected challenges
- **Mitigation**: Early prototype of MCP connectivity in Phase 1

## Future Enhancements

While out of scope for this demo implementation, the following enhancements could be considered for future development:

### Advanced Search Features
- Query understanding with intent classification
- Multi-modal search combining text and images
- Personalized search based on user preferences
- Real-time collaborative filtering

### Production Readiness
- Authentication and authorization
- Rate limiting and quota management
- Distributed caching layer
- Monitoring and alerting
- A/B testing framework

### Extended Data Sources
- Integration with additional property databases
- Social media sentiment analysis
- Market trend predictions
- School and crime data integration

## Conclusion

This MCP server implementation will provide a powerful demonstration of semantic search capabilities for real estate data, establishing a clean, extensible foundation for future enhancements. By focusing on core functionality with high-quality implementation, the project will showcase the potential of combining MCP protocols with advanced search technologies.

The modular architecture, strict type safety through Pydantic, and clean code principles ensure that the codebase remains maintainable and extensible. The phased implementation approach allows for iterative development with clear milestones and validation points.

Success will be measured not just by functional completeness, but by the quality of the implementation and the compelling nature of the demonstration. The project will serve as a reference implementation for MCP-based search systems and provide immediate value for natural language property and location searches.