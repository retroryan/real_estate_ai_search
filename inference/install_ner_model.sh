#!/bin/bash

# Load environment variables
source .env

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing NER Model using Eland${NC}"
echo "======================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Pull the latest Eland Docker image
echo -e "${YELLOW}Pulling latest Eland Docker image...${NC}"
docker pull docker.elastic.co/eland/eland

# Install the NER model
echo -e "${YELLOW}Installing DistilBERT NER model...${NC}"

docker run --rm --network host docker.elastic.co/eland/eland \
    eland_import_hub_model \
      --url "${ES_SCHEME}://${ES_HOST}:${ES_PORT}" \
      -u "${ES_USERNAME}" -p "${ES_PASSWORD}" \
      --hub-model-id elastic/distilbert-base-uncased-finetuned-conll03-english \
      --task-type ner \
      --start

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ NER model installed successfully!${NC}"
    
    # Verify model deployment
    echo -e "${YELLOW}Verifying model deployment...${NC}"
    
    curl -s -u "${ES_USERNAME}:${ES_PASSWORD}" \
        "${ES_SCHEME}://${ES_HOST}:${ES_PORT}/_ml/trained_models/elastic__distilbert-base-uncased-finetuned-conll03-english/_stats" | \
        python3 -m json.tool | head -20
    
    echo -e "${GREEN}Model deployment complete!${NC}"
else
    echo -e "${RED}❌ Failed to install NER model${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. The model is now deployed and ready to use"
echo "2. You can test it in Kibana under Machine Learning > Trained Models"
echo "3. Or use the _infer API to test the model programmatically"