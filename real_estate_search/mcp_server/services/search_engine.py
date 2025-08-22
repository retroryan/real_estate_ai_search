"""
Async search engine service for property searches.
Clean implementation with no Flask dependencies.
"""

import logging
from typing import List, Optional, Dict, Any
from elasticsearch import AsyncElasticsearch, NotFoundError

from models import (
    Property, PropertyHit, SearchResults,
    PropertySearchParams, GeoSearchParams,
    SearchMode, SortOrder, GeoDistanceUnit
)
from config.settings import settings

logger = logging.getLogger(__name__)


class SearchEngine:
    """Async search engine for properties."""
    
    def __init__(self, es_client: AsyncElasticsearch):
        """Initialize search engine with Elasticsearch client."""
        self.es = es_client
        self.index_name = settings.elasticsearch.index_name
        
    async def search(self, params: PropertySearchParams) -> SearchResults:
        """Execute property search based on parameters."""
        # Build Elasticsearch query
        query = self._build_query(params)
        
        # Add sorting
        sort = self._build_sort(params.sort_by)
        
        # Execute search
        try:
            response = await self.es.search(
                index=self.index_name,
                body={
                    "query": query,
                    "sort": sort,
                    "from": params.offset,
                    "size": params.max_results,
                    "track_total_hits": True,
                    "_source": True,
                    "highlight": self._build_highlights() if params.include_highlights else None,
                    "aggs": self._build_aggregations() if params.include_aggregations else None
                }
            )
            
            # Parse results
            return self._parse_results(response, params)
            
        except NotFoundError:
            logger.warning(f"Index {self.index_name} not found")
            return SearchResults(properties=[], total=0, hits=[], took_ms=0)
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise
    
    async def geo_search(self, params: GeoSearchParams) -> SearchResults:
        """Execute geographic radius search."""
        # Build geo query
        geo_query = {
            "bool": {
                "filter": [
                    {
                        "geo_distance": {
                            "distance": f"{params.radius}{params.unit.value}",
                            "address.location": {
                                "lat": params.center.lat,
                                "lon": params.center.lon
                            }
                        }
                    }
                ]
            }
        }
        
        # Add additional filters if provided
        if params.filters:
            filter_clauses = params.filters.to_elasticsearch_query()
            if filter_clauses.get("filter"):
                geo_query["bool"]["filter"].extend(filter_clauses["filter"])
        
        # Build sort
        sort = []
        if params.sort_by_distance:
            sort.append({
                "_geo_distance": {
                    "address.location": {
                        "lat": params.center.lat,
                        "lon": params.center.lon
                    },
                    "order": "asc",
                    "unit": params.unit.value
                }
            })
        
        # Execute search
        try:
            response = await self.es.search(
                index=self.index_name,
                body={
                    "query": geo_query,
                    "sort": sort,
                    "size": params.max_results,
                    "track_total_hits": True
                }
            )
            
            # Parse results with distance
            results = self._parse_results(response, None)
            
            # Extract distance from sort values
            for i, hit in enumerate(response["hits"]["hits"]):
                if "sort" in hit and len(hit["sort"]) > 0:
                    results.hits[i].distance = hit["sort"][0]
            
            return results
            
        except Exception as e:
            logger.error(f"Geo search error: {e}")
            raise
    
    async def find_similar(self, property_id: str, max_results: int = 10) -> List[Property]:
        """Find properties similar to a given property."""
        # Get the reference property
        reference = await self.get_property(property_id)
        if not reference:
            return []
        
        # Build more-like-this query
        mlt_query = {
            "more_like_this": {
                "fields": ["description", "features", "amenities", "address.city"],
                "like": [
                    {
                        "_index": self.index_name,
                        "_id": property_id
                    }
                ],
                "min_term_freq": 1,
                "max_query_terms": 25,
                "min_doc_freq": 1
            }
        }
        
        # Add filters for similar price range and size
        price_range = reference.price * 0.2  # 20% range
        filters = [
            {"range": {"price": {
                "gte": reference.price - price_range,
                "lte": reference.price + price_range
            }}},
            {"term": {"property_type": reference.property_type.value}},
            {"range": {"bedrooms": {
                "gte": max(0, reference.bedrooms - 1),
                "lte": reference.bedrooms + 1
            }}}
        ]
        
        # Exclude the reference property
        filters.append({"bool": {"must_not": {"term": {"_id": property_id}}}})
        
        query = {
            "bool": {
                "must": mlt_query,
                "filter": filters
            }
        }
        
        # Execute search
        try:
            response = await self.es.search(
                index=self.index_name,
                body={
                    "query": query,
                    "size": max_results
                }
            )
            
            # Parse properties
            properties = []
            for hit in response["hits"]["hits"]:
                prop = self._parse_property(hit)
                if prop:
                    properties.append(prop)
            
            return properties
            
        except Exception as e:
            logger.error(f"Similar properties search error: {e}")
            return []
    
    async def get_property(self, property_id: str) -> Optional[Property]:
        """Get a single property by ID."""
        try:
            response = await self.es.get(
                index=self.index_name,
                id=property_id
            )
            
            if response["found"]:
                return self._parse_property(response)
            
        except NotFoundError:
            logger.debug(f"Property {property_id} not found")
        except Exception as e:
            logger.error(f"Error getting property {property_id}: {e}")
        
        return None
    
    def _build_query(self, params: PropertySearchParams) -> Dict[str, Any]:
        """Build Elasticsearch query from search parameters."""
        must = []
        filter_clauses = []
        should = []
        
        # Handle different search modes
        if params.mode == SearchMode.semantic and params.query:
            # Semantic search using multi-match
            must.append({
                "multi_match": {
                    "query": params.query,
                    "fields": [
                        f"description^{settings.search.boost_description}",
                        f"features^{settings.search.boost_features}",
                        f"amenities^{settings.search.boost_amenities}",
                        f"address.city^{settings.search.boost_location}",
                        "address.state"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO" if settings.search.enable_fuzzy else None
                }
            })
        elif params.mode == SearchMode.lifestyle and params.query:
            # Lifestyle search focuses on features and amenities
            must.append({
                "multi_match": {
                    "query": params.query,
                    "fields": [
                        "features^3",
                        "amenities^3",
                        "description"
                    ],
                    "type": "most_fields"
                }
            })
        elif params.query:
            # Standard search
            must.append({
                "multi_match": {
                    "query": params.query,
                    "fields": ["description", "features", "amenities", "address.city"],
                    "type": "best_fields"
                }
            })
        
        # Location filter
        if params.location:
            should.append({"match": {"address.city": {"query": params.location, "boost": 2}}})
            should.append({"match": {"address.state": params.location}})
            should.append({"match": {"address.zip_code": params.location}})
        
        # Apply filters if provided
        if params.filters:
            filter_query = params.filters.to_elasticsearch_query()
            filter_clauses.extend(filter_query.get("filter", []))
            must.extend(filter_query.get("must", []))
        
        # Build final query
        if not must and not filter_clauses and not should:
            return {"match_all": {}}
        
        query = {"bool": {}}
        if must:
            query["bool"]["must"] = must
        if filter_clauses:
            query["bool"]["filter"] = filter_clauses
        if should:
            query["bool"]["should"] = should
            query["bool"]["minimum_should_match"] = 1
        
        return query
    
    def _build_sort(self, sort_order: Optional[SortOrder]) -> List[Dict]:
        """Build sort configuration."""
        if not sort_order or sort_order == SortOrder.relevance:
            return ["_score", {"listing_date": "desc"}]
        elif sort_order == SortOrder.price_asc:
            return [{"price": "asc"}]
        elif sort_order == SortOrder.price_desc:
            return [{"price": "desc"}]
        elif sort_order == SortOrder.newest:
            return [{"listing_date": "desc"}]
        elif sort_order == SortOrder.bedrooms:
            return [{"bedrooms": "desc"}]
        elif sort_order == SortOrder.square_feet:
            return [{"square_feet": "desc"}]
        else:
            return ["_score"]
    
    def _build_highlights(self) -> Dict[str, Any]:
        """Build highlight configuration."""
        return {
            "fields": {
                "description": {"number_of_fragments": 2},
                "features": {},
                "amenities": {}
            },
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"]
        }
    
    def _build_aggregations(self) -> Dict[str, Any]:
        """Build aggregation configuration."""
        return {
            "property_types": {
                "terms": {"field": "property_type", "size": 10}
            },
            "price_ranges": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 200000},
                        {"from": 200000, "to": 400000},
                        {"from": 400000, "to": 600000},
                        {"from": 600000, "to": 1000000},
                        {"from": 1000000}
                    ]
                }
            },
            "cities": {
                "terms": {"field": "address.city.keyword", "size": 20}
            },
            "bedroom_counts": {
                "terms": {"field": "bedrooms", "size": 10}
            },
            "avg_price": {
                "avg": {"field": "price"}
            },
            "avg_sqft": {
                "avg": {"field": "square_feet"}
            }
        }
    
    def _parse_results(self, response: Dict, params: Optional[PropertySearchParams]) -> SearchResults:
        """Parse Elasticsearch response into SearchResults."""
        hits = []
        properties = []
        
        for hit in response["hits"]["hits"]:
            prop = self._parse_property(hit)
            if prop:
                properties.append(prop)
                
                # Create PropertyHit with metadata
                property_hit = PropertyHit(
                    property=prop,
                    score=hit.get("_score"),
                    highlights=hit.get("highlight", {})
                )
                hits.append(property_hit)
        
        # Parse aggregations if present
        aggregations = None
        if "aggregations" in response:
            aggregations = response["aggregations"]
        
        return SearchResults(
            properties=properties,
            total=response["hits"]["total"]["value"],
            hits=hits,
            aggregations=aggregations,
            search_time_ms=response.get("took", 0)
        )
    
    def _parse_property(self, hit: Dict) -> Optional[Property]:
        """Parse Elasticsearch hit into Property model."""
        try:
            source = hit.get("_source", hit)
            
            # Add ID from document
            if "_id" in hit:
                source["id"] = hit["_id"]
            
            # Parse property
            return Property(**source)
            
        except Exception as e:
            logger.error(f"Error parsing property: {e}")
            return None