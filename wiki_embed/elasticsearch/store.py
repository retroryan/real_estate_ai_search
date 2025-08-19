"""Elasticsearch implementation for vector store creation and management."""

from typing import List, Dict, Any
from wiki_embed.base.vector_store import VectorStore


class ElasticsearchStore(VectorStore):
    """Elasticsearch implementation for vector store creation and management."""
    
    def __init__(self, config):
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
        
        self.config = config
        self.current_index = None
        
        # Determine embedding dimensions from provider
        if config.embedding.provider.value == "ollama":
            # nomic-embed-text = 768, mxbai-embed-large = 1024
            self.embedding_dims = 768 if "nomic" in config.embedding.ollama_model else 1024
        elif config.embedding.provider.value == "gemini":
            self.embedding_dims = 768  # Gemini embedding-001
        elif config.embedding.provider.value == "voyage":
            self.embedding_dims = 1024  # Voyage-3
        else:
            self.embedding_dims = 768  # Default fallback
    
    def create_collection(self, name: str, metadata: Dict[str, Any], force_recreate: bool = False) -> None:
        self.current_index = name
        
        if force_recreate and self.client.indices.exists(index=name):
            self.client.indices.delete(index=name)
        
        if not self.client.indices.exists(index=name):
            mapping = {
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.embedding_dims,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "content": {
                            "type": "text",
                            "store": True
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "page_id": {"type": "keyword"},
                                "title": {"type": "text"},
                                "location": {"type": "keyword"},
                                "state": {"type": "keyword"},
                                "country": {"type": "keyword"},
                                "location_context": {"type": "text"},
                                "provider": {"type": "keyword"},
                                "model": {"type": "keyword"},
                                "chunk_index": {"type": "integer"},
                                "embedding_method": {"type": "keyword"},
                                "word_count": {"type": "integer"},
                                "categories": {"type": "text"}
                            }
                        }
                    }
                }
            }
            
            self.client.indices.create(index=name, body=mapping)
    
    def add_embeddings(self, embeddings: List[List[float]], texts: List[str], 
                      metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        actions = []
        for embedding, text, metadata, doc_id in zip(embeddings, texts, metadatas, ids):
            actions.append({
                "_index": self.current_index,
                "_id": doc_id,
                "_source": {
                    "embedding": embedding,
                    "content": text,
                    "metadata": metadata
                }
            })
        
        from elasticsearch.helpers import bulk
        bulk(self.client, actions)
    
    def count(self) -> int:
        return self.client.count(index=self.current_index)["count"]
    
    def delete_collection(self, name: str) -> None:
        if self.client.indices.exists(index=name):
            self.client.indices.delete(index=name)