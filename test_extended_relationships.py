#!/usr/bin/env python3
"""
Test program for extended relationship building.

This test verifies that all extended relationship types are properly created:
- HAS_FEATURE: Properties to Features
- OF_TYPE: Properties to PropertyTypes
- IN_PRICE_RANGE: Properties to PriceRanges
- IN_COUNTY: Geographic entities to Counties
- IN_TOPIC_CLUSTER: Entities to TopicClusters
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, array, count, avg
from pyspark.sql.types import StructType, StructField, StringType, FloatType, ArrayType, IntegerType


def create_spark_session():
    """Create a test Spark session."""
    return SparkSession.builder \
        .appName("ExtendedRelationshipTest") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()


def create_test_properties(spark):
    """Create test property data."""
    schema = StructType([
        StructField("listing_id", StringType(), False),
        StructField("neighborhood_id", StringType(), True),
        StructField("property_type", StringType(), True),
        StructField("listing_price", FloatType(), True),
        StructField("features", ArrayType(StringType()), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("county", StringType(), True),
        StructField("latitude", FloatType(), True),
        StructField("longitude", FloatType(), True),
        StructField("aggregated_topics", ArrayType(StringType()), True),
    ])
    
    data = [
        ("prop1", "nbr1", "Single Family", 750000.0, 
         ["garage", "pool", "garden"], "San Francisco", "CA", "San Francisco", 
         37.7749, -122.4194, ["residential", "family"]),
        ("prop2", "nbr1", "Condo", 450000.0, 
         ["gym", "concierge", "garage"], "San Francisco", "CA", "San Francisco",
         37.7849, -122.4094, ["urban", "luxury"]),
        ("prop3", "nbr2", "Multi Family", 1200000.0, 
         ["garden", "parking", "balcony"], "San Jose", "CA", "Santa Clara",
         37.3382, -121.8863, ["investment", "residential"]),
    ]
    
    return spark.createDataFrame(data, schema)


def create_test_neighborhoods(spark):
    """Create test neighborhood data."""
    schema = StructType([
        StructField("neighborhood_id", StringType(), False),
        StructField("name", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("county", StringType(), True),
        StructField("aggregated_topics", ArrayType(StringType()), True),
    ])
    
    data = [
        ("nbr1", "Downtown", "San Francisco", "CA", "San Francisco", 
         ["urban", "business", "nightlife"]),
        ("nbr2", "Willow Glen", "San Jose", "CA", "Santa Clara",
         ["residential", "family", "quiet"]),
    ]
    
    return spark.createDataFrame(data, schema)


def create_test_features(spark):
    """Create test feature nodes."""
    from data_pipeline.enrichment.feature_extractor import FeatureExtractor
    
    properties_df = create_test_properties(spark)
    extractor = FeatureExtractor(spark)
    return extractor.extract(properties_df)


def create_test_property_types(spark):
    """Create test property type nodes."""
    from data_pipeline.enrichment.entity_extractors import PropertyTypeExtractor
    
    properties_df = create_test_properties(spark)
    extractor = PropertyTypeExtractor(spark)
    return extractor.extract_property_types(properties_df)


def create_test_price_ranges(spark):
    """Create test price range nodes."""
    from data_pipeline.enrichment.entity_extractors import PriceRangeExtractor
    
    properties_df = create_test_properties(spark)
    extractor = PriceRangeExtractor(spark)
    return extractor.extract_price_ranges(properties_df)


def create_test_counties(spark):
    """Create test county nodes."""
    schema = StructType([
        StructField("id", StringType(), False),
        StructField("name", StringType(), True),
        StructField("state", StringType(), True),
        StructField("latitude", FloatType(), True),
        StructField("longitude", FloatType(), True),
    ])
    
    data = [
        ("county_sf_ca", "San Francisco", "CA", 37.7749, -122.4194),
        ("county_sc_ca", "Santa Clara", "CA", 37.3541, -121.9552),
    ]
    
    return spark.createDataFrame(data, schema)


def create_test_topic_clusters(spark):
    """Create test topic cluster nodes."""
    from data_pipeline.enrichment.topic_extractor import TopicExtractor
    
    # Create test Wikipedia data with topics
    wiki_schema = StructType([
        StructField("page_id", StringType(), False),
        StructField("key_topics", ArrayType(StringType()), True),
    ])
    
    wiki_data = [
        ("wiki1", ["urban", "business", "technology"]),
        ("wiki2", ["residential", "family", "schools"]),
        ("wiki3", ["luxury", "shopping", "entertainment"]),
    ]
    
    wiki_df = spark.createDataFrame(wiki_data, wiki_schema)
    extractor = TopicExtractor(spark)
    return extractor.extract_topic_clusters(wiki_df)


def test_has_feature_relationships(spark):
    """Test HAS_FEATURE relationship building."""
    print("\n🧪 Testing HAS_FEATURE Relationships...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    properties_df = create_test_properties(spark)
    features_df = create_test_features(spark)
    
    builder = RelationshipBuilder(spark)
    has_feature_df = builder.build_has_feature_relationships(properties_df, features_df)
    
    if has_feature_df is None:
        print("❌ Failed to build HAS_FEATURE relationships")
        return False
    
    count = has_feature_df.count()
    print(f"✅ Created {count} HAS_FEATURE relationships")
    
    # Show sample relationships
    print("📊 Sample relationships:")
    has_feature_df.select("from_id", "to_id", "is_primary", "verified").show(5, truncate=False)
    
    return count > 0


def test_of_type_relationships(spark):
    """Test OF_TYPE relationship building."""
    print("\n🧪 Testing OF_TYPE Relationships...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    properties_df = create_test_properties(spark)
    property_types_df = create_test_property_types(spark)
    
    builder = RelationshipBuilder(spark)
    of_type_df = builder.build_of_type_relationships(properties_df, property_types_df)
    
    if of_type_df is None:
        print("❌ Failed to build OF_TYPE relationships")
        return False
    
    count = of_type_df.count()
    print(f"✅ Created {count} OF_TYPE relationships")
    
    # Show sample relationships
    print("📊 Sample relationships:")
    of_type_df.select("from_id", "to_id", "confidence", "is_primary").show(5, truncate=False)
    
    return count > 0


def test_in_price_range_relationships(spark):
    """Test IN_PRICE_RANGE relationship building."""
    print("\n🧪 Testing IN_PRICE_RANGE Relationships...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    properties_df = create_test_properties(spark)
    price_ranges_df = create_test_price_ranges(spark)
    
    builder = RelationshipBuilder(spark)
    in_range_df = builder.build_in_price_range_relationships(properties_df, price_ranges_df)
    
    if in_range_df is None:
        print("❌ Failed to build IN_PRICE_RANGE relationships")
        return False
    
    count = in_range_df.count()
    print(f"✅ Created {count} IN_PRICE_RANGE relationships")
    
    # Show sample relationships
    print("📊 Sample relationships:")
    in_range_df.select("from_id", "to_id", "price_percentile", "actual_price").show(5, truncate=False)
    
    return count > 0


def test_in_county_relationships(spark):
    """Test IN_COUNTY relationship building."""
    print("\n🧪 Testing IN_COUNTY Relationships...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    neighborhoods_df = create_test_neighborhoods(spark)
    counties_df = create_test_counties(spark)
    
    builder = RelationshipBuilder(spark)
    in_county_df = builder.build_in_county_relationships(
        neighborhoods_df, counties_df, "neighborhood"
    )
    
    if in_county_df is None:
        print("❌ Failed to build IN_COUNTY relationships")
        return False
    
    count = in_county_df.count()
    print(f"✅ Created {count} IN_COUNTY relationships")
    
    # Show sample relationships
    print("📊 Sample relationships:")
    in_county_df.select("from_id", "to_id", "hierarchy_level").show(5, truncate=False)
    
    return count > 0


def test_in_topic_cluster_relationships(spark):
    """Test IN_TOPIC_CLUSTER relationship building."""
    print("\n🧪 Testing IN_TOPIC_CLUSTER Relationships...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    neighborhoods_df = create_test_neighborhoods(spark)
    topic_clusters_df = create_test_topic_clusters(spark)
    
    builder = RelationshipBuilder(spark)
    in_cluster_df = builder.build_in_topic_cluster_relationships(
        neighborhoods_df, topic_clusters_df, "neighborhood", "aggregated_topics"
    )
    
    if in_cluster_df is None:
        print("❌ Failed to build IN_TOPIC_CLUSTER relationships")
        return False
    
    count = in_cluster_df.count()
    print(f"✅ Created {count} IN_TOPIC_CLUSTER relationships")
    
    # Show sample relationships
    print("📊 Sample relationships:")
    in_cluster_df.select("from_id", "to_id", "relevance_score", "confidence").show(5, truncate=False)
    
    return count > 0


def test_all_extended_relationships(spark):
    """Test building all extended relationships at once."""
    print("\n🧪 Testing All Extended Relationships Together...")
    
    from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
    
    # Create all test data
    properties_df = create_test_properties(spark)
    neighborhoods_df = create_test_neighborhoods(spark)
    features_df = create_test_features(spark)
    property_types_df = create_test_property_types(spark)
    price_ranges_df = create_test_price_ranges(spark)
    counties_df = create_test_counties(spark)
    topic_clusters_df = create_test_topic_clusters(spark)
    
    # Build all relationships
    builder = RelationshipBuilder(spark)
    all_relationships = builder.build_extended_relationships(
        properties_df=properties_df,
        neighborhoods_df=neighborhoods_df,
        features_df=features_df,
        property_types_df=property_types_df,
        price_ranges_df=price_ranges_df,
        counties_df=counties_df,
        topic_clusters_df=topic_clusters_df
    )
    
    print("\n📊 Relationship Summary:")
    for rel_type, df in all_relationships.items():
        if df is not None:
            count = df.count()
            print(f"   • {rel_type}: {count} relationships")
    
    return len(all_relationships) > 0


def main():
    """Run all Phase 3 relationship tests."""
    print("🚀 Starting Phase 3 Relationship Tests...")
    print("="*60)
    
    spark = create_spark_session()
    
    try:
        results = []
        
        # Test individual relationship builders
        results.append(("HAS_FEATURE", test_has_feature_relationships(spark)))
        results.append(("OF_TYPE", test_of_type_relationships(spark)))
        results.append(("IN_PRICE_RANGE", test_in_price_range_relationships(spark)))
        results.append(("IN_COUNTY", test_in_county_relationships(spark)))
        results.append(("IN_TOPIC_CLUSTER", test_in_topic_cluster_relationships(spark)))
        
        # Test all relationships together
        results.append(("ALL_EXTENDED", test_all_extended_relationships(spark)))
        
        # Summary
        print("\n" + "="*60)
        print("🎯 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_name:20} : {status}")
        
        print(f"\n📈 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All extended relationship tests passed successfully!")
            return 0
        else:
            print("⚠️ Some tests failed. Please review the output above.")
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