"""
Configuration loading and management with data subsetting support.

This module handles loading configuration from YAML files and environment variables,
providing a centralized configuration management system for the pipeline with
advanced features like data subsetting and flexible embedding model selection.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from data_pipeline.config.models import PipelineConfig

# Load environment variables from parent directory's .env file
# This allows sharing credentials across all projects in temporal/
parent_env_path = Path(__file__).parent.parent.parent.parent / ".env"
if parent_env_path.exists():
    load_dotenv(parent_env_path)
    logger = logging.getLogger(__name__)
    logger.debug(f"Loaded environment variables from {parent_env_path}")
else:
    # Fall back to local .env if parent doesn't exist
    load_dotenv()
    logger = logging.getLogger(__name__)
    logger.debug("Using local .env file or environment variables")


class ConfigurationManager:
    """Configuration manager with data subsetting and model selection."""
    
    def __init__(self, config_path: Optional[str] = None, environment: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file.
                        If None, uses default or environment variable.
            environment: Environment name (development, staging, production)
        """
        self.config_path = self._resolve_config_path(config_path)
        self.environment = environment or os.getenv("PIPELINE_ENV", "development")
        self._config: Optional[PipelineConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None
    
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """
        Resolve the configuration file path.
        
        Args:
            config_path: User-provided config path
            
        Returns:
            Resolved Path object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if config_path:
            path = Path(config_path)
        else:
            # Check environment variable
            env_path = os.getenv("PIPELINE_CONFIG_PATH")
            if env_path:
                path = Path(env_path)
            else:
                # Try multiple default locations
                possible_paths = [
                    Path("data_pipeline/config.yaml"),  # New comprehensive config
                    Path("data_pipeline/config/pipeline_config.yaml"),  # Legacy location
                    Path("config.yaml"),  # Current directory
                ]
                
                for possible_path in possible_paths:
                    if possible_path.exists():
                        path = possible_path
                        break
                else:
                    # Use first default if none exist
                    path = possible_paths[0]
        
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}, will use defaults")
        
        return path
    
    def load_config(self) -> PipelineConfig:
        """
        Load and validate configuration with environment-specific overrides.
        
        Returns:
            Validated PipelineConfig object
            
        Raises:
            ValidationError: If configuration is invalid
            yaml.YAMLError: If YAML parsing fails
        """
        if self._config is not None:
            return self._config
        
        if self.config_path.exists():
            logger.info(f"Loading configuration from: {self.config_path}")
            
            try:
                with open(self.config_path, "r") as f:
                    self._raw_config = yaml.safe_load(f)
                
                # Merge with environment variables
                self._merge_env_variables()
                
                # Handle embedding model configuration
                self._configure_embedding_models()
                
                # Handle data subsetting configuration
                self._configure_data_subsetting()
                
                # Validate and create config object
                self._config = PipelineConfig(**self._raw_config)
                
                # Apply environment-specific overrides
                if hasattr(self._config, 'apply_environment_overrides'):
                    self._config.apply_environment_overrides(self.environment)
                    logger.info(f"Applied {self.environment} environment overrides")
                
                logger.info(f"Configuration loaded successfully: {self._config.metadata.name} v{self._config.metadata.version}")
                logger.info(f"Environment: {self.environment}")
                
                # Log data subsetting status
                if self._config.data_subset.enabled:
                    logger.info(f"Data subsetting ENABLED: sample_size={self._config.data_subset.sample_size}")
                else:
                    logger.info("Data subsetting DISABLED - using full datasets")
                
                # Log embedding provider
                logger.info(f"Embedding provider: {self._config.embedding.provider}")
                
                return self._config
                
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML configuration: {e}")
                raise
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error loading configuration: {e}")
                raise
        else:
            logger.info("Using default configuration")
            self._config = PipelineConfig()
            return self._config
    
    def _merge_env_variables(self) -> None:
        """
        Merge environment variables into configuration.
        
        Environment variables override config file values.
        Naming convention: PIPELINE_<SECTION>_<KEY>
        """
        if not self._raw_config:
            self._raw_config = {}
        
        # Spark configuration from environment
        if "SPARK_MASTER" in os.environ:
            self._raw_config.setdefault("spark", {})["master"] = os.environ["SPARK_MASTER"]
        
        if "SPARK_APP_NAME" in os.environ:
            self._raw_config.setdefault("spark", {})["app_name"] = os.environ["SPARK_APP_NAME"]
        
        # Embedding configuration from environment
        if "EMBEDDING_PROVIDER" in os.environ:
            self._raw_config.setdefault("embedding", {})["provider"] = os.environ["EMBEDDING_PROVIDER"]
        
        if "EMBEDDING_MODEL" in os.environ:
            self._raw_config.setdefault("embedding", {})["model"] = os.environ["EMBEDDING_MODEL"]
        
        # Data subsetting from environment
        if "DATA_SUBSET_ENABLED" in os.environ:
            enabled = os.environ["DATA_SUBSET_ENABLED"].lower() in ("true", "1", "yes")
            self._raw_config.setdefault("data_subset", {})["enabled"] = enabled
        
        if "DATA_SUBSET_SAMPLE_SIZE" in os.environ:
            self._raw_config.setdefault("data_subset", {})["sample_size"] = int(os.environ["DATA_SUBSET_SAMPLE_SIZE"])
        
        # Output configuration from environment
        if "OUTPUT_PATH" in os.environ:
            self._raw_config.setdefault("output", {})["path"] = os.environ["OUTPUT_PATH"]
        
        if "OUTPUT_FORMAT" in os.environ:
            self._raw_config.setdefault("output", {})["format"] = os.environ["OUTPUT_FORMAT"]
        
        # Output destinations configuration from environment
        if "OUTPUT_DESTINATIONS" in os.environ:
            destinations = os.environ["OUTPUT_DESTINATIONS"].split(",")
            self._raw_config.setdefault("output_destinations", {})["enabled_destinations"] = destinations
        
        # Neo4j configuration from environment
        if "NEO4J_URI" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("neo4j", {})["uri"] = os.environ["NEO4J_URI"]
        if "NEO4J_USERNAME" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("neo4j", {})["username"] = os.environ["NEO4J_USERNAME"]
        if "NEO4J_PASSWORD" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("neo4j", {})["password"] = os.environ["NEO4J_PASSWORD"]
        if "NEO4J_DATABASE" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("neo4j", {})["database"] = os.environ["NEO4J_DATABASE"]
        
        # Elasticsearch configuration from environment
        if "ES_HOSTS" in os.environ:
            hosts = os.environ["ES_HOSTS"].split(",")
            self._raw_config.setdefault("output_destinations", {}).setdefault("elasticsearch", {})["hosts"] = hosts
        if "ES_USERNAME" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("elasticsearch", {})["username"] = os.environ["ES_USERNAME"]
        if "ES_PASSWORD" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("elasticsearch", {})["password"] = os.environ["ES_PASSWORD"]
        if "ES_INDEX_PREFIX" in os.environ:
            self._raw_config.setdefault("output_destinations", {}).setdefault("elasticsearch", {})["index_prefix"] = os.environ["ES_INDEX_PREFIX"]
        
        # Logging level from environment
        if "LOG_LEVEL" in os.environ:
            self._raw_config.setdefault("logging", {})["level"] = os.environ["LOG_LEVEL"]
        
        # Development mode from environment
        if "DEVELOPMENT_MODE" in os.environ:
            dev_mode = os.environ["DEVELOPMENT_MODE"].lower() in ("true", "1", "yes")
            self._raw_config.setdefault("development", {})["debug_mode"] = dev_mode
            self._raw_config.setdefault("development", {})["verbose_logging"] = dev_mode
    
    def _configure_embedding_models(self) -> None:
        """
        Configure embedding models with API key resolution.
        
        Handles both new models configuration and legacy model configuration.
        """
        if not self._raw_config:
            return
        
        embedding_config = self._raw_config.get("embedding", {})
        
        # Handle new models configuration
        if "models" in embedding_config:
            models = embedding_config["models"]
            
            # Resolve API keys from environment for each provider
            for provider in ["voyage", "openai", "gemini"]:
                if provider in models and "api_key" in models[provider]:
                    api_key = models[provider]["api_key"]
                    if api_key and api_key.startswith("${") and api_key.endswith("}"):
                        env_var = api_key[2:-1]
                        actual_key = os.getenv(env_var)
                        if actual_key:
                            models[provider]["api_key"] = actual_key
                        else:
                            logger.warning(f"Environment variable {env_var} not found")
        
        # Handle legacy single model configuration
        elif "model" in embedding_config:
            # For backward compatibility, create models config from legacy format
            provider = embedding_config.get("provider", "ollama")
            model = embedding_config.get("model")
            
            if model:
                models_config = {}
                
                if provider == "voyage":
                    models_config["voyage"] = {
                        "model": model,
                        "api_key": os.getenv("VOYAGE_API_KEY"),
                        "dimension": 1024 if "voyage-3" in model else 1536
                    }
                elif provider == "ollama":
                    models_config["ollama"] = {
                        "model": model,
                        "base_url": embedding_config.get("api_url", "http://localhost:11434"),
                        "dimension": 768 if "nomic" in model else 1024
                    }
                elif provider == "openai":
                    models_config["openai"] = {
                        "model": model,
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        "dimension": 1536 if "small" in model else 3072
                    }
                elif provider == "gemini":
                    models_config["gemini"] = {
                        "model": model,
                        "api_key": os.getenv("GEMINI_API_KEY"),
                        "dimension": 768
                    }
                
                embedding_config["models"] = models_config
    
    def _configure_data_subsetting(self) -> None:
        """
        Configure data subsetting based on environment and flags.
        
        Automatically enables subsetting in development/test environments.
        """
        if not self._raw_config:
            return
        
        # Auto-enable subsetting in development/test modes
        if self.environment in ("development", "test"):
            if "data_subset" not in self._raw_config:
                self._raw_config["data_subset"] = {}
            
            # Set reasonable defaults for development
            if "enabled" not in self._raw_config["data_subset"]:
                self._raw_config["data_subset"]["enabled"] = True
            
            if "sample_size" not in self._raw_config["data_subset"]:
                self._raw_config["data_subset"]["sample_size"] = 20
        
        # Check for test mode flag
        if self._raw_config.get("development", {}).get("test_mode", False):
            if "data_subset" not in self._raw_config:
                self._raw_config["data_subset"] = {}
            
            self._raw_config["data_subset"]["enabled"] = True
            self._raw_config["data_subset"]["sample_size"] = self._raw_config.get("development", {}).get("test_record_limit", 10)
    
    def get_config(self) -> PipelineConfig:
        """
        Get the loaded configuration.
        
        Returns:
            PipelineConfig object
            
        Raises:
            RuntimeError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def reload_config(self) -> PipelineConfig:
        """
        Force reload configuration from file.
        
        Returns:
            Newly loaded PipelineConfig object
        """
        self._config = None
        self._raw_config = None
        return self.load_config()
    
    def save_config(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Output path. If None, overwrites original file.
        """
        if self._config is None:
            raise RuntimeError("No configuration to save")
        
        output_path = Path(path) if path else self.config_path
        
        logger.info(f"Saving configuration to: {output_path}")
        
        with open(output_path, "w") as f:
            yaml.safe_dump(
                self._config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False
            )
    
    def validate_for_production(self) -> bool:
        """
        Validate configuration for production use.
        
        Returns:
            True if configuration is production-ready
        """
        if self._config is None:
            return False
        
        issues = []
        
        # Check Spark configuration
        if self._config.spark.master.startswith("local"):
            issues.append("Spark is configured for local mode")
        
        # Check data sources
        if not self._config.data_sources:
            issues.append("No data sources configured")
        
        # Check data subsetting
        if self._config.data_subset.enabled:
            issues.append("Data subsetting is enabled (should be disabled for production)")
        
        # Check output configuration
        if not self._config.output.path:
            issues.append("No output path configured")
        
        # Check embedding configuration
        if self._config.embedding.provider == "mock":
            issues.append("Mock embedding provider should not be used in production")
        
        # Check development settings
        if self._config.development.test_mode:
            issues.append("Test mode is enabled")
        
        if self._config.development.debug_mode:
            issues.append("Debug mode is enabled")
        
        if issues:
            logger.warning(f"Configuration issues for production: {issues}")
            return False
        
        logger.info("Configuration validated for production use")
        return True
    
    def get_effective_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the effective configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        if self._config is None:
            return {}
        
        return {
            "pipeline": {
                "name": self._config.metadata.name,
                "version": self._config.metadata.version,
                "environment": self.environment
            },
            "spark": {
                "master": self._config.spark.master,
                "memory": self._config.spark.memory
            },
            "data_subsetting": {
                "enabled": self._config.data_subset.enabled,
                "sample_size": self._config.data_subset.sample_size if self._config.data_subset.enabled else "N/A",
                "method": self._config.data_subset.sample_method if self._config.data_subset.enabled else "N/A"
            },
            "embedding": {
                "provider": self._config.embedding.provider,
                "model": self._get_effective_model_name(),
                "batch_size": self._config.embedding.batch_size
            },
            "output": {
                "format": self._config.output.format,
                "path": self._config.output.path
            },
            "processing": {
                "quality_checks": self._config.processing.enable_quality_checks,
                "cache_enabled": self._config.processing.cache_intermediate_results,
                "parallel_tasks": self._config.processing.parallel_tasks
            }
        }
    
    def _get_effective_model_name(self) -> str:
        """Get the effective model name for the current provider."""
        if self._config.embedding.models:
            model_config = self._config.embedding.get_model_config()
            if model_config:
                return model_config.model
        
        # Fall back to legacy model field
        return self._config.embedding.model or "default"


def load_configuration(
    config_path: Optional[str] = None,
    environment: Optional[str] = None
) -> PipelineConfig:
    """
    Convenience function to load configuration.
    
    Args:
        config_path: Optional path to configuration file
        environment: Optional environment name
        
    Returns:
        Loaded and validated PipelineConfig
    """
    manager = ConfigurationManager(config_path, environment)
    return manager.load_config()


def create_test_configuration(
    sample_size: int = 10,
    provider: str = "mock"
) -> PipelineConfig:
    """
    Create a test configuration with minimal data.
    
    Args:
        sample_size: Number of records to sample
        provider: Embedding provider to use
        
    Returns:
        Test configuration
    """
    config = PipelineConfig()
    
    # Enable data subsetting
    config.data_subset.enabled = True
    config.data_subset.sample_size = sample_size
    
    # Use mock embeddings for speed
    config.embedding.provider = provider
    
    # Enable test mode
    config.development.test_mode = True
    config.development.test_record_limit = sample_size
    
    # Disable caching for tests
    config.processing.cache_intermediate_results = False
    
    return config