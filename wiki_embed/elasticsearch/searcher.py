"""Elasticsearch implementation for vector search operations."""

from typing import List, Dict, Any
from wiki_embed.base.vector_store import VectorSearcher


class ElasticsearchSearcher(VectorSearcher):
    """Elasticsearch implementation for vector search operations."""
    
    def __init__(self, config, index_name: str):
        from elasticsearch import Elasticsearch
        
        es_config = config.vector_store.elasticsearch
        
        # Simple connection setup
        if es_config.username and es_config.password:
            self.client = Elasticsearch(
                [f"http://{es_config.host}:{es_config.port}"],
                basic_auth=(es_config.username, es_config.password)
            )
        else:
            self.client = Elasticsearch([f"http://{es_config.host}:{es_config.port}"])
        
        self.index_name = index_name
    
    def set_collection(self, index_name: str) -> None:
        """Set the index to search in."""
        self.index_name = index_name
    
    def similarity_search(self, query_embedding: List[float], top_k: int) -> Dict[str, Any]:
        if not self.index_name:
            raise RuntimeError("No index set. Call set_collection() first.")
        
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k,
                "num_candidates": top_k * 2
            },
            "_source": ["content", "metadata"]
        }
        
        response = self.client.search(index=self.index_name, body=query)
        
        # Convert to ChromaDB-compatible format
        hits = response["hits"]["hits"]
        return {
            "documents": [[hit["_source"]["content"] for hit in hits]],
            "metadatas": [[hit["_source"]["metadata"] for hit in hits]],
            "distances": [[1.0 - hit["_score"] for hit in hits]]  # Convert score to distance
        }