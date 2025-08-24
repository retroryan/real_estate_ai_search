"""
Main pipeline orchestration module.

This module provides the main runner that orchestrates the entire data pipeline
from data loading through enrichment to final output.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import avg, col, count, desc

from data_pipeline.config.settings import ConfigurationManager
from data_pipeline.core.spark_session import get_or_create_spark_session
from data_pipeline.loaders.data_loader_orchestrator import DataLoaderOrchestrator
from data_pipeline.processing.embedding_generator import (
    DistributedEmbeddingGenerator,
    EmbeddingGeneratorConfig,
    EmbeddingProvider,
    ProviderConfig,
)
from data_pipeline.processing.enrichment_engine import DataEnrichmentEngine, EnrichmentConfig, LocationMapping
from data_pipeline.processing.text_processor import ChunkingConfig, TextProcessor, TextProcessingConfig

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
        
        # Initialize enrichment and text processing
        self.enrichment_engine = self._init_enrichment_engine()
        self.text_processor = self._init_text_processor()
        self.embedding_generator = self._init_embedding_generator()
        
        # Track pipeline state
        self._pipeline_start_time: Optional[datetime] = None
        self._cached_dataframe: Optional[DataFrame] = None
    
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
    
    def _init_enrichment_engine(self) -> DataEnrichmentEngine:
        """Initialize the data enrichment engine."""
        # Build location mappings from config
        location_mappings = LocationMapping(
            city_abbreviations=self.config.enrichment.city_abbreviations,
            state_abbreviations=self.config.enrichment.state_abbreviations
        )
        
        enrichment_config = EnrichmentConfig(
            enable_location_normalization=self.config.enrichment.normalize_features,
            enable_derived_fields=self.config.enrichment.add_derived_fields,
            enable_correlation_ids=True,
            enable_quality_scoring=self.config.processing.enable_quality_checks,
            min_quality_score=self.config.enrichment.quality_threshold,
            location_mappings=location_mappings
        )
        return DataEnrichmentEngine(self.spark, enrichment_config)
    
    def _init_text_processor(self) -> TextProcessor:
        """Initialize the text processor."""
        # Build chunking config from settings
        chunking_config = ChunkingConfig(
            method=self.config.chunking.method,
            chunk_size=self.config.chunking.chunk_size,
            chunk_overlap=self.config.chunking.chunk_overlap
        )
        
        text_config = TextProcessingConfig(
            enable_cleaning=True,
            enable_chunking=True,
            chunking_config=chunking_config
        )
        return TextProcessor(self.spark, text_config)
    
    def _init_embedding_generator(self) -> DistributedEmbeddingGenerator:
        """Initialize the embedding generator."""
        from data_pipeline.processing.embedding_generator import (
            ChunkingMethod,
            ChunkingConfig as EmbedChunkingConfig
        )
        
        # Build provider config from settings
        provider = EmbeddingProvider(self.config.embedding.provider)
        
        # Create base config dict
        config_dict = {
            "provider": provider,
            "batch_size": getattr(self.config.embedding, "batch_size", 100),
            "max_retries": getattr(self.config.embedding, "max_retries", 3),
            "timeout": getattr(self.config.embedding, "timeout", 30)
        }
        
        # Add provider-specific settings
        if provider == EmbeddingProvider.OLLAMA:
            config_dict["ollama_model"] = getattr(self.config.embedding, "model", "nomic-embed-text")
            config_dict["ollama_base_url"] = getattr(self.config.embedding, "api_url", "http://localhost:11434")
        elif provider == EmbeddingProvider.OPENAI:
            config_dict["openai_model"] = getattr(self.config.embedding, "model", "text-embedding-3-small")
        elif provider == EmbeddingProvider.VOYAGE:
            config_dict["voyage_model"] = getattr(self.config.embedding, "model", "voyage-3")
            config_dict["embedding_dimension"] = 1024  # voyage-3 dimension
        elif provider == EmbeddingProvider.GEMINI:
            config_dict["gemini_model"] = getattr(self.config.embedding, "model", "models/embedding-001")
        
        provider_config = ProviderConfig(**config_dict)
        
        # Build chunking config - enable chunking for embeddings
        embed_chunking_config = EmbedChunkingConfig(
            method=ChunkingMethod(self.config.chunking.method),
            chunk_size=self.config.chunking.chunk_size,
            chunk_overlap=self.config.chunking.chunk_overlap,
            enable_chunking=True  # Enable chunking for better embedding coverage
        )
        
        embedding_config = EmbeddingGeneratorConfig(
            provider_config=provider_config,
            chunking_config=embed_chunking_config,
            process_empty_text=False,
            skip_existing_embeddings=False  # Always generate fresh embeddings
        )
        
        return DistributedEmbeddingGenerator(self.spark, embedding_config)
    
    def run_full_pipeline(self) -> DataFrame:
        """
        Execute the complete data pipeline WITHOUT embeddings.
        Use run_full_pipeline_with_embeddings() for the complete pipeline.
        
        Returns:
            Processed DataFrame without embeddings
        """
        self._pipeline_start_time = datetime.now()
        
        logger.info("="*60)
        logger.info(f"🚀 Starting {self.config.name} v{self.config.version}")
        logger.info("="*60)
        
        try:
            # Step 1: Load all data sources
            logger.info("📥 Loading data from all sources...")
            raw_df = self.loader.load_all_sources()
            raw_count = raw_df.count()
            logger.info(f"   Loaded {raw_count:,} records from all sources")
            
            if raw_count == 0:
                logger.warning("No data loaded. Pipeline terminating.")
                return raw_df
            
            # Cache if configured
            if self.config.processing.cache_intermediate_results:
                logger.info("⚡ Caching loaded data...")
                raw_df = raw_df.cache()
            
            # Step 2: Apply data enrichment
            logger.info("🔧 Enriching data...")
            enriched_df = self.enrichment_engine.enrich(raw_df)
            enrichment_stats = self.enrichment_engine.get_enrichment_statistics(enriched_df)
            logger.info(f"   ✓ Enriched {enrichment_stats['total_records']:,} records")
            logger.info(f"   ✓ Average quality score: {enrichment_stats.get('avg_quality_score', 0):.2f}")
            logger.info(f"   ✓ Validated records: {enrichment_stats.get('validated_records', 0):,}")
            
            # Step 3: Process text for embeddings
            logger.info("📝 Processing text content...")
            processed_df = self.text_processor.process(enriched_df)
            text_stats = self.text_processor.get_text_statistics(processed_df)
            logger.info(f"   ✓ Prepared embedding text for {text_stats['records_with_embedding_text']:,} records")
            logger.info(f"   ✓ Average text length: {text_stats.get('avg_text_length', 0):.0f} characters")
            
            # Cache if configured
            if self.config.processing.cache_intermediate_results:
                logger.info("⚡ Caching processed data...")
                processed_df = processed_df.cache()
            
            final_df = processed_df
            
            # Store cached reference
            self._cached_dataframe = final_df
            
            # Generate summary statistics
            self._print_pipeline_summary(final_df)
            
            # Calculate and log execution time
            execution_time = (datetime.now() - self._pipeline_start_time).total_seconds()
            logger.info(f"⏱️  Pipeline completed in {execution_time:.2f} seconds")
            logger.info("🎉 Pipeline execution successful!")
            
            return final_df
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def run_full_pipeline_with_embeddings(self) -> DataFrame:
        """
        Execute the complete pipeline including embedding generation.
        
        This follows the simplified approach:
        load → enrich → process text → embed → output in clean sequence
        
        Embeddings are added directly as DataFrame columns using withColumn()
        No correlation complexity, just simple DataFrame operations.
        
        Returns:
            Final DataFrame with all data and embeddings
        """
        self._pipeline_start_time = datetime.now()
        
        logger.info("="*60)
        logger.info(f"🚀 Starting {self.config.name} v{self.config.version} with Embeddings")
        logger.info("="*60)
        
        try:
            # Step 1: Load all data sources
            logger.info("📥 Loading data from all sources...")
            raw_df = self.loader.load_all_sources()
            raw_count = raw_df.count()
            logger.info(f"   Loaded {raw_count:,} records from all sources")
            
            if raw_count == 0:
                logger.warning("No data loaded. Pipeline terminating.")
                return raw_df
            
            # Cache if configured
            if self.config.processing.cache_intermediate_results:
                logger.info("⚡ Caching loaded data...")
                raw_df = raw_df.cache()
            
            # Step 2: Apply data enrichment
            logger.info("🔧 Enriching data...")
            enriched_df = self.enrichment_engine.enrich(raw_df)
            enrichment_stats = self.enrichment_engine.get_enrichment_statistics(enriched_df)
            logger.info(f"   ✓ Enriched {enrichment_stats['total_records']:,} records")
            logger.info(f"   ✓ Average quality score: {enrichment_stats.get('avg_quality_score', 0):.2f}")
            logger.info(f"   ✓ Validated records: {enrichment_stats.get('validated_records', 0):,}")
            
            # Step 3: Process text for embeddings
            logger.info("📝 Processing text content...")
            processed_df = self.text_processor.process(enriched_df)
            text_stats = self.text_processor.get_text_statistics(processed_df)
            logger.info(f"   ✓ Prepared embedding text for {text_stats['records_with_embedding_text']:,} records")
            logger.info(f"   ✓ Average text length: {text_stats.get('avg_text_length', 0):.0f} characters")
            
            # Cache if configured
            if self.config.processing.cache_intermediate_results:
                logger.info("⚡ Caching processed data...")
                processed_df = processed_df.cache()
            
            # Step 4: Add embeddings directly to DataFrame (simplified approach)
            logger.info("🔮 Generating embeddings...")
            logger.info(f"   Provider: {self.config.embedding.provider}")
            logger.info(f"   Chunking: {self.config.chunking.method} (size={self.config.chunking.chunk_size})")
            
            # Simple, direct DataFrame enrichment - no correlation needed!
            final_df = self.embedding_generator.add_embeddings_to_dataframe(processed_df)
            
            # Get embedding statistics
            embedding_stats = self.embedding_generator.get_statistics(final_df)
            logger.info(f"   ✓ Generated embeddings for {embedding_stats.get('records_with_embeddings', 0):,} records")
            logger.info(f"   ✓ Embedding model: {self.embedding_generator.model_identifier}")
            
            # Store cached reference
            self._cached_dataframe = final_df
            
            # Generate summary statistics
            self._print_pipeline_summary(final_df)
            
            # Calculate and log execution time
            execution_time = (datetime.now() - self._pipeline_start_time).total_seconds()
            logger.info(f"⏱️  Pipeline completed in {execution_time:.2f} seconds")
            logger.info("✨ Pipeline with embeddings completed successfully!")
            
            return final_df
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _print_pipeline_summary(self, df: DataFrame) -> None:
        """
        Print comprehensive pipeline statistics.
        
        Args:
            df: Final DataFrame to summarize
        """
        logger.info("")
        logger.info("="*60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("="*60)
        
        # Total records
        total_records = df.count()
        logger.info(f"📈 Total Records: {total_records:,}")
        
        # Entity type breakdown
        logger.info("")
        logger.info("🏢 Entity Type Breakdown:")
        entity_counts = df.groupBy("entity_type").count().collect()
        for row in entity_counts:
            logger.info(f"   {row['entity_type']}: {row['count']:,} records")
        
        # Location breakdown
        logger.info("")
        logger.info("📍 Top States by Record Count:")
        location_counts = df.filter(col("state").isNotNull()) \
                           .groupBy("state").count() \
                           .orderBy(desc("count")) \
                           .limit(5).collect()
        for row in location_counts:
            logger.info(f"   {row['state']}: {row['count']:,} records")
        
        # Data quality indicators
        logger.info("")
        logger.info("✅ Data Quality Indicators:")
        
        # Count null entity IDs
        null_ids = df.filter(col("entity_id").isNull()).count()
        logger.info(f"   Records with null entity_id: {null_ids}")
        
        # Count records with cities
        with_city = df.filter(col("city").isNotNull()).count()
        logger.info(f"   Records with city data: {with_city:,} ({100*with_city/total_records:.1f}%)")
        
        # Count records with states
        with_state = df.filter(col("state").isNotNull()).count()
        logger.info(f"   Records with state data: {with_state:,} ({100*with_state/total_records:.1f}%)")
        
        # Count enriched fields (only if they exist in the DataFrame)
        if "city_normalized" in df.columns:
            with_normalized_city = df.filter(col("city_normalized").isNotNull()).count()
            logger.info(f"   Records with normalized city: {with_normalized_city:,} ({100*with_normalized_city/total_records:.1f}%)")
        
        if "data_quality_score" in df.columns:
            with_quality_score = df.filter(col("data_quality_score").isNotNull()).count()
            logger.info(f"   Records with quality score: {with_quality_score:,} ({100*with_quality_score/total_records:.1f}%)")
        
        if "embedding_text" in df.columns:
            with_embedding_text = df.filter(col("embedding_text").isNotNull()).count()
            logger.info(f"   Records with embedding text: {with_embedding_text:,} ({100*with_embedding_text/total_records:.1f}%)")
        
        # Memory and partitioning info
        logger.info("")
        logger.info("💾 DataFrame Information:")
        logger.info(f"   Number of partitions: {df.rdd.getNumPartitions()}")
        logger.info(f"   Columns: {len(df.columns)}")
        
        logger.info("="*60)
    
    def get_cached_dataframe(self) -> Optional[DataFrame]:
        """
        Get the cached DataFrame from the last pipeline run.
        
        Returns:
            Cached DataFrame or None if no pipeline has been run
        """
        return self._cached_dataframe
    
    def save_results(self, output_path: Optional[str] = None) -> None:
        """
        Save pipeline results to specified format.
        
        Args:
            output_path: Optional output path override
        """
        if self._cached_dataframe is None:
            logger.error("No results to save. Run pipeline first.")
            return
        
        output_config = self.config.output
        path = output_path or output_config.path
        
        logger.info(f"💾 Saving results to {path} as {output_config.format}")
        
        # Prepare writer
        writer = self._cached_dataframe.write
        
        if output_config.overwrite:
            writer = writer.mode("overwrite")
        else:
            writer = writer.mode("append")
        
        # Apply partitioning if specified
        if output_config.partitioning:
            writer = writer.partitionBy(*output_config.partitioning)
        
        # Save based on format
        if output_config.format == "parquet":
            writer.option("compression", output_config.compression).parquet(path)
        elif output_config.format == "json":
            writer.json(path)
        elif output_config.format == "csv":
            writer.option("header", "true").csv(path)
        else:
            logger.error(f"Unsupported output format: {output_config.format}")
            return
        
        logger.info(f"✅ Results saved successfully to {path}")
    
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
        if self._cached_dataframe is not None:
            try:
                self._cached_dataframe.unpersist()
            except Exception as e:
                logger.warning(f"Error unpersisting DataFrame: {e}")
        
        # Stop Spark session
        if self.spark is not None:
            self.spark.stop()
        
        logger.info("Pipeline stopped successfully")