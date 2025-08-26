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

from data_pipeline.config.settings import ConfigurationManager
from data_pipeline.core.spark_session import get_or_create_spark_session
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
from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
from data_pipeline.enrichment.feature_extractor import FeatureExtractor
from data_pipeline.enrichment.county_extractor import CountyExtractor
from data_pipeline.enrichment.entity_extractors import PropertyTypeExtractor, PriceRangeExtractor
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
    
    def __init__(self, config_path: Optional[str] = None, config_override: Optional[Any] = None):
        """
        Initialize pipeline runner.
        
        Args:
            config_path: Path to configuration file
            config_override: Optional configuration object to use instead of loading from file
        """
        # Load configuration
        if config_override is not None:
            # Use the provided configuration directly
            self.config = config_override
            self.config_manager = None
        else:
            self.config_manager = ConfigurationManager(config_path)
            self.config = self.config_manager.load_config()
        
        # Configure logging
        self._setup_logging()
        
        # Initialize Spark session with conditional Neo4j configuration
        self.spark = get_or_create_spark_session(self.config, self.config)
        
        # Initialize components
        self.loader = DataLoaderOrchestrator(self.spark, self.config)
        
        # Initialize entity-specific processors and enrichers
        self._init_entity_processors()
        # Entity-specific embedding generators will be created as needed
        self.embedding_config = self._init_embedding_config()
        
        # Initialize relationship builder
        self.relationship_builder = RelationshipBuilder(self.spark)
        
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
        self.property_type_extractor = PropertyTypeExtractor(self.spark)
        self.price_range_extractor = PriceRangeExtractor(self.spark)
        self.topic_extractor = TopicExtractor(self.spark)
    
    def _init_embedding_config(self):
        """Initialize embedding configuration for entity-specific generators."""
        from data_pipeline.models.embedding_config import EmbeddingPipelineConfig
        
        # Convert config to proper Pydantic type
        if isinstance(self.config.embedding, EmbeddingPipelineConfig):
            return self.config.embedding
        elif isinstance(self.config.embedding, dict):
            return EmbeddingPipelineConfig.from_dict(self.config.embedding)
        else:
            # Handle legacy config objects
            return EmbeddingPipelineConfig.from_pipeline_config(self.config.embedding)
    
    def _init_writer_orchestrator(self) -> Optional[WriterOrchestrator]:
        """Initialize the writer orchestrator with configured destinations."""
        writers = []
        
        # Add writers based on enabled destinations
        if hasattr(self.config, 'enabled_destinations'):
            # Add Parquet writer if enabled
            if "parquet" in self.config.enabled_destinations:
                logger.info("Initializing Parquet writer")
                writers.append(ParquetWriter(self.config, self.spark))
            
            # Add Neo4j graph writer if enabled
            if "neo4j" in self.config.enabled_destinations:
                logger.info("Initializing Neo4j graph writer")
                from data_pipeline.writers.neo4j import Neo4jOrchestrator
                writers.append(Neo4jOrchestrator(self.config, self.spark))
            
            # Add Elasticsearch writer if enabled
            if "archive_elasticsearch" in self.config.enabled_destinations:
                logger.info("Initializing Elasticsearch writer")
                from data_pipeline.writers.archive_elasticsearch import ElasticsearchOrchestrator
                writers.append(ElasticsearchOrchestrator(self.config, self.spark))
        
        
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
            
            # Process neighborhoods first (needed for property enrichment)
            if loaded_data.neighborhoods is not None:
                logger.info("\n🏘️ Processing neighborhoods...")
                processed_entities['neighborhoods'] = self._process_neighborhoods(
                    loaded_data.neighborhoods
                )
                # Set neighborhoods data for property enricher
                self.property_enricher.set_neighborhoods_data(processed_entities['neighborhoods'])
            
            # Process properties
            if loaded_data.properties is not None:
                logger.info("\n🏠 Processing properties...")
                processed_entities['properties'] = self._process_properties(
                    loaded_data.properties
                )
            
            # Process Wikipedia articles
            if loaded_data.wikipedia is not None:
                logger.info("\n📚 Processing Wikipedia articles...")
                processed_entities['wikipedia'] = self._process_wikipedia(
                    loaded_data.wikipedia
                )
            
            # Extract new entity nodes from the processed data
            logger.info("\n🔍 Extracting entity nodes...")
            entity_nodes = self._extract_entity_nodes(loaded_data, processed_entities)
            
            # Add entity nodes to processed entities
            processed_entities.update(entity_nodes)
            
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
    
    def _extract_entity_nodes(self, loaded_data: LoadedData, processed_entities: Dict[str, DataFrame]) -> Dict[str, DataFrame]:
        """
        Extract new entity nodes from the loaded and processed data.
        
        Args:
            loaded_data: Original loaded data
            processed_entities: Processed entity DataFrames
            
        Returns:
            Dictionary of new entity node DataFrames
        """
        entity_nodes = {}
        
        # Extract features from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting features...")
            entity_nodes['features'] = self.feature_extractor.extract(processed_entities['properties'])
            entity_nodes['feature_relationships'] = self.feature_extractor.create_relationships(processed_entities['properties'])
        
        # Extract property types from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting property types...")
            entity_nodes['property_types'] = self.property_type_extractor.extract_property_types(processed_entities['properties'])
            entity_nodes['property_type_relationships'] = self.property_type_extractor.create_property_type_relationships(processed_entities['properties'])
        
        # Extract price ranges from properties
        if 'properties' in processed_entities:
            logger.info("   Extracting price ranges...")
            entity_nodes['price_ranges'] = self.price_range_extractor.extract_price_ranges(processed_entities['properties'])
            entity_nodes['price_range_relationships'] = self.price_range_extractor.create_price_range_relationships(processed_entities['properties'])
        
        # Extract counties from locations
        if loaded_data.locations is not None:
            logger.info("   Extracting counties...")
            entity_nodes['counties'] = self.county_extractor.extract_counties(
                loaded_data.locations,
                processed_entities.get('properties'),
                processed_entities.get('neighborhoods')
            )
            # Create county relationships if we have cities or neighborhoods
            cities_df = None  # We would need to extract cities first
            entity_nodes['county_relationships'] = self.county_extractor.create_county_relationships(
                cities_df,
                processed_entities.get('neighborhoods')
            )
        
        # Extract topic clusters from Wikipedia
        if 'wikipedia' in processed_entities:
            logger.info("   Extracting topic clusters...")
            entity_nodes['topic_clusters'] = self.topic_extractor.extract_topic_clusters(processed_entities['wikipedia'])
            entity_nodes['topic_relationships'] = self.topic_extractor.create_topic_relationships(
                processed_entities.get('wikipedia'),
                processed_entities.get('properties'),
                processed_entities.get('neighborhoods')
            )
        
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
        logger.info(f"🚀 Starting {self.config.name} v{self.config.version} with Embeddings")
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
            
            # Process each entity type separately WITH embeddings
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
            
            # Extract additional entity nodes from the processed data
            logger.info("\n🔍 Extracting entity nodes from processed data...")
            entity_nodes = self._extract_entity_nodes(loaded_data, processed_entities)
            
            # Merge extracted entities into processed_entities
            processed_entities.update(entity_nodes)
            
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
    
    def _log_write_summary(
        self, 
        entity_dataframes: Dict[str, DataFrame], 
        relationships: Dict[str, DataFrame],
        write_result: Any
    ) -> None:
        """
        Log write summary without forcing DataFrame evaluation.
        
        Args:
            entity_dataframes: Dictionary of entity DataFrames
            relationships: Dictionary of relationship DataFrames
            write_result: Result from write operations
        """
        logger.info("")
        logger.info("="*60)
        logger.info("📊 WRITE SUMMARY")
        logger.info("="*60)
        
        # Entities written
        logger.info("\n📦 Entities Written:")
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                logger.info(f"   • {entity_type.capitalize()}: ✓")
        
        # Relationships created
        if relationships:
            logger.info("\n🔗 Relationships Created:")
            for rel_type, rel_df in relationships.items():
                if rel_df is not None:
                    logger.info(f"   • {rel_type}: ✓")
        else:
            logger.info("\n🔗 No relationships created")
        
        # Performance metrics from write result
        if hasattr(write_result, 'total_duration_seconds'):
            logger.info(f"\n⏱️ Performance Metrics:")
            logger.info(f"   • Total write time: {write_result.total_duration_seconds:.2f} seconds")
        
        # Use write result statistics if available
        if hasattr(write_result, 'total_records_written'):
            logger.info(f"   • Total records written: {write_result.total_records_written:,}")
            
            if hasattr(write_result, 'total_duration_seconds') and write_result.total_duration_seconds > 0:
                records_per_sec = write_result.total_records_written / write_result.total_duration_seconds
                logger.info(f"   • Throughput: {records_per_sec:.0f} records/second")
        
        # Writer statistics
        if hasattr(write_result, 'results'):
            writers_used = set(r.writer_name for r in write_result.results)
            logger.info(f"\n📝 Writers Used: {', '.join(writers_used)}")
    
    def _build_relationships(self, entity_dataframes: Dict[str, DataFrame]) -> Dict[str, DataFrame]:
        """
        Build all relationships between entities.
        
        Args:
            entity_dataframes: Dictionary of entity DataFrames
            
        Returns:
            Dictionary of relationship DataFrames
        """
        logger.info("")
        logger.info("="*60)
        logger.info("🔗 Building Entity Relationships...")
        logger.info("="*60)
        
        relationships = {}
        
        # Build existing relationships using the RelationshipBuilder
        try:
            all_relationships = self.relationship_builder.build_all_relationships(
                properties_df=entity_dataframes.get('properties'),
                neighborhoods_df=entity_dataframes.get('neighborhoods'),
                wikipedia_df=entity_dataframes.get('wikipedia')
            )
            
            # Add successfully built relationships
            for rel_name, rel_df in all_relationships.items():
                if rel_df is not None:
                    logger.info(f"   ✓ Built {rel_name} relationships")
                    relationships[rel_name] = rel_df
            
        except Exception as e:
            logger.error(f"Failed to build base relationships: {e}")
            # Continue without relationships rather than failing pipeline
        
        # Build extended relationships
        try:
            logger.info("\n📍 Building Extended Relationships...")
            extended_relationships = self.relationship_builder.build_extended_relationships(
                properties_df=entity_dataframes.get('properties'),
                neighborhoods_df=entity_dataframes.get('neighborhoods'),
                wikipedia_df=entity_dataframes.get('wikipedia'),
                features_df=entity_dataframes.get('features'),
                property_types_df=entity_dataframes.get('property_types'),
                price_ranges_df=entity_dataframes.get('price_ranges'),
                counties_df=entity_dataframes.get('counties'),
                topic_clusters_df=entity_dataframes.get('topic_clusters')
            )
            
            # Add extended relationships
            for rel_name, rel_df in extended_relationships.items():
                if rel_df is not None:
                    logger.info(f"   ✓ Built {rel_name} relationships")
                    relationships[rel_name] = rel_df
                    
        except Exception as e:
            logger.error(f"Failed to build extended relationships: {e}")
            # Continue without extended relationships
        
        if not relationships:
            logger.warning("   No relationships built")
        
        return relationships
    
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
            "environment": self.config_manager.environment if self.config_manager else "test"
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
                'counties': EntityType.COUNTY,
                'cities': EntityType.CITY,
                'states': EntityType.STATE,
                'topic_clusters': EntityType.TOPIC_CLUSTER
            }
            
            total_written = 0
            failed_entities = []
            
            # Write each entity type
            for entity_name, df in output_dataframes.items():
                if df is None:
                    continue
                    
                # Skip relationship DataFrames (they have different structure)
                if "relationship" in entity_name.lower():
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
                    environment=self.config_manager.environment if self.config_manager else "test"
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
            
            # Step 2: Build and write relationships (if any writers support them)
            # Build relationships after nodes are written
            relationships = self._build_relationships(output_dataframes)
            
            if relationships:
                # Use the generic orchestrator method to write to all relationship-supporting writers
                success = self.writer_orchestrator.write_all_relationships(relationships)
                if success:
                    logger.info("✅ All relationships written successfully")
                else:
                    logger.warning("⚠️ Some relationships failed to write")
            
            # Step 3: Generate and log summary statistics
            self._log_write_summary(output_dataframes, relationships, None)
            
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