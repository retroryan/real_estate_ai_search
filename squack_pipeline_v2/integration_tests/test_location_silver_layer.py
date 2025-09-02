"""Integration tests for Location Silver Layer transformation.

Tests silver layer location data standardization following DuckDB best practices.
"""

import pytest

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.table_names import ENTITY_TYPES
from squack_pipeline_v2.bronze.location import LocationBronzeIngester
from squack_pipeline_v2.silver.location import LocationSilverTransformer


class TestLocationSilverLayer:
    """Test Location Silver Layer transformations."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = PipelineSettings()
        settings.duckdb.database_file = ":memory:"
        settings.data_sources.locations_file = "real_estate_data/locations.json"
        return settings
    
    @pytest.fixture
    def connection_manager(self, settings):
        """Create connection manager."""
        return DuckDBConnectionManager(settings.duckdb)
    
    def test_silver_transformation_state_standardization(self, settings, connection_manager):
        """Test that states are properly standardized."""
        # First load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_metadata = bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50  # Small sample for testing
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_metadata = silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Verify transformation
        conn = connection_manager.get_connection()
        
        # Check state standardization
        states = conn.sql(f"""
            SELECT DISTINCT state_standardized, state_original
            FROM {ENTITY_TYPES.location.silver_table}
            WHERE state_original IS NOT NULL
        """).df()
        
        # All CA should be California, all UT should be Utah
        for _, row in states.iterrows():
            if row['state_original'] == 'CA':
                assert row['state_standardized'] == 'California'
            elif row['state_original'] == 'UT':
                assert row['state_standardized'] == 'Utah'
            elif row['state_original'] in ['California', 'Utah']:
                assert row['state_standardized'] == row['state_original']
    
    def test_silver_transformation_county_cleaning(self, settings, connection_manager):
        """Test that county names have 'County' suffix removed."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Check county standardization
        conn = connection_manager.get_connection()
        counties = conn.sql(f"""
            SELECT county_standardized
            FROM {ENTITY_TYPES.location.silver_table}
            WHERE county_standardized IS NOT NULL
        """).df()
        
        # No county should end with "County"
        for county in counties['county_standardized']:
            assert not county.endswith(' County'), f"County '{county}' still has 'County' suffix"
    
    def test_silver_transformation_city_cleaning(self, settings, connection_manager):
        """Test that city names are properly cleaned."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Check city standardization
        conn = connection_manager.get_connection()
        cities = conn.sql(f"""
            SELECT city_standardized
            FROM {ENTITY_TYPES.location.silver_table}
            WHERE city_standardized IS NOT NULL
        """).df()
        
        # Cities should be trimmed
        for city in cities['city_standardized']:
            assert city == city.strip(), f"City '{city}' has extra whitespace"
    
    def test_silver_transformation_zip_validation(self, settings, connection_manager):
        """Test ZIP code validation flags."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Check ZIP validation
        conn = connection_manager.get_connection()
        zips = conn.sql(f"""
            SELECT zip_code, zip_code_status
            FROM {ENTITY_TYPES.location.silver_table}
            WHERE zip_code IS NOT NULL
        """).df()
        
        for _, row in zips.iterrows():
            zip_code = row['zip_code']
            status = row['zip_code_status']
            
            if zip_code == '90001':
                assert status == 'placeholder', "90001 should be flagged as placeholder"
            elif len(zip_code) == 5 and zip_code.isdigit():
                assert status == 'valid', f"Valid ZIP {zip_code} not marked as valid"
            else:
                assert status in ['invalid', 'missing'], f"Invalid ZIP {zip_code} not properly flagged"
    
    def test_silver_transformation_hierarchical_ids(self, settings, connection_manager):
        """Test hierarchical ID generation for linking."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Check hierarchical IDs
        conn = connection_manager.get_connection()
        ids = conn.sql(f"""
            SELECT 
                neighborhood_id,
                city_id, 
                county_id,
                state_id,
                neighborhood_standardized,
                city_standardized,
                county_standardized,
                state_standardized
            FROM {ENTITY_TYPES.location.silver_table}
            LIMIT 10
        """).df()
        
        for _, row in ids.iterrows():
            # State ID should be standardized
            if row['state_standardized'] == 'California':
                assert row['state_id'] == 'state_california', "California state_id incorrect"
            elif row['state_standardized'] == 'Utah':
                assert row['state_id'] == 'state_utah', "Utah state_id incorrect"
            
            # City ID should include city and state
            if row['city_standardized']:
                assert row['city_id'] is not None, "City ID missing"
                assert '_' in row['city_id'], "City ID should contain underscore separator"
            
            # Neighborhood ID should include neighborhood and city
            if row['neighborhood_standardized'] and row['city_standardized']:
                assert row['neighborhood_id'] is not None, "Neighborhood ID missing"
                assert '_' in row['neighborhood_id'], "Neighborhood ID should contain underscore separator"
    
    def test_silver_transformation_location_type(self, settings, connection_manager):
        """Test location type determination."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # Check location types
        conn = connection_manager.get_connection()
        types = conn.sql(f"""
            SELECT 
                location_type,
                neighborhood_standardized,
                city_standardized,
                county_standardized,
                state_standardized
            FROM {ENTITY_TYPES.location.silver_table}
        """).df()
        
        for _, row in types.iterrows():
            location_type = row['location_type']
            
            # Verify type matches hierarchy
            if row['neighborhood_standardized']:
                assert location_type == 'neighborhood', "Neighborhood location type incorrect"
            elif row['city_standardized'] and not row['neighborhood_standardized']:
                assert location_type == 'city', "City location type incorrect"
            elif row['county_standardized'] and not row['city_standardized']:
                assert location_type == 'county', "County location type incorrect"
            elif row['state_standardized'] and not row['county_standardized']:
                assert location_type == 'state', "State location type incorrect"
    
    def test_silver_transformation_record_count(self, settings, connection_manager):
        """Test that all records are transformed."""
        # Load full bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_metadata = bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table
        )
        
        # Apply silver transformation
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_metadata = silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        # All records should be transformed (no filtering in silver)
        assert silver_metadata.output_count == bronze_metadata.record_count
        assert silver_metadata.input_count == bronze_metadata.record_count
        
        # Verify table exists and has data
        assert connection_manager.table_exists(ENTITY_TYPES.location.silver_table)
        count = connection_manager.count_records(ENTITY_TYPES.location.silver_table)
        assert count == 293, f"Expected 293 silver records, got {count}"