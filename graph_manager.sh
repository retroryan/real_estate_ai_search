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
    
    # Test connection using cypher-shell
    if command -v cypher-shell &> /dev/null; then
        echo "RETURN 1;" | cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            print_success "Neo4j is running and accessible"
            return 0
        fi
    fi
    
    # Fallback to Python check
    python -c "
from neo4j import GraphDatabase
import os
try:
    driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    print('Neo4j connection successful')
    exit(0)
except Exception as e:
    print(f'Neo4j connection failed: {e}')
    exit(1)
" || {
        print_error "Neo4j is not accessible. Please ensure it's running."
        echo "You can start Neo4j with: docker-compose up -d neo4j"
        exit 1
    }
}

clear_database() {
    print_header "Clearing Neo4j Database"
    
    print_warning "This will delete ALL data from the Neo4j database!"
    print_info "Proceeding with clear operation..."
    
    print_info "Clearing all nodes and relationships..."
    
    python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

with driver.session() as session:
    # Delete all relationships first
    result = session.run('MATCH ()-[r]->() DELETE r RETURN COUNT(r) as count')
    rel_count = result.single()['count']
    print(f'Deleted {rel_count} relationships')
    
    # Delete all nodes
    result = session.run('MATCH (n) DELETE n RETURN COUNT(n) as count')
    node_count = result.single()['count']
    print(f'Deleted {node_count} nodes')
    
    # Drop all indexes and constraints
    constraints = session.run('SHOW CONSTRAINTS').data()
    for constraint in constraints:
        session.run(f\"DROP CONSTRAINT {constraint['name']}\")
    print(f'Dropped {len(constraints)} constraints')
    
    indexes = session.run('SHOW INDEXES WHERE type <> \"LOOKUP\"').data()
    for index in indexes:
        try:
            session.run(f\"DROP INDEX {index['name']}\")
        except:
            pass  # Some indexes may be tied to constraints
    print(f'Dropped {len(indexes)} indexes')

driver.close()
"
    
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
    
    python -c "
from neo4j import GraphDatabase
import os
import json

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

with driver.session() as session:
    # Sample query: Find properties with their neighborhoods and features
    result = session.run('''
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH p, n
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, n, COLLECT(f.name) as features
        RETURN 
            p.listing_id as listing_id,
            p.price as price,
            p.bedrooms as bedrooms,
            p.bathrooms as bathrooms,
            p.square_feet as sqft,
            n.name as neighborhood,
            features
        LIMIT 3
    ''')
    
    print('\nSample Properties:')
    print('-' * 80)
    for record in result:
        print(f\"Property ID: {record['listing_id']}\")
        print(f\"  Price: \${record['price']:,.0f}\")
        print(f\"  Bedrooms: {record['bedrooms']}, Bathrooms: {record['bathrooms']}\")
        print(f\"  Square Feet: {record['sqft']:,.0f}\")
        print(f\"  Neighborhood: {record['neighborhood']}\")
        if record['features']:
            print(f\"  Features: {', '.join(record['features'][:5])}\")
        print()

driver.close()
"
    
    print_success "Sample query completed"
}

show_database_stats() {
    print_header "Database Health and Statistics"
    
    python -c "
from neo4j import GraphDatabase
import os
from datetime import datetime

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

with driver.session() as session:
    print(f'Database Status Report')
    print(f'Generated: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}')
    print('=' * 60)
    
    # Node counts
    print('\n📊 Node Statistics:')
    node_labels = [
        'Property', 'Neighborhood', 'WikipediaArticle',
        'Feature', 'PropertyType', 'PriceRange',
        'City', 'State', 'ZipCode'
    ]
    
    total_nodes = 0
    for label in node_labels:
        result = session.run(f'MATCH (n:{label}) RETURN COUNT(n) as count')
        count = result.single()['count']
        total_nodes += count
        if count > 0:
            print(f'  {label:20} {count:>10,} nodes')
    
    print(f'  {\"TOTAL\":20} {total_nodes:>10,} nodes')
    
    # Relationship counts
    print('\n🔗 Relationship Statistics:')
    rel_types = [
        'LOCATED_IN', 'HAS_FEATURE', 'IN_CITY', 'IN_STATE',
        'IN_ZIP_CODE', 'TYPE_OF', 'IN_PRICE_RANGE', 'SIMILAR_TO',
        'NEARBY', 'MENTIONED_IN'
    ]
    
    total_rels = 0
    for rel_type in rel_types:
        result = session.run(f'MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count')
        count = result.single()['count']
        total_rels += count
        if count > 0:
            print(f'  {rel_type:20} {count:>10,} relationships')
    
    print(f'  {\"TOTAL\":20} {total_rels:>10,} relationships')
    
    # Constraints and Indexes
    print('\n🔐 Constraints:')
    constraints = session.run('SHOW CONSTRAINTS').data()
    for constraint in constraints[:5]:  # Show first 5
        print(f\"  • {constraint['name']}\")
    if len(constraints) > 5:
        print(f'  ... and {len(constraints) - 5} more')
    
    print('\n🔍 Indexes:')
    indexes = session.run('SHOW INDEXES WHERE type <> \"LOOKUP\"').data()
    for index in indexes[:5]:  # Show first 5
        print(f\"  • {index['name']} ({index['state']})\")
    if len(indexes) > 5:
        print(f'  ... and {len(indexes) - 5} more')
    
    # Database size estimate
    result = session.run('''
        CALL apoc.meta.stats()
        YIELD nodeCount, relCount, labelCount, relTypeCount
        RETURN nodeCount, relCount, labelCount, relTypeCount
    ''').single()
    
    if result:
        print('\n📈 Database Metrics:')
        print(f'  Node Count:          {result[\"nodeCount\"]:>10,}')
        print(f'  Relationship Count:  {result[\"relCount\"]:>10,}')
        print(f'  Label Count:         {result[\"labelCount\"]:>10,}')
        print(f'  Rel Type Count:      {result[\"relTypeCount\"]:>10,}')
    
    # Health check
    print('\n✅ Health Status:')
    if total_nodes > 0:
        print('  Database:     HEALTHY')
        print('  Connectivity: OK')
        print(f'  Data Present: YES ({total_nodes:,} nodes)')
    else:
        print('  Database:     EMPTY')
        print('  Connectivity: OK')
        print('  Data Present: NO')

driver.close()
" 2>/dev/null || {
    # Fallback if APOC is not installed
    python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

with driver.session() as session:
    # Basic stats without APOC
    result = session.run('MATCH (n) RETURN COUNT(n) as nodes')
    nodes = result.single()['nodes']
    
    result = session.run('MATCH ()-[r]->() RETURN COUNT(r) as rels')
    rels = result.single()['rels']
    
    print('\n📊 Database Summary:')
    print(f'  Total Nodes:         {nodes:>10,}')
    print(f'  Total Relationships: {rels:>10,}')
    
    if nodes > 0:
        print('\n✅ Database Status: HEALTHY')
    else:
        print('\n⚠️  Database Status: EMPTY')

driver.close()
"
}
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
    
    case "$demo_number" in
        1)
            print_info "Demo 1: Basic Property Search"
            python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

print('\\n🔍 Finding properties with 3+ bedrooms and < \$1M...')
with driver.session() as session:
    result = session.run('''
        MATCH (p:Property)
        WHERE p.bedrooms >= 3 AND p.price < 1000000
        RETURN p.listing_id as id, p.price as price, 
               p.bedrooms as beds, p.bathrooms as baths,
               p.square_feet as sqft
        ORDER BY p.price DESC
        LIMIT 5
    ''')
    
    for record in result:
        print(f'  ID: {record[\"id\"]} | Price: \${record[\"price\"]:,.0f} | {record[\"beds\"]} beds/{record[\"baths\"]} baths | {record[\"sqft\"]:,} sqft')

driver.close()
"
            ;;
        2)
            print_info "Demo 2: Neighborhood Analysis"
            python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

print('\\n🏘️ Neighborhood property counts...')
with driver.session() as session:
    result = session.run('''
        MATCH (n:Neighborhood)<-[:LOCATED_IN]-(p:Property)
        RETURN n.name as neighborhood, COUNT(p) as property_count
        ORDER BY property_count DESC
        LIMIT 5
    ''')
    
    for record in result:
        print(f'  {record[\"neighborhood\"]}: {record[\"property_count\"]} properties')

driver.close()
"
            ;;
        3)
            print_info "Demo 3: Feature Analysis"
            python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

print('\\n✨ Most common property features (by occurrence count)...')
with driver.session() as session:
    result = session.run('''
        MATCH (p:Property) 
        WHERE p.features IS NOT NULL 
        UNWIND p.features as feature 
        RETURN feature, COUNT(*) as count 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    
    for record in result:
        print(f'  {record[\"feature\"]}: {record[\"count\"]} properties')

print('\\n🏠 Properties with most features...')
with driver.session() as session:
    result = session.run('''
        MATCH (p:Property)
        WHERE p.features IS NOT NULL
        RETURN p.listing_id as id, SIZE(p.features) as feature_count, p.features[0..3] as sample_features
        ORDER BY feature_count DESC
        LIMIT 5
    ''')
    
    for record in result:
        sample = ', '.join(record['sample_features'][:3]) + ('...' if len(record['sample_features']) > 3 else '')
        print(f'  {record[\"id\"]}: {record[\"feature_count\"]} features (e.g., {sample})')

driver.close()
"
            ;;
        4)
            print_info "Demo 4: Price Range Distribution"
            python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

print('\\n💰 Price range distribution...')
with driver.session() as session:
    result = session.run('''
        MATCH (pr:PriceRange)<-[:IN_PRICE_RANGE]-(p:Property)
        WITH pr.min_price as min_price, pr.max_price as max_price, COUNT(p) as count
        ORDER BY min_price
        RETURN 
            '\$' + toString(min_price/1000) + 'K - \$' + toString(max_price/1000) + 'K' as range,
            count
    ''')
    
    for record in result:
        print(f'  {record[\"range\"]}: {record[\"count\"]} properties')

print('\\n📊 Average price by property type...')
with driver.session() as session:
    result = session.run('''
        MATCH (pt:PropertyType)<-[:TYPE_OF]-(p:Property)
        RETURN pt.type_name as type, 
               COUNT(p) as count,
               AVG(p.price) as avg_price
        ORDER BY avg_price DESC
    ''')
    
    for record in result:
        avg = record[\"avg_price\"] or 0
        print(f'  {record[\"type\"]}: {record[\"count\"]} properties (avg: \${avg:,.0f})')

driver.close()
"
            ;;
        5)
            print_info "Demo 5: Geographic Distribution"
            python -c "
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

print('\\n🗺️ Properties by city...')
with driver.session() as session:
    result = session.run('''
        MATCH (c:City)<-[:IN_CITY]-(p:Property)
        RETURN c.name as city, COUNT(p) as count, 
               AVG(p.price) as avg_price
        ORDER BY count DESC
    ''')
    
    for record in result:
        avg = record[\"avg_price\"] or 0
        print(f'  {record[\"city\"]}: {record[\"count\"]} properties (avg: \${avg:,.0f})')

driver.close()
"
            ;;
        6)
            print_info "Demo 6: Vector Similarity Search (Advanced)"
            python -c "
from neo4j import GraphDatabase
import os
import random

driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', os.getenv('NEO4J_PASSWORD')))

# Check if embeddings exist
with driver.session() as session:
    result = session.run('MATCH (p:Property) WHERE p.embedding IS NOT NULL RETURN COUNT(p) as count')
    embedding_count = result.single()['count']
    
    if embedding_count == 0:
        print('\\n⚠️  No embeddings found in database!')
        print('To generate embeddings, run:')
        print('  ./graph_manager.sh load 10  # with VOYAGE_API_KEY set')
        print('\\nShowing similar properties by features instead...')
        
        # Alternative: Find similar by shared features
        result = session.run('''
            MATCH (p1:Property)
            WHERE p1.features IS NOT NULL AND SIZE(p1.features) > 3
            WITH p1, p1.features as features1
            ORDER BY rand()
            LIMIT 1
            MATCH (p2:Property)
            WHERE p2.listing_id <> p1.listing_id 
              AND p2.features IS NOT NULL
            WITH p1, features1, p2, p2.features as features2
            WITH p1, p2, features1, features2,
                 [f IN features1 WHERE f IN features2] as shared
            WHERE SIZE(shared) > 2
            RETURN p1.listing_id as base_id, 
                   p1.price as base_price,
                   p1.bedrooms as base_beds,
                   SIZE(features1) as base_features,
                   p2.listing_id as similar_id,
                   p2.price as similar_price,
                   p2.bedrooms as similar_beds,
                   SIZE(shared) as shared_features
            ORDER BY shared_features DESC
            LIMIT 5
        ''')
        
        records = list(result)
        if records:
            first = records[0]
            print(f'\\n🏠 Base Property: {first[\"base_id\"]}')
            print(f'   Price: \${first[\"base_price\"]:,.0f} | {first[\"base_beds\"]} beds | {first[\"base_features\"]} features')
            print('\\n🔍 Similar properties (by shared features):')
            for r in records:
                print(f'   {r[\"similar_id\"]}: \${r[\"similar_price\"]:,.0f} | {r[\"similar_beds\"]} beds | {r[\"shared_features\"]} shared features')
    else:
        print(f'\\n✅ Found {embedding_count} properties with embeddings')
        
        # Pick a random property and find similar ones using vector similarity
        result = session.run('''
            MATCH (p1:Property)
            WHERE p1.embedding IS NOT NULL
            WITH p1
            ORDER BY rand()
            LIMIT 1
            CALL db.index.vector.queryNodes(
                'property_embedding', 
                5, 
                p1.embedding
            ) YIELD node as p2, score
            WHERE p2.listing_id <> p1.listing_id
            RETURN p1.listing_id as base_id,
                   p1.price as base_price,
                   p1.bedrooms as base_beds,
                   p1.square_feet as base_sqft,
                   p2.listing_id as similar_id,
                   p2.price as similar_price,
                   p2.bedrooms as similar_beds,
                   p2.square_feet as similar_sqft,
                   score
            ORDER BY score DESC
        ''')
        
        records = list(result)
        if records:
            first = records[0]
            print(f'\\n🏠 Base Property: {first[\"base_id\"]}')
            print(f'   Price: \${first[\"base_price\"]:,.0f} | {first[\"base_beds\"]} beds | {first[\"base_sqft\"]:,} sqft')
            print('\\n🔍 Similar properties (by vector similarity):')
            for r in records:
                print(f'   {r[\"similar_id\"]}: \${r[\"similar_price\"]:,.0f} | {r[\"similar_beds\"]} beds | {r[\"similar_sqft\"]:,} sqft | Score: {r[\"score\"]:.3f}')

driver.close()
"
            ;;
        *)
            print_error "Invalid demo number. Please choose 1-6"
            return 1
            ;;
    esac
    
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
                echo "  1) Basic Property Search    - Find properties by criteria"
                echo "  2) Neighborhood Analysis    - Property counts by neighborhood"
                echo "  3) Feature Analysis         - Most common property features"
                echo "  4) Price Range Distribution - Properties by price brackets"
                echo "  5) Geographic Distribution  - Properties by city with avg prices"
                echo "  6) Vector Similarity Search - Find similar properties (Advanced)"
                echo
                echo "Usage: $0 demo [1-6]"
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
            echo "  demo [number]      Run demo (1-6, default: 1)"
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
                echo "  1) Basic Property Search    - Find properties by criteria"
                echo "  2) Neighborhood Analysis    - Property counts by neighborhood"
                echo "  3) Feature Analysis         - Most common property features"
                echo "  4) Price Range Distribution - Properties by price brackets"
                echo "  5) Geographic Distribution  - Properties by city with avg prices"
                echo "  6) Vector Similarity Search - Find similar properties (Advanced)"
                echo
                read -p "Enter demo number (1-6, default: 1): " demo
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