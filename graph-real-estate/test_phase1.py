#!/usr/bin/env python3
"""Test script for Phase 1 implementation"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.vectors import VectorIndexConfig, EmbeddingConfig, SearchConfig, PropertyVectorManager
from src.vectors.config_loader import load_config, get_embedding_config, get_vector_index_config, get_search_config
from src.database.neo4j_client import get_neo4j_driver, close_neo4j_driver


def test_phase1():
    """Test Phase 1 components"""
    print("=" * 60)
    print("PHASE 1 TESTING")
    print("=" * 60)
    
    # Test 1: Load configuration
    print("\n1. Testing configuration loading...")
    try:
        config = load_config()
        print("   ✓ Configuration loaded successfully")
        print(f"   - Provider: {config['embedding']['provider']}")
        print(f"   - Model: {config['embedding']['ollama_model']}")
        print(f"   - Index name: {config['vector_index']['index_name']}")
    except Exception as e:
        print(f"   ✗ Failed to load config: {e}")
        return False
    
    # Test 2: Create configuration models
    print("\n2. Testing Pydantic models...")
    try:
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        search_config = SearchConfig(**config["search"])
        
        print("   ✓ Configuration models created")
        print(f"   - Embedding dimensions: {embedding_config.get_dimensions()}")
        print(f"   - Vector dimensions: {vector_config.vector_dimensions}")
        print(f"   - Search top_k: {search_config.default_top_k}")
    except Exception as e:
        print(f"   ✗ Failed to create models: {e}")
        return False
    
    # Test 3: Test Neo4j connection
    print("\n3. Testing Neo4j connection...")
    try:
        driver = get_neo4j_driver()
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            if result.single():
                print("   ✓ Neo4j connection successful")
        
        # Test 4: Create PropertyVectorManager
        print("\n4. Testing PropertyVectorManager...")
        vector_manager = PropertyVectorManager(driver, vector_config)
        print("   ✓ PropertyVectorManager created")
        
        # Test 5: Check embeddings status
        print("\n5. Checking embeddings status...")
        status = vector_manager.check_embeddings_exist()
        print(f"   - Total properties: {status['total']}")
        print(f"   - With embeddings: {status['with_embeddings']}")
        print(f"   - Without embeddings: {status['without_embeddings']}")
        
        # Test 6: Create vector index
        print("\n6. Testing vector index creation...")
        if vector_manager.create_vector_index():
            print("   ✓ Vector index created/verified")
        else:
            print("   ✗ Failed to create vector index")
        
        close_neo4j_driver(driver)
        
    except Exception as e:
        print(f"   ✗ Neo4j error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("PHASE 1 TESTING COMPLETE")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_phase1()
    sys.exit(0 if success else 1)