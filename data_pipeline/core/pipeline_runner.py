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
from pyspark.sql.functions import col

from data_pipeline.core.spark_session import get_or_create_spark_session
from data_pipeline.core.pipeline_fork import PipelineFork, ProcessingPaths
from data_pipeline.loaders.data_loader_orchestrator import DataLoaderOrchestrator, LoadedData
# Entity-specific imports will be done where needed
# Entity-specific embedding generators used instead
# Import entity-specific processors and enrichers
from data_pipeline.processing.property_text_processor import PropertyTextProcessor, PropertyTextConfig
from data_pipeline.processing.neighborhood_text_processor import NeighborhoodTextProcessor, NeighborhoodTextConfig
from data_pipeline.processing.wikipedia_text_processor import WikipediaTextProcessor, WikipediaTextConfig
from data_pipeline.enrichment.property_enricher import PropertyEnricher
from data_pipeline.enrichment.neighborhood_enricher import NeighborhoodEnricher
from data_pipeline.enrichment.wikipedia_enricher import WikipediaEnricher
from data_pipeline.enrichment.feature_extractor import FeatureExtractor
from data_pipeline.enrichment.geographic_extractors import CityExtractor, CountyExtractor, StateExtractor
from data_pipeline.enrichment.entity_extractors import PropertyTypeExtractor, PriceRangeExtractor, ZipCodeExtractor
from data_pipeline.enrichment.topic_extractor import TopicExtractor
from data_pipeline.writers.orchestrator import WriterOrchestrator
from data_pipeline.models.writer_models import (
    EntityType,
    WriteMetadata,
    WriteRequest,
)
from data_pipeline.writers.parquet_writer import ParquetWriter

logger = logging.getLogger(__name__)


