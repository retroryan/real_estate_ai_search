"""Integration test for real Voyage embedding generation with Gold layer extension.

This test validates that embeddings are correctly generated using the real Voyage API
and stored in Gold tables following medallion architecture principles.
"""

import os
from pathlib import Path
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator
from squack_pipeline_v2.bronze.property import PropertyBronzeIngester
from squack_pipeline_v2.silver.property import PropertySilverTransformer
from squack_pipeline_v2.gold.property import PropertyGoldEnricher
from squack_pipeline_v2.embeddings.generator import EmbeddingGenerator
from squack_pipeline_v2.embeddings.providers import VoyageProvider
from squack_pipeline_v2.embeddings.metadata import EmbeddingMetadata


def test_real_voyage_embeddings():
    """Test embedding generation with real Voyage API."""
    print("\n=== Testing Real Voyage Embedding Generation ===")
    
    # Check for API key
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("Warning: VOYAGE_API_KEY not found, skipping real API test")
        print("Set VOYAGE_API_KEY environment variable to run this test")
        return
    
    print(f"Using Voyage API key: {api_key[:8]}...")
    
    # Setup using orchestrator to avoid connection issues
    settings = PipelineSettings()
    orchestrator = PipelineOrchestrator(settings)
    conn_manager = orchestrator.connection_manager
    
    property_file = Path("real_estate_data/properties_sf.json")
    if not property_file.exists():
        print(f"Warning: {property_file} not found, skipping test")
        return
    
    # Create complete Bronze → Silver → Gold pipeline
    bronze_ingester = PropertyBronzeIngester(settings, conn_manager)
    silver_transformer = PropertySilverTransformer(settings, conn_manager)
    gold_enricher = PropertyGoldEnricher(settings, conn_manager)
    
    # Setup real Voyage embedding provider
    voyage_provider = VoyageProvider(
        api_key=api_key,
        model_name="voyage-3",
        dimension=1024
    )
    embedding_generator = EmbeddingGenerator(conn_manager, voyage_provider)
    
    # Clean up any existing test tables
    test_tables = ["test_real_bronze_properties", "test_real_silver_properties", "test_real_gold_properties"]
    for table in test_tables:
        if conn_manager.table_exists(table):
            conn_manager.drop_table(table)
    
    print("Running Bronze → Silver → Gold pipeline with real data...")
    
    # Run Bronze → Silver → Gold
    bronze_ingester.ingest(
        table_name="test_real_bronze_properties",
        file_path=property_file,
        sample_size=2  # Small sample to avoid API rate limits
    )
    
    silver_transformer.transform(
        input_table="test_real_bronze_properties",
        output_table="test_real_silver_properties"
    )
    
    gold_enricher.enrich(
        input_table="test_real_silver_properties",
        output_table="test_real_gold_properties"
    )
    
    # Verify Gold table has embedding infrastructure
    schema = conn_manager.get_table_schema("test_real_gold_properties")
    column_names = [col[0] for col in schema]
    
    assert "embedding_vector" in column_names, "Gold table should have embedding_vector column"
    assert "embedding_generated_at" in column_names, "Gold table should have embedding_generated_at column"
    assert "embedding_text" in column_names, "Gold table should have embedding_text column"
    
    # Verify no embeddings initially (NULL values)
    conn = conn_manager.get_connection()
    count_no_embeddings = conn.sql("""
        SELECT COUNT(*) 
        FROM test_real_gold_properties 
        WHERE embedding_vector IS NULL
    """).fetchone()[0]
    
    assert count_no_embeddings == 2, "Initially no records should have embeddings"
    
    print("Generating embeddings using real Voyage API...")
    
    # Generate embeddings using real Voyage API
    result = embedding_generator.generate_for_gold_table(
        entity_type="property",
        gold_table="test_real_gold_properties",
        id_column="listing_id"
    )
    
    # Validate embedding metadata
    assert isinstance(result, EmbeddingMetadata), "Should return EmbeddingMetadata"
    assert result.entity_type == "property"
    assert result.gold_table == "test_real_gold_properties"
    assert result.embeddings_generated == 2, "Should generate 2 embeddings"
    assert result.embedding_dimension == 1024, "Should use 1024 dimensions"
    assert result.embedding_model == "voyage-3", "Should use voyage-3 model"
    
    print(f"Generated {result.embeddings_generated} embeddings with dimension {result.embedding_dimension}")
    
    # Verify embeddings were stored in Gold table
    count_with_embeddings = conn.sql("""
        SELECT COUNT(*) 
        FROM test_real_gold_properties 
        WHERE embedding_vector IS NOT NULL
    """).fetchone()[0]
    
    assert count_with_embeddings == 2, "All records should now have embeddings"
    
    # Verify embedding dimensions and values
    embedding_sample = conn.sql("""
        SELECT embedding_vector, embedding_generated_at, embedding_text
        FROM test_real_gold_properties 
        WHERE embedding_vector IS NOT NULL
        LIMIT 1
    """).fetchone()
    
    assert len(embedding_sample[0]) == 1024, "Embedding should have 1024 dimensions"
    assert embedding_sample[1] is not None, "Should have embedding_generated_at timestamp"
    assert embedding_sample[2] is not None, "Should have embedding_text"
    assert len(embedding_sample[2]) > 0, "embedding_text should not be empty"
    
    # Verify embedding values are realistic (not all zeros, reasonable range)
    embedding_values = embedding_sample[0]
    non_zero_count = sum(1 for v in embedding_values if abs(v) > 0.001)
    assert non_zero_count > 500, f"Should have many non-zero values, got {non_zero_count}"
    
    # Check value ranges (Voyage embeddings typically in [-1, 1] range)
    min_val = min(embedding_values)
    max_val = max(embedding_values)
    assert -2.0 <= min_val <= 2.0, f"Min value {min_val} seems unrealistic"
    assert -2.0 <= max_val <= 2.0, f"Max value {max_val} seems unrealistic"
    
    print(f"Embedding validation passed:")
    print(f"  - Dimension: {len(embedding_values)}")
    print(f"  - Non-zero values: {non_zero_count}")
    print(f"  - Value range: [{min_val:.4f}, {max_val:.4f}]")
    print(f"  - Generated at: {embedding_sample[1]}")
    print(f"  - Text length: {len(embedding_sample[2])} chars")
    
    # Test incremental processing (run again, should skip existing)
    print("Testing incremental processing...")
    result2 = embedding_generator.generate_for_gold_table(
        entity_type="property",
        gold_table="test_real_gold_properties", 
        id_column="listing_id"
    )
    
    assert result2.embeddings_generated == 0, "Should skip records that already have embeddings"
    assert result2.records_skipped == 2, "Should skip all 2 existing records"
    
    print("Incremental processing test passed")
    
    # Test verification functionality
    print("Testing embedding verification...")
    verification_stats = embedding_generator.verify_embeddings("test_real_gold_properties")
    
    assert verification_stats["total_records"] == 2
    assert verification_stats["records_with_embeddings"] == 2
    assert verification_stats["records_without_embeddings"] == 0
    assert verification_stats["embedding_coverage"] == 1.0
    
    print(f"Verification stats: {verification_stats}")
    
    # Clean up
    for table in test_tables:
        if conn_manager.table_exists(table):
            conn_manager.drop_table(table)
    
    orchestrator.cleanup()
    print("✓ Real Voyage embedding test passed")


