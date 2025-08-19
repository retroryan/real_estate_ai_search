#!/usr/bin/env python3
"""Test script for Phase 2 implementation - Embedding Pipeline"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.vectors import PropertyEmbeddingPipeline, EmbeddingConfig, VectorIndexConfig
from src.vectors.config_loader import get_embedding_config, get_vector_index_config
from src.database.neo4j_client import get_neo4j_driver, close_neo4j_driver


def test_phase2():
    """Test Phase 2 components - Embedding Pipeline"""
    print("=" * 60)
    print("PHASE 2 TESTING - EMBEDDING PIPELINE")
    print("=" * 60)
    
    driver = None
    try:
        # Test 1: Load configuration
        print("\n1. Loading configuration...")
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        print(f"   ✓ Configuration loaded")
        print(f"   - Provider: {embedding_config.provider}")
        print(f"   - Model: {embedding_config.ollama_model if embedding_config.provider == 'ollama' else 'N/A'}")
        print(f"   - Batch size: {embedding_config.batch_size}")
        
        # Test 2: Connect to Neo4j
        print("\n2. Connecting to Neo4j...")
        driver = get_neo4j_driver()
        print("   ✓ Connected to Neo4j")
        
        # Test 3: Create embedding pipeline
        print("\n3. Creating PropertyEmbeddingPipeline...")
        pipeline = PropertyEmbeddingPipeline(driver, embedding_config, vector_config)
        print(f"   ✓ Pipeline created")
        print(f"   - Model: {pipeline._get_model_name()}")
        print(f"   - Dimensions: {embedding_config.get_dimensions()}")
        
        # Test 4: Test property text generation
        print("\n4. Testing property text generation...")
        test_property = {
            "listing_id": "test-001",
            "neighborhood": "Nob Hill",
            "city": "San Francisco",
            "property_type": "condo",
            "price": 1500000,
            "bedrooms": 2,
            "bathrooms": 2,
            "square_feet": 1200,
            "description": "Luxury condo with stunning city views",
            "features": ["City View", "Hardwood Floors", "Updated Kitchen"],
            "address": "123 California St"
        }
        
        text = pipeline._create_property_text(test_property)
        print("   ✓ Property text generated:")
        print("   " + "\n   ".join(text.split("\n")[:3]))  # Show first 3 lines
        
        # Test 5: Test embedding generation (single property)
        print("\n5. Testing embedding generation...")
        try:
            # Check if Ollama is running
            if embedding_config.provider == "ollama":
                import requests
                try:
                    response = requests.get(f"{embedding_config.ollama_base_url}/api/tags", timeout=2)
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m.get("name", "").split(":")[0] for m in models]
                        if embedding_config.ollama_model in model_names:
                            print(f"   ✓ Ollama model '{embedding_config.ollama_model}' is available")
                            
                            # Generate test embedding
                            embedding = pipeline.embed_model.get_text_embedding("Test property")
                            print(f"   ✓ Generated embedding with {len(embedding)} dimensions")
                        else:
                            print(f"   ⚠️  Model '{embedding_config.ollama_model}' not found in Ollama")
                            print(f"   Available models: {', '.join(model_names) if model_names else 'none'}")
                    else:
                        print("   ⚠️  Ollama is not responding properly")
                except requests.exceptions.RequestException:
                    print("   ⚠️  Ollama is not running at " + embedding_config.ollama_base_url)
                    print("   Run 'ollama serve' and 'ollama pull nomic-embed-text' first")
            else:
                print(f"   ⚠️  Skipping embedding test (provider: {embedding_config.provider})")
        except Exception as e:
            print(f"   ⚠️  Could not test embedding: {e}")
        
        # Test 6: Check database status
        print("\n6. Checking database status...")
        status = pipeline.vector_manager.check_embeddings_exist()
        print(f"   - Total properties: {status['total']}")
        print(f"   - With embeddings: {status['with_embeddings']}")
        print(f"   - Without embeddings: {status['without_embeddings']}")
        
        # Test 7: Process properties (dry run - show what would happen)
        print("\n7. Testing batch processing (dry run)...")
        if status['total'] > 0:
            # Get first few properties
            with driver.session() as session:
                result = session.run("MATCH (p:Property) RETURN count(p) as count LIMIT 1")
                count = result.single()["count"]
                print(f"   ✓ Found {count} properties in database")
                print(f"   Would process in batches of {embedding_config.batch_size}")
                print(f"   Estimated batches: {(count + embedding_config.batch_size - 1) // embedding_config.batch_size}")
        else:
            print("   ⚠️  No properties in database to process")
        
        print("\n" + "=" * 60)
        print("PHASE 2 TESTING COMPLETE")
        print("=" * 60)
        print("\nTo generate embeddings, run:")
        print("  pipeline.process_properties()")
        
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
    success = test_phase2()
    sys.exit(0 if success else 1)