#!/bin/bash

# ============================================================================
# MCP Real Estate Demo Runner
# ============================================================================
# 
# This script provides easy access to all MCP demo queries with support for
# both STDIO and HTTP transport modes.
#
# Usage:
#   ./mcp_demos.sh                  # List all available demos (stdio)
#   ./mcp_demos.sh 1                # Run demo 1 with stdio transport
#   ./mcp_demos.sh 1 --http         # Run demo 1 with HTTP transport
#   ./mcp_demos.sh --all            # Run all demos
#   ./mcp_demos.sh --help           # Show help
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Default settings
TRANSPORT="http"
CONFIG_FILE=""
VERBOSE="false"

# Function to show header
show_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              ${PURPLE}MCP Real Estate Demo Runner${CYAN}                    ║${NC}"
    echo -e "${CYAN}║          ${BLUE}Supporting STDIO and HTTP Transports${CYAN}               ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Function to show help
show_help() {
    show_header
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./mcp_demos.sh [options] [demo_number|command]"
    echo
    echo -e "${GREEN}Transport Options:${NC}"
    echo "  --http         Use HTTP transport (default)"
    echo "  --stdio        Use STDIO transport"
    echo "  --config FILE  Use custom config file"
    echo
    echo -e "${GREEN}Commands:${NC}"
    echo "  1-8,12-19      Run specific demo number"
    echo "  --all          Run all demos"
    echo "  --list, -l     List all available demos"
    echo "  --list-tools   Discover and list all MCP server tools with metadata"
    echo "  --test         Run quick connectivity test"
    echo
    echo -e "${GREEN}Options:${NC}"
    echo "  --help, -h     Show this help message"
    echo "  --verbose, -v  Show detailed output"
    echo
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./mcp_demos.sh                    # List all demos (HTTP)"
    echo "  ./mcp_demos.sh 1                  # Run demo 1 with HTTP"
    echo "  ./mcp_demos.sh 1 --stdio          # Run demo 1 with STDIO"
    echo "  ./mcp_demos.sh --all --http       # Run all demos with HTTP"
    echo "  ./mcp_demos.sh --test --stdio     # Test STDIO connection"
    echo "  ./mcp_demos.sh --config my.yaml 1 # Use custom config for demo 1"
    echo
    echo -e "${GREEN}Available Demos:${NC}"
    list_demos
}

# Function to list all demos
list_demos() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Demo #  Description${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "  1     Basic Property Search - Search with natural language"
    echo "  2     Filtered Property Search - Search with price/type filters"
    echo "  3     Wikipedia Search - Search Wikipedia articles"
    echo "  4     Wikipedia Location Context - Search Wikipedia by location"
    echo "  5     Location Discovery - Discover properties and info by location"
    echo "  6     Multi-Entity Search - Search properties and Wikipedia together"
    echo "  7     Property Details - Get detailed property information"
    echo "  8     Search Comparison - Compare semantic vs text search"
    echo " 12     Natural Language Semantic Search - AI-powered natural language"
    echo " 13     Natural Language Examples - Multiple diverse AI search examples"
    echo " 14     Semantic vs Keyword Comparison - Compare AI vs traditional search"
    echo -e "${PURPLE} === Hybrid Search MCP Tool Demos ===${NC}"
    echo " 15     Hybrid Search Basics - Core hybrid search functionality with RRF"
    echo " 16     Location Understanding Comparison - Compare DSPy extraction with management demo"
    echo " 17     [Reserved for future demo]"
    echo " 18     Location-Aware Search - DSPy location extraction and geographic filtering"
    echo " 19     Advanced Scenarios - Edge cases, validation, and complex queries"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    local transport=$1
    
    echo -e "${YELLOW}Checking prerequisites for ${transport} transport...${NC}"
    
    # Check Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}Error: Python is not installed!${NC}"
        exit 1
    fi
    
    # Check if MCP demos module exists
    if ! python -c "import real_estate_search.mcp_demos" &> /dev/null; then
        echo -e "${RED}Error: MCP demos module not found!${NC}"
        echo "Please ensure you're in the correct directory and the module is installed."
        exit 1
    fi
    
    if [ "$transport" = "stdio" ]; then
        # Check if MCP server module exists
        if ! python -c "import real_estate_search.mcp_server.main" &> /dev/null; then
            echo -e "${RED}Error: MCP server module not found!${NC}"
            echo "Expected: real_estate_search.mcp_server.main"
            return 1
        else
            echo -e "${GREEN}✓ MCP server module found${NC}"
        fi
    elif [ "$transport" = "http" ]; then
        # Check if HTTP server is accessible (customize port as needed)
        HTTP_URL="${HTTP_URL:-http://localhost:8000/mcp}"
        if ! curl -s -o /dev/null -w "%{http_code}" "$HTTP_URL" | grep -q "307\|406\|200"; then
            echo -e "${YELLOW}Warning: HTTP MCP server may not be running on $HTTP_URL${NC}"
            echo -e "${YELLOW}To start HTTP server, run the MCP server in HTTP mode${NC}"
        else
            echo -e "${GREEN}✓ HTTP server is accessible at $HTTP_URL${NC}"
        fi
    fi
    
    # Check Elasticsearch
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:9200 | grep -q "200"; then
        echo -e "${YELLOW}Warning: Elasticsearch may not be running on localhost:9200${NC}"
        echo -e "${YELLOW}To start Elasticsearch:${NC}"
        echo "  docker run -d -p 9200:9200 -e 'discovery.type=single-node' \\"
        echo "    -e 'xpack.security.enabled=false' elasticsearch:8.11.0"
    else
        echo -e "${GREEN}✓ Elasticsearch is accessible${NC}"
    fi
    
    echo
}

