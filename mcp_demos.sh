#!/bin/bash

# ============================================================================
# MCP Real Estate Demo Runner
# ============================================================================
# 
# This script provides easy access to all MCP demo queries.
# It demonstrates interaction with the MCP server for property searches.
#
# Usage:
#   ./mcp_demos.sh         # List all available demos
#   ./mcp_demos.sh 1       # Run demo number 1
#   ./mcp_demos.sh --help  # Show help
#   ./mcp_demos.sh --list  # List all demos with descriptions
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

# Default demo number
DEFAULT_DEMO=1

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Function to show header
show_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              ${PURPLE}MCP Real Estate Demo Runner${CYAN}                    ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Function to show help
show_help() {
    show_header
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./mcp_demos.sh [options] [demo_number]"
    echo
    echo -e "${GREEN}Options:${NC}"
    echo "  --help, -h     Show this help message"
    echo "  --list, -l     List all available demos"
    echo "  --verbose, -v  Show detailed output"
    echo
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./mcp_demos.sh              # List all demos"
    echo "  ./mcp_demos.sh 1            # Run demo number 1"
    echo "  ./mcp_demos.sh 1 -v         # Run demo 1 with verbose output"
    echo "  ./mcp_demos.sh --list       # Show all available demos"
    echo
    echo -e "${GREEN}Available Demos:${NC}"
    list_demos
}

# Function to list all demos
list_demos() {
    python -m real_estate_search.mcp_demos.main --list
}

# Function to check MCP server
check_mcp_server() {
    echo -e "${YELLOW}Checking MCP server status...${NC}"
    
    # Check if MCP server script exists
    if [ ! -f "start_mcp_server.py" ]; then
        echo -e "${RED}Error: MCP server script not found!${NC}"
        echo "Expected location: $SCRIPT_DIR/start_mcp_server.py"
        return 1
    fi
    
    # Check if Elasticsearch is running
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:9200 | grep -q "200"; then
        echo -e "${RED}Warning: Elasticsearch may not be running on localhost:9200${NC}"
        echo -e "${YELLOW}To start Elasticsearch:${NC}"
        echo "  docker run -d -p 9200:9200 -e 'discovery.type=single-node' \\"
        echo "    -e 'xpack.security.enabled=false' elasticsearch:8.11.0"
        echo
    else
        echo -e "${GREEN}✓ Elasticsearch is accessible${NC}"
    fi
    
    return 0
}

# Function to run a demo
run_demo() {
    local demo_num=$1
    local verbose_flag=$2
    
    echo -e "${GREEN}Running MCP Demo $demo_num...${NC}"
    echo
    
    # Build the command
    cmd="python -m real_estate_search.mcp_demos.main $demo_num"
    
    # Add verbose flag if requested
    if [ "$verbose_flag" = "true" ]; then
        cmd="$cmd --verbose"
    fi
    
    # Execute the command
    eval $cmd
    
    echo
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Main script logic
main() {
    local demo_number=""
    local verbose="false"
    local show_list="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --list|-l)
                show_list="true"
                shift
                ;;
            --verbose|-v)
                verbose="true"
                shift
                ;;
            [0-9]*)
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
    
    # Check MCP server prerequisites
    check_mcp_server
    
    if [ "$show_list" = "true" ] || [ -z "$demo_number" ]; then
        # Show list of demos
        list_demos
        if [ -z "$demo_number" ]; then
            echo
            echo -e "${YELLOW}Tip: Run './mcp_demos.sh <number>' to execute a specific demo${NC}"
        fi
    fi
    
    # Run demo if specified
    if [ -n "$demo_number" ]; then
        # Validate demo number
        if ! [[ "$demo_number" =~ ^[1-9][0-9]*$ ]]; then
            echo -e "${RED}Error: Invalid demo number '$demo_number'${NC}"
            echo "Use --list to see all available demos."
            exit 1
        fi
        
        run_demo $demo_number $verbose
    fi
}

# Run main function
main "$@"