#!/bin/bash

# Script to run tests with proper PYTHONPATH configuration
# This ensures editable packages are properly found

# Get the absolute path to the parent directory (real_estate_ai_search)
PARENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Set PYTHONPATH to include the parent directory
export PYTHONPATH="$PARENT_DIR:$PYTHONPATH"

echo "=========================================="
echo "Running tests with PYTHONPATH configuration"
echo "=========================================="
echo "PYTHONPATH includes: $PARENT_DIR"
echo ""

# If no arguments provided, run both unit and integration tests
if [ $# -eq 0 ]; then
    echo "No arguments provided - running all unit and integration tests"
    echo ""
    
    echo "==================== UNIT TESTS ===================="
    echo "Running: python -m pytest -v tests/"
    python -m pytest -v tests/
    unit_exit_code=$?
    
    echo ""
    echo "================== INTEGRATION TESTS ================"
    echo "Running: python -m pytest -v integration_tests/"
    python -m pytest -v integration_tests/
    integration_exit_code=$?
    
    echo ""
    echo "============== CORRELATION INTEGRATION TESTS ========"
    echo "Testing embedding correlation functionality with bronze articles..."
    echo "Running: python -m pytest -v -s integration_tests/test_correlation_bronze.py"
    python -m pytest -v -s integration_tests/test_correlation_bronze.py
    correlation_exit_code=$?
    
    echo ""
    echo "==================== TEST SUMMARY ==================="
    if [ $unit_exit_code -eq 0 ] && [ $integration_exit_code -eq 0 ] && [ $correlation_exit_code -eq 0 ]; then
        echo "✅ All tests passed!"
        echo "  - Unit tests: ✅"
        echo "  - Integration tests: ✅"
        echo "  - Correlation tests: ✅"
        exit 0
    else
        echo "❌ Some tests failed:"
        if [ $unit_exit_code -ne 0 ]; then
            echo "  - Unit tests: ❌ (exit code: $unit_exit_code)"
        else
            echo "  - Unit tests: ✅"
        fi
        if [ $integration_exit_code -ne 0 ]; then
            echo "  - Integration tests: ❌ (exit code: $integration_exit_code)"
        else
            echo "  - Integration tests: ✅"
        fi
        if [ $correlation_exit_code -ne 0 ]; then
            echo "  - Correlation tests: ❌ (exit code: $correlation_exit_code)"
        else
            echo "  - Correlation tests: ✅"
        fi
        exit 1
    fi
else
    # Check if -v flag is already provided
    if [[ " $@ " =~ " -v " ]] || [[ " $@ " =~ " --verbose " ]]; then
        # User already specified verbose, just run as-is
        echo "Running: python -m pytest $@"
        echo "=========================================="
        python -m pytest "$@"
    else
        # Add -v flag for verbose output by default
        echo "Running: python -m pytest -v $@"
        echo "=========================================="
        python -m pytest -v "$@"
    fi
fi