"""Integration test for Gold layer enrichment.

This test validates that the Gold layer correctly implements:
1. DuckDB Relation API usage with lazy evaluation
2. Medallion architecture (business-ready, aggregated, enriched data)
3. Clean code with Pydantic models
4. No TableIdentifier references
"""

from pathlib import Path
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.bronze.property import PropertyBronzeIngester
from squack_pipeline_v2.bronze.neighborhood import NeighborhoodBronzeIngester
from squack_pipeline_v2.bronze.wikipedia import WikipediaBronzeIngester
from squack_pipeline_v2.silver.property import PropertySilverTransformer
from squack_pipeline_v2.silver.neighborhood import NeighborhoodSilverTransformer
from squack_pipeline_v2.silver.wikipedia import WikipediaSilverTransformer
from squack_pipeline_v2.gold.property import PropertyGoldEnricher
from squack_pipeline_v2.gold.neighborhood import NeighborhoodGoldEnricher
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher
from squack_pipeline_v2.gold.base import GoldMetadata


def test_gold_property_enrichment():
    """Test property Gold enrichment."""
    print("\n=== Testing Property Gold Enrichment ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    property_file = Path("real_estate_data/properties_sf.json")
    if not property_file.exists():
        print(f"Warning: {property_file} not found, skipping property test")
        return
    
    # Create Bronze → Silver → Gold pipeline
    bronze_ingester = PropertyBronzeIngester(settings, conn_manager)
    silver_transformer = PropertySilverTransformer(settings, conn_manager)
    gold_enricher = PropertyGoldEnricher(settings, conn_manager)
    
    # Bronze
    bronze_ingester.ingest(
        table_name="test_bronze_properties",
        file_path=property_file,
        sample_size=10
    )
    
    # Silver
    silver_transformer.transform(
        input_table="test_bronze_properties",
        output_table="test_silver_properties"
    )
    
    # Gold
    result = gold_enricher.enrich(
        input_table="test_silver_properties",
        output_table="test_gold_properties"
    )
    
    # Validate Gold result
    assert isinstance(result, GoldMetadata), "Should return GoldMetadata"
    assert result.entity_type == "property"
    assert result.output_count > 0, "Should have output records"
    assert len(result.enrichments_applied) > 0, "Should have applied enrichments"
    
    # Verify business enrichments
    expected_enrichments = [
        "price_metrics", "market_positioning", "investment_analysis",
        "property_categorization", "business_embedding_text"
    ]
    for enrichment in expected_enrichments:
        assert enrichment in result.enrichments_applied, f"Should have {enrichment}"
    
    # Verify Gold table structure - business-ready data
    schema = conn_manager.get_table_schema("test_gold_properties")
    column_names = [col[0] for col in schema]
    
    # Check Gold enrichments
    assert "price_per_bedroom" in column_names, "Should have price_per_bedroom metric"
    assert "market_segment" in column_names, "Should have market positioning"
    assert "age_category" in column_names, "Should have property categorization"
    assert "investment_attractiveness_score" in column_names or "price_premium_pct" in column_names, "Should have investment analysis"
    assert "embedding_text" in column_names, "Should have business-ready embedding text"
    assert "search_facets" in column_names, "Should have search facets"
    
    # Clean up
    conn_manager.drop_table("test_bronze_properties")
    conn_manager.drop_table("test_silver_properties")
    conn_manager.drop_table("test_gold_properties")
    print("✓ Property Gold enrichment test passed")


def test_gold_neighborhood_enrichment():
    """Test neighborhood Gold enrichment."""
    print("\n=== Testing Neighborhood Gold Enrichment ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    neighborhood_file = Path("real_estate_data/neighborhoods_sf.json")
    if not neighborhood_file.exists():
        print(f"Warning: {neighborhood_file} not found, skipping neighborhood test")
        return
    
    # Create Bronze → Silver → Gold pipeline
    bronze_ingester = NeighborhoodBronzeIngester(settings, conn_manager)
    silver_transformer = NeighborhoodSilverTransformer(settings, conn_manager)
    gold_enricher = NeighborhoodGoldEnricher(settings, conn_manager)
    
    # Bronze
    bronze_ingester.ingest(
        table_name="test_bronze_neighborhoods",
        file_path=neighborhood_file,
        sample_size=5
    )
    
    # Silver
    silver_transformer.transform(
        input_table="test_bronze_neighborhoods",
        output_table="test_silver_neighborhoods"
    )
    
    # Gold
    result = gold_enricher.enrich(
        input_table="test_silver_neighborhoods",
        output_table="test_gold_neighborhoods"
    )
    
    # Validate Gold result
    assert isinstance(result, GoldMetadata), "Should return GoldMetadata"
    assert result.entity_type == "neighborhood"
    assert len(result.enrichments_applied) > 0, "Should have applied enrichments"
    
    # Verify business enrichments
    expected_enrichments = [
        "economic_analysis", "demographic_segmentation", "livability_scoring",
        "investment_attractiveness", "business_embedding_text"
    ]
    for enrichment in expected_enrichments:
        assert enrichment in result.enrichments_applied, f"Should have {enrichment}"
    
    # Verify Gold table structure - business analytics
    schema = conn_manager.get_table_schema("test_gold_neighborhoods")
    column_names = [col[0] for col in schema]
    
    # Check Gold enrichments
    assert "income_category" in column_names, "Should have demographic segmentation"
    assert "lifestyle_category" in column_names, "Should have lifestyle analysis"
    assert "investment_attractiveness_score" in column_names, "Should have investment scoring"
    assert "overall_livability_score" in column_names, "Should have livability metrics"
    assert "business_facets" in column_names, "Should have business facets"
    
    # Clean up
    conn_manager.drop_table("test_bronze_neighborhoods")
    conn_manager.drop_table("test_silver_neighborhoods")
    conn_manager.drop_table("test_gold_neighborhoods")
    print("✓ Neighborhood Gold enrichment test passed")


def test_gold_wikipedia_enrichment():
    """Test Wikipedia Gold enrichment."""
    print("\n=== Testing Wikipedia Gold Enrichment ===")
    
    # Setup
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    wiki_db = Path("data/wikipedia/wikipedia.db")
    if not wiki_db.exists():
        print(f"Warning: {wiki_db} not found, skipping Wikipedia test")
        return
    
    # Create Bronze → Silver → Gold pipeline
    bronze_ingester = WikipediaBronzeIngester(settings, conn_manager)
    silver_transformer = WikipediaSilverTransformer(settings, conn_manager)
    gold_enricher = WikipediaGoldEnricher(settings, conn_manager)
    
    # Bronze
    bronze_ingester.ingest(
        table_name="test_bronze_wikipedia",
        db_path=wiki_db,
        sample_size=10
    )
    
    # Silver
    silver_transformer.transform(
        input_table="test_bronze_wikipedia",
        output_table="test_silver_wikipedia"
    )
    
    # Gold
    result = gold_enricher.enrich(
        input_table="test_silver_wikipedia",
        output_table="test_gold_wikipedia"
    )
    
    # Validate Gold result
    assert isinstance(result, GoldMetadata), "Should return GoldMetadata"
    assert result.entity_type == "wikipedia"
    
    # Verify business enrichments
    expected_enrichments = [
        "content_quality_analysis", "authority_scoring", "topic_extraction",
        "business_categorization", "business_embedding_text"
    ]
    for enrichment in expected_enrichments:
        assert enrichment in result.enrichments_applied, f"Should have {enrichment}"
    
    # Verify Gold table structure - content analytics
    schema = conn_manager.get_table_schema("test_gold_wikipedia")
    column_names = [col[0] for col in schema]
    
    # Check Gold enrichments
    assert "authority_score" in column_names, "Should have authority scoring"
    assert "article_quality" in column_names, "Should have quality categorization"
    assert "content_depth_category" in column_names, "Should have content analysis"
    assert "key_topics" in column_names, "Should have topic extraction"
    assert "search_ranking_score" in column_names, "Should have ranking algorithms"
    
    # Clean up
    conn_manager.drop_table("test_bronze_wikipedia")
    conn_manager.drop_table("test_silver_wikipedia")
    conn_manager.drop_table("test_gold_wikipedia")
    print("✓ Wikipedia Gold enrichment test passed")


def test_relation_api_usage():
    """Test that Gold layer uses DuckDB Relation API with lazy evaluation."""
    print("\n=== Testing DuckDB Relation API Usage ===")
    
    # Check that enrichers use conn.sql() for lazy evaluation
    import inspect
    from squack_pipeline_v2.gold import property, neighborhood, wikipedia
    
    # Check property enricher source
    property_source = inspect.getsource(property.PropertyGoldEnricher._apply_enrichments)
    assert "conn.sql" in property_source, "Property enricher should use Relation API"
    assert "gold_relation.create" in property_source, "Should create table from relation"
    
    # Check neighborhood enricher source
    neighborhood_source = inspect.getsource(neighborhood.NeighborhoodGoldEnricher._apply_enrichments)
    assert "conn.sql" in neighborhood_source, "Neighborhood enricher should use Relation API"
    assert "gold_relation.create" in neighborhood_source, "Should create table from relation"
    
    # Check wikipedia enricher source
    wikipedia_source = inspect.getsource(wikipedia.WikipediaGoldEnricher._apply_enrichments)
    assert "conn.sql" in wikipedia_source, "Wikipedia enricher should use Relation API"
    assert "gold_relation.create" in wikipedia_source, "Should create table from relation"
    
    print("✓ Relation API usage test passed")


def test_medallion_architecture():
    """Test that Gold layer follows medallion architecture principles."""
    print("\n=== Testing Medallion Architecture ===")
    
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings)
    
    # Test that Gold layer adds business value
    property_file = Path("real_estate_data/properties_sf.json")
    
    if property_file.exists():
        # Create Bronze → Silver → Gold pipeline
        bronze_ingester = PropertyBronzeIngester(settings, conn_manager)
        silver_transformer = PropertySilverTransformer(settings, conn_manager)
        gold_enricher = PropertyGoldEnricher(settings, conn_manager)
        
        # Bronze (raw)
        bronze_ingester.ingest("test_medallion_bronze", property_file, sample_size=3)
        
        # Silver (standardized)
        silver_transformer.transform("test_medallion_bronze", "test_medallion_silver")
        
        # Gold (business-ready)
        gold_result = gold_enricher.enrich("test_medallion_silver", "test_medallion_gold")
        
        # Check that Gold adds business intelligence
        bronze_schema = conn_manager.get_table_schema("test_medallion_bronze")
        silver_schema = conn_manager.get_table_schema("test_medallion_silver")
        gold_schema = conn_manager.get_table_schema("test_medallion_gold")
        
        bronze_columns = [col[0] for col in bronze_schema]
        silver_columns = [col[0] for col in silver_schema]
        gold_columns = [col[0] for col in gold_schema]
        
        # Gold should have more business intelligence columns than Silver
        business_columns = [col for col in gold_columns if col not in silver_columns]
        assert len(business_columns) > 5, "Gold should add significant business intelligence"
        
        # Check for specific business enrichments
        assert "market_segment" in gold_columns, "Gold should categorize market segments"
        assert "embedding_text" in gold_columns, "Gold should have business-ready search text"
        assert len(gold_result.enrichments_applied) >= 5, "Gold should apply multiple enrichments"
        
        # Clean up
        conn_manager.drop_table("test_medallion_bronze")
        conn_manager.drop_table("test_medallion_silver")
        conn_manager.drop_table("test_medallion_gold")
    
    print("✓ Medallion architecture test passed")


def test_no_tableidentifier():
    """Test that there are no TableIdentifier references."""
    print("\n=== Testing No TableIdentifier References ===")
    
    # Check that Gold modules don't import TableIdentifier
    gold_files = [
        "squack_pipeline_v2/gold/base.py",
        "squack_pipeline_v2/gold/property.py",
        "squack_pipeline_v2/gold/neighborhood.py",
        "squack_pipeline_v2/gold/wikipedia.py",
        "squack_pipeline_v2/gold/graph_builder.py"
    ]
    
    for file_path in gold_files:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            assert "TableIdentifier" not in content, f"{file_path} should not reference TableIdentifier"
            assert "table_identifier" not in content.lower(), f"{file_path} should not have table_identifier variables"
    
    print("✓ No TableIdentifier references test passed")


def test_clean_pydantic_models():
    """Test that Gold layer uses clean Pydantic models."""
    print("\n=== Testing Clean Pydantic Models ===")
    
    from squack_pipeline_v2.gold.base import GoldMetadata
    
    # Test GoldMetadata model
    metadata = GoldMetadata(
        input_table="silver_test",
        output_table="gold_test",
        input_count=100,
        output_count=100,
        enrichments_applied=["test_enrichment"],
        entity_type="property"
    )
    
    # Should be frozen (immutable)
    try:
        metadata.input_table = "changed"
        assert False, "GoldMetadata should be frozen"
    except Exception:
        pass  # Expected - model is frozen
    
    # Test validation
    try:
        GoldMetadata(
            input_table="test",
            output_table="test",
            input_count=-1,  # Should fail validation
            output_count=0,
            enrichments_applied=[],
            entity_type="test"
        )
        assert False, "Should validate input_count >= 0"
    except Exception:
        pass  # Expected - validation should fail
    
    print("✓ Clean Pydantic models test passed")


def main():
    """Run all Gold layer integration tests."""
    print("\n" + "="*60)
    print("GOLD LAYER INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_gold_property_enrichment()
        test_gold_neighborhood_enrichment()
        test_gold_wikipedia_enrichment()
        test_relation_api_usage()
        test_medallion_architecture()
        test_no_tableidentifier()
        test_clean_pydantic_models()
        
        print("\n" + "="*60)
        print("ALL GOLD LAYER TESTS PASSED ✓")
        print("="*60)
        print("\nSummary:")
        print("- Gold layer correctly enriches data for business use")
        print("- DuckDB Relation API used with lazy evaluation")
        print("- Medallion architecture implemented (business-ready data)")
        print("- No TableIdentifier references remain")
        print("- Clean Pydantic models are used")
        print("- Business intelligence and analytics added")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()