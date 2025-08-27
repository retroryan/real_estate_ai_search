"""
Comprehensive configuration for the entire real estate search system using Pydantic.
Single source of truth with clean constructor injection patterns.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from pathlib import Path
import yaml
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration with validation."""
    host: str = Field(default="localhost", description="Elasticsearch host")
    port: int = Field(default=9200, description="Elasticsearch port", ge=1, le=65535)
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cloud_id: Optional[str] = Field(default=None, description="Elastic Cloud ID")
    property_index: str = Field(default="properties", description="Property index name")
    wiki_chunks_index_prefix: str = Field(default="wiki_chunks", description="Wikipedia chunks index prefix")
    wiki_summaries_index_prefix: str = Field(default="wiki_summaries", description="Wikipedia summaries index prefix")
    request_timeout: int = Field(default=30, description="Request timeout in seconds", gt=0)
    verify_certs: bool = Field(default=False, description="Verify SSL certificates")
    
    def model_post_init(self, __context):
        """Load credentials from environment if not provided."""
        if self.username is None:
            self.username = os.getenv("ES_USERNAME") or os.getenv("ELASTICSEARCH_USERNAME")
        if self.password is None:
            self.password = os.getenv("ES_PASSWORD") or os.getenv("ELASTICSEARCH_PASSWORD")
        if self.api_key is None:
            self.api_key = os.getenv("ES_API_KEY") or os.getenv("ELASTICSEARCH_API_KEY")


class DataConfig(BaseModel):
    """Data paths configuration."""
    wikipedia_db: Path = Field(default=Path("../data/wikipedia/wikipedia.db"))
    
    def model_post_init(self, __context):
        """Ensure database directory exists."""
        self.wikipedia_db.parent.mkdir(parents=True, exist_ok=True)


class AppConfig(BaseModel):
    """
    Configuration for Real Estate Search application.
    Works with pre-indexed data from data_pipeline.
    """
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    demo_mode: bool = Field(default=True, description="Running in demo mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    @classmethod
    def from_yaml(cls, path: Path = Path("config.yaml")) -> "AppConfig":
        """Load configuration from YAML file."""
        logger.info(f"Loading configuration from {path}")
        
        if not path.exists():
            logger.warning(f"Configuration file {path} not found, using defaults")
            return cls()
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        config = cls(**data)
        logger.info("Configuration loaded successfully")
        return config
    
    def to_yaml(self, path: Path = Path("config.yaml")):
        """Save configuration to YAML file."""
        logger.info(f"Saving configuration to {path}")
        
        with open(path, 'w') as f:
            data = self.model_dump(exclude_none=True, mode='json')
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info("Configuration saved successfully")