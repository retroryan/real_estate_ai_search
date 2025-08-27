"""
Dependency injection container for the real estate search application.
Creates and wires all application objects with constructor injection.
"""

from pathlib import Path
from elasticsearch import Elasticsearch
import logging

from real_estate_search.config import AppConfig
from real_estate_search.infrastructure.elasticsearch_client import ElasticsearchClientFactory
from real_estate_search.repositories.property_repository import PropertyRepository
from real_estate_search.services.search_service import SearchService

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Central dependency injection container.
    Creates and wires all application objects with proper constructor injection.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize container with application configuration.
        
        Args:
            config: Complete application configuration
        """
        self.config = config
        logger.info("Initializing dependency container")
        
        # Create infrastructure components
        self._es_client = self._create_elasticsearch_client()
        
        # Create repositories
        self._property_repository = self._create_property_repository()
        
        # Create services
        self._search_service = self._create_search_service()
        
        logger.info("Dependency container initialized successfully")
    
    def _create_elasticsearch_client(self) -> Elasticsearch:
        """Create Elasticsearch client using factory."""
        logger.debug("Creating Elasticsearch client")
        factory = ElasticsearchClientFactory(self.config.elasticsearch)
        return factory.create_client()
    
    def _create_property_repository(self) -> PropertyRepository:
        """Create property repository with Elasticsearch client."""
        logger.debug(f"Creating property repository for index {self.config.elasticsearch.property_index}")
        return PropertyRepository(
            es_client=self._es_client,
            index_name=self.config.elasticsearch.property_index
        )
    
    def _create_search_service(self) -> SearchService:
        """Create search service with property repository."""
        logger.debug("Creating search service")
        return SearchService(
            property_repository=self._property_repository
        )
    
    # Public accessors for services
    
    @property
    def elasticsearch_client(self) -> Elasticsearch:
        """Get Elasticsearch client for administrative operations."""
        return self._es_client
    
    @property
    def search_service(self) -> SearchService:
        """Get search service for property search operations."""
        return self._search_service
    
    @property
    def property_repository(self) -> PropertyRepository:
        """Get property repository for direct property data access."""
        return self._property_repository