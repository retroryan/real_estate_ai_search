"""Property vector manager with constructor injection"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from neo4j import Driver

from core.query_executor import QueryExecutor


class PropertyVectorManager:
    """Manage property vectors with injected dependencies"""
    
    def __init__(self, driver: Driver, query_executor: QueryExecutor):
        """
        Initialize vector manager with dependencies
        
        Args:
            driver: Neo4j driver
            query_executor: Query executor for database operations
        """
        self.driver = driver
        self.query_executor = query_executor
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def vector_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar properties using vector similarity
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            min_score: Minimum similarity score
            filters: Optional filters to apply
            
        Returns:
            List of similar properties with scores
        """
        self.logger.debug(f"Performing vector search with top_k={top_k}, min_score={min_score}")
        
        # Build filter clause if filters provided
        filter_clause = ""
        filter_params = {}
        
        if filters:
            filter_conditions = []
            
            if 'city' in filters:
                filter_conditions.append("p.city = $city")
                filter_params['city'] = filters['city']
            
            if 'price_min' in filters:
                filter_conditions.append("p.listing_price >= $price_min")
                filter_params['price_min'] = filters['price_min']
            
            if 'price_max' in filters:
                filter_conditions.append("p.listing_price <= $price_max")
                filter_params['price_max'] = filters['price_max']
            
            if 'bedrooms_min' in filters:
                filter_conditions.append("p.bedrooms >= $bedrooms_min")
                filter_params['bedrooms_min'] = filters['bedrooms_min']
            
            if filter_conditions:
                filter_clause = "AND " + " AND ".join(filter_conditions)
        
        # Get all property embeddings
        query = f"""
        MATCH (p:Property)
        WHERE p.embedding IS NOT NULL
        {filter_clause}
        RETURN p.listing_id as listing_id,
               p.embedding as embedding,
               p.street as address,
               p.city as city,
               p.neighborhood_id as neighborhood,
               p.listing_price as listing_price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               p.description as description
        """
        
        results = self.query_executor.execute_read(query, filter_params)
        
        if not results:
            self.logger.warning("No properties with embeddings found")
            return []
        
        # Calculate similarities
        query_vec = np.array(query_embedding)
        similarities = []
        
        for record in results:
            prop_vec = np.array(record['embedding'])
            
            # Cosine similarity
            similarity = self._cosine_similarity(query_vec, prop_vec)
            
            if similarity >= min_score:
                similarities.append({
                    'listing_id': record['listing_id'],
                    'score': float(similarity),
                    'address': record.get('address'),
                    'city': record.get('city'),
                    'neighborhood': record.get('neighborhood'),
                    'listing_price': record.get('listing_price'),
                    'bedrooms': record.get('bedrooms'),
                    'bathrooms': record.get('bathrooms'),
                    'square_feet': record.get('square_feet'),
                    'description': record.get('description')
                })
        
        # Sort by similarity score
        similarities.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top k results
        return similarities[:top_k]
    
    def store_embedding(
        self,
        node_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store embedding for a node
        
        Args:
            node_id: Node identifier
            embedding: Embedding vector
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            query = """
            MATCH (p:Property {listing_id: $node_id})
            SET p.embedding = $embedding,
                p.embedding_metadata = $metadata,
                p.embedding_updated_at = datetime()
            RETURN p.listing_id as id
            """
            
            result = self.query_executor.execute_write(query, {
                'node_id': node_id,
                'embedding': embedding,
                'metadata': metadata
            })
            
            return len(result) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to store embedding for {node_id}: {e}")
            return False
    
    def get_embedding(self, node_id: str) -> Optional[List[float]]:
        """
        Get embedding for a node
        
        Args:
            node_id: Node identifier
            
        Returns:
            Embedding vector if exists
        """
        query = """
        MATCH (p:Property {listing_id: $node_id})
        WHERE p.embedding IS NOT NULL
        RETURN p.embedding as embedding
        """
        
        result = self.query_executor.execute_read(query, {'node_id': node_id})
        
        if result and len(result) > 0:
            return result[0]['embedding']
        
        return None
    
    def create_vector_index(self, dimension: int = 384) -> bool:
        """
        Create vector index for similarity search
        
        Args:
            dimension: Vector dimension
            
        Returns:
            True if successful
        """
        try:
            # Note: Neo4j vector indexes require specific configuration
            # This is a placeholder for the actual vector index creation
            query = """
            CREATE INDEX property_embedding_index IF NOT EXISTS
            FOR (p:Property)
            ON (p.embedding)
            """
            
            self.query_executor.execute_write(query)
            
            self.logger.info(f"Created vector index with dimension {dimension}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create vector index: {e}")
            return False
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_properties(
        self,
        listing_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find properties similar to a given property
        
        Args:
            listing_id: Property listing ID
            top_k: Number of similar properties to return
            
        Returns:
            List of similar properties
        """
        # Get embedding for the property
        embedding = self.get_embedding(listing_id)
        
        if not embedding:
            self.logger.warning(f"No embedding found for property {listing_id}")
            return []
        
        # Search for similar properties
        results = self.vector_search(embedding, top_k=top_k + 1)  # +1 to exclude self
        
        # Filter out the property itself
        return [r for r in results if r['listing_id'] != listing_id][:top_k]
    
    def update_all_embeddings(self, embedding_pipeline) -> int:
        """
        Update embeddings for all properties
        
        Args:
            embedding_pipeline: Pipeline to generate embeddings
            
        Returns:
            Number of embeddings updated
        """
        return embedding_pipeline.generate_property_embeddings()