"""
Dependency injection container for the real estate search application.
Creates and wires all application objects with constructor injection.
"""

from pathlib import Path
from elasticsearch import Elasticsearch
import logging

from config.config import AppConfig
from infrastructure.elasticsearch_client import ElasticsearchClientFactory
from infrastructure.database import DatabaseConnection
from repositories.wikipedia_repository import WikipediaRepository
from repositories.property_repository import PropertyRepository
from services.enrichment_service import EnrichmentService
from services.indexing_service import IndexingService
from services.search_service import SearchService
from ingestion.orchestrator import IngestionOrchestrator

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
        self._database = self._create_database_connection()
        
        # Create repositories
        self._wikipedia_repository = self._create_wikipedia_repository()
        self._property_repository = self._create_property_repository()
        
        # Create services
        self._enrichment_service = self._create_enrichment_service()
        self._indexing_service = self._create_indexing_service()
        self._search_service = self._create_search_service()
        
        # Create orchestrator
        self._ingestion_orchestrator = self._create_ingestion_orchestrator()
        
        logger.info("Dependency container initialized successfully")
    
    def _create_elasticsearch_client(self) -> Elasticsearch:
        """Create Elasticsearch client using factory."""
        logger.debug("Creating Elasticsearch client")
        factory = ElasticsearchClientFactory(self.config.elasticsearch)
        return factory.create_client()
    
    def _create_database_connection(self) -> DatabaseConnection:
        """Create database connection for Wikipedia data."""
        logger.debug(f"Creating database connection for {self.config.data.wikipedia_db}")
        return DatabaseConnection(self.config.data.wikipedia_db)
    
    def _create_wikipedia_repository(self) -> WikipediaRepository:
        """Create Wikipedia repository with database connection."""
        logger.debug("Creating Wikipedia repository")
        return WikipediaRepository(self._database)
    
    def _create_property_repository(self) -> PropertyRepository:
        """Create property repository with Elasticsearch client."""
        logger.debug(f"Creating property repository for index {self.config.elasticsearch.property_index}")
        return PropertyRepository(
            es_client=self._es_client,
            index_name=self.config.elasticsearch.property_index
        )
    
    def _create_enrichment_service(self) -> EnrichmentService:
        """Create enrichment service with Wikipedia repository."""
        logger.debug("Creating enrichment service")
        return EnrichmentService(
            wikipedia_repository=self._wikipedia_repository
        )
    
    def _create_indexing_service(self) -> IndexingService:
        """Create indexing service with repositories and services."""
        logger.debug("Creating indexing service")
        return IndexingService(
            property_repository=self._property_repository,
            enrichment_service=self._enrichment_service
        )
    
    def _create_search_service(self) -> SearchService:
        """Create search service with property repository."""
        logger.debug("Creating search service")
        return SearchService(
            property_repository=self._property_repository
        )
    
    def _create_ingestion_orchestrator(self) -> IngestionOrchestrator:
        """Create ingestion orchestrator with indexing service."""
        logger.debug("Creating ingestion orchestrator")
        return IngestionOrchestrator(
            indexing_service=self._indexing_service,
            properties_dir=self.config.data.properties_dir
        )
    
    # Public accessors for services
    
    @property
    def elasticsearch_client(self) -> Elasticsearch:
        """Get Elasticsearch client for administrative operations."""
        return self._es_client
    
    @property
    def indexing_service(self) -> IndexingService:
        """Get indexing service for property indexing operations."""
        return self._indexing_service
    
    @property
    def search_service(self) -> SearchService:
        """Get search service for property search operations."""
        return self._search_service
    
    @property
    def enrichment_service(self) -> EnrichmentService:
        """Get enrichment service for Wikipedia data enrichment."""
        return self._enrichment_service
    
    @property
    def ingestion_orchestrator(self) -> IngestionOrchestrator:
        """Get ingestion orchestrator for bulk data ingestion."""
        return self._ingestion_orchestrator
    
    @property
    def property_repository(self) -> PropertyRepository:
        """Get property repository for direct property data access."""
        return self._property_repository
    
    @property
    def wikipedia_repository(self) -> WikipediaRepository:
        """Get Wikipedia repository for direct Wikipedia data access."""
        return self._wikipedia_repository