#!/usr/bin/env python3
"""
Test script for Wikipedia search with automatic location extraction.
Tests Phase 1 implementation of location extraction in Wikipedia search.
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {env_path}")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from elasticsearch import Elasticsearch
from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
from real_estate_search.mcp_server.services.elasticsearch_client import ElasticsearchClient
from real_estate_search.mcp_server.models.search import WikipediaSearchRequest
from real_estate_search.mcp_server.settings import MCPServerConfig
from real_estate_search.embeddings import QueryEmbeddingService
from real_estate_search.config import AppConfig


def test_wikipedia_search():
    """Test Wikipedia search with automatic location extraction."""
    
    print("\n" + "="*80)
    print("TESTING WIKIPEDIA SEARCH WITH LOCATION EXTRACTION")
    print("="*80)
    
    # Initialize configuration
    app_config = AppConfig.load()
    mcp_config = MCPServerConfig()
    
    # Initialize Elasticsearch client
    es_config = app_config.elasticsearch.get_client_config()
    es = Elasticsearch(**es_config)
    es_client = ElasticsearchClient(mcp_config)
    es_client.client = es  # Use the properly configured client
    
    # Initialize embedding service
    embedding_service = QueryEmbeddingService(config=app_config.embedding)
    embedding_service.initialize()
    
    # Initialize Wikipedia search service
    wiki_service = WikipediaSearchService(
        config=mcp_config,
        es_client=es_client,
        embedding_service=embedding_service
    )
    
    # Test queries with locations
    test_queries = [
        "museums in San Francisco",
        "parks in Oakland",
        "Temescal neighborhood history",
        "Golden Gate Bridge construction",
        "restaurants in SOMA",
        "Berkeley campus buildings",
        "Silicon Valley tech companies",
        "Napa Valley wineries"
    ]
    
    print("\nTesting location extraction in Wikipedia search:")
    print("-" * 60)
    
    for query in test_queries:
        print(f"\n📍 Query: '{query}'")
        
        try:
            # Create search request
            request = WikipediaSearchRequest(
                query=query,
                search_in="full",
                size=3,
                search_type="hybrid"
            )
            
            # Execute search
            response = wiki_service.search(request)
            
            print(f"   Total results: {response.metadata.total_hits}")
            print(f"   Execution time: {response.metadata.execution_time_ms}ms")
            
            if response.results:
                print("   Top results:")
                for i, result in enumerate(response.results[:3], 1):
                    title = result.get('title', 'Unknown')
                    score = result.get('_score', 0)
                    print(f"     {i}. {title} (score: {score:.2f})")
            else:
                print("   No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Clean up
    embedding_service.close()
    
    print("\n" + "="*80)
    print("✅ Test completed!")
    print("="*80)


if __name__ == "__main__":
    test_wikipedia_search()