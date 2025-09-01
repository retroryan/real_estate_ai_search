#!/bin/bash

# Elasticsearch Manager Script
# Manages the complete Elasticsearch pipeline for real estate search

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables from parent .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if Elasticsearch is running
check_elasticsearch() {
    print_status "Checking Elasticsearch connection..."
    
    # Build auth parameter if credentials exist
    AUTH=""
    if [ ! -z "$ES_USERNAME" ] && [ ! -z "$ES_PASSWORD" ]; then
        AUTH="-u $ES_USERNAME:$ES_PASSWORD"
    fi
    
    if curl -s $AUTH -X GET "localhost:9200/_cluster/health" > /dev/null 2>&1; then
        print_success "Elasticsearch is running"
        return 0
    else
        print_error "Elasticsearch is not accessible at localhost:9200"
        print_warning "Please start Elasticsearch first"
        echo "  docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
        return 1
    fi
}

# Function to get Elasticsearch stats
get_stats() {
    print_status "Fetching Elasticsearch statistics..."
    
    AUTH=""
    if [ ! -z "$ES_USERNAME" ] && [ ! -z "$ES_PASSWORD" ]; then
        AUTH="-u $ES_USERNAME:$ES_PASSWORD"
    fi
    
    echo ""
    echo "=== Cluster Health ==="
    curl -s $AUTH -X GET "localhost:9200/_cluster/health?pretty" | grep -E '"status"|"number_of_nodes"|"active_primary_shards"'
    
    echo ""
    echo "=== Index Statistics ==="
    echo "Index Name              | Documents | Size"
    echo "------------------------|-----------|----------"
    
    # Get all indices except system indices
    indices=$(curl -s $AUTH -X GET "localhost:9200/_cat/indices?format=json" | jq -r '.[] | select(.index | startswith(".") | not) | .index')
    
    for index in $indices; do
        stats=$(curl -s $AUTH -X GET "localhost:9200/$index/_stats")
        doc_count=$(echo $stats | jq -r '.indices["'$index'"].primaries.docs.count // 0')
        size=$(echo $stats | jq -r '.indices["'$index'"].primaries.store.size_in_bytes // 0')
        size_mb=$(echo "scale=2; $size / 1048576" | bc)
        printf "%-23s | %9s | %8s MB\n" "$index" "$doc_count" "$size_mb"
    done
    
    echo ""
    echo "=== Total Statistics ==="
    total_docs=$(curl -s $AUTH -X GET "localhost:9200/_cat/count?format=json" | jq -r '.[0].count // 0')
    echo "Total Documents: $total_docs"
    
    # Get total size
    total_size=$(curl -s $AUTH -X GET "localhost:9200/_stats" | jq -r '._all.primaries.store.size_in_bytes // 0')
    total_size_mb=$(echo "scale=2; $total_size / 1048576" | bc)
    echo "Total Size: ${total_size_mb} MB"
}

# Function to run a sample query
run_sample_query() {
    print_status "Running sample query..."
    
    AUTH=""
    if [ ! -z "$ES_USERNAME" ] && [ ! -z "$ES_PASSWORD" ]; then
        AUTH="-u $ES_USERNAME:$ES_PASSWORD"
    fi
    
    echo ""
    echo "=== Sample Query: Properties in San Francisco ==="
    
    query='{
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "city": "San Francisco"
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "price": {
                                "gte": 500000,
                                "lte": 2000000
                            }
                        }
                    }
                ]
            }
        },
        "size": 3,
        "_source": ["street_address", "city", "price", "bedrooms", "bathrooms", "square_footage"]
    }'
    
    result=$(curl -s $AUTH -X GET "localhost:9200/properties/_search" -H 'Content-Type: application/json' -d "$query")
    
    # Check if we got results
    total_hits=$(echo $result | jq -r '.hits.total.value // 0')
    
    if [ "$total_hits" -gt 0 ]; then
        echo "Found $total_hits properties. Showing first 3:"
        echo ""
        
        # Parse and display results
        echo "$result" | jq -r '.hits.hits[] | ._source | 
            "Address: \(.street_address), \(.city)\n" +
            "Price: $\(.price | tostring | gsub("(?<a>[0-9])(?=([0-9]{3})+$)"; "\(.a),"))\n" +
            "Bedrooms: \(.bedrooms) | Bathrooms: \(.bathrooms) | Sq Ft: \(.square_footage)\n"'
    else
        print_warning "No properties found in the sample query"
    fi
}

