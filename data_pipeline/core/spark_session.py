"""
Spark session management.

This module provides centralized Spark session creation and management,
including configuration-driven setup and proper resource cleanup.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from pyspark.sql import SparkSession

from data_pipeline.config.pipeline_config import PipelineConfig

logger = logging.getLogger(__name__)


class SparkSessionManager:
    """Manages Spark session lifecycle and configuration."""
    
    _instance: Optional["SparkSessionManager"] = None
    _spark_session: Optional[SparkSession] = None
    
    def __new__(cls) -> "SparkSessionManager":
        """Implement singleton pattern for session manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the session manager."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config: Optional[PipelineConfig] = None
    
    def create_session(self, config: PipelineConfig) -> SparkSession:
        """
        Create or get existing Spark session.
        
        Args:
            config: Spark configuration object
            
        Returns:
            Configured SparkSession
        """
        if self._spark_session is not None:
            logger.info("Returning existing Spark session")
            return self._spark_session
        
        logger.info(f"Creating new Spark session: {config.app_name}")
        
        try:
            # Build Spark session
            builder = SparkSession.builder \
                .appName(config.app_name) \
                .master(config.master)
            
            # Set driver memory if not in local mode
            if not config.master.startswith("local"):
                builder = builder.config("spark.driver.memory", config.memory)
                builder = builder.config("spark.executor.memory", config.executor_memory)
            
            # Apply additional configuration
            for key, value in config.config.items():
                builder = builder.config(key, value)
            
            # Create session
            self._spark_session = builder.getOrCreate()
            self._config = config
            
            # Set log level
            self._spark_session.sparkContext.setLogLevel("WARN")
            
            # Disable ambiguous self-join check for relationship building
            self._spark_session.conf.set("spark.sql.analyzer.failAmbiguousSelfJoin", "false")
            
            # Log session info
            self._log_session_info()
            
            return self._spark_session
            
        except Exception as e:
            logger.error(f"Failed to create Spark session: {e}")
            raise
    
    def get_session(self) -> Optional[SparkSession]:
        """
        Get the current Spark session.
        
        Returns:
            Current SparkSession or None if not created
        """
        return self._spark_session
    
    def stop_session(self) -> None:
        """Stop the current Spark session and release resources."""
        if self._spark_session is not None:
            logger.info("Stopping Spark session")
            try:
                self._spark_session.stop()
                self._spark_session = None
                self._config = None
                logger.info("Spark session stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Spark session: {e}")
                raise
    
    def restart_session(self, config: Optional[PipelineConfig] = None) -> SparkSession:
        """
        Restart Spark session with new or existing configuration.
        
        Args:
            config: Optional new configuration. Uses existing if None.
            
        Returns:
            New SparkSession
            
        Raises:
            RuntimeError: If no configuration available
        """
        if config is None and self._config is None:
            raise RuntimeError("No configuration available for restart")
        
        self.stop_session()
        return self.create_session(config or self._config)
    
    def _log_session_info(self) -> None:
        """Log information about the created Spark session."""
        if self._spark_session is None:
            return
        
        sc = self._spark_session.sparkContext
        logger.info(f"Spark version: {sc.version}")
        logger.info(f"Spark master: {sc.master}")
        logger.info(f"Spark app ID: {sc.applicationId}")
        logger.info(f"Spark UI: {sc.uiWebUrl}")
        
        # Log key configurations
        conf = sc.getConf()
        important_configs = [
            "spark.sql.adaptive.enabled",
            "spark.sql.shuffle.partitions",
            "spark.serializer"
        ]
        
        for key in important_configs:
            value = conf.get(key, "Not set")
            logger.debug(f"{key}: {value}")
    
    def get_spark_conf(self) -> Dict[str, str]:
        """
        Get current Spark configuration as dictionary.
        
        Returns:
            Dictionary of Spark configuration parameters
        """
        if self._spark_session is None:
            return {}
        
        conf = self._spark_session.sparkContext.getConf()
        return {k: v for k, v in conf.getAll()}
    
    def set_checkpoint_dir(self, path: str) -> None:
        """
        Set checkpoint directory for fault tolerance.
        
        Args:
            path: Path to checkpoint directory
        """
        if self._spark_session is None:
            raise RuntimeError("No active Spark session")
        
        self._spark_session.sparkContext.setCheckpointDir(path)
        logger.info(f"Checkpoint directory set to: {path}")
    
    def enable_adaptive_execution(self) -> None:
        """Enable Spark adaptive query execution for better performance."""
        if self._spark_session is None:
            raise RuntimeError("No active Spark session")
        
        self._spark_session.conf.set("spark.sql.adaptive.enabled", "true")
        self._spark_session.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
        # Disable ambiguous self-join check for relationship building
        self._spark_session.conf.set("spark.sql.analyzer.failAmbiguousSelfJoin", "false")
        logger.info("Adaptive query execution enabled")
    
    def set_shuffle_partitions(self, num_partitions: int) -> None:
        """
        Set number of shuffle partitions.
        
        Args:
            num_partitions: Number of partitions for shuffles
        """
        if self._spark_session is None:
            raise RuntimeError("No active Spark session")
        
        self._spark_session.conf.set("spark.sql.shuffle.partitions", str(num_partitions))
        logger.info(f"Shuffle partitions set to: {num_partitions}")


