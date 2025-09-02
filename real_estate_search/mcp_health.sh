#!/bin/bash

# MCP Server Health Check and Tool Discovery Script
# This script checks the MCP server configuration, services, and available tools
# MUST be run from the real_estate_ai_search directory (project root)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if we're in the correct directory
if [[ ! -f "real_estate_search/mcp_server/main.py" ]]; then
    echo -e "${RED}❌ Error: This script must be run from the real_estate_ai_search directory${NC}"
    echo ""
    echo "Current directory: $(pwd)"
    echo "Expected files: real_estate_search/mcp_server/main.py"
    echo ""
    echo "Please run:"
    echo "  cd /path/to/real_estate_ai_search"
    echo "  ./real_estate_search/mcp_health.sh"
    exit 1
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🏠 MCP Server Health Check & Tool Discovery${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}📍 Project Root:${NC} $(pwd)"
echo ""

# ========================================
# 1. Check Python Installation
# ========================================
echo -e "${YELLOW}1. Python Environment${NC}"
echo "────────────────────────────"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
echo -e "${GREEN}✅ Python version:${NC} $PYTHON_VERSION"

# Check for required packages
echo -n "   Checking FastMCP... "
if python3 -c "import fastmcp" 2>/dev/null; then
    FASTMCP_VERSION=$(python3 -c "import fastmcp; print(getattr(fastmcp, '__version__', 'unknown'))" 2>/dev/null)
    echo -e "${GREEN}✅ Installed${NC} (version: $FASTMCP_VERSION)"
else
    echo -e "${RED}❌ Not installed${NC}"
    echo "   Install with: pip install fastmcp"
fi

echo -n "   Checking Pydantic... "
if python3 -c "import pydantic" 2>/dev/null; then
    PYDANTIC_VERSION=$(python3 -c "import pydantic; print(pydantic.__version__)" 2>/dev/null)
    echo -e "${GREEN}✅ Installed${NC} (version: $PYDANTIC_VERSION)"
else
    echo -e "${RED}❌ Not installed${NC}"
fi

echo ""

# ========================================
# 2. Check Configuration
# ========================================
echo -e "${YELLOW}2. Configuration${NC}"
echo "────────────────────────────"

# Check for .env file
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file:${NC} Found"
    
    # Load environment variables from .env file
    set -a
    source .env
    set +a
    
    # Check for API keys (without showing values)
    if [ -n "$VOYAGE_API_KEY" ]; then
        echo -e "   ${GREEN}✓${NC} VOYAGE_API_KEY is set"
    elif [ -n "$OPENAI_API_KEY" ]; then
        echo -e "   ${GREEN}✓${NC} OPENAI_API_KEY is set"
    elif [ -n "$GOOGLE_API_KEY" ]; then
        echo -e "   ${GREEN}✓${NC} GOOGLE_API_KEY is set"
    else
        echo -e "   ${YELLOW}⚠${NC} No embedding API key found"
    fi
else
    echo -e "${YELLOW}⚠️  .env file:${NC} Not found in project root"
    echo -e "   ${BLUE}💡 Tip:${NC} Create .env file with API keys (see .env.example)"
fi

# Check for config.yaml
CONFIG_FILE="real_estate_search/mcp_server/config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✅ Config file:${NC} $CONFIG_FILE"
    
    # Extract key settings from config
    if command -v grep &> /dev/null; then
        SERVER_NAME=$(grep "server_name:" "$CONFIG_FILE" | cut -d':' -f2 | xargs)
        SERVER_VERSION=$(grep "server_version:" "$CONFIG_FILE" | cut -d':' -f2 | xargs)
        ES_HOST=$(grep "host:" "$CONFIG_FILE" | head -1 | cut -d':' -f2 | xargs)
        ES_PORT=$(grep "port:" "$CONFIG_FILE" | head -1 | cut -d':' -f2 | xargs)
        EMBEDDING_PROVIDER=$(grep "provider:" "$CONFIG_FILE" | cut -d':' -f2 | xargs)
        
        echo -e "   Server: ${CYAN}$SERVER_NAME v$SERVER_VERSION${NC}"
        echo -e "   Elasticsearch: ${CYAN}$ES_HOST:$ES_PORT${NC}"
        echo -e "   Embedding: ${CYAN}$EMBEDDING_PROVIDER${NC}"
    fi
else
    echo -e "${RED}❌ Config file:${NC} Not found at $CONFIG_FILE"
fi

echo ""

# ========================================
# 3. Check Elasticsearch
# ========================================
echo -e "${YELLOW}3. Elasticsearch Status${NC}"
echo "────────────────────────────"

ES_HOST="${ELASTICSEARCH_HOST:-localhost}"
ES_PORT="${ELASTICSEARCH_PORT:-9200}"
ES_URL="http://${ES_HOST}:${ES_PORT}"

echo -n "Testing connection to $ES_URL... "

# Prepare curl authentication options
CURL_AUTH=""
if [ -n "$ES_USERNAME" ] && [ -n "$ES_PASSWORD" ]; then
    CURL_AUTH="-u $ES_USERNAME:$ES_PASSWORD"
