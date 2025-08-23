"""
Service for searching properties with constructor injection.
All search business logic lives here.
"""

from typing import List, Dict, Any, Optional
import logging
import time

from repositories.property_repository import PropertyRepository
from search.models import (
    SearchRequest, SearchResponse, SearchFilters, PropertyHit,
    GeoSearchParams, Aggregation, BucketAggregation, StatsAggregation
)
from search.enums import QueryType, AggregationName
from indexer.models import Property, Address, Neighborhood

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for searching properties.
    All dependencies injected through constructor.
    """
    
    def __init__(self, property_repository: PropertyRepository):
        """
        Initialize service with property repository.
        
        Args:
            property_repository: Repository for property queries
        """
        self.property_repository = property_repository
        logger.info("Search service initialized")
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute a property search.
        
        Args:
            request: SearchRequest with query parameters
            
        Returns:
            SearchResponse with results
        """
        start_time = time.time()
        
        # Build Elasticsearch query based on request type
        es_query = self._build_query(request)
        
        # Add pagination
        size = request.size
        from_ = (request.page - 1) * request.size
        
        # Execute search
        es_response = self.property_repository.search(es_query, size=size, from_=from_)
        
        # Convert response to SearchResponse
        took_ms = int((time.time() - start_time) * 1000)
        
        return self._build_response(es_response, request, took_ms)
    
    def get_facets(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get faceted search options.
        
        Args:
            query: Optional query to filter facets
            
        Returns:
            Facet aggregations
        """
        # Build aggregations
        aggs = {
            "property_type": {
                "terms": {"field": "property_type", "size": 20}
            },
            "price_range": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 500000, "key": "Under $500K"},
                        {"from": 500000, "to": 1000000, "key": "$500K-$1M"},
                        {"from": 1000000, "to": 2000000, "key": "$1M-$2M"},
                        {"from": 2000000, "key": "Over $2M"}
                    ]
                }
            },
            "cities": {
                "terms": {"field": "address.city.keyword", "size": 30}
            },
            "bedrooms": {
                "terms": {"field": "bedrooms", "size": 10}
            },
            "bathrooms": {
                "terms": {"field": "bathrooms", "size": 10}
            }
        }
        
        # Add Wikipedia-enhanced facets
        aggs.update({
            "poi_categories": {
                "nested": {"path": "nearby_poi"},
                "aggs": {
                    "categories": {
                        "terms": {"field": "nearby_poi.category", "size": 15}
                    }
                }
            },
            "has_enrichment": {
                "filters": {
                    "filters": {
                        "with_location": {"exists": {"field": "location_context"}},
                        "with_neighborhood": {"exists": {"field": "neighborhood_context"}},
                        "with_pois": {"exists": {"field": "nearby_poi"}}
                    }
                }
            }
        })
        
        # Get aggregations
        if query:
            # Filter aggregations by query
            query_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["description", "enriched_search_text"]
                    }
                },
                "aggs": aggs
            }
            es_response = self.property_repository.search(query_body, size=0)
            return es_response.get("aggregations", {})
        else:
            return self.property_repository.get_aggregations(aggs)
    
    def _build_query(self, request: SearchRequest) -> Dict[str, Any]:
        """
        Build Elasticsearch query from search request.
        
        Args:
            request: SearchRequest object
            
        Returns:
            Elasticsearch query dictionary
        """
        # Route based on query type
        if request.query_type == QueryType.TEXT:
            query_body = self._build_text_query(request)
        elif request.query_type == QueryType.FILTER:
            query_body = self._build_filter_query(request)
        elif request.query_type == QueryType.GEO:
            query_body = self._build_geo_query(request)
        elif request.query_type == QueryType.SIMILAR:
            query_body = self._build_similar_query(request)
        else:
            raise ValueError(f"Unsupported query type: {request.query_type}")
        
        # Add aggregations if requested
        if request.include_aggregations:
            query_body["aggs"] = self._build_aggregations()
        
        # Add highlighting if requested
        if request.include_highlights:
            query_body["highlight"] = {
                "fields": {
                    "description": {},
                    "enriched_search_text": {},
                    "location_context.location_summary": {},
                    "neighborhood_context.description": {}
                }
            }
        
        # Add sorting
        if request.sort_by:
            query_body["sort"] = self._build_sort(request.sort_by)
        
        return query_body
    
    def _build_text_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build text search query."""
        query_text = request.query_text or ""
        
        should_clauses = []
        if query_text:
            # Search across multiple fields with different boosts
            should_clauses.extend([
                {"match": {"description": {"query": query_text, "boost": 2}}},
                {"match": {"enriched_search_text": {"query": query_text, "boost": 1.5}}},
                {"match": {"features": query_text}},
                {"match": {"amenities": query_text}},
                {"match": {"location_context.location_summary": query_text}},
                {"match": {"location_context.key_topics": query_text}},
                {
                    "nested": {
                        "path": "nearby_poi",
                        "query": {
                            "match": {"nearby_poi.name": query_text}
                        }
                    }
                }
            ])
        
        query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1 if should_clauses else 0
                }
            }
        }
        
        # Add filters if present
        if request.filters:
            filter_clauses = self._build_filter_clauses(request.filters)
            if filter_clauses:
                query["query"]["bool"]["filter"] = filter_clauses
        
        return query
    
    def _build_filter_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build filter-only query."""
        if not request.filters:
            return {"query": {"match_all": {}}}
        
        filter_clauses = self._build_filter_clauses(request.filters)
        
        return {
            "query": {
                "bool": {
                    "filter": filter_clauses
                }
            }
        }
    
    def _build_geo_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build geographic search query."""
        if not request.geo_params:
            raise ValueError("geo_params required for GEO query type")
        
        geo = request.geo_params
        
        query = {
            "query": {
                "geo_distance": {
                    "distance": f"{geo.distance}{geo.unit.value}",
                    "address.location": {
                        "lat": geo.center.lat,
                        "lon": geo.center.lon
                    }
                }
            },
            "sort": [
                {
                    "_geo_distance": {
                        "address.location": {
                            "lat": geo.center.lat,
                            "lon": geo.center.lon
                        },
                        "order": "asc",
                        "unit": geo.unit.value
                    }
                }
            ]
        }
        
        # Add additional filters
        if geo.filters:
            filter_clauses = self._build_filter_clauses(geo.filters)
            if filter_clauses:
                query["query"] = {
                    "bool": {
                        "must": [query["query"]],
                        "filter": filter_clauses
                    }
                }
        
        return query
    
    def _build_similar_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build similarity search query."""
        if not request.similar_to_id:
            raise ValueError("similar_to_id required for SIMILAR query type")
        
        # Verify property exists
        source = self.property_repository.get_property_by_id(request.similar_to_id)
        if not source:
            raise ValueError(f"Property {request.similar_to_id} not found")
        
        query = {
            "query": {
                "more_like_this": {
                    "fields": [
                        "description",
                        "features",
                        "amenities",
                        "enriched_search_text",
                        "location_context.key_topics"
                    ],
                    "like": [
                        {
                            "_index": self.property_repository.index_name,
                            "_id": request.similar_to_id
                        }
                    ],
                    "min_term_freq": 1,
                    "max_query_terms": 12
                }
            }
        }
        
        # Add filters if present
        if request.filters:
            filter_clauses = self._build_filter_clauses(request.filters)
            if filter_clauses:
                query["query"] = {
                    "bool": {
                        "must": [query["query"]],
                        "filter": filter_clauses
                    }
                }
        
        return query
    
    def _build_filter_clauses(self, filters: SearchFilters) -> List[Dict[str, Any]]:
        """Build filter clauses from SearchFilters."""
        clauses = []
        
        # Price filters
        if filters.min_price or filters.max_price:
            price_range = {}
            if filters.min_price:
                price_range["gte"] = filters.min_price
            if filters.max_price:
                price_range["lte"] = filters.max_price
            clauses.append({"range": {"price": price_range}})
        
        # Size filters
        if filters.min_bedrooms:
            clauses.append({"range": {"bedrooms": {"gte": filters.min_bedrooms}}})
        if filters.max_bedrooms:
            clauses.append({"range": {"bedrooms": {"lte": filters.max_bedrooms}}})
        if filters.min_bathrooms:
            clauses.append({"range": {"bathrooms": {"gte": filters.min_bathrooms}}})
        if filters.max_bathrooms:
            clauses.append({"range": {"bathrooms": {"lte": filters.max_bathrooms}}})
        if filters.min_square_feet:
            clauses.append({"range": {"square_feet": {"gte": filters.min_square_feet}}})
        if filters.max_square_feet:
            clauses.append({"range": {"square_feet": {"lte": filters.max_square_feet}}})
        
        # Property type filter
        if filters.property_types:
            property_type_values = [pt.value for pt in filters.property_types]
            clauses.append({"terms": {"property_type": property_type_values}})
        
        # Status filter
        if filters.status:
            clauses.append({"term": {"status": filters.status.value}})
        
        # Location filters
        if filters.cities:
            clauses.append({"terms": {"address.city": filters.cities}})
        if filters.states:
            clauses.append({"terms": {"address.state": filters.states}})
        if filters.zip_codes:
            clauses.append({"terms": {"address.zip_code": filters.zip_codes}})
        
        # Feature filters
        if filters.features:
            clauses.append({"terms": {"features": filters.features}})
        if filters.amenities:
            clauses.append({"terms": {"amenities": filters.amenities}})
        
        return clauses
    
    def _build_aggregations(self) -> Dict[str, Any]:
        """Build standard aggregations."""
        return {
            "property_types": {
                "terms": {"field": "property_type", "size": 10}
            },
            "price_stats": {
                "stats": {"field": "price"}
            },
            "cities": {
                "terms": {"field": "address.city.keyword", "size": 20}
            }
        }
    
    def _build_sort(self, sort_by) -> List[Dict[str, Any]]:
        """Build sort configuration."""
        from indexer.enums import SortOrder
        
        if sort_by == SortOrder.PRICE_ASC:
            return [{"price": "asc"}]
        elif sort_by == SortOrder.PRICE_DESC:
            return [{"price": "desc"}]
        elif sort_by == SortOrder.DATE_DESC:
            return [{"listing_date": "desc"}]
        else:
            # Default to relevance (score)
            return ["_score"]
    
    def _build_response(
        self,
        es_response: Dict[str, Any],
        request: SearchRequest,
        took_ms: int
    ) -> SearchResponse:
        """
        Build SearchResponse from Elasticsearch response.
        
        Args:
            es_response: Raw Elasticsearch response
            request: Original search request
            took_ms: Query execution time
            
        Returns:
            SearchResponse object
        """
        hits_data = es_response.get('hits', {})
        total = hits_data.get('total', {}).get('value', 0)
        
        # Convert hits to PropertyHit objects
        hits = []
        for hit in hits_data.get('hits', []):
            # Extract property data
            property_data = hit['_source']
            
            # Safely create Address
            address_data = property_data.get('address', {})
            if address_data:
                if 'location' in address_data and isinstance(address_data['location'], dict):
                    from indexer.models import GeoLocation
                    address_data['location'] = GeoLocation(**address_data['location'])
                address = Address(**address_data)
                property_data['address'] = address
            
            # Safely create Neighborhood if present
            if 'neighborhood' in property_data and isinstance(property_data['neighborhood'], dict):
                try:
                    neighborhood = Neighborhood(**property_data['neighborhood'])
                    property_data['neighborhood'] = neighborhood
                except Exception:
                    # Skip invalid neighborhood data
                    property_data.pop('neighborhood', None)
            
            # Filter to valid Property fields to avoid validation errors
            valid_fields = {
                'listing_id', 'property_type', 'price', 'bedrooms', 'bathrooms',
                'square_feet', 'address', 'description', 'features', 'amenities',
                'neighborhood', 'status', 'listing_date', 'last_updated', 'images',
                'virtual_tour_url', 'year_built', 'lot_size', 'hoa_fee', 'parking',
                'mls_number', 'tax_assessed_value', 'annual_tax', 'search_tags',
                'days_on_market', 'price_per_sqft'
            }
            
            clean_property_data = {
                k: v for k, v in property_data.items()
                if k in valid_fields and v is not None
            }
            
            # Create Property object with error handling
            try:
                property_obj = Property(**clean_property_data)
            except Exception as e:
                logger.warning(f"Failed to create Property object: {e}, using minimal data")
                # Create minimal property with required fields only
                property_obj = Property(
                    listing_id=property_data.get('listing_id', 'unknown'),
                    property_type=property_data.get('property_type', 'other'),
                    price=property_data.get('price', 0),
                    bedrooms=property_data.get('bedrooms', 0),
                    bathrooms=property_data.get('bathrooms', 0),
                    address=address if 'address' in locals() else Address(
                        street="Unknown",
                        city="Unknown",
                        state="XX",
                        zip_code="00000"
                    )
                )
            
            # Extract distance if present
            distance = None
            if 'sort' in hit and isinstance(hit['sort'], list):
                for sort_value in hit['sort']:
                    if isinstance(sort_value, (int, float)):
                        distance = sort_value
                        break
            
            # Create PropertyHit
            property_hit = PropertyHit(
                doc_id=hit['_id'],
                score=hit.get('_score'),
                property=property_obj,
                distance=distance,
                highlights=hit.get('highlight', {}) if request.include_highlights else {},
                raw_hit=hit
            )
            hits.append(property_hit)
        
        # Calculate pagination
        total_pages = max(1, (total + request.size - 1) // request.size) if request.size > 0 else 1
        
        # Process aggregations
        aggregations = None
        if request.include_aggregations and 'aggregations' in es_response:
            aggregations = self._process_aggregations(es_response['aggregations'])
        
        return SearchResponse(
            hits=hits,
            total=total,
            page=request.page,
            size=request.size,
            total_pages=total_pages,
            took_ms=took_ms,
            aggregations=aggregations,
            request=request
        )
    
    def _process_aggregations(
        self,
        es_aggregations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Elasticsearch aggregations."""
        processed = {}
        
        for name, data in es_aggregations.items():
            if 'buckets' in data:
                processed[name] = data['buckets']
            elif any(k in data for k in ['count', 'min', 'max', 'avg', 'sum']):
                processed[name] = data
            else:
                processed[name] = data
        
        return processed