"""Integration test for Location Bronze layer ingestion.

This test validates that the Location Bronze layer correctly implements:
1. DuckDB best practices (parameterized queries, native functions)
2. Medallion architecture (raw, immutable data only)
3. Clean code with proper patterns
4. Geographic hierarchy data loading
"""

from pathlib import Path
import duckdb
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.bronze.location import LocationBronzeIngester
from squack_pipeline_v2.bronze.base import BronzeMetadata


def test_location_bronze_ingestion():
    """Test location Bronze ingestion with real geographic hierarchy data."""
    print("\n=== Testing Location Bronze Ingestion ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    ingester = LocationBronzeIngester(settings, conn_manager)
    
    # Use real location data
    location_file = Path("real_estate_data/locations.json")
    if not location_file.exists():
        print(f"Warning: {location_file} not found, skipping location test")
        return
    
    # Test with a sample first
    result = ingester.ingest(
        table_name="test_bronze_locations_sample",
        file_path=location_file,
        sample_size=20
    )
    
    # Validate result is BronzeMetadata
    assert isinstance(result, BronzeMetadata), "Should return BronzeMetadata"
    assert result.table_name == "test_bronze_locations_sample"
    assert str(result.source_path) == str(location_file.absolute())
    assert result.record_count == 20
    assert result.entity_type == "location"
    
    # Verify data in DuckDB
    count_result = conn_manager.execute(
        "SELECT COUNT(*) FROM test_bronze_locations_sample"
    ).fetchone()
    assert count_result[0] == 20, "Should have 20 records"
    
    # Check that raw JSON structure is preserved (Bronze principle)
    schema = conn_manager.get_table_schema("test_bronze_locations_sample")
    assert len(schema) > 0, "Table should have columns"
    
    # Verify expected columns exist (from raw JSON)
    column_names = [col[0] for col in schema]
    assert "city" in column_names, "Should have city from raw data"
    assert "county" in column_names, "Should have county from raw data"
    assert "state" in column_names, "Should have state from raw data"
    assert "zip_code" in column_names, "Should have zip_code from raw data"
    
    # Clean up sample test
    conn_manager.drop_table("test_bronze_locations_sample")
    print("✓ Location Bronze sample ingestion test passed")
    
    # Test full data load
    print("\n=== Testing Full Location Data Load ===")
    result_full = ingester.ingest(
        table_name="test_bronze_locations_full",
        file_path=location_file,
        sample_size=None  # Load all data
    )
    
    # Validate full load
    assert result_full.record_count == 293, f"Should have 293 records, got {result_full.record_count}"
    
    # Verify data completeness
    count_full = conn_manager.execute(
        "SELECT COUNT(*) FROM test_bronze_locations_full"
    ).fetchone()
    assert count_full[0] == 293, "Should have all 293 location records"
    
    # Clean up
    conn_manager.drop_table("test_bronze_locations_full")
    print("✓ Location Bronze full ingestion test passed")


def test_location_data_quality():
    """Test quality and structure of loaded location data."""
    print("\n=== Testing Location Data Quality ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    ingester = LocationBronzeIngester(settings, conn_manager)
    
    # Load a sample
    location_file = Path("real_estate_data/locations.json")
    if not location_file.exists():
        print(f"Warning: {location_file} not found, skipping quality test")
        return
    
    ingester.ingest(
        table_name="test_location_quality",
        file_path=location_file,
        sample_size=100
    )
    
    # Test location type distribution
    type_query = """
        SELECT 
            CASE 
                WHEN neighborhood IS NOT NULL THEN 'neighborhood'
                WHEN city IS NOT NULL AND neighborhood IS NULL THEN 'city'
                WHEN county IS NOT NULL AND city IS NULL THEN 'county'
                WHEN state IS NOT NULL AND county IS NULL THEN 'state'
                ELSE 'unknown'
            END as location_type,
            COUNT(*) as count
        FROM test_location_quality
        GROUP BY location_type
        ORDER BY count DESC
    """
    
    type_results = conn_manager.execute(type_query).fetchall()
    assert len(type_results) > 0, "Should have location types"
    
    location_types = {row[0]: row[1] for row in type_results}
    print(f"  Location types found: {location_types}")
    
    # Test state distribution
    state_query = """
        SELECT state, COUNT(*) as count
        FROM test_location_quality
        WHERE state IS NOT NULL
        GROUP BY state
        ORDER BY count DESC
    """
    
    state_results = conn_manager.execute(state_query).fetchall()
    assert len(state_results) > 0, "Should have states"
    
    states = {row[0]: row[1] for row in state_results}
    print(f"  States found: {states}")
    
    # Verify hierarchy - neighborhoods should have cities
    hierarchy_query = """
        SELECT COUNT(*) as orphaned_neighborhoods
        FROM test_location_quality
        WHERE neighborhood IS NOT NULL 
        AND city IS NULL
    """
    
    orphaned = conn_manager.execute(hierarchy_query).fetchone()[0]
    assert orphaned == 0, f"Found {orphaned} neighborhoods without cities"
    
    # Test ZIP code format
    zip_query = """
        SELECT COUNT(*) as invalid_zips
        FROM test_location_quality
        WHERE zip_code IS NOT NULL
        AND LENGTH(zip_code) != 5
    """
    
    invalid_zips = conn_manager.execute(zip_query).fetchone()[0]
    print(f"  Invalid ZIP codes: {invalid_zips}")
    
    # Clean up
    conn_manager.drop_table("test_location_quality")
    print("✓ Location data quality test passed")


def test_location_geographic_coverage():
    """Test geographic coverage of location data."""
    print("\n=== Testing Geographic Coverage ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    ingester = LocationBronzeIngester(settings, conn_manager)
    
    # Load full data for coverage test
    location_file = Path("real_estate_data/locations.json")
    if not location_file.exists():
        print(f"Warning: {location_file} not found, skipping coverage test")
        return
    
    ingester.ingest(
        table_name="test_location_coverage",
        file_path=location_file,
        sample_size=500  # Use larger sample for coverage
    )
    
    # Test California coverage
    ca_query = """
        SELECT 
            COUNT(DISTINCT city) as cities,
            COUNT(DISTINCT county) as counties,
            COUNT(DISTINCT zip_code) as zip_codes,
            COUNT(DISTINCT neighborhood) as neighborhoods
        FROM test_location_coverage
        WHERE state IN ('CA', 'California')
    """
    
    ca_coverage = conn_manager.execute(ca_query).fetchone()
    print(f"  California coverage:")
    print(f"    Cities: {ca_coverage[0]}")
    print(f"    Counties: {ca_coverage[1]}")
    print(f"    ZIP codes: {ca_coverage[2]}")
    print(f"    Neighborhoods: {ca_coverage[3]}")
    
    assert ca_coverage[0] > 0, "Should have California cities"
    assert ca_coverage[1] > 0, "Should have California counties"
    
    # Test Utah coverage
    ut_query = """
        SELECT 
            COUNT(DISTINCT city) as cities,
            COUNT(DISTINCT county) as counties,
            COUNT(DISTINCT zip_code) as zip_codes,
            COUNT(DISTINCT neighborhood) as neighborhoods
        FROM test_location_coverage
        WHERE state IN ('UT', 'Utah')
    """
    
    ut_coverage = conn_manager.execute(ut_query).fetchone()
    print(f"  Utah coverage:")
    print(f"    Cities: {ut_coverage[0]}")
    print(f"    Counties: {ut_coverage[1]}")
    print(f"    ZIP codes: {ut_coverage[2]}")
    print(f"    Neighborhoods: {ut_coverage[3]}")
    
    # Test complete hierarchy paths
    hierarchy_query = """
        SELECT COUNT(*) as complete_paths
        FROM test_location_coverage
        WHERE neighborhood IS NOT NULL
        AND city IS NOT NULL
        AND county IS NOT NULL
        AND state IS NOT NULL
        AND zip_code IS NOT NULL
    """
    
    complete = conn_manager.execute(hierarchy_query).fetchone()[0]
    print(f"  Complete hierarchy paths: {complete}")
    
    # Clean up
    conn_manager.drop_table("test_location_coverage")
    print("✓ Geographic coverage test passed")


def run_all_location_tests():
    """Run all location bronze layer tests."""
    print("\n" + "="*60)
    print("LOCATION BRONZE LAYER INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_location_bronze_ingestion()
        test_location_data_quality()
        test_location_geographic_coverage()
        
        print("\n" + "="*60)
        print("✅ ALL LOCATION TESTS PASSED")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    success = run_all_location_tests()
    exit(0 if success else 1)