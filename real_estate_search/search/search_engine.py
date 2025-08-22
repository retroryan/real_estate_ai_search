"""
Search engine with Wikipedia-based capabilities.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import logging

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ApiError

from ..config.settings import Settings
from .models import SearchRequest, SearchResponse, Aggregation
from .enums import QueryType

logger = logging.getLogger(__name__)


class SearchMode(str, Enum):
    """Search modes for different query types."""
    STANDARD = "standard"
    LIFESTYLE = "lifestyle"
    POI_PROXIMITY = "poi_proximity"
    CULTURAL = "cultural"
    INVESTMENT = "investment"


class SearchEngine:
    """Search engine with Wikipedia-enhanced capabilities."""
    
    def __init__(
        self,
        es_client: Optional[Elasticsearch] = None,
        index_name: str = "properties",
        settings: Optional[Settings] = None
    ):
        """Initialize the search engine."""
        self.settings = settings or Settings.load()
        self.es_client = es_client or self._create_es_client()
        self.index_name = index_name
    
    def _create_es_client(self) -> Elasticsearch:
        """Create Elasticsearch client."""
        # Build proper URL with scheme from settings
        url = f"{self.settings.elasticsearch.scheme}://{self.settings.elasticsearch.host}:{self.settings.elasticsearch.port}"
        
        es_config = {
            "hosts": [url],
            "verify_certs": self.settings.elasticsearch.verify_certs,
            "request_timeout": self.settings.elasticsearch.timeout
        }
        
        if self.settings.elasticsearch.has_auth:
            es_config["basic_auth"] = (
                self.settings.elasticsearch.username,
                self.settings.elasticsearch.password
            )
        
        return Elasticsearch(**es_config)
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """
        THE ONLY search method. Always accepts SearchRequest, always returns SearchResponse.
        
        Args:
            request: SearchRequest object defining query parameters
            
        Returns:
            SearchResponse with properly typed property results
        """
        import time
        from .models import SearchResponse, PropertyHit
        from ..indexer.models import Property, Address, Neighborhood
        
        start_time = time.time()
        
        # Build query based on search_mode if provided, otherwise use query_type
        if request.search_mode:
            # Route based on search mode
            if request.search_mode == SearchMode.STANDARD:
                es_query = self._build_standard_query(
                    request.query_text, 
                    self._convert_filters_to_dict(request.filters) if request.filters else None,
                    wikipedia_boost=True
                )
            elif request.search_mode == SearchMode.LIFESTYLE:
                es_query = self._build_lifestyle_query(
                    request.query_text,
                    self._convert_filters_to_dict(request.filters) if request.filters else None
                )
            elif request.search_mode == SearchMode.POI_PROXIMITY:
                es_query = self._build_poi_proximity_query(
                    request.query_text,
                    self._convert_filters_to_dict(request.filters) if request.filters else None
                )
            elif request.search_mode == SearchMode.CULTURAL:
                es_query = self._build_cultural_query(
                    request.query_text,
                    self._convert_filters_to_dict(request.filters) if request.filters else None
                )
            elif request.search_mode == SearchMode.INVESTMENT:
                es_query = self._build_investment_query(
                    request.query_text,
                    self._convert_filters_to_dict(request.filters) if request.filters else None
                )
            else:
                raise ValueError(f"Unknown search mode: {request.search_mode}")
        else:
            # Fall back to query_type routing
            if request.query_type == QueryType.TEXT:
                es_query = self._build_text_query(request)
            elif request.query_type == QueryType.FILTER:
                es_query = self._build_filter_query(request)
            elif request.query_type == QueryType.GEO:
                es_query = self._build_geo_query(request)
            elif request.query_type == QueryType.SIMILAR:
                es_query = self._build_similar_query(request)
            else:
                raise ValueError(f"Unknown query type: {request.query_type}")
        
        # Add pagination
        es_query["size"] = request.size
        es_query["from"] = (request.page - 1) * request.size
        
        # Add highlighting if requested
        if request.include_highlights:
            es_query["highlight"] = {
                "fields": {
                    "description": {},
                    "enriched_search_text": {},
                    "wikipedia_summary": {},
                    "wikipedia_topics": {}
                }
            }
        
        try:
            # Execute search
            es_response = self.es_client.search(index=self.index_name, body=es_query)
            took_ms = int((time.time() - start_time) * 1000)
            
            # Convert to SearchResponse - ONE WAY ONLY
            return self._build_response(es_response, request, took_ms)
            
        except ApiError as e:
            logger.error(f"Search error: {e}")
            
            # Return error response with proper typing
            return SearchResponse(
                hits=[],
                total=0,
                page=request.page,
                size=request.size,
                total_pages=0,
                took_ms=0,
                aggregations=None,
                request=request
            )
    
    def _build_text_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build text search query."""
        query = request.query_text or ""
        should_clauses = []
        
        if query:
            should_clauses.extend([
                {"match": {"description": {"query": query, "boost": 2}}},
                {"match": {"features": query}},
                {"match": {"amenities": query}},
                {"match": {"search_tags": query}},
                {"match": {"enriched_search_text": {"query": query, "boost": 1.5}}},
                {"match": {"wikipedia_summary": query}},
                {"match": {"wikipedia_topics": query}}
            ])
        
        query_body = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1 if should_clauses else 0
                }
            }
        }
        
        # Add filters if present
        if request.filters:
            filter_clauses = self._build_filter_clauses_from_request(request.filters)
            if filter_clauses:
                query_body["query"]["bool"]["filter"] = filter_clauses
        
        return query_body
    
    def _build_filter_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build filter-only query."""
        if not request.filters:
            return {"query": {"match_all": {}}}
        
        filter_clauses = self._build_filter_clauses_from_request(request.filters)
        
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
        
        geo_params = request.geo_params
        
        query_body = {
            "query": {
                "geo_distance": {
                    "distance": f"{geo_params.distance}{geo_params.unit.value}",
                    "address.location": {
                        "lat": geo_params.center.lat,
                        "lon": geo_params.center.lon
                    }
                }
            },
            "sort": [
                {
                    "_geo_distance": {
                        "address.location": {
                            "lat": geo_params.center.lat,
                            "lon": geo_params.center.lon
                        },
                        "order": "asc",
                        "unit": geo_params.unit.value
                    }
                }
            ]
        }
        
        # Add additional filters
        if geo_params.filters:
            filter_clauses = self._build_filter_clauses_from_request(geo_params.filters)
            if filter_clauses:
                # Combine geo query with filters
                query_body["query"] = {
                    "bool": {
                        "must": [query_body["query"]],
                        "filter": filter_clauses
                    }
                }
        
        return query_body
    
    def _build_similar_query(self, request: SearchRequest) -> Dict[str, Any]:
        """Build similarity search query."""
        if not request.similar_to_id:
            raise ValueError("similar_to_id required for SIMILAR query type")
        
        # Get the source document first to validate it exists
        try:
            source_doc = self.es_client.get(index=self.index_name, id=request.similar_to_id)
        except ApiError:
            raise ValueError(f"Property {request.similar_to_id} not found")
        
        query_body = {
            "query": {
                "more_like_this": {
                    "fields": ["description", "features", "amenities", "enriched_search_text"],
                    "like": [
                        {
                            "_index": self.index_name,
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
            filter_clauses = self._build_filter_clauses_from_request(request.filters)
            if filter_clauses:
                query_body["query"] = {
                    "bool": {
                        "must": [query_body["query"]],
                        "filter": filter_clauses
                    }
                }
        
        return query_body
    
    def _build_filter_clauses_from_request(self, filters: 'SearchFilters') -> List[Dict[str, Any]]:
        """Build filter clauses from SearchFilters object."""
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
            clauses.append({"terms": {"address.city": [city.lower() for city in filters.cities]}})
        if filters.states:
            clauses.append({"terms": {"address.state": filters.states}})
        if filters.zip_codes:
            clauses.append({"terms": {"address.zip_code": filters.zip_codes}})
        
        # Feature filters
        if filters.features:
            clauses.append({"terms": {"features": [f.lower() for f in filters.features]}})
        if filters.amenities:
            clauses.append({"terms": {"amenities": [a.lower() for a in filters.amenities]}})
        
        return clauses
    
    def _build_response(self, es_response: Dict[str, Any], request: SearchRequest, took_ms: int) -> SearchResponse:
        """Convert ES response to SearchResponse. NO VARIATIONS."""
        from .models import SearchResponse, PropertyHit
        from ..indexer.models import Property, Address, Neighborhood
        
        hits = []
        for hit in es_response.get('hits', {}).get('hits', []):
            # Extract property data from _source
            property_data = hit['_source']
            
            # Create Address model if address data exists
            address_data = property_data.get('address', {})
            if address_data:
                # Handle nested location data
                if 'location' in address_data and isinstance(address_data['location'], dict):
                    from ..indexer.models import GeoLocation
                    address_data['location'] = GeoLocation(**address_data['location'])
                address = Address(**address_data)
                property_data['address'] = address
            
            # Create Neighborhood model if data exists
            neighborhood_data = property_data.get('neighborhood')
            if neighborhood_data and isinstance(neighborhood_data, dict):
                neighborhood = Neighborhood(**neighborhood_data)
                property_data['neighborhood'] = neighborhood
            
            # Filter property data to only include fields that exist in Property model
            property_fields = ['listing_id', 'property_type', 'price', 'bedrooms', 
                             'bathrooms', 'square_feet', 'address', 'description', 
                             'features', 'amenities', 'neighborhood', 'status', 
                             'listing_date', 'last_updated', 'images', 'virtual_tour_url',
                             'year_built', 'lot_size', 'parking_spaces', 'hoa_fee']
            
            clean_property_data = {k: v for k, v in property_data.items() 
                                  if k in property_fields and v is not None}
            
            # Create Property object - let it fail if invalid
            property_obj = Property(**clean_property_data)
            
            # Extract distance from sort if this was a geo query
            distance = None
            if 'sort' in hit and isinstance(hit['sort'], list):
                for sort_value in hit['sort']:
                    if isinstance(sort_value, (int, float)):
                        distance = sort_value
                        break
            
            # Create PropertyHit with raw hit for Wikipedia data access
            property_hit = PropertyHit(
                doc_id=hit['_id'],
                score=hit.get('_score', 0),
                property=property_obj,
                distance=distance,
                highlights=hit.get('highlight', {}) if request.include_highlights else {},
                raw_hit=hit  # Store raw hit for accessing enrichment data
            )
            hits.append(property_hit)
        
        # Calculate pagination
        total = es_response.get('hits', {}).get('total', {}).get('value', 0)
        total_pages = max(1, (total + request.size - 1) // request.size)
        
        return SearchResponse(
            hits=hits,
            total=total,
            page=request.page,
            size=request.size,
            total_pages=total_pages,
            took_ms=took_ms,
            aggregations=es_response.get('aggregations'),
            request=request
        )
    
    def _build_standard_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        wikipedia_boost: bool
    ) -> Dict[str, Any]:
        """Build standard search query with Wikipedia enhancement."""
        must_clauses = []
        should_clauses = []
        filter_clauses = []
        
        # Multi-field search (only if we have a query)
        if query:
            should_clauses.extend([
                {"match": {"description": {"query": query, "boost": 2}}},
                {"match": {"features": query}},
                {"match": {"amenities": query}},
                {"match": {"search_tags": query}}
            ])
            
            # Wikipedia-enhanced search
            if wikipedia_boost:
                should_clauses.extend([
                    {"match": {"enriched_search_text": {"query": query, "boost": 1.5}}},
                    {"match": {"location_context.location_summary": query}},
                    {"match": {"location_context.key_topics": query}},
                    {"match": {"neighborhood_context.description": query}},
                    {
                        "nested": {
                            "path": "nearby_poi",
                            "query": {
                                "match": {"nearby_poi.name": query}
                            }
                        }
                    }
                ])
        
        # Apply filters
        if filters:
            filter_clauses = self._build_filter_clauses(filters)
        
        # Build final query
        if should_clauses:
            query_body = {
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                }
            }
        elif filter_clauses:
            # Filter-only query
            query_body = {
                "query": {
                    "bool": {
                        "filter": filter_clauses
                    }
                }
            }
        else:
            # Match all
            query_body = {
                "query": {
                    "match_all": {}
                }
            }
        
        if should_clauses and filter_clauses:
            query_body["query"]["bool"]["filter"] = filter_clauses
        
        # Add function score for Wikipedia-enriched results
        if wikipedia_boost:
            query_body = self._add_wikipedia_scoring(query_body)
        
        return query_body
    
    def _build_lifestyle_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build lifestyle-based search query."""
        lifestyle_keywords = query.lower().split()
        
        should_clauses = [
            {"match": {"enriched_search_text": query}},
            {"terms": {"location_context.key_topics": lifestyle_keywords}},
            {"match": {"location_context.location_summary": query}},
            {"terms": {"features": lifestyle_keywords}},
            {"terms": {"amenities": lifestyle_keywords}},
            {
                "nested": {
                    "path": "nearby_poi",
                    "query": {
                        "bool": {
                            "should": [
                                {"terms": {"nearby_poi.category": lifestyle_keywords}},
                                {"match": {"nearby_poi.description": query}}
                            ]
                        }
                    }
                }
            }
        ]
        
        query_body = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 2
                }
            },
            "sort": [
                {"location_scores.overall_desirability": {"order": "desc"}},
                "_score"
            ]
        }
        
        if filters:
            query_body["query"]["bool"]["filter"] = self._build_filter_clauses(filters)
        
        return query_body
    
    def _build_poi_proximity_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build POI proximity search query."""
        poi_name = query
        
        return {
            "query": {
                "nested": {
                    "path": "nearby_poi",
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"nearby_poi.name": {"query": poi_name, "boost": 2.0}}},
                                {"match": {"nearby_poi.description": poi_name}},
                                {"match": {"nearby_poi.category": poi_name}}
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "score_mode": "max",
                    "inner_hits": {
                        "size": 5,
                        "_source": ["nearby_poi.name", "nearby_poi.category", "nearby_poi.significance_score"]
                    }
                }
            },
            "sort": [
                {
                    "nearby_poi.significance_score": {
                        "order": "desc",
                        "nested": {
                            "path": "nearby_poi",
                            "filter": {
                                "bool": {
                                    "should": [
                                        {"match": {"nearby_poi.name": poi_name}},
                                        {"match": {"nearby_poi.description": poi_name}},
                                        {"match": {"nearby_poi.category": poi_name}}
                                    ]
                                }
                            }
                        }
                    }
                }
            ]
        }
    
    def _build_cultural_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build cultural amenities search query."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"location_context.cultural_features": query}},
                        {"match": {"enriched_search_text": "museum gallery theater arts"}},
                        {
                            "nested": {
                                "path": "nearby_poi",
                                "query": {
                                    "terms": {
                                        "nearby_poi.category": ["museum", "cultural", "entertainment"]
                                    }
                                }
                            }
                        }
                    ],
                    "filter": self._build_filter_clauses(filters) if filters else []
                }
            },
            "sort": [
                {"location_scores.cultural_richness": {"order": "desc"}},
                "_score"
            ]
        }
    
    def _build_investment_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build investment property search query."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"enriched_search_text": query}},
                        {"range": {"location_scores.tourist_appeal": {"gte": 0.7}}},
                        {"range": {"location_scores.overall_desirability": {"gte": 0.75}}},
                        {
                            "nested": {
                                "path": "nearby_poi",
                                "query": {
                                    "range": {"nearby_poi.significance_score": {"gte": 0.8}}
                                }
                            }
                        }
                    ],
                    "filter": self._build_filter_clauses(filters) if filters else []
                }
            },
            "sort": [
                {"location_scores.tourist_appeal": {"order": "desc"}},
                {"location_scores.overall_desirability": {"order": "desc"}},
                "_score"
            ]
        }
    
    def _convert_filters_to_dict(self, filters: 'SearchFilters') -> Dict[str, Any]:
        """Convert SearchFilters model to dictionary format."""
        result = {}
        
        if filters.min_price or filters.max_price:
            result['price'] = {}
            if filters.min_price:
                result['price']['gte'] = filters.min_price
            if filters.max_price:
                result['price']['lte'] = filters.max_price
        
        if filters.cities:
            result['address.city'] = filters.cities
        if filters.states:
            result['address.state'] = filters.states
        if filters.property_types:
            result['property_type'] = [pt.value for pt in filters.property_types]
        if filters.min_bedrooms:
            result['bedrooms'] = {'gte': filters.min_bedrooms}
        
        # Add max_distance_miles if present (for POI searches)
        if hasattr(filters, 'max_distance_miles'):
            result['max_distance_miles'] = getattr(filters, 'max_distance_miles', 2.0)
            
        return result
    
    def _build_filter_clauses(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filter clauses from filter dictionary."""
        clauses = []
        
        for field, value in filters.items():
            if isinstance(value, dict):
                # Range query
                clauses.append({"range": {field: value}})
            elif isinstance(value, list):
                # Terms query
                clauses.append({"terms": {field: value}})
            else:
                # Term query
                clauses.append({"term": {field: value}})
        
        return clauses
    
    def _add_wikipedia_scoring(self, query_body: Dict[str, Any]) -> Dict[str, Any]:
        """Add function scoring based on Wikipedia enrichment."""
        return {
            "query": {
                "function_score": {
                    "query": query_body["query"],
                    "functions": [
                        {
                            "field_value_factor": {
                                "field": "location_scores.overall_desirability",
                                "factor": 2,
                                "modifier": "sqrt",
                                "missing": 0.5
                            },
                            "weight": 2
                        },
                        {
                            "filter": {
                                "exists": {"field": "location_context.wikipedia_page_id"}
                            },
                            "weight": 1.3
                        },
                        {
                            "filter": {
                                "nested": {
                                    "path": "nearby_poi",
                                    "query": {
                                        "range": {
                                            "nearby_poi.significance_score": {"gte": 0.7}
                                        }
                                    }
                                }
                            },
                            "weight": 1.5
                        }
                    ],
                    "boost_mode": "multiply",
                    "score_mode": "sum"
                }
            }
        }
    
    def _format_response(self, es_response: Dict[str, Any]) -> Dict[str, Any]:
        """Format Elasticsearch response for API consumption."""
        hits = []
        
        for hit in es_response.get("hits", {}).get("hits", []):
            formatted_hit = {
                "listing_id": hit["_id"],
                "score": hit.get("_score"),
                **hit["_source"]
            }
            
            # Add highlights if present
            if "highlight" in hit:
                formatted_hit["highlights"] = hit["highlight"]
            
            # Add inner hits for POI queries
            if "inner_hits" in hit:
                formatted_hit["matching_pois"] = [
                    poi["_source"] for poi in 
                    hit["inner_hits"].get("nearby_poi", {}).get("hits", {}).get("hits", [])
                ]
            
            hits.append(formatted_hit)
        
        return {
            "total": es_response.get("hits", {}).get("total", {}).get("value", 0),
            "hits": hits,
            "aggregations": es_response.get("aggregations", {})
        }
    
    
    
    def get_facets(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Get faceted search options with Wikipedia-derived facets."""
        base_query = {"match_all": {}}
        if query:
            base_query = {"match": {"enriched_search_text": query}}
        
        facet_query = {
            "size": 0,
            "query": base_query,
            "aggs": {
                # Traditional facets
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
                "neighborhoods": {
                    "terms": {"field": "neighborhood.name.keyword", "size": 30}
                },
                
                # Wikipedia-enhanced facets
                "cultural_features": {
                    "terms": {"field": "location_context.cultural_features", "size": 20}
                },
                "recreational_features": {
                    "terms": {"field": "location_context.recreational_features", "size": 20}
                },
                "architectural_styles": {
                    "terms": {"field": "neighborhood_context.architectural_style", "size": 15}
                },
                "poi_categories": {
                    "nested": {"path": "nearby_poi"},
                    "aggs": {
                        "categories": {
                            "terms": {"field": "nearby_poi.category", "size": 15}
                        }
                    }
                },
                "location_quality": {
                    "range": {
                        "field": "location_scores.overall_desirability",
                        "ranges": [
                            {"from": 0.8, "key": "Premium Location"},
                            {"from": 0.6, "to": 0.8, "key": "Desirable Location"},
                            {"from": 0.4, "to": 0.6, "key": "Standard Location"},
                            {"to": 0.4, "key": "Developing Area"}
                        ]
                    }
                }
            }
        }
        
        try:
            response = self.es_client.search(index=self.index_name, body=facet_query)
            return response.get("aggregations", {})
        except ApiError as e:
            logger.error(f"Facet query error: {e}")
            return {}

