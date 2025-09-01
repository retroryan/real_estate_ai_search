#!/bin/bash

# Elasticsearch Manager Script for Real Estate AI Search
# Manages Elasticsearch operations including indexing, querying, and demos

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${PROJECT_DIR}/.venv"

# Load environment variables
if [ -f "${PROJECT_DIR}/.env" ]; then
    export $(cat "${PROJECT_DIR}/.env" | grep -v '^#' | xargs)
fi

# Functions
print_header() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

activate_venv() {
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        print_info "Virtual environment activated"
    else
        print_error "Virtual environment not found at $VENV_PATH"
        exit 1
    fi
}

check_elasticsearch() {
    print_info "Checking Elasticsearch connection..."
    
    cd "$PROJECT_DIR"
    python -m real_estate_search.management health-check || {
        print_error "Elasticsearch is not accessible at localhost:9200"
        echo "You can start Elasticsearch with:"
        echo "  docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \\"
        echo "    -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" \\"
        echo "    docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
        exit 1
    }
}

clear_indices() {
    print_header "Clearing Elasticsearch Indices"
    
    print_warning "This will delete ALL data from Elasticsearch indices!"
    print_info "Proceeding with clear operation..."
    
    cd "$PROJECT_DIR"
    python -m real_estate_search.management setup-indices --clear
    
    print_success "Indices cleared successfully"
}

setup_indices() {
    print_header "Setting Up Elasticsearch Indices"
    
    print_info "Creating indices with proper mappings..."
    
    cd "$PROJECT_DIR"
    python -m real_estate_search.management setup-indices
    
    print_success "Indices created successfully"
}

load_data_from_pipeline() {
    print_header "Loading Data from SQUACK Pipeline"
    
    local sample_size=${1:-10}
    
    if [ "$sample_size" == "all" ] || [ "$sample_size" == "ALL" ]; then
        print_info "Running SQUACK pipeline with ALL data (no sample limit)"
        
        cd "$PROJECT_DIR"
        
        # Run the pipeline without sample-size parameter to process all data
        python -m squack_pipeline_v2 \
            --elasticsearch \
            --log-level INFO
    else
        print_info "Running SQUACK pipeline with sample size: $sample_size"
        
        cd "$PROJECT_DIR"
        
        # Run the pipeline with Elasticsearch output enabled
        python -m squack_pipeline_v2 \
            --sample-size "$sample_size" \
            --elasticsearch \
            --log-level INFO
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Data loaded successfully from SQUACK pipeline"
    else
        print_error "Failed to load data from SQUACK pipeline"
        exit 1
    fi
}

show_database_stats() {
    print_header "Database Health and Statistics"
    
    cd "$PROJECT_DIR"
    python -m real_estate_search.management stats
}

run_sample_query() {
    print_header "Running Sample Query"
    
    print_info "Executing sample query to verify data..."
    
    cd "$PROJECT_DIR"
    python -m real_estate_search.management sample-query
    
    print_success "Sample query completed"
}

rebuild_full() {
    print_header "Full Elasticsearch Rebuild"
    
    local sample_size=${1:-50}
    
    if [ "$sample_size" == "all" ] || [ "$sample_size" == "ALL" ]; then
        print_warning "This will clear and rebuild all indices with ALL data"
        print_warning "Processing all records may take significant time!"
    else
        print_warning "This will clear and rebuild all indices with $sample_size samples"
    fi
    
    print_info "Proceeding with rebuild..."
    
    # Clear indices
    clear_indices
    
    # Setup indices
    setup_indices
    
    # Load data from pipeline
    load_data_from_pipeline "$sample_size"
    
    # Show final stats
    show_database_stats
    
    print_success "Full rebuild completed successfully!"
}

run_demo() {
    print_header "Running Elasticsearch Demo"
    
    demo_number=${1:-14}
    verbose_flag=${2:-""}
    
    # Build the command
    cmd="cd $PROJECT_DIR && python -m real_estate_search.management demo $demo_number"
    
    # Add verbose flag if requested
    if [ "$verbose_flag" = "--verbose" ]; then
        cmd="$cmd --verbose"
    fi
    
    # Execute the command
    eval $cmd
    
    print_success "Demo completed successfully"
}

