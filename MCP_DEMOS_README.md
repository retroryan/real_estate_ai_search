# MCP Real Estate Demo Runner

A comprehensive shell script to run MCP (Model Context Protocol) demos with support for both STDIO and HTTP transports.

## Current Status: ✅ STDIO Transport (Tested & Working)

The current implementation has been tested and is working with **STDIO transport**:

- ✅ All 8 demos pass
- ✅ Real server connections established
- ✅ Actual Elasticsearch data returned
- ✅ 420 properties and 526 Wikipedia articles accessible
- ✅ No mock data - everything is live

## Features

- **Dual Transport Support**: Switch between STDIO and HTTP transports
- **8 Interactive Demos**: Property search, Wikipedia integration, multi-entity queries
- **Configuration Management**: YAML-based config with environment variable support
- **Real Data**: Connects to actual MCP server with Elasticsearch backend
- **Comprehensive Testing**: Built-in connectivity tests and full demo suite

## Usage

### Basic Commands

```bash
# List all available demos (default: stdio)
./mcp_demos.sh

# Run a specific demo with stdio transport
./mcp_demos.sh 1

# Run with HTTP transport (requires HTTP server)
./mcp_demos.sh 1 --http

# Run all demos
./mcp_demos.sh --all

# Test connectivity
./mcp_demos.sh --test
```

### Transport Options

```bash
# Use STDIO transport (default)
./mcp_demos.sh 1 --stdio

# Use HTTP transport
./mcp_demos.sh 1 --http

# Use custom config file
./mcp_demos.sh 1 --config my_config.yaml
```

### Available Demos

| Demo # | Description |
|--------|-------------|
| 1 | Basic Property Search - Natural language search |
| 2 | Filtered Property Search - Search with price/type filters |
| 3 | Wikipedia Search - Search Wikipedia articles |
| 4 | Wikipedia Location Context - Location-based Wikipedia search |
| 5 | Location Discovery - Discover properties and info by location |
| 6 | Multi-Entity Search - Search properties and Wikipedia together |
| 7 | Property Details - Get detailed property information |
| 8 | Search Comparison - Compare semantic vs text search algorithms |

### Advanced Usage

```bash
# Run all demos with verbose output
./mcp_demos.sh --all --verbose

# Test HTTP connectivity
./mcp_demos.sh --test --http

# Run demo with custom configuration
./mcp_demos.sh --config real_estate_search/mcp_demos/config/config_http.yaml 1
```

## Transport Modes

### STDIO Transport (Default) ✅ Working

- **Use Case**: Local development and testing
- **Protocol**: Process-based communication via stdin/stdout
- **Server**: Launches MCP server module automatically
- **Config**: `real_estate_search/mcp_demos/config/config_stdio.yaml`
- **Status**: ✅ Fully tested and working

**Prerequisites for STDIO:**
- MCP server module at `real_estate_search.mcp_server.main`
- Elasticsearch running on localhost:9200
- Python with required packages installed

### HTTP Transport ✅ Working

- **Use Case**: Network-based communication, production deployments
- **Protocol**: HTTP/HTTPS with Streamable HTTP transport
- **Server**: MCP server running in HTTP mode
- **Config**: `real_estate_search/mcp_demos/config/config_http.yaml`
- **Status**: ✅ Fully tested and working

**Prerequisites for HTTP:**
- MCP server running in HTTP mode on localhost:8000 (configurable)
- Elasticsearch running on localhost:9200
- Network connectivity to HTTP endpoint

## Configuration

### Environment Variables

The script supports configuration via environment variables:

```bash
# Specify custom config file
export MCP_CONFIG_PATH="path/to/config.yaml"
./mcp_demos.sh 1
```

### YAML Configuration Files

#### STDIO Configuration (`config_stdio.yaml`)
```yaml
transport: stdio
stdio:
  server_module: real_estate_search.mcp_server.main
  startup_timeout: 5
connection:
  request_timeout: 60
  enable_logging: true
  log_level: INFO
demo_mode: true
rich_output: true
```

#### HTTP Configuration (`config_http.yaml`)
```yaml
transport: http
http:
  base_url: http://localhost:8000/mcp
  timeout: 30
  verify_ssl: true
connection:
  request_timeout: 60
  enable_logging: true
  log_level: INFO
demo_mode: true
rich_output: true
```

## Prerequisites

### System Requirements
- Python 3.10+
- Bash shell
- curl (for connectivity checks)

