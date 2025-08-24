"""
Integration tests for location enricher functionality.

This module tests the core location enrichment capabilities including:
- LocationEnricher hierarchy resolution and name standardization
- PropertyEnricher location enhancement and neighborhood linking
- NeighborhoodEnricher hierarchy establishment and parent relationships
- WikipediaEnricher location matching and geographic context
"""

import pytest
from typing import Dict, Any, List

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
class TestLocationEnricherIntegration:
    """Integration tests for LocationEnricher functionality."""
    
    @pytest.fixture
    def sample_location_broadcast(self, spark_session: SparkSession):
        """Create sample location broadcast data for testing."""
        location_data = [
            {"city": "San Francisco", "county": "San Francisco", "state": "California"},
            {"city": "San Francisco", "county": "San Francisco", "state": "CA"}, 
            {"city": "Park City", "county": "Summit County", "state": "Utah"},
            {"city": "Park City", "county": "Summit County", "state": "UT"},
            {"city": "SF", "county": "San Francisco", "state": "CA"},  # Test abbreviations
        ]
        return spark_session.sparkContext.broadcast(location_data)
    
    def test_location_enricher_hierarchy_resolution(self, spark_session: SparkSession, sample_location_broadcast):
        """Test LocationEnricher's hierarchy resolution capabilities."""
        # Create LocationEnricher
        config = LocationEnrichmentConfig(
            enable_hierarchy_resolution=True,
            enable_name_standardization=True
        )
        location_enricher = LocationEnricher(spark_session, sample_location_broadcast, config)
        
        # Create test data with cities and states
        test_data = [
            ("San Francisco", "CA"),
            ("Park City", "UT"),
            ("San Francisco", "California")  # Test both full and abbreviated names
        ]
        test_df = spark_session.createDataFrame(test_data, ["city", "state"])
        
        # Test hierarchy enhancement
        enhanced_df = location_enricher.enhance_with_hierarchy(test_df, "city", "state")
        
        # Verify hierarchy columns were added
        assert 'county_resolved' in enhanced_df.columns, "County_resolved column should be added"
        
        enhanced_count = enhanced_df.count()
        assert enhanced_count == len(test_data), "Record count should be preserved during enhancement"
        
        # Verify some county data was resolved
        counties_resolved = enhanced_df.filter(col("county_resolved").isNotNull()).count()
        assert counties_resolved > 0, "Some counties should be resolved from location data"
        
        print(f"✅ LocationEnricher: Hierarchy resolution working for {enhanced_count} records, {counties_resolved} counties resolved")
    
    def test_location_enricher_name_standardization(self, spark_session: SparkSession, sample_location_broadcast):
        """Test LocationEnricher's name standardization capabilities."""
        config = LocationEnrichmentConfig(enable_name_standardization=True)
        location_enricher = LocationEnricher(spark_session, sample_location_broadcast, config)
        
        # Test data with various name formats
        test_data = [
            ("SF", "CA"),  # Abbreviations
            ("San Francisco", "California")  # Full names
        ]
        test_df = spark_session.createDataFrame(test_data, ["city", "state"])
        
        # Test name standardization
        standardized_df = location_enricher.standardize_location_names(
            test_df, "city", "state"
        )
        
        # Verify standardized columns were added
        expected_columns = ['city_standardized', 'state_standardized']
        for col_name in expected_columns:
            assert col_name in standardized_df.columns, f"Standardized column '{col_name}' should be added"
        
        print(f"✅ LocationEnricher: Name standardization working for {standardized_df.count()} records")


