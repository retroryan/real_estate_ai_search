"""Main orchestrator that coordinates entity-specific pipelines."""

import time
from typing import Optional, List
from pathlib import Path

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.orchestrator.property_orchestrator import PropertyPipelineOrchestrator
from squack_pipeline.orchestrator.neighborhood_orchestrator import NeighborhoodPipelineOrchestrator
from squack_pipeline.orchestrator.wikipedia_orchestrator import WikipediaPipelineOrchestrator
from squack_pipeline.models import EntityType
from squack_pipeline.models.data_types import PipelineMetrics, EntityMetrics
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class MainPipelineOrchestrator:
    """Main orchestrator that coordinates all entity-specific pipelines."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the main pipeline orchestrator.
        
        Args:
            settings: Pipeline configuration settings
        """
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize shared connection manager
        self.connection_manager = DuckDBConnectionManager()
        self.connection_manager.initialize(settings)
        
        # Initialize entity-specific orchestrators
        self.property_orchestrator = PropertyPipelineOrchestrator(settings, self.connection_manager)
        self.neighborhood_orchestrator = NeighborhoodPipelineOrchestrator(settings, self.connection_manager)
        self.wikipedia_orchestrator = WikipediaPipelineOrchestrator(settings, self.connection_manager)
        
        # Map entity types to orchestrators
        self.orchestrators = {
            EntityType.PROPERTY: self.property_orchestrator,
            EntityType.NEIGHBORHOOD: self.neighborhood_orchestrator,
            EntityType.WIKIPEDIA: self.wikipedia_orchestrator,
        }
        
        # Overall metrics
        self.overall_metrics = PipelineMetrics()
    
    @log_execution_time
    def run(
        self,
        entities: Optional[List[EntityType]] = None,
        sample_size: Optional[int] = None,
        dry_run: bool = False,
        skip_elasticsearch: bool = False
    ) -> PipelineMetrics:
        """Run the complete pipeline for specified entities.
        
        Args:
            entities: List of entity types to process (default: all)
            sample_size: Optional number of records to process per entity
            dry_run: If True, validate configuration without processing
            skip_elasticsearch: Whether to skip writing to Elasticsearch
            
        Returns:
            Dictionary of overall metrics
        """
        start_time = time.time()
        
        # Determine which entities to process
        entities_to_process = entities or list(self.orchestrators.keys())
        
        try:
            self.logger.info(f"Starting SQUACK pipeline for entities: {[e.value for e in entities_to_process]}")
            
            if dry_run:
                self.logger.info("Dry run mode - validating configuration only")
                self._validate_configuration()
                self.logger.success("Configuration validation passed")
                return {"dry_run": True, "validation": "passed"}
            
            # Process each entity
            for entity_type in entities_to_process:
                orchestrator = self.orchestrators[entity_type]
                
                self.logger.info(f"Processing {entity_type.value} entity...")
                
                try:
                    # Run entity-specific pipeline
                    entity_metrics = orchestrator.run(
                        sample_size=sample_size,
                        skip_elasticsearch=skip_elasticsearch
                    )
                    
                    # Store metrics
                    self.overall_metrics.entity_metrics[entity_type.value] = entity_metrics
                    self.overall_metrics.total_records += entity_metrics.gold_records
                    self.overall_metrics.total_embeddings += entity_metrics.embeddings_generated
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {entity_type.value}: {e}")
                    
                    if True:  # Always fail fast for now
                        raise
                    else:
                        # Continue with other entities
                        failed_metrics = EntityMetrics(error=str(e))
                        self.overall_metrics.entity_metrics[entity_type.value] = failed_metrics
            
            # Calculate total duration
            self.overall_metrics.pipeline_duration = time.time() - start_time
            
            # Log summary
            self._log_summary()
            
            return self.overall_metrics
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
        
        finally:
            # Clean up connections
            self.connection_manager.close()
    
    def _validate_configuration(self) -> None:
        """Validate pipeline configuration."""
        # Check data sources exist
        for file_path in self.settings.data_sources.properties_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Property file not found: {file_path}")
        
        for file_path in self.settings.data_sources.neighborhoods_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Neighborhood file not found: {file_path}")
        
        if not self.settings.data_sources.wikipedia_db.exists():
            raise FileNotFoundError(f"Wikipedia database not found: {self.settings.data_sources.wikipedia_db}")
        
        # Check output directory
        output_dir = Path(self.settings.output.base_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created output directory: {output_dir}")
        
        # Validate Elasticsearch connection if not skipping
        if self.settings.output.elasticsearch.enabled:
            from squack_pipeline.writers.elasticsearch.writer import ElasticsearchWriter
            
            es_writer = ElasticsearchWriter(self.settings.output.elasticsearch)
            if not es_writer.verify_connection():
                raise ConnectionError("Failed to connect to Elasticsearch")
            es_writer.close()
    
    def _log_summary(self) -> None:
        """Log pipeline execution summary."""
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        
        for entity_type, metrics in self.overall_metrics.entity_metrics.items():
            if metrics.error:
                self.logger.error(f"{entity_type}: FAILED - {metrics.error}")
            else:
                self.logger.success(
                    f"{entity_type}: "
                    f"{metrics.bronze_records} → "
                    f"{metrics.silver_records} → "
                    f"{metrics.gold_records} records"
                )
                
                if metrics.elasticsearch_records:
                    self.logger.info(f"  → Elasticsearch: {metrics.elasticsearch_records} records")
                
                if metrics.embeddings_generated:
                    self.logger.info(f"  → Embeddings: {metrics.embeddings_generated} generated")
        
        self.logger.info("-" * 60)
        self.logger.info(f"Total records processed: {self.overall_metrics.total_records}")
        if self.overall_metrics.total_embeddings > 0:
            self.logger.info(f"Total embeddings generated: {self.overall_metrics.total_embeddings}")
            embedding_rate = (self.overall_metrics.total_embeddings / self.overall_metrics.total_records * 100) if self.overall_metrics.total_records > 0 else 0
            self.logger.info(f"Embedding coverage: {embedding_rate:.1f}%")
        self.logger.info(f"Total duration: {self.overall_metrics.pipeline_duration:.2f} seconds")
        self.logger.info("=" * 60)