"""Main entry point for the SQUACK pipeline."""

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger


app = typer.Typer(
    name="squack-pipeline",
    help="SQUACK Pipeline - DuckDB-based data processing pipeline",
    add_completion=False,
)


@app.command()
def run(
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Path to configuration YAML file")
    ] = None,
    sample_size: Annotated[
        Optional[int],
        typer.Option("--sample-size", "-s", help="Sample size for testing")
    ] = None,
    entities: Annotated[
        Optional[str],
        typer.Option("--entities", help="Comma-separated list of entities to process (properties,neighborhoods,wikipedia)")
    ] = None,
    environment: Annotated[
        str,
        typer.Option("--environment", "-e", help="Environment name")
    ] = "development",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Run without writing output")
    ] = False,
    skip_elasticsearch: Annotated[
        bool,
        typer.Option("--skip-elasticsearch", help="Skip writing to Elasticsearch")
    ] = False,
    validate: Annotated[
        bool,
        typer.Option("--validate", help="Validate configuration and exit")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging")
    ] = False,
    generate_embeddings: Annotated[
        Optional[bool],
        typer.Option("--generate-embeddings/--no-embeddings", help="Enable/disable embedding generation")
    ] = None,
):
    """Run the SQUACK pipeline."""
    try:
        # Load configuration
        if config and config.exists():
            settings = PipelineSettings.load_from_yaml(config)
        else:
            # Try to load from default config.yaml location
            default_config = Path("squack_pipeline/config.yaml")
            if default_config.exists():
                settings = PipelineSettings.load_from_yaml(default_config)
            else:
                settings = PipelineSettings()
        
        # Override settings from CLI
        if sample_size:
            settings.data.sample_size = sample_size
        if environment:
            settings.environment = environment
        if dry_run:
            settings.dry_run = dry_run
        if verbose:
            settings.logging.level = "DEBUG"
        if generate_embeddings is not None:
            settings.processing.generate_embeddings = generate_embeddings
        
        # Initialize logging
        PipelineLogger.setup(settings.logging)
        logger = PipelineLogger.get_logger("main")
        
        # Log configuration
        logger.info(f"Starting SQUACK Pipeline v{settings.pipeline_version}")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Dry run: {settings.dry_run}")
        if settings.data.sample_size:
            logger.info(f"Sample size: {settings.data.sample_size}")
        
        # Validate configuration
        if validate:
            logger.success("Configuration is valid")
            typer.echo("✓ Configuration validation successful")
            return
        
        # Import orchestrator here to avoid circular imports
        from squack_pipeline.orchestrator.main_orchestrator import MainPipelineOrchestrator
        from squack_pipeline.models import EntityType
        
        # Parse entities if provided
        entities_to_process = None
        if entities:
            entity_map = {
                "properties": EntityType.PROPERTY,
                "neighborhoods": EntityType.NEIGHBORHOOD,
                "wikipedia": EntityType.WIKIPEDIA,
            }
            entities_to_process = []
            for entity_name in entities.split(","):
                entity_name = entity_name.strip().lower()
                if entity_name in entity_map:
                    entities_to_process.append(entity_map[entity_name])
                else:
                    logger.warning(f"Unknown entity type: {entity_name}")
        
        # Create and run pipeline
        orchestrator = MainPipelineOrchestrator(settings)
        metrics = orchestrator.run(
            entities=entities_to_process,
            sample_size=sample_size,
            dry_run=dry_run,
            skip_elasticsearch=skip_elasticsearch
        )
        
        if not dry_run:
            logger.success(f"Pipeline completed successfully - {metrics.total_records} records processed")
        
    except Exception as e:
        typer.echo(f"✗ Pipeline failed: {e}", err=True)
        sys.exit(1)


@app.command()
def validate_config(
    config: Annotated[
        Path,
        typer.Argument(help="Path to configuration YAML file")
    ],
):
    """Validate a configuration file."""
    try:
        settings = PipelineSettings.load_from_yaml(config)
        typer.echo(f"✓ Configuration file '{config}' is valid")
        typer.echo(f"  Pipeline: {settings.pipeline_name} v{settings.pipeline_version}")
        typer.echo(f"  Environment: {settings.environment}")
    except Exception as e:
        typer.echo(f"✗ Configuration validation failed: {e}", err=True)
        sys.exit(1)


@app.command()
def show_config(
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Path to configuration YAML file")
    ] = None,
):
    """Show current configuration."""
    try:
        if config and config.exists():
            settings = PipelineSettings.load_from_yaml(config)
        else:
            settings = PipelineSettings()
        
        import json
        config_dict = settings.model_dump()
        typer.echo(json.dumps(config_dict, indent=2, default=str))
    except Exception as e:
        typer.echo(f"✗ Failed to show configuration: {e}", err=True)
        sys.exit(1)


@app.command()
def version():
    """Show pipeline version."""
    settings = PipelineSettings()
    typer.echo(f"SQUACK Pipeline v{settings.pipeline_version}")


if __name__ == "__main__":
    app()