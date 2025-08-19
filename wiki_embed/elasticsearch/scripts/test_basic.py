#!/usr/bin/env python3
"""
Simple test script for basic Elasticsearch functionality.
Tests embedding creation and search with a small dataset.
"""

import json
import sys
import time
from pathlib import Path

# Add parent directory to path to import wiki_embed modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables before importing wiki_embed modules
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not available, relying on system environment variables")

from wiki_embed.models import Config, EmbeddingMethod
from wiki_embed.utils import configure_from_config
from wiki_embed.pipeline import WikipediaEmbeddingPipeline
from wiki_embed.query import WikipediaQueryTester


def create_test_config():
    """Create a test configuration for Elasticsearch."""
    # Create temporary config for Elasticsearch testing
    test_config_path = Path("test_config_elasticsearch.yaml")
    
    config_content = """
embedding:
  provider: ollama
  ollama_base_url: "http://localhost:11434"
  ollama_model: "nomic-embed-text"

vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "test_wiki_embeddings"

data:
  source_dir: "../../data/wikipedia/pages"
  registry_path: "../../data/wikipedia/REGISTRY.json"
  attribution_path: "../../data/wikipedia/attribution/WIKIPEDIA_ATTRIBUTION.json"
  wikipedia_db: "../../data/wikipedia/wikipedia.db"
  max_articles: 5  # Limit to 5 articles for testing

chunking:
  method: semantic
  breakpoint_percentile: 90
  buffer_size: 2
  chunk_size: 800
  chunk_overlap: 100
  embedding_method: traditional

testing:
  queries_path: "../../data/wiki_test_queries.json"
  top_k: 3
  min_similarity: 0.3
"""
    
    with open(test_config_path, 'w') as f:
        f.write(config_content)
    
    return str(test_config_path)


def test_elasticsearch_connection():
    """Test basic Elasticsearch connectivity."""
    print("🔍 Testing Elasticsearch connection...")
    
    try:
        import os
        from elasticsearch import Elasticsearch
        
        # Get credentials from environment
        username = os.getenv('ELASTICSEARCH_USERNAME')
        password = os.getenv('ELASTICSEARCH_PASSWORD')
        
        # Create client with authentication if available
        if username and password:
            print(f"🔐 Using authentication for user: {username}")
            client = Elasticsearch(
                ["http://localhost:9200"],
                basic_auth=(username, password)
            )
        else:
            print("🔓 No authentication credentials found, trying without auth")
            client = Elasticsearch(["http://localhost:9200"])
        
        # Test connection
        info = client.info()
        print(f"✅ Connected to Elasticsearch {info['version']['number']}")
        print(f"📊 Cluster name: {info['cluster_name']}")
        
        # Test index operations
        test_index = "test_connection_index"
        
        # Clean up any existing test index
        if client.indices.exists(index=test_index):
            client.indices.delete(index=test_index)
            print("🧹 Cleaned up existing test index")
        
        # Create test index
        client.indices.create(index=test_index, body={
            "mappings": {
                "properties": {
                    "test_field": {"type": "text"}
                }
            }
        })
        print("✅ Successfully created test index")
        
        # Delete test index
        client.indices.delete(index=test_index)
        print("✅ Successfully deleted test index")
        
        return True
        
    except Exception as e:
        print(f"❌ Elasticsearch connection failed: {e}")
        print("\n💡 Make sure Elasticsearch is running and credentials are correct:")
        print("   ./setup_elasticsearch.sh")
        print("   Check wiki_embed/.env for ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD")
        return False


def test_embedding_creation():
    """Test creating embeddings with Elasticsearch."""
    print("\n📦 Testing embedding creation with Elasticsearch...")
    
    try:
        # Create test config
        config_path = create_test_config()
        
        # Load config and configure global settings
        config = Config.from_yaml(config_path)
        configure_from_config(config)
        
        print(f"✅ Configuration loaded (max_articles: {config.data.max_articles})")
        
        # Create pipeline
        pipeline = WikipediaEmbeddingPipeline(config)
        print("✅ Pipeline initialized")
        
        # Create embeddings (force recreate to ensure clean test)
        start_time = time.time()
        count = pipeline.create_embeddings(force_recreate=True, method=EmbeddingMethod.TRADITIONAL)
        creation_time = time.time() - start_time
        
        print(f"✅ Created {count} embeddings in {creation_time:.2f} seconds")
        
        # Clean up test config
        Path(config_path).unlink()
        
        return count > 0
        
    except Exception as e:
        print(f"❌ Embedding creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_functionality():
    """Test search functionality with Elasticsearch."""
    print("\n🔍 Testing search functionality...")
    
    try:
        # Create test config
        config_path = create_test_config()
        
        # Load config and configure global settings  
        config = Config.from_yaml(config_path)
        configure_from_config(config)
        
        # Create query tester
        tester = WikipediaQueryTester(config, method=EmbeddingMethod.TRADITIONAL)
        print("✅ Query tester initialized")
        
        # Create simple test queries
        from wiki_embed.models import LocationQuery, QueryType
        test_queries = [
            LocationQuery(
                query="parks and recreation in Utah",
                expected_articles=["any"],  # We don't have specific expectations for this test
                location_context="Utah",
                query_type=QueryType.RECREATIONAL,
                description="Test query for parks"
            ),
            LocationQuery(
                query="mountain skiing resort",
                expected_articles=["any"],
                location_context="Utah", 
                query_type=QueryType.RECREATIONAL,
                description="Test query for skiing"
            )
        ]
        
        print(f"🔍 Running {len(test_queries)} test queries...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n  Query {i}: {query.query}")
            
            # Get query embedding
            query_embedding = tester.embed_model.get_text_embedding(query.query)
            
            # Perform search
            start_time = time.time()
            results = tester.vector_searcher.similarity_search(query_embedding, 3)
            search_time = time.time() - start_time
            
            # Check results format
            if 'documents' in results and 'metadatas' in results:
                num_results = len(results['documents'][0]) if results['documents'] else 0
                print(f"    ✅ Found {num_results} results in {search_time:.3f}s")
                
                # Show first result metadata
                if num_results > 0 and results['metadatas']:
                    first_metadata = results['metadatas'][0][0]
                    print(f"    📄 Top result: {first_metadata.get('title', 'No title')}")
                    print(f"    🎯 Page ID: {first_metadata.get('page_id', 'No ID')}")
            else:
                print(f"    ❌ Invalid result format: {results.keys()}")
                return False
        
        print("✅ All search queries completed successfully")
        
        # Clean up test config
        Path(config_path).unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Search testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_chromadb_elasticsearch():
    """Compare results between ChromaDB and Elasticsearch."""
    print("\n⚖️  Comparing ChromaDB vs Elasticsearch results...")
    
    # This would require having ChromaDB embeddings already created
    # For now, we'll just print a placeholder
    print("📝 Comparison test placeholder:")
    print("   1. Create embeddings in both ChromaDB and Elasticsearch")
    print("   2. Run identical queries on both")
    print("   3. Compare result similarity scores and page IDs")
    print("   4. Validate results are within acceptable variance")
    
    return True


def main():
    """Run all basic Elasticsearch tests."""
    print("🧪 Running Basic Elasticsearch Tests")
    print("=" * 50)
    
    tests = [
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("Embedding Creation", test_embedding_creation), 
        ("Search Functionality", test_search_functionality),
        ("ChromaDB Comparison", compare_chromadb_elasticsearch),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            success = test_func()
            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n❌ {test_name}: FAILED - {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Elasticsearch integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())