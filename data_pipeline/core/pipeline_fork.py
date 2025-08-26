"""
Pipeline fork implementation for routing data based on output destinations.

This module provides an output-driven fork that determines processing paths
based on required destinations. It eliminates configuration confusion by
deriving processing needs from output requirements.
"""

import logging
from typing import Dict, List, Optional, Set, Any

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
    Minimal pipeline fork for routing DataFrames to processing paths.
    
    This class receives DataFrames after text processing and routes them
    to the appropriate processing paths based on configuration. No caching
    or metrics in Phase 1 - just simple routing.
    """
    
    def __init__(self, config: ForkConfiguration):
        """
        Initialize the pipeline fork.
        
        Args:
            config: Fork configuration determining enabled paths
        """
        self.config = config
        logger.info(f"Pipeline fork initialized with paths: {config.enabled_paths}")
    
    def route(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame,
        wikipedia_df: DataFrame,
        spark: Optional[SparkSession] = None,
        search_config: Optional[Any] = None
    ) -> Tuple[ForkResult, Dict[str, Any]]:
        """
        Route DataFrames to enabled processing paths.
        
        Args:
            properties_df: Properties DataFrame after text processing
            neighborhoods_df: Neighborhoods DataFrame after text processing
            wikipedia_df: Wikipedia DataFrame after text processing
            spark: Optional Spark session for search pipeline
            search_config: Optional search pipeline configuration
            
        Returns:
            Tuple of (ForkResult, Dict of results for each path)
        """
        logger.info("Starting pipeline fork routing")
        
        result = ForkResult()
        routed_results = {}
        
        # Route to graph path if enabled
        if self.config.is_graph_enabled():
            logger.info("Routing DataFrames to graph path")
            try:
                # For graph path, just pass through the DataFrames
                routed_results["graph"] = {
                    "properties": properties_df,
                    "neighborhoods": neighborhoods_df,
                    "wikipedia": wikipedia_df
                }
                result.graph_success = True
                logger.info("Successfully routed to graph path")
            except Exception as e:
                logger.error(f"Failed to route to graph path: {e}")
                result.graph_error = str(e)
        
        # Route to search path if enabled
        if self.config.is_search_enabled():
            logger.info("Routing DataFrames to search path")
            try:
                # Process search path if Spark and config are provided
                if spark and search_config:
                    from search_pipeline.core.search_runner import SearchPipelineRunner
                    
                    search_runner = SearchPipelineRunner(spark, search_config)
                    search_result = search_runner.process({
                        "properties": properties_df,
                        "neighborhoods": neighborhoods_df,
                        "wikipedia": wikipedia_df
                    })
                    
                    routed_results["search"] = search_result
                    result.search_success = search_result.success
                    if not search_result.success:
                        result.search_error = search_result.error_message
                else:
                    # Just mark as routed without processing
                    routed_results["search"] = {
                        "properties": properties_df,
                        "neighborhoods": neighborhoods_df,
                        "wikipedia": wikipedia_df
                    }
                    result.search_success = True
                    logger.info("Search path enabled but not processed (missing config)")
                
                logger.info("Successfully routed to search path")
            except Exception as e:
                logger.error(f"Failed to route to search path: {e}")
                result.search_error = str(e)
        
        logger.info(
            f"Fork routing complete - Graph: {result.graph_success}, "
            f"Search: {result.search_success}"
        )
        
        return result, routed_results
    
    def validate_dataframes(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame,
        wikipedia_df: DataFrame
    ) -> bool:
        """
        Basic validation of input DataFrames.
        
        Args:
            properties_df: Properties DataFrame
            neighborhoods_df: Neighborhoods DataFrame
            wikipedia_df: Wikipedia DataFrame
            
        Returns:
            True if all DataFrames are valid
        """
        try:
            # Check that DataFrames are not None
            if properties_df is None:
                logger.error("Properties DataFrame is None")
                return False
            if neighborhoods_df is None:
                logger.error("Neighborhoods DataFrame is None")
                return False
            if wikipedia_df is None:
                logger.error("Wikipedia DataFrame is None")
                return False
            
            # Basic schema validation (just check they have columns)
            if len(properties_df.columns) == 0:
                logger.error("Properties DataFrame has no columns")
                return False
            if len(neighborhoods_df.columns) == 0:
                logger.error("Neighborhoods DataFrame has no columns")
                return False
            if len(wikipedia_df.columns) == 0:
                logger.error("Wikipedia DataFrame has no columns")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"DataFrame validation failed: {e}")
            return False