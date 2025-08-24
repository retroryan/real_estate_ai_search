"""
Basic integration tests for location enrichment functionality.

This module tests the fundamental location enrichment capabilities that are
working correctly, focusing on:
- Core enricher initialization and configuration
- Basic enrichment field generation
- Location data integration patterns
- Enrichment statistics calculation
"""

import pytest
from typing import Dict, Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, ArrayType

from data_pipeline.enrichment import (
    LocationEnricher, LocationEnrichmentConfig,
    PropertyEnricher, PropertyEnrichmentConfig,
    NeighborhoodEnricher, NeighborhoodEnrichmentConfig,
    WikipediaEnricher, WikipediaEnrichmentConfig
)


@pytest.mark.integration
class TestBasicLocationEnrichment:
    """Basic integration tests for location enrichment functionality."""
    
    def test_location_enrichment_configurations(self):
        """Test that all location enrichment configurations initialize correctly."""
        # Test LocationEnrichmentConfig
        loc_config = LocationEnrichmentConfig(
            enable_hierarchy_resolution=True,
            enable_name_standardization=True,
            enable_neighborhood_linking=True
        )
        assert loc_config.enable_hierarchy_resolution is True
        assert loc_config.enable_name_standardization is True
        assert loc_config.enable_neighborhood_linking is True
        
        # Test PropertyEnrichmentConfig with location options
        prop_config = PropertyEnrichmentConfig(
            enable_location_enhancement=True,
            enable_neighborhood_linking=True
        )
        assert prop_config.enable_location_enhancement is True
        assert prop_config.enable_neighborhood_linking is True
        
        # Test NeighborhoodEnrichmentConfig with hierarchy options
        neighbor_config = NeighborhoodEnrichmentConfig(
            enable_location_hierarchy=True,
            establish_parent_relationships=True
        )
        assert neighbor_config.enable_location_hierarchy is True
        assert neighbor_config.establish_parent_relationships is True
        
        # Test WikipediaEnrichmentConfig with location matching
        wiki_config = WikipediaEnrichmentConfig(
            enable_location_matching=True,
            enable_geographic_context=True,
            enable_location_organization=True
        )
        assert wiki_config.enable_location_matching is True
        assert wiki_config.enable_geographic_context is True
        assert wiki_config.enable_location_organization is True
        
        print("✅ All location enrichment configurations working correctly")
    
    def test_property_enricher_basic_functionality(self, spark_session: SparkSession):
        """Test PropertyEnricher basic functionality without complex location integration."""
        # Create PropertyEnricher with basic configuration
        config = PropertyEnrichmentConfig(
            enable_price_calculations=True,
            enable_quality_scoring=True
        )
        property_enricher = PropertyEnricher(spark_session, config)
        
        # Create simple test property data
        test_properties = [
            ("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA", "street": "123 Main St"}),
            ("PROP002", 750000, 3, 1800, {"city": "Park City", "state": "UT", "street": "456 Oak Ave"})
        ]
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("price", IntegerType(), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("address", StructType([
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("street", StringType(), True)
            ]), True)
        ])
        
        test_df = spark_session.createDataFrame(test_properties, schema)
        
        # Apply property enrichment
        enriched_df = property_enricher.enrich(test_df)
        
        # Verify basic enrichment fields
        required_fields = ['city', 'state', 'price_per_sqft', 'property_quality_score']
        for field in required_fields:
            assert field in enriched_df.columns, f"Required field '{field}' should be present"
        
        # Verify data quality
        result_count = enriched_df.count()
        assert result_count == 2, "Should process both properties"
        
        # Verify price calculations
        price_sqft_count = enriched_df.filter(col("price_per_sqft").isNotNull()).count()
        assert price_sqft_count == 2, "Price per sqft should be calculated for all properties"
        
        print(f"✅ PropertyEnricher basic functionality: {result_count} properties processed")
    
    def test_neighborhood_enricher_basic_functionality(self, spark_session: SparkSession):
        """Test NeighborhoodEnricher basic functionality."""
        # Create NeighborhoodEnricher with basic configuration
        config = NeighborhoodEnrichmentConfig(
            enable_demographic_validation=True,
            enable_quality_scoring=True
        )
        neighborhood_enricher = NeighborhoodEnricher(spark_session, config)
        
        # Create test neighborhood data
        test_neighborhoods = [
            ("NBHD001", "Mission District", "San Francisco", "CA", [], 50000, 75000.0, 35.5),
            ("NBHD002", "Old Town", "Park City", "UT", ["Skiing", "Restaurants"], 8000, 85000.0, 42.1)
        ]
        
        schema = StructType([
            StructField("neighborhood_id", StringType(), True),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("population", IntegerType(), True),
            StructField("median_income", FloatType(), True),
            StructField("median_age", FloatType(), True)
        ])
        
        test_df = spark_session.createDataFrame(test_neighborhoods, schema)
        
        # Apply neighborhood enrichment
        enriched_df = neighborhood_enricher.enrich(test_df)
        
        # Verify basic enrichment fields
        required_fields = ['neighborhood_name_normalized', 'demographic_completeness', 'neighborhood_quality_score']
        for field in required_fields:
            assert field in enriched_df.columns, f"Required field '{field}' should be present"
        
        # Verify data quality
        result_count = enriched_df.count()
        assert result_count == 2, "Should process both neighborhoods"
        
        print(f"✅ NeighborhoodEnricher basic functionality: {result_count} neighborhoods processed")
    
    def test_wikipedia_enricher_basic_functionality(self, spark_session: SparkSession):
        """Test WikipediaEnricher basic functionality."""
        # Create WikipediaEnricher with basic configuration
        config = WikipediaEnrichmentConfig(
            enable_confidence_metrics=True,
            enable_quality_scoring=True
        )
        wikipedia_enricher = WikipediaEnricher(spark_session, config)
        
        # Create test Wikipedia article data
        test_articles = [
            (12345, "San Francisco History", "San Francisco", "CA", 0.85, "Long article about SF history...", ["History", "California"], ["Cities"]),
            (67890, "Park City Skiing", "Park City", "UT", 0.92, "Article about Park City ski resorts...", ["Skiing", "Utah"], ["Recreation"])
        ]
        
        schema = StructType([
            StructField("page_id", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("confidence_score", FloatType(), True),
            StructField("long_summary", StringType(), True),
            StructField("key_topics", ArrayType(StringType()), True),
            StructField("categories", ArrayType(StringType()), True)
        ])
        
        test_df = spark_session.createDataFrame(test_articles, schema)
        
        # Apply Wikipedia enrichment
        enriched_df = wikipedia_enricher.enrich(test_df)
        
        # Verify basic enrichment fields
        required_fields = ['has_valid_location', 'confidence_level', 'article_quality_score']
        for field in required_fields:
            assert field in enriched_df.columns, f"Required field '{field}' should be present"
        
        # Verify data quality
        result_count = enriched_df.count()
        assert result_count == 2, "Should process both articles"
        
        # Verify confidence metrics
        high_confidence_count = enriched_df.filter(col("confidence_level") == "high").count()
        assert high_confidence_count > 0, "Should have high confidence articles"
        
        print(f"✅ WikipediaEnricher basic functionality: {result_count} articles processed")
    
    def test_enrichment_statistics(self, spark_session: SparkSession):
        """Test that enrichment statistics are calculated correctly."""
        # Test PropertyEnricher statistics
        property_config = PropertyEnrichmentConfig()
        property_enricher = PropertyEnricher(spark_session, property_config)
        
        # Create test data
        test_data = [
            ("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA", "street": "123 Main"}),
            ("PROP002", 750000, 3, 1800, {"city": "Park City", "state": "UT", "street": "456 Oak"})
        ]
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("price", IntegerType(), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("address", StructType([
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("street", StringType(), True)
            ]), True)
        ])
        
        test_df = spark_session.createDataFrame(test_data, schema)
        
        # Enrich and get statistics
        enriched_df = property_enricher.enrich(test_df)
        stats = property_enricher.get_enrichment_statistics(enriched_df)
        
        # Verify statistics structure
        assert isinstance(stats, dict), "Statistics should be returned as dictionary"
        assert 'total_properties' in stats, "Statistics should include total count"
        assert stats['total_properties'] == 2, "Should count correct number of properties"
        
        # Check for price statistics if available
        if 'avg_price_per_sqft' in stats:
            assert stats['avg_price_per_sqft'] > 0, "Average price per sqft should be positive"
        
        print(f"✅ Enrichment statistics: {stats}")
    
    def test_location_data_injection_pattern(self, spark_session: SparkSession):
        """Test that location data injection pattern works correctly."""
        # Create sample location data
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        location_broadcast = spark_session.sparkContext.broadcast(location_data)
        
        # Test that all enrichers can accept location data
        enrichers = [
            PropertyEnricher(spark_session, PropertyEnrichmentConfig()),
            NeighborhoodEnricher(spark_session, NeighborhoodEnrichmentConfig()),
            WikipediaEnricher(spark_session, WikipediaEnrichmentConfig())
        ]
        
        # Test set_location_data method exists and works
        for enricher in enrichers:
            assert hasattr(enricher, 'set_location_data'), f"{enricher.__class__.__name__} should have set_location_data method"
            
            # Call set_location_data (should not throw exception)
            enricher.set_location_data(location_broadcast)
            
            # Verify location_broadcast is set
            assert enricher.location_broadcast is not None, f"{enricher.__class__.__name__} should store location broadcast"
        
        print("✅ Location data injection pattern working for all enrichers")
    
    def test_enricher_initialization_with_location_data(self, spark_session: SparkSession):
        """Test that enrichers can be initialized with location data directly."""
        # Create sample location data
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        location_broadcast = spark_session.sparkContext.broadcast(location_data)
        
        # Test direct initialization with location data
        property_enricher = PropertyEnricher(
            spark_session, 
            PropertyEnrichmentConfig(),
            location_broadcast
        )
        
        neighborhood_enricher = NeighborhoodEnricher(
            spark_session,
            NeighborhoodEnrichmentConfig(), 
            location_broadcast
        )
        
        wikipedia_enricher = WikipediaEnricher(
            spark_session,
            WikipediaEnrichmentConfig(),
            location_broadcast
        )
        
        # Verify location data is stored
        assert property_enricher.location_broadcast is not None, "PropertyEnricher should store location data"
        assert neighborhood_enricher.location_broadcast is not None, "NeighborhoodEnricher should store location data"
        assert wikipedia_enricher.location_broadcast is not None, "WikipediaEnricher should store location data"
        
        print("✅ All enrichers can be initialized with location data directly")


