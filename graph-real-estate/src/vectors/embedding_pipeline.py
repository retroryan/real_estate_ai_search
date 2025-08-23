"""Property embedding pipeline with constructor injection"""

import logging
from typing import List, Dict, Any, Optional
from neo4j import Driver

from src.core.interfaces import IVectorManager


class EmbeddingModel:
    """Simple embedding model interface"""
    
    def __init__(self, model_name: str):
        """
        Initialize embedding model
        
        Args:
            model_name: Name of the embedding model
        """
        self.model_name = model_name
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Simplified implementation - in production would use actual model
        # This is a placeholder that creates a deterministic embedding based on text
        import hashlib
        
        # Create a hash of the text for deterministic "embedding"
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to list of floats normalized to [-1, 1]
        embedding = []
        for i in range(0, min(len(hash_bytes), 384), 3):  # 384-dim embedding
            if i + 2 < len(hash_bytes):
                value = (hash_bytes[i] + hash_bytes[i+1] + hash_bytes[i+2]) / 765.0  # Normalize
                embedding.append(value * 2 - 1)  # Scale to [-1, 1]
        
        # Pad to standard size if needed
        while len(embedding) < 384:
            embedding.append(0.0)
        
        return embedding[:384]  # Ensure exactly 384 dimensions


class PropertyEmbeddingPipeline:
    """Generate embeddings for properties with injected dependencies"""
    
    def __init__(self, driver: Driver, model_name: str = "nomic-embed-text"):
        """
        Initialize embedding pipeline with dependencies
        
        Args:
            driver: Neo4j driver
            model_name: Name of embedding model to use
        """
        self.driver = driver
        self.model_name = model_name
        self.embed_model = EmbeddingModel(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Track statistics
        self.properties_processed = 0
        self.embeddings_created = 0
    
    def generate_property_embeddings(self, limit: Optional[int] = None) -> int:
        """
        Generate embeddings for all properties
        
        Args:
            limit: Optional limit on number of properties to process
            
        Returns:
            Number of embeddings created
        """
        self.logger.info(f"Generating property embeddings using {self.model_name}")
        
        # Get properties from database
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        OPTIONAL MATCH (p)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)
        RETURN p.listing_id as listing_id,
               p.description as description,
               p.street as street,
               p.city as city,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               p.listing_price as price,
               collect(DISTINCT f.name) as features,
               n.name as neighborhood,
               n.description as neighborhood_desc
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.driver.session() as session:
            results = session.run(query)
            
            embeddings_created = 0
            for record in results:
                # Create text representation of property
                text = self._create_property_text(record)
                
                # Generate embedding
                embedding = self.embed_model.get_text_embedding(text)
                
                # Store embedding in database
                if self._store_embedding(record['listing_id'], embedding):
                    embeddings_created += 1
                
                self.properties_processed += 1
                
                if self.properties_processed % 100 == 0:
                    self.logger.info(f"Processed {self.properties_processed} properties")
        
        self.embeddings_created = embeddings_created
        self.logger.info(f"Created {embeddings_created} property embeddings")
        
        return embeddings_created
    
    def _create_property_text(self, record: Dict[str, Any]) -> str:
        """Create text representation of property for embedding"""
        parts = []
        
        # Basic info
        if record.get('description'):
            parts.append(record['description'])
        
        # Location
        location_parts = []
        if record.get('street'):
            location_parts.append(record['street'])
        if record.get('neighborhood'):
            location_parts.append(f"in {record['neighborhood']}")
        if record.get('city'):
            location_parts.append(record['city'])
        
        if location_parts:
            parts.append(" ".join(location_parts))
        
        # Property details
        details = []
        if record.get('bedrooms'):
            details.append(f"{record['bedrooms']} bedrooms")
        if record.get('bathrooms'):
            details.append(f"{record['bathrooms']} bathrooms")
        if record.get('square_feet'):
            details.append(f"{record['square_feet']} sq ft")
        if record.get('price'):
            details.append(f"${record['price']:,.0f}")
        
        if details:
            parts.append(", ".join(details))
        
        # Features
        if record.get('features'):
            parts.append("Features: " + ", ".join(record['features']))
        
        # Neighborhood description
        if record.get('neighborhood_desc'):
            parts.append(f"Neighborhood: {record['neighborhood_desc']}")
        
        return " | ".join(parts)
    
    def _store_embedding(self, listing_id: str, embedding: List[float]) -> bool:
        """Store embedding in database"""
        try:
            query = """
            MATCH (p:Property {listing_id: $listing_id})
            SET p.embedding = $embedding,
                p.embedding_model = $model,
                p.embedding_created_at = datetime()
            RETURN p.listing_id as id
            """
            
            with self.driver.session() as session:
                result = session.run(query, {
                    'listing_id': listing_id,
                    'embedding': embedding,
                    'model': self.model_name
                })
                
                return result.single() is not None
                
        except Exception as e:
            self.logger.error(f"Failed to store embedding for {listing_id}: {e}")
            return False
    
    def get_property_embedding(self, listing_id: str) -> Optional[List[float]]:
        """Get embedding for a specific property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})
        WHERE p.embedding IS NOT NULL
        RETURN p.embedding as embedding
        """
        
        with self.driver.session() as session:
            result = session.run(query, listing_id=listing_id).single()
            
            if result:
                return result['embedding']
            
        return None