# Main menu
show_menu() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Elasticsearch Database Manager                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "1) Health Check         - Check Elasticsearch connection"
    echo "2) Clear Indices        - Remove all data from Elasticsearch"
    echo "3) Setup Indices        - Create indices with proper mappings"
    echo "4) Load Data           - Run SQUACK pipeline to load data"
    echo "5) Rebuild Full        - Clear and rebuild everything"
    echo "6) Run Sample Query    - Execute a sample property search"
    echo "7) Show Statistics     - Display index health and stats"
    echo "8) Run Core Demo       - Run core demonstration queries (1-14)"
    echo "9) Run Hybrid Demo     - Run hybrid/location-aware demos (15-27)"
    echo "10) Quick Setup        - Setup + Load (10 samples)"
    echo "0) Exit"
    echo
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    case "$1" in
        health)
            activate_venv
            check_elasticsearch
            ;;
        clear)
            activate_venv
            clear_indices
            ;;
        setup)
            activate_venv
            setup_indices
            ;;
        load)
            activate_venv
            load_data_from_pipeline "${2:-10}"
            ;;
        rebuild)
            activate_venv
            rebuild_full "${2:-50}"
            ;;
        query)
            activate_venv
            run_sample_query
            ;;
        stats)
            activate_venv
            show_database_stats
            ;;
        demo)
            activate_venv
            if [ -z "$2" ]; then
                echo
                echo "Available demos:"
                echo
                echo "  ${CYAN}=== Core Search Demos ===${NC}"
                echo "  1) Basic Property Search"
                echo "  2) Property Filter Search"
                echo "  3) Geographic Distance Search"
                echo "  4) Neighborhood Statistics"
                echo "  5) Price Distribution Analysis"
                echo "  6) Semantic Similarity Search"
                echo "  7) Multi-Entity Combined Search"
                echo "  8) Wikipedia Article Search"
                echo "  9) Wikipedia Full-Text Search"
                echo "  10) Property Relationships via Denormalized Index"
                echo "  11) Natural Language Semantic Search"
                echo "  12) Natural Language Examples"
                echo "  13) Semantic vs Keyword Comparison"
                echo "  14) 🏡 Rich Real Estate Listing (Default)"
                echo
                echo "  ${CYAN}=== Hybrid & Location-Aware Demos ===${NC}"
                echo "  15) Hybrid Search with RRF"
                echo "  16) Location Understanding (DSPy)"
                echo "  17) 🌊 Location-Aware: Waterfront Luxury"
                echo "  18) 🏫 Location-Aware: Family Schools"
                echo "  19) 🏙️ Location-Aware: Urban Modern"
                echo "  20) 🏔️ Location-Aware: Recreation Mountain"
                echo "  21) 🏛️ Location-Aware: Historic Urban"
                echo "  22) 🏖️ Location-Aware: Beach Proximity"
                echo "  23) 💼 Location-Aware: Investment Market"
                echo "  24) 🌃 Location-Aware: Luxury Urban Views"
                echo "  25) 🏘️ Location-Aware: Suburban Architecture"
                echo "  26) 🏘️ Location-Aware: Neighborhood Character"
                echo "  27) 🎯 Location-Aware Search Showcase (Multiple)"
                echo
                echo "Usage: $0 demo [1-27] [--verbose]"
                echo "Running default demo 14..."
                echo
            fi
            run_demo "${2:-14}" "$3"
            ;;
        quick)
            activate_venv
            setup_indices
            load_data_from_pipeline 10
            show_database_stats
            ;;
        hybrid-demo)
            activate_venv
            if [ -z "$2" ]; then
                echo
                echo "  ${CYAN}=== Hybrid & Location-Aware Demos ===${NC}"
                echo "  15) Hybrid Search with RRF"
                echo "  16) Location Understanding (DSPy)"
                echo "  17) 🌊 Location-Aware: Waterfront Luxury"
                echo "  18) 🏫 Location-Aware: Family Schools"
                echo "  19) 🏙️ Location-Aware: Urban Modern"
                echo "  20) 🏔️ Location-Aware: Recreation Mountain"
                echo "  21) 🏛️ Location-Aware: Historic Urban"
                echo "  22) 🏖️ Location-Aware: Beach Proximity"
                echo "  23) 💼 Location-Aware: Investment Market"
                echo "  24) 🌃 Location-Aware: Luxury Urban Views"
                echo "  25) 🏘️ Location-Aware: Suburban Architecture"
                echo "  26) 🏘️ Location-Aware: Neighborhood Character"
                echo "  27) 🎯 Location-Aware Search Showcase (Multiple)"
                echo
                echo "Usage: $0 hybrid-demo [15-27] [--verbose]"
                echo "Running default hybrid demo 15..."
                echo
            fi
            run_demo "${2:-15}" "$3"
            ;;
        help|--help|-h)
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  health                       Check Elasticsearch connection"
            echo "  clear                        Clear all indices from Elasticsearch"
            echo "  setup                        Setup indices with proper mappings"
            echo "  load [size|all]              Load data from SQUACK pipeline (default: 10)"
            echo "  rebuild [size|all]           Full rebuild (default: 50)"
            echo "  query                        Run sample query"
            echo "  stats                        Show index statistics"
            echo "  demo [num] [--verbose]       Run demo (1-27, default: 14)"
            echo "  hybrid-demo [num] [--verbose] Run hybrid demo (15-27, default: 15)"
            echo "  quick                        Quick setup with 10 samples"
            echo "  help                         Show this help message"
            echo
            echo "Interactive mode: Run without arguments for menu"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
