#!/bin/bash

# Run correlation integration tests
# This script runs the specific tests for correlation functionality

set -e  # Exit on error

echo "Running correlation integration tests..."
echo "======================================="

# Change to the common_ingest directory
cd "$(dirname "$0")"

echo "Current directory: $(pwd)"

# Check if ChromaDB collection exists
echo "Checking ChromaDB collection..."
if [ -d "data/chroma_db" ]; then
    echo "✓ ChromaDB directory found"
else
    echo "⚠️  ChromaDB directory not found at data/chroma_db"
    echo "   Make sure common_embeddings has created collections"
fi

# Run the correlation tests with verbose output
echo ""
echo "Running correlation tests..."
pytest integration_tests/test_correlation_bronze.py -v -s --tb=short

echo ""
echo "Correlation tests completed!"