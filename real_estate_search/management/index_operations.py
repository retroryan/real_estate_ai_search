"""
Index operations module for managing Elasticsearch indices.
"""

import logging
from typing import Dict, List, Optional
from elasticsearch import Elasticsearch

from ..indexer.index_manager import ElasticsearchIndexManager
from ..indexer.enums import IndexName
from ..infrastructure.elasticsearch_client import ElasticsearchClient
from .models import IndexOperationResult, ValidationStatus, ClusterHealthInfo


class IndexOperations:
    """Handles all index-related operations."""
    
    def __init__(self, es_client: ElasticsearchClient, index_manager: ElasticsearchIndexManager):
        """
        Initialize index operations.
        
        Args:
            es_client: Enhanced Elasticsearch client
            index_manager: Index manager for index operations
        """
        self.es_client = es_client
        self.index_manager = index_manager
        self.logger = logging.getLogger(__name__)
    
    def setup_indices(self, clear: bool = False, build_relationships: bool = False) -> List[IndexOperationResult]:
        """
        Create all indices with proper mappings.
        
        Args:
            clear: If True, delete existing indices first
            build_relationships: If True, build property_relationships index after setup
        
        Returns:
            List of operation results for each index
        """
        results = []
        
        if clear:
            self.logger.info("Clear flag set - deleting existing indices first...")
            results.extend(self._clear_all_indices())
        
        self.logger.info("Setting up Elasticsearch indices...")
        
        try:
            setup_results = self.index_manager.setup_all_indices()
            
            for name, success in setup_results.items():
                result = IndexOperationResult(
                    index_name=name,
                    success=success,
                    message="Index created successfully" if success else "Failed to create index"
                )
                results.append(result)
                
                if success:
                    self.logger.info(f"Successfully set up index: {name}")
                else:
                    self.logger.error(f"Failed to set up index: {name}")
            
            # Build relationships if requested
            if build_relationships:
                self.logger.info("Building property relationships...")
                try:
                    relationships_success = self.index_manager.populate_property_relationships_index()
                    result = IndexOperationResult(
                        index_name="property_relationships_population",
                        success=relationships_success,
                        message="Property relationships built successfully" if relationships_success else "Failed to build property relationships"
                    )
                    results.append(result)
                    
                    if relationships_success:
                        self.logger.info("Successfully built property relationships")
                    else:
                        self.logger.error("Failed to build property relationships")
                        
                except Exception as e:
                    self.logger.error(f"Failed to build property relationships: {str(e)}")
                    result = IndexOperationResult(
                        index_name="property_relationships_population",
                        success=False,
                        error=str(e),
                        message=f"Failed to build property relationships: {str(e)}"
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to setup indices: {str(e)}")
            return [IndexOperationResult(
                index_name="all",
                success=False,
                error=str(e)
            )]
    
    def delete_indices(self, index_names: List[str]) -> List[IndexOperationResult]:
        """
        Delete specified indices.
        
        Args:
            index_names: List of index names to delete
            
        Returns:
            List of operation results
        """
        results = []
        
        for index_name in index_names:
            try:
                success = self.index_manager.delete_index(index_name)
                result = IndexOperationResult(
                    index_name=index_name,
                    success=success,
                    message="Index deleted successfully" if success else "Failed to delete index"
                )
                results.append(result)
                
                if success:
                    self.logger.info(f"Successfully deleted index: {index_name}")
                else:
                    self.logger.error(f"Failed to delete index: {index_name}")
                    
            except Exception as e:
                results.append(IndexOperationResult(
                    index_name=index_name,
                    success=False,
                    error=str(e)
                ))
                self.logger.error(f"Failed to delete {index_name}: {str(e)}")
        
        return results
    
    def list_indices(self) -> List[ValidationStatus]:
        """
        Get current status of all indices.
        
        Returns:
            List of validation statuses for all indices
        """
        self.logger.info("Listing Elasticsearch indices...")
        
        try:
            statuses = self.index_manager.list_all_indices()
            
            validation_statuses = []
            for status in statuses:
                validation_status = ValidationStatus(
                    index_name=status.name,
                    exists=status.exists,
                    health=status.health,
                    docs_count=status.docs_count,
                    store_size_bytes=status.store_size_bytes,
                    mapping_valid=status.mapping_valid,
                    error_message=status.error_message
                )
                validation_statuses.append(validation_status)
            
            self.logger.info("Successfully listed all indices")
            return validation_statuses
            
        except Exception as e:
            self.logger.error(f"Failed to list indices: {str(e)}")
            raise
    
    def get_cluster_health(self) -> ClusterHealthInfo:
        """
        Get cluster health information.
        
        Returns:
            Cluster health information
        """
        try:
            health = self.es_client.get_cluster_health()
            return ClusterHealthInfo(
                status=health['status'],
                number_of_nodes=health['number_of_nodes'],
                active_primary_shards=health['active_primary_shards'],
                active_shards=health['active_shards'],
                unassigned_shards=health.get('unassigned_shards')
            )
        except Exception as e:
            self.logger.error(f"Failed to get cluster health: {str(e)}")
            raise
    
    def _clear_all_indices(self) -> List[IndexOperationResult]:
        """
        Delete all managed indices.
        
        Returns:
            List of deletion results
        """
        indices_to_delete = [
            IndexName.PROPERTIES, IndexName.TEST_PROPERTIES,
            IndexName.NEIGHBORHOODS, IndexName.TEST_NEIGHBORHOODS,
            IndexName.WIKIPEDIA, IndexName.TEST_WIKIPEDIA,
            IndexName.PROPERTY_RELATIONSHIPS, IndexName.TEST_PROPERTY_RELATIONSHIPS
        ]
        
        results = []
        for index_name in indices_to_delete:
            try:
                if self.es_client.client.indices.exists(index=index_name):
                    self.es_client.delete_index(index_name)
                    results.append(IndexOperationResult(
                        index_name=index_name,
                        success=True,
                        message="Index deleted for reset"
                    ))
                    self.logger.info(f"Deleted index: {index_name}")
                    
            except Exception as e:
                results.append(IndexOperationResult(
                    index_name=index_name,
                    success=False,
                    error=str(e)
                ))
                self.logger.error(f"Failed to delete {index_name}: {str(e)}")
        
        return results