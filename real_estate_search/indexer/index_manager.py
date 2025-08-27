"""
Index management module for Elasticsearch operations.
Handles index creation, template registration, and mapping management.
"""

from typing import Dict, Any, List
import logging
from elasticsearch import Elasticsearch
from pydantic import BaseModel

from .mappings import get_property_mappings, get_neighborhood_mappings, get_wikipedia_mappings
from .enums import IndexName, ErrorCode
from .exceptions import ElasticsearchIndexError

logger = logging.getLogger(__name__)


class IndexStatus(BaseModel):
    """Index status information."""
    name: str
    exists: bool
    health: str = "unknown"
    docs_count: int = 0
    store_size_bytes: int = 0
    mapping_valid: bool = False
    error_message: str = None


class IndexTemplate(BaseModel):
    """Index template configuration."""
    name: str
    index_patterns: List[str]
    settings: Dict[str, Any]
    mappings: Dict[str, Any]
    priority: int = 100


class ElasticsearchIndexManager:
    """
    Manages Elasticsearch indices with proper error handling and validation.
    Provides methods for index lifecycle management.
    """
    
    def __init__(self, client: Elasticsearch):
        """
        Initialize index manager.
        
        Args:
            client: Configured Elasticsearch client
        """
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        # Verify client connection
        if not self.client.ping():
            raise ElasticsearchIndexError(
                ErrorCode.CONNECTION_ERROR,
                "Elasticsearch client connection failed"
            )
        
        self.logger.info("Index manager initialized successfully")
    
    def create_property_index(self, index_name: str = IndexName.PROPERTIES) -> bool:
        """
        Create properties index with proper mappings.
        
        Args:
            index_name: Name of the index to create
            
        Returns:
            True if index was created or already exists, False on error
        """
        try:
            # Check if index already exists
            if self.client.indices.exists(index=index_name):
                self.logger.info(f"Index {index_name} already exists")
                return True
            
            # Get mappings for properties index
            mappings_config = get_property_mappings()
            
            # Create the index
            self.client.indices.create(
                index=index_name,
                body=mappings_config
            )
            
            self.logger.info(f"Successfully created index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.INDEX_NOT_FOUND,
                f"Failed to create index {index_name}: {str(e)}"
            )

    def create_neighborhood_index(self, index_name: str = IndexName.NEIGHBORHOODS) -> bool:
        """
        Create neighborhoods index with proper mappings.
        
        Args:
            index_name: Name of the index to create
            
        Returns:
            True if index was created or already exists, False on error
        """
        try:
            # Check if index already exists
            if self.client.indices.exists(index=index_name):
                self.logger.info(f"Index {index_name} already exists")
                return True
            
            # Get mappings for neighborhoods index
            mappings_config = get_neighborhood_mappings()
            
            # Create the index
            self.client.indices.create(
                index=index_name,
                body=mappings_config
            )
            
            self.logger.info(f"Successfully created index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.INDEX_NOT_FOUND,
                f"Failed to create index {index_name}: {str(e)}"
            )

    def create_wikipedia_index(self, index_name: str = IndexName.WIKIPEDIA) -> bool:
        """
        Create Wikipedia index with proper mappings.
        
        Args:
            index_name: Name of the index to create
            
        Returns:
            True if index was created or already exists, False on error
        """
        try:
            # Check if index already exists
            if self.client.indices.exists(index=index_name):
                self.logger.info(f"Index {index_name} already exists")
                return True
            
            # Get mappings for Wikipedia index
            mappings_config = get_wikipedia_mappings()
            
            # Create the index
            self.client.indices.create(
                index=index_name,
                body=mappings_config
            )
            
            self.logger.info(f"Successfully created index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.INDEX_NOT_FOUND,
                f"Failed to create index {index_name}: {str(e)}"
            )
    
    def register_index_template(self, template: IndexTemplate) -> bool:
        """
        Register an index template.
        
        Args:
            template: Index template configuration
            
        Returns:
            True if template was registered successfully
        """
        try:
            template_body = {
                "index_patterns": template.index_patterns,
                "priority": template.priority,
                "data_stream": {
                    "failure_store": True
                },
                "template": {
                    "settings": template.settings,
                    "mappings": template.mappings
                }
            }
            
            self.client.indices.put_index_template(
                name=template.name,
                body=template_body
            )
            
            self.logger.info(f"Successfully registered template: {template.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register template {template.name}: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.CONFIGURATION_ERROR,
                f"Failed to register template {template.name}: {str(e)}"
            )
    
    def create_property_template(self) -> bool:
        """
        Create and register property index template.
        
        Returns:
            True if template was created successfully
        """
        mappings_config = get_property_mappings()
        
        template = IndexTemplate(
            name="properties_template",
            index_patterns=["properties*", "real_estate_properties*"],
            settings=mappings_config["settings"],
            mappings=mappings_config["mappings"],
            priority=100
        )
        
        return self.register_index_template(template)

    def create_neighborhood_template(self) -> bool:
        """
        Create and register neighborhood index template.
        
        Returns:
            True if template was created successfully
        """
        mappings_config = get_neighborhood_mappings()
        
        template = IndexTemplate(
            name="neighborhoods_template",
            index_patterns=["neighborhoods*", "real_estate_neighborhoods*"],
            settings=mappings_config["settings"],
            mappings=mappings_config["mappings"],
            priority=100
        )
        
        return self.register_index_template(template)

    def create_wikipedia_template(self) -> bool:
        """
        Create and register Wikipedia index template.
        
        Returns:
            True if template was created successfully
        """
        mappings_config = get_wikipedia_mappings()
        
        template = IndexTemplate(
            name="wikipedia_template",
            index_patterns=["wikipedia*", "real_estate_wikipedia*"],
            settings=mappings_config["settings"],
            mappings=mappings_config["mappings"],
            priority=100
        )
        
        return self.register_index_template(template)
    
    def validate_index_mappings(self, index_name: str) -> bool:
        """
        Validate that index has correct mappings.
        
        Args:
            index_name: Name of index to validate
            
        Returns:
            True if mappings are valid
        """
        try:
            if not self.client.indices.exists(index=index_name):
                self.logger.warning(f"Index {index_name} does not exist")
                return False
            
            # Get current mappings
            current_mappings = self.client.indices.get_mapping(index=index_name)
            index_mapping = current_mappings[index_name]["mappings"]
            current_properties = index_mapping.get("properties", {})
            
            # Determine which type of index and validate accordingly
            if "properties" in index_name.lower():
                # Properties index validation
                expected_config = get_property_mappings()
                expected_mappings = expected_config["mappings"]
                core_fields = ["listing_id", "property_type", "price"]
                
            elif "neighborhoods" in index_name.lower():
                # Neighborhoods index validation  
                expected_config = get_neighborhood_mappings()
                expected_mappings = expected_config["mappings"]
                core_fields = ["id", "name", "city"]
                
            elif "wikipedia" in index_name.lower():
                # Wikipedia index validation
                expected_config = get_wikipedia_mappings()
                expected_mappings = expected_config["mappings"]
                core_fields = ["page_id", "title", "url"]
                
            else:
                self.logger.warning(f"Unknown index type for {index_name}, skipping validation")
                return True
            
            # Check that all expected core fields exist
            for field in core_fields:
                if field not in current_properties:
                    self.logger.error(f"Missing core field {field} in index {index_name}")
                    return False
            
            # Check that embedding field exists (all indices should have this)
            if "embedding" not in current_properties:
                self.logger.error(f"Missing embedding field in index {index_name}")
                return False
                
            # Validate embedding field configuration
            embedding_field = current_properties.get("embedding", {})
            if embedding_field.get("type") != "dense_vector":
                self.logger.error(f"Embedding field type incorrect in index {index_name}")
                return False
                
            if embedding_field.get("dims") != 1024:
                self.logger.error(f"Embedding dimensions incorrect in index {index_name}")
                return False
            
            self.logger.info(f"Index {index_name} mappings validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate mappings for {index_name}: {str(e)}")
            return False
    
    def get_index_status(self, index_name: str) -> IndexStatus:
        """
        Get detailed status information for an index.
        
        Args:
            index_name: Name of index to check
            
        Returns:
            IndexStatus object with detailed information
        """
        try:
            exists = self.client.indices.exists(index=index_name)
            
            if not exists:
                return IndexStatus(
                    name=index_name,
                    exists=False,
                    error_message="Index does not exist"
                )
            
            # Get index stats
            stats = self.client.indices.stats(index=index_name)
            index_stats = stats["indices"][index_name]["total"]
            
            # Get health information
            health = self.client.cluster.health(index=index_name)
            
            # Validate mappings
            mapping_valid = self.validate_index_mappings(index_name)
            
            return IndexStatus(
                name=index_name,
                exists=True,
                health=health["status"],
                docs_count=index_stats["docs"]["count"],
                store_size_bytes=index_stats["store"]["size_in_bytes"],
                mapping_valid=mapping_valid
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get status for index {index_name}: {str(e)}")
            return IndexStatus(
                name=index_name,
                exists=False,
                error_message=str(e)
            )
    
    def list_all_indices(self) -> List[IndexStatus]:
        """
        List status for all relevant indices.
        
        Returns:
            List of IndexStatus objects for all indices
        """
        index_names = [
            IndexName.PROPERTIES,
            IndexName.TEST_PROPERTIES,
            IndexName.NEIGHBORHOODS,
            IndexName.TEST_NEIGHBORHOODS,
            IndexName.WIKIPEDIA,
            IndexName.TEST_WIKIPEDIA
        ]
        
        return [self.get_index_status(name) for name in index_names]
    
    def delete_index(self, index_name: str) -> bool:
        """
        Delete an index.
        
        Args:
            index_name: Name of index to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            if not self.client.indices.exists(index=index_name):
                self.logger.info(f"Index {index_name} does not exist, nothing to delete")
                return True
            
            self.client.indices.delete(index=index_name)
            self.logger.info(f"Successfully deleted index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete index {index_name}: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.INDEX_NOT_FOUND,
                f"Failed to delete index {index_name}: {str(e)}"
            )
    
    def setup_all_indices(self) -> Dict[str, bool]:
        """
        Set up all required indices with templates.
        
        Returns:
            Dictionary mapping index names to success status
        """
        results = {}
        
        try:
            # First create templates
            self.logger.info("Creating index templates...")
            results["property_template"] = self.create_property_template()
            results["neighborhood_template"] = self.create_neighborhood_template()
            results["wikipedia_template"] = self.create_wikipedia_template()
            
            # Then create indices
            self.logger.info("Creating indices...")
            results[IndexName.PROPERTIES] = self.create_property_index(IndexName.PROPERTIES)
            results[IndexName.TEST_PROPERTIES] = self.create_property_index(IndexName.TEST_PROPERTIES)
            results[IndexName.NEIGHBORHOODS] = self.create_neighborhood_index(IndexName.NEIGHBORHOODS)
            results[IndexName.TEST_NEIGHBORHOODS] = self.create_neighborhood_index(IndexName.TEST_NEIGHBORHOODS)
            results[IndexName.WIKIPEDIA] = self.create_wikipedia_index(IndexName.WIKIPEDIA)
            results[IndexName.TEST_WIKIPEDIA] = self.create_wikipedia_index(IndexName.TEST_WIKIPEDIA)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            self.logger.info(f"Index setup completed: {success_count}/{total_count} successful")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to setup indices: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.CONFIGURATION_ERROR,
                f"Failed to setup indices: {str(e)}"
            )