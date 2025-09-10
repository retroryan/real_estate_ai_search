"""
Query builder for hybrid search operations.

Builds queries for Elasticsearch's native RRF (Reciprocal Rank Fusion)
to combine text and vector search.
"""

from typing import List, Dict, Any, Optional


class HybridQueryBuilder:
    """
    Builds Elasticsearch queries for hybrid search using RRF.
    
    Creates retriever-based queries that combine multiple search
    methods using Reciprocal Rank Fusion.
    """
    
    def build_rrf_retriever(
        self,
        query_text: str,
        query_embedding: List[float],
        size: int = 10,
        rank_constant: int = 60,
        rank_window_size: int = 100
    ) -> Dict[str, Any]:
        """
        Build RRF retriever query combining text and vector search.
        
        Args:
            query_text: Natural language query
            query_embedding: Query vector (1024 dimensions)
            size: Number of results to return
            rank_constant: RRF rank constant parameter
            rank_window_size: RRF window size parameter
            
        Returns:
            Elasticsearch retriever query DSL with RRF
        """
        return {
            "retriever": {
                "rrf": {
                    "retrievers": [
                        {
                            "standard": {
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
                                }
                            }
                        },
                        {
                            "knn": {
                                "field": "embeddings.voyage_3.embedding",
                                "query_vector": query_embedding,
                                "k": size * 2,
                                "num_candidates": size * 10
                            }
                        }
                    ],
                    "rank_constant": rank_constant,
                    "rank_window_size": rank_window_size
                }
            },
            "size": size
        }
    
    def build_text_retriever(
        self,
        query_text: str,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build text-only retriever for hybrid search.
        
        Args:
            query_text: Natural language query
            size: Number of results
            
        Returns:
            Text retriever query DSL
        """
        return {
            "standard": {
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
                }
            }
        }
    
    def build_vector_retriever(
        self,
        query_embedding: List[float],
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build vector-only retriever for hybrid search.
        
        Args:
            query_embedding: Query vector
            size: Number of results
            
        Returns:
            KNN retriever query DSL
        """
        return {
            "knn": {
                "field": "embeddings.voyage_3.embedding",
                "query_vector": query_embedding,
                "k": size * 2,
                "num_candidates": size * 10
            }
        }
    
    def build_filtered_hybrid_query(
        self,
        query_text: str,
        query_embedding: List[float],
        filters: Dict[str, Any],
        size: int = 10,
        rank_constant: int = 60
    ) -> Dict[str, Any]:
        """
        Build hybrid query with filters.
        
        Args:
            query_text: Natural language query
            query_embedding: Query vector
            filters: Filter conditions
            size: Number of results
            rank_constant: RRF parameter
            
        Returns:
            Filtered hybrid query DSL
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
        
        # Build retrievers with filters
        text_retriever = {
            "standard": {
                "query": {
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": query_text,
                                "fields": [
                                    "description^2",
                                    "features^1.5"
                                ],
                                "type": "best_fields"
                            }
                        },
                        "filter": filter_clauses
                    }
                }
            }
        }
        
        knn_retriever = {
            "knn": {
                "field": "embeddings.voyage_3.embedding",
                "query_vector": query_embedding,
                "k": size * 2,
                "num_candidates": size * 10,
                "filter": {
                    "bool": {
                        "filter": filter_clauses
                    }
                } if filter_clauses else None
            }
        }
        
        # Remove None filter if no clauses
        if not filter_clauses:
            del knn_retriever["knn"]["filter"]
        
        return {
            "retriever": {
                "rrf": {
                    "retrievers": [text_retriever, knn_retriever],
                    "rank_constant": rank_constant,
                    "rank_window_size": 100
                }
            },
            "size": size
        }