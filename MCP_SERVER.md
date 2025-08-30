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

## Implementation Status

### Overview
**Phases 1-4 have been successfully completed** as of the implementation date. The MCP server is fully functional with enhanced semantic search capabilities, comprehensive filtering, aggregations, and performance optimizations for both property listings and Wikipedia articles.

### What's Implemented
- **Complete MCP server** using FastMCP framework
- **Dual search endpoints** for properties and Wikipedia content  
- **Multi-provider embedding support** (Voyage, OpenAI, Gemini, Ollama)
- **Hybrid search capabilities** combining semantic vectors with BM25 full-text search
- **Comprehensive filtering** for properties (price, location, features, bedrooms, status, etc.)
- **Geographic search** with distance-based filtering using geo_distance queries
- **Advanced aggregations** for property analytics (price ranges, property types, averages)
- **Multi-field boosting** with configurable field weights for relevance tuning
- **Search explanations** for debugging and optimization
- **Sorting options** by price, date, or relevance
- **Location-aware Wikipedia search** with geographic filtering
- **Health monitoring** with service status checks
- **Full test coverage** with 62 integration tests across all phases

### Available MCP Tools
1. **search_properties_tool** - Natural language property search with filters
2. **get_property_details_tool** - Detailed property information retrieval
3. **search_wikipedia_tool** - Semantic Wikipedia content search
4. **search_wikipedia_by_location_tool** - Location-specific Wikipedia search
5. **health_check_tool** - System health and status monitoring

### Architecture Highlights
- **Modular design** with clean separation of concerns
- **Type-safe** with Pydantic models throughout
- **Robust error handling** with retry logic and graceful degradation
- **Configurable** via YAML files and environment variables
- **Production-ready** logging and monitoring

### Quick Start
```bash
cd real_estate_search/mcp_server
pip install -r requirements.txt
python main.py config/config.yaml
```

## Implementation Plan

### Phase 1: Foundation and Infrastructure ✅ COMPLETED

#### Objective
Establish the core infrastructure and basic connectivity to existing systems.

#### Status: ✅ All tasks completed successfully

#### Implemented Components:
- ✅ Directory structure at `real_estate_search/mcp_server/` with proper module organization
- ✅ Configuration module with Pydantic settings (MCPServerConfig, ElasticsearchConfig, EmbeddingConfig)
- ✅ Elasticsearch client wrapper with connection pooling and tenacity retry logic
- ✅ Base Pydantic models: Property, Address, Wikipedia, PropertyFilter, SearchRequest/Response
- ✅ Logging configuration with structured JSON support and request tracing
- ✅ Health check service to verify Elasticsearch connectivity and embedding service
- ✅ Development environment setup with requirements.txt and config.yaml
- ✅ Connection retry logic with exponential backoff using tenacity
- ✅ Connection pool management for Elasticsearch with proper resource cleanup
- ✅ Integration tests covering all foundation components

### Phase 2: Search Service Implementation ✅ COMPLETED

#### Objective
Build the core search functionality for both property and Wikipedia queries.

#### Status: ✅ All tasks completed successfully

#### Implemented Components:
- ✅ Embedding service with multi-provider support (Voyage, OpenAI, Gemini, Ollama)
- ✅ Property search service with hybrid text/vector search capabilities
- ✅ Wikipedia search service supporting full articles, summaries, and chunks
- ✅ Advanced query builders combining semantic similarity and traditional filters
- ✅ Search request validation with comprehensive Pydantic models
- ✅ Search response models with metadata, highlights, and score explanations
- ✅ Pagination support for large result sets
- ✅ Query preprocessing and result post-processing pipelines
- ✅ Search execution pipeline with robust error handling
- ✅ Geographic filtering and location-based search capabilities
- ✅ Integration tests covering all search functionality

### Phase 3: MCP Server Integration ✅ COMPLETED

#### Objective
Integrate the search services with FastMCP to expose them via the Model Context Protocol.

#### Status: ✅ All tasks completed successfully

#### Implemented Components:
- ✅ FastMCP server with proper tool registration and context management
- ✅ Property search tool with natural language interface and structured parameters
- ✅ Wikipedia search tools for both general and location-based queries
- ✅ Tool descriptions with comprehensive parameter schemas and documentation
- ✅ Context management system for sharing services between tools
- ✅ Error response formatting following MCP protocol standards
- ✅ Request logging and monitoring with unique request IDs
- ✅ Graceful shutdown handling and resource cleanup
- ✅ Server startup and initialization with health checks
- ✅ Integration tests covering all MCP functionality and tool interactions

### Phase 4: Enhanced Search Capabilities ✅ COMPLETED

#### Objective
Add advanced search features to improve result quality and relevance.

#### Status: ✅ All tasks completed successfully

#### Implemented Components:
- ✅ Hybrid search combining vector and BM25 scoring with configurable weights
- ✅ Comprehensive filter support for all property attributes (price, bedrooms, location, etc.)
- ✅ Geographic search capabilities using geo_distance queries
- ✅ Multi-field boosting in text searches with configurable field weights
- ✅ Relevance tuning via text_weight and vector_weight configuration
- ✅ Search result explanation with optional explain parameter
- ✅ Full aggregation support for property analytics (price ranges, property types, etc.)
- ✅ Optimized embedding batch processing in embedding service
- ✅ Fuzzy matching support with configurable enable_fuzzy parameter
- ✅ Sorting capabilities by price, date, or relevance
- ✅ Comprehensive integration tests covering all enhanced features (24 tests passing)

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