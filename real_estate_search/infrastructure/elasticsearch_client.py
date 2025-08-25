"""
Elasticsearch client factory with constructor injection.
Creates configured Elasticsearch clients.
"""

from elasticsearch import Elasticsearch
import logging

from config.config import ElasticsearchConfig

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