"""
Property business logic service.

Handles all business operations for properties including filtering,
pagination, and data retrieval.
"""

import math
from typing import List, Optional, Tuple

from property_finder_models import EnrichedProperty
from ..loaders.property_loader import PropertyLoader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PropertyService:
    """Business logic service for property operations."""
    
    def __init__(self, property_loader: PropertyLoader):
        self.property_loader = property_loader
        
    def get_properties(
        self, 
        city: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        correlation_id: Optional[str] = None
    ) -> Tuple[List[EnrichedProperty], int, int]:
        """
        Get properties with filtering and pagination.
        
        Args:
            city: Optional city filter
            page: Page number (1-based)
            page_size: Number of items per page
            correlation_id: Request correlation ID for logging
            
        Returns:
            Tuple of (paginated_properties, total_count, total_pages)
        """
        logger.info(
            f"Getting properties - city: {city}, page: {page}, page_size: {page_size}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load data using generic interface
        properties = self.property_loader.load_by_filter(city=city)
            
        # Apply pagination logic
        total_count = len(properties)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Validate page number
        if page > total_pages and total_count > 0:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} not found. Total pages available: {total_pages}"
            )
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_properties = properties[start_idx:end_idx]
        
        return paginated_properties, total_count, total_pages
        
    def get_property_by_id(
        self, 
        property_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[EnrichedProperty]:
        """Get single property by listing ID."""
        logger.info(
            f"Getting property by ID: {property_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load all properties and find the specific one
        all_properties = self.property_loader.load_all()
        for prop in all_properties:
            if prop.listing_id == property_id:
                return prop
        return None