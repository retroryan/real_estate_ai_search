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
from squack_pipeline_v2.bronze.location import LocationBronzeIngester

# Silver layer
from squack_pipeline_v2.silver.property import PropertySilverTransformer
from squack_pipeline_v2.silver.neighborhood import NeighborhoodSilverTransformer
from squack_pipeline_v2.silver.wikipedia import WikipediaSilverTransformer
from squack_pipeline_v2.silver.location import LocationSilverTransformer

# Gold layer
from squack_pipeline_v2.gold.property import PropertyGoldEnricher
from squack_pipeline_v2.gold.neighborhood import NeighborhoodGoldEnricher
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher
from squack_pipeline_v2.gold.location import LocationGoldEnricher

# Embeddings
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
        self.connection_manager = ConnectionManager(self.settings.duckdb)
        self.pipeline_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        setup_logging(self.settings.logging.level)
        
        # Initialize embedding provider once at startup
        self.embedding_provider = self._initialize_embedding_provider()
        
        # Track metrics
        self.metrics = {}
    
    def _initialize_embedding_provider(self) -> Optional['EmbeddingProvider']:
        """Initialize embedding provider once at startup.
        
        Returns:
            Configured embedding provider or None if disabled
        """
        # Get API key for configured provider
        api_key = self.settings.get_api_key()
        
        # Validate API key is present for providers that require it
        provider_type = self.settings.embedding.provider
        if provider_type in ["voyage", "openai", "gemini"] and not api_key:
            logger.warning(f"No API key found for {provider_type} provider. Embeddings will be disabled.")
            return None
        
        # Create provider once
        try:
            provider = create_provider(
                provider_type=provider_type,
                api_key=api_key,
                model_name=self.settings.get_model_name(),
                base_url=self.settings.embedding.ollama_base_url if provider_type == "ollama" else None
            )
            logger.info(f"Embedding provider initialized: {provider_type}")
            return provider
        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            return None
    
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
        
        # Location ingestion
        entity = ENTITY_TYPES.location
        ingester = LocationBronzeIngester(self.settings, self.connection_manager)
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
        
        # Location transformation (MUST BE FIRST - neighborhoods depend on it)
        entity = ENTITY_TYPES.location
        transformer = LocationSilverTransformer(self.settings, self.connection_manager)
        start_time = datetime.now()
        
        transformer.transform(entity.bronze_table, entity.silver_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.silver_table)
        
        metrics[entity.name] = StageMetrics(
            stage_name="silver",
            input_records=count,
            output_records=count,
            dropped_records=0,
            start_time=start_time,
            end_time=end_time
        )
        
        # Property transformation
        entity = ENTITY_TYPES.property
        transformer = PropertySilverTransformer(self.settings, self.connection_manager, self.embedding_provider)
        start_time = datetime.now()
        
        transformer.transform(entity.bronze_table, entity.silver_table)
        
        end_time = datetime.now()
        
        # Get record count
        count = self.connection_manager.count_records(entity.silver_table)
        
        metrics[entity.name] = StageMetrics(
            stage_name="silver",
            input_records=count,  # Approximate
            output_records=count,
            dropped_records=0,
            start_time=start_time,
            end_time=end_time
        )
        
        # Neighborhood transformation (depends on locations)
        entity = ENTITY_TYPES.neighborhood
        transformer = NeighborhoodSilverTransformer(self.settings, self.connection_manager, self.embedding_provider)
        start_time = datetime.now()
        
        transformer.transform(entity.bronze_table, entity.silver_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.silver_table)
        
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
        transformer = WikipediaSilverTransformer(self.settings, self.connection_manager, self.embedding_provider)
        start_time = datetime.now()
        
        transformer.transform(entity.bronze_table, entity.silver_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.silver_table)
        
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
        
        # Location enrichment (MUST BE FIRST - properties and neighborhoods depend on it)
        entity = ENTITY_TYPES.location
        enricher = LocationGoldEnricher(
            self.settings, 
            self.connection_manager
        )
        start_time = datetime.now()
        
        enricher.enrich(entity.silver_table, entity.gold_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.gold_table)
        
        metrics[entity.name] = StageMetrics(
            stage_name="gold",
            input_records=count,
            output_records=count,
            dropped_records=0,
            start_time=start_time,
            end_time=end_time
        )
        
        # Property enrichment
        entity = ENTITY_TYPES.property
        enricher = PropertyGoldEnricher(
            self.settings, 
            self.connection_manager
        )
        start_time = datetime.now()
        
        enricher.enrich(entity.silver_table, entity.gold_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.gold_table)
        
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
        enricher = NeighborhoodGoldEnricher(
            self.settings, 
            self.connection_manager
        )
        start_time = datetime.now()
        
        enricher.enrich(entity.silver_table, entity.gold_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.gold_table)
        
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
        enricher = WikipediaGoldEnricher(
            self.settings, 
            self.connection_manager
        )
        start_time = datetime.now()
        
        enricher.enrich(entity.silver_table, entity.gold_table)
        
        end_time = datetime.now()
        
        count = self.connection_manager.count_records(entity.gold_table)
        
        metrics[entity.name] = StageMetrics(
            stage_name="gold",
            input_records=count,
            output_records=count,
            dropped_records=0,
            start_time=start_time,
            end_time=end_time
        )
        
        return metrics
    
    # Embeddings are now generated in Silver layer, no separate step needed
    
    @log_stage("Pipeline: Build Graph Tables")
    def run_graph_builder(self) -> None:
        """Build graph-specific tables for Neo4j export."""
        from squack_pipeline_v2.gold.graph_builder import GoldGraphBuilder
        
        graph_builder = GoldGraphBuilder(self.connection_manager)
        
        # Build all graph tables using the comprehensive method
        metadata = graph_builder.build_all_graph_tables()
        
        logger.info(
            f"Graph tables built successfully: "
            f"{len(metadata.node_tables)} node tables ({metadata.total_nodes} nodes), "
            f"{len(metadata.relationship_tables)} relationship tables ({metadata.total_relationships} relationships)"
        )
    
    @log_stage("Pipeline: Export Data")
    def run_writers(
        self,
        write_parquet: bool = True,
        write_elasticsearch: bool = False,
        write_neo4j: bool = False
    ) -> Dict[str, Any]:
        """Export data to Parquet, Elasticsearch, and/or Neo4j.
        
        Args:
            write_parquet: Export to Parquet files
            write_elasticsearch: Export to Elasticsearch
            write_neo4j: Export to Neo4j
            
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
        
        # Elasticsearch export
        if write_elasticsearch or self.settings.output.elasticsearch_enabled:
            writer = ElasticsearchWriter(
                self.connection_manager,
                self.settings
            )
            stats["elasticsearch"] = writer.index_all()
        
        # Neo4j export
        if write_neo4j or self.settings.output.neo4j.enabled:
            from squack_pipeline_v2.writers.neo4j import Neo4jWriter, Neo4jConfig
            
            neo4j_config = Neo4jConfig(
                uri=self.settings.output.neo4j.uri,
                username=self.settings.output.neo4j.username,
                password=self.settings.output.neo4j.get_password() or ""
            )
            
            writer = Neo4jWriter(neo4j_config, self.connection_manager)
            
            # Write all data using the comprehensive method
            write_metadata = writer.write_all()
            
            stats["neo4j"] = {
                "total_nodes": write_metadata.total_nodes,
                "total_relationships": write_metadata.total_relationships,
                "node_types": len(write_metadata.node_results),
                "relationship_types": len(write_metadata.relationship_results),
                "duration_seconds": write_metadata.total_duration_seconds
            }
            
            writer.close()
        
        return stats
    
    @log_stage("Pipeline: Full Run")
    def run_full_pipeline(
        self,
        sample_size: Optional[int] = None,
        write_parquet: bool = True,
        write_elasticsearch: bool = False,
        write_neo4j: bool = False
    ) -> PipelineMetrics:
        """Run the complete pipeline end-to-end for all entities.
        
        Args:
            sample_size: Optional sample size for testing
            write_parquet: Export to Parquet
            write_elasticsearch: Export to Elasticsearch
            write_neo4j: Export to Neo4j
            
        Returns:
            Complete pipeline metrics
        """
        pipeline_start = datetime.now()
        
        logger.info(f"Starting pipeline run: {self.pipeline_id}")
        
        try:
            # Bronze layer
            logger.info("Running Bronze layer...")
            bronze_metrics = self.run_bronze_layer(sample_size)
            bronze_total = sum(m.bronze_metrics.output_records for m in bronze_metrics.values())
            logger.info(f"Bronze complete: {bronze_total:,} total records ingested")
            
            # Silver layer
            logger.info("Running Silver layer...")
            silver_metrics = self.run_silver_layer()
            silver_total = sum(m.output_records for m in silver_metrics.values())
            logger.info(f"Silver complete: {silver_total:,} total records transformed")
            
            # Gold layer
            logger.info("Running Gold layer...")
            gold_metrics = self.run_gold_layer()
            gold_total = sum(m.output_records for m in gold_metrics.values())
            logger.info(f"Gold complete: {gold_total:,} total records enriched")
            
            # Graph builder - build graph tables for Neo4j
            if write_neo4j:
                logger.info("Building graph tables...")
                self.run_graph_builder()
                logger.info("Graph tables complete")
            
            # Update entity metrics
            for entity_type in bronze_metrics:
                if entity_type in silver_metrics:
                    bronze_metrics[entity_type] = EntityMetrics(
                        entity_type=entity_type,
                        bronze_metrics=bronze_metrics[entity_type].bronze_metrics,
                        silver_metrics=silver_metrics[entity_type],
                        gold_metrics=gold_metrics.get(entity_type)
                    )
            
            # Embeddings are now generated in Silver layer
            logger.info("Embeddings generated during Silver transformation")
            
            # Writers
            writer_stats = {}
            if write_parquet or write_elasticsearch or write_neo4j:
                logger.info("Exporting data...")
                writer_stats = self.run_writers(
                    write_parquet=write_parquet,
                    write_elasticsearch=write_elasticsearch,
                    write_neo4j=write_neo4j
                )
                if write_parquet and "parquet" in writer_stats:
                    logger.info(f"Parquet: {len(writer_stats['parquet'])} files written")
                if write_elasticsearch and "elasticsearch" in writer_stats:
                    total_indexed = sum(v.get("indexed", 0) for v in writer_stats.get("elasticsearch", {}).values() if isinstance(v, dict))
                    logger.info(f"Elasticsearch: {total_indexed:,} documents indexed")
                if write_neo4j and "neo4j" in writer_stats:
                    logger.info(f"Neo4j: {writer_stats['neo4j'].get('total_nodes', 0)} nodes, {writer_stats['neo4j'].get('total_relationships', 0)} relationships written")
            
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
                entity.gold_table
            ])
        
        stats = {}
        for table in tables:
            if self.connection_manager.table_exists(table):
                count = self.connection_manager.count_records(table)
                stats[table] = count
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        self.connection_manager.close()