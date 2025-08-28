"""
Pipeline fork implementation for routing data based on output destinations.

This module provides an output-driven fork that determines processing paths
based on required destinations. It eliminates configuration confusion by
deriving processing needs from output requirements.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)


class ProcessingPaths(BaseModel):
    """Defines which processing paths are required based on output destinations."""
    
    lightweight: bool = Field(
        default=False,
        description="Lightweight path for parquet-only output"
    )
    graph: bool = Field(
        default=False,
        description="Graph path for Neo4j output (includes entity extraction)"
    )
    search: bool = Field(
        default=False,
        description="Search path for Elasticsearch output (includes document building)"
    )
    
    @classmethod
    def from_destinations(cls, destinations: List[str]) -> "ProcessingPaths":
        """
        Determine processing paths from output destinations.
        
        Args:
            destinations: List of enabled output destinations
            
        Returns:
            ProcessingPaths configuration
        """
        dest_set = set(destinations)
        
        # Determine paths based on destinations
        needs_graph = "neo4j" in dest_set
        needs_search = "elasticsearch" in dest_set
        needs_lightweight = dest_set == {"parquet"}  # Only parquet
        
        return cls(
            lightweight=needs_lightweight,
            graph=needs_graph,
            search=needs_search
        )
    
    def get_enabled_paths(self) -> List[str]:
        """Get list of enabled path names."""
        paths = []
        if self.lightweight:
            paths.append("lightweight")
        if self.graph:
            paths.append("graph")
        if self.search:
            paths.append("search")
        return paths


class ProcessingResult(BaseModel):
    """Result from processing path operations."""
    
    paths_processed: List[str] = Field(
        default_factory=list,
        description="List of processing paths that were executed"
    )
    lightweight_success: bool = Field(
        default=True,
        description="Whether lightweight processing succeeded"
    )
    graph_success: bool = Field(
        default=True,
        description="Whether graph processing succeeded"
    )
    search_success: bool = Field(
        default=True,
        description="Whether search processing succeeded"
    )
    lightweight_error: Optional[str] = Field(
        default=None,
        description="Error message if lightweight processing failed"
    )
    graph_error: Optional[str] = Field(
        default=None,
        description="Error message if graph processing failed"
    )
    search_error: Optional[str] = Field(
        default=None,
        description="Error message if search processing failed"
    )
    
    def is_successful(self) -> bool:
        """Check if all executed paths succeeded."""
        return (
            self.lightweight_success and 
            self.graph_success and 
            self.search_success
        )
    
    def get_errors(self) -> List[str]:
        """Get list of all error messages."""
        errors = []
        if self.lightweight_error:
            errors.append(f"Lightweight: {self.lightweight_error}")
        if self.graph_error:
            errors.append(f"Graph: {self.graph_error}")
        if self.search_error:
            errors.append(f"Search: {self.search_error}")
        return errors


class PipelineFork:
    """
    Output-driven pipeline fork for routing DataFrames to processing paths.
    
    This class determines processing paths based on output destinations,
    eliminating configuration confusion. It processes only what's needed
    for the configured outputs.
    """
    
    def __init__(self, destinations: List[str]):
        """
        Initialize the pipeline fork based on output destinations.
        
        Args:
            destinations: List of enabled output destinations
        """
        self.destinations = destinations
        self.paths = ProcessingPaths.from_destinations(destinations)
        
        logger.info(f"Pipeline fork initialized for destinations: {destinations}")
        logger.info(f"Enabled processing paths: {self.paths.get_enabled_paths()}")
    
    def process_paths(
        self,
        processed_entities: Dict[str, DataFrame],
        spark: Optional[SparkSession] = None,
        search_config: Optional[Any] = None,
        entity_extractors: Optional[Any] = None
    ) -> Tuple[ProcessingResult, Dict[str, Any]]:
        """
        Process DataFrames according to required output destinations.
        
        Args:
            processed_entities: Dictionary of processed entity DataFrames
            spark: Spark session for search processing
            search_config: Search pipeline configuration
            entity_extractors: Dictionary of entity extractors for graph path
            
        Returns:
            Tuple of (ProcessingResult, Dict of output data by destination)
        """
        logger.info("Starting output-driven processing")
        logger.info(f"Processing paths: {self.paths.get_enabled_paths()}")
        
        result = ProcessingResult(paths_processed=self.paths.get_enabled_paths())
        output_data = {}
        
        # Lightweight path: Just processed entities for parquet-only
        if self.paths.lightweight:
            logger.info("🗂️  Processing lightweight path (parquet-only)")
            try:
                output_data["parquet"] = processed_entities
                logger.info("✓ Lightweight path completed")
            except Exception as e:
                logger.error(f"Lightweight path failed: {e}")
                result.lightweight_success = False
                result.lightweight_error = str(e)
        
        # Graph path: Extract entities for Neo4j + parquet
        if self.paths.graph:
            logger.info("📊 Processing graph path (Neo4j)")
            try:
                # Extract additional entities for graph
                graph_entities = dict(processed_entities)  # Start with processed entities
                
                if entity_extractors:
                    extracted = self._extract_graph_entities(processed_entities, entity_extractors)
                    graph_entities.update(extracted)
                
                output_data["neo4j"] = graph_entities
                
                # Parquet gets the enriched data when graph path is active
                if "parquet" in self.destinations:
                    output_data["parquet"] = graph_entities
                
                logger.info(f"✓ Graph path completed with {len(graph_entities)} entity types")
            except Exception as e:
                logger.error(f"Graph path failed: {e}")
                result.graph_success = False
                result.graph_error = str(e)
        
        # Search path: Process documents for Elasticsearch + parquet
        # Note: Unlike Neo4j/Parquet writers, Elasticsearch doesn't use a traditional writer class.
        # Instead, it leverages the Spark Elasticsearch connector for distributed writes.
        # The SearchPipelineRunner handles both transformation and writing using Spark's native capabilities.
        if self.paths.search:
            logger.info("🔍 Processing search path (Elasticsearch)")
            try:
                if spark and search_config:
                    from data_pipeline.search_pipeline.core.search_runner import SearchPipelineRunner
                    
                    # The SearchPipelineRunner processes each entity type (properties, neighborhoods, wikipedia):
                    # 1. Transforms DataFrames using entity-specific transformers
                    # 2. Writes directly to Elasticsearch using Spark's elasticsearch-spark connector
                    # 3. The connector handles batching internally (default: 1000 docs per bulk request)
                    # 4. Parallel writes occur across Spark executors automatically
                    search_runner = SearchPipelineRunner(spark, search_config)
                    search_result = search_runner.process(processed_entities)
                    
                    output_data["elasticsearch"] = search_result
                    
                    # Parquet gets processed entities if no graph path
                    if "parquet" in self.destinations and not self.paths.graph:
                        output_data["parquet"] = processed_entities
                    
                    if search_result.success:
                        logger.info(f"✓ Search path completed: {search_result.total_documents_indexed} documents indexed")
                    else:
                        result.search_success = False
                        result.search_error = search_result.error_message
                else:
                    logger.warning("Search path enabled but missing Spark session or config")
                    result.search_success = False
                    result.search_error = "Missing Spark session or search configuration"
                    
            except Exception as e:
                logger.error(f"Search path failed: {e}")
                result.search_success = False
                result.search_error = str(e)
        
        logger.info(f"Processing complete - Success: {result.is_successful()}")
        if not result.is_successful():
            logger.error(f"Errors: {', '.join(result.get_errors())}")
        
        return result, output_data
    
    def _extract_graph_entities(
        self, 
        processed_entities: Dict[str, DataFrame], 
        extractors: Dict[str, Any]
    ) -> Dict[str, DataFrame]:
        """
        Extract additional entities for graph processing.
        
        Args:
            processed_entities: Base processed entities
            extractors: Dictionary of entity extractors
            
        Returns:
            Dictionary of extracted entity DataFrames
        """
        extracted = {}
        
        # Extract features from properties
        if "properties" in processed_entities and "feature_extractor" in extractors:
            logger.info("   Extracting features...")
            extracted["features"] = extractors["feature_extractor"].extract(processed_entities["properties"])
        
        # Extract property types
        if "properties" in processed_entities and "property_type_extractor" in extractors:
            logger.info("   Extracting property types...")
            extracted["property_types"] = extractors["property_type_extractor"].extract_property_types(processed_entities["properties"])
        
        # Extract ZIP codes
        if "properties" in processed_entities and "zip_code_extractor" in extractors:
            logger.info("   Extracting ZIP codes...")
            locations_data = extractors.get("locations_data")
            extracted["zip_codes"] = extractors["zip_code_extractor"].extract_zip_codes(
                processed_entities["properties"], 
                locations_data
            )
        
        # Extract price ranges
        if "properties" in processed_entities and "price_range_extractor" in extractors:
            logger.info("   Extracting price ranges...")
            extracted["price_ranges"] = extractors["price_range_extractor"].extract_price_ranges(processed_entities["properties"])
        
        # Extract geographic entities from locations data
        locations_data = extractors.get("locations_data")
        properties_data = processed_entities.get("properties")
        
        # Extract cities
        if "city_extractor" in extractors and locations_data is not None:
            logger.info("   Extracting cities...")
            extracted["cities"] = extractors["city_extractor"].extract_cities(
                locations_data,
                properties_data
            )
        
        # Extract counties
        if "county_extractor" in extractors and locations_data is not None:
            logger.info("   Extracting counties...")
            extracted["counties"] = extractors["county_extractor"].extract_counties(
                locations_data,
                properties_data,
                processed_entities.get("neighborhoods")
            )
        
        # Extract states
        if "state_extractor" in extractors and locations_data is not None:
            logger.info("   Extracting states...")
            extracted["states"] = extractors["state_extractor"].extract_states(
                locations_data,
                properties_data
            )
        
        # Extract topic clusters from Wikipedia
        if "wikipedia" in processed_entities and "topic_extractor" in extractors:
            logger.info("   Extracting topic clusters...")
            extracted["topic_clusters"] = extractors["topic_extractor"].extract_topic_clusters(processed_entities["wikipedia"])
        
        return extracted
    
    def validate_entities(self, processed_entities: Dict[str, DataFrame]) -> bool:
        """
        Validate processed entities are ready for processing.
        
        Args:
            processed_entities: Dictionary of entity DataFrames
            
        Returns:
            True if entities are valid for processing
        """
        try:
            if not processed_entities:
                logger.error("No processed entities provided")
                return False
            
            for entity_type, df in processed_entities.items():
                if df is not None:
                    if len(df.columns) == 0:
                        logger.error(f"{entity_type} DataFrame has no columns")
                        return False
                    logger.debug(f"✓ {entity_type}: {len(df.columns)} columns")
            
            return True
            
        except Exception as e:
            logger.error(f"Entity validation failed: {e}")
            return False