else
    # Interactive mode
    activate_venv
    
    while true; do
        show_menu
        read -p "Enter your choice: " choice
        
        case $choice in
            1)
                check_elasticsearch
                ;;
            2)
                clear_indices
                ;;
            3)
                setup_indices
                ;;
            4)
                read -p "Enter sample size (default: 10, 'all' for full dataset): " size
                load_data_from_pipeline "${size:-10}"
                ;;
            5)
                read -p "Enter sample size for rebuild (default: 50, 'all' for full dataset): " size
                rebuild_full "${size:-50}"
                ;;
            6)
                run_sample_query
                ;;
            7)
                show_database_stats
                ;;
            8)
                echo
                echo "=== Core Search Demos ==="
                echo "  1) Basic Property Search"
                echo "  2) Property Filter Search"
                echo "  3) Geographic Distance Search"
                echo "  4) Neighborhood Statistics"
                echo "  5) Price Distribution Analysis"
                echo "  6) Semantic Similarity Search"
                echo "  7) Multi-Entity Combined Search"
                echo "  8) Wikipedia Article Search"
                echo "  9) Wikipedia Full-Text Search"
                echo "  10) Property Relationships via Denormalized Index"
                echo "  11) Natural Language Semantic Search"
                echo "  12) Natural Language Examples"
                echo "  13) Semantic vs Keyword Comparison"
                echo "  14) 🏡 Rich Real Estate Listing (Default)"
                echo
                read -p "Enter demo number (1-14, default: 14): " demo
                read -p "Verbose output? (y/n, default: n): " verbose
                verbose_flag=""
                if [ "$verbose" = "y" ] || [ "$verbose" = "Y" ]; then
                    verbose_flag="--verbose"
                fi
                run_demo "${demo:-14}" "$verbose_flag"
                ;;
            9)
                echo
                echo "=== Hybrid & Location-Aware Demos ==="
                echo "  15) Hybrid Search with RRF"
                echo "  16) Location Understanding (DSPy)"
                echo "  17) 🌊 Location-Aware: Waterfront Luxury"
                echo "  18) 🏫 Location-Aware: Family Schools"
                echo "  19) 🏙️ Location-Aware: Urban Modern"
                echo "  20) 🏔️ Location-Aware: Recreation Mountain"
                echo "  21) 🏛️ Location-Aware: Historic Urban"
                echo "  22) 🏖️ Location-Aware: Beach Proximity"
                echo "  23) 💼 Location-Aware: Investment Market"
                echo "  24) 🌃 Location-Aware: Luxury Urban Views"
                echo "  25) 🏘️ Location-Aware: Suburban Architecture"
                echo "  26) 🏘️ Location-Aware: Neighborhood Character"
                echo "  27) 🎯 Location-Aware Search Showcase (Multiple)"
                echo
                read -p "Enter demo number (15-27, default: 15): " demo
                read -p "Verbose output? (y/n, default: n): " verbose
                verbose_flag=""
                if [ "$verbose" = "y" ] || [ "$verbose" = "Y" ]; then
                    verbose_flag="--verbose"
                fi
                run_demo "${demo:-15}" "$verbose_flag"
                ;;
            10)
                print_info "Running quick setup..."
                setup_indices
                load_data_from_pipeline 10
                show_database_stats
                ;;
            0)
                print_info "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please try again."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
fi