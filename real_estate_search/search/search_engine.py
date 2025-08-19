"""
Main search engine for property search operations.
Coordinates query building, execution, and result processing.
"""

from typing import List, Dict, Any, Optional, Tuple
import time
import structlog
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ApiError as ElasticsearchException,
    NotFoundError,
    RequestError
)

from ..config.settings import Settings
from ..indexer.models import Property, PropertyDocument
from ..indexer.enums import SortOrder, FieldName
from .models import (
    SearchRequest,
    SearchResponse,
    SearchFilters,
    GeoSearchParams,
    PropertyHit,
    SimilarPropertiesRequest
)
from .query_builder import QueryBuilder
from .aggregation_builder import AggregationBuilder
from .enums import QueryType, ScriptField, HighlightTag
from .exceptions import SearchError, QueryValidationError


logger = structlog.get_logger(__name__)


class PropertySearchEngine:
    """
    Main search engine for executing property searches.
    Integrates query building, aggregations, and result processing.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the search engine.
        
        Args:
            settings: Configuration settings. If None, loads from environment.
        """
        self.settings = settings or Settings.load()
        self.es_settings = self.settings.elasticsearch
        self.search_settings = self.settings.search
        
        self._es_client: Optional[Elasticsearch] = None
        self.query_builder = QueryBuilder()
        self.aggregation_builder = AggregationBuilder()
        
        self.index_alias = self.settings.index.alias
        self.logger = logger.bind(component="PropertySearchEngine")
    
    @property
    def es(self) -> Elasticsearch:
        """
        Get or create Elasticsearch client.
        
        Returns:
            Elasticsearch client instance.
        """
        if self._es_client is None:
            # Build connection parameters
            es_params = {
                "hosts": [self.es_settings.url],
                "request_timeout": self.es_settings.timeout,
                "retry_on_timeout": self.es_settings.retry_on_timeout,
                "max_retries": self.es_settings.max_retries
            }
            
            # Add authentication if configured
            if self.es_settings.has_auth:
                es_params["basic_auth"] = (
                    self.es_settings.username,
                    self.es_settings.password
                )
                self.logger.info("Using authenticated connection", username=self.es_settings.username)
            
            # Add SSL verification settings
            if self.es_settings.scheme == "https":
                es_params["verify_certs"] = self.es_settings.verify_certs
                if self.es_settings.ca_certs:
                    es_params["ca_certs"] = self.es_settings.ca_certs
            
            self._es_client = Elasticsearch(**es_params)
            
            # Verify connection
            if not self._es_client.ping():
                raise SearchError(
                    "Cannot connect to Elasticsearch",
                    error_code="CONNECTION_ERROR"
                )
        
        return self._es_client
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute a property search.
        
        Args:
            request: Validated search request
            
        Returns:
            Search response with results and aggregations
            
        Raises:
            SearchError: If search execution fails
            QueryValidationError: If query is invalid
        """
        start_time = time.time()
        
        try:
            # Build the query
            if request.query_type == QueryType.SIMILAR and request.similar_to_id:
                query = self.query_builder.build_more_like_this_query(
                    request.similar_to_id,
                    request.filters
                )
            else:
                query = self.query_builder.build_search_query(
                    request.query_text,
                    request.filters,
                    request.geo_params
                )
            
            # Build the search body
            search_body = self._build_search_body(query, request)
            
            # Log the query for debugging
            self.logger.debug("Executing search", query=search_body)
            
            # Execute search
            es_response = self.es.search(
                index=self.index_alias,
                body=search_body
            )
            
            # Process results
            properties = self._extract_properties(es_response)
            
            # Create response
            response = SearchResponse.from_elasticsearch(
                es_response,
                request,
                properties
            )
            
            # Log performance
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.logger.info(
                "Search completed",
                took_ms=response.took_ms,
                total_ms=elapsed_ms,
                hits=response.total
            )
            
            return response
            
        except RequestError as e:
            self.logger.error("Invalid search query", error=str(e))
            raise QueryValidationError(f"Invalid query: {e}")
        except Exception as e:
            self.logger.error("Search failed", error=str(e))
            raise SearchError(f"Search execution failed: {e}")
    
    def find_similar_properties(
        self,
        request: SimilarPropertiesRequest
    ) -> SearchResponse:
        """
        Find properties similar to a given property.
        
        Args:
            request: Similar properties request
            
        Returns:
            Search response with similar properties
        """
        # Convert to regular search request
        search_request = SearchRequest(
            query_type=QueryType.SIMILAR,
            similar_to_id=request.property_id,
            filters=request.filters,
            size=request.max_results,
            include_aggregations=False
        )
        
        response = self.search(search_request)
        
        # Filter out source property if requested
        if not request.include_source:
            response.hits = [
                hit for hit in response.hits
                if hit.doc_id != request.property_id
            ]
            response.total = len(response.hits)
        
        return response
    
    def geo_search(
        self,
        center_lat: float,
        center_lon: float,
        radius: int,
        unit: str = "km",
        filters: Optional[SearchFilters] = None,
        size: int = 50
    ) -> SearchResponse:
        """
        Search properties within a geographic radius.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius: Search radius
            unit: Distance unit (km, mi, etc.)
            filters: Additional filters
            size: Maximum results
            
        Returns:
            Search response with distance-sorted results
        """
        from .models import GeoPoint
        from .enums import GeoDistanceUnit
        
        # Create geo search params
        geo_params = GeoSearchParams(
            center=GeoPoint(lat=center_lat, lon=center_lon),
            distance=radius,
            unit=GeoDistanceUnit(unit),
            filters=filters
        )
        
        # Create search request
        request = SearchRequest(
            query_type=QueryType.GEO,
            geo_params=geo_params,
            filters=filters,
            size=size,
            sort_by=SortOrder.RELEVANCE,  # Will be overridden for geo
            include_aggregations=False
        )
        
        return self.search(request)
    
    def get_property_by_id(self, property_id: str) -> Optional[Property]:
        """
        Retrieve a single property by its document ID.
        
        Args:
            property_id: Elasticsearch document ID
            
        Returns:
            Property model or None if not found
        """
        try:
            response = self.es.get(
                index=self.index_alias,
                id=property_id
            )
            
            if response['found']:
                source = response['_source']
                return self._convert_to_property(source)
            
            return None
            
        except NotFoundError:
            return None
        except Exception as e:
            self.logger.error("Failed to get property", id=property_id, error=str(e))
            return None
    
    def _build_search_body(
        self,
        query: Dict[str, Any],
        request: SearchRequest
    ) -> Dict[str, Any]:
        """
        Build complete Elasticsearch search body.
        
        Args:
            query: Query DSL dictionary
            request: Search request parameters
            
        Returns:
            Complete search body
        """
        # Start with query
        body = {"query": query}
        
        # Add pagination
        body["from"] = (request.page - 1) * request.size
        body["size"] = request.size
        
        # Add sorting
        sort_config = self._build_sort_config(request)
        if sort_config:
            body["sort"] = sort_config
        
        # Add aggregations
        if request.include_aggregations:
            body["aggs"] = self.aggregation_builder.build_standard_aggregations()
        
        # Add highlighting
        if request.include_highlights:
            body["highlight"] = self._build_highlight_config()
        
        # Add source filtering
        if request.exclude_fields:
            body["_source"] = {
                "excludes": [field.value for field in request.exclude_fields]
            }
        
        # Track total hits accurately
        body["track_total_hits"] = True
        
        return body
    
    def _build_sort_config(self, request: SearchRequest) -> Optional[List[Dict]]:
        """
        Build sort configuration based on request.
        
        Args:
            request: Search request with sort preferences
            
        Returns:
            Sort configuration list or None
        """
        # Geo distance sort for geo searches
        if request.geo_params:
            return [{
                "_geo_distance": {
                    FieldName.ADDRESS_LOCATION: {
                        "lat": request.geo_params.center.lat,
                        "lon": request.geo_params.center.lon
                    },
                    "order": "asc",
                    "unit": request.geo_params.unit.value,
                    "distance_type": "arc"
                }
            }]
        
        # Standard sorting
        if request.sort_by == SortOrder.RELEVANCE:
            return None  # Use default relevance scoring
        
        sort_map = {
            SortOrder.PRICE_ASC: {FieldName.PRICE: {"order": "asc"}},
            SortOrder.PRICE_DESC: {FieldName.PRICE: {"order": "desc"}},
            SortOrder.DATE_DESC: {FieldName.LISTING_DATE: {"order": "desc"}},
            SortOrder.SIZE_DESC: {FieldName.SQUARE_FEET: {"order": "desc"}},
            SortOrder.BEDROOMS_DESC: {FieldName.BEDROOMS: {"order": "desc"}}
        }
        
        sort_config = sort_map.get(request.sort_by)
        return [sort_config] if sort_config else None
    
    def _build_highlight_config(self) -> Dict[str, Any]:
        """
        Build highlighting configuration.
        
        Returns:
            Highlight configuration dictionary
        """
        return {
            "fields": {
                FieldName.DESCRIPTION: {
                    "fragment_size": 150,
                    "number_of_fragments": 3
                },
                FieldName.FEATURES: {},
                FieldName.AMENITIES: {},
                FieldName.SEARCH_TAGS: {}
            },
            "pre_tags": [HighlightTag.OPEN],
            "post_tags": [HighlightTag.CLOSE]
        }
    
    def _extract_properties(self, es_response: Dict[str, Any]) -> List[Property]:
        """
        Extract Property models from Elasticsearch response.
        
        Args:
            es_response: Raw Elasticsearch response
            
        Returns:
            List of Property models
        """
        properties = []
        
        for hit in es_response.get('hits', {}).get('hits', []):
            source = hit.get('_source', {})
            property_model = self._convert_to_property(source)
            if property_model:
                properties.append(property_model)
        
        return properties
    
    def _convert_to_property(self, source: Dict[str, Any]) -> Optional[Property]:
        """
        Convert Elasticsearch document to Property model.
        
        Args:
            source: Document source from Elasticsearch
            
        Returns:
            Property model or None if conversion fails
        """
        try:
            # Convert dates from ISO format
            if 'listing_date' in source and source['listing_date']:
                from datetime import datetime
                source['listing_date'] = datetime.fromisoformat(source['listing_date'])
            
            if 'last_updated' in source and source['last_updated']:
                from datetime import datetime
                source['last_updated'] = datetime.fromisoformat(source['last_updated'])
            
            # Convert location format
            if 'address' in source and 'location' in source['address']:
                location = source['address']['location']
                if isinstance(location, dict) and 'lat' in location and 'lon' in location:
                    from ..indexer.models import GeoLocation
                    source['address']['location'] = GeoLocation(
                        lat=location['lat'],
                        lon=location['lon']
                    )
            
            # Create Property model
            from ..indexer.models import Property, Address, Neighborhood, Parking
            from ..indexer.enums import PropertyType, PropertyStatus, ParkingType
            
            # Handle nested objects
            if 'address' in source:
                source['address'] = Address(**source['address'])
            
            if 'neighborhood' in source and source['neighborhood']:
                source['neighborhood'] = Neighborhood(**source['neighborhood'])
            
            if 'parking' in source and source['parking']:
                parking_data = source['parking']
                if 'type' in parking_data and parking_data['type']:
                    parking_data['type'] = ParkingType(parking_data['type'])
                source['parking'] = Parking(**parking_data)
            
            # Convert enums
            if 'property_type' in source:
                source['property_type'] = PropertyType(source['property_type'])
            
            if 'status' in source:
                source['status'] = PropertyStatus(source['status'])
            
            return Property(**source)
            
        except Exception as e:
            self.logger.warning("Failed to convert document to Property", error=str(e))
            return None
    
    def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._es_client:
            self._es_client.close()
            self._es_client = None
            self.logger.info("Closed Elasticsearch connection")