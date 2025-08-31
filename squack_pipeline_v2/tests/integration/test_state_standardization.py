"""Integration test for state field standardization."""

import pytest
import duckdb
from pathlib import Path
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings, DuckDBConfig
from squack_pipeline_v2.bronze.wikipedia import WikipediaBronzeIngester
from squack_pipeline_v2.silver.wikipedia import WikipediaSilverTransformer
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher


class TestStateStandardization:
    """Test that state field standardization works correctly through the medallion layers."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test_state.duckdb"
        return str(db_path)
    
    @pytest.fixture
    def test_settings(self, temp_db):
        """Create test settings."""
        config_data = {
            "duckdb": {
                "database_file": temp_db,
                "memory_limit": "1GB",
                "threads": 1
            },
            "data_sources": {
                "wikipedia_db_path": "data/wikipedia/wikipedia.db"
            }
        }
        return PipelineSettings(**config_data)
    
    @pytest.fixture
    def connection_manager(self, test_settings):
        """Create connection manager."""
        return DuckDBConnectionManager(test_settings.duckdb)
    
    def test_bronze_preserves_raw_state(self, test_settings, connection_manager):
        """Test that Bronze layer preserves raw best_state field."""
        # Check if Wikipedia DB exists
        wiki_db = Path(test_settings.data_sources.wikipedia_db_path)
        if not wiki_db.exists():
            pytest.skip(f"Wikipedia database not found at {wiki_db}")
        
        # Run Bronze ingestion
        ingester = WikipediaBronzeIngester(test_settings, connection_manager)
        ingester.ingest(sample_size=5)
        
        # Verify Bronze has best_state field
        result = connection_manager.execute("""
            SELECT best_state, COUNT(*) as cnt
            FROM bronze_wikipedia
            WHERE best_state IS NOT NULL
            GROUP BY best_state
            LIMIT 1
        """).fetchone()
        
        if result:
            state_value = result[0]
            # Bronze should have full state names
            assert len(state_value) > 2, f"Bronze should preserve full state names, got: {state_value}"
            print(f"✓ Bronze preserves raw state: {state_value}")
    
    def test_silver_transforms_to_abbreviations(self, test_settings, connection_manager):
        """Test that Silver layer transforms states to abbreviations."""
        # Check if Wikipedia DB exists
        wiki_db = Path(test_settings.data_sources.wikipedia_db_path)
        if not wiki_db.exists():
            pytest.skip(f"Wikipedia database not found at {wiki_db}")
        
        # Run Bronze ingestion
        ingester = WikipediaBronzeIngester(test_settings, connection_manager)
        ingester.ingest(sample_size=10)
        
        # Run Silver transformation
        transformer = WikipediaSilverTransformer(test_settings, connection_manager)
        transformer.transform("bronze_wikipedia", "silver_wikipedia")
        
        # Check Silver has state field (not best_state)
        schema = connection_manager.execute("""
            DESCRIBE silver_wikipedia
        """).fetchall()
        
        column_names = [row[0] for row in schema]
        assert "state" in column_names, "Silver should have 'state' field"
        assert "best_state" not in column_names, "Silver should NOT have 'best_state' field"
        
        # Verify state values are abbreviations
        result = connection_manager.execute("""
            SELECT state, COUNT(*) as cnt
            FROM silver_wikipedia
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            LIMIT 5
        """).fetchall()
        
        if result:
            for state_value, count in result:
                assert len(state_value) == 2, f"Silver should have 2-letter state abbreviations, got: {state_value}"
                assert state_value.isupper(), f"State abbreviations should be uppercase, got: {state_value}"
                print(f"✓ Silver has abbreviated state: {state_value} ({count} records)")
    
    def test_gold_uses_standardized_state(self, test_settings, connection_manager):
        """Test that Gold layer uses standardized state field."""
        # Check if Wikipedia DB exists
        wiki_db = Path(test_settings.data_sources.wikipedia_db_path)
        if not wiki_db.exists():
            pytest.skip(f"Wikipedia database not found at {wiki_db}")
        
        # Run full pipeline through Gold
        ingester = WikipediaBronzeIngester(test_settings, connection_manager)
        ingester.ingest(sample_size=10)
        
        transformer = WikipediaSilverTransformer(test_settings, connection_manager)
        transformer.transform("bronze_wikipedia", "silver_wikipedia")
        
        enricher = WikipediaGoldEnricher(test_settings, connection_manager)
        enricher.enrich("silver_wikipedia", "gold_wikipedia")
        
        # Check Gold has state field
        schema = connection_manager.execute("""
            DESCRIBE gold_wikipedia
        """).fetchall()
        
        column_names = [row[0] for row in schema]
        assert "state" in column_names, "Gold should have 'state' field"
        assert "best_state" not in column_names, "Gold should NOT have 'best_state' field"
        
        # Verify state values match Silver
        result = connection_manager.execute("""
            SELECT 
                g.state as gold_state,
                s.state as silver_state
            FROM gold_wikipedia g
            JOIN silver_wikipedia s ON g.page_id = s.page_id
            WHERE g.state IS NOT NULL AND g.state != ''
            LIMIT 5
        """).fetchall()
        
        if result:
            for gold_state, silver_state in result:
                assert gold_state == silver_state, f"Gold and Silver states should match: {gold_state} != {silver_state}"
                print(f"✓ Gold matches Silver state: {gold_state}")
    
    def test_state_transformation_mapping(self, test_settings, connection_manager):
        """Test specific state transformations."""
        from squack_pipeline_v2.utils import StateStandardizer
        
        # Test the utility class directly
        assert StateStandardizer.standardize_state("California") == "CA"
        assert StateStandardizer.standardize_state("New York") == "NY"
        assert StateStandardizer.standardize_state("Texas") == "TX"
        assert StateStandardizer.standardize_state("CA") == "CA"  # Already abbreviated
        assert StateStandardizer.standardize_state("") == ""
        
        # Test SQL generation
        sql = StateStandardizer.get_sql_case_statement("test_field", "output")
        assert "WHEN 'California' THEN 'CA'" in sql
        assert "WHEN 'New York' THEN 'NY'" in sql
        assert "END as output" in sql
        
        print("✓ StateStandardizer utility works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])