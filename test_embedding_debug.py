#!/usr/bin/env python3
"""Debug script to test embedding configuration and generation."""

import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

def test_config_loading():
    """Test configuration loading and serialization."""
    print("\n1. Testing configuration loading...")
    from data_pipeline.config.loader import load_configuration
    from data_pipeline.config.models import EmbeddingConfig
    
    config = load_configuration(sample_size=1)
    print(f"   Provider: {config.embedding.provider}")
    print(f"   Model: {config.embedding.model_name}")
    print(f"   API key loaded: {config.embedding.api_key is not None}")
    
    # Test serialization
    serialized = config.embedding.model_dump()
    print(f"   Serialized API key: {'present' if serialized.get('api_key') else 'missing'}")
    
    # Test deserialization
    reconstructed = EmbeddingConfig(**serialized)
    print(f"   Reconstructed API key: {'present' if reconstructed.api_key else 'missing'}")
    
    return config


def test_embedding_generation(config):
    """Test actual embedding generation with Pandas UDF."""
    print("\n2. Testing embedding generation...")
    
    spark = SparkSession.builder \
        .appName("EmbeddingDebug") \
        .master("local[1]") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Create test data
    data = [
        {"id": 1, "text": "Beautiful house in San Francisco"},
        {"id": 2, "text": "Modern apartment downtown"}
    ]
    df = spark.createDataFrame(data)
    
    # Test with our embedding generator
    from data_pipeline.processing.base_embedding import BaseEmbeddingGenerator
    
    class TestGenerator(BaseEmbeddingGenerator):
        def prepare_embedding_text(self, df):
            return df.withColumn("embedding_text", col("text"))
    
    try:
        generator = TestGenerator(spark, config.embedding)
        print(f"   Generator initialized with {config.embedding.provider}")
        
        # Prepare text
        prepared_df = generator.prepare_embedding_text(df)
        print(f"   Text prepared: {prepared_df.count()} rows")
        
        # Generate embeddings
        print("   Generating embeddings...")
        result_df = generator.generate_embeddings(prepared_df)
        
        # Collect results
        results = result_df.select("id", "embedding").collect()
        
        for row in results:
            if row["embedding"]:
                print(f"   ✅ ID {row['id']}: {len(row['embedding'])} dimensions")
            else:
                print(f"   ❌ ID {row['id']}: No embedding")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()


def test_provider_initialization():
    """Test embedding provider initialization directly."""
    print("\n3. Testing provider initialization...")
    
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Test with Voyage
    config_dict = {
        "provider": "voyage",
        "model_name": "voyage-3",
        "dimension": 1024,
        "api_key": os.environ.get("VOYAGE_API_KEY")
    }
    
    config = EmbeddingConfig(**config_dict)
    print(f"   Config created: {config.provider}")
    print(f"   API key: {'present' if config.api_key else 'missing'}")
    
    # Try to create provider
    try:
        from llama_index.embeddings.voyageai import VoyageEmbedding
        
        if config.api_key:
            embed_model = VoyageEmbedding(
                api_key=config.api_key,
                model_name=config.model_name
            )
            print(f"   ✅ VoyageEmbedding created successfully")
            
            # Test with a simple text
            test_text = "Test embedding"
            embedding = embed_model.get_text_embedding(test_text)
            print(f"   ✅ Test embedding generated: {len(embedding)} dimensions")
        else:
            print("   ❌ No API key available")
            
    except Exception as e:
        print(f"   ❌ Error creating provider: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("EMBEDDING CONFIGURATION DEBUG")
    print("=" * 60)
    
    # Test configuration
    config = test_config_loading()
    
    # Test provider directly
    test_provider_initialization()
    
    # Test full pipeline
    test_embedding_generation(config)
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)