"""Structured logging setup using loguru."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

from squack_pipeline.config.settings import LoggingConfig


class PipelineLogger:
    """Centralized logging configuration for the pipeline."""
    
    _initialized = False
    
    @classmethod
    def setup(cls, config: Optional[LoggingConfig] = None) -> None:
        """Configure loguru logger for the pipeline."""
        if cls._initialized:
            return
        
        # Remove default handler
        logger.remove()
        
        # Use default config if not provided
        if config is None:
            config = LoggingConfig()
        
        # Configure console handler
        logger.add(
            sys.stderr,
            format=config.format,
            level=config.level,
            serialize=config.serialize,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            catch=True
        )
        
        # Configure file handler if specified
        if config.log_file:
            logger.add(
                config.log_file,
                format=config.format,
                level=config.level,
                rotation=config.rotation,
                retention=config.retention,
                compression="zip",
                serialize=config.serialize,
                enqueue=True,
                catch=True
            )
        
        cls._initialized = True
        logger.info(f"Logging initialized with level {config.level}")
    
    @classmethod
    def get_logger(cls, name: str) -> "LoggerAdapter":
        """Get a logger instance with a specific name."""
        if not cls._initialized:
            cls.setup()
        return LoggerAdapter(name)


class LoggerAdapter:
    """Adapter to add context to log messages."""
    
    def __init__(self, name: str):
        """Initialize logger adapter with a name."""
        self.name = name
        self._context: Dict[str, Any] = {"module": name}
    
    def bind(self, **kwargs) -> "LoggerAdapter":
        """Add context variables to the logger."""
        self._context.update(kwargs)
        return self
    
    def _log(self, level: str, message: str, *args, **kwargs):
        """Internal method to log with context."""
        kwargs.update(self._context)
        getattr(logger.opt(depth=2), level)(message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self._log("debug", message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self._log("info", message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self._log("warning", message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self._log("error", message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self._log("critical", message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self._log("exception", message, *args, **kwargs)
    
    def success(self, message: str, *args, **kwargs):
        """Log success message."""
        self._log("success", message, *args, **kwargs)


def log_execution_time(func):
    """Decorator to log function execution time."""
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger_instance = PipelineLogger.get_logger(func.__module__)
        
        logger_instance.debug(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger_instance.success(
                f"Completed {func.__name__} in {execution_time:.2f} seconds"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger_instance.error(
                f"Failed {func.__name__} after {execution_time:.2f} seconds: {e}"
            )
            raise
    
    return wrapper


def log_data_quality(
    records_processed: int,
    records_failed: int,
    processing_time: float
) -> None:
    """Log data quality metrics."""
    logger_instance = PipelineLogger.get_logger("data_quality")
    
    success_rate = (
        (records_processed - records_failed) / records_processed * 100
        if records_processed > 0
        else 0
    )
    
    logger_instance.info(
        "Data quality metrics",
        records_processed=records_processed,
        records_failed=records_failed,
        success_rate=f"{success_rate:.2f}%",
        processing_time=f"{processing_time:.2f}s",
        throughput=f"{records_processed / processing_time:.2f} records/s" if processing_time > 0 else "N/A"
    )