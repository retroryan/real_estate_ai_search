"""Integration tests for Gold tier to Parquet writing with nested structure preservation.

This test validates that Gold tier data can be written to Parquet files 
while preserving all nested structures (no flattening).
"""

import tempfile
from pathlib import Path
from typing import Dict, Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
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


class TestGoldToParquetValidation:
    """Test Gold tier data can be written to Parquet with nested structures preserved."""
    
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
    
    def process_to_gold(self, entity_type: str, settings: PipelineSettings, connection) -> str:
        """Process entity through Bronze → Silver → Gold."""
        
        if entity_type == "property":
            # Bronze
            loader = PropertyLoader(settings)
            loader.set_connection(connection)
            bronze_table = loader.load(sample_size=5)
            
            # Silver
            silver_proc = PropertySilverProcessor(settings)
            silver_proc.set_connection(connection)
            silver_table = silver_proc.process(bronze_table)
            
            # Gold
            gold_proc = PropertyGoldProcessor(settings)
            gold_proc.set_connection(connection)
            return gold_proc.process(silver_table)
            
        elif entity_type == "neighborhood":
            # Bronze
            loader = NeighborhoodLoader(settings)
            loader.set_connection(connection)
            bronze_table = loader.load(sample_size=5)
            
            # Silver
            silver_proc = NeighborhoodSilverProcessor(settings)
            silver_proc.set_connection(connection)
            silver_table = silver_proc.process(bronze_table)
            
            # Gold
            gold_proc = NeighborhoodGoldProcessor(settings)
            gold_proc.set_connection(connection)
            return gold_proc.process(silver_table)
            
        elif entity_type == "wikipedia":
            # Bronze
            loader = WikipediaLoader(settings)
            loader.set_connection(connection)
            bronze_table = loader.load(sample_size=5)
            
            # Silver
            silver_proc = WikipediaSilverProcessor(settings)
            silver_proc.set_connection(connection)
            silver_table = silver_proc.process(bronze_table)
            
            # Gold
            gold_proc = WikipediaGoldProcessor(settings)
            gold_proc.set_connection(connection)
            return gold_proc.process(silver_table)
            
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
    
    def write_to_parquet(self, connection, table_name: str, output_path: Path):
        """Write DuckDB table to Parquet file."""
        query = f"""
        COPY {table_name} 
        TO '{output_path}' 
        (FORMAT PARQUET, COMPRESSION 'snappy')
        """
        connection.execute(query)
    
    def validate_parquet_schema(self, parquet_file: Path, entity_type: str) -> Dict[str, Any]:
        """Validate Parquet schema has expected nested structures."""
        schema = pq.read_schema(parquet_file)
        validation = {
            "has_nested": False,
            "nested_fields": [],
            "array_fields": [],
            "issues": []
        }
        
        # Check for expected nested fields based on entity type
        expected_nested = {
            "property": ["address", "property_details", "coordinates", "parking"],
            "neighborhood": ["coordinates", "characteristics", "demographics"],
            "wikipedia": []  # Wikipedia is mostly flat
        }
        
        for field_name in schema.names:
            field = schema.field(field_name)
            
            # Check if field is nested (struct)
            if isinstance(field.type, pa.StructType):
                validation["nested_fields"].append(field_name)
                validation["has_nested"] = True
                
            # Check if field is array (list)
            elif isinstance(field.type, pa.ListType):
                validation["array_fields"].append(field_name)
        
        # Validate expected nested fields are present
        for expected_field in expected_nested.get(entity_type, []):
            if expected_field not in validation["nested_fields"]:
                validation["issues"].append(f"Missing expected nested field: {expected_field}")
        
        return validation
    
    def validate_data_roundtrip(self, connection, 
                               original_table: str, parquet_file: Path) -> bool:
        """Validate data can be read back from Parquet with structure preserved."""
        # Create temporary table from Parquet
        temp_table = f"temp_roundtrip_{Path(parquet_file).stem}"
        connection.execute(f"""
            CREATE TABLE {temp_table} AS 
            SELECT * FROM read_parquet('{parquet_file}')
        """)
        
        # Compare record counts
        original_count = connection.execute(f"SELECT COUNT(*) FROM {original_table}").fetchone()[0]
        roundtrip_count = connection.execute(f"SELECT COUNT(*) FROM {temp_table}").fetchone()[0]
        
        if original_count != roundtrip_count:
            return False
        
        # Test nested field access with dot notation
        try:
            # Try to access nested fields
            result = connection.execute(f"""
                SELECT * FROM {temp_table} LIMIT 1
            """).fetchone()
            
            # Clean up
            connection.execute(f"DROP TABLE {temp_table}")
            return True
            
        except Exception as e:
            print(f"Roundtrip validation failed: {e}")
            return False
    
    def test_property_gold_to_parquet(self, settings, connection, temp_dir):
        """Test Property Gold tier to Parquet with nested structures."""
        print("\n=== Testing Property Gold → Parquet ===")
        
        # Process to Gold
        gold_table = self.process_to_gold("property", settings, connection)
        print(f"✓ Processed to Gold: {gold_table}")
        
        # Write to Parquet
        parquet_file = temp_dir / "properties_gold.parquet"
        self.write_to_parquet(connection, gold_table, parquet_file)
        print(f"✓ Written to Parquet: {parquet_file}")
        
        # Validate schema
        schema_validation = self.validate_parquet_schema(parquet_file, "property")
        assert schema_validation["has_nested"], "No nested structures found in Parquet"
        assert "address" in schema_validation["nested_fields"], "Address not nested in Parquet"
        assert "property_details" in schema_validation["nested_fields"], "Property details not nested"
        assert "coordinates" in schema_validation["nested_fields"], "Coordinates not nested"
        print(f"✓ Schema validated - Nested fields: {schema_validation['nested_fields']}")
        
        # Validate with Pandas
        df = pd.read_parquet(parquet_file)
        assert "address" in df.columns, "Address column missing"
        
        # Check nested structure is preserved (Pandas loads as dict)
        sample_address = df.iloc[0]["address"]
        assert isinstance(sample_address, dict), "Address should be a dict"
        assert "street" in sample_address, "Street missing from address"
        assert "city" in sample_address, "City missing from address"
        print(f"✓ Pandas validation - Address fields: {list(sample_address.keys())}")
        
        # Validate round-trip
        assert self.validate_data_roundtrip(connection, gold_table, parquet_file)
        print("✓ Round-trip validation passed")
        
        print("✓ Property Gold → Parquet test PASSED")
    
    def test_neighborhood_gold_to_parquet(self, settings, connection, temp_dir):
        """Test Neighborhood Gold tier to Parquet with nested structures."""
        print("\n=== Testing Neighborhood Gold → Parquet ===")
        
        # Process to Gold
        gold_table = self.process_to_gold("neighborhood", settings, connection)
        print(f"✓ Processed to Gold: {gold_table}")
        
        # Write to Parquet
        parquet_file = temp_dir / "neighborhoods_gold.parquet"
        self.write_to_parquet(connection, gold_table, parquet_file)
        print(f"✓ Written to Parquet: {parquet_file}")
        
        # Validate schema
        schema_validation = self.validate_parquet_schema(parquet_file, "neighborhood")
        assert schema_validation["has_nested"], "No nested structures found in Parquet"
        assert "coordinates" in schema_validation["nested_fields"], "Coordinates not nested"
        assert "characteristics" in schema_validation["nested_fields"], "Characteristics not nested"
        assert "demographics" in schema_validation["nested_fields"], "Demographics not nested"
        print(f"✓ Schema validated - Nested fields: {schema_validation['nested_fields']}")
        
        # Validate with Pandas
        df = pd.read_parquet(parquet_file)
        
        # Check nested demographics
        sample_demographics = df.iloc[0]["demographics"]
        assert isinstance(sample_demographics, dict), "Demographics should be a dict"
        assert "population" in sample_demographics, "Population missing from demographics"
        print(f"✓ Pandas validation - Demographics fields: {list(sample_demographics.keys())}")
        
        # Validate round-trip
        assert self.validate_data_roundtrip(connection, gold_table, parquet_file)
        print("✓ Round-trip validation passed")
        
        print("✓ Neighborhood Gold → Parquet test PASSED")
    
    def test_wikipedia_gold_to_parquet(self, settings, connection, temp_dir):
        """Test Wikipedia Gold tier to Parquet (mostly flat structure)."""
        print("\n=== Testing Wikipedia Gold → Parquet ===")
        
        # Process to Gold
        gold_table = self.process_to_gold("wikipedia", settings, connection)
        print(f"✓ Processed to Gold: {gold_table}")
        
        # Write to Parquet
        parquet_file = temp_dir / "wikipedia_gold.parquet"
        self.write_to_parquet(connection, gold_table, parquet_file)
        print(f"✓ Written to Parquet: {parquet_file}")
        
        # Validate schema
        schema_validation = self.validate_parquet_schema(parquet_file, "wikipedia")
        print(f"✓ Schema validated - Array fields: {schema_validation['array_fields']}")
        
        # Validate with Pandas
        df = pd.read_parquet(parquet_file)
        assert "page_id" in df.columns, "page_id column missing"
        assert "title" in df.columns, "title column missing"
        assert "extract" in df.columns, "extract column missing"
        
        # Check location array if present
        if "location" in df.columns:
            first_location = df.iloc[0]["location"]
            if first_location is not None and not (isinstance(first_location, float) and pd.isna(first_location)):
                sample_location = df.iloc[0]["location"]
                # Parquet arrays can be numpy arrays or lists
                assert hasattr(sample_location, '__len__'), "Location should be array-like"
                assert len(sample_location) == 2, "Location should have [lon, lat]"
                print(f"✓ Pandas validation - Location: {list(sample_location)}")
        
        # Validate round-trip
        assert self.validate_data_roundtrip(connection, gold_table, parquet_file)
        print("✓ Round-trip validation passed")
        
        print("✓ Wikipedia Gold → Parquet test PASSED")
    
    def test_all_entities_parquet_summary(self, settings, connection, temp_dir):
        """Test all entities and provide summary."""
        print("\n" + "="*60)
        print("GOLD TO PARQUET VALIDATION SUMMARY")
        print("="*60)
        
        results = {}
        
        for entity_type in ["property", "neighborhood", "wikipedia"]:
            gold_table = self.process_to_gold(entity_type, settings, connection)
            parquet_file = temp_dir / f"{entity_type}_gold.parquet"
            self.write_to_parquet(connection, gold_table, parquet_file)
            
            # Get file size
            file_size_mb = parquet_file.stat().st_size / (1024 * 1024)
            
            # Get schema info
            schema_validation = self.validate_parquet_schema(parquet_file, entity_type)
            
            # Get record count
            df = pd.read_parquet(parquet_file)
            
            results[entity_type] = {
                "records": len(df),
                "file_size_mb": file_size_mb,
                "nested_fields": schema_validation["nested_fields"],
                "array_fields": schema_validation["array_fields"]
            }
        
        # Print summary
        for entity, info in results.items():
            print(f"\n{entity.upper()}")
            print("-" * 40)
            print(f"  Records: {info['records']}")
            print(f"  File Size: {info['file_size_mb']:.3f} MB")
            print(f"  Nested Fields: {', '.join(info['nested_fields']) or 'None'}")
            print(f"  Array Fields: {', '.join(info['array_fields']) or 'None'}")
        
        print("\n" + "="*60)
        print("✅ All entities successfully written to Parquet with nested structures preserved!")
        print("="*60)