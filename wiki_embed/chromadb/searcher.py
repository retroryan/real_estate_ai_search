"""ChromaDB implementation for vector search operations."""

from typing import List, Dict, Any
from wiki_embed.base.vector_store import VectorSearcher


class ChromaDBSearcher(VectorSearcher):
    """ChromaDB implementation for vector search operations."""
    
    def __init__(self, config, collection_name: str):
        import chromadb
        self.client = chromadb.PersistentClient(path=config.vector_store.chromadb.path)
        self.collection_name = collection_name
        self.collection = None
        if collection_name:
            try:
                self.collection = self.client.get_collection(collection_name)
            except:
                pass
    
    def set_collection(self, collection_name: str) -> None:
        """Set the collection to search in."""
        self.collection_name = collection_name
        try:
            self.collection = self.client.get_collection(collection_name)
        except:
            raise RuntimeError(f"Collection '{collection_name}' not found. Create embeddings first.")
    
    def similarity_search(self, query_embedding: List[float], top_k: int) -> Dict[str, Any]:
        if not self.collection:
            raise RuntimeError("No collection set. Call set_collection() first.")
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )