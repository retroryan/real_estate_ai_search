#!/bin/bash

# Start the Real Estate MCP Server
# This script provides a convenient way to start the MCP server with proper environment setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏠 Real Estate Search MCP Server${NC}"
echo "=========================================="

# Get script directory (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}Working directory: $SCRIPT_DIR${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python version: ${PYTHON_VERSION}${NC}"

# Check for .env file in current directory
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Found .env file${NC}"
    # Export environment variables from .env file
    set -a
    source "$ENV_FILE"
    set +a
else
    echo -e "${YELLOW}⚠️  No .env file found${NC}"
    echo "   API keys should be set as environment variables"
    echo "   Create .env file with: VOYAGE_API_KEY=your-key-here"
fi

# Check if Elasticsearch is running
ES_HOST="${ELASTICSEARCH_HOST:-localhost}"
ES_PORT="${ELASTICSEARCH_PORT:-9200}"
ES_USERNAME="${ELASTICSEARCH_USERNAME:-}"
ES_PASSWORD="${ELASTICSEARCH_PASSWORD:-}"

echo -n "Checking Elasticsearch at ${ES_HOST}:${ES_PORT}... "

# Build curl authentication if credentials are available
AUTH_ARGS=""
if [ -n "$ES_USERNAME" ] && [ -n "$ES_PASSWORD" ]; then
    AUTH_ARGS="-u ${ES_USERNAME}:${ES_PASSWORD}"
fi

if curl -s -o /dev/null -w "%{http_code}" $AUTH_ARGS "http://${ES_HOST}:${ES_PORT}/_cluster/health" 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✅ Connected${NC}"
    
    # Check if indices exist
    echo -n "Checking indices... "
    if curl -s $AUTH_ARGS "http://${ES_HOST}:${ES_PORT}/_cat/indices" 2>/dev/null | grep -q "properties"; then
        PROPERTY_COUNT=$(curl -s $AUTH_ARGS "http://${ES_HOST}:${ES_PORT}/properties/_count" 2>/dev/null | grep -o '"count":[0-9]*' | cut -d':' -f2)
        if [ -n "$PROPERTY_COUNT" ]; then
            echo -e "${GREEN}✅ Properties index found (${PROPERTY_COUNT} documents)${NC}"
        else
            echo -e "${GREEN}✅ Properties index found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Properties index not found${NC}"
        echo "   Run data pipeline to create and populate indices"
    fi
else
    echo -e "${YELLOW}⚠️  Cannot connect to Elasticsearch${NC}"
    echo "   The server will start but may not function properly"
    echo ""
    if [ -z "$ES_USERNAME" ] || [ -z "$ES_PASSWORD" ]; then
        echo "   Note: No Elasticsearch credentials found in .env file"
        echo "   Add ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD to .env if needed"
        echo ""
    fi
    echo "   To start Elasticsearch with Docker:"
    echo "   docker run -d --name elasticsearch -p 9200:9200 \\"
    echo "     -e 'discovery.type=single-node' \\"
    echo "     -e 'xpack.security.enabled=false' \\"
    echo "     docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
fi

# Check for required Python packages
echo -n "Checking required packages... "
if python3 -c "import fastmcp" 2>/dev/null; then
    echo -e "${GREEN}✅ FastMCP installed${NC}"
else
    echo -e "${YELLOW}⚠️  FastMCP not installed${NC}"
    echo "   Install with: pip install fastmcp"
fi

# Check for config file
CONFIG_FILE="real_estate_search/mcp_server/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✅ Found config file: ${CONFIG_FILE}${NC}"
    CONFIG_ARG="$CONFIG_FILE"
else
    echo -e "${YELLOW}⚠️  Using default configuration${NC}"
    CONFIG_ARG=""
fi

echo "=========================================="
echo -e "${GREEN}Starting MCP Server...${NC}"
echo ""

# Run the MCP server module
if [ -n "$CONFIG_ARG" ]; then
    python3 -m real_estate_search.mcp_server.main --config "$CONFIG_ARG"
else
    python3 -m real_estate_search.mcp_server.main
fi