# Function to run the full pipeline
run_full_pipeline() {
    local sample_size="$1"
    
    if [ -n "$sample_size" ]; then
        print_status "Starting pipeline execution with sample size: $sample_size"
    else
        print_status "Starting full pipeline execution (loading all data)..."
    fi
    
    # Check Elasticsearch first
    if ! check_elasticsearch; then
        exit 1
    fi
    
    # Step 1: Setup indices
    print_status "Step 1/4: Setting up Elasticsearch indices..."
    if python -m real_estate_search.management setup-indices --clear; then
        print_success "Indices setup completed"
    else
        print_error "Failed to setup indices"
        exit 1
    fi
    
    # Step 2: Run main pipeline
    print_status "Step 2/4: Running Squack Pipeline v2..."
    if [ -n "$sample_size" ]; then
        print_status "Using sample size: $sample_size"
        if python -m squack_pipeline_v2 --sample-size "$sample_size"; then
            print_success "Pipeline execution completed"
        else
            print_error "Pipeline execution failed"
            exit 1
        fi
    else
        if python -m squack_pipeline_v2; then
            print_success "Pipeline execution completed"
        else
            print_error "Pipeline execution failed"
            exit 1
        fi
    fi
    
    # Step 3: Enrich Wikipedia data
    print_status "Step 3/4: Enriching Wikipedia data..."
    if python -m real_estate_search.management enrich-wikipedia; then
        print_success "Wikipedia enrichment completed"
    else
        print_error "Wikipedia enrichment failed"
        exit 1
    fi
    
    # Step 4: Build relationships
    print_status "Step 4/4: Building index relationships..."
    if python -m real_estate_search.management setup-indices --build-relationships; then
        print_success "Relationships built successfully"
    else
        print_error "Failed to build relationships"
        exit 1
    fi
    
    print_success "Full pipeline execution completed!"
    
    # Show stats and sample query
    echo ""
    echo "========================================"
    echo "         PIPELINE RESULTS"
    echo "========================================"
    
    get_stats
    echo ""
    run_sample_query
}

# Function to show usage
show_usage() {
    echo "Elasticsearch Manager Script - Manages the complete Elasticsearch pipeline for real estate search"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --run [SIZE]   Run complete pipeline: setup indices → run Squack Pipeline v2 → enrich Wikipedia → build relationships"
    echo "                 SIZE: optional sample size (e.g., 10, 100). If omitted, loads all data."
    echo "  --stats        Display Elasticsearch cluster health, index statistics, document counts, and total size"
    echo "  --check        Check if Elasticsearch is accessible at localhost:9200"
    echo "  --sample       Run sample query for San Francisco properties ($500K-$2M range)"
    echo "  --help         Show this help message"
    echo ""
    echo "Pipeline Steps (--run):"
    echo "  1. Setup Elasticsearch indices (clear existing data)"
    echo "  2. Run Squack Pipeline v2 (process properties, neighborhoods, Wikipedia)"
    echo "  3. Enrich Wikipedia data with embeddings"
    echo "  4. Build index relationships"
    echo "  5. Display final statistics and run sample query"
    echo ""
    echo "Examples:"
    echo "  $0 --run       # Execute full pipeline, load all data"
    echo "  $0 --run 10    # Execute pipeline with sample size of 10"
    echo "  $0 --run 100   # Execute pipeline with sample size of 100"
    echo "  $0 --stats     # Show current index stats (documents, size, health)"
    echo "  $0 --check     # Verify Elasticsearch connection"
    echo "  $0 --sample    # Test query: SF properties with price/bedroom filters"
    echo ""
    echo "Requirements:"
    echo "  - Elasticsearch running on localhost:9200"
    echo "  - .env file with API keys (VOYAGE_API_KEY, etc.)"
    echo "  - Python environment with real_estate_search and squack_pipeline_v2 modules"
}

# Main script logic
case "$1" in
    --run)
        # Check if second argument is a number (sample size)
        if [[ "$2" =~ ^[0-9]+$ ]]; then
            run_full_pipeline "$2"
        else
            run_full_pipeline
        fi
        ;;
    --stats)
        if check_elasticsearch; then
            get_stats
        fi
        ;;
    --check)
        check_elasticsearch
        ;;
    --sample)
        if check_elasticsearch; then
            run_sample_query
        fi
        ;;
    --help)
        show_usage
        ;;
    *)
        print_error "Invalid option: $1"
        show_usage
        exit 1
        ;;
esac