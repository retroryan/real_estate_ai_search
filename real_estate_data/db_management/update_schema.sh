#!/bin/bash

# Database Schema Update Script
# Updates the Wikipedia database with new knowledge graph tables while preserving existing data

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DB_PATH="${PROJECT_ROOT}/data/wikipedia/wikipedia.db"
SCHEMA_FILE="${SCRIPT_DIR}/create_schema.sql"
BACKUP_DIR="${PROJECT_ROOT}/data/backups"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create backup
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/wikipedia_backup_${timestamp}.db"
    
    print_info "Creating backup at ${backup_file}"
    mkdir -p "${BACKUP_DIR}"
    
    if [ -f "${DB_PATH}" ]; then
        cp "${DB_PATH}" "${backup_file}"
        print_success "Backup created successfully"
        echo "${backup_file}"
    else
        print_warning "Database file not found, will create new database"
        echo ""
    fi
}

# Function to check if database exists
check_database() {
    if [ -f "${DB_PATH}" ]; then
        print_info "Database found at ${DB_PATH}"
        return 0
    else
        print_info "Database not found, will be created at ${DB_PATH}"
        mkdir -p "$(dirname "${DB_PATH}")"
        return 1
    fi
}

# Function to get table count
get_table_count() {
    local count=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    echo "${count}"
}

# Function to check if a table exists
table_exists() {
    local table_name=$1
    local exists=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='${table_name}';" 2>/dev/null || echo "0")
    [ "${exists}" = "1" ]
}

# Function to apply schema
apply_schema() {
    print_info "Applying database schema from ${SCHEMA_FILE}"
    
    # Check if schema file exists
    if [ ! -f "${SCHEMA_FILE}" ]; then
        print_error "Schema file not found: ${SCHEMA_FILE}"
        exit 1
    fi
    
    # Apply schema
    if sqlite3 "${DB_PATH}" < "${SCHEMA_FILE}" 2>/tmp/schema_errors.log; then
        print_success "Schema applied successfully"
        return 0
    else
        print_error "Failed to apply schema. Errors:"
        cat /tmp/schema_errors.log
        return 1
    fi
}

# Function to verify schema
verify_schema() {
    print_info "Verifying schema..."
    
    local expected_tables=(
        "locations"
        "articles"
        "page_summaries"
        "ingested_data"
        "flagged_content"
        "removed_content"
        "neighborhoods_enhanced"
        "neighborhood_wiki_relationships"
        "geographic_hierarchy"
        "properties"
        "relationship_cache"
    )
    
    local missing_tables=()
    local existing_tables=()
    
    for table in "${expected_tables[@]}"; do
        if table_exists "${table}"; then
            existing_tables+=("${table}")
        else
            missing_tables+=("${table}")
        fi
    done
    
    # Report results
    echo ""
    echo "Schema Verification Results:"
    echo "============================"
    echo "Existing tables (${#existing_tables[@]}):"
    for table in "${existing_tables[@]}"; do
        echo "  ✓ ${table}"
    done
    
    if [ ${#missing_tables[@]} -gt 0 ]; then
        echo ""
        echo "Missing tables (${#missing_tables[@]}):"
        for table in "${missing_tables[@]}"; do
            echo "  ✗ ${table}"
        done
        print_warning "Some expected tables are missing"
    else
        print_success "All expected tables exist"
    fi
    
    # Check for views
    local view_count=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM sqlite_master WHERE type='view';" 2>/dev/null || echo "0")
    echo ""
    echo "Views created: ${view_count}"
    
    # Check for indexes
    local index_count=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM sqlite_master WHERE type='index';" 2>/dev/null || echo "0")
    echo "Indexes created: ${index_count}"
}

# Function to show usage statistics
show_statistics() {
    print_info "Database statistics:"
    
    if [ -f "${DB_PATH}" ]; then
        echo ""
        echo "Table Row Counts:"
        echo "================="
        
        # Get row counts for main tables
        for table in "articles" "page_summaries" "locations" "neighborhoods_enhanced" "neighborhood_wiki_relationships"; do
            if table_exists "${table}"; then
                local count=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM ${table};" 2>/dev/null || echo "0")
                printf "  %-35s %8s rows\n" "${table}:" "${count}"
            fi
        done
        
        # Database size
        local db_size=$(du -h "${DB_PATH}" | cut -f1)
        echo ""
        echo "Database size: ${db_size}"
    fi
}

# Main execution
main() {
    echo "======================================="
    echo "  Database Schema Update Tool"
    echo "======================================="
    echo ""
    
    # Parse command line arguments
    local skip_backup=false
    local dry_run=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                skip_backup=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-backup    Skip creating backup"
                echo "  --dry-run        Check what would be done without making changes"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Check if dry run
    if [ "${dry_run}" = true ]; then
        print_info "DRY RUN MODE - No changes will be made"
        echo ""
    fi
    
    # Check database
    local db_exists=true
    check_database || db_exists=false
    
    # Get initial table count
    local initial_tables=0
    if [ "${db_exists}" = true ]; then
        initial_tables=$(get_table_count)
        print_info "Current database has ${initial_tables} tables"
    fi
    
    # Create backup if database exists and not skipping
    local backup_file=""
    if [ "${db_exists}" = true ] && [ "${skip_backup}" = false ] && [ "${dry_run}" = false ]; then
        backup_file=$(create_backup)
    elif [ "${skip_backup}" = true ]; then
        print_warning "Skipping backup as requested"
    fi
    
    # Apply schema if not dry run
    if [ "${dry_run}" = false ]; then
        if apply_schema; then
            # Get new table count
            local final_tables=$(get_table_count)
            local new_tables=$((final_tables - initial_tables))
            
            if [ ${new_tables} -gt 0 ]; then
                print_success "Added ${new_tables} new tables"
            else
                print_info "No new tables added (all tables already existed)"
            fi
        else
            print_error "Schema application failed"
            
            # Restore from backup if available
            if [ -n "${backup_file}" ] && [ -f "${backup_file}" ]; then
                print_info "Restoring from backup..."
                cp "${backup_file}" "${DB_PATH}"
                print_success "Database restored from backup"
            fi
            exit 1
        fi
    else
        print_info "Would apply schema from ${SCHEMA_FILE}"
    fi
    
    # Verify schema
    echo ""
    if [ "${dry_run}" = false ]; then
        verify_schema
    else
        print_info "Would verify schema after application"
    fi
    
    # Show statistics
    echo ""
    show_statistics
    
    # Final message
    echo ""
    echo "======================================="
    if [ "${dry_run}" = true ]; then
        print_info "Dry run complete - no changes made"
    else
        print_success "Database schema update complete!"
        if [ -n "${backup_file}" ]; then
            echo ""
            echo "Backup saved at: ${backup_file}"
        fi
    fi
    echo "======================================="
}

# Run main function
main "$@"