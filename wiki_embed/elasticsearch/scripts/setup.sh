#!/bin/bash
# Simple Elasticsearch setup script for testing
# This sets up a single-node Elasticsearch instance suitable for development/testing

echo "🔍 Setting up Elasticsearch for testing..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop and remove existing container if it exists
echo "🧹 Cleaning up existing Elasticsearch container..."
docker stop elasticsearch-test 2>/dev/null || true
docker rm elasticsearch-test 2>/dev/null || true

# Start Elasticsearch container
echo "🚀 Starting Elasticsearch container..."
docker run -d \
  --name elasticsearch-test \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "xpack.security.enrollment.enabled=false" \
  -e "xpack.security.http.ssl.enabled=false" \
  -e "xpack.security.transport.ssl.enabled=false" \
  -e "cluster.routing.allocation.disk.threshold_enabled=false" \
  elasticsearch:8.11.0

# Wait for Elasticsearch to be ready
echo "⏳ Waiting for Elasticsearch to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:9200 >/dev/null 2>&1; then
        echo "✅ Elasticsearch is ready!"
        break
    fi
    echo "   Attempt $i/30... waiting 2 seconds"
    sleep 2
done

# Verify Elasticsearch is working
echo "🔍 Testing Elasticsearch connection..."
if curl -s http://localhost:9200 | grep -q "elasticsearch"; then
    echo "✅ Elasticsearch is running successfully!"
    echo ""
    echo "📊 Elasticsearch Info:"
    curl -s http://localhost:9200 | jq '.' 2>/dev/null || curl -s http://localhost:9200
    echo ""
    echo "🎯 Elasticsearch is ready for testing at: http://localhost:9200"
    echo ""
    echo "To stop Elasticsearch: docker stop elasticsearch-test"
    echo "To restart Elasticsearch: docker start elasticsearch-test"
    echo "To remove Elasticsearch: docker stop elasticsearch-test && docker rm elasticsearch-test"
else
    echo "❌ Elasticsearch failed to start properly"
    echo "Container logs:"
    docker logs elasticsearch-test
    exit 1
fi