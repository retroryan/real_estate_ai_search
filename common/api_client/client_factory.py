"""API Client Factory for easy client creation and management."""

import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .config import APIClientConfig
from .config_loader import ConfigLoader
from .property_client import PropertyAPIClient
from .wikipedia_client import WikipediaAPIClient
from .stats_client import StatsAPIClient
from .system_client import SystemAPIClient


class APIClientFactory:
    """Factory for creating and managing API clients.
    
    This factory provides convenient methods to create configured API clients
    for all available endpoints. It handles configuration loading, logging setup,
    and client instantiation.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the API Client Factory.
        
        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            config_path: Path to YAML configuration file
            config_dict: Configuration dictionary
            logger: Logger instance (creates default if not provided)
            
        Note:
            Provide either base_url, config_path, or config_dict.
            Priority: config_dict > config_path > base_url
        """
        self.logger = logger or self._create_default_logger()
        
        # Load configuration based on provided parameters
        if config_dict:
            self.base_config = ConfigLoader.load_from_dict(config_dict)
        elif config_path:
            self.base_config = ConfigLoader.load_from_yaml(config_path)
        elif base_url:
            self.base_config = APIClientConfig(base_url=base_url)
        else:
            # Default to localhost
            self.base_config = APIClientConfig(base_url="http://localhost:8000")
        
        # Store individual client configurations
        self._property_config = None
        self._wikipedia_config = None
        self._stats_config = None
        self._system_config = None
        
        # Store client instances for reuse
        self._property_client = None
        self._wikipedia_client = None
        self._stats_client = None
        self._system_client = None
    
    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger for the factory."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _get_endpoint_config(self, endpoint_path: str) -> APIClientConfig:
        """Get configuration for a specific endpoint.
        
        Args:
            endpoint_path: Path to append to base URL (e.g., "/api/v1")
            
        Returns:
            APIClientConfig for the endpoint
        """
        base_url = str(self.base_config.base_url).rstrip('/')
        endpoint_url = f"{base_url}{endpoint_path}"
        
        return APIClientConfig(
            base_url=endpoint_url,
            timeout=self.base_config.timeout,
            default_headers=self.base_config.default_headers
        )
    
    @property
    def property_client(self) -> PropertyAPIClient:
        """Get or create a Property API client.
        
        Returns:
            Configured PropertyAPIClient instance
        """
        if self._property_client is None:
            if self._property_config is None:
                self._property_config = self._get_endpoint_config("/api/v1")
            self._property_client = PropertyAPIClient(self._property_config, self.logger)
        return self._property_client
    
    @property
    def wikipedia_client(self) -> WikipediaAPIClient:
        """Get or create a Wikipedia API client.
        
        Returns:
            Configured WikipediaAPIClient instance
        """
        if self._wikipedia_client is None:
            if self._wikipedia_config is None:
                self._wikipedia_config = self._get_endpoint_config("/api/v1/wikipedia")
            self._wikipedia_client = WikipediaAPIClient(self._wikipedia_config, self.logger)
        return self._wikipedia_client
    
    @property
    def stats_client(self) -> StatsAPIClient:
        """Get or create a Statistics API client.
        
        Returns:
            Configured StatsAPIClient instance
        """
        if self._stats_client is None:
            if self._stats_config is None:
                self._stats_config = self._get_endpoint_config("/api/v1")
            self._stats_client = StatsAPIClient(self._stats_config, self.logger)
        return self._stats_client
    
    @property
    def system_client(self) -> SystemAPIClient:
        """Get or create a System API client.
        
        Returns:
            Configured SystemAPIClient instance
        """
        if self._system_client is None:
            if self._system_config is None:
                self._system_config = self._get_endpoint_config("/api/v1")
            self._system_client = SystemAPIClient(self._system_config, self.logger)
        return self._system_client
    
    def create_property_client(
        self,
        config: Optional[APIClientConfig] = None
    ) -> PropertyAPIClient:
        """Create a new Property API client with optional custom configuration.
        
        Args:
            config: Optional custom configuration
            
        Returns:
            New PropertyAPIClient instance
        """
        if config is None:
            config = self._get_endpoint_config("/api/v1")
        return PropertyAPIClient(config, self.logger)
    
    def create_wikipedia_client(
        self,
        config: Optional[APIClientConfig] = None
    ) -> WikipediaAPIClient:
        """Create a new Wikipedia API client with optional custom configuration.
        
        Args:
            config: Optional custom configuration
            
        Returns:
            New WikipediaAPIClient instance
        """
        if config is None:
            config = self._get_endpoint_config("/api/v1/wikipedia")
        return WikipediaAPIClient(config, self.logger)
    
    def create_stats_client(
        self,
        config: Optional[APIClientConfig] = None
    ) -> StatsAPIClient:
        """Create a new Statistics API client with optional custom configuration.
        
        Args:
            config: Optional custom configuration
            
        Returns:
            New StatsAPIClient instance
        """
        if config is None:
            config = self._get_endpoint_config("/api/v1")
        return StatsAPIClient(config, self.logger)
    
    def create_system_client(
        self,
        config: Optional[APIClientConfig] = None
    ) -> SystemAPIClient:
        """Create a new System API client with optional custom configuration.
        
        Args:
            config: Optional custom configuration
            
        Returns:
            New SystemAPIClient instance
        """
        if config is None:
            config = self._get_endpoint_config("/api/v1")
        return SystemAPIClient(config, self.logger)
    
    def check_health(self) -> bool:
        """Check if the API is healthy and ready.
        
        Returns:
            True if API is healthy or degraded, False if unhealthy
        """
        try:
            return self.system_client.check_readiness()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all statistics from the API.
        
        Returns:
            Dictionary containing all statistics
        """
        return self.stats_client.get_all_stats()
    
    @classmethod
    def from_yaml(
        cls,
        config_path: Union[str, Path],
        section: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> "APIClientFactory":
        """Create factory from YAML configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            section: Optional section name in YAML file
            logger: Optional logger instance
            
        Returns:
            Configured APIClientFactory instance
        """
        config = ConfigLoader.load_from_yaml(config_path, section)
        return cls(
            config_dict=config.model_dump() if hasattr(config, 'model_dump') else dict(config),
            logger=logger
        )
    
    @classmethod
    def from_env(
        cls,
        env_prefix: str = "API",
        logger: Optional[logging.Logger] = None
    ) -> "APIClientFactory":
        """Create factory from environment variables.
        
        Args:
            env_prefix: Prefix for environment variables (e.g., API_BASE_URL)
            logger: Optional logger instance
            
        Returns:
            Configured APIClientFactory instance
        """
        import os
        
        base_url = os.getenv(f"{env_prefix}_BASE_URL", "http://localhost:8000")
        timeout = int(os.getenv(f"{env_prefix}_TIMEOUT", "30"))
        
        config_dict = {
            "base_url": base_url,
            "timeout": timeout
        }
        
        # Check for optional headers
        api_key = os.getenv(f"{env_prefix}_KEY")
        if api_key:
            config_dict["default_headers"] = {"Authorization": f"Bearer {api_key}"}
        
        return cls(config_dict=config_dict, logger=logger)
    
    @classmethod
    def for_local_development(
        cls,
        port: int = 8000,
        logger: Optional[logging.Logger] = None
    ) -> "APIClientFactory":
        """Create factory configured for local development.
        
        Args:
            port: Port number for local API server
            logger: Optional logger instance
            
        Returns:
            APIClientFactory configured for localhost
        """
        return cls(
            base_url=f"http://localhost:{port}",
            logger=logger
        )
    
    @classmethod
    def for_production(
        cls,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
        logger: Optional[logging.Logger] = None
    ) -> "APIClientFactory":
        """Create factory configured for production use.
        
        Args:
            api_url: Production API URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            logger: Optional logger instance
            
        Returns:
            APIClientFactory configured for production
        """
        config_dict = {
            "base_url": api_url,
            "timeout": timeout
        }
        
        if api_key:
            config_dict["default_headers"] = {"Authorization": f"Bearer {api_key}"}
        
        return cls(config_dict=config_dict, logger=logger)