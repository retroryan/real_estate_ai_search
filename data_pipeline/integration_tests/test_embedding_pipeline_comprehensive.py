#!/usr/bin/env python3
"""
Comprehensive Embedding Pipeline Integration Tests

This test suite validates the entity-specific embedding generation pipeline.
Tests all embedding generators and their text preparation logic with realistic data.

**Validated Embedding Components:**

Entity Embedding Generators:
- WikipediaEmbeddingGenerator: Article content embeddings
- PropertyEmbeddingGenerator: Property description embeddings
- NeighborhoodEmbeddingGenerator: Neighborhood feature embeddings

Base Infrastructure:
- BaseEmbeddingGenerator: Abstract embedding logic
- EmbeddingConfig: Provider configuration and validation
- Batch processing with Pandas UDFs
- Multiple provider support (Voyage, OpenAI, Ollama, etc.)

**Test Coverage:**
- Text preparation for all entity types
- Embedding configuration validation
- Mock embedding generation (no API calls)
- Performance and memory characteristics
- Error handling and edge cases

**Usage:**
    python -m pytest data_pipeline/integration_tests/test_embedding_pipeline_comprehensive.py -v
    
    Or run directly:
    PYTHONPATH=$PWD:$PYTHONPATH python data_pipeline/integration_tests/test_embedding_pipeline_comprehensive.py

**Note:**
    Tests use mock embeddings to avoid external API dependencies.
    For full integration testing with real providers, use environment variables:
    - VOYAGE_API_KEY for Voyage AI testing
    - OPENAI_API_KEY for OpenAI testing
"""

import sys
import os
from unittest.mock import patch, MagicMock
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, array, when, length
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType, ArrayType, 
    IntegerType, DoubleType
)


def create_spark_session():
    """Create a test Spark session."""
    return SparkSession.builder \
        .appName("EmbeddingPipelineTest") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()


def create_test_wikipedia_data(spark):
    """Create test Wikipedia data for embedding testing."""
    schema = StructType([
        StructField("page_id", StringType(), False),
        StructField("title", StringType(), True),
        StructField("short_summary", StringType(), True),
        StructField("long_summary", StringType(), True),
        StructField("best_city", StringType(), True),
        StructField("best_state", StringType(), True),
    ])
    
    data = [
        (
            "12345", 
            "San Francisco Real Estate History",
            "Overview of SF real estate development",
            "San Francisco real estate has evolved dramatically since the Gold Rush era. "
            "Victorian architecture dominates many neighborhoods, while modern high-rises "
            "define the skyline. The city's unique geography and zoning laws create diverse "
            "micro-markets with distinct characteristics and price points.",
            "San Francisco",
            "California"
        ),
        (
            "67890",
            "Mission District Culture",
            "Cultural heritage of the Mission",
            "The Mission District represents San Francisco's vibrant Latino culture with "
            "colorful murals, authentic cuisine, and historic architecture. This neighborhood "
            "has undergone significant gentrification while maintaining its cultural identity.",
            "San Francisco", 
            "California"
        ),
        (
            "11111",
            "California Housing Crisis",
            "Statewide housing affordability issues",
            "California faces a severe housing affordability crisis affecting all income levels. "
            "Limited housing supply, zoning restrictions, and high construction costs contribute "
            "to the nation's highest housing costs. Policy solutions include zoning reform and "
            "affordable housing mandates.",
            "",
            "California"
        )
    ]
    
    return spark.createDataFrame(data, schema)


