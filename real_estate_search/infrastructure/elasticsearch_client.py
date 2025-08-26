"""
Elasticsearch client factory with constructor injection.
Creates configured Elasticsearch clients with index management capabilities.
"""

from elasticsearch import Elasticsearch
from typing import Dict, Any, List
import logging

from ..config.config import ElasticsearchConfig

logger = logging.getLogger(__name__)


class ElasticsearchClientFactory:
    """
    Factory for creating Elasticsearch clients.
    All configuration is injected through constructor.
    """
    
    def __init__(self, config: ElasticsearchConfig):
        """
        Initialize factory with Elasticsearch configuration.
        
        Args:
            config: Elasticsearch configuration object
        """
        self.config = config
        logger.info(f"Initialized Elasticsearch factory for {config.host}:{config.port}")
    
    def create_client(self) -> Elasticsearch:
        """
        Create a configured Elasticsearch client.
        
        Returns:
            Configured Elasticsearch client ready for use
        """
        # Build connection configuration
        if self.config.cloud_id:
            # Elastic Cloud configuration
            client_config = {
                "cloud_id": self.config.cloud_id,
                "request_timeout": self.config.request_timeout
            }
            
            # Add authentication
            if self.config.api_key:
                client_config["api_key"] = self.config.api_key
            elif self.config.username and self.config.password:
                client_config["basic_auth"] = (self.config.username, self.config.password)
            
            logger.info("Creating Elasticsearch client for Elastic Cloud")
        else:
            # Standard Elasticsearch configuration
            url = f"http://{self.config.host}:{self.config.port}"
            client_config = {
                "hosts": [url],
                "request_timeout": self.config.request_timeout,
                "verify_certs": self.config.verify_certs
            }
            
            # Add authentication if provided
            if self.config.api_key:
                client_config["api_key"] = self.config.api_key
            elif self.config.username and self.config.password:
                client_config["basic_auth"] = (self.config.username, self.config.password)
            
            logger.info(f"Creating Elasticsearch client for {url}")
        
        # Create and return client
        client = Elasticsearch(**client_config)
        
        # Verify connection
        if client.ping():
            logger.info("Elasticsearch client connected successfully")
        else:
            logger.warning("Elasticsearch client created but ping failed")
        
        return client


class ElasticsearchClient:
    """
    Enhanced Elasticsearch client with index management capabilities.
    Provides methods for template registration and index creation.
    """
    
    def __init__(self, client: Elasticsearch):
        """
        Initialize enhanced Elasticsearch client.
        
        Args:
            client: Configured Elasticsearch client
        """
        self.client = client
        self.logger = logging.getLogger(__name__)
    
    def register_index_template(self, name: str, template_body: Dict[str, Any]) -> bool:
        """
        Register an index template.
        
        Args:
            name: Template name
            template_body: Template configuration
            
        Returns:
            True if template was registered successfully
        """
        try:
            self.client.indices.put_index_template(
                name=name,
                body=template_body
            )
            self.logger.info(f"Successfully registered index template: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register template {name}: {str(e)}")
            raise
    
    def create_index_with_mappings(self, index_name: str, mappings_config: Dict[str, Any]) -> bool:
        """
        Create index with explicit mappings and settings.
        
        Args:
            index_name: Name of the index to create
            mappings_config: Complete mappings configuration including settings
            
        Returns:
            True if index was created successfully
        """
        try:
            # Check if index already exists
            if self.client.indices.exists(index=index_name):
                self.logger.info(f"Index {index_name} already exists")
                return True
            
            # Create the index
            self.client.indices.create(
                index=index_name,
                body=mappings_config
            )
            
            self.logger.info(f"Successfully created index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise
    
    def get_index_mapping(self, index_name: str) -> Dict[str, Any]:
        """
        Get current mapping for an index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index mapping dictionary
        """
        try:
            if not self.client.indices.exists(index=index_name):
                raise ValueError(f"Index {index_name} does not exist")
            
            return self.client.indices.get_mapping(index=index_name)
            
        except Exception as e:
            self.logger.error(f"Failed to get mapping for {index_name}: {str(e)}")
            raise
    
    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """
        Get statistics for an index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index statistics dictionary
        """
        try:
            if not self.client.indices.exists(index=index_name):
                raise ValueError(f"Index {index_name} does not exist")
            
            return self.client.indices.stats(index=index_name)
            
        except Exception as e:
            self.logger.error(f"Failed to get stats for {index_name}: {str(e)}")
            raise
    
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
                self.logger.info(f"Index {index_name} does not exist")
                return True
            
            self.client.indices.delete(index=index_name)
            self.logger.info(f"Successfully deleted index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete index {index_name}: {str(e)}")
            raise
    
    def list_indices(self, pattern: str = "*") -> List[str]:
        """
        List all indices matching pattern.
        
        Args:
            pattern: Index name pattern to match
            
        Returns:
            List of matching index names
        """
        try:
            response = self.client.cat.indices(index=pattern, format="json")
            return [index["index"] for index in response]
            
        except Exception as e:
            self.logger.error(f"Failed to list indices: {str(e)}")
            raise
    
    def ping(self) -> bool:
        """
        Check if Elasticsearch is reachable.
        
        Returns:
            True if connection is successful
        """
        return self.client.ping()
    
    def get_cluster_health(self, index: str = None) -> Dict[str, Any]:
        """
        Get cluster health information.
        
        Args:
            index: Optional index to check health for
            
        Returns:
            Cluster health information
        """
        try:
            return self.client.cluster.health(index=index)
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster health: {str(e)}")
            raise