def _add_neo4j_config_if_enabled(spark_config: PipelineConfig, pipeline_config: Any) -> PipelineConfig:
    """
    Add Neo4j configuration to Spark config if Neo4j writer is enabled.
    
    Args:
        spark_config: Base Spark configuration
        pipeline_config: Pipeline configuration to check for Neo4j settings
        
    Returns:
        Updated PipelineConfig with Neo4j settings if enabled
    """
    # Check if Neo4j writer is enabled in the pipeline configuration
    if (hasattr(pipeline_config, 'output_destinations') and 
        hasattr(pipeline_config.output_destinations, 'neo4j') and
        pipeline_config.output_destinations.neo4j.enabled):
        
        neo4j_cfg = pipeline_config.output_destinations.neo4j
        logger.info("Neo4j writer enabled - adding connection configuration to SparkSession")
        
        # Add Neo4j connection settings to Spark config
        spark_config.config["neo4j.url"] = neo4j_cfg.uri
        spark_config.config["neo4j.authentication.basic.username"] = neo4j_cfg.username
        spark_config.config["neo4j.authentication.basic.password"] = neo4j_cfg.get_password() or ""
        spark_config.config["neo4j.database"] = neo4j_cfg.database
        
        logger.debug(f"Added Neo4j config for database: {neo4j_cfg.database}")
    
    return spark_config


def _add_elasticsearch_config_if_enabled(spark_config: PipelineConfig, pipeline_config: Any) -> PipelineConfig:
    """
    Add Elasticsearch configuration to Spark config if Elasticsearch writer is enabled.
    
    Args:
        spark_config: Base Spark configuration
        pipeline_config: Pipeline configuration to check for Elasticsearch settings
        
    Returns:
        Updated PipelineConfig with Elasticsearch settings if enabled
    """
    # Check if Elasticsearch writer is enabled in the pipeline configuration
    if (hasattr(pipeline_config, 'output_destinations') and 
        hasattr(pipeline_config.output_destinations, 'elasticsearch') and
        pipeline_config.output_destinations.elasticsearch.enabled):
        
        es_cfg = pipeline_config.output_destinations.elasticsearch
        logger.info("Elasticsearch writer enabled - adding connection configuration to SparkSession")
        
        # Add Elasticsearch connection settings using official es.* namespace
        spark_config.config["es.nodes"] = ",".join(es_cfg.hosts)
        
        # Add authentication if provided
        if es_cfg.username:
            spark_config.config["es.net.http.auth.user"] = es_cfg.username
        if es_cfg.password:
            spark_config.config["es.net.http.auth.pass"] = es_cfg.get_password() or ""
            
        # Add batch and write settings
        spark_config.config["es.batch.size.entries"] = str(es_cfg.bulk_size)
        spark_config.config["es.write.operation"] = "upsert"
        spark_config.config["es.mapping.id"] = "id"  # Default ID field
        
        # Add retry settings for resilience
        spark_config.config["es.batch.write.retry.count"] = "3"
        spark_config.config["es.batch.write.retry.wait"] = "10s"
        
        # Add timeout settings for demo environment
        spark_config.config["es.http.timeout"] = "2m"
        spark_config.config["es.http.retries"] = "3"
        spark_config.config["es.scroll.keepalive"] = "10m"
        
        # Enable error logging
        spark_config.config["es.error.handler.log.error.message"] = "true"
        spark_config.config["es.error.handler.log.error.reason"] = "true"
        
        logger.debug(f"Added Elasticsearch config for nodes: {es_cfg.hosts}")
    
    return spark_config


@contextmanager
def spark_session_context(config: PipelineConfig) -> Generator[SparkSession, None, None]:
    """
    Context manager for Spark session lifecycle.
    
    Args:
        config: Spark configuration
        
    Yields:
        Configured SparkSession
        
    Example:
        ```python
        with spark_session_context(config) as spark:
            df = spark.read.json("data.json")
            # Process data
        # Session automatically cleaned up
        ```
    """
    manager = SparkSessionManager()
    session = None
    
    try:
        session = manager.create_session(config)
        yield session
    finally:
        if session is not None:
            manager.stop_session()


def get_or_create_spark_session(config: PipelineConfig, pipeline_config: Optional[Any] = None) -> SparkSession:
    """
    Get existing or create new Spark session.
    
    Args:
        config: Spark configuration
        pipeline_config: Optional pipeline configuration to check for Neo4j and Elasticsearch settings
        
    Returns:
        SparkSession instance
    """
    manager = SparkSessionManager()
    existing = manager.get_session()
    
    if existing is not None:
        return existing
    
    # Check if Neo4j or Elasticsearch should be configured at session level
    if pipeline_config is not None:
        config = _add_neo4j_config_if_enabled(config, pipeline_config)
        config = _add_elasticsearch_config_if_enabled(config, pipeline_config)
    
    return manager.create_session(config)


def stop_spark_session() -> None:
    """Stop the current Spark session."""
    manager = SparkSessionManager()
    manager.stop_session()