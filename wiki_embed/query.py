"""
Query testing module for Wikipedia embedding evaluation.
Tests location-based retrieval and calculates metrics.
"""

from typing import List, Optional
from wiki_embed.models import Config, QueryResult, LocationQuery, EmbeddingProvider, EmbeddingMethod
from wiki_embed.utils import settings
from wiki_embed.embedding import create_embedding_model


class WikipediaQueryTester:
    """Query tester for evaluating Wikipedia embedding models."""
    
    def __init__(self, config: Config, method: EmbeddingMethod = None):
        """
        Initialize query tester with configuration.
        
        Args:
            config: Validated configuration from Config model
            method: Override config method - 'traditional' or 'augmented'
        """
        self.config = config
        self.method = method or config.chunking.embedding_method
        
        # Validate method
        if self.method not in [EmbeddingMethod.TRADITIONAL, EmbeddingMethod.AUGMENTED]:
            self.method = EmbeddingMethod.TRADITIONAL  # Default fallback
        
        # Initialize embedding model using factory
        self.embed_model, self.model_identifier = create_embedding_model(config)
        
        # Use global vector searcher
        self.vector_searcher = settings.vector_searcher
        if not self.vector_searcher:
            raise RuntimeError("No vector searcher configured. Call wiki_embed.configure_from_config(config) first.")
        
        # Set up collection/index name
        provider = settings.config.vector_store.provider.value
        if provider == "elasticsearch":
            prefix = settings.config.vector_store.elasticsearch.index_prefix
        else:
            prefix = settings.config.vector_store.chromadb.collection_prefix
        
        collection_name = f"{prefix}_{self.model_identifier}_{self.method.value}"
        
        # Set the collection/index for searching
        self.vector_searcher.set_collection(collection_name)
        print(f"Using collection: {collection_name}", flush=True)
    
    def test_queries(self, queries: List[LocationQuery]) -> List[QueryResult]:
        """
        Test location-based queries and calculate metrics.
        
        Args:
            queries: List of LocationQuery objects to test
            
        Returns:
            List of QueryResult objects with metrics
        """
        results = []
        
        for i, query in enumerate(queries, 1):
            print(f"\nTesting query {i}/{len(queries)}: {query.query[:50]}...", flush=True)
            if query.location_context:
                print(f"  Location context: {query.location_context}", flush=True)
            if query.query_type:
                print(f"  Query type: {query.query_type.value}", flush=True)
            
            # Get query embedding
            query_embedding = self.embed_model.get_text_embedding(query.query)
            
            # Perform similarity search
            search_results = self.vector_searcher.similarity_search(
                query_embedding,
                self.config.testing.top_k
            )
            
            # Extract retrieved page IDs from metadata
            retrieved_ids = []
            if search_results and 'metadatas' in search_results:
                for metadata_list in search_results['metadatas']:
                    for metadata in metadata_list:
                        if 'page_id' in metadata:
                            retrieved_ids.append(metadata['page_id'])
            
            # Create result with metrics
            result = QueryResult(
                query=query.query,
                retrieved_ids=retrieved_ids,
                expected_ids=query.expected_articles,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                query_type=query.query_type,
                location_context=query.location_context
            )
            
            # Calculate metrics
            result.calculate_metrics()
            
            # Display metrics
            print(f"  Retrieved: {len(retrieved_ids)} articles", flush=True)
            print(f"  Expected: {len(query.expected_articles)} articles", flush=True)
            print(f"  Precision: {result.precision:.3f}", flush=True)
            print(f"  Recall: {result.recall:.3f}", flush=True)
            print(f"  F1 Score: {result.f1_score:.3f}", flush=True)
            
            # Show retrieved articles (for debugging)
            if retrieved_ids:
                print(f"  Retrieved IDs: {', '.join(retrieved_ids[:3])}{'...' if len(retrieved_ids) > 3 else ''}", flush=True)
            
            results.append(result)
        
        return results
    
    def test_by_location(self, queries: List[LocationQuery]) -> dict:
        """
        Test queries grouped by location context.
        
        Args:
            queries: List of LocationQuery objects
            
        Returns:
            Dictionary of results grouped by location
        """
        location_results = {}
        
        for query in queries:
            location = query.location_context or "Unknown"
            if location not in location_results:
                location_results[location] = []
            
            # Test single query
            result = self.test_queries([query])[0]
            location_results[location].append(result)
        
        # Calculate averages per location
        location_metrics = {}
        for location, results in location_results.items():
            avg_precision = sum(r.precision for r in results) / len(results)
            avg_recall = sum(r.recall for r in results) / len(results)
            avg_f1 = sum(r.f1_score for r in results) / len(results)
            
            location_metrics[location] = {
                'avg_precision': avg_precision,
                'avg_recall': avg_recall,
                'avg_f1': avg_f1,
                'count': len(results)
            }
        
        return location_metrics
    
    def test_by_type(self, queries: List[LocationQuery]) -> dict:
        """
        Test queries grouped by query type.
        
        Args:
            queries: List of LocationQuery objects
            
        Returns:
            Dictionary of results grouped by query type
        """
        type_results = {}
        
        for query in queries:
            query_type = query.query_type.value if query.query_type else "unknown"
            if query_type not in type_results:
                type_results[query_type] = []
            
            # Test single query
            result = self.test_queries([query])[0]
            type_results[query_type].append(result)
        
        # Calculate averages per type
        type_metrics = {}
        for query_type, results in type_results.items():
            avg_precision = sum(r.precision for r in results) / len(results)
            avg_recall = sum(r.recall for r in results) / len(results)
            avg_f1 = sum(r.f1_score for r in results) / len(results)
            
            type_metrics[query_type] = {
                'avg_precision': avg_precision,
                'avg_recall': avg_recall,
                'avg_f1': avg_f1,
                'count': len(results)
            }
        
        return type_metrics


# Keep compatibility
QueryTester = WikipediaQueryTester