# Real Estate Search MCP Server

A Model Context Protocol (MCP) server providing semantic search capabilities for real estate properties and Wikipedia content using FastMCP.

## Features

- **Semantic Property Search**: Natural language queries for property listings
- **Wikipedia Integration**: Location-aware content search for neighborhood context
- **Multi-Provider Embeddings**: Support for Voyage, OpenAI, Gemini, and Ollama
- **Hybrid Search**: Combines vector similarity with traditional text search
- **Type-Safe**: Built with Pydantic models throughout
- **Health Monitoring**: Comprehensive system health checks

## Quick Start

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
# Copy and edit configuration
cp config/config.yaml config/local.yaml
# Set your API keys in .env file in project root
```

3. **Start Server**
```bash
python main.py config/local.yaml
```

## Available Tools

### Property Search
- `search_properties_tool`: Natural language property search with filters
- `get_property_details_tool`: Detailed property information

### Wikipedia Search  
- `search_wikipedia_tool`: Semantic Wikipedia content search
- `search_wikipedia_by_location_tool`: Location-specific Wikipedia queries

### Monitoring
- `health_check_tool`: System health and service status

## Configuration

Configuration is managed through YAML files and environment variables:

```yaml
elasticsearch:
  host: localhost
  port: 9200
  property_index: properties

embedding:
  provider: voyage  # voyage, openai, gemini, ollama
  model_name: voyage-3
  dimension: 1024
  # API key loaded from environment
```

## Architecture

```
mcp_server/
├── config/          # Configuration management
├── models/          # Pydantic data models  
├── services/        # Core business logic
├── tools/           # MCP tool implementations
├── utils/           # Utilities and logging
└── main.py          # FastMCP server
```

## Testing

Run integration tests:
```bash
cd ../mcp_integration_tests
pytest -v
```

## Requirements

- Python 3.10+
- Elasticsearch with property and Wikipedia indices
- API key for chosen embedding provider
- FastMCP framework

See `requirements.txt` for complete dependency list.