elif [ -n "$ELASTICSEARCH_API_KEY" ]; then
    CURL_AUTH="-H 'Authorization: ApiKey $ELASTICSEARCH_API_KEY'"
elif [ -n "$ELASTICSEARCH_CLOUD_ID" ]; then
    CURL_AUTH="-H 'Authorization: ApiKey $ELASTICSEARCH_API_KEY'"
fi

# Test Elasticsearch connectivity with authentication
if [ -n "$CURL_AUTH" ]; then
    HTTP_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/es_response.json $CURL_AUTH "${ES_URL}/_cluster/health" 2>/dev/null || echo "000")
else
    HTTP_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/es_response.json "${ES_URL}/_cluster/health" 2>/dev/null || echo "000")
fi

HTTP_CODE="${HTTP_RESPONSE: -3}"

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Connected${NC}"
    ES_CONNECTED=true
    
    # Get cluster health from response
    if [ -f "/tmp/es_response.json" ]; then
        CLUSTER_STATUS=$(cat /tmp/es_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null)
        NODE_COUNT=$(cat /tmp/es_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('number_of_nodes', 0))" 2>/dev/null)
        
        if [ "$CLUSTER_STATUS" = "green" ]; then
            echo -e "   Cluster Status: ${GREEN}$CLUSTER_STATUS${NC}"
        elif [ "$CLUSTER_STATUS" = "yellow" ]; then
            echo -e "   Cluster Status: ${YELLOW}$CLUSTER_STATUS${NC}"
        else
            echo -e "   Cluster Status: ${RED}$CLUSTER_STATUS${NC}"
        fi
        echo -e "   Nodes: ${CYAN}$NODE_COUNT${NC}"
        
        # Show authentication method used
        if [ -n "$ES_USERNAME" ]; then
            echo -e "   Auth: ${CYAN}Basic (user: $ES_USERNAME)${NC}"
        elif [ -n "$ELASTICSEARCH_API_KEY" ]; then
            echo -e "   Auth: ${CYAN}API Key${NC}"
        else
            echo -e "   Auth: ${CYAN}None (no security)${NC}"
        fi
    fi
    
    # Check indices with authentication
    echo -n "   Checking indices... "
    if [ -n "$CURL_AUTH" ]; then
        INDICES=$(curl -s $CURL_AUTH "${ES_URL}/_cat/indices?format=json" 2>/dev/null)
    else
        INDICES=$(curl -s "${ES_URL}/_cat/indices?format=json" 2>/dev/null)
    fi
    
    if [ -n "$INDICES" ] && [ "$INDICES" != "[]" ]; then
        PROP_COUNT=$(echo "$INDICES" | python3 -c "import sys, json; indices=json.load(sys.stdin); props=[i for i in indices if 'properties' in i.get('index', '')]; print(props[0].get('docs.count', 0) if props else 0)" 2>/dev/null)
        WIKI_COUNT=$(echo "$INDICES" | python3 -c "import sys, json; indices=json.load(sys.stdin); wikis=[i for i in indices if 'wiki' in i.get('index', '')]; print(sum(int(i.get('docs.count', 0)) for i in wikis))" 2>/dev/null)
        
        if [ "$PROP_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✅ Found data${NC}"
            echo -e "      Properties: ${CYAN}$PROP_COUNT documents${NC}"
        else
            echo -e "${YELLOW}⚠️  Empty indices${NC}"
            echo -e "      Properties: ${YELLOW}0 documents${NC}"
            echo -e "      ${BLUE}💡 Run data pipeline to populate indices${NC}"
        fi
        
        if [ "$WIKI_COUNT" -gt 0 ]; then
            echo -e "      Wikipedia: ${CYAN}$WIKI_COUNT documents${NC}"
        else
            echo -e "      Wikipedia: ${YELLOW}0 documents${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No indices found${NC}"
        echo -e "      ${BLUE}💡 Run: python -m data_pipeline${NC}"
    fi
    
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}❌ Authentication failed (401)${NC}"
    echo ""
    echo -e "${BLUE}💡 Authentication Issues:${NC}"
    echo "   • Check ES_USERNAME and ES_PASSWORD"
    echo "   • Check ELASTICSEARCH_API_KEY is valid"
    echo "   • Verify Elasticsearch security is configured correctly"
    ES_CONNECTED=false
    
elif [ "$HTTP_CODE" = "000" ] || [ "$HTTP_CODE" = "" ]; then
    echo -e "${RED}❌ Connection refused${NC}"
    echo ""
    echo -e "${BLUE}💡 Troubleshooting:${NC}"
    echo "   • Elasticsearch is not running on $ES_HOST:$ES_PORT"
    echo "   • Check if Elasticsearch service is started"
    echo ""
    echo -e "${YELLOW}   To start Elasticsearch with Docker:${NC}"
    echo "   docker run -d --name elasticsearch -p 9200:9200 \\"
    echo "     -e 'discovery.type=single-node' \\"
    echo "     -e 'xpack.security.enabled=false' \\"
    echo "     docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
    echo ""
    echo -e "${YELLOW}   To check if Elasticsearch is already running:${NC}"
    echo "   docker ps | grep elasticsearch"
    echo "   curl $ES_URL"
    ES_CONNECTED=false
    
