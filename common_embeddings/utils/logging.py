"""
Logging configuration and utilities.

Uses Python's logging module exclusively - no print statements.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Any
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    structured: bool = True
) -> None:
    """
    Configure logging for the module.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        structured: Use structured logging format
    """
    # Create formatter
    if structured:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("llama_index").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class CorrelationLogger:
    """
    Specialized logger for correlation operations with tracking.
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize correlation logger.
        
        Args:
            correlation_id: Optional correlation ID for tracking
        """
        self.logger = get_logger(self.__class__.__name__)
        self.correlation_id = correlation_id or self._generate_correlation_id()
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID."""
        from uuid import uuid4
        return str(uuid4())[:8]
    
    def _format_message(self, message: str) -> str:
        """Format message with correlation ID."""
        return f"[{self.correlation_id}] {message}"
    
    def debug(self, message: str, **kwargs):
        """Log debug message with correlation ID."""
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with correlation ID."""
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with correlation ID."""
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with correlation ID."""
        self.logger.error(self._format_message(message), **kwargs)
    
    def log_progress(self, current: int, total: int, operation: str):
        """Log progress with percentage."""
        percentage = (current / total * 100) if total > 0 else 0
        self.info(f"{operation}: {current}/{total} ({percentage:.1f}%)")


class PerformanceLogger:
    """
    Logger for tracking performance metrics.
    """
    
    def __init__(self, operation: str):
        """
        Initialize performance logger.
        
        Args:
            operation: Name of operation being tracked
        """
        self.logger = get_logger(self.__class__.__name__)
        self.operation = operation
        self.start_time = None
        self.metrics = {}
    
    def __enter__(self):
        """Start timing on context enter."""
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log timing on context exit."""
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={"duration": duration, "metrics": self.metrics}
            )
    
    def add_metric(self, name: str, value: Any):
        """Add a metric to track."""
        self.metrics[name] = value