"""Hybrid search combining vector similarity and graph relationships"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from neo4j import Driver

from .models import SearchConfig
from .vector_manager import PropertyVectorManager
from .embedding_pipeline import PropertyEmbeddingPipeline
from .config_loader import get_search_config


@dataclass
class SearchResult:
    """Unified search result combining vector and graph data"""
    listing_id: str
    address: Optional[str]
    price: float
    vector_score: float
    graph_score: float
    combined_score: float
    neighborhood: str
    city: str
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    square_feet: Optional[int]
    description: Optional[str]
    similar_properties: List[str]
    features: List[str]


class HybridPropertySearch:
    """
    Combines vector similarity with graph relationships for enhanced search.
    Follows patterns from wiki_embed's query testing.
    """
    
    def __init__(
        self,
        driver: Driver,
        embedding_pipeline: PropertyEmbeddingPipeline,
        config: Optional[SearchConfig] = None
    ):
        """
        Initialize hybrid search
        
        Args:
            driver: Neo4j database driver
            embedding_pipeline: Pipeline for generating query embeddings
            config: Search configuration (loads from file if not provided)
        """
        self.driver = driver
        self.embedding_pipeline = embedding_pipeline
        self.vector_manager = embedding_pipeline.vector_manager
        self.config = config or get_search_config()
    
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
            filters: Optional filters (price_min, price_max, city, neighborhood, bedrooms, etc.)
            top_k: Number of results to return (defaults to config.default_top_k)
            use_graph_boost: Whether to boost scores using graph metrics (defaults to config.use_graph_boost)
            
        Returns:
            List of SearchResult objects sorted by combined score
        """
        # Use defaults from config if not specified
        top_k = top_k or self.config.default_top_k
        use_graph_boost = use_graph_boost if use_graph_boost is not None else self.config.use_graph_boost
        
        # Generate query embedding
        query_embedding = self.embedding_pipeline.embed_model.get_text_embedding(query)
        
        # Perform vector search (get extra results for filtering)
        vector_results = self.vector_manager.vector_search(
            query_embedding, 
            top_k=top_k * 3 if filters else top_k * 2,
            min_score=self.config.min_similarity
        )
        
        if not vector_results:
            return []
        
        # Apply filters if provided
        if filters:
            vector_results = self._apply_filters(vector_results, filters)
        
        # Enhance with graph data and calculate scores
        enhanced_results = []
        for result in vector_results[:top_k * 2]:  # Process more than needed for graph boost
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
                price=result.get('price', 0),
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
    
    def _apply_filters(self, results: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """Apply filters to search results"""
        filtered = []
        
        for result in results:
            # Price filters
            if 'price_min' in filters and result.get('price', 0) < filters['price_min']:
                continue
            if 'price_max' in filters and result.get('price', float('inf')) > filters['price_max']:
                continue
            
            # Location filters
            if 'city' in filters and result.get('city', '').lower() != filters['city'].lower():
                continue
            if 'neighborhood' in filters and result.get('neighborhood', '').lower() != filters['neighborhood'].lower():
                continue
            
            # Property detail filters
            if 'bedrooms_min' in filters and (result.get('bedrooms') or 0) < filters['bedrooms_min']:
                continue
            if 'bathrooms_min' in filters and (result.get('bathrooms') or 0) < filters['bathrooms_min']:
                continue
            if 'square_feet_min' in filters and (result.get('square_feet') or 0) < filters['square_feet_min']:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _get_graph_metrics(self, listing_id: str) -> Dict[str, Any]:
        """
        Calculate graph-based importance metrics for a property
        
        Returns dict with:
        - centrality_score: Overall importance in graph (0-1)
        - similarity_connections: Number of similar properties
        - neighborhood_connections: Number of properties in same neighborhood
        - feature_connections: Number of properties sharing features
        - feature_count: Number of features
        """
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
        
        with self.driver.session() as session:
            result = session.run(query, listing_id=listing_id).single()
            
            if not result:
                return {
                    'centrality_score': 0.0,
                    'similarity_connections': 0,
                    'neighborhood_connections': 0,
                    'feature_connections': 0,
                    'feature_count': 0,
                    'proximity_connections': 0
                }
            
            # Calculate centrality score based on connections
            # Normalize each metric and combine
            similarity_score = min(result['similarity_connections'] / 10, 1.0)  # Cap at 10
            neighborhood_score = min(result['neighborhood_connections'] / 50, 1.0)  # Cap at 50
            feature_conn_score = min(result['feature_connections'] / 20, 1.0)  # Cap at 20
            feature_count_score = min(result['feature_count'] / 15, 1.0)  # Cap at 15
            proximity_score = min(result['proximity_connections'] / 30, 1.0)  # Cap at 30
            
            # Weighted combination - now using Phase 6 proximity data
            centrality = (
                similarity_score * 0.3 +        # Phase 6 similarity relationships
                neighborhood_score * 0.15 +     # Neighborhood connections  
                feature_conn_score * 0.15 +     # Feature sharing
                feature_count_score * 0.2 +     # Feature richness
                proximity_score * 0.2           # Phase 6 geographic proximity
            )
            
            return {
                'centrality_score': min(centrality, 1.0),
                'similarity_connections': result['similarity_connections'],
                'neighborhood_connections': result['neighborhood_connections'],
                'feature_connections': result['feature_connections'],
                'feature_count': result['feature_count'],
                'proximity_connections': result['proximity_connections']
            }
    
    def _calculate_combined_score(
        self,
        vector_score: float,
        graph_score: float,
        graph_metrics: Dict[str, Any]
    ) -> float:
        """
        Calculate combined score using vector similarity and graph metrics
        
        Uses weighted combination from config:
        - vector_weight (default 0.6)
        - graph_weight (default 0.2)
        - features_weight (default 0.2)
        """
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
        
        with self.driver.session() as session:
            results = session.run(query, listing_id=listing_id, limit=limit)
            return [record['listing_id'] for record in results if record['listing_id']]
    
    def _get_property_features(self, listing_id: str) -> List[str]:
        """Get features of a property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:HAS_FEATURE]->(f:Feature)
        RETURN f.name as feature
        ORDER BY f.name
        """
        
        with self.driver.session() as session:
            results = session.run(query, listing_id=listing_id)
            return [record['feature'] for record in results if record['feature']]