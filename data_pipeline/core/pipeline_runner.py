"""
Main pipeline orchestration module.

This module provides the main runner that orchestrates the entire data pipeline
from data loading through enrichment to final output.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import avg, col, count, desc

from data_pipeline.config.settings import ConfigurationManager
from data_pipeline.core.spark_session import get_or_create_spark_session
from data_pipeline.loaders.data_loader_orchestrator import DataLoaderOrchestrator
# Entity-specific imports will be done where needed
# Entity-specific embedding generators used instead
# Import entity-specific processors and enrichers
from data_pipeline.processing.property_text_processor import PropertyTextProcessor, PropertyTextConfig
from data_pipeline.processing.neighborhood_text_processor import NeighborhoodTextProcessor, NeighborhoodTextConfig
from data_pipeline.processing.wikipedia_text_processor import WikipediaTextProcessor, WikipediaTextConfig
from data_pipeline.enrichment.property_enricher import PropertyEnricher, PropertyEnrichmentConfig
from data_pipeline.enrichment.neighborhood_enricher import NeighborhoodEnricher, NeighborhoodEnrichmentConfig
from data_pipeline.enrichment.wikipedia_enricher import WikipediaEnricher, WikipediaEnrichmentConfig
from data_pipeline.writers.orchestrator import WriterOrchestrator
from data_pipeline.writers.neo4j import Neo4jOrchestrator
from data_pipeline.writers.parquet_writer import ParquetWriter
from data_pipeline.writers.elasticsearch import (
    PropertyElasticsearchWriter,
    NeighborhoodElasticsearchWriter,
    WikipediaElasticsearchWriter
)

logger = logging.getLogger(__name__)


class DataPipelineRunner:
    """Main pipeline orchestrator."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize pipeline runner.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config_manager = ConfigurationManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Configure logging
        self._setup_logging()
        
        # Initialize Spark session
        self.spark = get_or_create_spark_session(self.config.spark)
        
        # Initialize components
        self.loader = DataLoaderOrchestrator(self.spark, self.config)
        
        # Initialize entity-specific processors and enrichers
        self._init_entity_processors()
        # Entity-specific embedding generators will be created as needed
        self.embedding_config = self._init_embedding_config()
        
        # Initialize writer orchestrator if configured
        self.writer_orchestrator = self._init_writer_orchestrator()
        
        # Track pipeline state
        self._pipeline_start_time: Optional[datetime] = None
        self._cached_dataframes: Optional[Dict[str, DataFrame]] = None
    
    def _setup_logging(self) -> None:
        """Configure logging based on pipeline configuration."""
        log_config = self.config.logging
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_config.level))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(log_config.format)
        
        # Add console handler if enabled
        if log_config.console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_config.file:
            file_path = Path(log_config.file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def _init_entity_processors(self):
        """Initialize entity-specific processors and enrichers."""
        # Property processors
        property_enrichment_config = PropertyEnrichmentConfig(
            enable_price_calculations=self.config.enrichment.add_derived_fields,
            enable_address_normalization=self.config.enrichment.normalize_features,
            enable_quality_scoring=self.config.processing.enable_quality_checks,
            enable_correlation_ids=True,
            min_quality_score=self.config.enrichment.quality_threshold,
            city_abbreviations=self.config.enrichment.city_abbreviations,
            state_abbreviations=self.config.enrichment.state_abbreviations
        )
        self.property_enricher = PropertyEnricher(self.spark, property_enrichment_config)
        self.property_text_processor = PropertyTextProcessor(self.spark)
        
        # Neighborhood processors
        neighborhood_enrichment_config = NeighborhoodEnrichmentConfig(
            enable_location_normalization=self.config.enrichment.normalize_features,
            enable_demographic_validation=True,
            enable_boundary_processing=False,  # Disabled - no boundary data in source files
            enable_quality_scoring=self.config.processing.enable_quality_checks,
            enable_correlation_ids=True,
            min_quality_score=self.config.enrichment.quality_threshold,
            city_mappings=self.config.enrichment.city_abbreviations,
            state_mappings=self.config.enrichment.state_abbreviations
        )
        self.neighborhood_enricher = NeighborhoodEnricher(self.spark, neighborhood_enrichment_config)
        self.neighborhood_text_processor = NeighborhoodTextProcessor(self.spark)
        
        # Wikipedia processors
        wikipedia_enrichment_config = WikipediaEnrichmentConfig(
            enable_location_extraction=True,
            enable_relevance_scoring=True,
            enable_confidence_metrics=True,
            enable_quality_scoring=self.config.processing.enable_quality_checks,
            enable_correlation_ids=True,
            min_quality_score=0.5,
            min_confidence_threshold=0.6
        )
        self.wikipedia_enricher = WikipediaEnricher(self.spark, wikipedia_enrichment_config)
        self.wikipedia_text_processor = WikipediaTextProcessor(self.spark)
    
    def _init_embedding_config(self):
        """Initialize embedding configuration for entity-specific generators."""
        from data_pipeline.config.models import ProviderType
        
        # Return the embedding config from settings directly
        return self.config.embedding
    
    def _init_writer_orchestrator(self) -> Optional[WriterOrchestrator]:
        """Initialize the writer orchestrator with configured destinations."""
        writers = []
        
        # Check if output_destinations is configured
        if hasattr(self.config, 'output_destinations'):
            dest_config = self.config.output_destinations
            
            # Add Parquet writer if enabled
            if "parquet" in dest_config.enabled_destinations and dest_config.parquet.enabled:
                logger.info("Initializing Parquet writer from output_destinations")
                writers.append(ParquetWriter(dest_config.parquet, self.spark))
            
            # Add Neo4j graph writer if enabled
            if "neo4j" in dest_config.enabled_destinations and dest_config.neo4j.enabled:
                logger.info("Initializing Neo4j graph writer")
                writers.append(Neo4jOrchestrator(dest_config.neo4j, self.spark))
            
            # Add entity-specific Elasticsearch writers if enabled
            if "elasticsearch" in dest_config.enabled_destinations and dest_config.elasticsearch.enabled:
                logger.info("Initializing entity-specific Elasticsearch writers")
                writers.append(PropertyElasticsearchWriter(dest_config.elasticsearch, self.spark))
                writers.append(NeighborhoodElasticsearchWriter(dest_config.elasticsearch, self.spark))
                writers.append(WikipediaElasticsearchWriter(dest_config.elasticsearch, self.spark))
        
        
        if writers:
            logger.info(f"Initialized {len(writers)} writer(s): {[w.get_writer_name() for w in writers]}")
            return WriterOrchestrator(writers)
        
        logger.info("No writers configured")
        return None
    
    def run_full_pipeline(self) -> Dict[str, DataFrame]:
        """
        Execute the complete data pipeline WITHOUT embeddings.
        Use run_full_pipeline_with_embeddings() for the complete pipeline.
        
        Returns:
            Dictionary of processed DataFrames by entity type
        """
        self._pipeline_start_time = datetime.now()
        
        logger.info("="*60)
        logger.info(f"🚀 Starting {self.config.metadata.name} v{self.config.metadata.version}")
        logger.info("="*60)
        
        try:
            # Step 1: Load all data sources as separate DataFrames
            logger.info("📥 Loading data from all sources...")
            entity_dataframes = self.loader.load_all_sources()
            
            # Log loading summary
            total_records = 0
            for entity_type, df in entity_dataframes.items():
                if df is not None:
                    count = df.count()
                    total_records += count
                    logger.info(f"   Loaded {count:,} {entity_type} records")
            
            if total_records == 0:
                logger.warning("No data loaded. Pipeline terminating.")
                return entity_dataframes
            
            logger.info(f"   Total: {total_records:,} records across all entities")
            
            # Process each entity type separately
            processed_entities = {}
            
            # Process properties
            if entity_dataframes.get('properties') is not None:
                logger.info("\n🏠 Processing properties...")
                processed_entities['properties'] = self._process_properties(
                    entity_dataframes['properties']
                )
            
            # Process neighborhoods
            if entity_dataframes.get('neighborhoods') is not None:
                logger.info("\n🏘️ Processing neighborhoods...")
                processed_entities['neighborhoods'] = self._process_neighborhoods(
                    entity_dataframes['neighborhoods']
                )
            
            # Process Wikipedia articles
            if entity_dataframes.get('wikipedia') is not None:
                logger.info("\n📚 Processing Wikipedia articles...")
                processed_entities['wikipedia'] = self._process_wikipedia(
                    entity_dataframes['wikipedia']
                )
            
            # Store cached references
            self._cached_dataframes = processed_entities
            
            # Generate summary statistics
            self._print_entity_pipeline_summary(processed_entities)
            
            # Calculate and log execution time
            execution_time = (datetime.now() - self._pipeline_start_time).total_seconds()
            logger.info(f"⏱️  Pipeline completed in {execution_time:.2f} seconds")
            logger.info("🎉 Pipeline execution successful!")
            
            return processed_entities
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _process_properties(self, df: DataFrame) -> DataFrame:
        """
        Process property data through enrichment and text processing.
        
        Args:
            df: Property DataFrame
            
        Returns:
            Processed property DataFrame
        """
        # Apply property-specific enrichment
        enriched_df = self.property_enricher.enrich(df)
        
        # Process text for properties
        processed_df = self.property_text_processor.process(enriched_df)
        
        # Cache if configured
        if self.config.processing.cache_intermediate_results:
            processed_df = processed_df.cache()
        
        return processed_df
    
    def _process_neighborhoods(self, df: DataFrame) -> DataFrame:
        """
        Process neighborhood data through enrichment and text processing.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            Processed neighborhood DataFrame
        """
        # Apply neighborhood-specific enrichment
        enriched_df = self.neighborhood_enricher.enrich(df)
        
        # Process text for neighborhoods
        processed_df = self.neighborhood_text_processor.process(enriched_df)
        
        # Cache if configured
        if self.config.processing.cache_intermediate_results:
            processed_df = processed_df.cache()
        
        return processed_df
    
    def _process_wikipedia(self, df: DataFrame) -> DataFrame:
        """
        Process Wikipedia data through enrichment and text processing.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            Processed Wikipedia DataFrame
        """
        # Apply Wikipedia-specific enrichment
        enriched_df = self.wikipedia_enricher.enrich(df)
        
        # Process text for Wikipedia (minimal processing as content is already optimized)
        processed_df = self.wikipedia_text_processor.process(enriched_df)
        
        # Cache if configured
        if self.config.processing.cache_intermediate_results:
            processed_df = processed_df.cache()
        
        return processed_df
    
    def run_full_pipeline_with_embeddings(self) -> Dict[str, DataFrame]:
        """
        Execute the complete pipeline including embedding generation.
        
        This follows the entity-specific approach:
        load → process each entity → add embeddings → output
        
        Each entity type is processed independently with its own logic.
        
        Returns:
            Dictionary of final DataFrames with embeddings by entity type
        """
        self._pipeline_start_time = datetime.now()
        
        logger.info("="*60)
        logger.info(f"🚀 Starting {self.config.metadata.name} v{self.config.metadata.version} with Embeddings")
        logger.info("="*60)
        
        try:
            # Step 1: Load all data sources as separate DataFrames
            logger.info("📥 Loading data from all sources...")
            entity_dataframes = self.loader.load_all_sources()
            
            # Log loading summary
            total_records = 0
            for entity_type, df in entity_dataframes.items():
                if df is not None:
                    count = df.count()
                    total_records += count
                    logger.info(f"   Loaded {count:,} {entity_type} records")
            
            if total_records == 0:
                logger.warning("No data loaded. Pipeline terminating.")
                return entity_dataframes
            
            logger.info(f"   Total: {total_records:,} records across all entities")
            
            # Process each entity type separately WITH embeddings
            processed_entities = {}
            
            # Import entity-specific embedding generators
            from data_pipeline.processing.entity_embeddings import (
                PropertyEmbeddingGenerator,
                NeighborhoodEmbeddingGenerator, 
                WikipediaEmbeddingGenerator
            )
            
            # Process properties with embeddings
            if entity_dataframes.get('properties') is not None:
                logger.info("\n🏠 Processing properties with embeddings...")
                processed_df = self._process_properties(entity_dataframes['properties'])
                
                # Generate property-specific embeddings
                logger.info("   🔮 Generating property embeddings...")
                property_embedder = PropertyEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['properties'] = property_embedder.generate_embeddings(processed_df)
            
            # Process neighborhoods with embeddings
            if entity_dataframes.get('neighborhoods') is not None:
                logger.info("\n🏘️ Processing neighborhoods with embeddings...")
                processed_df = self._process_neighborhoods(entity_dataframes['neighborhoods'])
                
                # Generate neighborhood-specific embeddings
                logger.info("   🔮 Generating neighborhood embeddings...")
                neighborhood_embedder = NeighborhoodEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['neighborhoods'] = neighborhood_embedder.generate_embeddings(processed_df)
            
            # Process Wikipedia articles with embeddings
            if entity_dataframes.get('wikipedia') is not None:
                logger.info("\n📚 Processing Wikipedia articles with embeddings...")
                processed_df = self._process_wikipedia(entity_dataframes['wikipedia'])
                
                # Generate Wikipedia-specific embeddings
                logger.info("   🔮 Generating Wikipedia embeddings...")
                wikipedia_embedder = WikipediaEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['wikipedia'] = wikipedia_embedder.generate_embeddings(processed_df)
            
            # Store cached references
            self._cached_dataframes = processed_entities
            
            # Generate summary statistics
            self._print_entity_pipeline_summary(processed_entities)
            
            # Calculate and log execution time
            execution_time = (datetime.now() - self._pipeline_start_time).total_seconds()
            logger.info(f"⏱️  Pipeline completed in {execution_time:.2f} seconds")
            logger.info("✨ Pipeline with embeddings completed successfully!")
            
            return processed_entities
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _print_entity_pipeline_summary(self, entity_dataframes: Dict[str, DataFrame]) -> None:
        """
        Print comprehensive pipeline statistics for entity-specific DataFrames.
        
        Args:
            entity_dataframes: Dictionary of entity type to DataFrame
        """
        logger.info("")
        logger.info("="*60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("="*60)
        
        # Total records across all entities
        total_records = sum(
            df.count() for df in entity_dataframes.values() if df is not None
        )
        logger.info(f"📈 Total Records: {total_records:,}")
        
        # Entity type breakdown
        logger.info("")
        logger.info("🏢 Entity Type Breakdown:")
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                count = df.count()
                logger.info(f"   {entity_type}: {count:,} records")
        
        # Process each entity separately for statistics
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                logger.info("")
                logger.info(f"📊 {entity_type.upper()} Statistics:")
                
                entity_count = df.count()
                
                # Location breakdown for this entity
                if "state" in df.columns:
                    location_counts = df.filter(col("state").isNotNull()) \
                                       .groupBy("state").count() \
                                       .orderBy(desc("count")) \
                                       .limit(3).collect()
                    if location_counts:
                        logger.info(f"   Top States:")
                        for row in location_counts:
                            logger.info(f"      {row['state']}: {row['count']:,} records")
                
                # Data quality indicators
                if "city" in df.columns:
                    with_city = df.filter(col("city").isNotNull()).count()
                    logger.info(f"   With city data: {with_city:,} ({100*with_city/entity_count:.1f}%)")
                
                if "city_normalized" in df.columns:
                    with_normalized = df.filter(col("city_normalized").isNotNull()).count()
                    logger.info(f"   With normalized city: {with_normalized:,} ({100*with_normalized/entity_count:.1f}%)")
                
                if "data_quality_score" in df.columns:
                    with_quality = df.filter(col("data_quality_score").isNotNull()).count()
                    logger.info(f"   With quality score: {with_quality:,} ({100*with_quality/entity_count:.1f}%)")
                
                if "embedding_text" in df.columns:
                    with_text = df.filter(col("embedding_text").isNotNull()).count()
                    logger.info(f"   With embedding text: {with_text:,} ({100*with_text/entity_count:.1f}%)")
                
                if "embeddings" in df.columns:
                    with_embeddings = df.filter(col("embeddings").isNotNull()).count()
                    logger.info(f"   With embeddings: {with_embeddings:,} ({100*with_embeddings/entity_count:.1f}%)")
                
                # DataFrame info
                logger.info(f"   Partitions: {df.rdd.getNumPartitions()}")
                logger.info(f"   Columns: {len(df.columns)}")
        
        logger.info("="*60)
    
    
    def get_cached_dataframes(self) -> Optional[Dict[str, DataFrame]]:
        """
        Get the cached DataFrames from the last pipeline run.
        
        Returns:
            Dictionary of cached DataFrames by entity type or None
        """
        return self._cached_dataframes
    
    
    def write_output(self, df: Optional[DataFrame] = None) -> None:
        """
        Write single DataFrame to all configured output destinations.
        
        For entity-specific writing, use write_entity_outputs instead.
        
        Args:
            df: DataFrame to write
        """
        if df is None:
            logger.error("No DataFrame provided to write.")
            return
        
        # Prepare metadata for writers
        metadata = {
            "pipeline_name": self.config.metadata.name,
            "pipeline_version": self.config.metadata.version,
            "timestamp": datetime.now().isoformat(),
            "record_count": df.count(),
            "environment": self.config_manager.environment
        }
        
        if self.writer_orchestrator:
            # Use multi-destination writer
            logger.info("="*60)
            logger.info("📤 Writing to configured destinations...")
            logger.info("="*60)
            
            # Validate connections first
            logger.info("Validating destination connections...")
            self.writer_orchestrator.validate_all_connections()
            
            # Write to all destinations
            self.writer_orchestrator.write_to_all(df, metadata)
            
            logger.info("="*60)
    
    def write_entity_outputs(self, entity_dataframes: Optional[Dict[str, DataFrame]] = None) -> None:
        """
        Write entity-specific DataFrames to all configured output destinations.
        
        Args:
            entity_dataframes: Dictionary of entity type to DataFrame. If None, uses cached DataFrames.
        """
        output_dataframes = entity_dataframes or self._cached_dataframes
        
        if output_dataframes is None or not output_dataframes:
            logger.error("No data to write. Run pipeline first.")
            return
        
        # Calculate total record count
        total_records = sum(df.count() for df in output_dataframes.values() if df is not None)
        
        # Prepare metadata for writers
        metadata = {
            "pipeline_name": self.config.metadata.name,
            "pipeline_version": self.config.metadata.version,
            "timestamp": datetime.now().isoformat(),
            "total_record_count": total_records,
            "entity_types": list(output_dataframes.keys()),
            "environment": self.config_manager.environment
        }
        
        if self.writer_orchestrator:
            # Use multi-destination writer
            logger.info("="*60)
            logger.info("📤 Writing entity DataFrames to configured destinations...")
            logger.info("="*60)
            
            # Validate connections first
            logger.info("Validating destination connections...")
            self.writer_orchestrator.validate_all_connections()
            
            # Write all entity DataFrames to destinations
            self.writer_orchestrator.write_entity_dataframes(output_dataframes, metadata)
            
            logger.info("="*60)
            logger.info("✅ Successfully wrote to all destinations")
            logger.info("="*60)
        else:
            # Use direct Parquet output when no orchestrator configured
            output_config = self.config.output
            path = output_config.path
            
            logger.info(f"💾 Writing results to {path} as {output_config.format}")
            
            writer = output_df.write.mode("overwrite" if output_config.overwrite else "append")
            
            # Apply partitioning if specified
            if output_config.partitioning and output_config.partitioning.enabled:
                if output_config.partitioning.columns:
                    writer = writer.partitionBy(*output_config.partitioning.columns)
            
            # Write based on format
            if output_config.format == "parquet":
                writer.option("compression", output_config.compression).parquet(path)
            elif output_config.format == "json":
                writer.json(path)
            elif output_config.format == "csv":
                writer.option("header", "true").csv(path)
            else:
                logger.error(f"Unsupported output format: {output_config.format}")
                return
            
            logger.info(f"✅ Results written successfully to {path}")
    
    def validate_pipeline(self) -> Dict[str, Any]:
        """
        Validate pipeline configuration and environment.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "configuration": {},
            "environment": {},
            "data_sources": {}
        }
        
        # Validate configuration
        validation_results["configuration"]["is_valid"] = True
        validation_results["configuration"]["production_ready"] = \
            self.config_manager.validate_for_production()
        
        # Validate Spark environment
        spark_conf = self.spark.sparkContext.getConf()
        validation_results["environment"]["spark_version"] = \
            self.spark.sparkContext.version
        validation_results["environment"]["spark_master"] = \
            spark_conf.get("spark.master")
        validation_results["environment"]["available_cores"] = \
            self.spark.sparkContext.defaultParallelism
        
        # Validate data sources
        for source_name, source_config in self.config.data_sources.items():
            source_valid = Path(source_config.path).exists() if source_config.enabled else True
            validation_results["data_sources"][source_name] = {
                "enabled": source_config.enabled,
                "exists": source_valid
            }
        
        return validation_results
    
    def stop(self) -> None:
        """Stop the pipeline and clean up resources."""
        logger.info("Stopping pipeline and cleaning up resources...")
        
        # Unpersist cached DataFrames
        if self._cached_dataframes is not None:
            try:
                for df in self._cached_dataframes.values():
                    if df is not None:
                        df.unpersist()
            except Exception as e:
                logger.warning(f"Error unpersisting DataFrames: {e}")
        
        # Stop Spark session
        if self.spark is not None:
            self.spark.stop()
        
        logger.info("Pipeline stopped successfully")