def test_real_voyage_all_entities():
    """Test embedding generation for all entity types with real Voyage API."""
    print("\n=== Testing All Entity Types with Real Voyage API ===")
    
    # Check for API key
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("Warning: VOYAGE_API_KEY not found, skipping real API test")
        return
    
    # Setup using orchestrator
    settings = PipelineSettings()
    orchestrator = PipelineOrchestrator(settings)
    conn_manager = orchestrator.connection_manager
    
    # Setup real Voyage embedding provider
    voyage_provider = VoyageProvider(
        api_key=api_key,
        model_name="voyage-3", 
        dimension=1024
    )
    embedding_generator = EmbeddingGenerator(conn_manager, voyage_provider)
    
    # Check if we have existing Gold tables with data
    gold_tables = ["gold_properties", "gold_neighborhoods", "gold_wikipedia"]
    available_tables = []
    
    for table in gold_tables:
        if conn_manager.table_exists(table):
            count = conn_manager.count_records(table)
            if count > 0:
                available_tables.append((table, count))
                print(f"Found {table} with {count} records")
    
    if not available_tables:
        print("No Gold tables with data found, skipping test")
        print("Run the main pipeline first to create Gold tables")
        orchestrator.cleanup()
        return
    
    print(f"Testing embedding generation on {len(available_tables)} tables...")
    
    # Generate embeddings for all available tables
    results = embedding_generator.generate_all_embeddings()
    
    print(f"Embedding generation results:")
    for entity_type, metadata in results.items():
        print(f"  {entity_type}:")
        print(f"    - Records processed: {metadata.records_processed}")
        print(f"    - Embeddings generated: {metadata.embeddings_generated}")
        print(f"    - Records skipped: {metadata.records_skipped}")
        print(f"    - Dimension: {metadata.embedding_dimension}")
        print(f"    - Model: {metadata.embedding_model}")
        
        # Validate results
        assert metadata.embedding_dimension == 1024
        assert metadata.embedding_model == "voyage-3"
        assert metadata.records_processed > 0
    
    # Verify embeddings were actually stored
    conn = conn_manager.get_connection()
    for table, original_count in available_tables:
        embedding_count = conn.sql(f"""
            SELECT COUNT(*) 
            FROM {table} 
            WHERE embedding_vector IS NOT NULL
        """).fetchone()[0]
        
        print(f"{table}: {embedding_count}/{original_count} records have embeddings")
        assert embedding_count > 0, f"Should have embeddings in {table}"
        
        # Sample an embedding to verify quality
        sample = conn.sql(f"""
            SELECT embedding_vector
            FROM {table}
            WHERE embedding_vector IS NOT NULL
            LIMIT 1
        """).fetchone()
        
        if sample:
            embedding = sample[0]
            assert len(embedding) == 1024, f"Wrong dimension in {table}"
            non_zero = sum(1 for v in embedding if abs(v) > 0.001)
            assert non_zero > 500, f"Too many zeros in {table} embeddings"
    
    orchestrator.cleanup()
    print("✓ All entity types embedding test passed")