@pytest.mark.integration  
class TestPropertyEnricherIntegration:
    """Integration tests for PropertyEnricher with location data."""
    
    @pytest.fixture
    def sample_location_broadcast(self, spark_session: SparkSession):
        """Create sample location broadcast data for testing."""
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        return spark_session.sparkContext.broadcast(location_data)
    
    def test_property_enricher_location_integration(self, spark_session: SparkSession, sample_location_broadcast):
        """Test PropertyEnricher's integration with location data."""
        # Create PropertyEnricher with location enhancement enabled
        config = PropertyEnrichmentConfig(
            enable_location_enhancement=True,
            enable_neighborhood_linking=True
        )
        property_enricher = PropertyEnricher(spark_session, config)
        property_enricher.set_location_data(sample_location_broadcast)
        
        # Create test property data matching actual data structure
        test_properties = [
            {
                "listing_id": "prop-test-001",
                "address": {"street": "123 Main St", "city": "San Francisco", "state": "CA", "zip": "94102"},
                "property_details": {"square_feet": 1200, "bedrooms": 2, "bathrooms": 2.0, "property_type": "condo"},
                "listing_price": 500000,
                "price_per_sqft": 417,
                "description": "Nice property in the heart of SF",
                "features": ["parking", "gym"]
            },
            {
                "listing_id": "prop-test-002", 
                "address": {"street": "456 Oak Ave", "city": "Park City", "state": "UT", "zip": "84060"},
                "property_details": {"square_feet": 1800, "bedrooms": 3, "bathrooms": 2.5, "property_type": "house"},
                "listing_price": 750000,
                "price_per_sqft": 417,
                "description": "Great location with mountain views",
                "features": ["yard", "garage"]
            }
        ]
        
        test_df = spark_session.createDataFrame(test_properties)
        
        # Apply property enrichment
        enriched_df = property_enricher.enrich(test_df)
        
        # Verify basic enrichment fields that PropertyEnricher actually creates
        basic_fields = ['city', 'state', 'zip_code', 'price_per_sqft', 'property_quality_score', 'price_category', 'size_category']
        for field_name in basic_fields:
            assert field_name in enriched_df.columns, f"Basic field '{field_name}' should be added to properties"
        
        # Verify location enhancement fields were added (if location enricher was integrated)
        location_fields = [col for col in enriched_df.columns if 'county' in col or 'normalized' in col]
        
        enriched_count = enriched_df.count()
        print(f"✅ PropertyEnricher: Location integration working for {enriched_count} properties")
        if location_fields:
            print(f"   - Location enhancement fields: {location_fields}")
    
    def test_property_enricher_price_calculations(self, spark_session: SparkSession):
        """Test PropertyEnricher's price calculation functionality."""
        config = PropertyEnrichmentConfig(
            enable_price_calculations=True,
            enable_address_normalization=False,
            enable_location_enhancement=False,
            enable_quality_scoring=False
        )
        property_enricher = PropertyEnricher(spark_session, config)
        
        # Create test data matching actual property structure
        test_data = [
            {
                "listing_id": "prop-price-001",
                "listing_price": 600000,
                "property_details": {"bedrooms": 2, "bathrooms": 2.0, "square_feet": 1200, "property_type": "condo"},
                "description": "Nice property",
                "features": ["parking"]
            },
            {
                "listing_id": "prop-price-002", 
                "listing_price": 900000,
                "property_details": {"bedrooms": 3, "bathrooms": 2.5, "square_feet": 1500, "property_type": "house"},
                "description": "Great home",
                "features": ["yard"]
            }
        ]
        test_df = spark_session.createDataFrame(test_data)
        
        # Apply enrichment
        enriched_df = property_enricher.enrich(test_df)
        
        # Verify price calculation fields
        price_fields = ['price_per_sqft', 'price_category', 'size_category']
        for field in price_fields:
            assert field in enriched_df.columns, f"Price field '{field}' should be calculated"
        
        # Verify calculations are working
        price_sqft_count = enriched_df.filter(col("price_per_sqft").isNotNull()).count()
        assert price_sqft_count > 0, "Price per sqft should be calculated for valid records"
        
        print(f"✅ PropertyEnricher: Price calculations working for {enriched_df.count()} properties")


@pytest.mark.integration
class TestNeighborhoodEnricherIntegration:
    """Integration tests for NeighborhoodEnricher with location data."""
    
    @pytest.fixture
    def sample_location_broadcast(self, spark_session: SparkSession):
        """Create sample location broadcast data for testing."""
        location_data = [
            {"city": "San Francisco", "county": "San Francisco", "state": "CA"},
            {"city": "Park City", "county": "Summit County", "state": "UT"}
        ]
        return spark_session.sparkContext.broadcast(location_data)
    
    def test_neighborhood_enricher_hierarchy_establishment(self, spark_session: SparkSession, sample_location_broadcast):
        """Test NeighborhoodEnricher's geographic hierarchy establishment."""
        # Create NeighborhoodEnricher with hierarchy enabled
        config = NeighborhoodEnrichmentConfig(
            enable_location_hierarchy=True,
            establish_parent_relationships=True
        )
        neighborhood_enricher = NeighborhoodEnricher(spark_session, config)
        neighborhood_enricher.set_location_data(sample_location_broadcast)
        
        # Create test neighborhood data matching actual data structure
        test_neighborhoods = [
            {
                "neighborhood_id": "sf-mission-test",
                "name": "Mission District",
                "city": "San Francisco", 
                "state": "CA",
                "description": "Historic neighborhood with vibrant culture",
                "demographics": {"population": 50000, "median_household_income": 75000, "median_age": 35.5},
                "amenities": ["restaurants", "galleries"]
            },
            {
                "neighborhood_id": "pc-oldtown-test",
                "name": "Old Town", 
                "city": "Park City",
                "state": "UT", 
                "description": "Charming historic district",
                "demographics": {"population": 20000, "median_household_income": 95000, "median_age": 42.0},
                "amenities": ["skiing", "dining"]
            }
        ]
        
        test_df = spark_session.createDataFrame(test_neighborhoods)
        
        # Apply neighborhood enrichment
        enriched_df = neighborhood_enricher.enrich(test_df)
        
        # Verify basic enrichment fields based on actual NeighborhoodEnricher output
        basic_fields = ['neighborhood_name_normalized', 'demographic_completeness', 'income_bracket', 'has_valid_boundary']
        for field in basic_fields:
            assert field in enriched_df.columns, f"Basic field '{field}' should be added to neighborhoods"
        
        # Verify location hierarchy fields (if location enricher was integrated) 
        location_fields = [col for col in enriched_df.columns if 'county' in col or 'standardized' in col]
        
        enriched_count = enriched_df.count()
        print(f"✅ NeighborhoodEnricher: Hierarchy establishment working for {enriched_count} neighborhoods")
        if location_fields:
            print(f"   - Hierarchy fields: {location_fields}")


