"""
Property search service implementation.
"""

import logging
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch

from .base import BaseSearchService
from .models import (
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyResult,
    PropertyAddress,
    PropertyFilter,
    GeoLocation
)

logger = logging.getLogger(__name__)


class PropertySearchService(BaseSearchService):
    """
    Service for searching properties in Elasticsearch.
    
    Handles all property-related search operations including text search,
    filtered search, geo-distance search, and semantic similarity search.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the property search service.
        
        Args:
            es_client: Elasticsearch client instance
        """
        super().__init__(es_client)
        self.index_name = "properties"
    
    def search(self, request: PropertySearchRequest) -> PropertySearchResponse:
        """
        Main search method that routes to appropriate search type.
        
        Args:
            request: Property search request
            
        Returns:
            Property search response
        """
        try:
            # Build query based on request parameters
            query = self._build_query(request)
            
            # Execute search
            es_response = self.execute_search(
                index=self.index_name,
                query=query,
                size=request.size,
                from_offset=request.from_offset
            )
            
            # Transform response
            return self._transform_response(es_response, request)
            
        except Exception as e:
            logger.error(f"Property search failed: {str(e)}")
            raise
    
    def search_text(self, query_text: str, size: int = 10) -> PropertySearchResponse:
        """
        Perform basic text search across property fields.
        
        Args:
            query_text: Search query
            size: Number of results
            
        Returns:
            Property search response
        """
        request = PropertySearchRequest(
            query=query_text,
            size=size,
            include_highlights=True
        )
        return self.search(request)
    
    def search_filtered(
        self,
        query_text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10
    ) -> PropertySearchResponse:
        """
        Search with property filters applied.
        
        Args:
            query_text: Optional text query
            filters: Property filters
            size: Number of results
            
        Returns:
            Property search response
        """
        property_filter = PropertyFilter(**filters) if filters else None
        request = PropertySearchRequest(
            query=query_text,
            filters=property_filter,
            size=size
        )
        return self.search(request)
    
    def search_geo(
        self,
        lat: float,
        lon: float,
        distance_km: float,
        query_text: Optional[str] = None,
        size: int = 10
    ) -> PropertySearchResponse:
        """
        Search properties within a geographic radius.
        
        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            distance_km: Search radius in kilometers
            query_text: Optional text query
            size: Number of results
            
        Returns:
            Property search response
        """
        request = PropertySearchRequest(
            query=query_text,
            geo_location=GeoLocation(lat=lat, lon=lon),
            geo_distance_km=distance_km,
            size=size
        )
        return self.search(request)
    
    def search_similar(
        self,
        reference_property_id: str,
        size: int = 10
    ) -> PropertySearchResponse:
        """
        Find properties similar to a reference property using embeddings.
        
        Args:
            reference_property_id: ID of reference property
            size: Number of similar properties to find
            
        Returns:
            Property search response
        """
        # Get reference property embedding
        ref_property = self.get_document(
            index=self.index_name,
            doc_id=reference_property_id,
            source_fields=["embedding"]
        )
        
        if not ref_property or "embedding" not in ref_property:
            raise ValueError(f"Reference property {reference_property_id} not found or has no embedding")
        
        request = PropertySearchRequest(
            reference_property_id=reference_property_id,
            size=size
        )
        return self.search(request)
    
    def _build_query(self, request: PropertySearchRequest) -> Dict[str, Any]:
        """
        Build Elasticsearch query from request parameters.
        
        Args:
            request: Property search request
            
        Returns:
            Elasticsearch query DSL
        """
        query = {}
        
        # Semantic similarity search
        if request.reference_property_id:
            ref_property = self.get_document(
                index=self.index_name,
                doc_id=request.reference_property_id,
                source_fields=["embedding"]
            )
            
            if ref_property and "embedding" in ref_property:
                query["knn"] = {
                    "field": "embedding",
                    "query_vector": ref_property["embedding"],
                    "k": request.size + 1,
                    "num_candidates": 100
                }
                # Exclude reference property
                query["query"] = {
                    "bool": {
                        "must_not": [
                            {"term": {"_id": request.reference_property_id}}
                        ]
                    }
                }
        
        # Geo-distance search
        elif request.geo_location and request.geo_distance_km:
            bool_query = {"bool": {"filter": []}}
            
            # Add geo-distance filter
            bool_query["bool"]["filter"].append({
                "geo_distance": {
                    "distance": f"{request.geo_distance_km}km",
                    "address.location": {
                        "lat": request.geo_location.lat,
                        "lon": request.geo_location.lon
                    }
                }
            })
            
            # Add text query if provided
            if request.query:
                bool_query["bool"]["must"] = [{
                    "multi_match": {
                        "query": request.query,
                        "fields": [
                            "description^2",
                            "address.street",
                            "address.city",
                            "features"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }]
            
            query["query"] = bool_query
            
            # Add sorting by distance
            query["sort"] = [{
                "_geo_distance": {
                    "address.location": {
                        "lat": request.geo_location.lat,
                        "lon": request.geo_location.lon
                    },
                    "order": "asc",
                    "unit": "km"
                }
            }]
        
        # Filtered search
        elif request.filters or request.query:
            bool_query = {"bool": {}}
            
            # Add text query
            if request.query:
                bool_query["bool"]["must"] = [{
                    "multi_match": {
                        "query": request.query,
                        "fields": [
                            "description^2",
                            "address.street",
                            "address.city",
                            "property_type",
                            "features"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }]
            
            # Add filters
            if request.filters:
                filters = []
                
                if request.filters.property_types:
                    filters.append({
                        "terms": {"property_type": [pt.value for pt in request.filters.property_types]}
                    })
                
                if request.filters.min_price is not None or request.filters.max_price is not None:
                    range_filter = {"range": {"price": {}}}
                    if request.filters.min_price is not None:
                        range_filter["range"]["price"]["gte"] = request.filters.min_price
                    if request.filters.max_price is not None:
                        range_filter["range"]["price"]["lte"] = request.filters.max_price
                    filters.append(range_filter)
                
                if request.filters.min_bedrooms is not None or request.filters.max_bedrooms is not None:
                    range_filter = {"range": {"bedrooms": {}}}
                    if request.filters.min_bedrooms is not None:
                        range_filter["range"]["bedrooms"]["gte"] = request.filters.min_bedrooms
                    if request.filters.max_bedrooms is not None:
                        range_filter["range"]["bedrooms"]["lte"] = request.filters.max_bedrooms
                    filters.append(range_filter)
                
                if request.filters.min_bathrooms is not None or request.filters.max_bathrooms is not None:
                    range_filter = {"range": {"bathrooms": {}}}
                    if request.filters.min_bathrooms is not None:
                        range_filter["range"]["bathrooms"]["gte"] = request.filters.min_bathrooms
                    if request.filters.max_bathrooms is not None:
                        range_filter["range"]["bathrooms"]["lte"] = request.filters.max_bathrooms
                    filters.append(range_filter)
                
                if request.filters.min_square_feet is not None or request.filters.max_square_feet is not None:
                    range_filter = {"range": {"square_feet": {}}}
                    if request.filters.min_square_feet is not None:
                        range_filter["range"]["square_feet"]["gte"] = request.filters.min_square_feet
                    if request.filters.max_square_feet is not None:
                        range_filter["range"]["square_feet"]["lte"] = request.filters.max_square_feet
                    filters.append(range_filter)
                
                if filters:
                    bool_query["bool"]["filter"] = filters
            
            query["query"] = bool_query
        
        # Default to match all
        else:
            query["query"] = {"match_all": {}}
        
        # Add highlighting if requested
        if request.include_highlights:
            query["highlight"] = {
                "fields": {
                    "description": {"fragment_size": 150},
                    "features": {"fragment_size": 100}
                }
            }
        
        # Add source filtering
        query["_source"] = [
            "listing_id", "property_type", "price", "bedrooms", "bathrooms",
            "square_feet", "address", "description", "features", "location"
        ]
        
        return query
    
    def _extract_address(self, address_data: Any) -> PropertyAddress:
        """
        Extract address from various data formats.
        
        Args:
            address_data: Address data as dict or Address object
            
        Returns:
            PropertyAddress for API response
        """
        # Handle dict format from Elasticsearch
        if isinstance(address_data, dict):
            return PropertyAddress(
                street=address_data.get("street", ""),
                city=address_data.get("city", ""),
                state=address_data.get("state", ""),
                zip_code=address_data.get("zip_code", "")
            )
        
        # Handle Address object from PropertyListing
        return PropertyAddress(
            street=getattr(address_data, 'street', ''),
            city=getattr(address_data, 'city', ''),
            state=getattr(address_data, 'state', ''),
            zip_code=getattr(address_data, 'zip_code', '')
        )
    
    def _transform_response(
        self,
        es_response: Dict[str, Any],
        request: PropertySearchRequest
    ) -> PropertySearchResponse:
        """
        Transform Elasticsearch response to PropertySearchResponse.
        
        Args:
            es_response: Raw Elasticsearch response
            request: Original search request
            
        Returns:
            Transformed property search response
        """
        results = []
        
        for hit in es_response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            
            # Extract address using dedicated method
            address = self._extract_address(source.get("address", {}))
            
            # Build property result
            result = PropertyResult(
                listing_id=source.get("listing_id", ""),
                property_type=source.get("property_type", ""),
                price=source.get("price", 0),
                bedrooms=source.get("bedrooms", 0),
                bathrooms=source.get("bathrooms", 0),
                square_feet=source.get("square_feet", 0),
                address=address,
                description=source.get("description", ""),
                features=source.get("features", []),
                score=hit.get("_score") or 0.0
            )
            
            # Add distance if present (geo queries)
            if "sort" in hit and len(hit["sort"]) > 0:
                result.distance_km = hit["sort"][0]
            
            # Add highlights if present
            if request.include_highlights:
                result.highlights = self.extract_highlights(hit)
            
            results.append(result)
        
        # Build response
        return PropertySearchResponse(
            results=results,
            total_hits=self.calculate_total_hits(es_response),
            execution_time_ms=es_response.get("execution_time_ms", 0),
            applied_filters=request.filters
        )