"""Simplified pipeline orchestrator for SQUACK pipeline using entity-specific processors.

This orchestrator uses the new entity-specific processors that preserve nested structures:
- Bronze tier: Loaders create nested structures using DuckDB STRUCTs
- Silver tier: Entity-specific Silver processors add denormalized fields while preserving nesting
- Gold tier: Entity-specific Gold processors apply minimal transformations for Elasticsearch
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.wikipedia_loader import WikipediaLoader

# Silver tier processors (entity-specific)
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.wikipedia_silver_processor import WikipediaSilverProcessor

# Gold tier processors (entity-specific)
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.processors.wikipedia_gold_processor import WikipediaGoldProcessor

# Writers and enrichment
from squack_pipeline.embeddings.pipeline import EmbeddingPipeline
from squack_pipeline.writers.orchestrator import WriterOrchestrator
from squack_pipeline.writers.embedding_writer import EmbeddingWriter
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class SimplifiedPipelineOrchestrator:
    """Simplified orchestrator using entity-specific processors per tier."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the pipeline orchestrator."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection_manager = DuckDBConnectionManager()
        self.connection = None
        
        # Track metrics
        self.metrics: Dict[str, Any] = {
            "bronze": {"properties": 0, "neighborhoods": 0, "wikipedia": 0},
            "silver": {"properties": 0, "neighborhoods": 0, "wikipedia": 0},
            "gold": {"properties": 0, "neighborhoods": 0, "wikipedia": 0},
            "embeddings_generated": 0,
            "elasticsearch_written": 0,
            "total_time": 0.0
        }
        
        # Track table names for each tier
        self.tables: Dict[str, Dict[str, str]] = {
            "bronze": {},
            "silver": {},
            "gold": {}
        }
        
        # Loaders
        self.property_loader: Optional[PropertyLoader] = None
        self.neighborhood_loader: Optional[NeighborhoodLoader] = None
        self.wikipedia_loader: Optional[WikipediaLoader] = None
        
        # Silver processors
        self.property_silver: Optional[PropertySilverProcessor] = None
        self.neighborhood_silver: Optional[NeighborhoodSilverProcessor] = None
        self.wikipedia_silver: Optional[WikipediaSilverProcessor] = None
        
        # Gold processors
        self.property_gold: Optional[PropertyGoldProcessor] = None
        self.neighborhood_gold: Optional[NeighborhoodGoldProcessor] = None
        self.wikipedia_gold: Optional[WikipediaGoldProcessor] = None
        
        # Writers
        self.embedding_pipeline: Optional[EmbeddingPipeline] = None
        self.embedding_writer: Optional[EmbeddingWriter] = None
        self.writer_orchestrator: Optional[WriterOrchestrator] = None
    
    @log_execution_time
    def run(self) -> None:
        """Execute the complete pipeline."""
        start_time = time.time()
        self.logger.info("=" * 80)
        self.logger.info("Starting SQUACK Pipeline (Simplified Entity-Specific Processors)")
        self.logger.info("=" * 80)
        
        try:
            # Initialize all components
            self._initialize()
            
            # Phase 1: Bronze (Load raw data with nested structures)
            self.logger.info("\n" + "=" * 40)
            self.logger.info("PHASE 1: BRONZE TIER (Loading Data)")
            self.logger.info("=" * 40)
            self._load_bronze_data()
            
            # Phase 2: Silver (Clean and denormalize while preserving nesting)
            self.logger.info("\n" + "=" * 40)
            self.logger.info("PHASE 2: SILVER TIER (Cleaning Data)")
            self.logger.info("=" * 40)
            self._process_silver_tier()
            
            # Phase 3: Gold (Minimal transformation for Elasticsearch)
            self.logger.info("\n" + "=" * 40)
            self.logger.info("PHASE 3: GOLD TIER (Final Preparation)")
            self.logger.info("=" * 40)
            self._process_gold_tier()
            
            # Phase 4: Generate embeddings (skip for now - optional)
            # if self.embedding_pipeline:
            #     self.logger.info("\n" + "=" * 40)
            #     self.logger.info("PHASE 4: EMBEDDINGS")
            #     self.logger.info("=" * 40)
            #     self._generate_embeddings()
            
            # Phase 5: Write to Elasticsearch (skip for now - optional)
            # if self.writer_orchestrator:
            #     self.logger.info("\n" + "=" * 40)
            #     self.logger.info("PHASE 5: ELASTICSEARCH")
            #     self.logger.info("=" * 40)
            #     self._write_to_elasticsearch()
            
            # Report final metrics
            self.metrics["total_time"] = time.time() - start_time
            self._report_metrics()
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise
        
        finally:
            self._cleanup()
    
    def _initialize(self) -> None:
        """Initialize all pipeline components."""
        self.logger.info("Initializing pipeline components...")
        
        # Initialize connection
        self.connection_manager.initialize(self.settings)
        self.connection = self.connection_manager.get_connection()
        
        # Initialize loaders
        self.property_loader = PropertyLoader(self.settings)
        self.property_loader.set_connection(self.connection)
        
        self.neighborhood_loader = NeighborhoodLoader(self.settings)
        self.neighborhood_loader.set_connection(self.connection)
        
        self.wikipedia_loader = WikipediaLoader(self.settings)
        self.wikipedia_loader.set_connection(self.connection)
        
        # Initialize Silver processors
        self.property_silver = PropertySilverProcessor(self.settings)
        self.property_silver.set_connection(self.connection)
        
        self.neighborhood_silver = NeighborhoodSilverProcessor(self.settings)
        self.neighborhood_silver.set_connection(self.connection)
        
        self.wikipedia_silver = WikipediaSilverProcessor(self.settings)
        self.wikipedia_silver.set_connection(self.connection)
        
        # Initialize Gold processors
        self.property_gold = PropertyGoldProcessor(self.settings)
        self.property_gold.set_connection(self.connection)
        
        self.neighborhood_gold = NeighborhoodGoldProcessor(self.settings)
        self.neighborhood_gold.set_connection(self.connection)
        
        self.wikipedia_gold = WikipediaGoldProcessor(self.settings)
        self.wikipedia_gold.set_connection(self.connection)
        
        # Initialize writers (optional - commented out for testing)
        # self.embedding_pipeline = EmbeddingPipeline(self.settings)
        # self.embedding_writer = EmbeddingWriter(self.settings)
        # self.embedding_writer.set_connection(self.connection)
        # self.writer_orchestrator = WriterOrchestrator(self.settings)
        
        self.logger.success("All components initialized")
    
    def _load_bronze_data(self) -> None:
        """Load all entity types into Bronze tier with nested structures."""
        # Load properties
        self.logger.info("Loading properties...")
        sample_size = self.settings.data.sample_size if self.settings.data.sample_size > 0 else None
        bronze_properties = self.property_loader.load(sample_size=sample_size)
        self.tables["bronze"]["properties"] = bronze_properties
        self.metrics["bronze"]["properties"] = self.property_loader.count_records(bronze_properties)
        self.logger.success(f"✓ Loaded {self.metrics['bronze']['properties']} properties → {bronze_properties}")
        
        # Load neighborhoods
        self.logger.info("Loading neighborhoods...")
        bronze_neighborhoods = self.neighborhood_loader.load(sample_size=sample_size)
        self.tables["bronze"]["neighborhoods"] = bronze_neighborhoods
        self.metrics["bronze"]["neighborhoods"] = self.neighborhood_loader.count_records(bronze_neighborhoods)
        self.logger.success(f"✓ Loaded {self.metrics['bronze']['neighborhoods']} neighborhoods → {bronze_neighborhoods}")
        
        # Load Wikipedia
        self.logger.info("Loading Wikipedia articles...")
        bronze_wikipedia = self.wikipedia_loader.load(sample_size=sample_size)
        self.tables["bronze"]["wikipedia"] = bronze_wikipedia
        self.metrics["bronze"]["wikipedia"] = self.wikipedia_loader.count_records(bronze_wikipedia)
        self.logger.success(f"✓ Loaded {self.metrics['bronze']['wikipedia']} Wikipedia articles → {bronze_wikipedia}")
    
    def _process_silver_tier(self) -> None:
        """Process all entities through Silver tier (cleaning + denormalization)."""
        # Process properties
        if self.tables["bronze"].get("properties"):
            self.logger.info("Processing properties through Silver...")
            silver_properties = self.property_silver.process(self.tables["bronze"]["properties"])
            self.tables["silver"]["properties"] = silver_properties
            self.metrics["silver"]["properties"] = self.property_silver.count_records(silver_properties)
            self.logger.success(f"✓ Properties: {self.metrics['bronze']['properties']} → {self.metrics['silver']['properties']} records")
        
        # Process neighborhoods
        if self.tables["bronze"].get("neighborhoods"):
            self.logger.info("Processing neighborhoods through Silver...")
            silver_neighborhoods = self.neighborhood_silver.process(self.tables["bronze"]["neighborhoods"])
            self.tables["silver"]["neighborhoods"] = silver_neighborhoods
            self.metrics["silver"]["neighborhoods"] = self.neighborhood_silver.count_records(silver_neighborhoods)
            self.logger.success(f"✓ Neighborhoods: {self.metrics['bronze']['neighborhoods']} → {self.metrics['silver']['neighborhoods']} records")
        
        # Process Wikipedia
        if self.tables["bronze"].get("wikipedia"):
            self.logger.info("Processing Wikipedia through Silver...")
            silver_wikipedia = self.wikipedia_silver.process(self.tables["bronze"]["wikipedia"])
            self.tables["silver"]["wikipedia"] = silver_wikipedia
            self.metrics["silver"]["wikipedia"] = self.wikipedia_silver.count_records(silver_wikipedia)
            self.logger.success(f"✓ Wikipedia: {self.metrics['bronze']['wikipedia']} → {self.metrics['silver']['wikipedia']} records")
    
    def _process_gold_tier(self) -> None:
        """Process all entities through Gold tier (minimal transformation for Elasticsearch)."""
        # Process properties
        if self.tables["silver"].get("properties"):
            self.logger.info("Processing properties through Gold...")
            gold_properties = self.property_gold.process(self.tables["silver"]["properties"])
            self.tables["gold"]["properties"] = gold_properties
            self.metrics["gold"]["properties"] = self.property_gold.count_records(gold_properties)
            self.logger.success(f"✓ Properties: {self.metrics['silver']['properties']} → {self.metrics['gold']['properties']} records")
        
        # Process neighborhoods
        if self.tables["silver"].get("neighborhoods"):
            self.logger.info("Processing neighborhoods through Gold...")
            gold_neighborhoods = self.neighborhood_gold.process(self.tables["silver"]["neighborhoods"])
            self.tables["gold"]["neighborhoods"] = gold_neighborhoods
            self.metrics["gold"]["neighborhoods"] = self.neighborhood_gold.count_records(gold_neighborhoods)
            self.logger.success(f"✓ Neighborhoods: {self.metrics['silver']['neighborhoods']} → {self.metrics['gold']['neighborhoods']} records")
        
        # Process Wikipedia
        if self.tables["silver"].get("wikipedia"):
            self.logger.info("Processing Wikipedia through Gold...")
            gold_wikipedia = self.wikipedia_gold.process(self.tables["silver"]["wikipedia"])
            self.tables["gold"]["wikipedia"] = gold_wikipedia
            self.metrics["gold"]["wikipedia"] = self.wikipedia_gold.count_records(gold_wikipedia)
            self.logger.success(f"✓ Wikipedia: {self.metrics['silver']['wikipedia']} → {self.metrics['gold']['wikipedia']} records")
    
    def _generate_embeddings(self) -> None:
        """Generate embeddings for Gold tier data."""
        self.logger.info("Generating embeddings...")
        
        # Process each Gold table
        for entity_type, table_name in self.tables["gold"].items():
            if table_name:
                self.logger.info(f"Generating embeddings for {entity_type}...")
                
                # Create embedding documents
                documents = self.embedding_pipeline.create_documents_from_table(
                    table_name, entity_type
                )
                
                if documents:
                    # Generate embeddings
                    embedded_docs = self.embedding_pipeline.generate_embeddings(documents)
                    
                    # Write back to database
                    if embedded_docs:
                        self.embedding_writer.write_embeddings(
                            embedded_docs, table_name, entity_type
                        )
                        self.metrics["embeddings_generated"] += len(embedded_docs)
                        self.logger.success(f"✓ Generated {len(embedded_docs)} embeddings for {entity_type}")
    
    def _write_to_elasticsearch(self) -> None:
        """Write Gold tier data to Elasticsearch."""
        self.logger.info("Writing to Elasticsearch...")
        
        # Write each Gold table
        for entity_type, table_name in self.tables["gold"].items():
            if table_name:
                self.logger.info(f"Writing {entity_type} to Elasticsearch...")
                
                # Read data from Gold table
                query = f"SELECT * FROM {table_name}"
                data = self.connection.execute(query).fetchall()
                
                if data:
                    # Convert to dictionaries
                    columns = [desc[0] for desc in self.connection.description]
                    records = [dict(zip(columns, row)) for row in data]
                    
                    # Write to Elasticsearch using writer orchestrator
                    result = self.writer_orchestrator.write_entity_data(
                        entity_type, records
                    )
                    
                    if result.success:
                        self.metrics["elasticsearch_written"] += result.record_count
                        self.logger.success(f"✓ Wrote {result.record_count} {entity_type} to Elasticsearch")
                    else:
                        self.logger.error(f"Failed to write {entity_type}: {result.error}")
    
    def _report_metrics(self) -> None:
        """Report final pipeline metrics."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PIPELINE METRICS")
        self.logger.info("=" * 80)
        
        # Tier metrics
        self.logger.info("\nRecords by Tier:")
        for tier in ["bronze", "silver", "gold"]:
            total = sum(self.metrics[tier].values())
            self.logger.info(f"  {tier.upper():8} → {total:,} records")
            for entity, count in self.metrics[tier].items():
                if count > 0:
                    self.logger.info(f"    - {entity:12} {count:,}")
        
        # Other metrics
        if self.metrics["embeddings_generated"] > 0:
            self.logger.info(f"\nEmbeddings: {self.metrics['embeddings_generated']:,} generated")
        
        if self.metrics["elasticsearch_written"] > 0:
            self.logger.info(f"Elasticsearch: {self.metrics['elasticsearch_written']:,} documents written")
        
        # Timing
        self.logger.info(f"\nTotal Time: {self.metrics['total_time']:.2f} seconds")
        self.logger.info("=" * 80)
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.connection_manager:
            self.connection_manager.close()
            self.logger.info("Connection closed")