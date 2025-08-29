"""Main pipeline orchestrator for SQUACK pipeline."""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from squack_pipeline.config.settings import PipelineSettings
# from squack_pipeline.config.schemas import MedallionTier  # Using MedallionTier from processing_models instead
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.location_loader import LocationLoader
from squack_pipeline.loaders.wikipedia_loader import WikipediaLoader
# Silver tier processors (entity-specific)
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.wikipedia_silver_processor import WikipediaSilverProcessor

# Gold tier processors (entity-specific)
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.processors.wikipedia_gold_processor import WikipediaGoldProcessor

# Enrichment processors
from squack_pipeline.processors.geographic_enrichment import GeographicEnrichmentProcessor
from squack_pipeline.processors.entity_processor import PropertyProcessor
from squack_pipeline.processors.cross_entity_enrichment import CrossEntityEnrichmentProcessor
from squack_pipeline.models import (
    EntityType, MedallionTier, ProcessingStage, ProcessingContext,
    TableIdentifier, create_standard_property_pipeline, ProcessingResult
)
from squack_pipeline.embeddings.pipeline import EmbeddingPipeline
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
        
        # Silver tier processors (entity-specific)
        self.property_silver_processor: Optional[PropertySilverProcessor] = None
        self.neighborhood_silver_processor: Optional[NeighborhoodSilverProcessor] = None
        self.wikipedia_silver_processor: Optional[WikipediaSilverProcessor] = None
        
        # Gold tier processors (entity-specific)
        self.property_gold_processor: Optional[PropertyGoldProcessor] = None
        self.neighborhood_gold_processor: Optional[NeighborhoodGoldProcessor] = None
        self.wikipedia_gold_processor: Optional[WikipediaGoldProcessor] = None
        
        # Enrichment processors
        self.geo_enrichment: Optional[GeographicEnrichmentProcessor] = None
        self.embedding_pipeline: Optional[EmbeddingPipeline] = None
        self.property_processor: Optional[PropertyProcessor] = None
        self.cross_entity_enrichment: Optional[CrossEntityEnrichmentProcessor] = None
        self.processing_pipeline = create_standard_property_pipeline()
        
        # Initialize writers
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
            
            # Phase 5: Cross-entity enrichment (join properties with neighborhoods and Wikipedia)
            self.state_manager.update_state(PipelineState.ENRICHING_GEOGRAPHIC, "Applying cross-entity enrichment")
            self._apply_cross_entity_enrichment()
            
            # Phase 6: Embedding generation (optional)
            if self.settings.processing.generate_embeddings:
                self.state_manager.update_state(PipelineState.GENERATING_EMBEDDINGS, "Generating embeddings")
            self._generate_embeddings()
            
            # Phase 7: Write output to Parquet files
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
        
        self.geo_enrichment = GeographicEnrichmentProcessor(self.settings)
        self.geo_enrichment.set_connection(connection)
        self.geo_enrichment.set_tier(MedallionTier.GOLD)
        
        # Initialize Silver tier processors
        self.property_silver_processor = PropertySilverProcessor(self.settings)
        self.property_silver_processor.set_connection(connection)
        
        self.neighborhood_silver_processor = NeighborhoodSilverProcessor(self.settings)
        self.neighborhood_silver_processor.set_connection(connection)
        
        self.wikipedia_silver_processor = WikipediaSilverProcessor(self.settings)
        self.wikipedia_silver_processor.set_connection(connection)
        
        # Initialize Gold tier processors
        self.property_gold_processor = PropertyGoldProcessor(self.settings)
        self.property_gold_processor.set_connection(connection)
        
        self.neighborhood_gold_processor = NeighborhoodGoldProcessor(self.settings)
        self.neighborhood_gold_processor.set_connection(connection)
        
        self.wikipedia_gold_processor = WikipediaGoldProcessor(self.settings)
        self.wikipedia_gold_processor.set_connection(connection)
        
        # Initialize enrichment processor
        self.property_processor = PropertyProcessor(self.settings)
        self.property_processor.set_connection(connection)
        
        self.cross_entity_enrichment = CrossEntityEnrichmentProcessor(self.settings)
        self.cross_entity_enrichment.set_connection(connection)
        
        # Initialize embedding pipeline if enabled
        if self.settings.processing.generate_embeddings:
            self.embedding_pipeline = EmbeddingPipeline(self.settings)
            if not self.embedding_pipeline.initialize():
                raise RuntimeError("Failed to initialize embedding pipeline")
        
        # Initialize embedding writer if needed
        if not self.settings.dry_run:
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
        
        # Load all entity types
        self._load_properties()
        self._load_neighborhoods()
        self._load_locations()
        self._load_wikipedia()
    
    def _load_properties(self) -> None:
        """Load property data from all configured files."""
        self.logger.info("Loading property data...")
        
        # Initialize property loader
        property_loader = PropertyLoader(self.settings)
        property_loader.set_connection(self.connection_manager.get_connection())
        
        # Load data (loader now uses configured files)
        table_name = property_loader.load()
        
        # Validate data
        if property_loader.validate(table_name):
            record_count = property_loader.count_records(table_name)
            self.metrics["records_processed"] += record_count
            self.metrics["bronze_records"] += record_count
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
    
    def _load_neighborhoods(self) -> None:
        """Load neighborhood data from all configured files."""
        self.logger.info("Loading neighborhood data...")
        
        # Initialize neighborhood loader
        neighborhood_loader = NeighborhoodLoader(self.settings)
        neighborhood_loader.set_connection(self.connection_manager.get_connection())
        
        # Load data
        table_name = neighborhood_loader.load()
        
        # Validate data
        if neighborhood_loader.validate(table_name):
            record_count = neighborhood_loader.count_records(table_name)
            self.metrics["records_processed"] += record_count
            self.metrics["bronze_records"] += record_count
            self.metrics["tables_created"] += 1
            
            # Track table for recovery
            self.state_manager.record_table("bronze", table_name)
            
            self.logger.success(f"Loaded {record_count} neighborhoods into {table_name} (Bronze tier)")
            
            # Show sample data
            sample_data = neighborhood_loader.get_sample_data(table_name, limit=3)
            if sample_data:
                self.logger.info("Sample neighborhood data:")
                for i, hood in enumerate(sample_data, 1):
                    self.logger.info(f"  {i}. {hood.get('name', 'N/A')} in {hood.get('city', 'N/A')}")
        else:
            self.logger.error(f"Neighborhood data validation failed for {table_name}")
            self.metrics["records_failed"] += neighborhood_loader.count_records(table_name)
    
    def _load_locations(self) -> None:
        """Load location data from configured file."""
        self.logger.info("Loading location data...")
        
        # Initialize location loader
        location_loader = LocationLoader(self.settings)
        location_loader.set_connection(self.connection_manager.get_connection())
        
        # Load data
        table_name = location_loader.load()
        
        # Validate data
        if location_loader.validate(table_name):
            record_count = location_loader.count_records(table_name)
            self.metrics["records_processed"] += record_count
            self.metrics["bronze_records"] += record_count
            self.metrics["tables_created"] += 1
            
            # Track table for recovery
            self.state_manager.record_table("bronze", table_name)
            
            self.logger.success(f"Loaded {record_count} locations into {table_name} (Bronze tier)")
        else:
            self.logger.error(f"Location data validation failed for {table_name}")
            self.metrics["records_failed"] += location_loader.count_records(table_name)
    
    def _load_wikipedia(self) -> None:
        """Load Wikipedia data from SQLite database."""
        self.logger.info("Loading Wikipedia data...")
        
        # Initialize Wikipedia loader
        wikipedia_loader = WikipediaLoader(self.settings)
        wikipedia_loader.set_connection(self.connection_manager.get_connection())
        
        # Load data
        table_name = wikipedia_loader.load()
        
        # Validate data
        if wikipedia_loader.validate(table_name):
            record_count = wikipedia_loader.count_records(table_name)
            self.metrics["records_processed"] += record_count
            self.metrics["bronze_records"] += record_count
            self.metrics["tables_created"] += 1
            
            # Track table for recovery
            self.state_manager.record_table("bronze", table_name)
            
            self.logger.success(f"Loaded {record_count} Wikipedia articles into {table_name} (Bronze tier)")
            
            # Show sample data
            sample_data = wikipedia_loader.get_sample_data(table_name, limit=3)
            if sample_data:
                self.logger.info("Sample Wikipedia data:")
                for i, article in enumerate(sample_data, 1):
                    self.logger.info(f"  {i}. {article.get('title', 'N/A')} (relevance: {article.get('relevance_score', 0):.2f})")
        else:
            self.logger.error(f"Wikipedia data validation failed for {table_name}")
            self.metrics["records_failed"] += wikipedia_loader.count_records(table_name)
    
    def _process_silver_tier(self) -> None:
        """Process Bronze data to Silver tier (data cleaning)."""
        if self.metrics["bronze_records"] == 0:
            self.logger.warning("No Bronze tier data to process")
            return
        
        self.logger.info("Processing Silver tier (data cleaning)")
        
        if not self.property_silver_processor:
            self.logger.error("Property Silver processor not initialized")
            return
        
        try:
            # Type-safe processing from Bronze to Silver
            timestamp = int(time.time())
            batch_id = f"property_batch_{timestamp}"
            
            # Create type-safe processing context
            context = ProcessingContext(
                entity_type=EntityType.PROPERTY,
                source_tier=self.processing_pipeline.processing_stages[0].source_tier,
                target_tier=self.processing_pipeline.processing_stages[0].target_tier,
                processing_stage=ProcessingStage.CLEANING,
                source_table=TableIdentifier(
                    entity_type=EntityType.PROPERTY,
                    tier=self.processing_pipeline.processing_stages[0].source_tier,
                    timestamp=timestamp
                ),
                target_table=TableIdentifier(
                    entity_type=EntityType.PROPERTY,
                    tier=self.processing_pipeline.processing_stages[0].target_tier,
                    timestamp=timestamp
                ),
                batch_id=batch_id,
                record_limit=self.settings.data.sample_size
            )
            
            # Create a custom source table identifier for compatibility with existing bronze loader
            # We need to bypass the property-generated table_name for the raw table
            source_table_id = TableIdentifier(
                entity_type=EntityType.PROPERTY,
                tier=MedallionTier.BRONZE,
                timestamp=0  # Special timestamp for raw table
            )
            
            # Update context with the custom source table identifier
            context.source_table = source_table_id
            
            # Execute type-safe processing
            result = self.property_processor.process_entity(context)
            
            if result.success:
                self.metrics["silver_records"] = result.records_created
                self.metrics["tables_created"] += 1
                
                # Track table for recovery
                self.state_manager.record_table("silver", context.target_table.table_name)
                
                self.logger.success(
                    f"Type-safe processing: {result.records_processed} → {result.records_created} records "
                    f"(Quality: {result.data_quality_score:.2%}, "
                    f"Completeness: {result.completeness_score:.2%})"
                )
                
                # Log warnings if any
                for warning in result.warnings:
                    self.logger.warning(warning)
            else:
                self.logger.error(f"Type-safe Silver processing failed: {result.error_message}")
                if result.validation_errors:
                    for error in result.validation_errors:
                        self.logger.error(f"Validation error: {error}")
                
        except Exception as e:
            self.logger.error(f"Silver tier processing error: {e}")
            raise
        
        # Process neighborhoods through silver tier
        self._process_neighborhoods_silver()
    
    def _process_neighborhoods_silver(self) -> None:
        """Process neighborhoods through Silver tier."""
        if not self.neighborhood_silver_processor:
            self.logger.warning("Neighborhood processor not initialized, skipping neighborhood Silver processing")
            return
        
        try:
            timestamp = int(time.time())
            batch_id = f"neighborhood_batch_{timestamp}"
            
            # Create processing context for neighborhoods
            context = ProcessingContext(
                entity_type=EntityType.NEIGHBORHOOD,
                source_tier=MedallionTier.BRONZE,
                target_tier=MedallionTier.SILVER,
                processing_stage=ProcessingStage.CLEANING,
                source_table=TableIdentifier(
                    entity_type=EntityType.NEIGHBORHOOD,
                    tier=MedallionTier.BRONZE,
                    timestamp=0
                ),
                target_table=TableIdentifier(
                    entity_type=EntityType.NEIGHBORHOOD,
                    tier=MedallionTier.SILVER,
                    timestamp=timestamp
                ),
                batch_id=batch_id,
                record_limit=self.settings.data.sample_size
            )
            
            result = self.neighborhood_silver_processor.process_entity(context)
            
            if result.success:
                self.logger.success(
                    f"Neighborhoods Silver: {result.records_processed} → {result.records_created} records"
                )
                self.state_manager.record_table("silver", context.target_table.table_name)
            else:
                self.logger.error(f"Neighborhood Silver processing failed: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Neighborhood Silver processing error: {e}")
            # Don't raise - allow pipeline to continue with properties
    
    def _process_gold_tier(self) -> None:
        """Process Silver data to Gold tier (data enrichment)."""
        if self.metrics["silver_records"] == 0:
            self.logger.warning("No Silver tier data to process")
            return
        
        self.logger.info("Processing Gold tier (data enrichment)")
        
        if not self.property_processor:
            self.logger.error("Property processor not initialized")
            return
        
        try:
            # Get the latest Silver table using type-safe naming
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'property_gold_%' OR table_name LIKE 'property_silver_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if not result:
                self.logger.error("No Silver tier table found")
                return
            
            silver_table_name = result[0]
            
            # Parse the table name to get timestamp
            try:
                # Extract timestamp from property_silver_{timestamp}
                timestamp_str = silver_table_name.split('_')[-1]
                timestamp = int(timestamp_str)
            except (IndexError, ValueError):
                timestamp = int(time.time())
            
            # Create type-safe processing context for Silver -> Gold
            batch_id = f"property_batch_{timestamp}"
            context = ProcessingContext(
                entity_type=EntityType.PROPERTY,
                source_tier=MedallionTier.SILVER,
                target_tier=MedallionTier.GOLD,
                processing_stage=ProcessingStage.ENRICHMENT,
                source_table=TableIdentifier(
                    entity_type=EntityType.PROPERTY,
                    tier=MedallionTier.SILVER,
                    timestamp=timestamp
                ),
                target_table=TableIdentifier(
                    entity_type=EntityType.PROPERTY,
                    tier=MedallionTier.GOLD,
                    timestamp=timestamp
                ),
                batch_id=batch_id,
                record_limit=self.settings.data.sample_size
            )
            
            # Execute type-safe processing
            result = self.property_processor.process_entity(context)
            
            if result.success:
                self.metrics["gold_records"] = result.records_created
                self.metrics["tables_created"] += 1
                
                # Track table for recovery
                self.state_manager.record_table("gold", context.target_table.table_name)
                
                # Calculate enrichment completeness from result
                self.metrics["enrichment_completeness"] = result.completeness_score
                
                self.logger.success(
                    f"Type-safe Gold processing: {result.records_processed} → {result.records_created} records "
                    f"(Quality: {result.data_quality_score:.2%}, "
                    f"Completeness: {result.completeness_score:.2%})"
                )
                
                # Log warnings if any
                for warning in result.warnings:
                    self.logger.warning(warning)
            else:
                self.logger.error(f"Type-safe Gold processing failed: {result.error_message}")
                if result.validation_errors:
                    for error in result.validation_errors:
                        self.logger.error(f"Validation error: {error}")
                
        except Exception as e:
            self.logger.error(f"Gold tier processing error: {e}")
            raise
        
        # Process neighborhoods through gold tier
        self._process_neighborhoods_gold()
    
    def _process_neighborhoods_gold(self) -> None:
        """Process neighborhoods through Gold tier."""
        if not self.neighborhood_gold_processor:
            self.logger.warning("Neighborhood processor not initialized, skipping neighborhood Gold processing")
            return
        
        try:
            # Find the neighborhood silver table
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'neighborhood_silver_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if not result:
                self.logger.warning("No neighborhood Silver table found, skipping Gold processing")
                return
            
            silver_table_name = result[0]
            timestamp_str = silver_table_name.split('_')[-1]
            timestamp = int(timestamp_str)
            
            batch_id = f"neighborhood_batch_{timestamp}"
            context = ProcessingContext(
                entity_type=EntityType.NEIGHBORHOOD,
                source_tier=MedallionTier.SILVER,
                target_tier=MedallionTier.GOLD,
                processing_stage=ProcessingStage.ENRICHMENT,
                source_table=TableIdentifier(
                    entity_type=EntityType.NEIGHBORHOOD,
                    tier=MedallionTier.SILVER,
                    timestamp=timestamp
                ),
                target_table=TableIdentifier(
                    entity_type=EntityType.NEIGHBORHOOD,
                    tier=MedallionTier.GOLD,
                    timestamp=timestamp
                ),
                batch_id=batch_id,
                record_limit=self.settings.data.sample_size
            )
            
            result = self.neighborhood_gold_processor.process_entity(context)
            
            if result.success:
                self.logger.success(
                    f"Neighborhoods Gold: {result.records_processed} → {result.records_created} records"
                )
                self.state_manager.record_table("gold", context.target_table.table_name)
            else:
                self.logger.error(f"Neighborhood Gold processing failed: {result.error_message}")
                
        except Exception as e:
            self.logger.error(f"Neighborhood Gold processing error: {e}")
            # Don't raise - allow pipeline to continue
    
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
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'property_gold_%' ORDER BY table_name DESC LIMIT 1"
            ).fetchone()
            
            if not result:
                self.logger.error("No Gold tier table found")
                return
            
            gold_table = result[0]
            
            # Process returns the output table name
            enriched_table = self.geo_enrichment.process(gold_table)
            if enriched_table:
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
    
    def _apply_cross_entity_enrichment(self) -> None:
        """Apply cross-entity enrichment using SQL joins."""
        self.logger.info("Applying cross-entity enrichment")
        
        if not self.cross_entity_enrichment:
            self.logger.error("Cross-entity enrichment processor not initialized")
            return
        
        try:
            connection = self.connection_manager.get_connection()
            
            # Get the latest tables for each entity type
            # Properties - get the most enriched version
            properties_table = self._get_final_table("property")
            if not properties_table:
                self.logger.warning("No properties table found for enrichment")
                return
            
            # Neighborhoods - check for Gold tier first, then Silver, then Bronze
            neighborhoods_table = None
            for tier_prefix in ["neighborhood_gold", "neighborhood_silver", "bronze_neighborhoods"]:
                result = connection.execute(
                    f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{tier_prefix}%' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if result:
                    neighborhoods_table = result[0]
                    break
            
            if not neighborhoods_table:
                # If no processed version, use Bronze
                result = connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'bronze_neighborhoods'"
                ).fetchone()
                if result:
                    neighborhoods_table = result[0]
            
            # Wikipedia - check for Gold tier first, then Silver, then Bronze
            wikipedia_table = None
            for tier_prefix in ["wikipedia_gold", "wikipedia_silver", "bronze_wikipedia"]:
                result = connection.execute(
                    f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{tier_prefix}%' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if result:
                    wikipedia_table = result[0]
                    break
            
            if not wikipedia_table:
                # If no processed version, use Bronze
                result = connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'bronze_wikipedia'"
                ).fetchone()
                if result:
                    wikipedia_table = result[0]
            
            # Step 1: Enrich properties with neighborhoods
            if neighborhoods_table:
                enriched_table = self.cross_entity_enrichment.enrich_properties_with_neighborhoods(
                    properties_table,
                    neighborhoods_table,
                    "properties_neighborhood_enriched"
                )
                self.metrics["tables_created"] += 1
                self.state_manager.record_table("enriched", enriched_table)
                
                # Use the enriched table for next step
                properties_table = enriched_table
            else:
                self.logger.warning("No neighborhoods table found for enrichment")
            
            # Step 2: Enrich with Wikipedia articles
            if wikipedia_table:
                wiki_enriched_table = self.cross_entity_enrichment.enrich_with_geographic_proximity(
                    properties_table,
                    wikipedia_table,
                    "properties_fully_enriched",
                    max_distance_km=5.0
                )
                self.metrics["tables_created"] += 1
                self.state_manager.record_table("enriched", wiki_enriched_table)
            else:
                self.logger.warning("No Wikipedia table found for enrichment")
            
            # Step 3: Create neighborhood aggregates
            if neighborhoods_table:
                stats_table = self.cross_entity_enrichment.create_neighborhood_aggregates(
                    properties_table,
                    "neighborhood_statistics"
                )
                self.metrics["tables_created"] += 1
                self.state_manager.record_table("enriched", stats_table)
            
            # Get metrics from enrichment processor
            enrichment_metrics = self.cross_entity_enrichment.get_metrics()
            self.logger.info(f"Cross-entity enrichment metrics: {enrichment_metrics}")
            
        except Exception as e:
            self.logger.error(f"Cross-entity enrichment error: {e}")
            raise
    
    def _generate_embeddings(self) -> None:
        """Generate embeddings for all entity types."""
        if not self.settings.processing.generate_embeddings:
            self.logger.info("Embedding generation disabled")
            return
        
        if not self.embedding_pipeline:
            self.logger.warning("No embedding pipeline initialized")
            return
        
        self.logger.info("Generating embeddings for all entity types")
        connection = self.connection_manager.get_connection()
        all_embedded_nodes = []
        
        try:
            # 1. Generate embeddings for properties
            properties_table = self._get_final_table("property")
            if not properties_table:
                # Try fully enriched table
                result = connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'properties_%enriched' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if result:
                    properties_table = result[0]
            
            if properties_table:
                self.logger.info(f"Generating embeddings for properties from {properties_table}")
                properties_data = connection.execute(f"SELECT * FROM {properties_table}").fetchall()
                
                if properties_data:
                    # Convert to list of dictionaries
                    columns = [desc[0] for desc in connection.execute(f"DESCRIBE {properties_table}").fetchall()]
                    properties_dict = [
                        {col: row[i] for i, col in enumerate(columns)}
                        for row in properties_data
                    ]
                    
                    # Process through embedding pipeline
                    property_nodes = self.embedding_pipeline.process_gold_properties(properties_dict)
                    all_embedded_nodes.extend(property_nodes)
                    self.logger.success(f"Generated {len(property_nodes)} property embeddings")
            
            # 2. Generate embeddings for neighborhoods
            neighborhoods_table = None
            for prefix in ["neighborhood_gold", "neighborhood_silver", "bronze_neighborhoods"]:
                result = connection.execute(
                    f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{prefix}%' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if result:
                    neighborhoods_table = result[0]
                    break
            
            if neighborhoods_table:
                self.logger.info(f"Generating embeddings for neighborhoods from {neighborhoods_table}")
                neighborhoods_data = connection.execute(f"SELECT * FROM {neighborhoods_table}").fetchall()
                
                if neighborhoods_data:
                    # Convert to list of dictionaries
                    columns = [desc[0] for desc in connection.execute(f"DESCRIBE {neighborhoods_table}").fetchall()]
                    neighborhoods_dict = [
                        {col: row[i] for i, col in enumerate(columns)}
                        for row in neighborhoods_data
                    ]
                    
                    # Process through embedding pipeline
                    neighborhood_nodes = self.embedding_pipeline.process_neighborhoods(neighborhoods_dict)
                    all_embedded_nodes.extend(neighborhood_nodes)
                    self.logger.success(f"Generated {len(neighborhood_nodes)} neighborhood embeddings")
            
            # 3. Generate embeddings for Wikipedia articles (summaries only for efficiency)
            wikipedia_table = None
            for prefix in ["wikipedia_gold", "wikipedia_silver", "bronze_wikipedia"]:
                result = connection.execute(
                    f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{prefix}%' ORDER BY table_name DESC LIMIT 1"
                ).fetchone()
                if result:
                    wikipedia_table = result[0]
                    break
            
            if wikipedia_table:
                self.logger.info(f"Generating embeddings for Wikipedia articles from {wikipedia_table}")
                # Limit to high-relevance articles for demo efficiency
                wikipedia_data = connection.execute(
                    f"SELECT * FROM {wikipedia_table} WHERE relevance_score >= 0.3 OR relevance_score IS NULL LIMIT 100"
                ).fetchall()
                
                if wikipedia_data:
                    # Convert to list of dictionaries
                    columns = [desc[0] for desc in connection.execute(f"DESCRIBE {wikipedia_table}").fetchall()]
                    wikipedia_dict = [
                        {col: row[i] for i, col in enumerate(columns)}
                        for row in wikipedia_data
                    ]
                    
                    # Process through embedding pipeline
                    wikipedia_nodes = self.embedding_pipeline.process_wikipedia(wikipedia_dict)
                    all_embedded_nodes.extend(wikipedia_nodes)
                    self.logger.success(f"Generated {len(wikipedia_nodes)} Wikipedia embeddings")
            
            # Store all embedded nodes for output
            self.embedded_nodes = all_embedded_nodes
            
            # Update metrics
            embedding_metrics = self.embedding_pipeline.get_pipeline_metrics()
            self.metrics.update({
                "documents_converted": embedding_metrics["documents_converted"],
                "embeddings_generated": embedding_metrics["embeddings_generated"],
                "embedding_success_rate": embedding_metrics.get("embedding_success_rate", 0.0)
            })
            
            self.logger.success(f"Generated embeddings for {len(all_embedded_nodes)} total text nodes")
            self.logger.info(f"Embedding success rate: {self.metrics['embedding_success_rate']:.2%}")
            
        except Exception as e:
            self.logger.error(f"Embedding generation error: {e}")
            raise
    
    def _write_output(self) -> None:
        """Write final output to configured destinations."""
        if self.settings.dry_run:
            self.logger.info("Dry run mode - skipping output writing")
            return
        
        self.logger.info("Writing output to configured destinations")
        
        try:
            # Get final tables for all entity types
            tables = self._get_all_final_tables()
            
            if not tables:
                self.logger.warning("No data available for output")
                return
            
            # Use WriterOrchestrator to write to all destinations
            from squack_pipeline.writers.orchestrator import WriterOrchestrator
            writer_orchestrator = WriterOrchestrator(self.settings)
            
            # Write all entities to all configured destinations
            results = writer_orchestrator.write_all(
                self.connection_manager.get_connection(),
                tables
            )
            
            # Log results for each destination
            for destination, destination_results in results.items():
                self.logger.info(f"Results for {destination}:")
                
                if destination == "elasticsearch":
                    # Elasticsearch results are WriteResult objects
                    for result in destination_results:
                        if result.is_successful():
                            self.logger.success(
                                f"  ✓ {result.entity_type.value}: {result.record_count} records "
                                f"in {result.duration_seconds:.2f}s"
                            )
                        else:
                            self.logger.error(
                                f"  ✗ {result.entity_type.value}: {result.error}"
                            )
                else:
                    # Parquet results are dictionaries
                    for result in destination_results:
                        if result.get('success'):
                            self.logger.success(
                                f"  ✓ {result['entity_type']}: {result.get('record_count', 0)} records"
                            )
                        else:
                            self.logger.error(
                                f"  ✗ {result['entity_type']}: {result.get('error', 'Unknown error')}"
                            )
            
            # Update metrics
            self.metrics["output_destinations"] = len(results)
            
            # Write embeddings if available
            if self.embedded_nodes and self.embedding_writer:
                self._write_embeddings()
            
            # Close writer connections
            writer_orchestrator.close()
            
        except Exception as e:
            self.logger.error(f"Output writing error: {e}")
            raise
    
    def _write_embeddings(self) -> None:
        """Write embeddings to Parquet file."""
        if not self.embedded_nodes or not self.embedding_writer:
            return
        
        timestamp = int(time.time())
        embeddings_filename = f"embeddings_{self.settings.environment}_{timestamp}.parquet"
        embeddings_path = self.settings.data.output_path / embeddings_filename
        
        # Get embedding pipeline metrics
        embedding_metrics = self.embedding_pipeline.get_pipeline_metrics() if self.embedding_pipeline else {}
        
        provider_name = str(self.settings.embedding.provider.value)
        chunk_method_name = str(self.settings.processing.chunk_method.value)
        model_name = self.settings.embedding.voyage_model  # Default to voyage model
        
        self.embedding_writer.write_embedding_batch(
            nodes=self.embedded_nodes,
            output_path=embeddings_path,
            provider=provider_name,
            model=model_name,
            processing_time=embedding_metrics.get("processing_time", 0.0),
            chunk_method=chunk_method_name,
            chunk_size=self.settings.processing.chunk_size,
            batch_size=self.settings.processing.batch_size
        )
        
        self.logger.success(f"Wrote embeddings to {embeddings_path}")
        self.metrics["embedding_files"] = 1
    
    def _get_final_table(self, entity_prefix: str = "property") -> Optional[str]:
        """Get the most enriched table available for output for a specific entity type."""
        connection = self.connection_manager.get_connection()
        
        # Try to get the latest enriched table first
        enriched_result = connection.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{entity_prefix}_enriched_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if enriched_result:
            return enriched_result[0]
        
        # Fall back to Gold tier
        gold_result = connection.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{entity_prefix}_gold_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if gold_result:
            return gold_result[0]
        
        # Fall back to Silver tier
        silver_result = connection.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{entity_prefix}_silver_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if silver_result:
            return silver_result[0]
        
        # Fall back to raw/bronze tier
        bronze_result = connection.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{entity_prefix}_bronze_%' ORDER BY table_name DESC LIMIT 1"
        ).fetchone()
        
        if bronze_result:
            return bronze_result[0]
        
        return None
    
    def _get_all_final_tables(self) -> Dict[str, str]:
        """Get the most enriched tables for all entity types."""
        tables = {}
        
        # Get properties table
        properties_table = self._get_final_table("property")
        if properties_table:
            tables["properties"] = properties_table
        
        # Get neighborhoods table (check for raw if no processed version exists)
        neighborhoods_table = self._get_final_table("neighborhood")
        if not neighborhoods_table:
            # Fall back to raw table
            connection = self.connection_manager.get_connection()
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'bronze_neighborhoods'"
            ).fetchone()
            if result:
                neighborhoods_table = result[0]
        if neighborhoods_table:
            tables["neighborhoods"] = neighborhoods_table
        
        # Get locations table (typically stays at bronze/raw level)
        connection = self.connection_manager.get_connection()
        result = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'bronze_locations'"
        ).fetchone()
        if result:
            tables["locations"] = result[0]
        
        # Get Wikipedia table (check for processed or raw)
        wikipedia_table = self._get_final_table("wikipedia")
        if not wikipedia_table:
            # Fall back to raw table
            result = connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'bronze_wikipedia'"
            ).fetchone()
            if result:
                wikipedia_table = result[0]
        if wikipedia_table:
            tables["wikipedia"] = wikipedia_table
        
        return tables
    
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
        if self.connection_manager:
            self.connection_manager.close()
        
        # Clean up old state files
        if self.state_manager:
            self.state_manager.cleanup_old_states(days=7)
        
        self.logger.info("Pipeline cleanup completed")