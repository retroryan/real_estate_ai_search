"""
Neighborhood search service implementation.
"""

import logging
from typing import Dict, Any, List, Optional
from .elasticsearch_compat import Elasticsearch

from .base import BaseSearchService
from .models import (
    NeighborhoodSearchRequest,
    NeighborhoodSearchResponse,
    NeighborhoodResult,
    NeighborhoodStatistics,
    RelatedProperty,
    RelatedWikipediaArticle
)

logger = logging.getLogger(__name__)


class NeighborhoodSearchService(BaseSearchService):
    """
    Service for searching neighborhoods and related entities.
    
    Handles location-based search, aggregated statistics,
    and cross-index queries for related properties and Wikipedia articles.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the neighborhood search service.
        
        Args:
            es_client: Elasticsearch client instance
        """
        super().__init__(es_client)
        self.wikipedia_index = "wikipedia"
        self.properties_index = "properties"
    
    def search(self, request: NeighborhoodSearchRequest) -> NeighborhoodSearchResponse:
        """
        Main search method for neighborhoods.
        
        Args:
            request: Neighborhood search request
            
        Returns:
            Neighborhood search response
        """
        try:
            # Build and execute main search query
            query = self._build_query(request)
            
            es_response = self.execute_search(
                index=self.wikipedia_index,
                query=query,
                size=request.size,
                from_offset=0
            )
            
            # Transform base response
            response = self._transform_response(es_response, request)
            
            # Add related data if requested
            if request.include_statistics or request.include_related_properties:
                response = self._add_related_data(response, request)
            
            if request.include_related_wikipedia:
                response = self._add_related_wikipedia(response, request)
            
            return response
            
        except Exception as e:
            logger.error(f"Neighborhood search failed: {str(e)}")
            raise
    
    def search_location(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        size: int = 10
    ) -> NeighborhoodSearchResponse:
        """
        Search neighborhoods by city and/or state.
        
        Args:
            city: City name
            state: State name
            size: Number of results
            
        Returns:
            Neighborhood search response
        """
        request = NeighborhoodSearchRequest(
            city=city,
            state=state,
            size=size
        )
        return self.search(request)
    
    def search_with_stats(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        size: int = 10
    ) -> NeighborhoodSearchResponse:
        """
        Search neighborhoods with aggregated property statistics.
        
        Args:
            city: City name
            state: State name
            size: Number of results
            
        Returns:
            Neighborhood search response with statistics
        """
        request = NeighborhoodSearchRequest(
            city=city,
            state=state,
            include_statistics=True,
            size=size
        )
        return self.search(request)
    
    def search_related(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        include_properties: bool = True,
        include_wikipedia: bool = True,
        size: int = 10
    ) -> NeighborhoodSearchResponse:
        """
        Search neighborhoods with related entities.
        
        Args:
            city: City name
            state: State name
            include_properties: Include related properties
            include_wikipedia: Include related Wikipedia articles
            size: Number of results
            
        Returns:
            Neighborhood search response with related entities
        """
        request = NeighborhoodSearchRequest(
            city=city,
            state=state,
            include_related_properties=include_properties,
            include_related_wikipedia=include_wikipedia,
            size=size
        )
        return self.search(request)
    
    def _build_query(self, request: NeighborhoodSearchRequest) -> Dict[str, Any]:
        """
        Build Elasticsearch query for neighborhood search.
        
        Args:
            request: Neighborhood search request
            
        Returns:
            Elasticsearch query DSL
        """
        bool_query = {"bool": {"must": [], "filter": []}}
        
        # Add category filter for neighborhoods
        bool_query["bool"]["filter"].append({
            "terms": {
                "categories": ["Neighborhoods", "Districts", "Communities"]
            }
        })
        
        # Add location filters
        if request.city:
            bool_query["bool"]["must"].append({
                "match": {
                    "full_content": {
                        "query": request.city,
                        "boost": 2
                    }
                }
            })
        
        if request.state:
            bool_query["bool"]["must"].append({
                "match": {
                    "full_content": {
                        "query": request.state,
                        "boost": 1.5
                    }
                }
            })
        
        # Add free text query if provided
        if request.query:
            bool_query["bool"]["must"].append({
                "multi_match": {
                    "query": request.query,
                    "fields": [
                        "title^3",
                        "summary^2",
                        "full_content"
                    ],
                    "type": "best_fields"
                }
            })
        
        # Default to match all if no specific criteria
        if not bool_query["bool"]["must"]:
            bool_query["bool"]["must"] = [{"match_all": {}}]
        
        query = {
            "query": bool_query,
            "_source": ["page_id", "title", "summary", "categories", "url"]
        }
        
        return query
    
    def _transform_response(
        self,
        es_response: Dict[str, Any],
        request: NeighborhoodSearchRequest
    ) -> NeighborhoodSearchResponse:
        """
        Transform Elasticsearch response to NeighborhoodSearchResponse.
        
        Args:
            es_response: Raw Elasticsearch response
            request: Original search request
            
        Returns:
            Transformed neighborhood search response
        """
        results = []
        
        for hit in es_response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            
            # Extract city and state from content or title
            city = request.city or self._extract_city(source)
            state = request.state or self._extract_state(source)
            
            result = NeighborhoodResult(
                name=source.get("title", ""),
                city=city or "Unknown",
                state=state or "Unknown",
                description=source.get("summary", ""),
                score=hit.get("_score", 0)
            )
            
            results.append(result)
        
        return NeighborhoodSearchResponse(
            results=results,
            total_hits=self.calculate_total_hits(es_response),
            execution_time_ms=es_response.get("execution_time_ms", 0)
        )
    
    def _add_related_data(
        self,
        response: NeighborhoodSearchResponse,
        request: NeighborhoodSearchRequest
    ) -> NeighborhoodSearchResponse:
        """
        Add related property data and statistics to response.
        
        Args:
            response: Base neighborhood response
            request: Original search request
            
        Returns:
            Response with added related data
        """
        if not response.results:
            return response
        
        # Get the first neighborhood for statistics
        neighborhood = response.results[0]
        
        # Build property search query
        property_query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"address.city": neighborhood.city}},
                        {"match": {"address.state": neighborhood.state}}
                    ]
                }
            },
            "size": 5 if request.include_related_properties else 0,
            "_source": ["listing_id", "address", "price", "property_type"]
        }
        
        # Add aggregations for statistics
        if request.include_statistics:
            property_query["aggs"] = {
                "total_properties": {"value_count": {"field": "listing_id"}},
                "avg_price": {"avg": {"field": "price"}},
                "avg_bedrooms": {"avg": {"field": "bedrooms"}},
                "avg_square_feet": {"avg": {"field": "square_feet"}},
                "property_types": {
                    "terms": {"field": "property_type", "size": 10}
                }
            }
        
        try:
            prop_response = self.es_client.search(
                index=self.properties_index,
                body=property_query
            )
            
            # Add statistics if requested
            if request.include_statistics and "aggregations" in prop_response:
                aggs = prop_response["aggregations"]
                
                property_types = {}
                if "property_types" in aggs and "buckets" in aggs["property_types"]:
                    for bucket in aggs["property_types"]["buckets"]:
                        property_types[bucket["key"]] = bucket["doc_count"]
                
                response.statistics = NeighborhoodStatistics(
                    total_properties=int(aggs.get("total_properties", {}).get("value", 0)),
                    avg_price=float(aggs.get("avg_price", {}).get("value", 0)),
                    avg_bedrooms=float(aggs.get("avg_bedrooms", {}).get("value", 0)),
                    avg_square_feet=float(aggs.get("avg_square_feet", {}).get("value", 0)),
                    property_types=property_types
                )
            
            # Add related properties if requested
            if request.include_related_properties:
                related_properties = []
                for hit in prop_response.get("hits", {}).get("hits", []):
                    source = hit["_source"]
                    address = source.get("address", {})
                    
                    related_properties.append(RelatedProperty(
                        listing_id=source.get("listing_id", ""),
                        address=f"{address.get('street', '')}, {address.get('city', '')}",
                        price=float(source.get("price", 0)),
                        property_type=source.get("property_type", "")
                    ))
                
                response.related_properties = related_properties
        
        except Exception as e:
            logger.warning(f"Failed to get related property data: {str(e)}")
        
        return response
    
    def _add_related_wikipedia(
        self,
        response: NeighborhoodSearchResponse,
        request: NeighborhoodSearchRequest
    ) -> NeighborhoodSearchResponse:
        """
        Add related Wikipedia articles to response.
        
        Args:
            response: Base neighborhood response
            request: Original search request
            
        Returns:
            Response with added Wikipedia articles
        """
        if not response.results or not request.include_related_wikipedia:
            return response
        
        neighborhood = response.results[0]
        
        # Search for related Wikipedia articles
        wiki_query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"full_content": neighborhood.city}},
                        {"match": {"full_content": neighborhood.state}}
                    ],
                    "must_not": [
                        {"terms": {"categories": ["Neighborhoods", "Districts", "Communities"]}}
                    ]
                }
            },
            "size": 5,
            "_source": ["page_id", "title", "summary"]
        }
        
        try:
            wiki_response = self.es_client.search(
                index=self.wikipedia_index,
                body=wiki_query
            )
            
            related_wikipedia = []
            for hit in wiki_response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                
                related_wikipedia.append(RelatedWikipediaArticle(
                    page_id=source.get("page_id", ""),
                    title=source.get("title", ""),
                    summary=source.get("summary", "")[:200],
                    relevance_score=hit.get("_score", 0)
                ))
            
            response.related_wikipedia = related_wikipedia
        
        except Exception as e:
            logger.warning(f"Failed to get related Wikipedia articles: {str(e)}")
        
        return response
    
    def _extract_city(self, source: Dict[str, Any]) -> Optional[str]:
        """
        Extract city name from Wikipedia article source.
        
        Args:
            source: Wikipedia article source
            
        Returns:
            City name or None
        """
        # Simple extraction from title (e.g., "Nob Hill, San Francisco")
        title = source.get("title", "")
        if ", " in title:
            parts = title.split(", ")
            if len(parts) >= 2:
                return parts[-1]
        return None
    
    def _extract_state(self, source: Dict[str, Any]) -> Optional[str]:
        """
        Extract state name from Wikipedia article source.
        
        Args:
            source: Wikipedia article source
            
        Returns:
            State name or None
        """
        # Look for common state abbreviations or names in content
        content = source.get("summary", "") + " " + source.get("title", "")
        
        # Common California references
        if any(term in content for term in ["California", "CA", "San Francisco Bay Area"]):
            return "California"
        
        return None