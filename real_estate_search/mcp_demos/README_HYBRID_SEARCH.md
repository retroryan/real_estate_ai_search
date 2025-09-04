# Hybrid Search MCP Tool Demos

This directory contains comprehensive demos for the **Hybrid Search MCP Tool**, showcasing advanced property search capabilities that combine semantic vector search, traditional text search, and intelligent location extraction.

## Overview

The Hybrid Search MCP Tool provides AI models with powerful property search capabilities through a clean MCP interface. It leverages:

- **Semantic Vector Search**: Uses embeddings for understanding property features and descriptions
- **Traditional Text Search**: BM25 relevance scoring for exact term matching
- **RRF Fusion**: Elasticsearch's native Reciprocal Rank Fusion for optimal result ranking
- **DSPy Location Understanding**: Intelligent extraction of location information from natural language
- **Geographic Filtering**: Automatic filtering based on extracted city/state information

## Demo Files

### Demo 1: Basic Hybrid Search (`demo_9_basic_hybrid.py`)
**Purpose**: Demonstrates core hybrid search functionality with RRF fusion

**Features Tested**:
- Semantic understanding of property features
- Hybrid RRF scoring combining vector + text search
- Different query types (family homes, luxury properties, investment properties)
- Performance metrics and response structure validation

**Sample Queries**:
- "modern home with spacious kitchen and garage"
- "luxury condominium with amenities"
- "family-friendly house with backyard and multiple bedrooms"
- "income property duplex or multi-unit rental"

### Demo 2: Location-Aware Search (`demo_11_location_aware.py`)
**Purpose**: Showcases DSPy-powered location extraction and geographic filtering

**Features Tested**:
- DSPy location extraction from natural language queries
- City and state recognition (full names and abbreviations)
- Geographic filtering integration with hybrid search
- Location extraction accuracy validation
- Query cleaning (removing location terms from search)

**Sample Queries**:
- "waterfront condo in San Francisco California"
- "luxury home near downtown Oakland CA"
- "family house in Mission District San Francisco"
- "beachfront property with ocean views in Monterey"
- "investment property in San Jose or nearby Santa Clara California"

### Demo 3: Advanced Scenarios (`demo_12_advanced_scenarios.py`)
**Purpose**: Tests robustness, edge cases, and advanced capabilities

**Features Tested**:
- **Parameter Validation**: Empty queries, size limits, boundary conditions
- **Complex Queries**: Multi-feature searches, technical specifications, architectural styles
- **Edge Cases**: Unicode characters, special symbols, abbreviations, minimal queries
- **Performance Analysis**: Execution time metrics across query complexities
- **Error Handling**: Validation errors and system robustness

**Test Categories**:
- Parameter validation with Pydantic models
- Complex multi-feature property searches
- Edge cases with special characters and unicode
- Performance consistency analysis

## Usage

### Running Individual Demos

```bash
# Using the mcp_demos.sh script
./mcp_demos.sh 9     # Demo 1: Basic Hybrid Search
./mcp_demos.sh 11    # Demo 2: Location-Aware Search  
./mcp_demos.sh 12    # Demo 3: Advanced Scenarios

# Or run directly
python3 real_estate_search/mcp_demos/demo_9_basic_hybrid.py
python3 real_estate_search/mcp_demos/demo_11_location_aware.py
python3 real_estate_search/mcp_demos/demo_12_advanced_scenarios.py
```

### Prerequisites

1. **Elasticsearch running** on localhost:9200
2. **MCP server services initialized** (embedding service, hybrid search engine)
3. **Valid API keys** in environment (Voyage AI, OpenAI, or Gemini)
4. **Property data indexed** in Elasticsearch

### Quick Start

```bash
# Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" elasticsearch:8.11.0

# Set API key (choose one)
export VOYAGE_API_KEY=your-voyage-api-key
# OR export OPENAI_API_KEY=your-openai-key  
# OR export GOOGLE_API_KEY=your-gemini-key

# Run data pipeline (if not done already)
python -m squack_pipeline

# Run a hybrid search demo
./mcp_demos.sh 9
```

## Demo Output

Each demo provides structured output including:

