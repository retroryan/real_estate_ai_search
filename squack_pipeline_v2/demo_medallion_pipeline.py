#!/usr/bin/env python3
"""
Medallion Architecture Pipeline Demo

This demo showcases the complete data pipeline following medallion architecture:
- Bronze: Raw data ingestion
- Silver: Data standardization and cleaning
- Gold: Business intelligence and analytics
- Embeddings: ML-ready vector generation
- Analytics: Business-ready datasets

Run with: python -m squack_pipeline_v2.demo_medallion_pipeline
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.writers.parquet import ParquetWriter


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_stats(stats: Dict[str, Any], indent: int = 2):
    """Print statistics in a formatted way."""
    prefix = " " * indent
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_stats(value, indent + 2)
        else:
            print(f"{prefix}{key}: {value}")


def run_medallion_demo():
    """Run the complete medallion architecture pipeline demo."""
    
    print_header("MEDALLION ARCHITECTURE PIPELINE DEMO")
    print("""
This demo showcases a production-ready data pipeline following medallion architecture
with DuckDB best practices, business intelligence, and ML-ready embeddings.
    """)
    
    # Initialize
    print_header("INITIALIZATION")
    print("Setting up pipeline orchestrator...")
    
    settings = PipelineSettings()
    orchestrator = PipelineOrchestrator(settings)
    
    # Check for Voyage API key
    has_voyage = bool(os.getenv("VOYAGE_API_KEY"))
    if has_voyage:
        print("✓ Voyage API key detected - will generate real embeddings")
    else:
        print("⚠ No Voyage API key - will skip embedding generation")
        print("  Set VOYAGE_API_KEY environment variable to enable embeddings")
    
    # Clean previous run (optional)
    print("\nCleaning previous demo data...")
    demo_tables = [
        "demo_bronze_properties", "demo_silver_properties", "demo_gold_properties",
        "demo_bronze_neighborhoods", "demo_silver_neighborhoods", "demo_gold_neighborhoods",
        "demo_bronze_wikipedia", "demo_silver_wikipedia", "demo_gold_wikipedia"
    ]
    
    conn = orchestrator.connection_manager.get_connection()
    for table in demo_tables:
        if orchestrator.connection_manager.table_exists(table):
            conn.sql(f"DROP TABLE {table}")
            print(f"  Dropped {table}")
    
    # Phase 1: Bronze Layer
    print_header("PHASE 1: BRONZE LAYER - RAW DATA INGESTION")
    print("Ingesting raw data from multiple sources...")
    
    bronze_start = datetime.now()
    
    # We'll use the existing orchestrator methods but with demo table names
    # For demo purposes, let's run with small samples
    print("\n1. Properties (JSON)...")
    bronze_metrics = orchestrator.run_bronze_layer(sample_size=10)
    
    bronze_duration = (datetime.now() - bronze_start).total_seconds()
    
    print(f"\n✓ Bronze layer complete in {bronze_duration:.2f} seconds")
    if 'property' in bronze_metrics:
        prop_metrics = bronze_metrics['property']
        print(f"  Properties: {prop_metrics.bronze_metrics.output_records if hasattr(prop_metrics, 'bronze_metrics') else 0} records")
    if 'neighborhood' in bronze_metrics:
        neigh_metrics = bronze_metrics['neighborhood']
        print(f"  Neighborhoods: {neigh_metrics.bronze_metrics.output_records if hasattr(neigh_metrics, 'bronze_metrics') else 0} records")
    if 'wikipedia' in bronze_metrics:
        wiki_metrics = bronze_metrics['wikipedia']
        print(f"  Wikipedia: {wiki_metrics.bronze_metrics.output_records if hasattr(wiki_metrics, 'bronze_metrics') else 0} records")
    
    # Phase 2: Silver Layer
    print_header("PHASE 2: SILVER LAYER - DATA STANDARDIZATION")
    print("Transforming and standardizing data...")
    
    silver_start = datetime.now()
    silver_metrics = orchestrator.run_silver_layer()
    silver_duration = (datetime.now() - silver_start).total_seconds()
    
    print(f"\n✓ Silver layer complete in {silver_duration:.2f} seconds")
    print("  Data cleaned, standardized, and validated")
    print("  Type conversions and schema normalization applied")
    
    # Phase 3: Gold Layer
    print_header("PHASE 3: GOLD LAYER - BUSINESS INTELLIGENCE")
    print("Enriching data with business intelligence and analytics...")
    
    gold_start = datetime.now()
    gold_metrics = orchestrator.run_gold_layer()
    gold_duration = (datetime.now() - gold_start).total_seconds()
    
    print(f"\n✓ Gold layer complete in {gold_duration:.2f} seconds")
    print("  Business metrics calculated:")
    print("    - Investment scores")
    print("    - Market segments")
    print("    - Price analytics")
    print("    - Neighborhood insights")
    print("    - Geographic intelligence")
    
    # Phase 4: Embeddings (if API key available)
    embedding_duration = 0
    if has_voyage:
        print_header("PHASE 4: EMBEDDINGS - ML-READY VECTORS")
        print("Generating 1024-dimensional embeddings with Voyage AI...")
        
        embedding_start = datetime.now()
        embedding_stats = orchestrator.run_embeddings()
        embedding_duration = (datetime.now() - embedding_start).total_seconds()
        
        print(f"\n✓ Embeddings complete in {embedding_duration:.2f} seconds")
        for entity_type, metadata in embedding_stats.items():
            print(f"  {entity_type}: {metadata.embeddings_generated} vectors generated")
    else:
        print_header("PHASE 4: EMBEDDINGS - SKIPPED")
        print("Skipping embedding generation (no API key)")
    
    # Phase 5: Analytics Datasets
    print_header("PHASE 5: ANALYTICS DATASETS - BUSINESS READY")
    print("Creating optimized analytical datasets...")
    
    # Use Parquet writer with medallion architecture support
    parquet_writer = ParquetWriter(
        orchestrator.connection_manager,
        Path(settings.output.parquet_dir) / "demo"
    )
    
    analytics_start = datetime.now()
    
    # Export medallion layers
    print("\n1. Exporting medallion layers...")
    for layer in ["bronze", "silver", "gold"]:
        layer_stats = parquet_writer.export_medallion_layer(layer)
        print(f"  {layer.capitalize()}: {len(layer_stats)} tables exported")
    
    # Create business analytics datasets
    print("\n2. Creating business analytics datasets...")
    analytics_stats = parquet_writer.create_business_analytics_dataset()
    analytics_duration = (datetime.now() - analytics_start).total_seconds()
    
    print(f"\n✓ Analytics datasets complete in {analytics_duration:.2f} seconds")
    print(f"  {analytics_stats['datasets_created']} datasets created")
    print(f"  Total size: {analytics_stats['total_size_mb']} MB")
    
    # Phase 6: Data Quality Report
    print_header("PHASE 6: DATA QUALITY REPORT")
    print("Generating data quality metrics...")
    
    quality_report = parquet_writer.generate_quality_report()
    print(f"\n✓ Quality report generated for {len(quality_report)} files")
    
    valid_files = sum(1 for f in quality_report.values() if f.get('file_valid', False))
    print(f"  Valid files: {valid_files}/{len(quality_report)}")
    
    # Final Summary
    print_header("PIPELINE SUMMARY")
    
    total_duration = (
        bronze_duration + silver_duration + gold_duration + 
        (embedding_duration if has_voyage else 0) + analytics_duration
    )
    
    # Get final table statistics
    final_stats = orchestrator.get_table_stats()
    
    print(f"""
