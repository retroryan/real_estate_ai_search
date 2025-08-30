"""Wikipedia search service for semantic and text search."""

import time
from typing import Dict, Any, List, Optional

from ..config.settings import MCPServerConfig
from ..models.search import (
    WikipediaSearchRequest,
    WikipediaSearchResponse,
    SearchMetadata
)
from .elasticsearch_client import ElasticsearchClient
from .embedding_service import EmbeddingService
from ..utils.logging import get_logger


logger = get_logger(__name__)


class WikipediaSearchService:
    """Service for searching Wikipedia articles."""
    
    def __init__(
        self,
        config: MCPServerConfig,
        es_client: ElasticsearchClient,
        embedding_service: EmbeddingService
    ):
        """Initialize Wikipedia search service.
        
        Args:
            config: Server configuration
            es_client: Elasticsearch client
            embedding_service: Embedding service
        """
        self.config = config
        self.es_client = es_client
        self.embedding_service = embedding_service
        
        # Determine index based on search target
        self.chunks_index = f"{config.elasticsearch.wiki_chunks_index_prefix}_*"
        self.summaries_index = f"{config.elasticsearch.wiki_summaries_index_prefix}_*"
        self.full_index = "wikipedia"  # Main Wikipedia index
    
    def get_index_for_search(self, search_in: str) -> str:
        """Get the appropriate index for search type.
        
        Args:
            search_in: What to search in (full, summaries, chunks)
            
        Returns:
            Index name or pattern
        """
        if search_in == "chunks":
            return self.chunks_index
        elif search_in == "summaries":
            return self.summaries_index
        else:  # full
            return self.full_index
    
    def build_filter_query(self, request: WikipediaSearchRequest) -> List[Dict[str, Any]]:
        """Build filter query from request.
        
        Args:
            request: Search request
            
        Returns:
            List of filter clauses
        """
        filter_clauses = []
        
        # City filter
        if request.city:
            filter_clauses.append({
                "term": {"best_city": request.city.lower()}
            })
        
        # State filter
        if request.state:
            filter_clauses.append({
                "term": {"best_state": request.state.upper()}
            })
        
        # Categories filter
        if request.categories:
            filter_clauses.append({
                "terms": {"categories": request.categories}
            })
        
        # Minimum relevance filter
        if request.min_relevance is not None:
            filter_clauses.append({
                "range": {"relevance_score": {"gte": request.min_relevance}}
            })
        
        return filter_clauses
    
    def build_text_query(self, query: str, search_in: str) -> Dict[str, Any]:
        """Build text search query.
        
        Args:
            query: Search query text
            search_in: What to search in
            
        Returns:
            Text search query
        """
        if search_in == "chunks":
            # Search in chunk text
            fields = [
                "chunk_text^2",
                "title"
            ]
        elif search_in == "summaries":
            # Search in summaries
            fields = [
                "short_summary^3",
                "long_summary^2",
                "title^1.5",
                "key_topics"
            ]
        else:  # full
            # Search in full content
            fields = [
                "title^3",
                "short_summary^2.5",
                "long_summary^2",
                "full_content^1.5",
                "key_topics^1.5",
                "categories"
            ]
        
        return {
            "multi_match": {
                "query": query,
                "fields": fields,
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
    
    def search(self, request: WikipediaSearchRequest) -> WikipediaSearchResponse:
        """Execute Wikipedia search.
        
        Args:
            request: Search request
            
        Returns:
            Search response
        """
        start_time = time.time()
        logger.info(f"Executing Wikipedia search: {request.query} in {request.search_in}")
        
        try:
            # Get appropriate index
            index = self.get_index_for_search(request.search_in)
            
            # Build filter query
            filter_clauses = self.build_filter_query(request)
            
            # Build main query based on search type
            if request.search_type == "semantic":
                # Pure vector search
                query_embedding = self.embedding_service.embed_text(request.query)
                main_query = self.build_vector_query(query_embedding)
            elif request.search_type == "text":
                # Pure text search
                main_query = self.build_text_query(request.query, request.search_in)
            else:  # hybrid
                # Combined text and vector search
                text_query = self.build_text_query(request.query, request.search_in)
                query_embedding = self.embedding_service.embed_text(request.query)
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
                if request.search_in == "chunks":
                    highlight_fields = {
                        "chunk_text": {"fragment_size": 200, "number_of_fragments": 3},
                        "title": {}
                    }
                elif request.search_in == "summaries":
                    highlight_fields = {
                        "short_summary": {"fragment_size": 150, "number_of_fragments": 2},
                        "long_summary": {"fragment_size": 200, "number_of_fragments": 3},
                        "title": {}
                    }
                else:  # full
                    highlight_fields = {
                        "title": {},
                        "short_summary": {"fragment_size": 150, "number_of_fragments": 2},
                        "long_summary": {"fragment_size": 200, "number_of_fragments": 3},
                        "full_content": {"fragment_size": 250, "number_of_fragments": 5}
                    }
                
                body["highlight"] = {
                    "fields": highlight_fields,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            
            # Add explain if requested
            if request.explain:
                body["explain"] = True
            
            # Execute search
            response = self.es_client.search(
                index=index,
                body=body
            )
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["_score"] = hit["_score"]
                result["_index"] = hit["_index"]
                
                # Add entity type for client processing
                if request.search_in == "chunks":
                    result["entity_type"] = "wikipedia_chunk"
                else:
                    result["entity_type"] = "wikipedia_article"
                
                if request.include_highlights and "highlight" in hit:
                    result["_highlights"] = hit["highlight"]
                
                if request.explain and "_explanation" in hit:
                    result["_explanation"] = hit["_explanation"]
                
                results.append(result)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Create metadata
            metadata = SearchMetadata(
                total_hits=response["hits"]["total"]["value"],
                returned_hits=len(results),
                max_score=response["hits"]["max_score"],
                execution_time_ms=execution_time_ms,
                query_type=f"{request.search_type}_{request.search_in}"
            )
            
            # Create response
            return WikipediaSearchResponse(
                metadata=metadata,
                results=results,
                original_query=request.query,
                search_in=request.search_in
            )
            
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
            raise