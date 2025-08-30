# Real Estate Search MCP Server

A Model Context Protocol (MCP) server providing semantic search capabilities for real estate properties and Wikipedia content using FastMCP framework.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Elasticsearch running on localhost:9200 with indexed property and Wikipedia data
- API key for embedding provider (Voyage, OpenAI, or Gemini)

### 1. Install Dependencies
```bash
# From project root
pip install -r real_estate_search/mcp_server/requirements.txt

# Or from mcp_server directory
cd real_estate_search/mcp_server
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create a `.env` file in the project root (real_estate_ai_search directory):
```bash
# From real_estate_ai_search directory (project root)
cat > .env << EOF
# Embedding provider API key (choose one)
VOYAGE_API_KEY=your-voyage-api-key-here
# OPENAI_API_KEY=your-openai-key-here  
# GOOGLE_API_KEY=your-gemini-key-here

# Optional Elasticsearch credentials
# ES_USERNAME=elastic
# ES_PASSWORD=your-password
EOF
```

### 3. Start the MCP Server

From the project root directory:
```bash
# Option 1: Using Python module
python -m real_estate_search.mcp_server.main

# Option 2: Using shell script (includes environment checks)
./start_mcp_server.sh

# Option 3: Direct execution from mcp_server directory
cd real_estate_search/mcp_server
python main.py
```

The server will start and register these MCP tools:
- `search_properties_tool` - Natural language property search
- `get_property_details_tool` - Get detailed property information
- `search_wikipedia_tool` - Semantic Wikipedia content search
- `search_wikipedia_by_location_tool` - Location-specific Wikipedia queries
- `health_check_tool` - System health monitoring

### 4. Test the Server
```bash
# Run comprehensive health check (from project root - real_estate_ai_search directory)
./real_estate_search/mcp_health.sh
```

This will check:
- Python environment and required packages  
- Configuration files and API keys (loads .env from project root)
- Elasticsearch connectivity and indices with detailed troubleshooting
- MCP server initialization and health check
- Available tools and services

**Important:** The health check script must be run from the `real_estate_ai_search` directory (project root). It will validate the directory and exit with an error if run from the wrong location.

## 🧪 Running Tests

### Integration Tests
```bash
# Run all MCP integration tests (from project root - real_estate_ai_search directory)
python -m pytest real_estate_search/mcp_integration_tests/ -v

# Run specific test modules (from project root)
python -m pytest real_estate_search/mcp_integration_tests/test_foundation.py -v
python -m pytest real_estate_search/mcp_integration_tests/test_search_services.py -v
python -m pytest real_estate_search/mcp_integration_tests/test_mcp_server.py -v
python -m pytest real_estate_search/mcp_integration_tests/test_enhanced_search.py -v
python -m pytest real_estate_search/mcp_integration_tests/test_tool_discovery.py -v
```

### Test Coverage
- **Foundation Tests** (13 tests) - Configuration, models, Elasticsearch client, health checks
- **Search Services Tests** (14 tests) - Embedding service, property/Wikipedia search  
- **MCP Server Tests** (11 tests) - Server initialization, tools, integration scenarios
- **Enhanced Search Tests** (24 tests) - Hybrid search, aggregations, filtering, sorting
- **Tool Discovery Tests** (7 tests) - MCP tool discovery, metadata validation, LLM routing

### Expected Output
```
================================ test session starts =================================
real_estate_search/mcp_integration_tests/test_foundation.py::TestConfiguration::test_config_from_env PASSED
real_estate_search/mcp_integration_tests/test_search_services.py::TestEmbeddingService::test_embedding_service_initialization PASSED
real_estate_search/mcp_integration_tests/test_mcp_server.py::TestMCPServer::test_server_initialization_from_env PASSED
...
============================== 61 passed in 1.2s ===============================
```

## 🔧 Configuration

### Basic Configuration (config/config.yaml)
```yaml
# Server settings
server_name: real-estate-search-mcp
server_version: 0.1.0
debug: false

# Elasticsearch
elasticsearch:
  host: localhost
  port: 9200
  property_index: properties
  
# Embedding provider
embedding:
  provider: voyage  # voyage, openai, gemini, ollama
  model_name: voyage-3
  dimension: 1024
```

### Environment Variables
```bash
# Embedding providers (choose one)
VOYAGE_API_KEY=your-key
OPENAI_API_KEY=your-key  
GOOGLE_API_KEY=your-key

# Elasticsearch (optional)
ES_USERNAME=elastic
ES_PASSWORD=password
ELASTICSEARCH_API_KEY=your-api-key
ELASTICSEARCH_CLOUD_ID=your-cloud-id
```

---

## 🔬 Advanced Usage

### Custom Configuration

#### Using Different Embedding Providers
```yaml
# OpenAI embeddings
embedding:
  provider: openai
  model_name: text-embedding-3-small
  dimension: 1536
  batch_size: 100

