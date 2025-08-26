"""
Spark session management.

This module provides centralized Spark session creation and management,
including configuration-driven setup and proper resource cleanup.
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from pyspark.sql import SparkSession

from data_pipeline.config.models import SparkConfig

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
            self._config: Optional[SparkConfig] = None
    
    def create_session(self, config: SparkConfig, extra_configs: Optional[Dict[str, str]] = None) -> SparkSession:
        """
        Create or get existing Spark session.
        
        Args:
            config: Spark configuration object
            extra_configs: Optional additional Spark configurations (e.g., Neo4j, Elasticsearch)
            
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
                builder = builder.config("spark.driver.memory", config.driver_memory)
                builder = builder.config("spark.executor.memory", config.executor_memory)
            
            # Apply extra configurations (Neo4j, Elasticsearch, etc.)
            if extra_configs:
                for key, value in extra_configs.items():
                    builder = builder.config(key, value)
            
            # Create session
            self._spark_session = builder.getOrCreate()
            self._config = config
            
            # Set log level
            self._spark_session.sparkContext.setLogLevel("WARN")
            
            # Disable ambiguous self-join check for relationship building
            self._spark_session.conf.set("spark.sql.analyzer.failAmbiguousSelfJoin", "false")
            
            # Increase maxToStringFields to prevent truncation warnings
            self._spark_session.conf.set("spark.sql.debug.maxToStringFields", "200")
            
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
    
    def restart_session(self, config: Optional[SparkConfig] = None) -> SparkSession:
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
        # Increase maxToStringFields to prevent truncation warnings
        self._spark_session.conf.set("spark.sql.debug.maxToStringFields", "200")
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




@contextmanager
def spark_session_context(config: SparkConfig) -> Generator[SparkSession, None, None]:
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


def get_or_create_spark_session(spark_config: SparkConfig, pipeline_config: Optional[Any] = None) -> SparkSession:
    """
    Get existing or create new Spark session.
    
    Args:
        spark_config: Spark configuration
        pipeline_config: Optional full pipeline configuration with output settings
        
    Returns:
        SparkSession instance
    """
    manager = SparkSessionManager()
    existing = manager.get_session()
    
    if existing is not None:
        return existing
    
    # Get all configs from pipeline config if provided (includes Neo4j, Elasticsearch)
    extra_configs = {}
    if pipeline_config is not None:
        # Use Pydantic method to get all Spark configs
        extra_configs = pipeline_config.get_spark_configs()
    
    # Create session with all configs
    return manager.create_session(spark_config, extra_configs)


def stop_spark_session() -> None:
    """Stop the current Spark session."""
    manager = SparkSessionManager()
    manager.stop_session()