else
    echo -e "${RED}❌ HTTP Error ${HTTP_CODE}${NC}"
    echo ""
    echo -e "${BLUE}💡 Elasticsearch responded with HTTP $HTTP_CODE${NC}"
    if [ -f "/tmp/es_response.json" ]; then
        ERROR_MSG=$(cat /tmp/es_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', {}).get('reason', 'Unknown error'))" 2>/dev/null)
        if [ -n "$ERROR_MSG" ] && [ "$ERROR_MSG" != "Unknown error" ]; then
            echo "   Error: $ERROR_MSG"
        fi
    fi
    ES_CONNECTED=false
fi

# Clean up temporary file
rm -f /tmp/es_response.json

echo ""

# ========================================
# 4. Test MCP Server Initialization
# ========================================
echo -e "${YELLOW}4. MCP Server Test${NC}"
echo "────────────────────────────"

# Create a test Python script to check server initialization
HEALTH_TEST=$(cat << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from real_estate_search.mcp_server.main import MCPServer
    from pathlib import Path
    
    # Try to initialize server
    config_path = Path("real_estate_search/mcp_server/config/config.yaml")
    server = MCPServer(config_path if config_path.exists() else None)
    
    print(f"✅ Server initialized: {server.config.server_name} v{server.config.server_version}")
    
    # Check services
    services_ok = True
    if hasattr(server, 'es_client'):
        print("   ✓ Elasticsearch client ready")
    if hasattr(server, 'embedding_service'):
        print("   ✓ Embedding service ready")
    if hasattr(server, 'property_search_service'):
        print("   ✓ Property search service ready")
    if hasattr(server, 'wikipedia_search_service'):
        print("   ✓ Wikipedia search service ready")
    if hasattr(server, 'health_check_service'):
        print("   ✓ Health check service ready")
    
    # Try to get health status
    try:
        server._initialize_services()
        health = server.health_check_service.perform_health_check()
        print(f"\nHealth Status: {health.status.upper()}")
        for service_name, service_info in health.services.items():
            status = service_info.get('status', 'unknown')
            if status == 'healthy':
                print(f"   ✓ {service_name}: healthy")
            else:
                print(f"   ⚠ {service_name}: {status}")
    except Exception as e:
        print(f"   ⚠ Could not perform health check: {e}")
    
except ImportError as e:
    print(f"❌ Failed to import MCP server: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Server initialization failed: {e}")
    sys.exit(1)
EOF
)

echo "$HEALTH_TEST" | python3 2>&1

echo ""

# ========================================
# 5. Available MCP Tools
# ========================================
echo -e "${YELLOW}5. Available MCP Tools${NC}"
echo "────────────────────────────"

# List the available tools
echo -e "${CYAN}📦 Property Tools:${NC}"
echo "   • search_properties_tool"
echo "     └─ Natural language property search with filters"
echo "   • get_property_details_tool"
echo "     └─ Get detailed information for a specific property"
echo ""

echo -e "${CYAN}📚 Wikipedia Tools:${NC}"
echo "   • search_wikipedia_tool"
echo "     └─ Search Wikipedia for location and topic information"
echo "   • get_wikipedia_article_tool"
echo "     └─ Retrieve complete Wikipedia article by ID"
echo "   • search_wikipedia_by_location_tool"
echo "     └─ Find Wikipedia articles for a specific location"
echo ""

echo -e "${CYAN}🔧 System Tools:${NC}"
echo "   • health_check_tool"
echo "     └─ Check the health status of services"

echo ""

# ========================================
# 6. Summary
# ========================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 Health Check Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Count successes and warnings
SUCCESS_COUNT=0
WARNING_COUNT=0

# Simple summary based on what we found
if command -v python3 &> /dev/null; then
    ((SUCCESS_COUNT++))
else
    ((WARNING_COUNT++))
fi

if [ -f ".env" ] || [ -n "$VOYAGE_API_KEY" ] || [ -n "$OPENAI_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
    ((SUCCESS_COUNT++))
else
    ((WARNING_COUNT++))
fi

if [ -f "$CONFIG_FILE" ]; then
    ((SUCCESS_COUNT++))
else
    ((WARNING_COUNT++))
fi

if curl -s -o /dev/null -w "%{http_code}" "${ES_URL}/_cluster/health" 2>/dev/null | grep -q "200"; then
    ((SUCCESS_COUNT++))
else
    ((WARNING_COUNT++))
fi

echo ""
if [ $WARNING_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ All systems operational!${NC}"
    echo "   The MCP server is ready to use."
else
    echo -e "${YELLOW}⚠️  Some components need attention${NC}"
    echo "   Check the warnings above for details."
fi

echo ""
echo "To start the MCP server, run:"
echo -e "${CYAN}  ./start_mcp_server.sh${NC}"
echo ""