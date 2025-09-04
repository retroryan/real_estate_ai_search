#!/usr/bin/env python3
"""Simple test for the new tool names."""

import requests
import json

def test_tool_list():
    """Test listing tools from MCP server."""
    url = "http://localhost:8000/mcp/v1/sse"
    
    # Test tool listing
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream, application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    
    print("Testing MCP Server Tool Listing...")
    print("=" * 60)
    
    try:
        # Use SSE endpoint properly
        response = requests.post(url, json=payload, headers=headers, stream=True)
        
        if response.status_code == 200:
            print("✅ Connected to MCP server")
            
            # Parse SSE events
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'result' in data and 'tools' in data['result']:
                            tools = data['result']['tools']
                            print(f"\n📦 Found {len(tools)} tools:")
                            print("-" * 40)
                            
                            # Check for our new tool names
                            expected_tools = [
                                "search_properties",  # Main AI tool
                                "search_properties_with_filters",  # Filter tool
                                "search_wikipedia",
                                "search_wikipedia_by_location",
                                "get_property_details",
                                "get_rich_property_details",
                                "health_check"
                            ]
                            
                            for tool in tools:
                                name = tool.get('name', 'unknown')
                                desc = tool.get('description', '')[:60]
                                
                                if name in expected_tools:
                                    print(f"  ✅ {name}")
                                    print(f"     {desc}...")
                                else:
                                    print(f"  ⚠️  {name} (unexpected)")
                            
                            # Check for removed tools
                            removed_tools = ["natural_language_search", "natural_language_search_tool"]
                            tool_names = [t.get('name') for t in tools]
                            
                            print("\n🔍 Checking for removed tools:")
                            print("-" * 40)
                            for removed in removed_tools:
                                if removed in tool_names:
                                    print(f"  ❌ {removed} still exists (should be removed)")
                                else:
                                    print(f"  ✅ {removed} properly removed")
                            
                            break
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\nMake sure the MCP server is running:")
        print("  python -m real_estate_search.mcp_server.main")

if __name__ == "__main__":
    test_tool_list()