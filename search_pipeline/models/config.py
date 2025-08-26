"""
Configuration models for the search pipeline.

Defines Pydantic models for Elasticsearch configuration based on
current best practices for Spark-Elasticsearch integration.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

# Import existing embedding configuration - this MUST be available for embeddings to work
from data_pipeline.config.models import EmbeddingConfig


class BulkWriteConfig(BaseModel):
    """
    Configuration for bulk write operations to Elasticsearch.
    
    Based on Elasticsearch best practices:
    - Bulk requests should complete in 1-2 seconds
    - Start with defaults and adjust based on testing
    """
    
    batch_size_bytes: str = Field(
        default="1mb",
        description="Maximum size of bulk request in bytes (es.batch.size.bytes)"
    )
    batch_size_entries: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of documents per bulk request (es.batch.size.entries)"
    )
    batch_write_retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retries for failed bulk writes"
    )
    batch_write_retry_wait: str = Field(
        default="10s",
        description="Wait time between retries"
    )
    write_operation: str = Field(
        default="index",
        description="Write operation type: index, create, update, upsert"
    )
    
    @field_validator("write_operation")
    @classmethod
    def validate_write_operation(cls, v: str) -> str:
        """Validate write operation is supported."""
        valid_ops = {"index", "create", "update", "upsert"}
        if v not in valid_ops:
            raise ValueError(f"Invalid write operation: {v}. Must be one of {valid_ops}")
        return v


class ElasticsearchConfig(BaseModel):
    """
    Elasticsearch connection and operation configuration.
    
    Follows Spark-Elasticsearch connector best practices for 2024:
    - Compatible with Spark 3.0-3.4 (3.5 not yet supported)
    - Optimized for bulk operations
    - Proper parallelism management
    """
    
    nodes: List[str] = Field(
        default_factory=lambda: ["localhost:9200"],
        description="Elasticsearch node addresses (es.nodes)"
    )
    port: int = Field(
        default=9200,
        ge=1,
        le=65535,
        description="Elasticsearch port (es.port)"
    )
    index_prefix: str = Field(
        default="real_estate",
        description="Prefix for index names"
    )
    index_auto_create: bool = Field(
        default=True,
        description="Automatically create indices if they don't exist (es.index.auto.create)"
    )
    nodes_discovery: bool = Field(
        default=True,
        description="Enable node discovery (set to False for local/controlled environments)"
    )
    nodes_wan_only: bool = Field(
        default=False,
        description="Whether to use nodes over WAN (es.nodes.wan.only)"
    )
    http_timeout: str = Field(
        default="2m",
        description="HTTP request timeout (es.http.timeout)"
    )
    http_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of HTTP retries (es.http.retries)"
    )
    scroll_keepalive: str = Field(
        default="10m",
        description="Scroll query keepalive time (es.scroll.keepalive)"
    )
    mapping_id: Optional[str] = Field(
        default=None,
        description="Field to use as document ID (es.mapping.id)"
    )
    username: Optional[str] = Field(
        default=None,
        description="Elasticsearch username for authentication"
    )
    error_handler_log_message: bool = Field(
        default=True,
        description="Log error messages (es.error.handler.log.error.message)"
    )
    error_handler_log_reason: bool = Field(
        default=True,
        description="Log error reasons (es.error.handler.log.error.reason)"
    )
    
    # Bulk write configuration
    bulk: BulkWriteConfig = Field(
        default_factory=BulkWriteConfig,
        description="Bulk write operation settings"
    )
    
    def get_spark_conf(self) -> Dict[str, str]:
        """
        Convert configuration to Spark connector options.
        
        Returns:
            Dictionary of Spark configuration options for Elasticsearch
        """
        conf = {
            "es.nodes": ",".join(self.nodes),
            "es.port": str(self.port),
            "es.index.auto.create": str(self.index_auto_create).lower(),
            "es.nodes.discovery": str(self.nodes_discovery).lower(),
            "es.nodes.wan.only": str(self.nodes_wan_only).lower(),
            "es.batch.size.bytes": self.bulk.batch_size_bytes,
            "es.batch.size.entries": str(self.bulk.batch_size_entries),
            "es.batch.write.retry.count": str(self.bulk.batch_write_retry_count),
            "es.batch.write.retry.wait": self.bulk.batch_write_retry_wait,
            "es.write.operation": self.bulk.write_operation,
            "es.http.timeout": self.http_timeout,
            "es.http.retries": str(self.http_retries),
            "es.scroll.keepalive": self.scroll_keepalive,
            "es.error.handler.log.error.message": str(self.error_handler_log_message).lower(),
            "es.error.handler.log.error.reason": str(self.error_handler_log_reason).lower(),
        }
        
        # Add optional configurations
        if self.mapping_id:
            conf["es.mapping.id"] = self.mapping_id
        
        # Add authentication if configured
        if self.username:
            conf["es.net.http.auth.user"] = self.username
            password = os.environ.get("ELASTIC_PASSWORD")
            if password:
                conf["es.net.http.auth.pass"] = password
        
        return conf
    
    def get_index_name(self, entity_type: str) -> str:
        """
        Generate index name for an entity type.
        
        Args:
            entity_type: Type of entity (properties, neighborhoods, wikipedia)
            
        Returns:
            Full index name
        """
        return f"{self.index_prefix}_{entity_type}"


class SearchPipelineConfig(BaseModel):
    """
    Root configuration for the search pipeline.
    
    Manages all search-related configurations and processing settings.
    """
    
    enabled: bool = Field(
        default=False,
        description="Whether search pipeline is enabled"
    )
    elasticsearch: ElasticsearchConfig = Field(
        default_factory=ElasticsearchConfig,
        description="Elasticsearch configuration"
    )
    process_properties: bool = Field(
        default=True,
        description="Process and index property documents"
    )
    process_neighborhoods: bool = Field(
        default=True,
        description="Process and index neighborhood documents"
    )
    process_wikipedia: bool = Field(
        default=True,
        description="Process and index Wikipedia documents"
    )
    validate_connection: bool = Field(
        default=True,
        description="Validate Elasticsearch connection before processing"
    )
    embedding_config: Optional[EmbeddingConfig] = Field(
        default=None,
        description="Embedding generation configuration (optional)"
    )
    
    @field_validator("enabled")
    @classmethod
    def check_environment(cls, v: bool) -> bool:
        """Check environment when search is enabled."""
        if v:
            # Check for Elasticsearch password if authentication is expected
            if not os.environ.get("ELASTIC_PASSWORD"):
                # Just log a warning, don't fail
                import logging
                logging.getLogger(__name__).warning(
                    "ELASTIC_PASSWORD not set. Elasticsearch authentication may fail."
                )
        return v
    
    def should_process(self, entity_type: str) -> bool:
        """
        Check if an entity type should be processed.
        
        Args:
            entity_type: Type of entity to check
            
        Returns:
            True if entity should be processed
        """
        if not self.enabled:
            return False
        
        mapping = {
            "properties": self.process_properties,
            "neighborhoods": self.process_neighborhoods,
            "wikipedia": self.process_wikipedia,
        }
        
        return mapping.get(entity_type, False)