- **Query Information**: Original query, expected behavior, purpose
- **Execution Metrics**: Response time, total hits, returned results
- **Location Extraction**: When enabled, shows DSPy extraction results
- **Property Results**: Formatted property details with hybrid scores
- **Validation Results**: For parameter validation and edge case testing
- **Performance Analysis**: Timing and efficiency metrics

### Sample Output

```
🏠 DEMO 1: Basic Hybrid Search Functionality
════════════════════════════════════════════════════════════════════════════════

📋 Initializing MCP server and services...

🔍 Running 4 basic hybrid search queries...

--- Query 1: Semantic Search ---
Query: "modern home with spacious kitchen and garage"
Purpose: Tests semantic understanding of property features

📊 Results (5 of 234 total):
⏱️  Execution time: 127ms

  1. House - $850,000
     📍 123 Oak Street, San Francisco, CA
     🏡 3 bed, 2 bath, 1,850 sqft
     ⭐ Hybrid Score: 0.924
     🎯 Key Features: Modern Kitchen, Garage, Updated

  2. House - $720,000
     📍 456 Pine Avenue, Oakland, CA
     🏡 4 bed, 3 bath, 2,100 sqft
     ⭐ Hybrid Score: 0.891
     🎯 Key Features: Spacious Kitchen, 2-Car Garage

✅ Query completed successfully
```

## MCP Tool Integration

These demos test the MCP tool that can be called by AI models:

**Tool Name**: `search_properties_hybrid_tool`

**Parameters**:
- `query` (string): Natural language property search query
- `size` (int, 1-50): Number of results to return (default: 10)
- `include_location_extraction` (bool): Include location extraction details (default: false)

**Response Structure**:
```json
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
      "price": 850000,
      "bedrooms": 3,
      "bathrooms": 2,
      "square_feet": 1850,
      "description": "string",
      "features": ["Modern Kitchen", "Garage"],
      "hybrid_score": 0.924
    }
  ],
  "metadata": {
    "query": "modern home with spacious kitchen",
    "total_hits": 234,
    "returned_hits": 5,
    "execution_time_ms": 127,
    "location_extracted": {
      "city": "San Francisco",
      "state": "California",
      "has_location": true,
      "cleaned_query": "modern home with spacious kitchen"
    }
  }
}
```

## Best Practices Demonstrated

1. **Pydantic Validation**: All inputs and outputs use Pydantic models for type safety
2. **Clean Error Handling**: Functions raise exceptions instead of returning error objects
3. **Comprehensive Logging**: Request tracking and performance monitoring
4. **Modular Design**: Clean separation of models, tools, and services
5. **MCP Compliance**: Follows FastMCP patterns and best practices
6. **Type Safety**: Full type annotations without Union types

## Performance Expectations

- **Basic Queries**: 50-200ms response time
- **Complex Queries**: 100-500ms response time  
- **Location Extraction**: Adds ~20-50ms overhead
- **Typical Results**: 10-50 properties per query
- **Memory Usage**: Low, stateless operations

## Troubleshooting

**Common Issues**:

1. **Service Not Available**: Ensure MCP server is initialized with all services
2. **No Results**: Check if property data is indexed in Elasticsearch
3. **Location Extraction Fails**: Verify DSPy is properly initialized
4. **Validation Errors**: Check query length and size parameter limits
5. **Performance Issues**: Monitor Elasticsearch cluster health

**Debug Commands**:
```bash
# Check Elasticsearch
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check property index
curl -X GET "localhost:9200/properties/_count?pretty"

# Test MCP server
python -c "from real_estate_search.mcp_server.main import MCPServer; s = MCPServer(); s._initialize_services()"
```

## Contributing

When adding new demo scenarios:

1. Follow the existing pattern of async functions with clear documentation
2. Use comprehensive error handling and logging
3. Include both successful cases and edge case testing
4. Provide clear output formatting with performance metrics
5. Update this README with new demo descriptions

## Related Files

- `../mcp_server/models/hybrid.py` - Pydantic models for requests/responses
- `../mcp_server/tools/hybrid_search_tool.py` - Core MCP tool implementation
- `../hybrid/` - Hybrid search engine and location understanding modules
- `../../mcp_demos.sh` - Demo runner script (use demos 9-12)