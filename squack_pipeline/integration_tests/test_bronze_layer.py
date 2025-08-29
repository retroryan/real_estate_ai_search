"""Integration tests for Bronze Layer with Nested Structures."""

from pathlib import Path
import pytest

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.location_loader import LocationLoader
from squack_pipeline.models.duckdb_models import TableIdentifier


class TestBronzeLayerNestedStructures:
    """Integration tests for Bronze layer with preserved nested structures."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def property_loader(self, settings):
        """Create property loader."""
        return PropertyLoader(settings)
    
    @pytest.fixture
    def neighborhood_loader(self, settings):
        """Create neighborhood loader."""
        return NeighborhoodLoader(settings)
    
    @pytest.fixture
    def location_loader(self, settings):
        """Create location loader."""
        return LocationLoader(settings)
    
    def test_property_bronze_layer_nested_structures(self, property_loader, settings):
        """Test property Bronze layer preserves nested structures as STRUCT types."""
        print("\n=== Testing Property Bronze Layer Nested Structures ===")
        
        # Initialize connections
        property_loader.connection_manager.initialize(settings)
        property_loader.set_connection(property_loader.connection_manager.get_connection())
        
        try:
            # Load properties into Bronze layer
            print("Loading properties into Bronze layer...")
            table_name = property_loader.load(sample_size=10)
            assert table_name == "bronze_properties"
            
            # Verify table exists and has data
            count = property_loader.count_records(table_name)
            assert count > 0, "No properties loaded into Bronze layer"
            print(f"✓ Loaded {count} properties into Bronze layer")
            
            # Verify nested structure schema
            table_info = property_loader.connection_manager.get_table_info(
                TableIdentifier(name=table_name)
            )
            
            schema_fields = {col["name"] for col in table_info["schema"]}
            
            # Expected nested fields (not flattened)
            expected_fields = {
                "listing_id", "neighborhood_id", "listing_price", "price_per_sqft",
                "listing_date", "days_on_market", "address", "property_details", 
                "coordinates", "description", "features", "images", 
                "virtual_tour_url", "price_history"
            }
            
            print(f"Schema fields found: {schema_fields}")
            print(f"Expected fields: {expected_fields}")
            
            # Check all expected fields are present
            missing_fields = expected_fields - schema_fields
            extra_fields = schema_fields - expected_fields
            
            if missing_fields:
                print(f"Missing fields: {missing_fields}")
            if extra_fields:
                print(f"Extra fields: {extra_fields}")
            
            # Allow extra fields but ensure required ones are present
            assert not missing_fields, f"Missing Bronze layer fields: {missing_fields}"
            print("✓ All expected nested structure fields present in Bronze schema")
            
            # Verify nested structures are preserved
            connection = property_loader.connection_manager.get_connection()
            
            # Test accessing nested fields with dot notation
            nested_query = f"""
            SELECT 
                listing_id,
                address.city as city,
                address.state as state,
                property_details.bedrooms as bedrooms,
                coordinates.latitude as lat,
                coordinates.longitude as lon
            FROM {table_name}
            LIMIT 1
            """
            
            result = connection.execute(nested_query)
            row = result.fetchone()
            assert row is not None, "Failed to query nested fields"
            print("✓ Nested structures accessible via dot notation")
            
            # Validate Bronze layer data
            validation_passed = property_loader.validate(table_name)
            assert validation_passed, "Property Bronze layer validation failed"
            print("✓ Property Bronze layer validation passed")
            
        except Exception as e:
            pytest.fail(f"Property Bronze layer test failed: {e}")
    
    def test_neighborhood_bronze_layer_nested_structures(self, neighborhood_loader, settings):
        """Test neighborhood Bronze layer preserves nested structures as STRUCT types."""
        print("\n=== Testing Neighborhood Bronze Layer Nested Structures ===")
        
        # Initialize connections
        neighborhood_loader.connection_manager.initialize(settings)
        neighborhood_loader.set_connection(neighborhood_loader.connection_manager.get_connection())
        
        try:
            # Load neighborhoods into Bronze layer
            print("Loading neighborhoods into Bronze layer...")
            table_name = neighborhood_loader.load(sample_size=5)
            assert table_name == "bronze_neighborhoods"
            
            # Verify table exists and has data
            count = neighborhood_loader.count_records(table_name)
            assert count > 0, "No neighborhoods loaded into Bronze layer"
            print(f"✓ Loaded {count} neighborhoods into Bronze layer")
            
            # Verify nested structure schema
            table_info = neighborhood_loader.connection_manager.get_table_info(
                TableIdentifier(name=table_name)
            )
            
            schema_fields = {col["name"] for col in table_info["schema"]}
            
            # Expected nested fields (not flattened)
            expected_fields = {
                "neighborhood_id", "name", "city", "county", "state", 
                "coordinates", "characteristics", "demographics",
                "description", "amenities", "lifestyle_tags", 
                "median_home_price", "price_trend", "wikipedia_correlations"
            }
            
            print(f"Schema fields found: {schema_fields}")
            
            # Check key nested fields are present
            key_nested_fields = {"coordinates", "characteristics", "demographics"}
            present_nested = schema_fields & key_nested_fields
            
            assert present_nested, f"No nested fields found. Expected at least: {key_nested_fields}"
            print(f"✓ Nested structure fields present: {present_nested}")
            
            # Test accessing nested fields with dot notation
            connection = neighborhood_loader.connection_manager.get_connection()
            
            nested_query = f"""
            SELECT 
                neighborhood_id,
                coordinates.latitude as lat,
                coordinates.longitude as lon,
                characteristics.walkability_score as walk_score,
                demographics.population as pop
            FROM {table_name}
            LIMIT 1
            """
            
            result = connection.execute(nested_query)
            row = result.fetchone()
            assert row is not None, "Failed to query nested fields"
            print("✓ Nested structures accessible via dot notation")
            
            # Validate Bronze layer data
            validation_passed = neighborhood_loader.validate(table_name)
            assert validation_passed, "Neighborhood Bronze layer validation failed"
            print("✓ Neighborhood Bronze layer validation passed")
            
        except Exception as e:
            pytest.fail(f"Neighborhood Bronze layer test failed: {e}")
    
    def test_location_bronze_layer_simple_structure(self, location_loader, settings):
        """Test location Bronze layer with simple structure (already flat)."""
        print("\n=== Testing Location Bronze Layer Simple Structure ===")
        
        # Initialize connections
        location_loader.connection_manager.initialize(settings)
        location_loader.set_connection(location_loader.connection_manager.get_connection())
        
        try:
            # Load locations into Bronze layer
            print("Loading locations into Bronze layer...")
            table_name = location_loader.load(sample_size=10)
            assert table_name == "bronze_locations"
            
            # Verify table exists and has data
            count = location_loader.count_records(table_name)
            assert count > 0, "No locations loaded into Bronze layer"
            print(f"✓ Loaded {count} locations into Bronze layer")
            
            # Verify simple schema structure
            table_info = location_loader.connection_manager.get_table_info(
                TableIdentifier(name=table_name)
            )
            
            schema_fields = {col["name"] for col in table_info["schema"]}
            
            # Expected fields from Location model (already flat)
            expected_fields = {"city", "county", "state", "zip_code", "neighborhood"}
            
            print(f"Schema fields found: {schema_fields}")
            print(f"Expected fields: {expected_fields}")
            
            # Check all expected fields are present
            missing_fields = expected_fields - schema_fields
            
            assert not missing_fields, f"Missing Bronze layer fields: {missing_fields}"
            print("✓ All expected fields present in Bronze schema")
            
            # Validate Bronze layer data
            validation_passed = location_loader.validate(table_name)
            assert validation_passed, "Location Bronze layer validation failed"
            print("✓ Location Bronze layer validation passed")
            
        except Exception as e:
            pytest.fail(f"Location Bronze layer test failed: {e}")
    
    def test_nested_structure_preservation_across_bronze_tables(self, property_loader, neighborhood_loader, settings):
        """Test that nested structures are preserved across Bronze layer tables."""
        print("\n=== Testing Nested Structure Preservation Across Bronze Tables ===")
        
        # Initialize connections
        for loader in [property_loader, neighborhood_loader]:
            loader.connection_manager.initialize(settings)
            loader.set_connection(loader.connection_manager.get_connection())
        
        try:
            # Load entity types
            print("Loading entity types into Bronze layer...")
            property_table = property_loader.load(sample_size=5)
            neighborhood_table = neighborhood_loader.load(sample_size=3)
            
            connection = property_loader.connection_manager.get_connection()
            
            # Test cross-table query with nested fields
            print("Testing cross-table nested field access...")
            
            # Query properties with nested address
            prop_query = f"""
            SELECT 
                listing_id,
                address.city as city,
                address.state as state,
                property_details.bedrooms as bedrooms
            FROM {property_table}
            WHERE address.city IS NOT NULL
            LIMIT 1
            """
            
            prop_result = connection.execute(prop_query)
            prop_row = prop_result.fetchone()
            assert prop_row is not None, "Failed to query property nested fields"
            print(f"✓ Property nested access: city={prop_row[1]}, state={prop_row[2]}, bedrooms={prop_row[3]}")
            
            # Query neighborhoods with nested demographics
            hood_query = f"""
            SELECT 
                neighborhood_id,
                name,
                demographics.population as population,
                characteristics.walkability_score as walk_score
            FROM {neighborhood_table}
            WHERE name IS NOT NULL
            LIMIT 1
            """
            
            hood_result = connection.execute(hood_query)
            hood_row = hood_result.fetchone()
            assert hood_row is not None, "Failed to query neighborhood nested fields"
            print(f"✓ Neighborhood nested access: name={hood_row[1]}, population={hood_row[2]}, walk_score={hood_row[3]}")
            
            print("✓ All Bronze layer tables preserve nested structures correctly")
            
        except Exception as e:
            pytest.fail(f"Nested structure preservation test failed: {e}")
    
    def test_bronze_layer_data_quality_with_nested_structures(self, property_loader, neighborhood_loader, location_loader, settings):
        """Test data quality metrics for Bronze layer tables with nested structures."""
        print("\n=== Testing Bronze Layer Data Quality with Nested Structures ===")
        
        # Initialize all connections
        for loader in [property_loader, neighborhood_loader, location_loader]:
            loader.connection_manager.initialize(settings)
            loader.set_connection(loader.connection_manager.get_connection())
        
        try:
            # Load all entity types
            property_table = property_loader.load(sample_size=20)
            neighborhood_table = neighborhood_loader.load(sample_size=10)
            location_table = location_loader.load(sample_size=15)
            
            # Get record counts
            property_count = property_loader.count_records(property_table)
            neighborhood_count = neighborhood_loader.count_records(neighborhood_table)
            location_count = location_loader.count_records(location_table)
            
            print(f"Properties loaded: {property_count}")
            print(f"Neighborhoods loaded: {neighborhood_count}")
            print(f"Locations loaded: {location_count}")
            
            # Verify minimum data quality thresholds
            assert property_count >= 5, f"Insufficient property data: {property_count}"
            assert neighborhood_count >= 3, f"Insufficient neighborhood data: {neighborhood_count}"
            assert location_count >= 5, f"Insufficient location data: {location_count}"
            
            # Test sample data extraction works for all tables
            property_samples = property_loader.get_sample_data(property_table, 3)
            neighborhood_samples = neighborhood_loader.get_sample_data(neighborhood_table, 2)
            location_samples = location_loader.get_sample_data(location_table, 3)
            
            assert property_samples and len(property_samples) > 0, "Failed to extract property samples"
            assert neighborhood_samples and len(neighborhood_samples) > 0, "Failed to extract neighborhood samples"
            assert location_samples and len(location_samples) > 0, "Failed to extract location samples"
            
            # Verify nested structures in samples
            if property_samples:
                first_prop = property_samples[0]
                assert 'address' in first_prop or 'city' in first_prop, "Property sample should have address data"
                print("✓ Property samples contain expected structure")
            
            if neighborhood_samples:
                first_hood = neighborhood_samples[0]
                assert 'coordinates' in first_hood or 'walkability_score' in first_hood, "Neighborhood sample should have nested data"
                print("✓ Neighborhood samples contain expected structure")
            
            print("✓ Sample data extraction working for all Bronze layer tables")
            
            # Verify all validations pass
            assert property_loader.validate(property_table), "Property Bronze layer validation failed"
            assert neighborhood_loader.validate(neighborhood_table), "Neighborhood Bronze layer validation failed"
            assert location_loader.validate(location_table), "Location Bronze layer validation failed"
            
            print("✓ All Bronze layer data quality validations passed")
            
            # Summary
            print(f"\nBRONZE LAYER SUMMARY:")
            print(f"  Properties: {property_count} records with nested structures (address, property_details, coordinates)")
            print(f"  Neighborhoods: {neighborhood_count} records with nested structures (demographics, characteristics)")
            print(f"  Locations: {location_count} records with simple structure")
            print(f"  Total Bronze records: {property_count + neighborhood_count + location_count}")
            print("✓ All Bronze layer tables ready for Silver tier processing with preserved nested structures")
            
        except Exception as e:
            pytest.fail(f"Bronze layer data quality test failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])