"""
Dependency injection providers for FastAPI endpoints.

This module bridges FastAPI's Depends() system with the existing constructor-based
dependency injection used in the core common_ingest module.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException

from ..loaders.property_loader import PropertyLoader
from ..loaders.neighborhood_loader import NeighborhoodLoader
from ..loaders.wikipedia_loader import WikipediaLoader
from ..services.property_service import PropertyService
from ..services.neighborhood_service import NeighborhoodService
from ..services.wikipedia_service import WikipediaService
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
        
    Raises:
        HTTPException: If property data path does not exist
    """
    data_path = settings.data_paths.get_property_data_path()
    logger.debug(f"Creating PropertyLoader with data_path: {data_path}")
    
    if not data_path.exists():
        logger.error(f"Property data path not found: {data_path}")
        raise HTTPException(
            status_code=503,
            detail=f"Property data source not available: {data_path}"
        )
    
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
        
    Raises:
        HTTPException: If neighborhood data path does not exist
    """
    data_path = settings.data_paths.get_property_data_path()
    logger.debug(f"Creating NeighborhoodLoader with data_path: {data_path}")
    
    if not data_path.exists():
        logger.error(f"Neighborhood data path not found: {data_path}")
        raise HTTPException(
            status_code=503,
            detail=f"Neighborhood data source not available: {data_path}"
        )
    
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
        
    Raises:
        HTTPException: If Wikipedia database path does not exist
    """
    database_path = settings.data_paths.get_wikipedia_db_path()
    logger.debug(f"Creating WikipediaLoader with database_path: {database_path}")
    
    if not database_path.exists():
        logger.error(f"Wikipedia database not found: {database_path}")
        raise HTTPException(
            status_code=503,
            detail=f"Wikipedia database not available: {database_path}"
        )
    
    return WikipediaLoader(database_path)


def get_property_service(
    property_loader: Annotated[PropertyLoader, Depends(get_property_loader)]
) -> PropertyService:
    """Create PropertyService instance."""
    return PropertyService(property_loader)


def get_neighborhood_service(
    neighborhood_loader: Annotated[NeighborhoodLoader, Depends(get_neighborhood_loader)]
) -> NeighborhoodService:
    """Create NeighborhoodService instance."""
    return NeighborhoodService(neighborhood_loader)


def get_wikipedia_service(
    wikipedia_loader: Annotated[WikipediaLoader, Depends(get_wikipedia_loader)]
) -> WikipediaService:
    """Create WikipediaService instance."""
    return WikipediaService(wikipedia_loader)


# Type aliases for cleaner endpoint signatures
PropertyLoaderDep = Annotated[PropertyLoader, Depends(get_property_loader)]
NeighborhoodLoaderDep = Annotated[NeighborhoodLoader, Depends(get_neighborhood_loader)]
WikipediaLoaderDep = Annotated[WikipediaLoader, Depends(get_wikipedia_loader)]
PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
NeighborhoodServiceDep = Annotated[NeighborhoodService, Depends(get_neighborhood_service)]
WikipediaServiceDep = Annotated[WikipediaService, Depends(get_wikipedia_service)]
SettingsDep = Annotated[Settings, Depends(get_cached_settings)]