# Function to get config file based on transport
get_config_file() {
    local transport=$1
    
    if [ -n "$CONFIG_FILE" ]; then
        # User specified custom config
        echo "$CONFIG_FILE"
    else
        # Use consolidated config file
        echo "real_estate_search/mcp_demos/config.yaml"
    fi
}

# Function to read transport from config file
get_transport_from_config() {
    local config_file=$1
    
    if [ -f "$config_file" ]; then
        python -c "
import yaml
try:
    with open('$config_file') as f:
        config = yaml.safe_load(f)
    print(config.get('transport', 'http'))
except:
    print('http')
"
    else
        echo "http"
    fi
}

# Function to run connectivity test
run_test() {
    local config_file=$(get_config_file $TRANSPORT)
    
    echo -e "${GREEN}Running connectivity test with $TRANSPORT transport...${NC}"
    echo -e "${BLUE}Config: $config_file${NC}"
    echo -e "${YELLOW}Module: real_estate_search.mcp_demos.test_quick_start${NC}"
    
    # Show the server endpoint for HTTP transport
    if [ "$TRANSPORT" = "http" ]; then
        HTTP_URL="${HTTP_URL:-http://localhost:8000/mcp}"
        echo -e "${YELLOW}Server URL: $HTTP_URL${NC}"
    fi
    echo
    
    # Set environment variables for config and transport override
    export MCP_CONFIG_PATH="$config_file"
    export MCP_TRANSPORT="$TRANSPORT"
    
    # Run the test script
    python real_estate_search/mcp_demos/test_quick_start.py
}

# Function to run a single demo
run_demo() {
    local demo_num=$1
    local config_file=$(get_config_file $TRANSPORT)
    
    echo -e "${GREEN}Running Demo $demo_num with $TRANSPORT transport...${NC}"
    echo -e "${BLUE}Config: $config_file${NC}"
    
    # Show the server endpoint for HTTP transport
    if [ "$TRANSPORT" = "http" ]; then
        HTTP_URL="${HTTP_URL:-http://localhost:8000/mcp}"
        echo -e "${YELLOW}Server URL: $HTTP_URL${NC}"
    fi
    
    # Set environment variables for config and transport override
    export MCP_CONFIG_PATH="$config_file"
    export MCP_TRANSPORT="$TRANSPORT"
    
    # Map demo numbers to actual demo functions
    case $demo_num in
        1)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_basic_property_search('modern home with pool')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_basic_property_search('modern home with pool')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_basic_property_search
asyncio.run(demo_basic_property_search('modern home with pool'))
"
            ;;
        2)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_property_filter()${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_property_filter()
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_property_filter
asyncio.run(demo_property_filter())
"
            ;;
        3)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_wikipedia_search('San Francisco')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_wikipedia_search('San Francisco')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_wikipedia_search