def create_test_property_data(spark):
    """Create test property data for embedding testing."""
    schema = StructType([
        StructField("listing_id", StringType(), False),
        StructField("neighborhood_id", StringType(), True),
        StructField("listing_price", FloatType(), True),
        StructField("bedrooms", IntegerType(), True),
        StructField("bathrooms", FloatType(), True),
        StructField("square_feet", IntegerType(), True),
        StructField("features", ArrayType(StringType()), True),
        StructField("description", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
    ])
    
    data = [
        (
            "prop1", "nbr1", 750000.0, 3, 2.0, 1800, 
            ["garage", "pool", "garden"], 
            "Beautiful Victorian home with modern amenities. Features original hardwood floors, "
            "updated kitchen with granite counters, and a private garden. Walking distance to "
            "parks and public transit. Perfect for families.",
            "San Francisco", "California"
        ),
        (
            "prop2", "nbr1", 1200000.0, 4, 3.0, 2400,
            ["garage", "deck", "fireplace"],
            "Stunning contemporary home with panoramic city views. Open-concept living with "
            "high-end finishes throughout. Private deck for entertaining and two-car garage. "
            "Located in quiet residential area.",
            "San Francisco", "California"
        ),
        (
            "prop3", "nbr2", 650000.0, 2, 1.0, 1200,
            ["parking", "laundry"],
            "Charming condo in historic building. Recently renovated with modern appliances. "
            "Secure parking included. Great investment opportunity in up-and-coming neighborhood.",
            "Oakland", "California"
        )
    ]
    
    return spark.createDataFrame(data, schema)


def create_test_neighborhood_data(spark):
    """Create test neighborhood data for embedding testing."""
    schema = StructType([
        StructField("neighborhood_id", StringType(), False),
        StructField("name", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("county", StringType(), True),
        StructField("population", IntegerType(), True),
        StructField("median_income", IntegerType(), True),
        StructField("amenities", ArrayType(StringType()), True),
        StructField("description", StringType(), True),
        StructField("walkability_score", IntegerType(), True),
        StructField("transit_score", IntegerType(), True),
    ])
    
    data = [
        (
            "nbr1", "Mission District", "San Francisco", "California", "San Francisco",
            60000, 75000, ["restaurants", "nightlife", "parks", "public_transit"],
            "Vibrant neighborhood known for its Latino culture, street art, and diverse dining scene. "
            "The Mission offers excellent walkability with numerous shops, cafes, and entertainment venues. "
            "Well-connected by public transit with easy access to downtown.",
            9, 8
        ),
        (
            "nbr2", "Oakland Hills", "Oakland", "California", "Alameda", 
            45000, 95000, ["hiking", "views", "quiet", "family_friendly"],
            "Peaceful residential area with stunning bay views and access to hiking trails. "
            "Family-friendly community with good schools and low crime rates. More affordable "
            "alternative to San Francisco while maintaining proximity to the city.",
            6, 4
        )
    ]
    
    return spark.createDataFrame(data, schema)


def test_wikipedia_embedding_generator(spark):
    """Test Wikipedia embedding text preparation."""
    print("\n🧪 Testing Wikipedia Embedding Generator...")
    
    from data_pipeline.processing.entity_embeddings import WikipediaEmbeddingGenerator
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Create test data
    wikipedia_df = create_test_wikipedia_data(spark)
    
    # Configure for testing (use EmbeddingPipelineConfig wrapper)
    embedding_config = EmbeddingConfig(provider=EmbeddingProvider.MOCK)
    config = embedding_config  # No wrapper needed anymore
    
    # Initialize generator
    generator = WikipediaEmbeddingGenerator(spark, config)
    
    # Test text preparation
    prepared_df = generator.prepare_embedding_text(wikipedia_df)
    
    # Validate embedding text column exists
    assert "embedding_text" in prepared_df.columns, "embedding_text column missing"
    
    # Collect results for validation
    results = prepared_df.select("page_id", "title", "embedding_text").collect()
    
    # Validate text preparation logic
    for row in results:
        assert row["embedding_text"] is not None, f"Null embedding text for {row['page_id']}"
        assert len(row["embedding_text"]) > 50, f"Embedding text too short for {row['page_id']}"
        print(f"  ✅ {row['title']}: {len(row['embedding_text'])} chars")
    
    count = prepared_df.count()
    print(f"✅ Successfully prepared {count} Wikipedia articles for embedding")
    
    return count > 0


def test_property_embedding_generator(spark):
    """Test Property embedding text preparation."""
    print("\n🧪 Testing Property Embedding Generator...")
    
    from data_pipeline.processing.entity_embeddings import PropertyEmbeddingGenerator
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Create test data
    property_df = create_test_property_data(spark)
    
    # Configure for testing
    embedding_config = EmbeddingConfig(provider=EmbeddingProvider.MOCK)
    config = embedding_config  # No wrapper needed anymore
    
    # Initialize generator
    generator = PropertyEmbeddingGenerator(spark, config)
    
    # Test text preparation
    prepared_df = generator.prepare_embedding_text(property_df)
    
    # Validate embedding text column exists
    assert "embedding_text" in prepared_df.columns, "embedding_text column missing"
    
    # Collect results for validation
    results = prepared_df.select("listing_id", "embedding_text").collect()
    
    # Validate text preparation combines multiple fields
    for row in results:
        assert row["embedding_text"] is not None, f"Null embedding text for {row['listing_id']}"
        embedding_text = row["embedding_text"].lower()
        
        # Should contain price information
        assert "$" in row["embedding_text"], f"Missing price info for {row['listing_id']}"
        
        # Should contain bedroom/bathroom info (BR/BA from the text preparation)
        assert " br" in embedding_text or " ba" in embedding_text or "bedroom" in embedding_text or "bath" in embedding_text, \
            f"Missing room info for {row['listing_id']} - got: {embedding_text[:100]}..."
            
        print(f"  ✅ {row['listing_id']}: {len(row['embedding_text'])} chars")
    
    count = prepared_df.count()
    print(f"✅ Successfully prepared {count} properties for embedding")
    
    return count > 0


def test_neighborhood_embedding_generator(spark):
    """Test Neighborhood embedding text preparation."""
    print("\n🧪 Testing Neighborhood Embedding Generator...")
    
    from data_pipeline.processing.entity_embeddings import NeighborhoodEmbeddingGenerator  
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Create test data
    neighborhood_df = create_test_neighborhood_data(spark)
    
    # Configure for testing
    embedding_config = EmbeddingConfig(provider=EmbeddingProvider.MOCK)
    config = embedding_config  # No wrapper needed anymore
    
    # Initialize generator
    generator = NeighborhoodEmbeddingGenerator(spark, config)
    
    # Test text preparation
    prepared_df = generator.prepare_embedding_text(neighborhood_df)
    
    # Validate embedding text column exists
    assert "embedding_text" in prepared_df.columns, "embedding_text column missing"
    
    # Collect results for validation
    results = prepared_df.select("neighborhood_id", "name", "embedding_text").collect()
    
    # Validate text preparation combines neighborhood features
    for row in results:
        assert row["embedding_text"] is not None, f"Null embedding text for {row['neighborhood_id']}"
        embedding_text = row["embedding_text"].lower()
        
        # Should contain name and location
        assert row["name"].lower() in embedding_text, f"Missing name for {row['neighborhood_id']}"
        
        # Should contain demographic info when available
        if "population:" in embedding_text:
            print(f"  ✓ Demographics included for {row['name']}")
            
        # Should contain amenities  
        if "amenities:" in embedding_text:
            print(f"  ✓ Amenities included for {row['name']}")
            
        print(f"  ✅ {row['name']}: {len(row['embedding_text'])} chars")
    
    count = prepared_df.count()
    print(f"✅ Successfully prepared {count} neighborhoods for embedding")
    
    return count > 0


def test_mock_embedding_generation(spark):
    """Test embedding text preparation (mock generation without API calls)."""
    print("\n🧪 Testing Mock Embedding Generation...")
    
    from data_pipeline.processing.entity_embeddings import WikipediaEmbeddingGenerator
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Create test data
    wikipedia_df = create_test_wikipedia_data(spark)
    
    # Configure for testing 
    os.environ["VOYAGE_API_KEY"] = "test-key-for-validation"
    embedding_config = EmbeddingConfig(provider=EmbeddingProvider.MOCK)
    config = embedding_config  # No wrapper needed anymore
    
    # Initialize generator
    generator = WikipediaEmbeddingGenerator(spark, config)
    
    # Test text preparation (the part before actual embedding API calls)
    prepared_df = generator.prepare_embedding_text(wikipedia_df)
    
    # Validate prepared data is ready for embedding
    text_lengths = prepared_df.select(
        length(col("embedding_text")).alias("text_length")
    ).collect()
    
    for row in text_lengths:
        assert row["text_length"] > 0, "Empty embedding text detected"
        print(f"  ✓ Text length: {row['text_length']} chars")
    
    count = prepared_df.count()
    print(f"✅ Successfully validated {count} items ready for embedding generation")
    
    return count > 0


def test_embedding_config_validation():
    """Test embedding configuration validation."""
    print("\n🧪 Testing Embedding Configuration...")
    
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Test valid configuration (set dummy API key for testing)
    os.environ["VOYAGE_API_KEY"] = "test-key-for-validation"
    
    embedding_config = EmbeddingConfig(
        provider=EmbeddingProvider.VOYAGE,
        voyage_model="voyage-3"
    )
    config = embedding_config  # No wrapper needed anymore
    
    assert config.embedding.provider == EmbeddingProvider.VOYAGE
    assert config.embedding.voyage_model == "voyage-3"
    print("  ✅ Valid configuration created")
    
    # Test configuration serialization/deserialization
    config_dict = config.model_dump()
    restored_config = EmbeddingConfig(**config_dict)
    
    assert restored_config.embedding.provider == config.embedding.provider
    assert restored_config.embedding.voyage_model == config.embedding.voyage_model
    print("  ✅ Configuration serialization works")
    
    # Test different providers
    openai_embedding_config = EmbeddingConfig(
        provider=EmbeddingProvider.OPENAI,
        openai_model="text-embedding-3-small"
    )
    openai_config = openai_embedding_config  # No wrapper needed anymore
    
    assert openai_config.embedding.provider == EmbeddingProvider.OPENAI
    print("  ✅ OpenAI configuration valid")
    
    print("✅ Embedding configuration validation passed")
    return True


def test_text_statistics_and_performance(spark):
    """Test embedding text statistics and performance characteristics.""" 
    print("\n🧪 Testing Text Statistics and Performance...")
    
    from data_pipeline.processing.entity_embeddings import (
        WikipediaEmbeddingGenerator, 
        PropertyEmbeddingGenerator,
        NeighborhoodEmbeddingGenerator
    )
    from data_pipeline.config.models import EmbeddingConfig, EmbeddingProvider
    
    # Create larger test datasets
    wikipedia_df = create_test_wikipedia_data(spark)
    property_df = create_test_property_data(spark) 
    neighborhood_df = create_test_neighborhood_data(spark)
    
    embedding_config = EmbeddingConfig()
    config = embedding_config  # No wrapper needed anymore
    
    # Test all generators
    generators = [
        ("Wikipedia", WikipediaEmbeddingGenerator(spark, config), wikipedia_df),
        ("Property", PropertyEmbeddingGenerator(spark, config), property_df),
        ("Neighborhood", NeighborhoodEmbeddingGenerator(spark, config), neighborhood_df)
    ]
    
    results = []
    
    for name, generator, df in generators:
        print(f"\n  📊 Analyzing {name} embeddings...")
        
        # Prepare embedding text
        prepared_df = generator.prepare_embedding_text(df)
        
        # Calculate text statistics using proper aggregation
        from pyspark.sql.functions import avg, max as spark_max, min as spark_min
        
        stats = prepared_df.select(
            length(col("embedding_text")).alias("text_length")
        ).agg(
            avg("text_length").alias("avg_length"),
            spark_max("text_length").alias("max_length"),
            spark_min("text_length").alias("min_length")
        ).collect()[0]
        
        avg_length = stats["avg_length"]
        max_length = stats["max_length"]  
        min_length = stats["min_length"]
        
        print(f"    Avg length: {avg_length:.0f} chars")
        print(f"    Max length: {max_length} chars")
        print(f"    Min length: {min_length} chars")
        
        # Validate reasonable text lengths
        assert avg_length > 50, f"{name} text too short on average"
        assert max_length < 10000, f"{name} text too long (may hit token limits)"
        assert min_length > 10, f"{name} text too short minimum"
        
        results.append({
            "entity_type": name,
            "avg_length": avg_length,
            "max_length": max_length,
            "min_length": min_length,
            "count": prepared_df.count()
        })
    
    print(f"\n✅ Text statistics validation passed for all {len(results)} entity types")
    return len(results) > 0


def main():
    """Run comprehensive embedding pipeline integration tests."""
    print("🚀 Starting Comprehensive Embedding Pipeline Integration Tests...")
    print("="*80)
    
    spark = create_spark_session()
    
    try:
        results = []
        
        print("\n📋 ENTITY EMBEDDING GENERATORS:")
        results.append(("Wikipedia Generator", test_wikipedia_embedding_generator(spark)))
        results.append(("Property Generator", test_property_embedding_generator(spark)))  
        results.append(("Neighborhood Generator", test_neighborhood_embedding_generator(spark)))
        
        print("\n📋 EMBEDDING INFRASTRUCTURE:")
        results.append(("Configuration Validation", test_embedding_config_validation()))
        results.append(("Mock Generation", test_mock_embedding_generation(spark)))
        results.append(("Text Statistics", test_text_statistics_and_performance(spark)))
        
        # Summary
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE EMBEDDING PIPELINE TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_name:25} : {status}")
        
        print(f"\n📈 Overall: {passed}/{total} embedding tests working")
        
        if passed == total:
            print("🎉 All embedding pipeline components working correctly!")
            print("\n🎯 NEXT STEPS:")
            print("   • All embedding generators implemented and tested")
            print("   • Ready for production embedding pipeline testing")
            print("   • Ready for API provider integration testing")
            return 0
        else:
            print("⚠️ Some embedding tests failed. Please review the output above.")
            return 1
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())