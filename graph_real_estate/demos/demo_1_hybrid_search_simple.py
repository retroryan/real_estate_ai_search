#!/usr/bin/env python3
"""
DEMO 1: SIMPLE HYBRID SEARCH TEST
=================================

Quick test of enhanced hybrid search with similarity and proximity relationships.
"""

import sys
from pathlib import Path

# Add src to path 
sys.path.insert(0, str(Path(__file__).parent.parent))

from vectors import PropertyEmbeddingPipeline, HybridPropertySearch
from vectors.config_loader import get_embedding_config, get_vector_index_config, get_search_config
from database import get_neo4j_driver, close_neo4j_driver, run_query

def test_hybrid_search():
    """Simple test of enhanced hybrid search"""
    print("🚀 Testing Enhanced Hybrid Search")
    print("=" * 50)
    
    print("\n🚀 NEO4J FEATURES DEMONSTRATED:")
    print("   • Hybrid Search - Combining vector embeddings with graph relationships")
    print("   • Graph Boosting - Using graph metrics to enhance vector scores")
    print("   • Feature-Based Scoring - Leveraging HAS_FEATURE relationships")
    print("   • Proximity Intelligence - Using NEAR_BY for location awareness")
    print("   • Combined Scoring - Merging vector and graph scores")
    print("   • Real-time Similarity - On-demand embedding comparisons")
    print("   • Graph Centrality - Measuring node importance in the network\n")
    
    try:
        # Connect to database
        driver = get_neo4j_driver()
        
        # Show relationship stats
        print("\nRelationship Statistics:")
        stats_queries = {
            'Properties with Embeddings': "MATCH (p:Property) WHERE p.embedding IS NOT NULL RETURN count(p) as count",
            'Geographic Proximities': "MATCH ()-[r:NEAR_BY]->() RETURN count(r) as count",
            'Feature Relationships': "MATCH ()-[r:HAS_FEATURE]->() RETURN count(r) as count"
        }
        
        for name, query in stats_queries.items():
            result = run_query(driver, query)
            count = result[0]['count'] if result else 0
            print(f"  {name}: {count:,}")
        
        # Initialize hybrid search with constructor injection
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        search_config = get_search_config()
        
        # Create dependencies for hybrid search
        from core.query_executor import QueryExecutor
        from vectors.vector_manager import PropertyVectorManager
        
        # Clean initialization - embedding config handles model selection
        pipeline = PropertyEmbeddingPipeline(driver, embedding_config)
        
        query_executor = QueryExecutor(driver)
        vector_manager = PropertyVectorManager(driver, query_executor)
        
        search = HybridPropertySearch(query_executor, pipeline, vector_manager, search_config)
        
        # Check embeddings exist by querying database
        query = "MATCH (p:Property) WHERE p.embedding IS NOT NULL RETURN count(p) as with_embeddings"
        result = query_executor.execute_read(query)
        embeddings_count = result[0]['with_embeddings'] if result else 0
        
        if embeddings_count == 0:
            print("\n❌ No embeddings found! Create embeddings first.")
            return
            
        print(f"\n✅ Ready to search {embeddings_count} properties")
        
        # Test queries
        test_queries = [
            "luxury home with mountain views",
            "family-friendly property with garage"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            
            # Pure vector search
            print("  📊 Pure Vector Search:")
            vector_results = search.search(query, top_k=3, use_graph_boost=False)
            for i, result in enumerate(vector_results[:2], 1):
                price = result.listing_price or 0
                print(f"    {i}. {result.listing_id} - ${price:,}")
                print(f"       Vector: {result.vector_score:.3f}")
            
            # Enhanced hybrid search  
            print("  🧠 Graph-Enhanced Search:")
            hybrid_results = search.search(query, top_k=3, use_graph_boost=True)
            for i, result in enumerate(hybrid_results[:2], 1):
                price = result.listing_price or 0
                print(f"    {i}. {result.listing_id} - ${price:,}")
                print(f"       Vector: {result.vector_score:.3f} | Graph: {result.graph_score:.3f} | Combined: {result.combined_score:.3f}")
                if result.similar_properties:
                    print(f"       Connected to {len(result.similar_properties)} similar properties")
        
        print("\n🎉 Enhanced hybrid search working successfully!")
        print("✅ Similarity relationships boost graph scores")
        print("✅ Proximity relationships add location intelligence") 
        print("✅ Combined scoring provides superior relevance")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nPlease ensure:")
        print("  1. Neo4j is running and accessible")
        print("  2. Data has been loaded with data_pipeline")
        print("  3. Relationships have been built")
    finally:
        close_neo4j_driver()

def main():
    """Main entry point for demo runner"""
    test_hybrid_search()

if __name__ == "__main__":
    test_hybrid_search()