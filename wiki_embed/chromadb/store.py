"""ChromaDB implementation for vector store creation and management."""

from typing import List, Dict, Any
from wiki_embed.base.vector_store import VectorStore


class ChromaDBStore(VectorStore):
    """ChromaDB implementation for vector store creation and management."""
    
    def __init__(self, config):
        import chromadb
        self.client = chromadb.PersistentClient(path=config.vector_store.chromadb.path)
        self.collection = None
        self.config = config
    
    def create_collection(self, name: str, metadata: Dict[str, Any], force_recreate: bool = False) -> None:
        if force_recreate:
            try:
                self.client.delete_collection(name)
            except:
                pass
        self.collection = self.client.get_or_create_collection(name, metadata=metadata)
    
    def add_embeddings(self, embeddings: List[List[float]], texts: List[str], 
                      metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def count(self) -> int:
        return self.collection.count()
    
    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(name)