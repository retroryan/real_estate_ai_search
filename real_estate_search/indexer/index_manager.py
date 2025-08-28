"""
Index management module for Elasticsearch operations.
Handles index creation, template registration, and mapping management.
"""

from typing import Dict, Any, List
import logging
from elasticsearch import Elasticsearch
from pydantic import BaseModel

from .mappings import (
    get_property_mappings, 
    get_neighborhood_mappings, 
    get_wikipedia_mappings,
    get_property_relationships_mappings
)
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
    
    def create_property_relationships_index(self, index_name: str = IndexName.PROPERTY_RELATIONSHIPS) -> bool:
        """
        Create property relationships index with proper mappings.
        
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
            
            # Get mappings for property relationships index
            mappings_config = get_property_relationships_mappings()
            
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
            index_patterns=["properties*"],
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
            index_patterns=["neighborhoods*"],
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
            index_patterns=["wikipedia*"],
            settings=mappings_config["settings"],
            mappings=mappings_config["mappings"],
            priority=100
        )
        
        return self.register_index_template(template)
    
    def create_property_relationships_template(self) -> bool:
        """
        Create and register property relationships index template.
        
        Returns:
            True if template was created successfully
        """
        mappings_config = get_property_relationships_mappings()
        
        template = IndexTemplate(
            name="property_relationships_template",
            index_patterns=["property_relationships*"],
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
            IndexName.TEST_WIKIPEDIA,
            IndexName.PROPERTY_RELATIONSHIPS,
            IndexName.TEST_PROPERTY_RELATIONSHIPS
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
    
    def populate_property_relationships_index(self) -> bool:
        """
        Populate property_relationships index from existing indices.
        Called after setup-indices to build denormalized documents.
        
        Returns:
            True if relationships were populated successfully
        """
        from .relationship_builder import PropertyRelationshipBuilder, RelationshipBuilderConfig
        
        self.logger.info("Starting property relationships population...")
        
        try:
            # Check that required indices exist and have data
            required_indices = [IndexName.PROPERTIES, IndexName.NEIGHBORHOODS, IndexName.WIKIPEDIA]
            for index in required_indices:
                if not self.client.indices.exists(index=index):
                    self.logger.error(f"Required index '{index}' does not exist")
                    return False
                
                count = self.client.count(index=index)["count"]
                if count == 0:
                    self.logger.warning(f"Index '{index}' is empty")
                else:
                    self.logger.info(f"  {index}: {count} documents")
            
            # Ensure property_relationships index exists
            if not self.client.indices.exists(index=IndexName.PROPERTY_RELATIONSHIPS):
                self.logger.info("Creating property_relationships index...")
                success = self.create_property_relationships_index(IndexName.PROPERTY_RELATIONSHIPS)
                if not success:
                    self.logger.error("Failed to create property_relationships index")
                    return False
            
            # Build relationships using the relationship builder
            config = RelationshipBuilderConfig(
                batch_size=50,  # Smaller batches for stability
                max_wikipedia_articles=3,
                enable_combined_text=True
            )
            
            builder = PropertyRelationshipBuilder(self.client, config)
            total_created = builder.build_all_relationships()
            
            if total_created > 0:
                self.logger.info(f"✅ Successfully created {total_created} relationship documents")
                
                # Verify final count
                final_count = self.client.count(index=IndexName.PROPERTY_RELATIONSHIPS)["count"]
                self.logger.info(f"✅ property_relationships index now has {final_count} documents")
                return True
            else:
                self.logger.warning("No relationship documents were created")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to populate property relationships: {str(e)}")
            raise ElasticsearchIndexError(
                ErrorCode.CONFIGURATION_ERROR,
                f"Failed to populate property relationships: {str(e)}"
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
            results["property_relationships_template"] = self.create_property_relationships_template()
            
            # Then create indices
            self.logger.info("Creating indices...")
            results[IndexName.PROPERTIES] = self.create_property_index(IndexName.PROPERTIES)
            results[IndexName.TEST_PROPERTIES] = self.create_property_index(IndexName.TEST_PROPERTIES)
            results[IndexName.NEIGHBORHOODS] = self.create_neighborhood_index(IndexName.NEIGHBORHOODS)
            results[IndexName.TEST_NEIGHBORHOODS] = self.create_neighborhood_index(IndexName.TEST_NEIGHBORHOODS)
            results[IndexName.WIKIPEDIA] = self.create_wikipedia_index(IndexName.WIKIPEDIA)
            results[IndexName.TEST_WIKIPEDIA] = self.create_wikipedia_index(IndexName.TEST_WIKIPEDIA)
            results[IndexName.PROPERTY_RELATIONSHIPS] = self.create_property_relationships_index(IndexName.PROPERTY_RELATIONSHIPS)
            results[IndexName.TEST_PROPERTY_RELATIONSHIPS] = self.create_property_relationships_index(IndexName.TEST_PROPERTY_RELATIONSHIPS)
            
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