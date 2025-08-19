"""
Query testing module for evaluating embedding quality.
Simple similarity search and metrics calculation.
"""

from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
import chromadb
from typing import List, Optional
from .models import Config, QueryResult, TestQuery


class QueryTester:
    """Simple query tester for evaluating embedding models."""
    
    def __init__(self, config: Config):
        """
        Initialize query tester with config.
        
        Args:
            config: Validated configuration
        """
        self.config = config
        
        # Initialize embedding model based on provider
        if config.embedding.provider == "ollama":
            self.embed_model = OllamaEmbedding(
                model_name=config.embedding.ollama_model,
                base_url=config.embedding.ollama_base_url
            )
            self.model_identifier = config.embedding.ollama_model
        elif config.embedding.provider == "gemini":
            self.embed_model = GeminiEmbedding(
                api_key=config.embedding.gemini_api_key,
                model_name=config.embedding.gemini_model
            )
            self.model_identifier = "gemini_embedding"
        else:  # voyage
            self.embed_model = VoyageEmbedding(
                api_key=config.embedding.voyage_api_key,
                model_name=config.embedding.voyage_model
            )
            self.model_identifier = f"voyage_{config.embedding.voyage_model}"
        
        # Direct ChromaDB client
        self.client = chromadb.PersistentClient(path=config.chromadb.path)
    
    def test_query(self, query: str, expected_ids: List[str], top_k: int = 10) -> QueryResult:
        """
        Test a single query and calculate metrics.
        
        Args:
            query: Query text to test
            expected_ids: List of expected result IDs
            top_k: Number of results to retrieve
            
        Returns:
            QueryResult with calculated metrics
        """
        # Get collection for this model
        collection_name = f"{self.config.chromadb.collection_prefix}_{self.model_identifier}"
        
        try:
            collection = self.client.get_collection(collection_name)
        except Exception as e:
            print(f"Warning: Collection {collection_name} not found. Run embedding creation first.")
            # Return empty result
            result = QueryResult(
                query=query,
                retrieved_ids=[],
                expected_ids=expected_ids,
                precision=0.0,
                recall=0.0,
                f1_score=0.0
            )
            return result
        
        # Embed the query using the same model
        query_embedding = self.embed_model.get_text_embedding(query)
        
        # Direct similarity search via ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count())  # Don't request more than exists
        )
        
        # Extract retrieved IDs from metadata
        retrieved_ids = []
        if results['ids'] and results['ids'][0]:
            for i, metadata in enumerate(results['metadatas'][0]):
                # Get the ID from metadata
                doc_id = metadata.get('id', results['ids'][0][i])
                retrieved_ids.append(doc_id)
        
        # Create result and calculate metrics
        result = QueryResult(
            query=query,
            retrieved_ids=retrieved_ids[:top_k],  # Ensure we only return top_k
            expected_ids=expected_ids,
            precision=0.0,
            recall=0.0,
            f1_score=0.0
        )
        
        # Calculate metrics using the model's method
        result.calculate_metrics()
        
        return result
    
    def test_queries(self, test_queries: List[TestQuery], top_k: int = 10) -> List[QueryResult]:
        """
        Test multiple queries and return results.
        
        Args:
            test_queries: List of TestQuery objects
            top_k: Number of results to retrieve per query
            
        Returns:
            List of QueryResult objects
        """
        results = []
        
        for i, test_query in enumerate(test_queries, 1):
            print(f"Testing query {i}/{len(test_queries)}: {test_query.query[:50]}...")
            
            result = self.test_query(
                query=test_query.query,
                expected_ids=test_query.expected_results,
                top_k=top_k
            )
            
            results.append(result)
            
            # Print immediate feedback
            print(f"  Precision: {result.precision:.3f}, Recall: {result.recall:.3f}")
        
        return results