# Gemini embeddings  
embedding:
  provider: gemini
  model_name: models/embedding-001
  dimension: 768
  batch_size: 10

# Local Ollama
embedding:
  provider: ollama
  model_name: nomic-embed-text
  dimension: 768
```

#### Elasticsearch Configuration
```yaml
elasticsearch:
  host: your-es-cluster.com
  port: 9200
  username: elastic
  password: your-password
  # OR use API key
  api_key: your-api-key
  # OR use Elastic Cloud
  cloud_id: your-cloud-id
  
  # Index names
  property_index: properties
  wiki_chunks_index_prefix: wiki_chunks
  wiki_summaries_index_prefix: wiki_summaries
  
  # Connection settings
  request_timeout: 60
  max_retries: 5
  verify_certs: true
```

#### Search Configuration
```yaml
search:
  default_size: 20
  max_size: 100
  enable_fuzzy: true
  highlight_enabled: true
  
  # Hybrid search weights
  vector_weight: 0.7    # Favor semantic similarity
  text_weight: 0.3      # Less weight on keyword matching
```

#### Logging Configuration
```yaml
logging:
  level: DEBUG
  structured: true      # JSON structured logs
  file_path: logs/mcp_server.log
```

### Tool Discovery

#### How MCP Tool Discovery Works

MCP servers expose their available tools through a discovery mechanism that allows clients (like LLMs) to:
1. **List available tools** - Get all tools the server provides
2. **Understand tool purposes** - Read clear descriptions of what each tool does
3. **View parameter schemas** - See required and optional parameters with types
4. **Make informed selections** - Choose the right tool for user intents

#### Discovering Available Tools

When a client connects to the MCP server, it can discover tools programmatically:

```python
# Example: How clients discover MCP tools
async def discover_tools(mcp_server):
    """Discover available tools from MCP server."""
    # In FastMCP, tools are registered with the @app.tool() decorator
    # Clients can query available tools through the MCP protocol
    
    tools = await mcp_server.list_tools()
    
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Parameters: {tool.parameters}")
```

#### Available Tools in This Server

The MCP server exposes 6 primary tools:

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `search_properties_tool` | Search for properties using natural language queries | query, filters, search_type |
| `get_property_details_tool` | Get detailed information for a specific property | listing_id |
| `search_wikipedia_tool` | Search Wikipedia for location and topic information | query, search_in, filters |
| `get_wikipedia_article_tool` | Retrieve complete Wikipedia article by ID | page_id |
| `search_wikipedia_by_location_tool` | Find Wikipedia articles for a specific location | city, state, query |
| `health_check_tool` | Check the health status of services | none |

#### Tool Selection by LLMs

LLMs use tool descriptions and parameter schemas to:

1. **Match user intent to tools**:
   - "Find homes in Berkeley" → `search_properties_tool`
   - "Tell me about Golden Gate Park" → `search_wikipedia_tool`
   - "Get details for listing ABC123" → `get_property_details_tool`

2. **Extract parameters from natural language**:
   ```python
   # User says: "Show me 3-bedroom houses under 500k in San Francisco"
   # LLM extracts:
   {
       "tool": "search_properties_tool",
       "parameters": {
           "query": "houses",
           "min_bedrooms": 3,
           "max_price": 500000,
           "city": "San Francisco"
       }
   }
   ```

3. **Validate parameters against schemas**:
   - Required vs optional parameters
   - Type checking (string, number, array)
   - Value constraints (min/max, enums)

#### Testing Tool Discovery

Run the tool discovery tests to see this in action:

```bash
# Run tool discovery tests
cd real_estate_search
python -m pytest mcp_integration_tests/test_tool_discovery.py -v

