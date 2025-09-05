#!/usr/bin/env python3
"""
Test Phase 1: Wikipedia demo search with automatic location extraction.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {env_path}")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from real_estate_search.demo_queries import demo_wikipedia_location_search
from real_estate_search.config import AppConfig


def test_phase1_wikipedia_demo():
    """Test Phase 1 implementation of Wikipedia location search."""
    
    print("\n" + "="*80)
    print("PHASE 1 TEST: Wikipedia Demo with Location Extraction")
    print("="*80)
    
    # Initialize configuration and Elasticsearch
    app_config = AppConfig.load()
    es_config = app_config.elasticsearch.get_client_config()
    es_client = Elasticsearch(**es_config)
    
    # Test queries with locations
    test_queries = [
        "museums in San Francisco",
        "parks in Oakland", 
        "Temescal neighborhood history",
        "Golden Gate Bridge construction",
        "restaurants in SOMA",
        "Berkeley campus buildings",
        "Silicon Valley tech history",
        "Napa Valley wineries"
    ]
    
    print("\nTesting Wikipedia demo location search:")
    print("-" * 60)
    
    for query in test_queries:
        print(f"\n📍 Testing: '{query}'")
        
        try:
            # Execute demo search
            result = demo_wikipedia_location_search(
                es_client=es_client,
                query=query,
                size=3
            )
            
            print(f"   ✓ Query completed")
            print(f"   Total hits: {result.total_hits}")
            print(f"   Execution time: {result.execution_time_ms}ms")
            
            # Show extracted location from features
            for feature in result.es_features:
                if "Extracted Location" in feature:
                    print(f"   {feature}")
            
            # Show top results
            if result.results:
                print("   Top results:")
                for i, article in enumerate(result.results[:3], 1):
                    location = f" ({article.city}, {article.state})" if article.city else ""
                    print(f"     {i}. {article.title}{location}")
            else:
                print("   No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ Phase 1 test completed!")
    print("="*80)


if __name__ == "__main__":
    test_phase1_wikipedia_demo()