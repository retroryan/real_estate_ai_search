#!/usr/bin/env python3
"""Test with REAL Voyage API embeddings."""

import os
import sys
from dotenv import load_dotenv
from pyspark.sql import SparkSession

# Load .env file FIRST
load_dotenv()

def test_real_voyage_embeddings():
    """Test embedding generation with real Voyage API."""
    
    print("\n" + "="*60)
    print("TESTING WITH REAL VOYAGE API")
    print("="*60)
    
    # Check API key is loaded
    api_key = os.environ.get('VOYAGE_API_KEY')
    if not api_key:
        print("❌ VOYAGE_API_KEY not found in environment")
        return False
    
    print("✅ VOYAGE_API_KEY loaded successfully.")
    
    # Import after env is loaded
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    from data_pipeline.processing.entity_embeddings import PropertyEmbeddingGenerator
    
    # Create config with Voyage provider
    print("\n1. Creating EmbeddingConfig with Voyage provider...")
    config = EmbeddingConfig(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-3",
        batch_size=2,  # Small batch for testing
        dimension=1024
    )
    
    # Verify API key was loaded into config
    assert config.api_key is not None, "API key not loaded into config"
    assert config.api_key == api_key, "API key mismatch"
    print(f"   ✅ Config has API key: {config.api_key[:10]}...")
    
    # Test serialization (as happens in UDF)
    print("\n2. Testing serialization for UDF...")
    serialized = config.model_dump()
    assert serialized['api_key'] == api_key
    print(f"   ✅ Serialized config includes API key")
    
    # Create Spark session and test real embedding generation
    print("\n3. Testing real embedding generation with Voyage API...")
    spark = SparkSession.builder \
        .appName("VoyageAPITest") \
        .master("local[1]") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Create test property data
        data = [
            {
                "listing_id": "test1",
                "city": "San Francisco",
                "state": "CA",
                "listing_price": 1500000,
                "bedrooms": 3,
                "bathrooms": 2,
                "square_feet": 1800,
                "features": ["garage", "garden"],
                "description": "Beautiful Victorian home in Pacific Heights"
            },
            {
                "listing_id": "test2",
                "city": "Palo Alto",
                "state": "CA",
                "listing_price": 2500000,
                "bedrooms": 4,
                "bathrooms": 3,
                "square_feet": 2400,
                "features": ["pool", "modern kitchen"],
                "description": "Modern home near Stanford University"
            }
        ]
        
        df = spark.createDataFrame(data)
        print(f"   Created test DataFrame with {df.count()} properties")
        
        # Initialize generator with Voyage config
        generator = PropertyEmbeddingGenerator(spark, config)
        print(f"   Generator initialized with {generator.provider_name} provider")
        
        # Prepare embedding text
        df_with_text = generator.prepare_embedding_text(df)
        texts = df_with_text.select("listing_id", "embedding_text").collect()
        for row in texts:
            print(f"   Text for {row['listing_id']}: {row['embedding_text'][:50]}...")
        
        # Generate REAL embeddings using Voyage API
        print("\n4. Calling Voyage API to generate embeddings...")
        df_with_embeddings = generator.generate_embeddings(df_with_text)
        
        # Verify embeddings were generated
        results = df_with_embeddings.select(
            "listing_id", 
            "embedding",
            "embedding_model",
            "embedding_dimension"
        ).collect()
        
        print("\n5. Verifying embedding results...")
        for row in results:
            if row['embedding'] is None:
                print(f"   ❌ No embedding for {row['listing_id']}")
                return False
            
            embedding_len = len(row['embedding'])
            print(f"   ✅ {row['listing_id']}: {embedding_len} dimensions")
            print(f"      Model: {row['embedding_model']}")
            print(f"      First 5 values: {row['embedding'][:5]}")
            
            # Verify it's a Voyage-3 1024-dimensional embedding
            assert embedding_len == 1024, f"Expected 1024 dimensions, got {embedding_len}"
            assert row['embedding_model'] == "voyage_voyage-3"
            assert row['embedding_dimension'] == 1024
            
            # Check that values are reasonable floats (not mock random values)
            assert all(isinstance(v, float) for v in row['embedding'][:5])
            assert any(v < 0 for v in row['embedding']), "Real embeddings should have negative values"
        
        print("\n✅ SUCCESS: Real Voyage API embeddings generated correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error generating embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        spark.stop()


def test_direct_voyage_api():
    """Test Voyage API directly without Spark."""
    print("\n" + "="*60)
    print("DIRECT VOYAGE API TEST")
    print("="*60)
    
    api_key = os.environ.get('VOYAGE_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return False
    
    try:
        from llama_index.embeddings.voyageai import VoyageEmbedding
        
        print("1. Creating VoyageEmbedding client...")
        client = VoyageEmbedding(
            api_key=api_key,
            model_name="voyage-3"
        )
        print("   ✅ Client created")
        
        print("\n2. Generating single embedding...")
        text = "Beautiful home in San Francisco with ocean views"
        embedding = client.get_text_embedding(text)
        
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
        
        # Test batch embedding
        print("\n3. Testing batch embedding...")
        texts = [
            "Modern apartment in downtown",
            "Spacious family home with garden"
        ]
        embeddings = client.get_text_embedding_batch(texts)
        
        print(f"   ✅ Batch generated: {len(embeddings)} embeddings")
        for i, emb in enumerate(embeddings):
            print(f"   Text {i+1}: {len(emb)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
        return False


if __name__ == "__main__":
    print("VOYAGE API KEY STATUS:")
    api_key = os.environ.get('VOYAGE_API_KEY')
    if api_key:
        print(f"✅ Found in environment: {api_key[:10]}...")
    else:
        print("❌ Not found in environment")
        sys.exit(1)
    
    # Test direct API first
    direct_success = test_direct_voyage_api()
    
    # Then test with Spark
    spark_success = test_real_voyage_embeddings()
    
    if direct_success and spark_success:
        print("\n" + "="*60)
        print("🎉 ALL REAL VOYAGE API TESTS PASSED!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed")
        sys.exit(1)