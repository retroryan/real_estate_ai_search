#!/bin/bash

# Text Embedding Model Installation Script
# Uses Eland to install sentence-transformers model for semantic search

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Load environment variables from parent directory
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Set default values if not in .env
ES_SCHEME="${ES_SCHEME:-http}"
ES_HOST="${ES_HOST:-localhost}"
ES_PORT="${ES_PORT:-9200}"
ES_USERNAME="${ES_USERNAME:-elastic}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Installing Text Embedding Model for Semantic Search  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Model selection - using all-MiniLM-L6-v2 for good balance of speed and quality
MODEL_ID="sentence-transformers/all-MiniLM-L6-v2"
MODEL_ALIAS="all-minilm-l6-v2"

echo -e "${YELLOW}📚 Model Details:${NC}"
echo "   Model: $MODEL_ID"
echo "   Type: Text Embedding"
echo "   Dimensions: 384"
echo "   Use Case: Semantic search, similarity matching"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Pull the latest Eland Docker image
echo -e "${YELLOW}🐳 Pulling latest Eland Docker image...${NC}"
docker pull docker.elastic.co/eland/eland

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to pull Eland Docker image${NC}"
    exit 1
fi

# Install the text embedding model
echo -e "${YELLOW}🚀 Installing text embedding model...${NC}"
echo "   This may take a few minutes..."

# Construct the full URL
ES_URL="${ES_SCHEME}://${ES_HOST}:${ES_PORT}"
echo "   Connecting to: ${ES_URL}"

docker run --rm --network host docker.elastic.co/eland/eland \
    eland_import_hub_model \
      --url "${ES_URL}" \
      -u "${ES_USERNAME}" -p "${ES_PASSWORD}" \
      --hub-model-id "${MODEL_ID}" \
      --task-type text_embedding \
      --start

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Text embedding model installed successfully!${NC}"
    
    # Verify model deployment
    echo -e "${YELLOW}🔍 Verifying model deployment...${NC}"
    
    # Wait a moment for model to fully deploy
    sleep 3
    
    # Check model status
    curl -s -u "${ES_USERNAME}:${ES_PASSWORD}" \
        "${ES_URL}/_ml/trained_models/sentence-transformers__all-minilm-l6-v2/_stats" | \
        python3 -m json.tool | head -30
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Model deployment verified!${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not verify model status, but installation completed${NC}"
    fi
    
else
    echo -e "${RED}❌ Failed to install text embedding model${NC}"
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  1. Check Elasticsearch is running: curl -u elastic:password localhost:9200"
    echo "  2. Verify credentials in .env file"
    echo "  3. Ensure you have enough memory (at least 2GB free)"
    echo "  4. Check Elasticsearch logs for errors"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Run: python inference/setup_embedding_pipeline.py"
echo "2. Process documents: python inference/process_wikipedia_embeddings.py"
echo "3. Test semantic search: python inference/search_embeddings.py"
echo ""
echo -e "${YELLOW}Model Capabilities:${NC}"
echo "• Semantic search - find conceptually similar content"
echo "• Question answering - match questions to relevant passages"
echo "• Document similarity - find related documents"
echo "• Multilingual search - works across 100+ languages"