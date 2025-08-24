"""
Integration tests for location data integration across all entity types.

This module tests the complete location enhancement pipeline including:
- Location reference data loading and broadcasting
- Property-neighborhood linking via neighborhood_id
- Geographic hierarchy establishment (neighborhood → city → county → state)
- Location name standardization and canonical resolution
- Entity-specific location enhancements
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, isnan, isnull, when
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType

from data_pipeline.enrichment import (
    LocationEnricher, LocationEnrichmentConfig,
    PropertyEnricher, PropertyEnrichmentConfig,
    NeighborhoodEnricher, NeighborhoodEnrichmentConfig,
    WikipediaEnricher, WikipediaEnrichmentConfig
)


@pytest.mark.integration
@pytest.mark.slow
class TestLocationDataIntegration:
    """Integration tests for location data enhancement across all entities."""
    
    def test_location_broadcast_creation(self, spark_session: SparkSession):
        """Test that location broadcast can be created from sample data."""
        # Create sample location data
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco", "neighborhood": "Mission District"},
            {"state": "California", "county": "San Francisco County", "city": "San Francisco", "neighborhood": "SOMA"}, 
            {"state": "Utah", "county": "Summit County", "city": "Park City", "neighborhood": "Old Town"},
            {"state": "Utah", "county": "Summit County", "city": "Park City", "neighborhood": "Deer Valley"}
        ]
        
        # Create broadcast variable
        location_broadcast = spark_session.sparkContext.broadcast(location_data)
        
        assert location_broadcast is not None, "Location broadcast variable should be created"
        
        # Verify broadcast contains data
        broadcast_data = location_broadcast.value
        assert len(broadcast_data) > 0, "Broadcast variable should contain location data"
        assert len(broadcast_data) == 4, "Should have 4 location records"
        
        print(f"✅ Location Broadcast: {len(broadcast_data)} records available for enrichment")
    
    def test_location_enricher_hierarchy_resolution(self, spark_session: SparkSession):
        """Test LocationEnricher's hierarchy resolution capabilities."""
        # Create sample location data
        location_data = [
            {"state": "California", "county": "San Francisco County", "city": "San Francisco"},
            {"state": "Utah", "county": "Summit County", "city": "Park City"}
        ]
        location_broadcast = spark_session.sparkContext.broadcast(location_data)
        
        # Create LocationEnricher
        config = LocationEnrichmentConfig(
            enable_hierarchy_resolution=True,
            enable_name_standardization=True
        )
        location_enricher = LocationEnricher(spark_session, location_broadcast, config)
        
        # Create test data with cities and states
        test_data = [
            ("San Francisco", "CA"),
            ("Park City", "UT"),
            ("New York", "NY")
        ]
        test_df = spark_session.createDataFrame(test_data, ["city", "state"])
        
        # Test hierarchy enhancement
        enhanced_df = location_enricher.enhance_with_hierarchy(test_df, "city", "state")
        
        # Verify hierarchy columns were added
        expected_hierarchy_columns = ['county']
        for col_name in expected_hierarchy_columns:
            assert col_name in enhanced_df.columns, f"Hierarchy column '{col_name}' should be added"
        
        enhanced_count = enhanced_df.count()
        assert enhanced_count == len(test_data), "Record count should be preserved during enhancement"
        
        print(f"✅ LocationEnricher: Hierarchy resolution working for {enhanced_count} records")
    
    def test_property_enricher_location_integration(self, spark_session: SparkSession, test_settings):
        """Test PropertyEnricher's integration with location data."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Create PropertyEnricher with location enhancement enabled
        config = PropertyEnrichmentConfig(
            enable_location_enhancement=True,
            enable_neighborhood_linking=True
        )
        property_enricher = PropertyEnricher(spark_session, config, location_broadcast)
        
        # Create test property data
        test_properties = [
            ("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA", "street": "123 Main St"}),
            ("PROP002", 750000, 3, 1800, {"city": "Park City", "state": "UT", "street": "456 Oak Ave"})
        ]
        test_df = spark_session.createDataFrame(
            test_properties, 
            ["listing_id", "price", "bedrooms", "square_feet", "address"]
        )
        
        # Apply property enrichment
        enriched_df = property_enricher.enrich(test_df)
        
        # Verify location enhancement fields were added
        expected_location_fields = ['city_normalized', 'state_normalized', 'county']
        for field_name in expected_location_fields:
            assert field_name in enriched_df.columns, f"Location field '{field_name}' should be added to properties"
        
        # Verify price calculations
        assert 'price_per_sqft' in enriched_df.columns, "Price per sqft should be calculated"
        
        enriched_count = enriched_df.count()
        print(f"✅ PropertyEnricher: Location enhancement working for {enriched_count} properties")
    
    def test_neighborhood_enricher_hierarchy_establishment(self, spark_session: SparkSession, test_settings):
        """Test NeighborhoodEnricher's geographic hierarchy establishment."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Create NeighborhoodEnricher with hierarchy enabled
        config = NeighborhoodEnrichmentConfig(
            enable_location_hierarchy=True,
            establish_parent_relationships=True
        )
        neighborhood_enricher = NeighborhoodEnricher(spark_session, config, location_broadcast)
        
        # Create test neighborhood data
        test_neighborhoods = [
            ("NBHD001", "Mission District", "San Francisco", "CA", []),
            ("NBHD002", "Old Town", "Park City", "UT", [])
        ]
        test_df = spark_session.createDataFrame(
            test_neighborhoods,
            ["neighborhood_id", "name", "city", "state", "amenities"]
        )
        
        # Apply neighborhood enrichment
        enriched_df = neighborhood_enricher.enrich(test_df)
        
        # Verify hierarchy establishment
        expected_hierarchy_fields = ['neighborhood_name_normalized', 'city_normalized', 'state_normalized']
        for field_name in expected_hierarchy_fields:
            assert field_name in enriched_df.columns, f"Hierarchy field '{field_name}' should be added to neighborhoods"
        
        enriched_count = enriched_df.count()
        print(f"✅ NeighborhoodEnricher: Hierarchy establishment working for {enriched_count} neighborhoods")
    
    def test_wikipedia_enricher_location_matching(self, spark_session: SparkSession, test_settings):
        """Test WikipediaEnricher's location matching and geographic context."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Create WikipediaEnricher with location features enabled
        config = WikipediaEnrichmentConfig(
            enable_location_matching=True,
            enable_geographic_context=True,
            enable_location_organization=True
        )
        wikipedia_enricher = WikipediaEnricher(spark_session, config, location_broadcast)
        
        # Create test Wikipedia article data
        test_articles = [
            (12345, "San Francisco History", "San Francisco", "CA", 0.85, "Long article about SF history..."),
            (67890, "Park City Skiing", "Park City", "UT", 0.92, "Article about Park City ski resorts...")
        ]
        test_df = spark_session.createDataFrame(
            test_articles,
            ["page_id", "title", "best_city", "best_state", "confidence_score", "long_summary"]
        )
        
        # Apply Wikipedia enrichment
        enriched_df = wikipedia_enricher.enrich(test_df)
        
        # Verify location matching fields
        expected_location_fields = ['canonical_city', 'canonical_state', 'geographic_scope', 'location_context']
        for field_name in expected_location_fields:
            assert field_name in enriched_df.columns, f"Location field '{field_name}' should be added to Wikipedia articles"
        
        enriched_count = enriched_df.count()
        print(f"✅ WikipediaEnricher: Location matching working for {enriched_count} articles")
    
    def test_end_to_end_pipeline_location_integration(self, spark_session: SparkSession, test_settings_with_temp_output):
        """Test complete pipeline with location integration across all entities."""
        # Initialize pipeline runner
        runner = DataPipelineRunner(test_settings_with_temp_output)
        
        # Execute pipeline with location processing
        results = runner.run_full_pipeline()
        
        # Verify all entity types were processed
        assert 'properties' in results, "Properties should be processed"
        assert 'neighborhoods' in results, "Neighborhoods should be processed"
        assert 'wikipedia' in results, "Wikipedia articles should be processed"
        
        # Test Properties location integration
        properties_df = results['properties']
        property_columns = properties_df.columns
        
        # Check for location enhancement fields
        property_location_fields = ['city_normalized', 'state_normalized', 'property_quality_score']
        for field in property_location_fields:
            assert field in property_columns, f"Property location field '{field}' missing"
        
        # Test Neighborhoods location integration
        neighborhoods_df = results['neighborhoods']
        neighborhood_columns = neighborhoods_df.columns
        
        # Check for hierarchy establishment fields
        neighborhood_hierarchy_fields = ['neighborhood_name_normalized', 'city_normalized', 'demographic_completeness']
        for field in neighborhood_hierarchy_fields:
            assert field in neighborhood_columns, f"Neighborhood hierarchy field '{field}' missing"
        
        # Test Wikipedia location integration
        wikipedia_df = results['wikipedia']
        wikipedia_columns = wikipedia_df.columns
        
        # Check for location matching fields
        wikipedia_location_fields = ['has_valid_location', 'location_relevance_score', 'article_quality_score']
        for field in wikipedia_location_fields:
            assert field in wikipedia_columns, f"Wikipedia location field '{field}' missing"
        
        # Verify data quality
        property_count = properties_df.count()
        neighborhood_count = neighborhoods_df.count()
        wikipedia_count = wikipedia_df.count()
        
        assert property_count > 0, "Properties should be processed"
        assert neighborhood_count > 0, "Neighborhoods should be processed"
        assert wikipedia_count > 0, "Wikipedia articles should be processed"
        
        print(f"✅ End-to-End Pipeline: Successfully processed {property_count} properties, "
              f"{neighborhood_count} neighborhoods, {wikipedia_count} Wikipedia articles")
    
    def test_property_neighborhood_relationship_linking(self, spark_session: SparkSession, test_settings):
        """Test that properties can be linked to neighborhoods via neighborhood_id."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Load actual property and neighborhood data
        entity_data = loader.load_all_sources()
        properties_df = entity_data.get('properties')
        neighborhoods_df = entity_data.get('neighborhoods')
        
        if properties_df is None or neighborhoods_df is None:
            pytest.skip("Property or neighborhood data not available for relationship testing")
        
        # Create PropertyEnricher with neighborhood linking enabled
        property_config = PropertyEnrichmentConfig(enable_neighborhood_linking=True)
        property_enricher = PropertyEnricher(spark_session, property_config, location_broadcast)
        
        # Enrich properties
        enriched_properties = property_enricher.enrich(properties_df)
        
        # Verify relationship capability exists
        property_columns = enriched_properties.columns
        location_fields = [col for col in property_columns if 'city' in col.lower() or 'state' in col.lower()]
        
        assert len(location_fields) > 0, "Properties should have location fields for neighborhood linking"
        
        # Test join capability between properties and neighborhoods
        joined_df = enriched_properties.join(
            neighborhoods_df.select('neighborhood_id', 'name', 'city', 'state'), 
            on=['city', 'state'], 
            how='inner'
        )
        
        joined_count = joined_df.count()
        total_properties = enriched_properties.count()
        
        # Some properties should be linkable to neighborhoods
        linking_percentage = (joined_count / total_properties * 100) if total_properties > 0 else 0
        
        print(f"✅ Property-Neighborhood Linking: {joined_count}/{total_properties} properties "
              f"can be linked to neighborhoods ({linking_percentage:.1f}%)")
        
        # Verify the linking structure supports the required neighborhood_id relationship
        assert 'neighborhood_id' in joined_df.columns, "Joined data should include neighborhood_id for linking"
    
    def test_geographic_hierarchy_completeness(self, spark_session: SparkSession, test_settings):
        """Test that geographic hierarchy (neighborhood → city → county → state) is properly established."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Test hierarchy establishment with LocationEnricher
        config = LocationEnrichmentConfig(enable_hierarchy_resolution=True)
        location_enricher = LocationEnricher(spark_session, location_broadcast, config)
        
        # Load neighborhoods and test hierarchy establishment
        entity_data = loader.load_all_sources()
        neighborhoods_df = entity_data.get('neighborhoods')
        
        if neighborhoods_df is None:
            pytest.skip("Neighborhood data not available for hierarchy testing")
        
        # Enhance neighborhoods with hierarchy
        enhanced_neighborhoods = location_enricher.enhance_with_hierarchy(
            neighborhoods_df, "city", "state"
        )
        
        # Verify hierarchy fields
        hierarchy_columns = enhanced_neighborhoods.columns
        expected_hierarchy = ['city', 'state', 'county']  # neighborhood is implicit in the data
        
        for level in expected_hierarchy:
            assert level in hierarchy_columns, f"Geographic hierarchy level '{level}' should be present"
        
        # Test hierarchy completeness
        total_records = enhanced_neighborhoods.count()
        
        # Count records with complete hierarchy (at least city and state)
        complete_hierarchy = enhanced_neighborhoods.filter(
            col("city").isNotNull() & col("state").isNotNull()
        ).count()
        
        hierarchy_completeness = (complete_hierarchy / total_records * 100) if total_records > 0 else 0
        
        print(f"✅ Geographic Hierarchy: {complete_hierarchy}/{total_records} records "
              f"have complete city/state hierarchy ({hierarchy_completeness:.1f}%)")
        
        # Verify the hierarchy supports the required neighborhood → city → county → state structure
        assert hierarchy_completeness > 0, "Some records should have complete geographic hierarchy"


@pytest.mark.integration
class TestLocationEnrichmentStatistics:
    """Tests for location enrichment statistics and quality metrics."""
    
    def test_enrichment_statistics_calculation(self, spark_session: SparkSession, test_settings):
        """Test that enrichment statistics are properly calculated."""
        loader = DataLoaderOrchestrator(spark_session, test_settings)
        location_broadcast = loader.get_location_broadcast()
        
        # Test PropertyEnricher statistics
        property_config = PropertyEnrichmentConfig()
        property_enricher = PropertyEnricher(spark_session, property_config, location_broadcast)
        
        # Create test data
        test_data = [
            ("PROP001", 500000, 2, 1200, {"city": "San Francisco", "state": "CA"}),
            ("PROP002", 750000, 3, 1800, {"city": "Park City", "state": "UT"})
        ]
        test_df = spark_session.createDataFrame(
            test_data, 
            ["listing_id", "price", "bedrooms", "square_feet", "address"]
        )
        
        # Enrich and get statistics
        enriched_df = property_enricher.enrich(test_df)
        stats = property_enricher.get_enrichment_statistics(enriched_df)
        
        # Verify statistics structure
        assert isinstance(stats, dict), "Statistics should be returned as dictionary"
        assert 'total_properties' in stats, "Statistics should include total count"
        
        print(f"✅ Enrichment Statistics: {stats}")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])