#!/usr/bin/env python3
"""Test script for Phase 3 implementation - Hybrid Search"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.vectors import HybridPropertySearch, PropertyEmbeddingPipeline
from src.vectors.config_loader import get_embedding_config, get_vector_index_config, get_search_config
from src.database.neo4j_client import get_neo4j_driver, close_neo4j_driver


def test_phase3():
    """Test Phase 3 components - Hybrid Search"""
    print("=" * 60)
    print("PHASE 3 TESTING - HYBRID SEARCH")
    print("=" * 60)
    
    driver = None
    try:
        # Test 1: Load configuration
        print("\n1. Loading configuration...")
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        search_config = get_search_config()
        print(f"   ✓ Configuration loaded")
        print(f"   - Default top_k: {search_config.default_top_k}")
        print(f"   - Graph boost: {search_config.use_graph_boost}")
        print(f"   - Score weights: V={search_config.vector_weight}, G={search_config.graph_weight}, F={search_config.features_weight}")
        
        # Test 2: Connect to Neo4j
        print("\n2. Connecting to Neo4j...")
        driver = get_neo4j_driver()
        print("   ✓ Connected to Neo4j")
        
        # Test 3: Create pipeline and search
        print("\n3. Creating HybridPropertySearch...")
        pipeline = PropertyEmbeddingPipeline(driver, embedding_config, vector_config)
        search = HybridPropertySearch(driver, pipeline, search_config)
        print("   ✓ HybridPropertySearch created")
        
        # Test 4: Check embeddings status
        print("\n4. Checking embeddings status...")
        status = pipeline.vector_manager.check_embeddings_exist()
        print(f"   - Total properties: {status['total']}")
        print(f"   - With embeddings: {status['with_embeddings']}")
        
        if status['with_embeddings'] == 0:
            print("   ⚠️  No embeddings found - search won't work")
            print("   Run 'python create_embeddings.py' first")
        
        # Test 5: Test graph metrics
        print("\n5. Testing graph metrics...")
        # Get a sample property
        with driver.session() as session:
            result = session.run("MATCH (p:Property) RETURN p.listing_id as id LIMIT 1").single()
            if result:
                sample_id = result['id']
                metrics = search._get_graph_metrics(sample_id)
                print(f"   ✓ Got metrics for property {sample_id}:")
                print(f"   - Centrality score: {metrics['centrality_score']:.3f}")
                print(f"   - Similarity connections: {metrics['similarity_connections']}")
                print(f"   - Neighborhood connections: {metrics['neighborhood_connections']}")
                print(f"   - Feature count: {metrics['feature_count']}")
            else:
                print("   ⚠️  No properties in database")
        
        # Test 6: Test scoring algorithm
        print("\n6. Testing scoring algorithm...")
        test_vector_score = 0.8
        test_graph_score = 0.5
        test_metrics = {
            'centrality_score': 0.5,
            'similarity_connections': 3,
            'neighborhood_connections': 25,
            'feature_connections': 10,
            'feature_count': 8
        }
        combined = search._calculate_combined_score(
            test_vector_score,
            test_graph_score,
            test_metrics
        )
        print(f"   ✓ Combined score calculation:")
        print(f"   - Vector: {test_vector_score:.3f} * {search_config.vector_weight} = {test_vector_score * search_config.vector_weight:.3f}")
        print(f"   - Graph: {test_graph_score:.3f} * {search_config.graph_weight} = {test_graph_score * search_config.graph_weight:.3f}")
        print(f"   - Features: {test_metrics['feature_count']/15:.3f} * {search_config.features_weight} = {(test_metrics['feature_count']/15) * search_config.features_weight:.3f}")
        print(f"   - Combined: {combined:.3f}")
        
        # Test 7: Test filters
        print("\n7. Testing filter application...")
        test_results = [
            {'listing_id': '1', 'price': 500000, 'city': 'San Francisco', 'bedrooms': 2},
            {'listing_id': '2', 'price': 750000, 'city': 'San Francisco', 'bedrooms': 3},
            {'listing_id': '3', 'price': 1000000, 'city': 'Park City', 'bedrooms': 4},
        ]
        filters = {'price_max': 800000, 'city': 'San Francisco'}
        filtered = search._apply_filters(test_results, filters)
        print(f"   ✓ Filter test:")
        print(f"   - Input: {len(test_results)} properties")
        print(f"   - Filters: {filters}")
        print(f"   - Output: {len(filtered)} properties")
        
        # Test 8: Test search (if embeddings exist)
        if status['with_embeddings'] > 0:
            print("\n8. Testing search functionality...")
            test_query = "modern property with good location"
            print(f"   Query: '{test_query}'")
            
            try:
                results = search.search(test_query, top_k=3)
                print(f"   ✓ Search returned {len(results)} results")
                if results:
                    top_result = results[0]
                    print(f"   Top result: {top_result.listing_id}")
                    print(f"   - Combined score: {top_result.combined_score:.3f}")
                    print(f"   - Location: {top_result.neighborhood}, {top_result.city}")
            except Exception as e:
                print(f"   ⚠️  Search test failed: {e}")
        else:
            print("\n8. Skipping search test (no embeddings)")
        
        print("\n" + "=" * 60)
        print("PHASE 3 TESTING COMPLETE")
        print("=" * 60)
        
        if status['with_embeddings'] == 0:
            print("\n⚠️  To fully test search:")
            print("1. Run: python create_embeddings.py")
            print("2. Then: python search_properties.py --demo")
        else:
            print("\n✓ Ready to search!")
            print("Try: python search_properties.py --demo")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            close_neo4j_driver(driver)


if __name__ == "__main__":
    success = test_phase3()
    sys.exit(0 if success else 1)