"""Property API Client Implementation."""

import logging
from typing import List, Optional, Iterator

from property_finder_models import EnrichedProperty, EnrichedNeighborhood

from .base import BaseAPIClient
from .config import APIClientConfig
from .exceptions import NotFoundError, APIError
from .property_models import (
    PropertyListRequest,
    PropertyListResponse,
    PropertyResponse,
    NeighborhoodListRequest,
    NeighborhoodListResponse,
    NeighborhoodResponse
)


class PropertyAPIClient(BaseAPIClient):
    """API client for property and neighborhood data."""
    
    def __init__(self, config: APIClientConfig, logger: logging.Logger):
        """Initialize the Property API client.
        
        Args:
            config: API client configuration
            logger: Logger instance for structured logging
        """
        super().__init__(config, logger)
        self.logger.info(
            "Initialized Property API client",
            extra={"base_url": str(config.base_url)}
        )
    
    def get_properties(
        self,
        city: Optional[str] = None,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[EnrichedProperty]:
        """Get properties with optional filtering.
        
        Args:
            city: Filter by city name
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            List of enriched properties
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching properties",
            extra={
                "city": city,
                "include_embeddings": include_embeddings,
                "page": page,
                "page_size": page_size
            }
        )
        
        # Build request parameters
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if city:
            params["city"] = city
        if include_embeddings:
            params["include_embeddings"] = include_embeddings
        if collection_name:
            params["collection_name"] = collection_name
        
        # Make request
        response_data = self.get("properties", params=params)
        
        # Validate and parse response
        response = PropertyListResponse(**response_data)
        
        self.logger.info(
            f"Retrieved {len(response.data)} properties",
            extra={
                "total": response.metadata.total_count,
                "page": response.metadata.page
            }
        )
        
        return response.data
    
    def get_all_properties(
        self,
        city: Optional[str] = None,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page_size: int = 50
    ) -> Iterator[List[EnrichedProperty]]:
        """Get all properties with automatic pagination.
        
        Args:
            city: Filter by city name
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page_size: Number of items per page
            
        Yields:
            Lists of enriched properties from each page
            
        Raises:
            APIError: If request fails
        """
        self.logger.info(
            "Fetching all properties with pagination",
            extra={"city": city, "page_size": page_size}
        )
        
        page = 1
        while True:
            # Get current page
            properties = self.get_properties(
                city=city,
                include_embeddings=include_embeddings,
                collection_name=collection_name,
                page=page,
                page_size=page_size
            )
            
            # If no properties returned, we're done
            if not properties:
                break
                
            yield properties
            
            # If we got fewer than requested, this is the last page
            if len(properties) < page_size:
                break
                
            page += 1
    
    def get_property_by_id(self, property_id: str) -> EnrichedProperty:
        """Get a single property by ID.
        
        Args:
            property_id: Property listing ID
            
        Returns:
            Enriched property data
            
        Raises:
            NotFoundError: If property not found
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching property by ID",
            extra={"property_id": property_id}
        )
        
        try:
            response_data = self.get(f"properties/{property_id}")
            response = PropertyResponse(**response_data)
            
            self.logger.info(
                "Retrieved property by ID",
                extra={"property_id": property_id}
            )
            
            return response.data
            
        except NotFoundError:
            self.logger.warning(
                f"Property not found: {property_id}",
                extra={"property_id": property_id}
            )
            raise
    
    def get_neighborhoods(
        self,
        city: Optional[str] = None,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[EnrichedNeighborhood]:
        """Get neighborhoods with optional filtering.
        
        Args:
            city: Filter by city name
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            List of enriched neighborhoods
            
        Raises:
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching neighborhoods",
            extra={
                "city": city,
                "include_embeddings": include_embeddings,
                "page": page,
                "page_size": page_size
            }
        )
        
        # Build request parameters
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if city:
            params["city"] = city
        if include_embeddings:
            params["include_embeddings"] = include_embeddings
        if collection_name:
            params["collection_name"] = collection_name
        
        # Make request
        response_data = self.get("neighborhoods", params=params)
        
        # Validate and parse response
        response = NeighborhoodListResponse(**response_data)
        
        self.logger.info(
            f"Retrieved {len(response.data)} neighborhoods",
            extra={
                "total": response.metadata.total_count,
                "page": response.metadata.page
            }
        )
        
        return response.data
    
    def get_all_neighborhoods(
        self,
        city: Optional[str] = None,
        include_embeddings: bool = False,
        collection_name: Optional[str] = None,
        page_size: int = 50
    ) -> Iterator[List[EnrichedNeighborhood]]:
        """Get all neighborhoods with automatic pagination.
        
        Args:
            city: Filter by city name
            include_embeddings: Include embedding data in response
            collection_name: ChromaDB collection name for embeddings
            page_size: Number of items per page
            
        Yields:
            Lists of enriched neighborhoods from each page
            
        Raises:
            APIError: If request fails
        """
        self.logger.info(
            "Fetching all neighborhoods with pagination",
            extra={"city": city, "page_size": page_size}
        )
        
        page = 1
        while True:
            # Get current page
            neighborhoods = self.get_neighborhoods(
                city=city,
                include_embeddings=include_embeddings,
                collection_name=collection_name,
                page=page,
                page_size=page_size
            )
            
            if not neighborhoods:
                break
                
            yield neighborhoods
            
            # Check if this was a full page (indicating more might exist)
            if len(neighborhoods) < page_size:
                break
                
            page += 1
    
    def get_neighborhood_by_id(self, neighborhood_id: str) -> EnrichedNeighborhood:
        """Get a single neighborhood by ID.
        
        Args:
            neighborhood_id: Neighborhood ID
            
        Returns:
            Enriched neighborhood data
            
        Raises:
            NotFoundError: If neighborhood not found
            APIError: If request fails
        """
        self.logger.debug(
            "Fetching neighborhood by ID",
            extra={"neighborhood_id": neighborhood_id}
        )
        
        try:
            response_data = self.get(f"neighborhoods/{neighborhood_id}")
            response = NeighborhoodResponse(**response_data)
            
            self.logger.info(
                "Retrieved neighborhood by ID",
                extra={"neighborhood_id": neighborhood_id}
            )
            
            return response.data
            
        except NotFoundError:
            self.logger.warning(
                f"Neighborhood not found: {neighborhood_id}",
                extra={"neighborhood_id": neighborhood_id}
            )
            raise
    
    def batch_get_properties(self, property_ids: List[str]) -> List[EnrichedProperty]:
        """Get multiple properties by their IDs.
        
        Args:
            property_ids: List of property listing IDs
            
        Returns:
            List of enriched properties (may be fewer than requested if some not found)
            
        Raises:
            APIError: If request fails
        """
        self.logger.info(
            f"Batch fetching {len(property_ids)} properties",
            extra={"count": len(property_ids)}
        )
        
        properties = []
        for property_id in property_ids:
            try:
                property_data = self.get_property_by_id(property_id)
                properties.append(property_data)
            except NotFoundError:
                self.logger.warning(
                    f"Skipping missing property: {property_id}",
                    extra={"property_id": property_id}
                )
                continue
        
        self.logger.info(
            f"Retrieved {len(properties)}/{len(property_ids)} properties in batch",
            extra={"successful": len(properties), "requested": len(property_ids)}
        )
        
        return properties