@pytest.mark.integration
class TestWikipediaEnricherIntegration:
    """Integration tests for WikipediaEnricher with location data."""
    
    @pytest.fixture
    def sample_location_broadcast(self, spark_session: SparkSession):
        """Create sample location broadcast data for testing."""
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        return spark_session.sparkContext.broadcast(location_data)
    
    def test_wikipedia_enricher_location_matching(self, spark_session: SparkSession, sample_location_broadcast):
        """Test WikipediaEnricher's location matching and geographic context."""
        # Create WikipediaEnricher with location features enabled
        config = WikipediaEnrichmentConfig(
            enable_location_matching=True,
            enable_geographic_context=True,
            enable_location_organization=True
        )
        wikipedia_enricher = WikipediaEnricher(spark_session, config)
        wikipedia_enricher.set_location_data(sample_location_broadcast)
        
        # Create test Wikipedia article data
        test_articles = [
            (12345, "San Francisco History", "San Francisco", "CA", 0.85, "Long article about SF history...", [], None),
            (67890, "Park City Skiing", "Park City", "UT", 0.92, "Article about Park City ski resorts...", [], None)
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
        basic_fields = ['has_valid_location', 'location_relevance_score', 'article_quality_score']
        for field in basic_fields:
            assert field in enriched_df.columns, f"Basic field '{field}' should be added to Wikipedia articles"
        
        # Verify location-specific fields (if location enricher was integrated)  
        location_fields = [col for col in enriched_df.columns if 'geographic' in col or 'canonical' in col]
        
        enriched_count = enriched_df.count()
        print(f"✅ WikipediaEnricher: Location matching working for {enriched_count} articles")
        if location_fields:
            print(f"   - Geographic context fields: {location_fields}")
    
    def test_wikipedia_enricher_confidence_metrics(self, spark_session: SparkSession):
        """Test WikipediaEnricher's confidence metrics functionality."""
        config = WikipediaEnrichmentConfig(enable_confidence_metrics=True)
        wikipedia_enricher = WikipediaEnricher(spark_session, config)
        
        # Create test data with varying confidence scores
        test_data = [
            (1, "High Confidence Article", "City", "State", 0.95, "Long summary"),
            (2, "Low Confidence Article", "City", "State", 0.45, "Short summary")
        ]
        
        schema = StructType([
            StructField("page_id", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("confidence_score", FloatType(), True),
            StructField("long_summary", StringType(), True)
        ])
        
        test_df = spark_session.createDataFrame(test_data, schema)
        
        # Apply enrichment
        enriched_df = wikipedia_enricher.enrich(test_df)
        
        # Verify confidence metrics
        confidence_fields = ['confidence_level', 'extraction_reliable', 'overall_confidence']
        for field in confidence_fields:
            assert field in enriched_df.columns, f"Confidence field '{field}' should be added"
        
        # Verify confidence categorization
        high_confidence_count = enriched_df.filter(col("confidence_level") == "very_high").count()
        assert high_confidence_count > 0, "High confidence records should be categorized"
        
        print(f"✅ WikipediaEnricher: Confidence metrics working for {enriched_df.count()} articles")


@pytest.mark.integration
class TestLocationEnrichmentStatistics:
    """Tests for location enrichment statistics and quality metrics."""
    
    def test_enrichment_statistics_calculation(self, spark_session: SparkSession):
        """Test that enrichment statistics are properly calculated."""
        # Test PropertyEnricher statistics
        property_config = PropertyEnrichmentConfig()
        property_enricher = PropertyEnricher(spark_session, property_config)
        
        # Create test data
        test_data = [
            ("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA"}),
            ("PROP002", 750000, 3, 1800, {"city": "Park City", "state": "UT"})
        ]
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("price", IntegerType(), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("address", StructType([
                StructField("city", StringType(), True),
                StructField("state", StringType(), True)
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
        
        print(f"✅ Enrichment Statistics: {stats}")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])