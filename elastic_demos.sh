#!/bin/bash

# ============================================================================
# Elasticsearch Real Estate Demo Runner
# ============================================================================
# 
# This script provides easy access to all Elasticsearch demo queries.
# It automatically loads authentication from .env file.
#
# Usage:
#   ./elastic_demos.sh         # Run default demo (14 - Rich Property Listing)
#   ./elastic_demos.sh 5       # Run demo number 5
#   ./elastic_demos.sh --help  # Show all available demos
#   ./elastic_demos.sh --list  # List all demos with descriptions
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

# Default demo number (Rich Property Listing)
DEFAULT_DEMO=14

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please ensure .env file exists with Elasticsearch credentials."
    exit 1
fi

# Verify Elasticsearch credentials are set
if [ -z "$ES_PASSWORD" ]; then
    echo -e "${RED}Error: Elasticsearch password not found in .env!${NC}"
    echo "Please set ES_PASSWORD in .env file."
    exit 1
fi

# Function to show header
show_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ${PURPLE}Elasticsearch Real Estate Demo Runner${CYAN}              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Function to show help
show_help() {
    show_header
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./elastic_demos.sh [options] [demo_number]"
    echo
    echo -e "${GREEN}Options:${NC}"
    echo "  --help, -h     Show this help message"
    echo "  --list, -l     List all available demos"
    echo "  --verbose, -v  Show detailed query DSL"
    echo
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./elastic_demos.sh              # Run default demo (14)"
    echo "  ./elastic_demos.sh 5            # Run demo number 5"
    echo "  ./elastic_demos.sh 14 -v        # Run demo 14 with verbose output"
    echo "  ./elastic_demos.sh --list       # Show all available demos"
    echo
    echo -e "${GREEN}Available Demos:${NC}"
    list_demos
}

# Function to list all demos
list_demos() {
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE} #  │ Demo Name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo " 1  │ Basic Property Search"
    echo " 2  │ Property Filter Search"
    echo " 3  │ Geographic Distance Search"
    echo " 4  │ Neighborhood Statistics"
    echo " 5  │ Price Distribution Analysis"
    echo " 6  │ Semantic Similarity Search"
    echo " 7  │ Multi-Entity Combined Search"
    echo " 8  │ Wikipedia Article Search"
    echo " 9  │ Wikipedia Full-Text Search"
    echo " 10 │ Property Relationships via Denormalized Index"
    echo " 11 │ Natural Language Semantic Search"
    echo " 12 │ Natural Language Examples"
    echo " 13 │ Semantic vs Keyword Comparison"
    echo -e "${GREEN} 14 │ 🏡 Rich Real Estate Listing (Single Query) [DEFAULT]${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to run a demo
run_demo() {
    local demo_num=$1
    local verbose_flag=$2
    
    echo -e "${GREEN}Running Demo $demo_num...${NC}"
    echo
    
    # Build the command
    cmd="python -m real_estate_search.management demo $demo_num"
    
    # Add verbose flag if requested
    if [ "$verbose_flag" = "true" ]; then
        cmd="$cmd --verbose"
    fi
    
    # Execute the command
    eval $cmd
    
    # Check if it's demo 14 and show HTML file location
    if [ "$demo_num" = "14" ]; then
        echo
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}📄 HTML Report:${NC}"
        
        # Find the latest HTML file
        latest_html=$(ls -t real_estate_search/html_results/property_listing_*.html 2>/dev/null | head -1)
        
        if [ -n "$latest_html" ]; then
            echo -e "   File: ${BLUE}$latest_html${NC}"
            echo -e "   ${YELLOW}To open in browser:${NC}"
            echo -e "   open $latest_html"
        fi
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

# Main script logic
main() {
    local demo_number=""
    local verbose="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --list|-l)
                show_header
                list_demos
                exit 0
                ;;
            --verbose|-v)
                verbose="true"
                shift
                ;;
            [0-9]|1[0-4])
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
    
    # Use default demo if none specified
    if [ -z "$demo_number" ]; then
        demo_number=$DEFAULT_DEMO
        echo -e "${YELLOW}No demo specified. Running default demo $DEFAULT_DEMO (Rich Property Listing)${NC}"
        echo
    fi
    
    # Validate demo number
    if ! [[ "$demo_number" =~ ^[1-9]$|^1[0-4]$ ]]; then
        echo -e "${RED}Error: Invalid demo number '$demo_number'${NC}"
        echo "Valid demo numbers are 1-14. Use --list to see all demos."
        exit 1
    fi
    
    show_header
    run_demo $demo_number $verbose
}

# Run main function
main "$@"