asyncio.run(demo_wikipedia_search('San Francisco'))
"
            ;;
        4)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_wikipedia_location_context('San Francisco', 'CA')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_wikipedia_location_context('San Francisco', 'CA')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_wikipedia_location_context
asyncio.run(demo_wikipedia_location_context('San Francisco', 'CA'))
"
            ;;
        5)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_location_based_discovery('Oakland', 'CA')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_location_based_discovery('Oakland', 'CA')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_location_based_discovery
asyncio.run(demo_location_based_discovery('Oakland', 'CA'))
"
            ;;
        6)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_multi_entity_search('downtown living')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_multi_entity_search('downtown living')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_multi_entity_search
asyncio.run(demo_multi_entity_search('downtown living'))
"
            ;;
        7)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_property_details_deep_dive('luxury')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_property_details_deep_dive('luxury')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_property_details_deep_dive
asyncio.run(demo_property_details_deep_dive('luxury'))
"
            ;;
        8)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.demo_semantic_vs_text_comparison('modern kitchen')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.demo_semantic_vs_text_comparison('modern kitchen')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos import demo_semantic_vs_text_comparison
asyncio.run(demo_semantic_vs_text_comparison('modern kitchen'))
"
            ;;
        12)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.natural_language_demo.demo_natural_language_semantic_search('cozy family home near good schools and parks')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.natural_language_demo.demo_natural_language_semantic_search('cozy family home near good schools and parks')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos.natural_language_demo import demo_natural_language_semantic_search
asyncio.run(demo_natural_language_semantic_search('cozy family home near good schools and parks'))
"
            ;;
        13)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.natural_language_demo.demo_natural_language_examples()${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.natural_language_demo.demo_natural_language_examples()
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos.natural_language_demo import demo_natural_language_examples
asyncio.run(demo_natural_language_examples())
"
            ;;
        14)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demos.natural_language_demo.demo_semantic_vs_keyword_comparison('stunning views from modern kitchen')${NC}"
            echo
            # URL: real_estate_search.mcp_demos.demos.natural_language_demo.demo_semantic_vs_keyword_comparison('stunning views from modern kitchen')
            python -c "
import asyncio
from real_estate_search.mcp_demos.demos.natural_language_demo import demo_semantic_vs_keyword_comparison
asyncio.run(demo_semantic_vs_keyword_comparison('stunning views from modern kitchen'))
"
            ;;
        15)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demo_1_basic_hybrid${NC}"
            echo
            python3 real_estate_search/mcp_demos/demo_1_basic_hybrid.py
            ;;
        16)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demo_2_location_comparison${NC}"
            echo
            python3 real_estate_search/mcp_demos/demo_2_location_comparison.py
            ;;
        17)
            echo -e "${YELLOW}Reserved for future demo${NC}"
            echo -e "${RED}Demo 17 is not implemented yet${NC}"
            exit 1
            ;;
        18)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demo_4_location_aware${NC}"
            echo
            python3 real_estate_search/mcp_demos/demo_4_location_aware.py
            ;;
        19)
            echo -e "${YELLOW}Module: real_estate_search.mcp_demos.demo_5_advanced_scenarios${NC}"
            echo
            python3 real_estate_search/mcp_demos/demo_5_advanced_scenarios.py
            ;;
        *)
            echo -e "${RED}Error: Invalid demo number '$demo_num'${NC}"
            echo "Valid demo numbers are 1-8, 12-16, 18-19"
            exit 1
            ;;
    esac
    
    echo
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to run all demos
run_all_demos() {
    local config_file=$(get_config_file $TRANSPORT)
    
    echo -e "${GREEN}Running ALL demos with $TRANSPORT transport...${NC}"
    echo -e "${BLUE}Config: $config_file${NC}"
    echo -e "${YELLOW}Module: real_estate_search.mcp_demos.run_all_demos${NC}"
    
    # Show the server endpoint for HTTP transport
    if [ "$TRANSPORT" = "http" ]; then
        HTTP_URL="${HTTP_URL:-http://localhost:8000/mcp}"
        echo -e "${YELLOW}Server URL: $HTTP_URL${NC}"
    fi
    echo
    
    # Set environment variables for config and transport override
    export MCP_CONFIG_PATH="$config_file"
    export MCP_TRANSPORT="$TRANSPORT"
    
    # Run the comprehensive demo script
    if [ "$VERBOSE" = "true" ]; then
        python real_estate_search/mcp_demos/run_all_demos.py
    else
        python real_estate_search/mcp_demos/run_all_demos.py 2>/dev/null
    fi
}