# Output shows:
# ✓ Server initialization with tools
# ✓ Tool registration verification  
# ✓ Tool metadata structure validation
# ✓ Description quality checks
# ✓ Parameter schema validation
# ✓ Client discovery flow simulation
# ✓ LLM routing scenario testing
```

#### Best Practices for Tool Design

Our tools follow MCP best practices:

1. **Clear, Descriptive Names**: 
   - ✅ `search_properties_tool` (clear purpose)
   - ❌ `search` (too vague)

2. **Comprehensive Descriptions**:
   - ✅ "Search for properties using natural language queries"
   - ❌ "Property function"

3. **Well-Documented Parameters**:
   ```python
   # Good parameter documentation
   query: str  # "Natural language description (e.g., 'modern home with pool')"
   size: int   # "Number of results (1-100, default 20)"
   ```

4. **Logical Parameter Grouping**:
   - Core parameters (query)
   - Filters (price, location, features)
   - Control parameters (size, search_type)

### MCP Tool Usage Examples

#### Property Search Tool
```python
# Natural language property search
result = await search_properties_tool(
    query="modern home with pool near good schools",
    min_price=300000,
    max_price=800000,
    min_bedrooms=3,
    city="San Francisco",
    state="CA",
    size=10,
    search_type="hybrid"  # semantic + text
)
```

#### Wikipedia Location Search
```python
# Find information about a neighborhood
result = await search_wikipedia_by_location_tool(
    city="Mission District",
    state="CA", 
    query="history culture restaurants",
    size=5
)
```

#### Health Monitoring
```python
# Check system health
health = await health_check_tool()
print(f"Status: {health['status']}")
print(f"Elasticsearch: {health['services']['elasticsearch']['status']}")
```

### Architecture Deep Dive

#### Service Layer Architecture
```
MCPServer
├── ElasticsearchClient     # Connection pooling, retry logic
├── EmbeddingService        # Multi-provider embedding generation
├── PropertySearchService   # Hybrid property search logic
├── WikipediaSearchService  # Wikipedia content search
└── HealthCheckService     # System monitoring
```

#### Data Flow
1. **Tool Request** → MCP protocol receives natural language query
2. **Validation** → Pydantic models validate and parse parameters  
3. **Embedding** → Generate query vector using configured provider
4. **Search** → Execute hybrid search (vector + BM25) against Elasticsearch
5. **Processing** → Rank, filter, and format results
6. **Response** → Return structured data via MCP protocol

#### Error Handling Strategy
- **Validation Errors** → Clear parameter requirement messages
- **Elasticsearch Issues** → Retry with exponential backoff, connection pooling
- **Embedding Failures** → Graceful fallback to text-only search
- **Network Timeouts** → Configurable timeouts with retry logic
- **Resource Cleanup** → Proper connection and resource management

### Performance Optimization

#### Elasticsearch Optimization
```yaml
elasticsearch:
  request_timeout: 30
  max_retries: 3
  # Use connection pooling for better performance
```

#### Embedding Optimization  
```yaml
embedding:
  batch_size: 50        # Larger batches for better throughput
  timeout_seconds: 60.0 # Longer timeout for large batches
  max_retries: 3
```

#### Search Optimization
```yaml
search:
  vector_weight: 0.6    # Tune based on your use case
  text_weight: 0.4
  enable_fuzzy: false   # Disable for better performance
  default_size: 10      # Smaller result sets
```

### Deployment Considerations

#### Production Configuration
```yaml
# Production settings
debug: false
logging:
  level: INFO
  structured: true
  file_path: /var/log/mcp_server.log

elasticsearch:
  verify_certs: true
  request_timeout: 30
  
embedding:
  timeout_seconds: 30.0
  max_retries: 3
```

#### Monitoring and Observability
- Health check endpoint provides detailed service status
- Structured JSON logging for log aggregation
- Request tracing with unique IDs
- Performance metrics (execution time, hit counts)

#### Security Best Practices
- Store API keys in environment variables, never in code
- Use Elasticsearch authentication in production
- Enable SSL certificate verification
- Implement rate limiting at infrastructure level
- Regular security updates for dependencies

### Troubleshooting

#### Common Issues

**"Embedding service not available"**
```bash
# Check API key is set
echo $VOYAGE_API_KEY

# Test provider connectivity
python -c "
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.config.settings import EmbeddingConfig
service = EmbeddingService(EmbeddingConfig(provider='voyage', api_key='your-key'))
print(service.embed_text('test'))
"
```

**"Elasticsearch connection failed"**
```bash
# Verify Elasticsearch is running
curl -X GET "localhost:9200/_cluster/health"

# Check index exists
curl -X GET "localhost:9200/properties/_count"
```

**"No search results"**
```bash
# Verify data exists
curl -X GET "localhost:9200/properties/_search?size=1"

# Check embedding dimensions match
python -c "
from mcp_server.config.settings import MCPServerConfig
config = MCPServerConfig.from_env()
print(f'Configured dimension: {config.embedding.dimension}')
"
```

#### Debug Mode
```yaml
# Enable debug logging
debug: true
logging:
  level: DEBUG
```

This will provide detailed logs showing:
- Query construction and execution
- Embedding generation process
- Elasticsearch request/response details
- Service initialization steps

### Development Setup

#### Development Dependencies
```bash
# Install development tools
pip install pytest pytest-asyncio pytest-mock black mypy

# Code formatting
black mcp_server/

# Type checking  
mypy mcp_server/

# Run tests with coverage
pytest --cov=mcp_server mcp_integration_tests/
```

#### Custom Tool Development
Extend the server with custom tools by:

1. **Create tool function** in appropriate tools module
2. **Register tool** in `main.py` `_register_tools()` method
3. **Add tests** in `mcp_integration_tests/`
4. **Update documentation**

Example custom tool:
```python
@app.tool()
async def custom_search_tool(query: str) -> Dict[str, Any]:
    """Custom search functionality."""
    # Implementation here
    return {"results": [...]}
```

The MCP server architecture is designed for easy extension and customization while maintaining type safety and robust error handling.