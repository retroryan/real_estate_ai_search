"""Hybrid search with constructor injection"""

import logging
from typing import List, Dict, Any, Optional

from graph_real_estate.core.query_executor import QueryExecutor
from graph_real_estate.core.config import SearchConfig
from graph_real_estate.vectors.embedding_pipeline import PropertyEmbeddingPipeline
from graph_real_estate.vectors.vector_manager import PropertyVectorManager
from graph_real_estate.demos.models import SearchResult


class HybridPropertySearch:
    """Hybrid search with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        embedding_pipeline: PropertyEmbeddingPipeline,
        vector_manager: PropertyVectorManager,
        config: SearchConfig
    ):
        """
        Initialize hybrid search with all dependencies
        
        Args:
            query_executor: Query executor for database operations
            embedding_pipeline: Pipeline for generating query embeddings
            vector_manager: Manager for vector operations
            config: Search configuration
        """
        self.query_executor = query_executor
        self.embedding_pipeline = embedding_pipeline
        self.vector_manager = vector_manager
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        use_graph_boost: Optional[bool] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector similarity and graph relationships
        
        Args:
            query: Natural language search query
            filters: Optional filters
            top_k: Number of results to return
            use_graph_boost: Whether to boost scores using graph metrics
            
        Returns:
            List of SearchResult objects sorted by combined score
        """
        # Use defaults from config if not specified
        top_k = top_k or self.config.default_top_k
        use_graph_boost = use_graph_boost if use_graph_boost is not None else self.config.use_graph_boost
        
        # Generate query embedding
        query_embedding = self.embedding_pipeline.embed_model.get_text_embedding(query)
        
        # Perform vector search
        vector_results = self.vector_manager.vector_search(
            query_embedding, 
            top_k=top_k * 3 if filters else top_k * 2,
            min_score=self.config.min_similarity,
            filters=filters
        )
        
        if not vector_results:
            return []
        
        # Enhance with graph data and calculate scores
        enhanced_results = []
        for result in vector_results[:top_k * 2]:
            # Get graph metrics
            graph_metrics = self._get_graph_metrics(result['listing_id'])
            
            # Calculate scores
            vector_score = result['score']
            graph_score = graph_metrics['centrality_score']
            
            if use_graph_boost:
                combined_score = self._calculate_combined_score(
                    vector_score,
                    graph_score,
                    graph_metrics
                )
            else:
                combined_score = vector_score
            
            # Get similar properties
            similar_properties = self._get_similar_properties(result['listing_id'], limit=5)
            
            # Get property features
            features = self._get_property_features(result['listing_id'])
            
            # Create search result
            enhanced_results.append(SearchResult(
                listing_id=result['listing_id'],
                address=result.get('address'),
                listing_price=result.get('listing_price', 0),
                vector_score=vector_score,
                graph_score=graph_score,
                combined_score=combined_score,
                neighborhood=result.get('neighborhood', 'Unknown'),
                city=result.get('city', 'Unknown'),
                bedrooms=result.get('bedrooms'),
                bathrooms=result.get('bathrooms'),
                square_feet=result.get('square_feet'),
                description=result.get('description'),
                similar_properties=similar_properties,
                features=features
            ))
        
        # Sort by combined score and return top_k
        enhanced_results.sort(key=lambda x: x.combined_score, reverse=True)
        return enhanced_results[:top_k]
    
    def _get_graph_metrics(self, listing_id: str) -> Dict[str, Any]:
        """Calculate graph-based importance metrics for a property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})
        OPTIONAL MATCH (p)-[:SIMILAR_TO]-(similar:Property)
        OPTIONAL MATCH (p)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)<-[:IN_NEIGHBORHOOD]-(neighbor:Property)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(featured:Property)
        OPTIONAL MATCH (p)-[:NEAR_BY]-(nearby:Property)
        RETURN 
            COUNT(DISTINCT similar) as similarity_connections,
            COUNT(DISTINCT neighbor) as neighborhood_connections,
            COUNT(DISTINCT featured) as feature_connections,
            COUNT(DISTINCT f) as feature_count,
            COUNT(DISTINCT nearby) as proximity_connections
        """
        
        result = self.query_executor.execute_read(query, {'listing_id': listing_id})
        
        if not result or len(result) == 0:
            return {
                'centrality_score': 0.0,
                'similarity_connections': 0,
                'neighborhood_connections': 0,
                'feature_connections': 0,
                'feature_count': 0,
                'proximity_connections': 0
            }
        
        data = result[0]
        
        # Calculate centrality score based on connections
        similarity_score = min(data['similarity_connections'] / 10, 1.0)
        neighborhood_score = min(data['neighborhood_connections'] / 50, 1.0)
        feature_conn_score = min(data['feature_connections'] / 20, 1.0)
        feature_count_score = min(data['feature_count'] / 15, 1.0)
        proximity_score = min(data['proximity_connections'] / 30, 1.0)
        
        # Weighted combination
        centrality = (
            similarity_score * 0.3 +
            neighborhood_score * 0.15 +
            feature_conn_score * 0.15 +
            feature_count_score * 0.2 +
            proximity_score * 0.2
        )
        
        return {
            'centrality_score': min(centrality, 1.0),
            'similarity_connections': data['similarity_connections'],
            'neighborhood_connections': data['neighborhood_connections'],
            'feature_connections': data['feature_connections'],
            'feature_count': data['feature_count'],
            'proximity_connections': data['proximity_connections']
        }
    
    def _calculate_combined_score(
        self,
        vector_score: float,
        graph_score: float,
        graph_metrics: Dict[str, Any]
    ) -> float:
        """Calculate combined score using vector similarity and graph metrics"""
        # Feature richness score
        feature_score = min(graph_metrics['feature_count'] / 15, 1.0)
        
        # Weighted combination
        combined = (
            vector_score * self.config.vector_weight +
            graph_score * self.config.graph_weight +
            feature_score * self.config.features_weight
        )
        
        # Apply neighborhood boost for well-connected properties
        if graph_metrics['neighborhood_connections'] > 30:
            combined *= 1.1  # 10% boost
        
        # Apply similarity boost for properties with many similar ones
        if graph_metrics['similarity_connections'] > 5:
            combined *= 1.05  # 5% boost
        
        return min(combined, 1.0)  # Cap at 1.0
    
    def _get_similar_properties(self, listing_id: str, limit: int = 5) -> List[str]:
        """Get IDs of similar properties based on graph relationships"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:SIMILAR_TO]-(similar:Property)
        RETURN similar.listing_id as listing_id
        LIMIT $limit
        """
        
        results = self.query_executor.execute_read(query, {
            'listing_id': listing_id,
            'limit': limit
        })
        
        return [r['listing_id'] for r in results if r.get('listing_id')]
    
    def _get_property_features(self, listing_id: str) -> List[str]:
        """Get features of a property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:HAS_FEATURE]->(f:Feature)
        RETURN f.name as feature
        ORDER BY f.name
        """
        
        results = self.query_executor.execute_read(query, {'listing_id': listing_id})
        return [r['feature'] for r in results if r.get('feature')]