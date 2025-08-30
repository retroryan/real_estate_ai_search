"""Integration tests for SQUACK Pipeline V2."""

import pytest
from pathlib import Path
import tempfile
import json
import duckdb
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings, DuckDBConfig
from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.duckdb"
            yield str(db_path)
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def test_settings(self, temp_db, temp_output_dir):
        """Create test settings."""
        from squack_pipeline_v2.core.settings import DuckDBConfig, OutputConfig
        
        # Create with proper config structure
        config_data = {
            "duckdb": {
                "database_file": temp_db,
                "memory_limit": "2GB",
                "threads": 2
            },
            "output": {
                "parquet_dir": str(temp_output_dir),
                "parquet_enabled": True,
                "elasticsearch_enabled": False
            }
        }
        
        settings = PipelineSettings(**config_data)
        return settings
    
    def test_bronze_layer_ingestion(self, test_settings):
        """Test Bronze layer can ingest data."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Run Bronze layer with small sample
        metrics = orchestrator.run_bronze_layer(
            sample_size=5
        )
        
        # Verify data was ingested
        assert "property" in metrics
        assert metrics["property"].bronze_metrics is not None
        assert metrics["property"].bronze_metrics.output_records > 0
        
        # Check table exists
        assert orchestrator.connection_manager.table_exists("bronze_properties")
        
        # Verify record count
        count = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM bronze_properties"
        ).fetchone()[0]
        assert count == 5
        
        orchestrator.cleanup()
    
    def test_silver_layer_transformation(self, test_settings):
        """Test Silver layer transformation."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # First ingest Bronze data
        orchestrator.run_bronze_layer(
            sample_size=5
        )
        
        # Run Silver transformation
        metrics = orchestrator.run_silver_layer()
        
        # Verify transformation
        assert "property" in metrics
        assert metrics["property"].output_records > 0
        
        # Check standardization
        result = orchestrator.connection_manager.execute(
            "SELECT listing_id, state_code FROM silver_properties LIMIT 1"
        ).fetchone()
        
        assert result is not None
        listing_id, state_code = result
        assert listing_id is not None
        assert len(state_code) == 2  # State code should be 2 characters
        assert state_code.isupper()  # Should be uppercase
        
        orchestrator.cleanup()
    
    def test_gold_layer_enrichment(self, test_settings):
        """Test Gold layer enrichment."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Run Bronze and Silver first
        orchestrator.run_bronze_layer(
            sample_size=5
        )
        orchestrator.run_silver_layer()
        
        # Run Gold enrichment
        metrics = orchestrator.run_gold_layer()
        
        # Verify enrichment
        assert "property" in metrics
        
        # Check computed fields exist
        result = orchestrator.connection_manager.execute("""
            SELECT 
                listing_id,
                price_per_sqft,
                price_category,
                embedding_text
            FROM gold_properties
            LIMIT 1
        """).fetchone()
        
        assert result is not None
        _, price_per_sqft, price_category, embedding_text = result
        assert price_per_sqft is not None
        assert price_category in ["luxury", "standard", "affordable"]
        assert embedding_text is not None and len(embedding_text) > 0
        
        orchestrator.cleanup()
    
    def test_parquet_export(self, test_settings, temp_output_dir):
        """Test Parquet export functionality."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Run pipeline through Gold
        orchestrator.run_bronze_layer(
            sample_size=3
        )
        orchestrator.run_silver_layer()
        orchestrator.run_gold_layer()
        
        # Export to Parquet
        stats = orchestrator.run_writers(
            write_parquet=True,
            write_elasticsearch=False
        )
        
        # Verify Parquet files created
        assert "parquet" in stats
        assert stats["parquet"]["total_files"] > 0
        
        # Check files exist
        parquet_files = list(temp_output_dir.rglob("*.parquet"))
        assert len(parquet_files) > 0
        
        # Verify we can read back the Parquet file
        gold_parquet = temp_output_dir / "gold" / "properties.parquet"
        if gold_parquet.exists():
            conn = duckdb.connect()
            result = conn.execute(f"SELECT COUNT(*) FROM '{gold_parquet}'").fetchone()
            assert result[0] == 3
            conn.close()
        
        orchestrator.cleanup()
    
    def test_full_pipeline_execution(self, test_settings, temp_output_dir):
        """Test full pipeline end-to-end."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Run full pipeline
        metrics = orchestrator.run_full_pipeline(
            sample_size=5,
            generate_embeddings=False,  # Skip embeddings for test
            write_parquet=True,
            write_elasticsearch=False
        )
        
        # Verify pipeline completed
        assert metrics.status == "completed"
        assert metrics.is_successful
        assert len(metrics.error_messages) == 0
        
        # Check all tables exist
        table_stats = orchestrator.get_table_stats()
        assert "bronze_properties" in table_stats
        assert "silver_properties" in table_stats
        assert "gold_properties" in table_stats
        assert "bronze_neighborhoods" in table_stats
        assert "silver_neighborhoods" in table_stats
        assert "gold_neighborhoods" in table_stats
        
        # Verify Parquet files
        parquet_files = list(temp_output_dir.rglob("*.parquet"))
        assert len(parquet_files) > 0
        
        orchestrator.cleanup()
    
    def test_medallion_data_flow(self, test_settings):
        """Test data flows correctly through medallion layers."""
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Run pipeline
        orchestrator.run_bronze_layer(
            sample_size=10
        )
        orchestrator.run_silver_layer()
        orchestrator.run_gold_layer()
        
        # Get counts at each layer
        bronze_count = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM bronze_properties"
        ).fetchone()[0]
        
        silver_count = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM silver_properties"
        ).fetchone()[0]
        
        gold_count = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM gold_properties"
        ).fetchone()[0]
        
        # Verify data flows through (some records might be filtered)
        assert bronze_count == 10
        assert silver_count <= bronze_count  # Some might be filtered
        assert gold_count <= silver_count  # Some might be filtered
        
        # Verify data quality improves
        # Bronze: Check raw data
        bronze_nulls = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM bronze_properties WHERE listing_price IS NULL"
        ).fetchone()[0]
        
        # Silver: No nulls in required fields
        silver_nulls = orchestrator.connection_manager.execute(
            "SELECT COUNT(*) FROM silver_properties WHERE price IS NULL"
        ).fetchone()[0]
        
        assert silver_nulls == 0  # Silver should have cleaned nulls
        
        orchestrator.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])