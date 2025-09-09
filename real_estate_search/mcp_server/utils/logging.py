"""Logging configuration utilities."""

import logging
import sys
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

from ..settings import LoggingConfig


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log string
        """
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "exc_info", "exc_text", "stack_info"]:
                log_obj[key] = value
        
        return json.dumps(log_obj)


def setup_logging(config: LoggingConfig) -> None:
    """Set up logging configuration.
    
    Args:
        config: Logging configuration
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    if config.structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(config.format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    file_path_attr = getattr(config, 'file_path', None)
    if file_path_attr:
        file_path = Path(file_path_attr)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("tenacity").setLevel(logging.WARNING)
    
    root_logger.info("Logging configured", extra={
        "level": config.level,
        "structured": config.structured,
        "file_path": str(file_path_attr) if file_path_attr else None
    })


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding context to log messages."""
    
    def __init__(self, logger: logging.Logger, extra: dict):
        """Initialize logger adapter.
        
        Args:
            logger: Base logger
            extra: Extra context to add to all logs
        """
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """Process log message to add context.
        
        Args:
            msg: Log message
            kwargs: Log kwargs
            
        Returns:
            Processed message and kwargs
        """
        if "extra" in kwargs:
            kwargs["extra"].update(self.extra)
        else:
            kwargs["extra"] = self.extra
        
        return msg, kwargs


def get_request_logger(request_id: str) -> LoggerAdapter:
    """Get a logger with request context.
    
    Args:
        request_id: Request ID for tracking
        
    Returns:
        Logger adapter with request context
    """
    logger = get_logger("mcp_server.request")
    return LoggerAdapter(logger, {"request_id": request_id})