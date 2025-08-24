"""
Neighborhood business logic service.

Handles all business operations for neighborhoods including filtering,
pagination, and data retrieval.
"""

import math
from typing import List, Optional, Tuple

from property_finder_models import EnrichedNeighborhood
from ..loaders.neighborhood_loader import NeighborhoodLoader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class NeighborhoodService:
    """Business logic service for neighborhood operations."""
    
    def __init__(self, neighborhood_loader: NeighborhoodLoader):
        self.neighborhood_loader = neighborhood_loader
        
    def get_neighborhoods(
        self, 
        city: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        correlation_id: Optional[str] = None
    ) -> Tuple[List[EnrichedNeighborhood], int, int]:
        """
        Get neighborhoods with filtering and pagination.
        
        Args:
            city: Optional city filter
            page: Page number (1-based)
            page_size: Number of items per page
            correlation_id: Request correlation ID for logging
            
        Returns:
            Tuple of (paginated_neighborhoods, total_count, total_pages)
        """
        logger.info(
            f"Getting neighborhoods - city: {city}, page: {page}, page_size: {page_size}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load data using generic interface
        neighborhoods = self.neighborhood_loader.load_by_filter(city=city)
            
        # Apply pagination logic
        total_count = len(neighborhoods)
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
        paginated_neighborhoods = neighborhoods[start_idx:end_idx]
        
        return paginated_neighborhoods, total_count, total_pages
        
    def get_neighborhood_by_id(
        self, 
        neighborhood_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[EnrichedNeighborhood]:
        """Get single neighborhood by ID."""
        logger.info(
            f"Getting neighborhood by ID: {neighborhood_id}",
            extra={"correlation_id": correlation_id}
        )
        
        # Load all neighborhoods and find the specific one
        all_neighborhoods = self.neighborhood_loader.load_all()
        for neighborhood in all_neighborhoods:
            if neighborhood.neighborhood_id == neighborhood_id:
                return neighborhood
        return None