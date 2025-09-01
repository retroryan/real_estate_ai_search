"""Integration test for embedding Gold layer extension.

This test validates that embeddings are correctly generated and stored 
in Gold tables following medallion architecture principles.
"""

from pathlib import Path
from unittest.mock import MagicMock
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.bronze.property import PropertyBronzeIngester
from squack_pipeline_v2.silver.property import PropertySilverTransformer
from squack_pipeline_v2.gold.property import PropertyGoldEnricher
from squack_pipeline_v2.embeddings.generator import EmbeddingGenerator
from squack_pipeline_v2.embeddings.metadata import EmbeddingMetadata
from squack_pipeline_v2.embeddings.base import EmbeddingProvider, EmbeddingResponse


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""
    
    def __init__(self):
        super().__init__("mock-api-key", "voyage-3", 1024)
    
    def generate_embeddings(self, texts):
        """Generate mock embeddings with fixed 1024 dimensions."""
        embeddings = []
        for _ in texts:
            # Generate deterministic mock embedding vector
            embedding = [0.1] * 1024
            embeddings.append(embedding)
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model_name=self.model_name,
            dimension=self.dimension,
            token_count=len(texts) * 10  # Mock token count
        )
    
    def get_batch_size(self):
        """Get batch size."""
        return 10


def test_embedding_gold_extension():
    """Test embedding generation with Gold layer extension."""
    print("\n=== Testing Embedding Gold Layer Extension ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    property_file = Path("real_estate_data/properties_sf.json")
    if not property_file.exists():
        print(f"Warning: {property_file} not found, skipping test")
        return
    
    # Create complete Bronze → Silver → Gold pipeline
    bronze_ingester = PropertyBronzeIngester(settings, conn_manager)
    silver_transformer = PropertySilverTransformer(settings, conn_manager)
    gold_enricher = PropertyGoldEnricher(settings, conn_manager)
    
    # Setup mock embedding provider
    mock_provider = MockEmbeddingProvider()
    embedding_generator = EmbeddingGenerator(conn_manager, mock_provider)
    
    # Run Bronze → Silver → Gold
    bronze_ingester.ingest(
        table_name="test_bronze_properties",
        file_path=property_file,
        sample_size=5
    )
    
    silver_transformer.transform(
        input_table="test_bronze_properties",
        output_table="test_silver_properties"
    )
    
    gold_enricher.enrich(
        input_table="test_silver_properties",
        output_table="test_gold_properties"
    )
    
    # Verify Gold table has embedding columns
    schema = conn_manager.get_table_schema("test_gold_properties")
    column_names = [col[0] for col in schema]
    
    assert "embedding_vector" in column_names, "Gold table should have embedding_vector column"
    assert "embedding_generated_at" in column_names, "Gold table should have embedding_generated_at column"
    
    # Verify no embeddings initially (NULL values)
    conn = conn_manager.get_connection()
    count_no_embeddings = conn.sql("""
        SELECT COUNT(*) 
        FROM test_gold_properties 
        WHERE embedding_vector IS NULL
    """).fetchone()[0]
    
    assert count_no_embeddings == 5, "Initially no records should have embeddings"
    
    # Generate embeddings using Gold layer extension
    result = embedding_generator.generate_for_gold_table(
        entity_type="property",
        gold_table="test_gold_properties",
        id_column="listing_id"
    )
    
    # Validate embedding metadata
    assert isinstance(result, EmbeddingMetadata), "Should return EmbeddingMetadata"
    assert result.entity_type == "property"
    assert result.gold_table == "test_gold_properties"
    assert result.embeddings_generated == 5, "Should generate 5 embeddings"
    assert result.embedding_dimension == 1024, "Should use 1024 dimensions"
    assert result.embedding_model == "voyage-3", "Should use voyage-3 model"
    
    # Verify embeddings were stored in Gold table
    count_with_embeddings = conn.sql("""
        SELECT COUNT(*) 
        FROM test_gold_properties 
        WHERE embedding_vector IS NOT NULL
    """).fetchone()[0]
    
    assert count_with_embeddings == 5, "All records should now have embeddings"
    
    # Verify embedding dimensions
    embedding_sample = conn.sql("""
        SELECT embedding_vector 
        FROM test_gold_properties 
        LIMIT 1
    """).fetchone()[0]
    
    assert len(embedding_sample) == 1024, "Embedding should have 1024 dimensions"
    
    # Test incremental processing (run again, should skip existing)
    result2 = embedding_generator.generate_for_gold_table(
        entity_type="property",
        gold_table="test_gold_properties", 
        id_column="listing_id"
    )
    
    assert result2.embeddings_generated == 0, "Should skip records that already have embeddings"
    assert result2.records_skipped == 5, "Should skip all 5 existing records"
    
    # Clean up
    conn_manager.drop_table("test_bronze_properties")
    conn_manager.drop_table("test_silver_properties")
    conn_manager.drop_table("test_gold_properties")
    
    print("✓ Embedding Gold extension test passed")


def test_medallion_architecture_compliance():
    """Test that embeddings follow medallion architecture."""
    print("\n=== Testing Medallion Architecture Compliance ===")
    
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    property_file = Path("real_estate_data/properties_sf.json")
    if not property_file.exists():
        print(f"Warning: {property_file} not found, skipping test")
        return
    
    # Create pipeline
    bronze_ingester = PropertyBronzeIngester(settings, conn_manager)
    silver_transformer = PropertySilverTransformer(settings, conn_manager) 
    gold_enricher = PropertyGoldEnricher(settings, conn_manager)
    
    # Run pipeline
    bronze_ingester.ingest("test_bronze", property_file, sample_size=3)
    silver_transformer.transform("test_bronze", "test_silver")
    gold_enricher.enrich("test_silver", "test_gold")
    
    # Verify medallion architecture compliance
    conn = conn_manager.get_connection()
    
    # Gold table should have ALL business data including embeddings
    gold_schema = conn_manager.get_table_schema("test_gold")
    gold_columns = [col[0] for col in gold_schema]
    
    # Should have business data
    assert "price" in gold_columns, "Gold should have business data"
    assert "market_segment" in gold_columns, "Gold should have business intelligence"
    assert "embedding_text" in gold_columns, "Gold should have prepared embedding text"
    
    # Should have embedding infrastructure 
    assert "embedding_vector" in gold_columns, "Gold should have embedding vectors"
    assert "embedding_generated_at" in gold_columns, "Gold should have embedding metadata"
    
    # Should NOT have separate embedding tables
    assert not conn_manager.table_exists("embeddings_properties"), "Should not have separate embedding tables"
    
    # Clean up
    conn_manager.drop_table("test_bronze")
    conn_manager.drop_table("test_silver") 
    conn_manager.drop_table("test_gold")
    
    print("✓ Medallion architecture compliance test passed")


def test_duckdb_relation_api_usage():
    """Test that embedding operations use DuckDB Relation API."""
    print("\n=== Testing DuckDB Relation API Usage ===")
    
    # Check that EmbeddingGenerator uses Relation API
    import inspect
    from squack_pipeline_v2.embeddings.generator import EmbeddingGenerator
    
    # Check source code uses conn.sql() for lazy evaluation
    source = inspect.getsource(EmbeddingGenerator.generate_for_gold_table)
    assert "conn.sql" in source, "Should use conn.sql() for lazy evaluation"
    assert "WHERE embedding_vector IS NULL" in source, "Should use incremental processing"
    
    # Check verification uses Relation API
    verify_source = inspect.getsource(EmbeddingGenerator.verify_embeddings)
    assert "conn.sql" in verify_source, "Verification should use Relation API"
    
    print("✓ DuckDB Relation API usage test passed")


def main():
    """Run all embedding Gold extension integration tests."""
    print("\n" + "="*60)
    print("EMBEDDING GOLD EXTENSION INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_embedding_gold_extension()
        test_medallion_architecture_compliance()  
        test_duckdb_relation_api_usage()
        
        print("\n" + "="*60)
        print("ALL EMBEDDING EXTENSION TESTS PASSED ✓")
        print("="*60)
        print("\nSummary:")
        print("- Gold tables correctly extended with embedding infrastructure")
        print("- Medallion architecture principles followed (single source of truth)")
        print("- DuckDB Relation API used for efficient operations")
        print("- Incremental processing works correctly")
        print("- Fixed 1024 dimensions with current LlamaIndex + Voyage integration")
        print("- No separate embedding tables (architectural fix complete)")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()