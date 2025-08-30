"""Main pipeline orchestrator following DuckDB best practices.

Coordinates the flow:
1. Bronze: Ingest raw data
2. Silver: Standardize and clean
3. Gold: Enrich and compute metrics
4. Embeddings: Generate vectors
5. Writers: Export to Parquet/Elasticsearch
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.logging import log_stage, setup_logging
from squack_pipeline_v2.core.table_names import ENTITY_TYPES, EntityType
from squack_pipeline_v2.models.pipeline.metrics import PipelineMetrics, EntityMetrics, StageMetrics

# Bronze layer
from squack_pipeline_v2.bronze.property import PropertyBronzeIngester
from squack_pipeline_v2.bronze.neighborhood import NeighborhoodBronzeIngester
from squack_pipeline_v2.bronze.wikipedia import WikipediaBronzeIngester

# Silver layer
from squack_pipeline_v2.silver.property import PropertySilverTransformer
from squack_pipeline_v2.silver.neighborhood import NeighborhoodSilverTransformer
from squack_pipeline_v2.silver.wikipedia import WikipediaSilverTransformer

# Gold layer
from squack_pipeline_v2.gold.property import PropertyGoldEnricher
from squack_pipeline_v2.gold.neighborhood import NeighborhoodGoldEnricher
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher

# Embeddings
from squack_pipeline_v2.embeddings.generator import EmbeddingGenerator
from squack_pipeline_v2.embeddings.providers import create_provider

# Writers
from squack_pipeline_v2.writers.parquet import ParquetWriter
from squack_pipeline_v2.writers.elasticsearch import ElasticsearchWriter

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the entire medallion architecture pipeline.
    
    Following DuckDB best practices:
    - Single connection throughout pipeline
    - SQL-based transformations
    - Efficient data movement
    - Clear separation of concerns
    """
    
    def __init__(self, settings: Optional[PipelineSettings] = None):
        """Initialize orchestrator.
        
        Args:
            settings: Pipeline settings (uses defaults if not provided)
        """
        self.settings = settings or PipelineSettings()
        self.connection_manager = ConnectionManager(self.settings.database)
        self.pipeline_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        setup_logging(self.settings.log_level)
        
        # Track metrics
        self.metrics = {}
    
    @log_stage("Pipeline: Run Bronze Layer")
    def run_bronze_layer(
        self,
        sample_size: Optional[int] = None
    ) -> Dict[str, EntityMetrics]:
        """Run Bronze layer ingestion for all entities.
        
        Args:
            sample_size: Optional sample size for testing
            
        Returns:
            Bronze layer metrics
        """
        metrics = {}
        
        # Property ingestion
        entity = ENTITY_TYPES.property
        ingester = PropertyBronzeIngester(self.settings, self.connection_manager)
        start_time = datetime.now()
        
        ingester.ingest(
                table_name=entity.bronze_table,
                sample_size=sample_size
            )
            
            end_time = datetime.now()
            
            metrics[entity.name] = EntityMetrics(
                entity_type=entity.name,
                bronze_metrics=StageMetrics(
                    stage_name="bronze",
                    input_records=ingester.records_ingested,
                    output_records=ingester.records_ingested,
                    dropped_records=0,
                    start_time=start_time,
                    end_time=end_time
                )
            )
        
        # Neighborhood ingestion
        entity = ENTITY_TYPES.neighborhood
        ingester = NeighborhoodBronzeIngester(self.settings, self.connection_manager)
        start_time = datetime.now()
            
        ingester.ingest(
            table_name=entity.bronze_table,
            sample_size=sample_size
        )
        
        end_time = datetime.now()
        
        metrics[entity.name] = EntityMetrics(
            entity_type=entity.name,
            bronze_metrics=StageMetrics(
                stage_name="bronze",
                input_records=ingester.records_ingested,
                output_records=ingester.records_ingested,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        )
        
        # Wikipedia ingestion
        entity = ENTITY_TYPES.wikipedia
        ingester = WikipediaBronzeIngester(self.settings, self.connection_manager)
        start_time = datetime.now()
            
        ingester.ingest(
            table_name=entity.bronze_table,
            sample_size=sample_size
        )
        
        end_time = datetime.now()
        
        metrics[entity.name] = EntityMetrics(
            entity_type=entity.name,
            bronze_metrics=StageMetrics(
                stage_name="bronze",
                input_records=ingester.records_ingested,
                output_records=ingester.records_ingested,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        )
        
        return metrics
    
    @log_stage("Pipeline: Run Silver Layer")
    def run_silver_layer(self) -> Dict[str, StageMetrics]:
        """Run Silver layer transformations for all entities.
            
        Returns:
            Silver layer metrics
        """
        metrics = {}
        
        # Property transformation
            entity = ENTITY_TYPES.property
            transformer = PropertySilverTransformer(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            transformer.transform(entity.bronze_table, entity.silver_table)
            
            end_time = datetime.now()
            
            # Get record count
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.silver_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="silver",
                input_records=count,  # Approximate
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        # Neighborhood transformation
            entity = ENTITY_TYPES.neighborhood
            transformer = NeighborhoodSilverTransformer(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            transformer.transform(entity.bronze_table, entity.silver_table)
            
            end_time = datetime.now()
            
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.silver_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="silver",
                input_records=count,
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        # Wikipedia transformation
            entity = ENTITY_TYPES.wikipedia
            transformer = WikipediaSilverTransformer(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            transformer.transform(entity.bronze_table, entity.silver_table)
            
            end_time = datetime.now()
            
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.silver_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="silver",
                input_records=count,
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        return metrics
    
    @log_stage("Pipeline: Run Gold Layer")
    def run_gold_layer(self) -> Dict[str, StageMetrics]:
        """Run Gold layer enrichments for all entities.
            
        Returns:
            Gold layer metrics
        """
        metrics = {}
        
        # Property enrichment
            entity = ENTITY_TYPES.property
            enricher = PropertyGoldEnricher(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            enricher.enrich(entity.silver_table, entity.gold_table)
            
            end_time = datetime.now()
            
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.gold_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="gold",
                input_records=count,
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        # Neighborhood enrichment
            entity = ENTITY_TYPES.neighborhood
            enricher = NeighborhoodGoldEnricher(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            enricher.enrich(entity.silver_table, entity.gold_table)
            
            end_time = datetime.now()
            
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.gold_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="gold",
                input_records=count,
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        # Wikipedia enrichment
            entity = ENTITY_TYPES.wikipedia
            enricher = WikipediaGoldEnricher(self.settings, self.connection_manager)
            start_time = datetime.now()
            
            enricher.enrich(entity.silver_table, entity.gold_table)
            
            end_time = datetime.now()
            
            count = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {entity.gold_table}"
            ).fetchone()[0]
            
            metrics[entity.name] = StageMetrics(
                stage_name="gold",
                input_records=count,
                output_records=count,
                dropped_records=0,
                start_time=start_time,
                end_time=end_time
            )
        
        return metrics
    
    @log_stage("Pipeline: Generate Embeddings")
    def run_embeddings(
        self,
        provider_type: str = "voyage",
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for Gold data.
        
        Args:
            provider_type: Embedding provider (voyage, openai, ollama)
            api_key: API key if required
            
        Returns:
            Embedding generation statistics
        """
        # Create provider
        provider = create_provider(
            provider_type=provider_type,
            api_key=api_key or self.settings.embedding.api_key,
            model_name=self.settings.embedding.model_name,
            dimension=self.settings.embedding.dimension
        )
        
        # Generate embeddings
        generator = EmbeddingGenerator(self.connection_manager, provider)
        stats = generator.generate_all_embeddings()
        
        return stats
    
    @log_stage("Pipeline: Export Data")
    def run_writers(
        self,
        write_parquet: bool = True,
        write_elasticsearch: bool = False
    ) -> Dict[str, Any]:
        """Export data to Parquet and/or Elasticsearch.
        
        Args:
            write_parquet: Export to Parquet files
            write_elasticsearch: Export to Elasticsearch
            
        Returns:
            Export statistics
        """
        stats = {}
        
        # Parquet export
        if write_parquet and self.settings.output.parquet_enabled:
            writer = ParquetWriter(
                self.connection_manager,
                Path(self.settings.output.parquet_dir)
            )
            stats["parquet"] = writer.export_all_layers()
            
            # Also export denormalized view
            stats["parquet"]["denormalized"] = writer.export_denormalized_properties()
        
        # Elasticsearch export
        if write_elasticsearch or self.settings.output.elasticsearch_enabled:
            writer = ElasticsearchWriter(
                self.connection_manager,
                self.settings.output.elasticsearch.host,
                self.settings.output.elasticsearch.port
            )
            stats["elasticsearch"] = writer.index_all()
        
        return stats
    
    @log_stage("Pipeline: Full Run")
    def run_full_pipeline(
        self,
        sample_size: Optional[int] = None,
        generate_embeddings: bool = True,
        write_parquet: bool = True,
        write_elasticsearch: bool = False
    ) -> PipelineMetrics:
        """Run the complete pipeline end-to-end for all entities.
        
        Args:
            sample_size: Optional sample size for testing
            generate_embeddings: Generate embeddings
            write_parquet: Export to Parquet
            write_elasticsearch: Export to Elasticsearch
            
        Returns:
            Complete pipeline metrics
        """
        pipeline_start = datetime.now()
        
        logger.info(f"Starting pipeline run: {self.pipeline_id}")
        
        try:
            # Bronze layer
            logger.info("Running Bronze layer...")
            bronze_metrics = self.run_bronze_layer(sample_size)
            
            # Silver layer
            logger.info("Running Silver layer...")
            silver_metrics = self.run_silver_layer()
            
            # Gold layer
            logger.info("Running Gold layer...")
            gold_metrics = self.run_gold_layer()
            
            # Update entity metrics
            for entity_type in bronze_metrics:
                if entity_type in silver_metrics:
                    bronze_metrics[entity_type] = EntityMetrics(
                        entity_type=entity_type,
                        bronze_metrics=bronze_metrics[entity_type].bronze_metrics,
                        silver_metrics=silver_metrics[entity_type],
                        gold_metrics=gold_metrics.get(entity_type)
                    )
            
            # Embeddings
            embedding_stats = {}
            if generate_embeddings and self.settings.embedding.enabled:
                logger.info("Generating embeddings...")
                embedding_stats = self.run_embeddings()
            
            # Writers
            writer_stats = {}
            if write_parquet or write_elasticsearch:
                logger.info("Exporting data...")
                writer_stats = self.run_writers(write_parquet, write_elasticsearch)
            
            pipeline_end = datetime.now()
            
            # Create pipeline metrics
            metrics = PipelineMetrics(
                pipeline_id=self.pipeline_id,
                start_time=pipeline_start,
                end_time=pipeline_end,
                property_metrics=bronze_metrics.get("property"),
                neighborhood_metrics=bronze_metrics.get("neighborhood"),
                wikipedia_metrics=bronze_metrics.get("wikipedia"),
                status="completed"
            )
            
            logger.info(f"Pipeline completed successfully in {metrics.duration}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            
            return PipelineMetrics(
                pipeline_id=self.pipeline_id,
                start_time=pipeline_start,
                end_time=datetime.now(),
                status="failed",
                error_messages=[str(e)]
            )
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get record counts for all tables.
        
        Returns:
            Table names and record counts
        """
        tables = []
        for entity in ENTITY_TYPES.all_entities():
            tables.extend([
                entity.bronze_table,
                entity.silver_table,
                entity.gold_table,
                entity.embeddings_table
            ])
        
        stats = {}
        for table in tables:
            if self.connection_manager.table_exists(table):
                count = self.connection_manager.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                stats[table] = count
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        self.connection_manager.close()