class DataPipelineRunner:
    """Main pipeline orchestrator."""
    
    def __init__(self, config):
        """
        Initialize pipeline runner with configuration.
        
        Args:
            config: Validated PipelineConfig object
        """
        # Store configuration
        self.config = config
        
        # Configure logging
        self._setup_logging()
        
        # Initialize Spark session with conditional Neo4j configuration
        self.spark = get_or_create_spark_session(self.config.spark, self.config)
        
        # Initialize components
        self.loader = DataLoaderOrchestrator(self.spark, self.config.data_sources)
        
        # Initialize entity-specific processors and enrichers
        self._init_entity_processors()
        # Entity-specific embedding generators will be created as needed
        self.embedding_config = self._init_embedding_config()
        
        # Initialize pipeline fork based on output destinations
        self.pipeline_fork = PipelineFork(self.config.output.enabled_destinations)
        
        # Initialize writer orchestrator if configured
        self.writer_orchestrator = self._init_writer_orchestrator()
        
        # Track pipeline state
        self._pipeline_start_time: Optional[datetime] = None
        self._cached_dataframes: Optional[Dict[str, DataFrame]] = None
    
    def _setup_logging(self) -> None:
        """Configure logging with simple defaults."""
        # Configure root logger with INFO level and console output
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create simple formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    def _init_entity_processors(self):
        """Initialize entity-specific processors and enrichers."""
        # Property processors - always enabled
        self.property_enricher = PropertyEnricher(self.spark)
        self.property_text_processor = PropertyTextProcessor(self.spark)
        
        # Neighborhood processors - always enabled
        self.neighborhood_enricher = NeighborhoodEnricher(self.spark)
        self.neighborhood_text_processor = NeighborhoodTextProcessor(self.spark)
        
        # Wikipedia processors - always enabled
        self.wikipedia_enricher = WikipediaEnricher(self.spark)
        self.wikipedia_text_processor = WikipediaTextProcessor(self.spark)
        
        # Entity extractors - always enabled
        self.feature_extractor = FeatureExtractor(self.spark)
        self.county_extractor = CountyExtractor(self.spark)
        self.city_extractor = CityExtractor(self.spark)
        self.state_extractor = StateExtractor(self.spark)
        self.property_type_extractor = PropertyTypeExtractor(self.spark)
        self.price_range_extractor = PriceRangeExtractor(self.spark)
        self.zip_code_extractor = ZipCodeExtractor(self.spark)
        self.topic_extractor = TopicExtractor(self.spark)
    
    def _init_embedding_config(self):
        """Initialize embedding configuration for entity-specific generators."""
        # Our config.embedding is already a proper Pydantic EmbeddingConfig from config/models.py
        # No conversion needed since we're using the new clean configuration system
        return self.config.embedding
    
    def _init_writer_orchestrator(self) -> Optional[WriterOrchestrator]:
        """Initialize the writer orchestrator with configured destinations."""
        writers = []
        
        # Add writers based on enabled destinations
        # Pydantic guarantees enabled_destinations exists with at least empty list
        if "parquet" in self.config.output.enabled_destinations:
            logger.info("Initializing Parquet writer")
            writers.append(ParquetWriter(self.config.output.parquet, self.spark))
        
        # Add Neo4j graph writer if enabled
        if "neo4j" in self.config.output.enabled_destinations:
            logger.info("Initializing Neo4j graph writer")
            from data_pipeline.writers.neo4j import Neo4jOrchestrator
            writers.append(Neo4jOrchestrator(self.config.output.neo4j, self.spark))
        
        
        
        if writers:
            logger.info(f"Initialized {len(writers)} writer(s): {[w.get_writer_name() for w in writers]}")
            return WriterOrchestrator(writers)
        
        logger.info("No writers configured")
        return None
    
    def run_full_pipeline(self) -> Dict[str, DataFrame]:
        """
        Execute the complete data pipeline with embeddings.
        
        Returns:
            Dictionary of processed DataFrames by entity type with embeddings
        """
        self._pipeline_start_time = datetime.now()
        
        logger.info("="*60)
        logger.info(f"🚀 Starting {self.config.name} v{self.config.version}")
        logger.info("="*60)
        
        try:
            # Step 1: Load all data sources as separate DataFrames
            logger.info("📥 Loading data from all sources...")
            loaded_data = self.loader.load_all_sources()
            
            # Log loading summary without forcing evaluation
            if loaded_data.properties is not None:
                logger.info("   ✓ Properties data loaded")
            if loaded_data.neighborhoods is not None:
                logger.info("   ✓ Neighborhoods data loaded")
            if loaded_data.wikipedia is not None:
                logger.info("   ✓ Wikipedia data loaded")
            if loaded_data.locations is not None:
                logger.info("   ✓ Locations data loaded")
            
            # Check if any data was loaded without forcing evaluation
            has_data = (
                loaded_data.properties is not None or
                loaded_data.neighborhoods is not None or
                loaded_data.wikipedia is not None or
                loaded_data.locations is not None
            )
            
            if not has_data:
                logger.warning("No data loaded. Pipeline terminating.")
                return {}
            
            logger.info("   Data loading complete")
            
            # Process each entity type separately
            processed_entities = {}
            
            # Import entity-specific embedding generators
            from data_pipeline.processing.entity_embeddings import (
                PropertyEmbeddingGenerator, 
                NeighborhoodEmbeddingGenerator, 
                WikipediaEmbeddingGenerator
            )
            
            # Process neighborhoods first (needed for property enrichment)
            if loaded_data.neighborhoods is not None:
                logger.info("\n🏘️ Processing neighborhoods with embeddings...")
                processed_df = self._process_neighborhoods(loaded_data.neighborhoods)
                
                # Generate neighborhood-specific embeddings
                logger.info("   🔮 Generating neighborhood embeddings...")
                neighborhood_embedder = NeighborhoodEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['neighborhoods'] = neighborhood_embedder.generate_embeddings(processed_df)
                
                # Set neighborhoods data for property enricher
                self.property_enricher.set_neighborhoods_data(processed_entities['neighborhoods'])
            
            # Process properties with embeddings
            if loaded_data.properties is not None:
                logger.info("\n🏠 Processing properties with embeddings...")
                processed_df = self._process_properties(loaded_data.properties)
                
                # Generate property-specific embeddings
                logger.info("   🔮 Generating property embeddings...")
                property_embedder = PropertyEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['properties'] = property_embedder.generate_embeddings(processed_df)
            
            # Process Wikipedia articles with embeddings
            if loaded_data.wikipedia is not None:
                logger.info("\n📚 Processing Wikipedia articles with embeddings...")
                processed_df = self._process_wikipedia(loaded_data.wikipedia)
                
                # Generate Wikipedia-specific embeddings
                logger.info("   🔮 Generating Wikipedia embeddings...")
                wikipedia_embedder = WikipediaEmbeddingGenerator(self.spark, self.embedding_config)
                processed_entities['wikipedia'] = wikipedia_embedder.generate_embeddings(processed_df)
            
            # Fork point: Process based on output destinations
            logger.info("\n🔀 Fork point: Processing based on output destinations...")
            logger.info(f"Enabled destinations: {self.config.output.enabled_destinations}")
            
            # Create search config if needed
            search_config = None
            if "elasticsearch" in self.config.output.enabled_destinations:
                search_config = self._get_search_config()
            
            # Prepare extractors for graph processing if needed
            entity_extractors = None
            if "neo4j" in self.config.output.enabled_destinations:
                entity_extractors = {
                    "feature_extractor": self.feature_extractor,
                    "property_type_extractor": self.property_type_extractor,
                    "price_range_extractor": self.price_range_extractor,
                    "zip_code_extractor": self.zip_code_extractor,
                    "city_extractor": self.city_extractor,
                    "county_extractor": self.county_extractor,
                    "state_extractor": self.state_extractor,
                    "topic_extractor": self.topic_extractor,
                    "locations_data": loaded_data.locations
                }
            
            # Process all required paths
            processing_result, output_data = self.pipeline_fork.process_paths(
                processed_entities,
                spark=self.spark,
                search_config=search_config,
                entity_extractors=entity_extractors
            )
            
            # Update processed_entities based on processing results
            if "neo4j" in output_data:
                processed_entities = output_data["neo4j"]
            elif "parquet" in output_data:
                processed_entities = output_data["parquet"]
            
            # Log any processing errors
            if not processing_result.is_successful():
                for error in processing_result.get_errors():
                    logger.error(f"Processing error: {error}")
            
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
    
    def _process_properties(self, df: DataFrame) -> DataFrame:
        """
        Process property data through enrichment and text processing.
        
        Args:
            df: Property DataFrame
            
        Returns:
            Processed property DataFrame
        """
        # Set location data if available
        location_broadcast = self.loader.get_location_broadcast()
        if location_broadcast:
            self.property_enricher.set_location_data(location_broadcast)
        

        # Apply property-specific enrichment
        enriched_df = self.property_enricher.enrich(df)
        
        # Process text for properties
        processed_df = self.property_text_processor.process(enriched_df)
        
        return processed_df
    
    def _process_neighborhoods(self, df: DataFrame) -> DataFrame:
        """
        Process neighborhood data through enrichment and text processing.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            Processed neighborhood DataFrame
        """
        # Set location data if available
        location_broadcast = self.loader.get_location_broadcast()
        if location_broadcast:
            self.neighborhood_enricher.set_location_data(location_broadcast)
        
        # Apply neighborhood-specific enrichment
        enriched_df = self.neighborhood_enricher.enrich(df)
        
        # Process text for neighborhoods
        processed_df = self.neighborhood_text_processor.process(enriched_df)
        
        return processed_df
    
    def _get_search_config(self):
        """
        Create search pipeline configuration from main pipeline config.
        
        Returns:
            SearchPipelineConfig instance
        """
        from search_pipeline.models.config import SearchPipelineConfig, ElasticsearchConfig
        
        # Check if Elasticsearch is enabled in output destinations
        search_enabled = "elasticsearch" in self.config.output.enabled_destinations
        
        # Create search configuration
        search_config = SearchPipelineConfig(
            enabled=search_enabled,
            elasticsearch=ElasticsearchConfig(
                nodes=self.config.output.elasticsearch.hosts if self.config.output.elasticsearch else ["localhost:9200"],
                index_prefix=self.config.output.elasticsearch.index_prefix if self.config.output.elasticsearch else "real_estate",
                username=self.config.output.elasticsearch.username if self.config.output.elasticsearch else None
                # Don't set mapping_id here - let each entity type handle its own ID field
            )
        )
        
        return search_config
    
    def _extract_entity_nodes(self, loaded_data: LoadedData, processed_entities: Dict[str, DataFrame]) -> Dict[str, DataFrame]:
        """
        Extract new entity nodes from the loaded and processed data.
        Note: Only extracts node data. Relationships are created separately in Neo4j.
        
        Args:
            loaded_data: Original loaded data
            processed_entities: Processed entity DataFrames
            
        Returns:
            Dictionary of new entity node DataFrames (nodes only, no relationships)
        """
        entity_nodes = {}
        
        # Extract features from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting features...")
            entity_nodes['features'] = self.feature_extractor.extract(processed_entities['properties'])
        
        # Extract property types from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting property types...")
            entity_nodes['property_types'] = self.property_type_extractor.extract_property_types(processed_entities['properties'])
        
        # Extract price ranges from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting price ranges...")
            entity_nodes['price_ranges'] = self.price_range_extractor.extract_price_ranges(processed_entities['properties'])
        
        # Extract counties from locations
        if loaded_data.locations is not None:
            logger.info("   Extracting counties...")
            entity_nodes['counties'] = self.county_extractor.extract_counties(
                loaded_data.locations,
                processed_entities.get('properties'),
                processed_entities.get('neighborhoods')
            )
        
        # Extract topic clusters from Wikipedia
        if 'wikipedia' in processed_entities:
            logger.info("   Extracting topic clusters...")
            entity_nodes['topic_clusters'] = self.topic_extractor.extract_topic_clusters(processed_entities['wikipedia'])
        
        return entity_nodes
    
    def _process_wikipedia(self, df: DataFrame) -> DataFrame:
        """
        Process Wikipedia data through enrichment and text processing.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            Processed Wikipedia DataFrame
        """
        # Set location data if available
        location_broadcast = self.loader.get_location_broadcast()
        if location_broadcast:
            self.wikipedia_enricher.set_location_data(location_broadcast)
        
        # Apply Wikipedia-specific enrichment
        enriched_df = self.wikipedia_enricher.enrich(df)
        
        # Process text for Wikipedia (minimal processing as content is already optimized)
        processed_df = self.wikipedia_text_processor.process(enriched_df)
        
        return processed_df
    
    def _print_entity_pipeline_summary(self, entity_dataframes: Dict[str, DataFrame]) -> None:
        """
        Print pipeline summary without forcing DataFrame evaluation.
        
        Args:
            entity_dataframes: Dictionary of entity type to DataFrame
        """
        logger.info("")
        logger.info("="*60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("="*60)
        
        # Entity types processed
        logger.info("")
        logger.info("🏢 Entities Processed:")
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                logger.info(f"   ✓ {entity_type}")
                logger.info(f"      Columns: {len(df.columns)}")
                logger.info(f"      Partitions: {df.rdd.getNumPartitions()}")
                
                # Log schema fields without evaluation
                if "state" in df.columns:
                    logger.info(f"      Has location data: ✓")
                if "embedding_text" in df.columns:
                    logger.info(f"      Has embedding text: ✓")
                if "embeddings" in df.columns:
                    logger.info(f"      Has embeddings: ✓")
        
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
            "pipeline_name": self.config.name,
            "pipeline_version": self.config.version,
            "timestamp": datetime.now().isoformat(),
            "environment": "production"
        }
        
        if self.writer_orchestrator:
            # Use multi-destination writer
            logger.info("="*60)
            logger.info("📤 Writing to configured destinations...")
            logger.info("="*60)
            
            # Validate connections first
            logger.info("Validating destination connections...")
            self.writer_orchestrator.validate_all_connections()
            
            # Write to all destinations (legacy single DataFrame support)
            # For backward compatibility, wrap single DataFrame as "property" entity
            write_metadata = WriteMetadata(
                pipeline_name=metadata["pipeline_name"],
                pipeline_version=metadata["pipeline_version"],
                entity_type=EntityType.PROPERTY,
                record_count=0,  # Will be counted during write if needed
                environment=metadata.get("environment", "development")
            )
            request = WriteRequest(
                entity_type=EntityType.PROPERTY,
                dataframe=df,
                metadata=write_metadata
            )
            self.writer_orchestrator.write_entity(request)
            
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
        
        # Prepare metadata for writers
        metadata = {
            "pipeline_name": self.config.name,
            "pipeline_version": self.config.version,
            "timestamp": datetime.now().isoformat(),
            "entity_types": list(output_dataframes.keys()),
            "environment": "production"
        }
        
        if self.writer_orchestrator:
            # Use multi-destination writer
            logger.info("="*60)
            logger.info("📤 Writing entity DataFrames to configured destinations...")
            logger.info("="*60)
            
            # Validate connections first
            logger.info("Validating destination connections...")
            self.writer_orchestrator.validate_all_connections()
            
            # Step 1: Write all entity nodes first
            logger.info("📝 Writing entity nodes...")
            
            # Import required types
            from data_pipeline.models.writer_models import EntityType, WriteMetadata, WriteRequest
            
            # Map entity names to EntityType enum
            entity_type_map = {
                'properties': EntityType.PROPERTY,
                'neighborhoods': EntityType.NEIGHBORHOOD,
                'wikipedia': EntityType.WIKIPEDIA,
                'features': EntityType.FEATURE,
                'property_types': EntityType.PROPERTY_TYPE,
                'price_ranges': EntityType.PRICE_RANGE,
                'zip_codes': EntityType.ZIP_CODE,
                'counties': EntityType.COUNTY,
                'cities': EntityType.CITY,
                'states': EntityType.STATE,
                'topic_clusters': EntityType.TOPIC_CLUSTER
            }
            
            # Define write order according to Phase 5.3 requirements
            # 1. Geographic hierarchy first (State, County, City, ZipCode)
            # 2. Classification nodes next (PropertyType, Feature, PriceRange)
            # 3. Entity nodes (Neighborhood, Property, Wikipedia)
            # 4. Topic clusters last
            write_order = [
                'states',           # Geographic hierarchy
                'counties',         # Geographic hierarchy
                'cities',           # Geographic hierarchy
                'zip_codes',        # Geographic hierarchy
                'property_types',   # Classification nodes
                'features',         # Classification nodes
                'price_ranges',     # Classification nodes
                'neighborhoods',    # Entity nodes
                'properties',       # Entity nodes
                'wikipedia',        # Entity nodes
                'topic_clusters'    # Knowledge nodes
            ]
            
            total_written = 0
            failed_entities = []
            
            # Write entities in the defined order
            for entity_name in write_order:
                # Skip if entity not in output
                if entity_name not in output_dataframes:
                    continue
                    
                df = output_dataframes[entity_name]
                if df is None:
                    continue
                
                # Get the entity type
                entity_type = entity_type_map.get(entity_name)
                if not entity_type:
                    logger.warning(f"Skipping unknown entity type: {entity_name}")
                    continue
                
                # Create metadata for this entity
                metadata = WriteMetadata(
                    pipeline_name=self.config.name,
                    pipeline_version=self.config.version,
                    entity_type=entity_type,
                    record_count=df.count(),
                    environment="production"
                )
                
                # Create write request
                request = WriteRequest(
                    entity_type=entity_type,
                    dataframe=df,
                    metadata=metadata
                )
                
                # Write the entity
                logger.info(f"   Writing {entity_name}: {metadata.record_count:,} records...")
                results = self.writer_orchestrator.write_entity(request)
                
                # Check results
                if all(r.success for r in results):
                    total_written += metadata.record_count
                    logger.info(f"     ✓ {entity_name} written successfully")
                else:
                    failed_entities.append(entity_name)
                    logger.error(f"     ✗ {entity_name} write failed")
            
            # Log overall results
            if not failed_entities:
                logger.info(f"✅ All entity nodes written successfully")
                logger.info(f"   Total records written: {total_written:,}")
            else:
                logger.error(f"⚠️ Entity node write had failures: {failed_entities}")
                # Continue to try relationships even if some writes failed
            
            # Entity writing complete
            # Note: Relationships are created in a separate Neo4j orchestration step:
            # python -m graph_real_estate build-relationships
            
            # Log summary of entity writing only
            logger.info("")
            logger.info("="*60)
            logger.info("📊 ENTITY WRITE SUMMARY")
            logger.info("="*60)
            logger.info(f"✅ Entity nodes written successfully")
            logger.info(f"   Total records written: {total_written:,}")
            
            # List entities written
            for entity_name, df in output_dataframes.items():
                if df is not None:
                    logger.info(f"   • {entity_name.capitalize()}: Written")
            
            logger.info("\n🔗 Note: Relationships will be created in separate step")
            logger.info("   Next: python -m graph_real_estate build-relationships")
            
            logger.info("="*60)
            logger.info("✅ Pipeline write completed")
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