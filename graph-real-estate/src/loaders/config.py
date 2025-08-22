"""Configuration loader for graph database batch processing.

This module provides centralized configuration management for batch sizes
used throughout the graph loading process.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class GraphLoadingConfig(BaseModel):
    """Configuration for graph loading batch sizes.
    
    All batch sizes are configurable via config.yaml to optimize
    loading performance based on system capabilities.
    """
    
    state_batch_size: int = Field(default=500, description="Batch size for state node creation")
    county_batch_size: int = Field(default=1000, description="Batch size for county node creation")
    city_batch_size: int = Field(default=1000, description="Batch size for city node creation")
    feature_batch_size: int = Field(default=1000, description="Batch size for feature node creation")
    property_batch_size: int = Field(default=1000, description="Batch size for property node creation")
    wikipedia_batch_size: int = Field(default=1000, description="Batch size for Wikipedia node creation")
    neighborhood_batch_size: int = Field(default=500, description="Batch size for neighborhood node creation")
    default_batch_size: int = Field(default=1000, description="Default batch size for unspecified operations")
    
    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "GraphLoadingConfig":
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to config.yaml. If None, uses default location.
            
        Returns:
            GraphLoadingConfig instance with settings from YAML or defaults.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config.yaml'
        
        if not config_path.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Extract graph_loading section or use empty dict
            graph_config = config_data.get('graph_loading', {})
            
            # Create config with values from YAML, using defaults for missing keys
            return cls(**graph_config)
        
        except (yaml.YAMLError, IOError) as e:
            # Log error and return defaults
            print(f"Warning: Could not load config from {config_path}: {e}")
            return cls()
    
    def get_batch_size_for_entity(self, entity_type: str) -> int:
        """Get batch size for a specific entity type.
        
        Args:
            entity_type: Type of entity (e.g., 'state', 'county', 'property')
            
        Returns:
            Configured batch size for the entity type or default.
        """
        batch_size_attr = f"{entity_type.lower()}_batch_size"
        return getattr(self, batch_size_attr, self.default_batch_size)