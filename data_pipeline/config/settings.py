"""
Configuration loading and management.

This module handles loading configuration from YAML files and environment variables,
providing a centralized configuration management system for the pipeline.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from data_pipeline.config.models import PipelineConfig

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Manages pipeline configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file.
                        If None, uses default or environment variable.
        """
        self.config_path = self._resolve_config_path(config_path)
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
                # Default location
                path = Path(__file__).parent / "pipeline_config.yaml"
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        return path
    
    def load_config(self) -> PipelineConfig:
        """
        Load and validate configuration.
        
        Returns:
            Validated PipelineConfig object
            
        Raises:
            ValidationError: If configuration is invalid
            yaml.YAMLError: If YAML parsing fails
        """
        if self._config is not None:
            return self._config
        
        logger.info(f"Loading configuration from: {self.config_path}")
        
        try:
            with open(self.config_path, "r") as f:
                self._raw_config = yaml.safe_load(f)
            
            # Merge with environment variables
            self._merge_env_variables()
            
            # Validate and create config object
            self._config = PipelineConfig(**self._raw_config)
            
            logger.info(f"Configuration loaded successfully: {self._config.name} v{self._config.version}")
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
    
    def _merge_env_variables(self) -> None:
        """
        Merge environment variables into configuration.
        
        Environment variables override config file values.
        Naming convention: PIPELINE_<SECTION>_<KEY>
        """
        if not self._raw_config:
            return
        
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
        
        if "EMBEDDING_API_KEY" in os.environ:
            self._raw_config.setdefault("embedding", {})["api_key"] = os.environ["EMBEDDING_API_KEY"]
        
        # Output configuration from environment
        if "OUTPUT_PATH" in os.environ:
            self._raw_config.setdefault("output", {})["path"] = os.environ["OUTPUT_PATH"]
        
        if "OUTPUT_FORMAT" in os.environ:
            self._raw_config.setdefault("output", {})["format"] = os.environ["OUTPUT_FORMAT"]
        
        # Logging level from environment
        if "LOG_LEVEL" in os.environ:
            self._raw_config.setdefault("logging", {})["level"] = os.environ["LOG_LEVEL"]
    
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
        if self._config.spark.master == "local[*]":
            issues.append("Spark is configured for local mode")
        
        # Check data sources
        if not self._config.data_sources:
            issues.append("No data sources configured")
        
        # Check output configuration
        if not self._config.output.path:
            issues.append("No output path configured")
        
        # Check embedding configuration
        if self._config.embedding.provider == "ollama" and not self._config.embedding.api_url:
            issues.append("Ollama provider requires API URL")
        
        if issues:
            logger.warning(f"Configuration issues for production: {issues}")
            return False
        
        return True


def load_configuration(config_path: Optional[str] = None) -> PipelineConfig:
    """
    Convenience function to load configuration.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Loaded and validated PipelineConfig
    """
    manager = ConfigurationManager(config_path)
    return manager.load_config()