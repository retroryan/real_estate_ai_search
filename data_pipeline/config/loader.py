"""
Configuration loading module for the data pipeline.

This module provides a simple function to load configuration from YAML files,
apply environment variable overrides for secrets, and return a validated
PipelineConfig object.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from data_pipeline.config.models import PipelineConfig


def load_configuration(config_path: Optional[str] = None, sample_size: Optional[int] = None) -> PipelineConfig:
    """
    Load pipeline configuration with clear precedence.
    
    Precedence order:
    1. sample_size from argument (if provided)
    2. Environment variables (for secrets/API keys only)
    3. YAML configuration file
    4. Pydantic model defaults
    
    Args:
        config_path: Optional path to specific config file
        sample_size: Optional number of records to sample from each source
        
    Returns:
        Validated PipelineConfig object
        
    Raises:
        FileNotFoundError: If config.yaml not found and no defaults work
        ValueError: If configuration validation fails
    """
    # Load .env file if it exists
    load_dotenv()
    
    # Find and load YAML configuration
    config_dict = _load_yaml_config(config_path)
    
    # Apply environment variable overrides for secrets
    config_dict = _apply_environment_secrets(config_dict)
    
    # Apply sample_size if provided
    if sample_size is not None:
        config_dict["sample_size"] = sample_size
    
    # Create and validate configuration
    config = PipelineConfig(**config_dict)
    
    # Resolve relative paths to absolute
    config.resolve_paths()
    
    return config


def _load_yaml_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    If config_path is provided, uses that specific file.
    Otherwise searches for config.yaml in standard locations:
    1. data_pipeline/config.yaml
    2. config.yaml (current directory)
    
    Args:
        config_path: Optional specific config file path
    
    Returns:
        Dictionary of configuration values
        
    Raises:
        FileNotFoundError: If specific config file not found
    """
    if config_path:
        # Use specific config file
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
            return config
    
    # Search standard locations
    possible_paths = [
        Path("data_pipeline/config.yaml"),
        Path("config.yaml"),
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, "r") as f:
                config = yaml.safe_load(f) or {}
                return config
    
    # If no config file found, return empty dict to use defaults
    # In production, you may want to raise an error instead
    return {}


def _apply_environment_secrets(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply environment variable overrides for secrets only.
    
    Only applies environment variables for sensitive data:
    - API keys (VOYAGE_API_KEY, OPENAI_API_KEY, etc.)
    - Database passwords (NEO4J_PASSWORD, ELASTIC_PASSWORD)
    
    Args:
        config_dict: Configuration dictionary from YAML
        
    Returns:
        Configuration with environment secrets applied
    """
    # Neo4j password from environment
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    if neo4j_password and "output" in config_dict:
        if "neo4j" not in config_dict["output"]:
            config_dict["output"]["neo4j"] = {}
        config_dict["output"]["neo4j"]["password"] = neo4j_password
    
    # Elasticsearch password from environment
    elastic_password = os.environ.get("ELASTIC_PASSWORD")
    if elastic_password and "output" in config_dict:
        if "elasticsearch" not in config_dict["output"]:
            config_dict["output"]["elasticsearch"] = {}
        config_dict["output"]["elasticsearch"]["password"] = elastic_password
    
    # API keys are validated in the model validators, not set here
    # The models check for environment variables directly
    
    return config_dict