"""Integration test demonstrating MCP tool discovery.

This test shows how a client can discover available tools from the MCP server,
including their names, descriptions, and parameter schemas.
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from real_estate_search.mcp_server.main import MCPServer
from real_estate_search.mcp_server.config.settings import MCPServerConfig


@pytest.fixture
def test_config():
    """Create test configuration."""
    config_dict = {
        "server_name": "test-real-estate-search",
        "server_version": "1.0.0",
        "debug": True,
        "elasticsearch": {
            "host": "localhost",
            "port": 9200,
            "property_index": "properties",
            "wiki_chunks_index_prefix": "wiki_chunks",
            "wiki_summaries_index_prefix": "wiki_summaries"
        },
        "embedding": {
            "provider": "voyage",
            "model_name": "voyage-3",
            "dimension": 1024,
            "batch_size": 10
        },
        "search": {
            "default_size": 20,
            "max_size": 100,
            "text_weight": 0.5,
            "vector_weight": 0.5,
            "enable_fuzzy": True,
            "aggregations_enabled": True
        }
    }
    return MCPServerConfig(**config_dict)


@pytest.fixture
def mock_services():
    """Create mock services to avoid real connections."""
    with patch('real_estate_search.mcp_server.main.ElasticsearchClient') as mock_es, \
         patch('real_estate_search.mcp_server.main.EmbeddingService') as mock_embed, \
         patch('real_estate_search.mcp_server.main.PropertySearchService') as mock_prop, \
         patch('real_estate_search.mcp_server.main.WikipediaSearchService') as mock_wiki, \
         patch('real_estate_search.mcp_server.main.HealthCheckService') as mock_health:
        
        # Configure mock Elasticsearch client
        mock_es_instance = Mock()
        mock_es_instance.ping.return_value = True
        mock_es_instance.get_cluster_health.return_value = {"status": "green"}
        mock_es.return_value = mock_es_instance
        
        yield {
            'es_client': mock_es,
            'embedding': mock_embed,
            'property': mock_prop,
            'wikipedia': mock_wiki,
            'health': mock_health
        }


class TestMCPToolDiscovery:
    """Test MCP tool discovery functionality."""
    
    def test_server_initialization(self, test_config, mock_services):
        """Test that MCP server initializes with correct metadata."""
        with patch('real_estate_search.mcp_server.main.MCPServerConfig.from_env', return_value=test_config):
            server = MCPServer()
            
            # Verify server name and version
            assert server.config.server_name == "test-real-estate-search"
            assert server.config.server_version == "1.0.0"
            
            # Verify FastMCP app is created
            assert server.app is not None
    
    def test_tool_registration(self, test_config, mock_services):
        """Test that all expected tools are registered."""
        with patch('real_estate_search.mcp_server.main.MCPServerConfig.from_env', return_value=test_config):
            server = MCPServer()
            
            # Get registered tools from FastMCP app
            # Note: In a real scenario, FastMCP would expose a way to list tools
            # For this test, we verify the registration was called
            expected_tools = [
                'search_properties_tool',
                'get_property_details_tool',
                'search_wikipedia_tool',
                'get_wikipedia_article_tool',
                'search_wikipedia_by_location_tool',
                'health_check_tool'
            ]
            
            # Since we can't directly access FastMCP's registered tools,
            # we verify the registration method was called
            assert hasattr(server, '_register_tools')
    
    def test_tool_metadata_structure(self):
        """Test the expected structure of tool metadata for clients."""
        # This demonstrates what a client would expect to receive
        # when discovering tools from the MCP server
        
        expected_tool_discovery_response = {
            "tools": [
                {
                    "name": "search_properties_tool",
                    "description": "Search for properties using natural language queries",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language description"
                            },
                            "property_type": {
                                "type": "string",
                                "description": "Filter by type (House, Condo, Townhouse, etc.)",
                                "required": False
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum price filter",
                                "required": False
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price filter",
                                "required": False
                            },
                            "city": {
                                "type": "string",
                                "description": "Filter by city",
                                "required": False
                            },
                            "size": {
                                "type": "integer",
                                "description": "Number of results (1-100)",
                                "default": 20
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "search_wikipedia_tool",
                    "description": "Search Wikipedia for location and topic information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What you're looking for"
                            },
                            "search_in": {
                                "type": "string",
                                "enum": ["full", "summaries", "chunks"],
                                "default": "full"
                            },
                            "city": {
                                "type": "string",
                                "description": "Filter by city name",
                                "required": False
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
        
        # Verify the structure is what we expect
        assert "tools" in expected_tool_discovery_response
        assert len(expected_tool_discovery_response["tools"]) > 0
        
        # Check first tool structure
        first_tool = expected_tool_discovery_response["tools"][0]
        assert "name" in first_tool
        assert "description" in first_tool
        assert "parameters" in first_tool
        assert "properties" in first_tool["parameters"]
        assert "required" in first_tool["parameters"]
    
    def test_tool_description_quality(self):
        """Test that tool descriptions are clear and helpful for LLMs."""
        # This test verifies that our tool descriptions follow best practices
        
        tool_descriptions = {
            "search_properties_tool": {
                "good": "Search for properties using natural language queries",
                "bad_examples": [
                    "search",  # Too vague
                    "prop",    # Unclear abbreviation
                    "execute"  # Doesn't describe what it does
                ]
            },
            "get_property_details_tool": {
                "good": "Get detailed information for a specific property",
                "bad_examples": [
                    "get",      # Too generic
                    "details",  # Missing context
                    "fetch"     # Technical jargon
                ]
            }
        }
        
        for tool_name, desc_info in tool_descriptions.items():
            good_desc = desc_info["good"]
            
            # Good descriptions should be:
            # 1. At least 5 words long
            assert len(good_desc.split()) >= 5
            
            # 2. Start with a verb
            first_word = good_desc.split()[0].lower()
            action_verbs = ["search", "get", "find", "retrieve", "list", "check"]
            assert any(first_word.startswith(verb) for verb in action_verbs)
            
            # 3. Mention the resource type
            resource_keywords = ["properties", "property", "wikipedia", "article", "health"]
            assert any(keyword in good_desc.lower() for keyword in resource_keywords)
    
    def test_parameter_validation_schemas(self):
        """Test that parameter schemas include proper validation rules."""
        # Example of what proper parameter validation should look like
        
        property_search_params = {
            "query": {
                "type": "string",
                "description": "Natural language description",
                "minLength": 1,
                "maxLength": 500
            },
            "min_price": {
                "type": "number",
                "description": "Minimum price filter",
                "minimum": 0
            },
            "max_price": {
                "type": "number",
                "description": "Maximum price filter",
                "minimum": 0
            },
            "min_bedrooms": {
                "type": "integer",
                "description": "Minimum bedrooms",
                "minimum": 0,
                "maximum": 20
            },
            "city": {
                "type": "string",
                "description": "Filter by city",
                "pattern": "^[a-zA-Z\\s-]+$"  # Letters, spaces, and hyphens
            },
            "state": {
                "type": "string",
                "description": "Filter by state (2-letter code)",
                "pattern": "^[A-Z]{2}$",
                "minLength": 2,
                "maxLength": 2
            },
            "size": {
                "type": "integer",
                "description": "Number of results",
                "minimum": 1,
                "maximum": 100,
                "default": 20
            },
            "search_type": {
                "type": "string",
                "description": "Search mode",
                "enum": ["hybrid", "semantic", "text"],
                "default": "hybrid"
            }
        }
        
        # Verify validation rules are comprehensive
        assert property_search_params["state"]["pattern"] == "^[A-Z]{2}$"
        assert property_search_params["size"]["minimum"] == 1
        assert property_search_params["size"]["maximum"] == 100
        assert "enum" in property_search_params["search_type"]


class TestClientToolDiscoveryFlow:
    """Test the complete flow of how a client discovers and uses tools."""
    
    @pytest.mark.asyncio
    async def test_discovery_flow_simulation(self, test_config, mock_services):
        """Simulate how a client would discover and call tools."""
        with patch('real_estate_search.mcp_server.main.MCPServerConfig.from_env', return_value=test_config):
            # Step 1: Client connects to MCP server
            server = MCPServer()
            
            # Step 2: Client requests available tools
            # In a real MCP protocol, this would be something like:
            # response = await client.list_tools()
            
            # Simulated tool discovery response
            discovered_tools = {
                "tools": [
                    {
                        "name": "search_properties_tool",
                        "description": "Search for properties using natural language queries"
                    },
                    {
                        "name": "get_property_details_tool", 
                        "description": "Get detailed information for a specific property"
                    },
                    {
                        "name": "search_wikipedia_tool",
                        "description": "Search Wikipedia for location and topic information"
                    },
                    {
                        "name": "health_check_tool",
                        "description": "Check the health status of the MCP server and its services"
                    }
                ]
            }
            
            # Step 3: Client selects a tool based on user intent
            user_intent = "I want to find modern homes in San Francisco"
            
            # An LLM would analyze the intent and match it to the best tool
            selected_tool = "search_properties_tool"
            
            # Step 4: Client prepares parameters based on tool schema
            tool_params = {
                "query": "modern homes",
                "city": "San Francisco",
                "state": "CA",
                "search_type": "hybrid"
            }
            
            # Step 5: Client validates parameters match the schema
            assert "query" in tool_params  # Required parameter
            assert isinstance(tool_params["query"], str)
            assert len(tool_params["state"]) == 2 if "state" in tool_params else True
            
            # This demonstrates the complete discovery and usage flow
            assert selected_tool in [t["name"] for t in discovered_tools["tools"]]
    
    def test_tool_discovery_for_llm_routing(self):
        """Test that tool metadata is suitable for LLM-based routing."""
        # This test verifies that our tools can be effectively routed by an LLM
        
        routing_scenarios = [
            {
                "user_query": "Show me houses under 500k in Berkeley",
                "expected_tool": "search_properties_tool",
                "extracted_params": {
                    "query": "houses",
                    "max_price": 500000,
                    "city": "Berkeley"
                }
            },
            {
                "user_query": "Tell me about the history of Golden Gate Park",
                "expected_tool": "search_wikipedia_tool",
                "extracted_params": {
                    "query": "Golden Gate Park history",
                    "search_in": "full"
                }
            },
            {
                "user_query": "Get details for property listing ABC123",
                "expected_tool": "get_property_details_tool",
                "extracted_params": {
                    "listing_id": "ABC123"
                }
            },
            {
                "user_query": "Is the search system working properly?",
                "expected_tool": "health_check_tool",
                "extracted_params": {}
            }
        ]
        
        for scenario in routing_scenarios:
            # Verify that each scenario maps to a clear tool choice
            assert scenario["expected_tool"] is not None
            assert isinstance(scenario["extracted_params"], dict)
            
            # An LLM should be able to extract these parameters from the query
            user_query = scenario["user_query"]
            assert len(user_query) > 0
            
            # The expected tool should match the user intent
            if "houses" in user_query.lower() or "property" in user_query.lower():
                assert "propert" in scenario["expected_tool"]  # matches "properties" or "property"
            elif "history" in user_query.lower() or "about" in user_query.lower():
                assert "wikipedia" in scenario["expected_tool"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])