# Function to list all MCP server tools
run_list_tools() {
    local config_file=$(get_config_file $TRANSPORT)
    
    echo -e "${GREEN}Discovering MCP server tools with $TRANSPORT transport...${NC}"
    echo -e "${BLUE}Config: $config_file${NC}"
    
    # Display the exact URL/module being called
    echo -e "${YELLOW}Module: real_estate_search.mcp_demos.list_tools${NC}"
    
    # Show the server endpoint for HTTP transport
    if [ "$TRANSPORT" = "http" ]; then
        HTTP_URL="${HTTP_URL:-http://localhost:8000/mcp}"
        echo -e "${YELLOW}Server URL: $HTTP_URL${NC}"
    fi
    echo
    
    # Set environment variables for config and transport override
    export MCP_CONFIG_PATH="$config_file"
    export MCP_TRANSPORT="$TRANSPORT"
    
    # Run the tool discovery script
    python -m real_estate_search.mcp_demos.list_tools
}

# Main script logic
main() {
    local demo_number=""
    local command=""
    local transport_explicitly_set="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --stdio)
                TRANSPORT="stdio"
                transport_explicitly_set="true"
                shift
                ;;
            --http)
                TRANSPORT="http"
                transport_explicitly_set="true"
                shift
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --list|-l)
                command="list"
                shift
                ;;
            --list-tools)
                command="list-tools"
                shift
                ;;
            --test)
                command="test"
                shift
                ;;
            --all)
                command="all"
                shift
                ;;
            --verbose|-v)
                VERBOSE="true"
                shift
                ;;
            [1-8]|1[2-6]|18|19)
                demo_number=$1
                shift
                ;;
            *)
                echo -e "${RED}Error: Unknown option '$1'${NC}"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done
    
    show_header
    
    # If custom config provided, read transport from config unless explicitly overridden
    if [ -n "$CONFIG_FILE" ] && [ "$transport_explicitly_set" = "false" ]; then
        # Transport not explicitly set, check if config overrides default
        config_transport=$(get_transport_from_config "$CONFIG_FILE")
        TRANSPORT="$config_transport"
    fi
    
    # Show transport mode
    TRANSPORT_UPPER=$(echo "$TRANSPORT" | tr '[:lower:]' '[:upper:]')
    echo -e "${PURPLE}Transport Mode: ${YELLOW}${TRANSPORT_UPPER}${NC}"
    if [ -n "$CONFIG_FILE" ]; then
        echo -e "${PURPLE}Config File: ${YELLOW}$CONFIG_FILE${NC}"
    fi
    echo
    
    # Check prerequisites
    check_prerequisites $TRANSPORT
    
    # Execute command or demo
    if [ "$command" = "list" ] || ([ -z "$demo_number" ] && [ -z "$command" ]); then
        list_demos
        if [ -z "$demo_number" ] && [ "$command" != "list" ]; then
            echo
            echo -e "${YELLOW}Tip: Run './mcp_demos.sh <number>' to execute a specific demo${NC}"
            echo -e "${YELLOW}     Run './mcp_demos.sh --all' to execute all demos${NC}"
            echo -e "${YELLOW}     Run './mcp_demos.sh --list-tools' to discover and list all MCP server tools${NC}"
            echo -e "${YELLOW}     Add '--stdio' to use STDIO transport instead of HTTP${NC}"
        fi
    elif [ "$command" = "list-tools" ]; then
        run_list_tools
    elif [ "$command" = "test" ]; then
        run_test
    elif [ "$command" = "all" ]; then
        run_all_demos
    elif [ -n "$demo_number" ]; then
        run_demo $demo_number
    fi
}

# Run main function
main "$@"