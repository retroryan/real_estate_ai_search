"""Property search service for semantic and text search."""

import time
from typing import Dict, Any, List, Optional

from ..settings import MCPServerConfig
from ..models.search import (
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyFilter,
    SearchMetadata,
    Aggregation
)
from .elasticsearch_client import ElasticsearchClient
from ...embeddings import QueryEmbeddingService
from ..utils.logging import get_logger


logger = get_logger(__name__)


class PropertySearchService:
    """Service for searching properties."""
    
    def __init__(
        self,
        config: MCPServerConfig,
        es_client: ElasticsearchClient,
        embedding_service: QueryEmbeddingService
    ):
        """Initialize property search service.
        
        Args:
            config: Server configuration
            es_client: Elasticsearch client
            embedding_service: Embedding service
        """
        self.config = config
        self.es_client = es_client
        self.embedding_service = embedding_service
        self.index_name = config.elasticsearch.property_index
    
    def build_filter_query(self, filters: Optional[PropertyFilter]) -> List[Dict[str, Any]]:
        """Build Elasticsearch filter query from filters.
        
        Args:
            filters: Property filters
            
        Returns:
            List of filter clauses
        """
        if not filters:
            return []
        
        filter_clauses = []
        
        # Property type filter
        if filters.property_type:
            filter_clauses.append({
                "term": {"property_type": filters.property_type}
            })
        
        # Price range
        if filters.min_price is not None or filters.max_price is not None:
            price_range = {}
            if filters.min_price is not None:
                price_range["gte"] = filters.min_price
            if filters.max_price is not None:
                price_range["lte"] = filters.max_price
            filter_clauses.append({"range": {"price": price_range}})
        
        # Bedroom range
        if filters.min_bedrooms is not None or filters.max_bedrooms is not None:
            bedroom_range = {}
            if filters.min_bedrooms is not None:
                bedroom_range["gte"] = filters.min_bedrooms
            if filters.max_bedrooms is not None:
                bedroom_range["lte"] = filters.max_bedrooms
            filter_clauses.append({"range": {"bedrooms": bedroom_range}})
        
        # Bathroom range
        if filters.min_bathrooms is not None or filters.max_bathrooms is not None:
            bathroom_range = {}
            if filters.min_bathrooms is not None:
                bathroom_range["gte"] = filters.min_bathrooms
            if filters.max_bathrooms is not None:
                bathroom_range["lte"] = filters.max_bathrooms
            filter_clauses.append({"range": {"bathrooms": bathroom_range}})
        
        # Square feet range
        if filters.min_square_feet is not None or filters.max_square_feet is not None:
            sqft_range = {}
            if filters.min_square_feet is not None:
                sqft_range["gte"] = filters.min_square_feet
            if filters.max_square_feet is not None:
                sqft_range["lte"] = filters.max_square_feet
            filter_clauses.append({"range": {"square_feet": sqft_range}})
        
        # Location filters
        if filters.city:
            filter_clauses.append({
                "term": {"address.city": filters.city.lower()}
            })
        
        if filters.state:
            filter_clauses.append({
                "term": {"address.state": filters.state.upper()}
            })
        
        if filters.zip_code:
            filter_clauses.append({
                "term": {"address.zip_code": filters.zip_code}
            })
        
        if filters.neighborhood_id:
            filter_clauses.append({
                "term": {"neighborhood.id": filters.neighborhood_id}
            })
        
        # Geo-distance filter
        if filters.center_lat is not None and filters.center_lon is not None and filters.radius_km:
            filter_clauses.append({
                "geo_distance": {
                    "distance": f"{filters.radius_km}km",
                    "address.location": {
                        "lat": filters.center_lat,
                        "lon": filters.center_lon
                    }
                }
            })
        
        # Status filter
        if filters.status:
            filter_clauses.append({
                "term": {"status": filters.status}
            })
        
        # Days on market filter
        if filters.max_days_on_market is not None:
            filter_clauses.append({
                "range": {"days_on_market": {"lte": filters.max_days_on_market}}
            })
        
        return filter_clauses
    
    def build_text_query(self, query: str) -> Dict[str, Any]:
        """Build text search query.
        
        Args:
            query: Search query text
            
        Returns:
            Text search query
        """
        return {
            "multi_match": {
                "query": query,
                "fields": [
                    "description^3",
                    "enriched_search_text^2",
                    "features^1.5",
                    "amenities^1.5",
                    "search_tags",
                    "address.street",
                    "address.city",
                    "neighborhood.name",
                    "location_context.location_summary",
                    "location_context.historical_significance",
                    "neighborhood_context.description",
                    "neighborhood_context.character"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO" if self.config.search.enable_fuzzy else None
            }
        }
    
    def build_vector_query(self, query_embedding: List[float]) -> Dict[str, Any]:
        """Build vector search query.
        
        Args:
            query_embedding: Query embedding vector
            
        Returns:
            Vector search query
        """
        return {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                    "params": {
                        "query_vector": query_embedding
                    }
                }
            }
        }
    
    def build_hybrid_query(
        self,
        text_query: Dict[str, Any],
        vector_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build hybrid search query combining text and vector.
        
        Args:
            text_query: Text search query
            vector_query: Vector search query
            
        Returns:
            Hybrid search query
        """
        return {
            "bool": {
                "should": [
                    {
                        "constant_score": {
                            "filter": text_query,
                            "boost": self.config.search.text_weight
                        }
                    },
                    {
                        "constant_score": {
                            "filter": vector_query,
                            "boost": self.config.search.vector_weight
                        }
                    }
                ]
            }
        }
    
    def build_aggregations(self) -> Dict[str, Any]:
        """Build search aggregations.
        
        Returns:
            Aggregations query
        """
        return {
            "property_types": {
                "terms": {
                    "field": "property_type",
                    "size": 10
                }
            },
            "price_ranges": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 200000, "key": "Under $200k"},
                        {"from": 200000, "to": 500000, "key": "$200k-$500k"},
                        {"from": 500000, "to": 1000000, "key": "$500k-$1M"},
                        {"from": 1000000, "key": "Over $1M"}
                    ]
                }
            },
            "bedroom_counts": {
                "terms": {
                    "field": "bedrooms",
                    "size": 10
                }
            },
            "cities": {
                "terms": {
                    "field": "address.city",
                    "size": 20
                }
            },
            "avg_price": {
                "avg": {
                    "field": "price"
                }
            },
            "avg_sqft": {
                "avg": {
                    "field": "square_feet"
                }
            }
        }
    
    def build_sort(self, request: PropertySearchRequest) -> Optional[List[Dict[str, Any]]]:
        """Build sort criteria.
        
        Args:
            request: Search request
            
        Returns:
            Sort criteria or None
        """
        if not request.sort_by or request.sort_by == "relevance":
            return None
        
        sort_field_map = {
            "price": "price",
            "date": "listing_date",
            "bedrooms": "bedrooms"
        }
        
        field = sort_field_map.get(request.sort_by)
        if not field:
            return None
        
        return [{field: {"order": request.sort_order}}]
    
    def search(self, request: PropertySearchRequest) -> PropertySearchResponse:
        """Execute property search.
        
        Args:
            request: Search request
            
        Returns:
            Search response
        """
        start_time = time.time()
        logger.info(f"Executing property search: {request.query}")
        
        try:
            # Build filter query
            filter_clauses = self.build_filter_query(request.filters)
            
            # Build main query based on search type
            if request.search_type == "semantic":
                # Pure vector search
                query_embedding = self.embedding_service.embed_query(request.query)
                main_query = self.build_vector_query(query_embedding)
            elif request.search_type == "text":
                # Pure text search
                main_query = self.build_text_query(request.query)
            else:  # hybrid
                # Combined text and vector search
                text_query = self.build_text_query(request.query)
                query_embedding = self.embedding_service.embed_query(request.query)
                vector_query = self.build_vector_query(query_embedding)
                main_query = self.build_hybrid_query(text_query, vector_query)
            
            # Combine with filters
            if filter_clauses:
                query = {
                    "bool": {
                        "must": main_query,
                        "filter": filter_clauses
                    }
                }
            else:
                query = main_query
            
            # Build complete search body
            body = {
                "query": query,
                "size": request.size,
                "from": request.from_,
                "_source": True
            }
            
            # Add highlighting if requested
            if request.include_highlights:
                body["highlight"] = {
                    "fields": {
                        "description": {},
                        "enriched_search_text": {},
                        "features": {},
                        "amenities": {}
                    }
                }
            
            # Add aggregations if requested
            if request.include_aggregations:
                body["aggs"] = self.build_aggregations()
            
            # Add sort
            sort = self.build_sort(request)
            if sort:
                body["sort"] = sort
            
            # Add explain if requested
            if request.explain:
                body["explain"] = True
            
            # Execute search
            response = self.es_client.search(
                index=self.index_name,
                body=body
            )
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["_score"] = hit["_score"]
                
                if request.include_highlights and "highlight" in hit:
                    result["_highlights"] = hit["highlight"]
                
                if request.explain and "_explanation" in hit:
                    result["_explanation"] = hit["_explanation"]
                
                results.append(result)
            
            # Process aggregations
            aggregations = None
            if request.include_aggregations and "aggregations" in response:
                aggregations = []
                for agg_name, agg_data in response["aggregations"].items():
                    if "buckets" in agg_data:
                        aggregations.append(Aggregation(
                            name=agg_name,
                            type="terms" if "doc_count" in agg_data["buckets"][0] else "range",
                            buckets=agg_data["buckets"]
                        ))
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Create metadata
            metadata = SearchMetadata(
                total_hits=response["hits"]["total"]["value"],
                returned_hits=len(results),
                max_score=response["hits"]["max_score"],
                execution_time_ms=execution_time_ms,
                query_type=request.search_type
            )
            
            # Create response
            return PropertySearchResponse(
                metadata=metadata,
                results=results,
                aggregations=aggregations,
                original_query=request.query,
                applied_filters=request.filters
            )
            
        except Exception as e:
            logger.error(f"Property search failed: {e}")
            raise