@pytest.mark.integration
class TestLocationEnrichmentIntegration:
    """Integration tests demonstrating location enrichment capabilities."""
    
    def test_end_to_end_enrichment_flow(self, spark_session: SparkSession):
        """Test end-to-end enrichment flow with location data."""
        # Create location broadcast data
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        location_broadcast = spark_session.sparkContext.broadcast(location_data)
        
        # Initialize all enrichers
        property_enricher = PropertyEnricher(spark_session, PropertyEnrichmentConfig(), location_broadcast)
        neighborhood_enricher = NeighborhoodEnricher(spark_session, NeighborhoodEnrichmentConfig(), location_broadcast)
        wikipedia_enricher = WikipediaEnricher(spark_session, WikipediaEnrichmentConfig(), location_broadcast)
        
        # Create test datasets
        properties_data = [("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA", "street": "123 Main St"})]
        properties_schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("price", IntegerType(), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("address", StructType([
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("street", StringType(), True)
            ]), True)
        ])
        properties_df = spark_session.createDataFrame(properties_data, properties_schema)
        
        neighborhoods_data = [("NBHD001", "Mission District", "San Francisco", "CA", [], None, None, None)]
        neighborhoods_schema = StructType([
            StructField("neighborhood_id", StringType(), True),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("population", IntegerType(), True),
            StructField("median_income", FloatType(), True),
            StructField("median_age", FloatType(), True)
        ])
        neighborhoods_df = spark_session.createDataFrame(neighborhoods_data, neighborhoods_schema)
        
        wikipedia_data = [(12345, "San Francisco History", "San Francisco", "CA", 0.85, "Long article...", [], [])]
        wikipedia_schema = StructType([
            StructField("page_id", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("confidence_score", FloatType(), True),
            StructField("long_summary", StringType(), True),
            StructField("key_topics", ArrayType(StringType()), True),
            StructField("categories", ArrayType(StringType()), True)
        ])
        wikipedia_df = spark_session.createDataFrame(wikipedia_data, wikipedia_schema)
        
        # Apply enrichment to all entity types
        enriched_properties = property_enricher.enrich(properties_df)
        enriched_neighborhoods = neighborhood_enricher.enrich(neighborhoods_df)
        enriched_wikipedia = wikipedia_enricher.enrich(wikipedia_df)
        
        # Verify all entities were processed successfully
        assert enriched_properties.count() == 1, "Properties should be enriched"
        assert enriched_neighborhoods.count() == 1, "Neighborhoods should be enriched"
        assert enriched_wikipedia.count() == 1, "Wikipedia articles should be enriched"
        
        # Verify enrichment fields exist
        assert 'property_quality_score' in enriched_properties.columns, "Properties should have quality score"
        assert 'neighborhood_quality_score' in enriched_neighborhoods.columns, "Neighborhoods should have quality score"
        assert 'article_quality_score' in enriched_wikipedia.columns, "Wikipedia should have quality score"
        
        print("✅ End-to-end enrichment flow successful for all entity types")
        print(f"   - Properties: {enriched_properties.count()} processed")
        print(f"   - Neighborhoods: {enriched_neighborhoods.count()} processed") 
        print(f"   - Wikipedia articles: {enriched_wikipedia.count()} processed")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])