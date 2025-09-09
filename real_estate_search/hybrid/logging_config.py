"""
Logging configuration module for hybrid search.

Provides centralized logging configuration with structured logging,
performance tracking, and debug capabilities.
"""

import logging
import sys
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: LogLevel = Field(LogLevel.INFO, description="Default log level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    date_format: str = Field(
        "%Y-%m-%d %H:%M:%S",
        description="Date format for log messages"
    )
    enable_console: bool = Field(True, description="Enable console output")
    enable_file: bool = Field(False, description="Enable file output")
    file_path: Optional[str] = Field(None, description="Log file path")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class LoggerFactory:
    """
    Factory for creating and configuring loggers.
    
    Provides consistent logger configuration across the hybrid search module.
    """
    
    _configured = False
    _config: Optional[LoggingConfig] = None
    
    @classmethod
    def configure(cls, config: Optional[LoggingConfig] = None) -> None:
        """
        Configure logging for the entire module.
        
        Args:
            config: Logging configuration (uses defaults if None)
        """
        if cls._configured:
            return
        
        cls._config = config or LoggingConfig()
        
        # Configure root logger for hybrid search module
        root_logger = logging.getLogger("real_estate_search.hybrid")
        root_logger.setLevel(cls._config.level.value)
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # Add console handler if enabled
        if cls._config.enable_console:
            console_handler = cls._create_console_handler()
            root_logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if cls._config.enable_file and cls._config.file_path:
            file_handler = cls._create_file_handler()
            root_logger.addHandler(file_handler)
        
        cls._configured = True
        
        # Log configuration
        logger = cls.get_logger("LoggerFactory")
        logger.info(f"Logging configured - Level: {cls._config.level}")
    
    @classmethod
    def _create_console_handler(cls) -> logging.StreamHandler:
        """
        Create configured console handler.
        
        Returns:
            Configured console handler
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(cls._config.level.value)
        
        formatter = logging.Formatter(
            cls._config.format,
            datefmt=cls._config.date_format
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @classmethod
    def _create_file_handler(cls) -> logging.FileHandler:
        """
        Create configured file handler.
        
        Returns:
            Configured file handler
        """
        handler = logging.FileHandler(cls._config.file_path)
        handler.setLevel(cls._config.level.value)
        
        formatter = logging.Formatter(
            cls._config.format,
            datefmt=cls._config.date_format
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a configured logger instance.
        
        Args:
            name: Logger name (typically module or class name)
            
        Returns:
            Configured logger instance
        """
        # Ensure configuration is applied
        if not cls._configured:
            cls.configure()
        
        # Create logger with hybrid search prefix
        full_name = f"real_estate_search.hybrid.{name}"
        return logging.getLogger(full_name)
    
    @classmethod
    def set_level(cls, level: LogLevel) -> None:
        """
        Dynamically change log level.
        
        Args:
            level: New log level
        """
        root_logger = logging.getLogger("real_estate_search.hybrid")
        root_logger.setLevel(level.value)
        
        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(level.value)
        
        if cls._config:
            cls._config.level = level
        
        logger = cls.get_logger("LoggerFactory")
        logger.info(f"Log level changed to: {level}")


class PerformanceLogger:
    """
    Specialized logger for performance metrics.
    
    Tracks and logs performance data for search operations.
    """
    
    def __init__(self, logger_name: str = "PerformanceLogger"):
        """
        Initialize performance logger.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = LoggerFactory.get_logger(logger_name)
    
    def log_search_performance(
        self,
        query: str,
        total_time_ms: int,
        es_time_ms: int,
        embedding_time_ms: int,
        result_count: int
    ) -> None:
        """
        Log search performance metrics.
        
        Args:
            query: Search query
            total_time_ms: Total execution time
            es_time_ms: Elasticsearch execution time
            embedding_time_ms: Embedding generation time
            result_count: Number of results
        """
        self.logger.info(
            f"Search Performance - "
            f"Query: '{query[:50]}...', "
            f"Total: {total_time_ms}ms, "
            f"ES: {es_time_ms}ms, "
            f"Embedding: {embedding_time_ms}ms, "
            f"Results: {result_count}"
        )
        
        # Log warning for slow queries
        if total_time_ms > 1000:
            self.logger.warning(
                f"Slow query detected - "
                f"Query: '{query}', "
                f"Time: {total_time_ms}ms"
            )
    
    def log_cache_hit(self, cache_type: str, key: str) -> None:
        """
        Log cache hit event.
        
        Args:
            cache_type: Type of cache
            key: Cache key
        """
        self.logger.debug(f"Cache hit - Type: {cache_type}, Key: {key}")
    
    def log_cache_miss(self, cache_type: str, key: str) -> None:
        """
        Log cache miss event.
        
        Args:
            cache_type: Type of cache
            key: Cache key
        """
        self.logger.debug(f"Cache miss - Type: {cache_type}, Key: {key}")


# Initialize default configuration on module import
LoggerFactory.configure()