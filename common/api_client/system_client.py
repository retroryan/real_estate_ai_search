"""System API Client Implementation."""

import logging
from typing import Dict, Any
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: float
    components: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]


class RootInfo(BaseModel):
    """Root endpoint response model."""
    name: str
    version: str
    description: str
    docs_url: str
    health_url: str


from .base import BaseAPIClient
from .config import APIClientConfig
from .exceptions import APIError


class SystemAPIClient(BaseAPIClient):
    """API client for system health and information endpoints."""
    
    def __init__(self, config: APIClientConfig, logger: logging.Logger):
        """Initialize the System API client.
        
        Args:
            config: API client configuration
            logger: Logger instance for structured logging
        """
        super().__init__(config, logger)
        self.logger.info(
            "Initialized System API client",
            extra={"base_url": str(config.base_url)}
        )
    
    def get_health(self) -> HealthStatus:
        """Get health status of the API.
        
        Checks the actual availability and accessibility of all data sources including
        property JSON files, Wikipedia database, and directory structures.
        
        Returns:
            Health status information including:
            - Overall status (healthy/degraded/unhealthy)
            - Component-level health status
            - Basic system information
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Checking API health status")
        
        # Make request to health endpoint
        response_data = self.get("health")
        
        # Parse response
        health = HealthStatus(**response_data)
        
        self.logger.info(
            "Retrieved health status",
            extra={
                "status": health.status,
                "healthy_components": health.summary.get("healthy_components", 0),
                "total_components": health.summary.get("total_components", 0)
            }
        )
        
        return health
    
    def get_root_info(self) -> RootInfo:
        """Get root API information.
        
        Returns basic API information including version, documentation URLs, etc.
        This uses a special path that goes to the root of the API server.
        
        Returns:
            Root API information
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug("Fetching root API information")
        
        # Make request to root endpoint - special handling needed
        # Since base_url likely includes /api/v1, we need to go up to root
        original_base = str(self.config.base_url)
        
        # Extract the root URL (everything before /api)
        if "/api" in original_base:
            root_url = original_base.split("/api")[0]
        else:
            root_url = original_base
        
        # Temporarily create a client with root URL
        temp_config = APIClientConfig(
            base_url=root_url,
            timeout=self.config.timeout,
            default_headers=self.config.default_headers
        )
        
        # Use parent class methods directly with adjusted URL
        response = self._http_client.request(
            "GET",
            root_url.rstrip('/') + '/',
            timeout=self.config.timeout
        )
        response.raise_for_status()
        response_data = response.json()
        
        # Parse response
        root_info = RootInfo(**response_data)
        
        self.logger.info(
            "Retrieved root API information",
            extra={
                "name": root_info.name,
                "version": root_info.version
            }
        )
        
        return root_info
    
    def check_readiness(self) -> bool:
        """Check if the API is ready to serve requests.
        
        This is a simplified health check that just returns whether the API
        is in a healthy or degraded state (but still functional).
        
        Returns:
            True if API is ready (healthy or degraded), False if unhealthy
            
        Raises:
            APIError: If request fails completely
        """
        self.logger.debug("Checking API readiness")
        
        try:
            health = self.get_health()
            is_ready = health.status in ["healthy", "degraded"]
            
            self.logger.info(
                f"API readiness check: {'ready' if is_ready else 'not ready'}",
                extra={"status": health.status}
            )
            
            return is_ready
            
        except Exception as e:
            self.logger.error(
                f"API readiness check failed: {str(e)}",
                extra={"error": str(e)}
            )
            return False
    
    def get_component_health(self, component_name: str) -> Dict[str, Any]:
        """Get health status of a specific component.
        
        Args:
            component_name: Name of the component to check
                           (e.g., "property_data_directory", "wikipedia_database")
        
        Returns:
            Component health information
            
        Raises:
            APIError: If request fails
            KeyError: If component not found
        """
        self.logger.debug(
            "Checking component health",
            extra={"component": component_name}
        )
        
        health = self.get_health()
        
        if component_name not in health.components:
            raise KeyError(f"Component '{component_name}' not found in health status")
        
        component_health = health.components[component_name]
        
        self.logger.info(
            f"Component '{component_name}' health status",
            extra={
                "component": component_name,
                "status": component_health.get("status", "unknown")
            }
        )
        
        return component_health