"""Logging utilities for the pipeline."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class PipelineLogger:
    """Centralized logging for the pipeline."""
    
    _loggers = {}
    _initialized = False
    _log_level = logging.INFO
    _log_file: Optional[Path] = None
    
    @classmethod
    def initialize(cls, log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
        """Initialize the logging system.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file
        """
        if cls._initialized:
            return
        
        # Convert string level to logging constant
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        cls._log_level = level_map.get(log_level.upper(), logging.INFO)
        cls._log_file = log_file
        
        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(cls._log_level)
        
        # File handler if specified
        handlers = [console_handler]
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(cls._log_level)
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=cls._log_level,
            handlers=handlers,
            force=True
        )
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger instance.
        
        Args:
            name: Logger name (usually module name)
            
        Returns:
            Configured logger instance
        """
        # Initialize with defaults if not already done
        if not cls._initialized:
            cls.initialize()
        
        if name not in cls._loggers:
            logger = logging.getLogger(f"squack.{name}")
            logger.setLevel(cls._log_level)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def set_level(cls, level: str) -> None:
        """Change the logging level for all loggers.
        
        Args:
            level: New logging level
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        new_level = level_map.get(level.upper(), logging.INFO)
        cls._log_level = new_level
        
        # Update all existing loggers
        for logger in cls._loggers.values():
            logger.setLevel(new_level)
        
        # Update root logger handlers
        for handler in logging.root.handlers:
            handler.setLevel(new_level)


def log_execution_time(func):
    """Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = PipelineLogger.get_logger(func.__module__)
        
        start_time = time.time()
        logger.info(f"Starting {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"Completed {func.__name__} in {elapsed:.2f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Failed {func.__name__} after {elapsed:.2f} seconds: {e}")
            raise
    
    return wrapper


def log_stage(stage_name: str):
    """Decorator to log pipeline stage execution.
    
    Args:
        stage_name: Name of the pipeline stage
        
    Returns:
        Decorator function
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = PipelineLogger.get_logger(func.__module__)
            
            logger.info(f"{'='*60}")
            logger.info(f"Starting Stage: {stage_name}")
            logger.info(f"{'='*60}")
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(f"{'='*60}")
                logger.info(f"Completed Stage: {stage_name}")
                logger.info(f"Duration: {elapsed:.2f} seconds")
                logger.info(f"{'='*60}")
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                
                logger.error(f"{'='*60}")
                logger.error(f"Failed Stage: {stage_name}")
                logger.error(f"Duration: {elapsed:.2f} seconds")
                logger.error(f"Error: {e}")
                logger.error(f"{'='*60}")
                
                raise
        
        return wrapper
    return decorator


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    PipelineLogger.initialize(log_level=level)