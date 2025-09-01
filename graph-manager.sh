#!/bin/bash

# Graph Manager Script for Real Estate AI Search
# Manages Neo4j graph database operations including clearing, rebuilding, and querying

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
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"

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

check_neo4j() {
    print_info "Checking Neo4j connection..."
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main test || {
        print_error "Neo4j is not accessible. Please ensure it's running."
        echo "You can start Neo4j with: docker-compose up -d neo4j"
        exit 1
    }
}

clear_database() {
    print_header "Clearing Neo4j Database"
    
    print_warning "This will delete ALL data from the Neo4j database!"
    print_info "Proceeding with clear operation..."
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main clear
    
    print_success "Database cleared successfully"
}

initialize_database() {
    print_header "Initializing Neo4j Database Schema"
    
    print_info "Creating constraints and indexes..."
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main init
    
    print_success "Database schema initialized"
}

load_data_from_pipeline() {
    print_header "Loading Data from SQUACK Pipeline"
    
    local sample_size=${1:-10}
    
    if [ "$sample_size" == "all" ] || [ "$sample_size" == "ALL" ]; then
        print_info "Running SQUACK pipeline with ALL data (no sample limit)"
        
        cd "$PROJECT_DIR"
        
        # Run the pipeline without sample-size parameter to process all data
        python -m squack_pipeline_v2 \
            --config squack_pipeline_v2/neo4j.config.yaml \
            --log-level INFO
    else
        print_info "Running SQUACK pipeline with sample size: $sample_size"
        
        cd "$PROJECT_DIR"
        
        # Run the pipeline with Neo4j output enabled
        python -m squack_pipeline_v2 \
            --config squack_pipeline_v2/neo4j.config.yaml \
            --sample-size "$sample_size" \
            --log-level INFO
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Data loaded successfully from SQUACK pipeline"
    else
        print_error "Failed to load data from SQUACK pipeline"
        exit 1
    fi
}

build_relationships() {
    print_header "Building Graph Relationships"
    
    print_info "Building relationships in Neo4j..."
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main build-relationships
    
    print_success "Relationships built successfully"
}

run_sample_query() {
    print_header "Running Sample Query"
    
    print_info "Executing sample query to verify data..."
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main sample-query
    
    print_success "Sample query completed"
}

show_database_stats() {
    print_header "Database Health and Statistics"
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main stats-detailed
}

rebuild_full() {
    print_header "Full Database Rebuild"
    
    local sample_size=${1:-50}
    
    if [ "$sample_size" == "all" ] || [ "$sample_size" == "ALL" ]; then
        print_warning "This will clear and rebuild the database with ALL data"
        print_warning "Processing all records may take significant time!"
    else
        print_warning "This will clear and rebuild the database with $sample_size samples"
    fi
    
    print_info "Proceeding with rebuild..."
    
    # Clear database
    clear_database
    
    # Initialize schema
    initialize_database
    
    # Load data from pipeline
    load_data_from_pipeline "$sample_size"
    
    # Build relationships
    build_relationships
    
    # Show final stats
    show_database_stats
    
    print_success "Full rebuild completed successfully!"
}

run_demo() {
    print_header "Running Graph Demo"
    
    demo_number=${1:-1}
    
    cd "$PROJECT_DIR"
    python -m graph_real_estate.main demo --demo "$demo_number"
    
    print_success "Demo completed successfully"
}

# Main menu
show_menu() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Neo4j Graph Database Manager                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "1) Clear Database         - Remove all data from Neo4j"
    echo "2) Initialize Schema      - Create constraints and indexes"
    echo "3) Load Data             - Run SQUACK pipeline to load data"
    echo "4) Build Relationships   - Create graph relationships"
    echo "5) Rebuild Full         - Clear and rebuild everything"
    echo "6) Run Sample Query     - Execute a sample query"
    echo "7) Show Statistics      - Display database health and stats"
    echo "8) Run Demo            - Run demonstration queries"
    echo "9) Quick Setup         - Initialize + Load (10 samples) + Build"
    echo "0) Exit"
    echo
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    case "$1" in
        clear)
            activate_venv
            check_neo4j
            clear_database
            ;;
        init)
            activate_venv
            check_neo4j
            initialize_database
            ;;
        load)
            activate_venv
            check_neo4j
            load_data_from_pipeline "${2:-10}"
            ;;
        build)
            activate_venv
            check_neo4j
            build_relationships
            ;;
        rebuild)
            activate_venv
            check_neo4j
            rebuild_full "${2:-50}"
            ;;
        query)
            activate_venv
            check_neo4j
            run_sample_query
            ;;
        stats)
            activate_venv
            check_neo4j
            show_database_stats
            ;;
        demo)
            activate_venv
            check_neo4j
            if [ -z "$2" ]; then
                echo
                echo "Available demos:"
                echo "  1-7) Various graph demos available in the module"
                echo
                echo "Usage: $0 demo [1-7]"
                echo "Running default demo 1..."
                echo
            fi
            run_demo "${2:-1}"
            ;;
        quick)
            activate_venv
            check_neo4j
            initialize_database
            load_data_from_pipeline 10
            build_relationships
            show_database_stats
            ;;
        help|--help|-h)
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  clear              Clear all data from Neo4j"
            echo "  init               Initialize database schema"
            echo "  load [size|all]    Load data from SQUACK pipeline (default: 10, 'all' for full dataset)"
            echo "  build              Build graph relationships"
            echo "  rebuild [size|all] Full rebuild (default: 50, 'all' for full dataset)"
            echo "  query              Run sample query"
            echo "  stats              Show database statistics"
            echo "  demo [number]      Run demo (1-7, default: 1)"
            echo "  quick              Quick setup with 10 samples"
            echo "  help               Show this help message"
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
    check_neo4j
    
    while true; do
        show_menu
        read -p "Enter your choice: " choice
        
        case $choice in
            1)
                clear_database
                ;;
            2)
                initialize_database
                ;;
            3)
                read -p "Enter sample size (default: 10, 'all' for full dataset): " size
                load_data_from_pipeline "${size:-10}"
                ;;
            4)
                build_relationships
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
                echo "Available demos:"
                echo "  1-7) Various graph demos available in the module"
                echo
                read -p "Enter demo number (1-7, default: 1): " demo
                run_demo "${demo:-1}"
                ;;
            9)
                print_info "Running quick setup..."
                initialize_database
                load_data_from_pipeline 10
                build_relationships
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