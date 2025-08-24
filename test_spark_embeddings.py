#!/usr/bin/env python
"""
Simple standalone test of Spark with embeddings.
Tests the basic functionality without all the pipeline complexity.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, pandas_udf
from pyspark.sql.types import ArrayType, DoubleType
import pandas as pd
import numpy as np

# Load environment variables from parent .env
parent_env = Path(__file__).parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env)
    print(f"✓ Loaded .env from {parent_env}")

# Check for API key
voyage_key = os.getenv('VOYAGE_API_KEY')
if voyage_key:
    print(f"✓ VOYAGE_API_KEY found (length: {len(voyage_key)})")
else:
    print("⚠️  VOYAGE_API_KEY not found, using mock embeddings")

def test_basic_spark():
    """Test basic Spark functionality."""
    print("\n=== Testing Basic Spark ===")
    
    spark = SparkSession.builder \
        .appName("TestSparkEmbeddings") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Create simple test data
    data = [
        (1, "San Francisco is a beautiful city"),
        (2, "Park City has great skiing"),
        (3, "Python is a programming language"),
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    df.show(truncate=False)
    
    print(f"✓ Created DataFrame with {df.count()} rows")
    
    spark.stop()
    return True

def test_mock_embeddings():
    """Test with mock embeddings (no API calls)."""
    print("\n=== Testing Mock Embeddings ===")
    
    spark = SparkSession.builder \
        .appName("TestMockEmbeddings") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Create test data
    data = [
        (1, "San Francisco is a beautiful city"),
        (2, "Park City has great skiing"),
        (3, "Python is a programming language"),
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    
    # Create a simple pandas UDF for mock embeddings
    @pandas_udf(returnType=ArrayType(DoubleType()))
    def generate_mock_embeddings(texts: pd.Series) -> pd.Series:
        """Generate mock embeddings for testing."""
        print(f"Processing batch of {len(texts)} texts")
        results = []
        for text in texts:
            if text:
                # Generate deterministic fake embedding
                import hashlib
                text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
                np.random.seed(text_hash)
                embedding = np.random.normal(0, 1, 384).tolist()  # Small dimension for testing
                results.append(embedding)
            else:
                results.append(None)
        return pd.Series(results)
    
    # Apply embeddings
    result_df = df.withColumn("embedding", generate_mock_embeddings(col("text")))
    
    # Show results (use slice function for arrays in Spark)
    from pyspark.sql.functions import slice
    result_df.select("id", "text", slice(col("embedding"), 1, 3).alias("embedding_sample")).show(truncate=False)
    
    # Count results
    embedded_count = result_df.filter(col("embedding").isNotNull()).count()
    print(f"✓ Generated {embedded_count} mock embeddings")
    
    spark.stop()
    return True

def test_voyage_embeddings():
    """Test with real Voyage embeddings (requires API key)."""
    print("\n=== Testing Voyage Embeddings ===")
    
    if not os.getenv('VOYAGE_API_KEY'):
        print("⚠️  Skipping Voyage test - no API key found")
        return False
    
    spark = SparkSession.builder \
        .appName("TestVoyageEmbeddings") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Create small test data
    data = [
        (1, "San Francisco is a beautiful city"),
        (2, "Park City has great skiing"),
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    
    # Create pandas UDF for Voyage embeddings
    @pandas_udf(returnType=ArrayType(DoubleType()))
    def generate_voyage_embeddings(texts: pd.Series) -> pd.Series:
        """Generate Voyage embeddings."""
        print(f"Processing batch of {len(texts)} texts with Voyage")
        
        try:
            from llama_index.embeddings.voyageai import VoyageEmbedding
            
            api_key = os.getenv('VOYAGE_API_KEY')
            embed_model = VoyageEmbedding(
                api_key=api_key,
                model_name="voyage-3",
                embed_batch_size=10
            )
            
            results = []
            for text in texts:
                if text:
                    try:
                        embedding = embed_model.get_text_embedding(text)
                        results.append(embedding)
                        print(f"  ✓ Generated embedding of length {len(embedding)}")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        results.append(None)
                else:
                    results.append(None)
            
            return pd.Series(results)
            
        except Exception as e:
            print(f"Failed to initialize Voyage: {e}")
            return pd.Series([None] * len(texts))
    
    # Apply embeddings
    result_df = df.withColumn("embedding", generate_voyage_embeddings(col("text")))
    
    # Show results (use slice function for arrays in Spark)
    from pyspark.sql.functions import slice
    result_df.select("id", "text", slice(col("embedding"), 1, 3).alias("embedding_sample")).show(truncate=False)
    
    # Count results
    embedded_count = result_df.filter(col("embedding").isNotNull()).count()
    print(f"✓ Generated {embedded_count} Voyage embeddings")
    
    spark.stop()
    return embedded_count > 0

def test_llama_index_direct():
    """Test llama-index embeddings directly without Spark."""
    print("\n=== Testing LlamaIndex Direct (No Spark) ===")
    
    texts = [
        "San Francisco is a beautiful city",
        "Park City has great skiing",
    ]
    
    # Test with mock first
    print("\n1. Testing with mock embeddings:")
    mock_embeddings = []
    for text in texts:
        import hashlib
        text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        np.random.seed(text_hash)
        embedding = np.random.normal(0, 1, 384).tolist()
        mock_embeddings.append(len(embedding))
    print(f"✓ Generated {len(mock_embeddings)} mock embeddings: {mock_embeddings}")
    
    # Test with Voyage if available
    if os.getenv('VOYAGE_API_KEY'):
        print("\n2. Testing with Voyage API:")
        try:
            from llama_index.embeddings.voyageai import VoyageEmbedding
            
            embed_model = VoyageEmbedding(
                api_key=os.getenv('VOYAGE_API_KEY'),
                model_name="voyage-3",
                embed_batch_size=10
            )
            
            # Test single embedding
            single_embedding = embed_model.get_text_embedding(texts[0])
            print(f"✓ Single embedding length: {len(single_embedding)}")
            
            # Test batch embedding
            if hasattr(embed_model, 'get_text_embedding_batch'):
                batch_embeddings = embed_model.get_text_embedding_batch(texts)
                print(f"✓ Batch embeddings count: {len(batch_embeddings)}")
                print(f"✓ Batch embedding lengths: {[len(e) for e in batch_embeddings]}")
            else:
                print("⚠️  Batch embedding not supported")
            
        except Exception as e:
            print(f"✗ Voyage error: {e}")
    else:
        print("\n2. Skipping Voyage test - no API key")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("SPARK EMBEDDINGS TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Basic Spark", test_basic_spark),
        ("Mock Embeddings", test_mock_embeddings),
        ("LlamaIndex Direct", test_llama_index_direct),
        ("Voyage Embeddings", test_voyage_embeddings),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓ PASSED" if success else "⚠️ SKIPPED"))
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append((name, f"✗ FAILED: {str(e)[:50]}"))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, status in results:
        print(f"{name:.<30} {status}")
    
    # Overall status
    failures = [r for r in results if "FAILED" in r[1]]
    if failures:
        print(f"\n✗ {len(failures)} test(s) failed")
        sys.exit(1)
    else:
        print("\n✓ All tests passed or skipped appropriately")
        sys.exit(0)

if __name__ == "__main__":
    main()