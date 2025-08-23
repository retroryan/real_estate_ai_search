"""
Dependency injection providers for FastAPI endpoints.

This module bridges FastAPI's Depends() system with the existing constructor-based
dependency injection used in the core common_ingest module.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from ..loaders.property_loader import PropertyLoader
from ..loaders.neighborhood_loader import NeighborhoodLoader
from ..loaders.wikipedia_loader import WikipediaLoader
from ..utils.config import Settings, get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@lru_cache()
def get_cached_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to ensure settings are only loaded once and reused
    across all dependency injections.
    
    Returns:
        Settings: The cached settings instance
    """
    return get_settings()


def get_property_loader(
    settings: Annotated[Settings, Depends(get_cached_settings)]
) -> PropertyLoader:
    """
    Create PropertyLoader instance with constructor-based dependency injection.
    
    This function bridges FastAPI's Depends() with the core module's constructor-based DI.
    
    Args:
        settings: Application settings from FastAPI dependency
        
    Returns:
        PropertyLoader: Configured PropertyLoader instance
    """
    data_path = settings.data_paths.get_property_data_path()
    logger.debug(f"Creating PropertyLoader with data_path: {data_path}")
    
    return PropertyLoader(data_path)


def get_neighborhood_loader(
    settings: Annotated[Settings, Depends(get_cached_settings)]
) -> NeighborhoodLoader:
    """
    Create NeighborhoodLoader instance with constructor-based dependency injection.
    
    This function bridges FastAPI's Depends() with the core module's constructor-based DI.
    
    Args:
        settings: Application settings from FastAPI dependency
        
    Returns:
        NeighborhoodLoader: Configured NeighborhoodLoader instance
    """
    data_path = settings.data_paths.get_property_data_path()
    logger.debug(f"Creating NeighborhoodLoader with data_path: {data_path}")
    
    return NeighborhoodLoader(data_path)


def get_wikipedia_loader(
    settings: Annotated[Settings, Depends(get_cached_settings)]
) -> WikipediaLoader:
    """
    Create WikipediaLoader instance with constructor-based dependency injection.
    
    This function bridges FastAPI's Depends() with the core module's constructor-based DI.
    
    Args:
        settings: Application settings from FastAPI dependency
        
    Returns:
        WikipediaLoader: Configured WikipediaLoader instance
    """
    database_path = settings.data_paths.get_wikipedia_db_path()
    logger.debug(f"Creating WikipediaLoader with database_path: {database_path}")
    
    return WikipediaLoader(database_path)


# Type aliases for cleaner endpoint signatures
PropertyLoaderDep = Annotated[PropertyLoader, Depends(get_property_loader)]
NeighborhoodLoaderDep = Annotated[NeighborhoodLoader, Depends(get_neighborhood_loader)]
WikipediaLoaderDep = Annotated[WikipediaLoader, Depends(get_wikipedia_loader)]
SettingsDep = Annotated[Settings, Depends(get_cached_settings)]