### For STDIO Transport ✅
- MCP server module: `real_estate_search.mcp_server.main`
- Elasticsearch running on localhost:9200

### For HTTP Transport 🚧
- MCP server running in HTTP mode
- Accessible HTTP endpoint (default: localhost:8000)

### Start Elasticsearch
```bash
docker run -d -p 9200:9200 -e 'discovery.type=single-node' \
  -e 'xpack.security.enabled=false' elasticsearch:8.11.0
```

## Example Output

```bash
$ ./mcp_demos.sh 1

╔══════════════════════════════════════════════════════════════╗
║              MCP Real Estate Demo Runner                    ║
║          Supporting STDIO and HTTP Transports               ║
╚══════════════════════════════════════════════════════════════╝

Transport Mode: STDIO

✓ MCP server script found
✓ Elasticsearch is accessible

Running Demo 1 with stdio transport...
Config: real_estate_search/mcp_demos/config/config_stdio.yaml

╭────────────────────────────────╮
│ Demo 1: Basic Property Search  │
│ Query: 'modern home with pool' │
╰────────────────────────────────╯

[Property search results displayed with real data...]

✓ Found 420 properties in 284ms
```

## Testing Results

### STDIO Transport Results
```
======================================================================
DEMO RESULTS SUMMARY (STDIO Transport)
======================================================================
Demo Name                           Status       Results    Time (ms) 
----------------------------------------------------------------------
Basic Property Search               ✓ PASSED     420        244       
Filtered Property Search            ✓ PASSED     0          169       
Wikipedia Search                    ✓ PASSED     526        190       
Wikipedia Location Context          ✓ PASSED     0          152       
Location-Based Discovery            ✓ PASSED     22         334       
Multi-Entity Search                 ✓ PASSED     946        348       
Property Details Deep Dive          ✓ PASSED     1          50        
Search Comparison                   ✓ PASSED     884        374       
----------------------------------------------------------------------
Total: 8 demos | Passed: 8 | Failed: 0
======================================================================

✅ ALL DEMOS PASSED!
```

### HTTP Transport Results
```
======================================================================
DEMO RESULTS SUMMARY (HTTP Transport)
======================================================================
Demo Name                           Status       Results    Time (ms) 
----------------------------------------------------------------------
Basic Property Search               ✓ PASSED     420        182       
Filtered Property Search            ✓ PASSED     0          164       
Wikipedia Search                    ✓ PASSED     526        198       
Wikipedia Location Context          ✓ PASSED     0          153       
Location-Based Discovery            ✓ PASSED     22         362       
Multi-Entity Search                 ✓ PASSED     946        366       
Property Details Deep Dive          ✓ PASSED     1          50        
Search Comparison                   ✓ PASSED     884        386       
----------------------------------------------------------------------
Total: 8 demos | Passed: 8 | Failed: 0
======================================================================

✅ ALL DEMOS PASSED!
```

## Implementation Details

### Architecture
- **Shell Script**: Main demo runner with transport selection
- **Python Client**: FastMCP-based client with Pydantic models
- **Configuration**: YAML-based config with environment variable override
- **MCP Server**: Real server with Elasticsearch integration

### Key Features
- **Real Data**: No mock responses - all data from live Elasticsearch
- **Transport Abstraction**: Clean separation between STDIO and HTTP
- **Error Handling**: Comprehensive error detection and user-friendly messages
- **Logging**: Configurable logging levels for debugging
- **Rich Output**: Colorized terminal output with tables and progress indicators

## Starting the HTTP Server

To start the MCP server in HTTP mode:

```bash
# Start HTTP server (default: localhost:8000)
python -m real_estate_search.mcp_server.main --transport http

# Start with custom host and port
python -m real_estate_search.mcp_server.main --transport http --host 0.0.0.0 --port 8080

# Start with specific config file
python -m real_estate_search.mcp_server.main --transport http --config path/to/config.yaml
```

The server will be available at `http://localhost:8000/mcp` by default.

## Troubleshooting

### Common Issues

**"MCP server module not found"**
- Ensure the MCP server module is properly installed
- Check that `real_estate_search.mcp_server.main` is importable

**"Elasticsearch may not be running"**
- Start Elasticsearch with provided Docker command
- Verify localhost:9200 is accessible

**"HTTP MCP server may not be running"**
- Configure and start MCP server in HTTP mode
- Check HTTP endpoint accessibility

### Debug Mode
```bash
# Run with verbose logging
./mcp_demos.sh 1 --verbose

# Check connectivity
./mcp_demos.sh --test
```