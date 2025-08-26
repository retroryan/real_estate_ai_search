"""
Property cleanup for Neo4j denormalization removal.

This module handles the final phase of the three-phase Neo4j normalization process:
Phase 1: Create complete nodes
Phase 2: Create relationships 
Phase 3: Clean up denormalized properties (this module)
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from neo4j import Driver

from ..utils.database import run_query
from .config import RelationshipConfig

logger = logging.getLogger(__name__)


class CleanupResult(BaseModel):
    """Result of property cleanup operation."""
    
    entity_type: str = Field(..., description="Entity type that was cleaned")
    properties_removed: List[str] = Field(..., description="Properties that were removed")
    nodes_affected: int = Field(0, description="Number of nodes that were cleaned")
    success: bool = Field(True, description="Whether cleanup was successful")
    error_message: Optional[str] = Field(None, description="Error message if cleanup failed")


class CleanupStats(BaseModel):
    """Statistics for all cleanup operations."""
    
    properties_cleaned: int = Field(0, description="Number of Property nodes cleaned")
    neighborhoods_cleaned: int = Field(0, description="Number of Neighborhood nodes cleaned")
    total_properties_removed: int = Field(0, description="Total number of properties removed")
    
    @property
    def total_nodes_cleaned(self) -> int:
        """Total number of nodes that were cleaned."""
        return self.properties_cleaned + self.neighborhoods_cleaned


class PropertyCleanupBuilder:
    """
    Handles cleanup of denormalized properties after relationships are established.
    
    Uses native Neo4j REMOVE clauses for efficient property removal.
    """
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the property cleanup builder.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
    
    def cleanup_property_denormalization(self) -> CleanupResult:
        """
        Remove denormalized geographic and classification fields from Property nodes.
        
        These fields are no longer needed because relationships now provide
        the same information through the graph structure.
        
        Returns:
            CleanupResult with operation details
        """
        # Only remove truly denormalized fields, keep zip_code as it's a direct attribute
        properties_to_remove = ["city", "state", "property_type"]
        
        query = """
        MATCH (p:Property)
        REMOVE p.city, p.state, p.property_type
        RETURN count(p) as nodes_affected
        """
        
        try:
            if self.config.verbose:
                logger.debug("Removing denormalized properties from Property nodes...")
            
            result = run_query(self.driver, query)
            nodes_affected = result[0]["nodes_affected"] if result else 0
            
            if self.config.enable_performance_monitoring:
                logger.info(f"✓ Cleaned {nodes_affected:,} Property nodes")
            
            return CleanupResult(
                entity_type="Property",
                properties_removed=properties_to_remove,
                nodes_affected=nodes_affected,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Failed to cleanup Property nodes: {str(e)}"
            logger.error(error_msg)
            
            return CleanupResult(
                entity_type="Property",
                properties_removed=properties_to_remove,
                nodes_affected=0,
                success=False,
                error_message=error_msg
            )
    
    def cleanup_neighborhood_denormalization(self) -> CleanupResult:
        """
        Remove denormalized geographic fields from Neighborhood nodes.
        
        These fields are no longer needed because relationships now provide
        the same information through the graph structure.
        
        Returns:
            CleanupResult with operation details
        """
        properties_to_remove = ["city", "state", "county"]
        
        query = """
        MATCH (n:Neighborhood)
        REMOVE n.city, n.state, n.county
        RETURN count(n) as nodes_affected
        """
        
        try:
            if self.config.verbose:
                logger.debug("Removing denormalized properties from Neighborhood nodes...")
            
            result = run_query(self.driver, query)
            nodes_affected = result[0]["nodes_affected"] if result else 0
            
            if self.config.enable_performance_monitoring:
                logger.info(f"✓ Cleaned {nodes_affected:,} Neighborhood nodes")
            
            return CleanupResult(
                entity_type="Neighborhood",
                properties_removed=properties_to_remove,
                nodes_affected=nodes_affected,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Failed to cleanup Neighborhood nodes: {str(e)}"
            logger.error(error_msg)
            
            return CleanupResult(
                entity_type="Neighborhood",
                properties_removed=properties_to_remove,
                nodes_affected=0,
                success=False,
                error_message=error_msg
            )
    
    def cleanup_all_denormalization(self) -> CleanupStats:
        """
        Remove all denormalized properties from nodes after relationships are established.
        
        This completes the three-phase normalization process:
        1. Nodes created with complete data
        2. Relationships created using complete data  
        3. Denormalized properties cleaned up (this method)
        
        Returns:
            CleanupStats with comprehensive statistics
        """
        logger.info("🧹 Phase 3: Cleaning up denormalized properties...")
        
        # Clean Property nodes
        property_result = self.cleanup_property_denormalization()
        
        # Clean Neighborhood nodes
        neighborhood_result = self.cleanup_neighborhood_denormalization()
        
        # Calculate statistics
        stats = CleanupStats(
            properties_cleaned=property_result.nodes_affected if property_result.success else 0,
            neighborhoods_cleaned=neighborhood_result.nodes_affected if neighborhood_result.success else 0,
            total_properties_removed=(
                len(property_result.properties_removed) + len(neighborhood_result.properties_removed)
            )
        )
        
        # Log summary
        if self.config.enable_performance_monitoring:
            logger.info(f"✓ Cleanup complete: {stats.total_nodes_cleaned:,} nodes normalized")
        
        # Check for any failures
        if not property_result.success:
            logger.error(f"Property cleanup failed: {property_result.error_message}")
        if not neighborhood_result.success:
            logger.error(f"Neighborhood cleanup failed: {neighborhood_result.error_message}")
        
        return stats