def test_real_voyage_medallion_compliance():
    """Test that real Voyage embeddings follow medallion architecture."""
    print("\n=== Testing Medallion Architecture Compliance with Real Voyage ===")
    
    # Check for API key
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("Warning: VOYAGE_API_KEY not found, skipping test")
        return
    
    settings = PipelineSettings()
    orchestrator = PipelineOrchestrator(settings)
    conn_manager = orchestrator.connection_manager
    
    # Verify NO separate embedding tables exist
    separate_embedding_tables = [
        "embeddings_properties", 
        "embeddings_neighborhoods", 
        "embeddings_wikipedia"
    ]
    
    for table in separate_embedding_tables:
        assert not conn_manager.table_exists(table), f"Separate embedding table {table} should not exist"
    
    print("✓ No separate embedding tables found (medallion compliance)")
    
    # Verify Gold tables contain ALL business data including embeddings
    gold_tables = ["gold_properties", "gold_neighborhoods", "gold_wikipedia"]
    
    for table in gold_tables:
        if conn_manager.table_exists(table):
            schema = conn_manager.get_table_schema(table)
            column_names = [col[0].lower() for col in schema]
            
            # Should have business data
            business_columns = ["price", "bedrooms"] if "properties" in table else ["population"]
            if "wikipedia" in table:
                business_columns = ["title", "content_length"]
            
            for col in business_columns:
                if col in ["price", "bedrooms"] and "properties" not in table:
                    continue
                assert any(col in name for name in column_names), f"Missing business column {col} in {table}"
            
            # Should have embedding infrastructure 
            assert "embedding_vector" in column_names, f"Missing embedding_vector in {table}"
            assert "embedding_generated_at" in column_names, f"Missing embedding_generated_at in {table}"
            assert "embedding_text" in column_names, f"Missing embedding_text in {table}"
            
            print(f"✓ {table} has complete business + embedding schema")
    
    orchestrator.cleanup()
    print("✓ Medallion architecture compliance verified")


def main():
    """Run all real Voyage embedding integration tests."""
    print("\n" + "="*60)
    print("REAL VOYAGE EMBEDDING INTEGRATION TESTS")
    print("="*60)
    
    # Check for API key upfront
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("\n❌ VOYAGE_API_KEY environment variable not set")
        print("Please set your Voyage API key to run these tests:")
        print("export VOYAGE_API_KEY='your-voyage-api-key-here'")
        return
    
    try:
        test_real_voyage_embeddings()
        test_real_voyage_medallion_compliance()
        test_real_voyage_all_entities()
        
        print("\n" + "="*60)
        print("ALL REAL VOYAGE EMBEDDING TESTS PASSED ✓")
        print("="*60)
        print("\nSummary:")
        print("- Real Voyage API integration works correctly")
        print("- Medallion architecture principles followed")
        print("- Embeddings stored directly in Gold tables") 
        print("- 1024-dimensional vectors generated successfully")
        print("- Incremental processing prevents duplicate work")
        print("- All entity types supported")
        print("- No separate embedding tables (architectural compliance)")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()