# Quickstart Guide: MCP Server Direct Search Service Integration

**Date**: 2025-01-07  
**Feature**: MCP Server Direct Search Service Integration  
**Branch**: 001-update-the-real

## Prerequisites

Before starting, ensure you have:
1. Python 3.10+ installed
2. Elasticsearch running on port 9200
3. Virtual environment activated
4. Project dependencies installed (`pip install -e .`)

## Important Note

This is a COMPLETE REPLACEMENT with no backward compatibility. The MCP server will return search_service response format directly. All clients must be updated to handle the new format.

## Quick Validation Steps

### Step 1: Verify Search Service is Working

```bash
# Test search service directly
python -c "
from elasticsearch import Elasticsearch
from real_estate_search.search_service.properties import PropertySearchService
from real_estate_search.search_service.models import PropertySearchRequest

es = Elasticsearch('http://localhost:9200')
service = PropertySearchService(es)
request = PropertySearchRequest(query='San Francisco', size=5)
response = service.search(request)
print(f'Search service working: {response.total_hits} properties found')
print(f'Response type: {type(response).__name__}')
"
```

Expected output: 
- `Search service working: X properties found`
- `Response type: PropertySearchResponse`

### Step 2: Start the Updated MCP Server

```bash
# Start MCP server with direct search_service integration
cd real_estate_search/mcp_server
python main.py
```

Expected output:
```
INFO: MCP Server initialized with direct search_service integration
INFO: Using search_service.properties.PropertySearchService
INFO: Using search_service.wikipedia.WikipediaSearchService  
INFO: Using search_service.neighborhoods.NeighborhoodSearchService
INFO: Server listening on stdio transport
```

### Step 3: Verify Direct Integration

```bash
# Check that MCP models are gone
python -c "
import os
mcp_models = 'real_estate_search/mcp_server/models'
if os.path.exists(mcp_models):
    files = os.listdir(mcp_models)
    if any(f.endswith('.py') and f != '__init__.py' for f in files):
        print('ERROR: MCP models still exist - not fully migrated')
    else:
        print('✓ MCP models removed')
else:
    print('✓ MCP models directory removed')
"
```

Expected: `✓ MCP models removed` or `✓ MCP models directory removed`

### Step 4: Test Property Search with New Format

```bash
# Test property search returns search_service format
cd real_estate_search/mcp_demos
python -c "
from client.client import MCPClient
import json

client = MCPClient()
response = client.call_tool('search_properties', {
    'query': 'San Francisco',
    'search_type': 'text',
    'size': 2
})

# Check for search_service response format
assert 'results' in response
assert 'total_hits' in response
assert 'request' in response
assert 'execution_time_ms' in response

print('✓ Property search returns search_service format')
print(f'Total hits: {response[\"total_hits\"]}')
print(f'Request echoed: {response[\"request\"][\"query\"]}')
"
```

Expected: 
- `✓ Property search returns search_service format`
- Request object is included in response

### Step 5: Test Wikipedia Search with New Format

```bash
# Test Wikipedia search with direct integration
python -c "
from client.client import MCPClient

client = MCPClient()
response = client.call_tool('search_wikipedia', {
    'query': 'San Francisco',
    'search_type': 'fulltext',
    'size': 2
})

# Verify search_service format
assert 'results' in response
assert 'total_hits' in response
assert 'request' in response

print('✓ Wikipedia search returns search_service format')
print(f'Found {len(response[\"results\"])} articles')
"
```

Expected: `✓ Wikipedia search returns search_service format`

### Step 6: Test Neighborhood Search

```bash
# Test neighborhood search with cross-index data
python -c "
from client.client import MCPClient

client = MCPClient()
response = client.call_tool('search_neighborhoods', {
    'city': 'San Francisco',
    'state': 'CA',
    'include_properties': True,
    'include_wikipedia': True
})

# Verify search_service format
assert 'neighborhoods' in response
assert 'property_stats' in response or response['include_properties'] == False
assert 'request' in response

print('✓ Neighborhood search returns search_service format')
if 'property_stats' in response:
    print(f'Avg price: ${response[\"property_stats\"][\"avg_price\"]:,.0f}')
"
```

Expected: `✓ Neighborhood search returns search_service format`

### Step 7: Verify No Adapters Exist

```bash
# Check for adapter code (should not exist)
python -c "
import ast
import os

def check_for_adapters(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    return 'Adapter' in content or 'adapter' in content or 'convert' in content

tools_dir = 'real_estate_search/mcp_server/tools'
has_adapters = False
for file in os.listdir(tools_dir):
    if file.endswith('.py'):
        filepath = os.path.join(tools_dir, file)
        if check_for_adapters(filepath):
            print(f'WARNING: {file} may contain adapter code')
            has_adapters = True

if not has_adapters:
    print('✓ No adapter patterns found in tools')
"
```

Expected: `✓ No adapter patterns found in tools`

### Step 8: Run Full Validation Suite

```bash
# Run all MCP demos with new response format
cd real_estate_search/mcp_demos
python run_all_demos.py
```

Note: Demos may need updates to handle new response format. This is expected as we're doing a complete replacement with no backward compatibility.

## Troubleshooting

### Issue: "ImportError: cannot import PropertySearchRequest from mcp_server.models"
**Solution**: Update imports to use search_service:
```python
from real_estate_search.search_service.models import PropertySearchRequest
```

### Issue: "Response format has changed"
**Expected**: This is a complete replacement. Update client code to handle search_service format.

### Issue: "Module 'mcp_server.services.property_search' not found"
**Expected**: This module was deleted. Use:
```python
from real_estate_search.search_service.properties import PropertySearchService
```

### Issue: "KeyError when accessing response fields"
**Solution**: Response format has changed to search_service format. Update field access:
- Old: `response['properties']`
- New: `response['results']`

## Validation Checklist

- [ ] Search service works independently
- [ ] MCP server starts with search_service
- [ ] All MCP models deleted
- [ ] All MCP service duplicates deleted
- [ ] Tools use search_service directly
- [ ] No adapter code exists
- [ ] Response format is search_service format
- [ ] No backward compatibility code
- [ ] Tests updated for new format
- [ ] Demos work with new format (after updates)

## Important Changes

### What Was Deleted
1. `mcp_server/models/` - All model files
2. `mcp_server/services/property_search.py`
3. `mcp_server/services/wikipedia_search.py`
4. All adapter and transformation code

### What Changed
1. MCP tools import from `search_service.models`
2. MCP tools use `search_service` classes directly
3. Response format matches `search_service` exactly
4. No transformation or compatibility layers

### What Stays the Same
1. MCP protocol interface
2. Tool names and parameters
3. Elasticsearch connectivity
4. Configuration management

## Next Steps

After successful validation:

1. **Commit all changes atomically**: Single commit for complete replacement
2. **Update all clients**: Modify to handle search_service response format
3. **Remove old tests**: Delete tests for removed MCP models/services
4. **Update documentation**: Reflect direct integration architecture

## No Rollback

Per constitutional principles:
- This is a permanent change
- No rollback plan exists
- No compatibility mode available
- All systems must be updated to work with new format