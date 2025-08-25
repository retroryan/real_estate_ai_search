#!/usr/bin/env python
"""
Minimal CLI for multi-entity ingestion.
Usage: python -m real_estate_search.ingestion.main [--force-recreate]
"""

import click
import sys
from pathlib import Path

# Support both module and direct execution
try:
    from .orchestrator import IngestionOrchestrator
except ImportError:
    from orchestrator import IngestionOrchestrator


@click.command()
@click.option('--config', default='config.yaml', help='Config file path')
@click.option('--force-recreate', is_flag=True, help='Recreate all indices')
@click.option('--properties-only', is_flag=True, help='Ingest only properties')
@click.option('--wiki-only', is_flag=True, help='Ingest only Wikipedia data')
def main(config: str, force_recreate: bool, properties_only: bool, wiki_only: bool):
    """
    Multi-entity ingestion for Elasticsearch.
    
    This orchestrates existing components:
    - PropertyIndexer from real_estate_search
    - WikipediaEmbeddingPipeline from wiki_embed
    - Minimal summary ingestion logic
    """
    # Check config exists
    if not Path(config).exists():
        click.echo(f"❌ Config file not found: {config}")
        sys.exit(1)
    
    click.echo(f"🚀 Starting multi-entity ingestion")
    click.echo(f"   Config: {config}")
    click.echo(f"   Force recreate: {force_recreate}")
    
    # Initialize pipeline
    try:
        pipeline = IngestionOrchestrator(config_path=config)
    except Exception as e:
        click.echo(f"❌ Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    # Run ingestion
    try:
        if properties_only:
            click.echo("\n📦 Ingesting properties only...")
            stats = {"properties": pipeline._ingest_properties(force_recreate)}
        elif wiki_only:
            click.echo("\n📚 Ingesting Wikipedia data only...")
            stats = {
                "wiki_chunks": pipeline._ingest_wiki_chunks(force_recreate),
                "wiki_summaries": pipeline._ingest_wiki_summaries(force_recreate)
            }
        else:
            click.echo("\n🔄 Running full ingestion...")
            stats = pipeline.ingest_all(force_recreate)
        
        # Display results
        click.echo("\n✅ Ingestion complete!")
        click.echo("\n📊 Statistics:")
        for index_type, stat in stats.items():
            status = stat.get("status", "unknown")
            indexed = stat.get("indexed", 0)
            
            if status == "success":
                click.echo(f"   ✓ {index_type}: {indexed} documents")
            elif status == "no_data":
                click.echo(f"   ⚠ {index_type}: No data found")
            else:
                error = stat.get("error", "Unknown error")
                click.echo(f"   ✗ {index_type}: Failed - {error}")
        
    except Exception as e:
        click.echo(f"\n❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()