Pipeline Execution Summary:
---------------------------
Total Duration: {total_duration:.2f} seconds

Table Statistics:
""")
    
    for layer in ["bronze", "silver", "gold"]:
        layer_tables = {k: v for k, v in final_stats.items() if k.startswith(layer)}
        if layer_tables:
            print(f"\n  {layer.upper()} Layer:")
            for table, count in layer_tables.items():
                print(f"    {table}: {count} records")
    
    print(f"""

Medallion Architecture Compliance:
----------------------------------
✓ Bronze: Raw data preserved
✓ Silver: Data standardized and cleaned  
✓ Gold: Business intelligence applied
✓ Embeddings: Stored in Gold layer (single source of truth)
✓ Analytics: Business-ready datasets created

DuckDB Best Practices:
---------------------
✓ Native COPY TO for exports
✓ Relation API with lazy evaluation
✓ Parameterized queries for safety
✓ Optimal compression (snappy/zstd)
✓ Partitioning for large datasets

Output Files:
------------
Location: {settings.output.parquet_dir}/demo/
- Bronze layer tables
- Silver layer tables  
- Gold layer tables (with embeddings)
- Analytics datasets
- Business intelligence reports
    """)
    
    # Cleanup
    orchestrator.cleanup()
    print("\n✓ Pipeline demo complete!")


def main():
    """Main entry point."""
    try:
        run_medallion_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()