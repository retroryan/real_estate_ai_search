#!/usr/bin/env python
"""
Simple standalone test of Spark with text chunking.
Tests chunking functionality in isolation.
"""

import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, udf, lit, size, monotonically_increasing_id
from pyspark.sql.types import ArrayType, StringType

def create_spark_session(app_name="TestChunking"):
    """Create a Spark session with minimal config."""
    spark = SparkSession.builder \
        .appName(app_name) \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def test_basic_chunking():
    """Test basic text chunking without explode."""
    print("\n=== Test 1: Basic Chunking (No Explode) ===")
    spark = create_spark_session("TestBasicChunking")
    
    # Create simple chunking UDF
    def chunk_text(text):
        if not text:
            return []
        
        chunk_size = 100  # Small chunks for testing
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    chunking_udf = udf(chunk_text, ArrayType(StringType()))
    
    # Test data
    data = [
        (1, "Short text that fits in one chunk"),
        (2, "This is a longer text that will be split into multiple chunks. " * 5),
        (3, None),  # Test null handling
        (4, ""),     # Test empty string
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    print(f"Input records: {df.count()}")
    
    # Apply chunking
    df_chunked = df.withColumn("chunks", chunking_udf(col("text")))
    df_chunked = df_chunked.withColumn("num_chunks", size(col("chunks")))
    
    # Show results
    df_chunked.select("id", "num_chunks").show()
    
    print("✓ Basic chunking completed")
    spark.stop()
    return True

def test_chunking_with_explode():
    """Test chunking with explode operation."""
    print("\n=== Test 2: Chunking with Explode ===")
    spark = create_spark_session("TestChunkingExplode")
    
    # Create chunking UDF with overlap
    def chunk_text_with_overlap(text):
        if not text:
            return []
        
        chunk_size = 50
        overlap = 10
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap if overlap > 0 else end
            
        return chunks if chunks else [text] if text else []
    
    chunking_udf = udf(chunk_text_with_overlap, ArrayType(StringType()))
    
    # Small test data
    data = [
        (1, "San Francisco is a beautiful city with great weather"),
        (2, "Park City has excellent skiing and mountain biking"),
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    print(f"Input records: {df.count()}")
    
    # Apply chunking
    start_time = time.time()
    df_chunked = df.withColumn("chunks", chunking_udf(col("text")))
    print(f"Chunking completed in {time.time() - start_time:.2f}s")
    
    # Count chunks before explode
    chunk_counts = df_chunked.select(size(col("chunks")).alias("count")).collect()
    total_chunks = sum(row["count"] for row in chunk_counts if row["count"])
    print(f"Total chunks before explode: {total_chunks}")
    
    # Explode chunks
    start_time = time.time()
    df_exploded = df_chunked.select(
        col("id"),
        col("text"),
        explode(col("chunks")).alias("chunk")
    )
    
    # Force computation
    exploded_count = df_exploded.count()
    print(f"Explode completed in {time.time() - start_time:.2f}s")
    print(f"Records after explode: {exploded_count}")
    
    # Show sample
    df_exploded.select("id", col("chunk").substr(1, 30).alias("chunk_preview")).show()
    
    print("✓ Chunking with explode completed")
    spark.stop()
    return True

def test_large_text_chunking():
    """Test chunking with larger texts."""
    print("\n=== Test 3: Large Text Chunking ===")
    spark = create_spark_session("TestLargeChunking")
    
    # Chunking UDF matching the pipeline
    def chunk_text_pipeline_style(text):
        if not text:
            return []
        
        chunk_size = 512
        chunk_overlap = 50
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - chunk_overlap if chunk_overlap > 0 else end
            
        return chunks if chunks else [text]
    
    chunking_udf = udf(chunk_text_pipeline_style, ArrayType(StringType()))
    
    # Create larger test data
    large_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
    data = [
        (1, large_text[:500]),   # ~500 chars -> 1 chunk
        (2, large_text[:1000]),  # ~1000 chars -> 2 chunks
        (3, large_text[:5000]),  # ~5000 chars -> 10+ chunks
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    print(f"Input records: {df.count()}")
    
    # Apply chunking
    start_time = time.time()
    df_chunked = df.withColumn("chunks", chunking_udf(col("text")))
    df_chunked = df_chunked.withColumn("num_chunks", size(col("chunks")))
    
    # Cache to avoid recomputation
    df_chunked.cache()
    
    # Show chunk counts
    df_chunked.select("id", "num_chunks").show()
    print(f"Chunking completed in {time.time() - start_time:.2f}s")
    
    # Now explode
    start_time = time.time()
    df_exploded = df_chunked.select(
        col("id"),
        explode(col("chunks")).alias("chunk")
    ).withColumn("chunk_length", col("chunk").cast("string").length())
    
    # Force computation and show stats
    total_exploded = df_exploded.count()
    print(f"Explode completed in {time.time() - start_time:.2f}s")
    print(f"Total chunks after explode: {total_exploded}")
    
    # Show length distribution
    df_exploded.groupBy("id").agg(
        {"chunk_length": "avg", "*": "count"}
    ).show()
    
    print("✓ Large text chunking completed")
    spark.stop()
    return True

def test_empty_and_null_handling():
    """Test handling of empty and null values."""
    print("\n=== Test 4: Empty and Null Handling ===")
    spark = create_spark_session("TestEmptyNull")
    
    def safe_chunk_text(text):
        if not text or not text.strip():
            return []
        
        # Simple chunking
        chunk_size = 100
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        return [c for c in chunks if c.strip()]
    
    chunking_udf = udf(safe_chunk_text, ArrayType(StringType()))
    
    # Test edge cases
    data = [
        (1, "Normal text"),
        (2, ""),
        (3, None),
        (4, "   "),  # Only whitespace
        (5, "\n\n\n"),  # Only newlines
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    
    # Apply chunking
    df_chunked = df.withColumn("chunks", chunking_udf(col("text")))
    df_chunked = df_chunked.withColumn("num_chunks", 
        col("chunks").isNotNull().cast("int") * size(col("chunks"))
    )
    
    # Show results
    df_chunked.select("id", "text", "num_chunks").show()
    
    # Try to explode (should handle empty arrays gracefully)
    df_exploded = df_chunked.filter(size(col("chunks")) > 0).select(
        col("id"),
        explode(col("chunks")).alias("chunk")
    )
    
    print(f"Records with chunks: {df_exploded.count()}")
    
    print("✓ Empty and null handling completed")
    spark.stop()
    return True

def test_with_monotonic_id():
    """Test chunking with monotonically_increasing_id like the pipeline."""
    print("\n=== Test 5: Chunking with Monotonic ID ===")
    spark = create_spark_session("TestMonotonicID")
    
    def chunk_text(text):
        if not text:
            return []
        chunks = []
        chunk_size = 200
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    chunking_udf = udf(chunk_text, ArrayType(StringType()))
    
    # Test data
    data = [
        (1, "Text for document 1 " * 20),
        (2, "Text for document 2 " * 20),
        (3, "Text for document 3 " * 20),
    ]
    
    df = spark.createDataFrame(data, ["id", "text"])
    
    # Apply chunking and explode
    df_chunked = df.withColumn("chunks", chunking_udf(col("text")))
    
    df_exploded = df_chunked.select(
        "*",
        explode(col("chunks")).alias("chunk_text")
    ).drop("chunks", "text").withColumnRenamed("chunk_text", "text")
    
    # Add monotonic ID
    df_with_id = df_exploded.withColumn(
        "chunk_index",
        monotonically_increasing_id()
    )
    
    # Show results
    print(f"Total chunks with IDs: {df_with_id.count()}")
    df_with_id.select("id", "chunk_index", col("text").substr(1, 20).alias("text_preview")).show(10)
    
    print("✓ Monotonic ID test completed")
    spark.stop()
    return True

def main():
    """Run all chunking tests."""
    print("=" * 60)
    print("SPARK TEXT CHUNKING TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Basic Chunking", test_basic_chunking),
        ("Chunking with Explode", test_chunking_with_explode),
        ("Large Text Chunking", test_large_text_chunking),
        ("Empty/Null Handling", test_empty_and_null_handling),
        ("Monotonic ID", test_with_monotonic_id),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓ PASSED" if success else "⚠️ FAILED"))
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append((name, f"✗ ERROR: {str(e)[:50]}"))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, status in results:
        print(f"{name:.<30} {status}")
    
    failures = [r for r in results if "✗" in r[1]]
    if failures:
        print(f"\n✗ {len(failures)} test(s) failed")
        return 1
    else:
        print("\n✓ All chunking tests passed")
        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())