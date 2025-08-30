"""Health check service for monitoring system status."""

import os
from datetime import datetime
from typing import Dict, Any, Literal

from ..settings import MCPServerConfig
from ..models.search import HealthCheckResponse
from .elasticsearch_client import ElasticsearchClient
from ..utils.logging import get_logger


logger = get_logger(__name__)


class HealthCheckService:
    """Service for checking system health."""
    
    def __init__(self, config: MCPServerConfig, es_client: ElasticsearchClient):
        """Initialize health check service.
        
        Args:
            config: Server configuration
            es_client: Elasticsearch client
        """
        self.config = config
        self.es_client = es_client
    
    def check_elasticsearch(self) -> Dict[str, Any]:
        """Check Elasticsearch health.
        
        Returns:
            Elasticsearch health status
        """
        try:
            # Check if reachable
            if not self.es_client.ping():
                return {
                    "status": "unhealthy",
                    "message": "Cannot reach Elasticsearch",
                    "reachable": False
                }
            
            # Get cluster health
            health = self.es_client.get_cluster_health()
            
            # Check indices exist
            properties_exists = self.es_client.index_exists(
                self.config.elasticsearch.property_index
            )
            
            # Count documents
            property_count = 0
            if properties_exists:
                try:
                    property_count = self.es_client.count(
                        self.config.elasticsearch.property_index
                    )
                except Exception as e:
                    logger.warning(f"Failed to count properties: {e}")
            
            return {
                "status": "healthy" if health["status"] in ["yellow", "green"] else "degraded",
                "message": f"Cluster status: {health['status']}",
                "reachable": True,
                "cluster_status": health["status"],
                "nodes": health["number_of_nodes"],
                "indices": {
                    "properties": {
                        "exists": properties_exists,
                        "document_count": property_count
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "reachable": False
            }
    
    def check_embedding_service(self) -> Dict[str, Any]:
        """Check embedding service configuration.
        
        Returns:
            Embedding service status
        """
        try:
            provider = self.config.embedding.provider
            
            # Check API key presence for providers that need it
            api_key_required = provider in ["voyage", "openai", "gemini"]
            api_key_present = bool(self.config.embedding.api_key)
            
            if api_key_required and not api_key_present:
                return {
                    "status": "unhealthy",
                    "message": f"API key missing for {provider}",
                    "provider": provider,
                    "configured": False
                }
            
            return {
                "status": "healthy",
                "message": f"Embedding service configured",
                "provider": provider,
                "model": self.config.embedding.model_name,
                "dimension": self.config.embedding.dimension,
                "configured": True
            }
            
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "configured": False
            }
    
    def check_configuration(self) -> Dict[str, Any]:
        """Check configuration validity.
        
        Returns:
            Configuration status
        """
        try:
            # Check search configuration
            valid_config = (
                0 <= self.config.search.vector_weight <= 1 and
                0 <= self.config.search.text_weight <= 1 and
                self.config.search.default_size > 0 and
                self.config.search.max_size >= self.config.search.default_size
            )
            
            if not valid_config:
                return {
                    "status": "degraded",
                    "message": "Invalid configuration values",
                    "valid": False
                }
            
            return {
                "status": "healthy",
                "message": "Configuration valid",
                "valid": True,
                "debug_mode": self.config.debug,
                "server_name": self.config.server_name,
                "server_version": self.config.server_version
            }
            
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "valid": False
            }
    
    def get_overall_status(
        self,
        services: Dict[str, Dict[str, Any]]
    ) -> Literal["healthy", "degraded", "unhealthy"]:
        """Determine overall system status.
        
        Args:
            services: Individual service statuses
            
        Returns:
            Overall status
        """
        statuses = [service["status"] for service in services.values()]
        
        if all(s == "healthy" for s in statuses):
            return "healthy"
        elif any(s == "unhealthy" for s in statuses):
            return "unhealthy"
        else:
            return "degraded"
    
    def perform_health_check(self) -> HealthCheckResponse:
        """Perform complete health check.
        
        Returns:
            Health check response
        """
        logger.info("Performing health check")
        
        # Check individual services
        services = {
            "elasticsearch": self.check_elasticsearch(),
            "embedding": self.check_embedding_service(),
            "configuration": self.check_configuration()
        }
        
        # Determine overall status
        overall_status = self.get_overall_status(services)
        
        # Create response
        response = HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            services=services,
            version=self.config.server_version
        )
        
        logger.info(f"Health check complete: {overall_status}")
        return response