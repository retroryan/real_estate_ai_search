"""
Query builder for semantic search operations.

Consolidates all semantic/embedding query building logic
without any display or processing concerns.
"""

from typing import List, Dict, Any, Optional
from ..demo_config import demo_config


class SemanticQueryBuilder:
    """
    Builds Elasticsearch queries for semantic search operations.
    
    All methods return query DSL dictionaries ready for execution.
    No conditional logic or entity type checking.
    """
    
    def knn_semantic_search(
        self,
        query_embedding: List[float],
        size: int = 10,
        num_candidates: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build KNN query for semantic similarity search.
        
        Args:
            query_embedding: Query vector (1024 dimensions)
            size: Number of results to return
            num_candidates: Number of candidates for KNN (defaults to size * 10)
            
        Returns:
            Elasticsearch KNN query DSL
        """
        if num_candidates is None:
            num_candidates = size * 10
        
        return {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": size,
                "num_candidates": num_candidates
            },
            "size": size
        }
    
    def keyword_search(
        self,
        query_text: str,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build traditional keyword search query.
        
        Args:
            query_text: Text query string
            size: Number of results to return
            
        Returns:
            Elasticsearch multi-match query DSL
        """
        return {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "description^2",
                        "features^1.5",
                        "address.street",
                        "address.city",
                        "neighborhood_overview"
                    ],
                    "type": "best_fields",
                    "operator": "or",
                    "fuzziness": "AUTO"
                }
            },
            "size": size
        }
    
    def hybrid_knn_query(
        self,
        query_embedding: List[float],
        query_text: str,
        size: int = 10,
        boost_knn: float = 1.0,
        boost_text: float = 1.0
    ) -> Dict[str, Any]:
        """
        Build hybrid query combining KNN and text search.
        
        Note: This is for manual hybrid search. For RRF-based hybrid,
        use HybridQueryBuilder instead.
        
        Args:
            query_embedding: Query vector
            query_text: Text query
            size: Number of results
            boost_knn: Boost factor for KNN results
            boost_text: Boost factor for text results
            
        Returns:
            Combined query DSL
        """
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {
                                        "query_vector": query_embedding
                                    }
                                },
                                "boost": boost_knn
                            }
                        },
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": [
                                    "description^2",
                                    "features^1.5",
                                    "address.street",
                                    "address.city"
                                ],
                                "type": "best_fields",
                                "boost": boost_text
                            }
                        }
                    ]
                }
            },
            "size": size
        }
    
    def filtered_semantic_search(
        self,
        query_embedding: List[float],
        filters: Dict[str, Any],
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build semantic search with filters.
        
        Args:
            query_embedding: Query vector
            filters: Filter conditions (e.g., {"min_price": 500000})
            size: Number of results
            
        Returns:
            KNN query with filters
        """
        # Build filter clauses
        filter_clauses = []
        
        if "min_price" in filters:
            filter_clauses.append({
                "range": {
                    "price": {"gte": filters["min_price"]}
                }
            })
        
        if "max_price" in filters:
            filter_clauses.append({
                "range": {
                    "price": {"lte": filters["max_price"]}
                }
            })
        
        if "property_type" in filters:
            filter_clauses.append({
                "term": {
                    "property_type": filters["property_type"]
                }
            })
        
        if "city" in filters:
            filter_clauses.append({
                "term": {
                    "address.city": filters["city"].lower()
                }
            })
        
        # Build query
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": size,
                "num_candidates": size * 10
            },
            "size": size
        }
        
        # Add filters if present
        if filter_clauses:
            query["knn"]["filter"] = {
                "bool": {
                    "filter": filter_clauses
                }
            }
        
        return query