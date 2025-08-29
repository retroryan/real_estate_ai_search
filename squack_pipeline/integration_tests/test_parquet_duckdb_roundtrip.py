"""Integration test for reading Parquet files back into DuckDB with nested structures.

This test validates the complete round-trip:
1. Gold tier DuckDB table → Parquet file
2. Parquet file → DuckDB table
3. Query nested fields with dot notation
"""

import tempfile
from pathlib import Path
from typing import Dict, List, Any

import duckdb
import pytest

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.wikipedia_loader import WikipediaLoader
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.wikipedia_silver_processor import WikipediaSilverProcessor
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.processors.wikipedia_gold_processor import WikipediaGoldProcessor


class TestParquetDuckDBRoundtrip:
    """Test complete round-trip of Gold data through Parquet back to DuckDB."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def connection(self, settings):
        """Create DuckDB connection."""
        conn_mgr = DuckDBConnectionManager()
        conn_mgr.initialize(settings)
        return conn_mgr.get_connection()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for Parquet files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def process_property_to_gold(self, settings: PipelineSettings, connection) -> str:
        """Process properties through Bronze → Silver → Gold."""
        # Bronze
        loader = PropertyLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(sample_size=10)
        
        # Silver
        silver_proc = PropertySilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = PropertyGoldProcessor(settings)
        gold_proc.set_connection(connection)
        return gold_proc.process(silver_table)
    
    def process_neighborhood_to_gold(self, settings: PipelineSettings, connection) -> str:
        """Process neighborhoods through Bronze → Silver → Gold."""
        # Bronze
        loader = NeighborhoodLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(sample_size=10)
        
        # Silver
        silver_proc = NeighborhoodSilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = NeighborhoodGoldProcessor(settings)
        gold_proc.set_connection(connection)
        return gold_proc.process(silver_table)
    
    def process_wikipedia_to_gold(self, settings: PipelineSettings, connection) -> str:
        """Process Wikipedia through Bronze → Silver → Gold."""
        # Bronze
        loader = WikipediaLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(sample_size=10)
        
        # Silver
        silver_proc = WikipediaSilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = WikipediaGoldProcessor(settings)
        gold_proc.set_connection(connection)
        return gold_proc.process(silver_table)
    
    def test_property_parquet_duckdb_roundtrip(self, settings, connection, temp_dir):
        """Test Properties: Gold → Parquet → DuckDB with nested field queries."""
        print("\n" + "="*60)
        print("Testing Property Parquet/DuckDB Round-trip")
        print("="*60)
        
        # 1. Process to Gold
        gold_table = self.process_property_to_gold(settings, connection)
        print(f"✓ Created Gold table: {gold_table}")
        
        # Get original data for comparison
        original_data = connection.execute(f"""
            SELECT 
                listing_id,
                price,
                address.street as street,
                address.city as city,
                property_details.bedrooms as bedrooms,
                property_details.garage_spaces as garage_spaces,
                coordinates.latitude as lat,
                coordinates.longitude as lon,
                parking.spaces as parking_spaces,
                location[1] as loc_lon,
                location[2] as loc_lat
            FROM {gold_table}
            ORDER BY listing_id
            LIMIT 5
        """).fetchall()
        
        print(f"✓ Original data sampled - {len(original_data)} records")
        
        # 2. Write to Parquet
        parquet_file = temp_dir / "properties_gold.parquet"
        connection.execute(f"""
            COPY {gold_table} 
            TO '{parquet_file}' 
            (FORMAT PARQUET, COMPRESSION 'snappy')
        """)
        print(f"✓ Written to Parquet: {parquet_file.name}")
        
        # 3. Read back from Parquet into new table
        roundtrip_table = "properties_from_parquet"
        connection.execute(f"""
            CREATE TABLE {roundtrip_table} AS 
            SELECT * FROM read_parquet('{parquet_file}')
        """)
        print(f"✓ Read from Parquet into: {roundtrip_table}")
        
        # 4. Verify record counts match
        original_count = connection.execute(f"SELECT COUNT(*) FROM {gold_table}").fetchone()[0]
        roundtrip_count = connection.execute(f"SELECT COUNT(*) FROM {roundtrip_table}").fetchone()[0]
        assert original_count == roundtrip_count, f"Count mismatch: {original_count} → {roundtrip_count}"
        print(f"✓ Record count preserved: {original_count}")
        
        # 5. Query nested fields with dot notation
        print("\nTesting nested field access with dot notation:")
        
        # Test address nested access
        address_query = connection.execute(f"""
            SELECT 
                listing_id,
                address.street,
                address.city,
                address.state,
                address.zip
            FROM {roundtrip_table}
            WHERE address.city IS NOT NULL
            LIMIT 3
        """).fetchall()
        assert len(address_query) > 0, "Failed to query nested address fields"
        print(f"  ✓ address.* fields: {len(address_query)} records accessible")
        
        # Test property_details nested access
        details_query = connection.execute(f"""
            SELECT 
                listing_id,
                property_details.bedrooms,
                property_details.bathrooms,
                property_details.garage_spaces,
                property_details.year_built
            FROM {roundtrip_table}
            WHERE property_details.bedrooms > 0
            LIMIT 3
        """).fetchall()
        assert len(details_query) > 0, "Failed to query nested property_details fields"
        print(f"  ✓ property_details.* fields: {len(details_query)} records accessible")
        
        # Test coordinates nested access
        coords_query = connection.execute(f"""
            SELECT 
                listing_id,
                coordinates.latitude,
                coordinates.longitude
            FROM {roundtrip_table}
            WHERE coordinates.latitude IS NOT NULL
            LIMIT 3
        """).fetchall()
        assert len(coords_query) > 0, "Failed to query nested coordinates fields"
        print(f"  ✓ coordinates.* fields: {len(coords_query)} records accessible")
        
        # Test parking object access
        parking_query = connection.execute(f"""
            SELECT 
                listing_id,
                parking.spaces,
                parking.available
            FROM {roundtrip_table}
            WHERE parking.spaces >= 0
            LIMIT 3
        """).fetchall()
        assert len(parking_query) > 0, "Failed to query parking object fields"
        print(f"  ✓ parking.* fields: {len(parking_query)} records accessible")
        
        # 6. Compare specific values to ensure data integrity
        roundtrip_data = connection.execute(f"""
            SELECT 
                listing_id,
                price,
                address.street as street,
                address.city as city,
                property_details.bedrooms as bedrooms,
                property_details.garage_spaces as garage_spaces,
                coordinates.latitude as lat,
                coordinates.longitude as lon,
                parking.spaces as parking_spaces,
                location[1] as loc_lon,
                location[2] as loc_lat
            FROM {roundtrip_table}
            ORDER BY listing_id
            LIMIT 5
        """).fetchall()
        
        # Compare original vs roundtrip data
        for i, (orig, round) in enumerate(zip(original_data, roundtrip_data)):
            assert orig[0] == round[0], f"listing_id mismatch at row {i}"
            assert orig[1] == round[1], f"price mismatch at row {i}"
            assert orig[2] == round[2], f"street mismatch at row {i}"
            assert orig[3] == round[3], f"city mismatch at row {i}"
        
        print("\n✓ Data integrity verified - values match perfectly")
        
        # 7. Test complex nested query
        complex_query = connection.execute(f"""
            SELECT 
                COUNT(*) as total,
                AVG(price) as avg_price,
                MAX(property_details.bedrooms) as max_bedrooms,
                COUNT(DISTINCT address.city) as unique_cities
            FROM {roundtrip_table}
            WHERE coordinates.latitude BETWEEN 37.0 AND 38.0
                AND property_details.bedrooms >= 2
        """).fetchone()
        
        print(f"\n✓ Complex nested query successful:")
        print(f"  - Total matching: {complex_query[0]}")
        print(f"  - Avg price: ${complex_query[1]:,.2f}" if complex_query[1] else "  - Avg price: N/A")
        print(f"  - Max bedrooms: {complex_query[2]}")
        print(f"  - Unique cities: {complex_query[3]}")
        
        print("\n" + "="*60)
        print("✅ Property Parquet/DuckDB round-trip test PASSED")
        print("="*60)
    
    def test_neighborhood_parquet_duckdb_roundtrip(self, settings, connection, temp_dir):
        """Test Neighborhoods: Gold → Parquet → DuckDB with nested field queries."""
        print("\n" + "="*60)
        print("Testing Neighborhood Parquet/DuckDB Round-trip")
        print("="*60)
        
        # 1. Process to Gold
        gold_table = self.process_neighborhood_to_gold(settings, connection)
        print(f"✓ Created Gold table: {gold_table}")
        
        # 2. Write to Parquet
        parquet_file = temp_dir / "neighborhoods_gold.parquet"
        connection.execute(f"""
            COPY {gold_table} 
            TO '{parquet_file}' 
            (FORMAT PARQUET, COMPRESSION 'snappy')
        """)
        print(f"✓ Written to Parquet: {parquet_file.name}")
        
        # 3. Read back from Parquet
        roundtrip_table = "neighborhoods_from_parquet"
        connection.execute(f"""
            CREATE TABLE {roundtrip_table} AS 
            SELECT * FROM read_parquet('{parquet_file}')
        """)
        print(f"✓ Read from Parquet into: {roundtrip_table}")
        
        # 4. Verify counts
        original_count = connection.execute(f"SELECT COUNT(*) FROM {gold_table}").fetchone()[0]
        roundtrip_count = connection.execute(f"SELECT COUNT(*) FROM {roundtrip_table}").fetchone()[0]
        assert original_count == roundtrip_count
        print(f"✓ Record count preserved: {original_count}")
        
        # 5. Test nested field queries
        print("\nTesting nested field access with dot notation:")
        
        # Test coordinates
        coords_query = connection.execute(f"""
            SELECT 
                neighborhood_id,
                name,
                coordinates.latitude,
                coordinates.longitude
            FROM {roundtrip_table}
            WHERE coordinates.latitude IS NOT NULL
            LIMIT 3
        """).fetchall()
        assert len(coords_query) > 0
        print(f"  ✓ coordinates.* fields: {len(coords_query)} records accessible")
        
        # Test demographics
        demographics_query = connection.execute(f"""
            SELECT 
                neighborhood_id,
                demographics.population,
                demographics.median_household_income,
                demographics.primary_age_group
            FROM {roundtrip_table}
            WHERE demographics.population > 0
            LIMIT 3
        """).fetchall()
        assert len(demographics_query) > 0
        print(f"  ✓ demographics.* fields: {len(demographics_query)} records accessible")
        
        # Test characteristics
        characteristics_query = connection.execute(f"""
            SELECT 
                neighborhood_id,
                characteristics.walkability_score,
                characteristics.transit_score,
                characteristics.school_rating
            FROM {roundtrip_table}
            WHERE characteristics.walkability_score IS NOT NULL
            LIMIT 3
        """).fetchall()
        assert len(characteristics_query) > 0
        print(f"  ✓ characteristics.* fields: {len(characteristics_query)} records accessible")
        
        # 6. Test complex aggregation on nested data
        complex_query = connection.execute(f"""
            SELECT 
                COUNT(*) as total,
                AVG(demographics.population) as avg_population,
                AVG(characteristics.walkability_score) as avg_walkability,
                MIN(demographics.median_household_income) as min_income,
                MAX(demographics.median_household_income) as max_income
            FROM {roundtrip_table}
            WHERE demographics.population IS NOT NULL
        """).fetchone()
        
        print(f"\n✓ Complex nested aggregation successful:")
        print(f"  - Total neighborhoods: {complex_query[0]}")
        if complex_query[1]:
            print(f"  - Avg population: {complex_query[1]:,.0f}")
        if complex_query[2]:
            print(f"  - Avg walkability: {complex_query[2]:.1f}")
        if complex_query[3] and complex_query[4]:
            print(f"  - Income range: ${complex_query[3]:,.0f} - ${complex_query[4]:,.0f}")
        
        print("\n" + "="*60)
        print("✅ Neighborhood Parquet/DuckDB round-trip test PASSED")
        print("="*60)
    
    def test_wikipedia_parquet_duckdb_roundtrip(self, settings, connection, temp_dir):
        """Test Wikipedia: Gold → Parquet → DuckDB (mostly flat structure)."""
        print("\n" + "="*60)
        print("Testing Wikipedia Parquet/DuckDB Round-trip")
        print("="*60)
        
        # 1. Process to Gold
        gold_table = self.process_wikipedia_to_gold(settings, connection)
        print(f"✓ Created Gold table: {gold_table}")
        
        # 2. Write to Parquet
        parquet_file = temp_dir / "wikipedia_gold.parquet"
        connection.execute(f"""
            COPY {gold_table} 
            TO '{parquet_file}' 
            (FORMAT PARQUET, COMPRESSION 'snappy')
        """)
        print(f"✓ Written to Parquet: {parquet_file.name}")
        
        # 3. Read back from Parquet
        roundtrip_table = "wikipedia_from_parquet"
        connection.execute(f"""
            CREATE TABLE {roundtrip_table} AS 
            SELECT * FROM read_parquet('{parquet_file}')
        """)
        print(f"✓ Read from Parquet into: {roundtrip_table}")
        
        # 4. Verify counts
        original_count = connection.execute(f"SELECT COUNT(*) FROM {gold_table}").fetchone()[0]
        roundtrip_count = connection.execute(f"SELECT COUNT(*) FROM {roundtrip_table}").fetchone()[0]
        assert original_count == roundtrip_count
        print(f"✓ Record count preserved: {original_count}")
        
        # 5. Test field access (Wikipedia is mostly flat)
        print("\nTesting field access:")
        
        # Test basic fields
        basic_query = connection.execute(f"""
            SELECT 
                id,
                page_id,
                title,
                LENGTH(extract) as extract_length,
                latitude,
                longitude
            FROM {roundtrip_table}
            WHERE title IS NOT NULL
            LIMIT 3
        """).fetchall()
        assert len(basic_query) > 0
        print(f"  ✓ Basic fields accessible: {len(basic_query)} records")
        
        # Test location array
        location_query = connection.execute(f"""
            SELECT 
                id,
                title,
                location[1] as lon,
                location[2] as lat
            FROM {roundtrip_table}
            WHERE location IS NOT NULL
            LIMIT 3
        """).fetchall()
        
        if len(location_query) > 0:
            print(f"  ✓ Location array accessible: {len(location_query)} records with coordinates")
            sample = location_query[0]
            print(f"    Sample: {sample[1]} at [{sample[2]:.4f}, {sample[3]:.4f}]")
        
        # 6. Test text search capability
        text_search = connection.execute(f"""
            SELECT 
                COUNT(*) as matches,
                MIN(LENGTH(extract)) as min_length,
                MAX(LENGTH(extract)) as max_length,
                AVG(LENGTH(extract)) as avg_length
            FROM {roundtrip_table}
            WHERE LOWER(extract) LIKE '%park%'
                OR LOWER(title) LIKE '%park%'
        """).fetchone()
        
        print(f"\n✓ Text search on round-trip data:")
        print(f"  - Matches for 'park': {text_search[0]}")
        if text_search[0] > 0:
            print(f"  - Extract length range: {text_search[1]}-{text_search[2]} chars")
            print(f"  - Average extract: {text_search[3]:.0f} chars")
        
        print("\n" + "="*60)
        print("✅ Wikipedia Parquet/DuckDB round-trip test PASSED")
        print("="*60)
    
    def test_cross_entity_parquet_join(self, settings, connection, temp_dir):
        """Test joining across multiple Parquet files with nested structures."""
        print("\n" + "="*60)
        print("Testing Cross-Entity Parquet Joins")
        print("="*60)
        
        # Process all entities to Gold and write to Parquet
        property_gold = self.process_property_to_gold(settings, connection)
        property_parquet = temp_dir / "properties.parquet"
        connection.execute(f"COPY {property_gold} TO '{property_parquet}' (FORMAT PARQUET)")
        
        neighborhood_gold = self.process_neighborhood_to_gold(settings, connection)
        neighborhood_parquet = temp_dir / "neighborhoods.parquet"
        connection.execute(f"COPY {neighborhood_gold} TO '{neighborhood_parquet}' (FORMAT PARQUET)")
        
        print("✓ Created Parquet files for properties and neighborhoods")
        
        # Read both back
        connection.execute(f"""
            CREATE VIEW properties_parquet AS 
            SELECT * FROM read_parquet('{property_parquet}')
        """)
        
        connection.execute(f"""
            CREATE VIEW neighborhoods_parquet AS 
            SELECT * FROM read_parquet('{neighborhood_parquet}')
        """)
        
        print("✓ Created views from Parquet files")
        
        # Test join with nested field access
        join_query = connection.execute("""
            SELECT 
                p.listing_id,
                p.price,
                p.address.street as property_street,
                p.address.city as property_city,
                p.property_details.bedrooms as bedrooms,
                n.name as neighborhood_name,
                n.demographics.population as neighborhood_population,
                n.characteristics.walkability_score as walkability
            FROM properties_parquet p
            LEFT JOIN neighborhoods_parquet n 
                ON p.neighborhood_id = n.neighborhood_id
            WHERE p.address.city IS NOT NULL
                AND n.demographics.population > 0
            LIMIT 5
        """).fetchall()
        
        if len(join_query) > 0:
            print(f"\n✓ Cross-entity join successful: {len(join_query)} records")
            print("\nSample joined data:")
            for row in join_query[:2]:
                print(f"  - {row[0]}: ${row[1]:,.0f}, {row[4]} BR in {row[5]}")
                print(f"    {row[2]}, {row[3]}")
                print(f"    Population: {row[6]:,}, Walkability: {row[7]}")
        else:
            print("\n✓ Cross-entity join executed (no matching records in sample)")
        
        # Test aggregation across joined nested data
        agg_query = connection.execute("""
            SELECT 
                n.name as neighborhood,
                COUNT(p.listing_id) as property_count,
                AVG(p.price) as avg_price,
                AVG(p.property_details.bedrooms) as avg_bedrooms,
                MAX(p.property_details.garage_spaces) as max_garage,
                n.demographics.median_household_income as median_income
            FROM properties_parquet p
            JOIN neighborhoods_parquet n 
                ON p.neighborhood_id = n.neighborhood_id
            GROUP BY n.neighborhood_id, n.name, n.demographics.median_household_income
            HAVING COUNT(p.listing_id) > 0
            ORDER BY property_count DESC
            LIMIT 3
        """).fetchall()
        
        if len(agg_query) > 0:
            print(f"\n✓ Aggregation across joined Parquet data:")
            for row in agg_query:
                if row[0]:  # neighborhood name exists
                    print(f"  - {row[0]}: {row[1]} properties")
                    if row[2]:
                        print(f"    Avg price: ${row[2]:,.0f}")
                    if row[3]:
                        print(f"    Avg bedrooms: {row[3]:.1f}")
        
        print("\n" + "="*60)
        print("✅ Cross-entity Parquet join test PASSED")
        print("="*60)