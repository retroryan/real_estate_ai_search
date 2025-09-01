#!/bin/bash

# Set up paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Run integration tests
echo "Running Squack Pipeline V2 Integration Tests..."
echo "----------------------------------------"
pytest squack_pipeline_v2/integration_tests/ -v