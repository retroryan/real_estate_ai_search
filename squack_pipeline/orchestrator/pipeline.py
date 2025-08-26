"""Main pipeline orchestrator for SQUACK pipeline."""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.processors.silver_processor import SilverProcessor
from squack_pipeline.processors.gold_processor import GoldProcessor
from squack_pipeline.processors.geographic_enrichment import GeographicEnrichmentProcessor
from squack_pipeline.embeddings.pipeline import EmbeddingPipeline
from squack_pipeline.writers.parquet_writer import ParquetWriter
from squack_pipeline.writers.embedding_writer import EmbeddingWriter
from squack_pipeline.orchestrator.state_manager import PipelineStateManager, PipelineState
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time, log_data_quality


class PipelineOrchestrator:
    """Main orchestrator for the SQUACK data pipeline."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the pipeline orchestrator."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection_manager = DuckDBConnectionManager()
        self.start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {
            "records_processed": 0,
            "records_failed": 0,
            "tables_created": 0,
            "processing_time": 0.0,
            "bronze_records": 0,
            "silver_records": 0,
            "gold_records": 0,
            "enrichment_completeness": 0.0,
            "documents_converted": 0,
            "embeddings_generated": 0,
            "embedding_success_rate": 0.0
        }
        
        # Initialize processors
        self.silver_processor: Optional[SilverProcessor] = None
        self.gold_processor: Optional[GoldProcessor] = None
        self.geo_enrichment: Optional[GeographicEnrichmentProcessor] = None
        self.embedding_pipeline: Optional[EmbeddingPipeline] = None
        
        # Initialize writers
        self.parquet_writer: Optional[ParquetWriter] = None
        self.embedding_writer: Optional[EmbeddingWriter] = None
        
        # Track embedded nodes for output
        self.embedded_nodes: Optional[list] = None
        
        # Initialize state manager
        self.state_manager = PipelineStateManager(settings)
    
    @log_execution_time
    def run(self) -> None:
        """Execute the complete pipeline."""
        self.start_time = time.time()
        self.logger.info("Starting SQUACK pipeline execution")
        
        try:
            # Initialize components
            self._initialize_pipeline()
            
            # Phase 1: Load raw data (Bronze tier)
            self.state_manager.update_state(PipelineState.LOADING_BRONZE, "Loading raw data")
            self._load_raw_data()
            
            # Phase 2: Process to Silver tier (data cleaning)
            self.state_manager.update_state(PipelineState.PROCESSING_SILVER, "Processing Silver tier")
            self._process_silver_tier()
            
            # Phase 3: Process to Gold tier (data enrichment)
            self.state_manager.update_state(PipelineState.PROCESSING_GOLD, "Processing Gold tier")
            self._process_gold_tier()
            
            # Phase 4: Geographic enrichment (optional)
            self.state_manager.update_state(PipelineState.ENRICHING_GEOGRAPHIC, "Applying geographic enrichment")
            self._apply_geographic_enrichment()
            
            # Phase 5: Embedding generation (optional)
            if self.settings.processing.generate_embeddings:
                self.state_manager.update_state(PipelineState.GENERATING_EMBEDDINGS, "Generating embeddings")
            self._generate_embeddings()
            
            # Phase 6: Write output to Parquet files
            if not self.settings.dry_run:
                self.state_manager.update_state(PipelineState.WRITING_OUTPUT, "Writing output files")
            self._write_output()
            
            # Log completion
            self._finalize_pipeline()
            self.state_manager.mark_completed()
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self.state_manager.mark_failed(str(e), self.state_manager.current_state.current_phase)
            raise
    
    def _initialize_pipeline(self) -> None:
        """Initialize pipeline components."""
        self.logger.info("Initializing pipeline components")
        
        # Initialize DuckDB connection
        self.connection_manager.initialize(self.settings)
        self.logger.info("DuckDB connection established")
        
        # Initialize processors
        connection = self.connection_manager.get_connection()
        self.silver_processor = SilverProcessor(self.settings)
        self.silver_processor.set_connection(connection)
        
        self.gold_processor = GoldProcessor(self.settings)
        self.gold_processor.set_connection(connection)
        
        self.geo_enrichment = GeographicEnrichmentProcessor(self.settings)
        self.geo_enrichment.set_connection(connection)
        
        # Initialize embedding pipeline if enabled
        if self.settings.processing.generate_embeddings:
            self.embedding_pipeline = EmbeddingPipeline(self.settings)
            if not self.embedding_pipeline.initialize():
                raise RuntimeError("Failed to initialize embedding pipeline")
        
        # Initialize writers if not in dry run mode
        if not self.settings.dry_run:
            self.parquet_writer = ParquetWriter(self.settings)
            self.parquet_writer.set_connection(connection)
            
            if self.settings.processing.generate_embeddings:
                self.embedding_writer = EmbeddingWriter(self.settings)
                self.embedding_writer.set_connection(connection)
        
        self.logger.info("Processors initialized")
        
        # Create output directory
        if not self.settings.dry_run:
            self.settings.data.output_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory: {self.settings.data.output_path}")
        
        # Log configuration
        self.logger.info(f"Sample size: {self.settings.data.sample_size or 'All'}")
        self.logger.info(f"Dry run: {self.settings.dry_run}")
    
    def _load_raw_data(self) -> None:
        """Load raw data into Bronze tier."""
        self.logger.info("Loading raw data (Bronze tier)")
        
        # Load properties
        self._load_properties()
        
        # Note: Additional data sources (neighborhoods, wikipedia) can be added in future phases
    
    def _load_properties(self) -> None:
        """Load property data."""
        property_file = self.settings.data.input_path / self.settings.data.properties_file
        
        if not property_file.exists():
            self.logger.warning(f"Property file not found: {property_file}")
            return
        
        # Initialize property loader
        property_loader = PropertyLoader(self.settings)
        property_loader.set_connection(self.connection_manager.get_connection())
        
        # Load data
        table_name = property_loader.load(property_file)
        
        # Validate data
        if property_loader.validate(table_name):
            record_count = property_loader.count_records(table_name)
            self.metrics["records_processed"] += record_count
            self.metrics["bronze_records"] = record_count
            self.metrics["tables_created"] += 1
            
            # Track table for recovery
            self.state_manager.record_table("bronze", table_name)
            
            self.logger.success(f"Loaded {record_count} properties into {table_name} (Bronze tier)")
            
            # Show sample data
            sample_data = property_loader.get_sample_data(table_name, limit=3)
            if sample_data:
                self.logger.info("Sample property data:")
                for i, prop in enumerate(sample_data, 1):
                    self.logger.info(f"  {i}. {prop['listing_id']}: ${prop['listing_price']:,.0f} "
                                   f"({prop['bedrooms']}bed/{prop['bathrooms']}bath in {prop['city']})")
        else:
            self.logger.error(f"Property data validation failed for {table_name}")
            self.metrics["records_failed"] += property_loader.count_records(table_name)
    
    def _process_silver_tier(self) -> None:
        """Process Bronze data to Silver tier (data cleaning)."""
        if self.metrics["bronze_records"] == 0:
            self.logger.warning("No Bronze tier data to process")
            return
        
        self.logger.info("Processing Silver tier (data cleaning)")
        
        if not self.silver_processor:
            self.logger.error("Silver processor not initialized")
            return
        
        try:
            # Process properties from bronze to silver
            bronze_table = "raw_properties"
            silver_table = f"properties_silver_{int(time.time())}"
            
            if self.silver_processor.process(bronze_table, silver_table):
                record_count = self.silver_processor.count_records(silver_table)
                self.metrics["silver_records"] = record_count
                self.metrics["tables_created"] += 1
                
                # Track table for recovery
                self.state_manager.record_table("silver", silver_table)
                
                # Merge metrics from processor
                processor_metrics = self.silver_processor.get_metrics()
                quality_score = processor_metrics.get("data_quality_score", 0.0)
                
                self.logger.success(f"Processed {record_count} records to Silver tier")
                self.logger.info(f"Data quality score: {quality_score:.2%}")
            else:
                self.logger.error("Silver tier processing failed")
                
        except Exception as e:
            self.logger.error(f"Silver tier processing error: {e}")
            raise
    
    def _process_gold_tier(self) -> None:
        """Process Silver data to Gold tier (data enrichment)."""
        if self.metrics["silver_records"] == 0:
            self.logger.warning("No Silver tier data to process")
            return
        
        self.logger.info("Processing Gold tier (data enrichment)")
        
        if not self.gold_processor:
            self.logger.error("Gold processor not initialized")
            return
        
        try:
            # Get the latest Silver table
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_silver_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if not result:
                self.logger.error("No Silver tier table found")
                return
            
            silver_table = result[0]
            gold_table = f"properties_gold_{int(time.time())}"
            
            if self.gold_processor.process(silver_table, gold_table):
                record_count = self.gold_processor.count_records(gold_table)
                self.metrics["gold_records"] = record_count
                self.metrics["tables_created"] += 1
                
                # Track table for recovery
                self.state_manager.record_table("gold", gold_table)
                
                # Merge metrics from processor
                processor_metrics = self.gold_processor.get_metrics()
                enrichment_completeness = processor_metrics.get("enrichment_completeness", 0.0)
                self.metrics["enrichment_completeness"] = enrichment_completeness
                
                self.logger.success(f"Processed {record_count} records to Gold tier")
                self.logger.info(f"Enrichment completeness: {enrichment_completeness:.2%}")
            else:
                self.logger.error("Gold tier processing failed")
                
        except Exception as e:
            self.logger.error(f"Gold tier processing error: {e}")
            raise
    
    def _apply_geographic_enrichment(self) -> None:
        """Apply geographic enrichment to Gold tier data."""
        if self.metrics["gold_records"] == 0:
            self.logger.warning("No Gold tier data for geographic enrichment")
            return
        
        self.logger.info("Applying geographic enrichment")
        
        if not self.geo_enrichment:
            self.logger.error("Geographic enrichment processor not initialized")
            return
        
        try:
            # Get the latest Gold table
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_gold_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if not result:
                self.logger.error("No Gold tier table found")
                return
            
            gold_table = result[0]
            enriched_table = f"properties_enriched_{int(time.time())}"
            
            if self.geo_enrichment.process(gold_table, enriched_table):
                record_count = self.geo_enrichment.count_records(enriched_table)
                self.metrics["tables_created"] += 1
                
                # Track table for recovery
                self.state_manager.record_table("enriched", enriched_table)
                
                # Merge metrics from processor
                processor_metrics = self.geo_enrichment.get_metrics()
                geo_completeness = processor_metrics.get("geographic_completeness", 0.0)
                
                self.logger.success(f"Applied geographic enrichment to {record_count} records")
                self.logger.info(f"Geographic completeness: {geo_completeness:.2%}")
            else:
                self.logger.error("Geographic enrichment failed")
                
        except Exception as e:
            self.logger.error(f"Geographic enrichment error: {e}")
            raise
    
    def _generate_embeddings(self) -> None:
        """Generate embeddings from enriched property data."""
        if not self.settings.processing.generate_embeddings:
            self.logger.info("Embedding generation disabled")
            return
        
        if not self.embedding_pipeline:
            self.logger.warning("No embedding pipeline initialized")
            return
        
        # Determine which table to use for embedding generation
        final_table = None
        if self.metrics.get("gold_records", 0) > 0:
            # Get the latest enriched table (geographic enrichment or Gold tier)
            connection = self.connection_manager.get_connection()
            
            # Try to get the latest enriched table first
            enriched_result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_enriched_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if enriched_result:
                final_table = enriched_result[0]
                self.logger.info("Using geographic enriched data for embeddings")
            else:
                # Fall back to Gold tier
                gold_result = connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_gold_%' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if gold_result:
                    final_table = gold_result[0]
                    self.logger.info("Using Gold tier data for embeddings")
        
        if not final_table:
            self.logger.warning("No suitable data found for embedding generation")
            return
        
        self.logger.info("Generating embeddings from enriched property data")
        
        try:
            # Extract property data from the final table
            connection = self.connection_manager.get_connection()
            properties_data = connection.execute(f"SELECT * FROM {final_table}").fetchall()
            
            if not properties_data:
                self.logger.warning("No property data found for embedding generation")
                return
            
            # Convert to list of dictionaries
            columns = [desc[0] for desc in connection.execute(f"DESCRIBE {final_table}").fetchall()]
            properties_dict = [
                {col: row[i] for i, col in enumerate(columns)}
                for row in properties_data
            ]
            
            self.logger.info(f"Processing {len(properties_dict)} properties for embedding generation")
            
            # Process through embedding pipeline
            embedded_nodes = self.embedding_pipeline.process_gold_properties(properties_dict)
            
            # Store embedded nodes for output
            self.embedded_nodes = embedded_nodes
            
            # Update metrics
            embedding_metrics = self.embedding_pipeline.get_pipeline_metrics()
            self.metrics.update({
                "documents_converted": embedding_metrics["documents_converted"],
                "embeddings_generated": embedding_metrics["embeddings_generated"],
                "embedding_success_rate": embedding_metrics["embedding_success_rate"]
            })
            
            self.logger.success(f"Generated embeddings for {len(embedded_nodes)} text nodes")
            self.logger.info(f"Embedding success rate: {self.metrics['embedding_success_rate']:.2%}")
            
        except Exception as e:
            self.logger.error(f"Embedding generation error: {e}")
            raise
    
    def _write_output(self) -> None:
        """Write final output to Parquet files."""
        if self.settings.dry_run:
            self.logger.info("Dry run mode - skipping output writing")
            return
        
        if not self.parquet_writer:
            self.logger.warning("No Parquet writer initialized")
            return
        
        self.logger.info("Writing output to Parquet files")
        
        try:
            # Determine which table to write (most enriched available)
            final_table = self._get_final_table()
            
            if not final_table:
                self.logger.warning("No data available for output")
                return
            
            # Generate output filename with timestamp
            timestamp = int(time.time())
            output_filename = f"properties_{self.settings.environment}_{timestamp}.parquet"
            output_path = self.settings.data.output_path / output_filename
            
            # Determine partitioning strategy
            partition_columns = []
            if self.settings.parquet.per_thread_output or len(self.parquet_writer.get_partition_columns()) > 0:
                # Check which partition columns are available
                available_columns = set()
                schema_result = self.connection_manager.get_connection().execute(
                    f"DESCRIBE {final_table}"
                ).fetchall()
                for col in schema_result:
                    available_columns.add(col[0])
                
                # Only use partition columns that exist in the table
                requested_partitions = self.parquet_writer.get_partition_columns()
                partition_columns = [col for col in requested_partitions if col in available_columns]
                
                if partition_columns:
                    self.logger.info(f"Using partition columns: {partition_columns}")
            
            # Write properties data to Parquet
            if partition_columns:
                # Write partitioned output
                partition_dir = self.settings.data.output_path / f"partitioned_{timestamp}"
                written_files = self.parquet_writer.write_partitioned(
                    final_table,
                    partition_dir,
                    partition_columns
                )
                self.logger.success(f"Wrote {len(written_files)} partitioned files to {partition_dir}")
                self.metrics["output_files"] = len(written_files)
            else:
                # Write single file
                parquet_path = self.parquet_writer.write_with_schema(
                    final_table,
                    output_path
                )
                self.logger.success(f"Wrote properties to {parquet_path}")
                self.metrics["output_files"] = 1
            
            # Validate output if configured
            if self.settings.validate_output:
                validation_file = output_path if not partition_columns else written_files[0] if written_files else None
                if validation_file and self.parquet_writer.validate_output(validation_file):
                    self.logger.success("Output validation passed")
                else:
                    self.logger.warning("Output validation failed")
            
            # Write embeddings if available
            if self.embedded_nodes and self.embedding_writer:
                embeddings_filename = f"embeddings_{self.settings.environment}_{timestamp}.parquet"
                embeddings_path = self.settings.data.output_path / embeddings_filename
                
                self.embedding_writer.write_embedded_nodes(
                    self.embedded_nodes,
                    embeddings_path,
                    include_embeddings=True
                )
                
                # Write embedding metadata
                metadata_path = embeddings_path.with_suffix('.metadata.json')
                self.embedding_writer.write_embedding_metadata(
                    self.embedded_nodes,
                    metadata_path
                )
                
                self.logger.success(f"Wrote embeddings to {embeddings_path}")
                self.metrics["embedding_files"] = 1
            
            # Get output statistics
            total_size_mb = self.parquet_writer.get_total_size() / (1024 * 1024)
            self.metrics["output_size_mb"] = total_size_mb
            self.logger.info(f"Total output size: {total_size_mb:.2f} MB")
            
        except Exception as e:
            self.logger.error(f"Output writing error: {e}")
            raise
    
    def _get_final_table(self) -> Optional[str]:
        """Get the most enriched table available for output."""
        connection = self.connection_manager.get_connection()
        
        # Try to get the latest enriched table first
        enriched_result = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_enriched_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if enriched_result:
            return enriched_result[0]
        
        # Fall back to Gold tier
        gold_result = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_gold_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if gold_result:
            return gold_result[0]
        
        # Fall back to Silver tier
        silver_result = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_silver_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if silver_result:
            return silver_result[0]
        
        return None
    
    def _finalize_pipeline(self) -> None:
        """Finalize pipeline execution and log metrics."""
        if self.start_time:
            self.metrics["processing_time"] = time.time() - self.start_time
        
        # Log final metrics
        log_data_quality(
            self.metrics["records_processed"],
            self.metrics["records_failed"],
            self.metrics["processing_time"]
        )
        
        self.logger.success("Pipeline execution completed")
        self.logger.info(f"Tables created: {self.metrics['tables_created']}")
        self.logger.info(f"Total processing time: {self.metrics['processing_time']:.2f}s")
        
        # Log medallion tier metrics
        self.logger.info("Medallion Architecture Results:")
        self.logger.info(f"  Bronze tier: {self.metrics['bronze_records']} records")
        self.logger.info(f"  Silver tier: {self.metrics['silver_records']} records")  
        self.logger.info(f"  Gold tier: {self.metrics['gold_records']} records")
        if self.metrics['enrichment_completeness'] > 0:
            self.logger.info(f"  Enrichment completeness: {self.metrics['enrichment_completeness']:.2%}")
        
        # Log embedding metrics if applicable
        if self.metrics.get('documents_converted', 0) > 0:
            self.logger.info("Embedding Generation Results:")
            self.logger.info(f"  Documents converted: {self.metrics['documents_converted']}")
            self.logger.info(f"  Embeddings generated: {self.metrics['embeddings_generated']}")
            self.logger.info(f"  Embedding success rate: {self.metrics['embedding_success_rate']:.2%}")
        
        # Log output metrics if applicable
        if self.metrics.get('output_files', 0) > 0:
            self.logger.info("Output Generation Results:")
            self.logger.info(f"  Output files written: {self.metrics.get('output_files', 0)}")
            if self.metrics.get('embedding_files', 0) > 0:
                self.logger.info(f"  Embedding files written: {self.metrics.get('embedding_files', 0)}")
            self.logger.info(f"  Total output size: {self.metrics.get('output_size_mb', 0):.2f} MB")
        
        if self.settings.dry_run:
            self.logger.info("Dry run completed - no files written")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline execution metrics."""
        # Update state manager with latest metrics
        self.state_manager.update_metrics(self.metrics)
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status.
        
        Returns:
            Dictionary with pipeline status information
        """
        status = self.state_manager.get_state_summary()
        status["metrics"] = self.metrics
        return status
    
    def cleanup(self) -> None:
        """Clean up pipeline resources."""
        if hasattr(self, 'connection_manager'):
            self.connection_manager.close()
        
        # Clean up old state files
        if hasattr(self, 'state_manager'):
            self.state_manager.cleanup_old_states(days=7)
        
        self.logger.info("Pipeline cleanup completed")