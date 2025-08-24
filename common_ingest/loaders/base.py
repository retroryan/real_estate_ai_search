"""
Base loader interface for all data loaders.

Defines the abstract interface that all concrete loaders must implement.
Uses constructor-based dependency injection for all dependencies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generic, TypeVar, Type
from pathlib import Path
import functools

from pydantic import BaseModel

from ..utils.logger import setup_logger

# Generic type for loader return types - must be a Pydantic model
T = TypeVar('T', bound=BaseModel)

logger = setup_logger(__name__)


def log_operation(operation_name: str):
    """
    Decorator to log loader operations.
    
    Args:
        operation_name: Name of the operation being performed
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            logger.debug(f"Starting {operation_name} in {self.__class__.__name__}")
            try:
                result = func(self, *args, **kwargs)
                if isinstance(result, list):
                    logger.info(f"Completed {operation_name}: loaded {len(result)} items")
                else:
                    logger.info(f"Completed {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}")
                raise
        return wrapper
    return decorator


class BaseLoader(ABC, Generic[T]):
    """
    Abstract base class for all data loaders.
    
    Provides common functionality and defines the interface that
    all concrete loaders must implement.
    """
    
    def __init__(self, source_path: Path):
        """
        Initialize base loader with source path.
        
        Args:
            source_path: Path to the data source (file or directory)
            
        Raises:
            TypeError: If source_path is not a Path object
            FileNotFoundError: If source_path does not exist
        """
        if not isinstance(source_path, Path):
            raise TypeError(f"source_path must be a Path object, got {type(source_path)}")
        
        self.source_path = source_path
        self.logger = setup_logger(self.__class__.__name__)
        self._validate_source()
    
    def _validate_source(self) -> None:
        """Validate that the source path exists and is accessible."""
        if not self.source_path.exists():
            error_msg = f"Source path does not exist: {self.source_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        self.logger.debug(f"Source path validated: {self.source_path}")
    
    @abstractmethod
    def load_all(self) -> List[T]:
        """
        Load all data from the source.
        
        Returns:
            List of loaded items
        """
        pass
    
    @abstractmethod
    def load_by_filter(self, **filters) -> List[T]:
        """
        Load data matching the specified filters.
        
        Args:
            **filters: Keyword arguments for filtering
            
        Returns:
            List of loaded items matching the filters
        """
        pass
    
    def exists(self) -> bool:
        """
        Check if the data source exists.
        
        Returns:
            True if source exists, False otherwise
        """
        return self.source_path.exists()
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Get information about the data source.
        
        Returns:
            Dictionary with source information
        """
        return {
            "path": str(self.source_path),
            "exists": self.exists(),
            "type": "file" if self.source_path.is_file() else "directory",
            "loader": self.__class__.__name__
        }


