"""Property embedding pipeline with constructor injection"""

import logging
import os
from typing import List, Dict, Any, Optional
import requests
import numpy as np
from neo4j import Driver

from ..core.interfaces import IVectorManager


class EmbeddingModel:
    """Embedding model supporting multiple providers"""
    
    def __init__(self, model_name: str, embedding_config=None):
        """
        Initialize embedding model
        
        Args:
            model_name: Name of the embedding model
            embedding_config: Embedding configuration object
        """
        self.model_name = model_name
        self.embedding_config = embedding_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Determine dimensions based on model and config
        self.dimensions = self._get_model_dimensions()
        
        # Initialize provider-specific settings
        if not embedding_config:
            raise ValueError("EmbeddingConfig is required")
        self.provider = embedding_config.provider
        self._initialize_provider()
    
    def _get_model_dimensions(self) -> int:
        """
        Get embedding dimensions based on model name and configuration
        
        Returns:
            Number of dimensions for the embedding
        """
        if not self.embedding_config:
            raise ValueError("EmbeddingConfig is required to determine dimensions")
        return self.embedding_config.get_dimensions()
    
    def _initialize_provider(self):
        """Initialize provider-specific settings"""
        # Get the active model config for the selected provider
        model_config = self.embedding_config.get_active_model_config()
        
        if self.provider == "voyage":
            self.api_key = model_config.api_key or os.getenv("VOYAGE_API_KEY")
            if not self.api_key:
                raise ValueError("Voyage API key is required but not found in config or environment")
            self.api_url = "https://api.voyageai.com/v1/embeddings"
        elif self.provider == "openai":
            self.api_key = model_config.api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is required but not found in config or environment")
            self.api_url = "https://api.openai.com/v1/embeddings"
        elif self.provider == "ollama":
            self.base_url = model_config.base_url
            self.api_url = f"{self.base_url}/api/embeddings"
        elif self.provider == "gemini":
            self.api_key = model_config.api_key or os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("Gemini API key is required but not found in config or environment")
            # Gemini uses a different endpoint structure
            self.api_url = "https://generativelanguage.googleapis.com/v1beta/models"
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    def get_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using configured provider
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if self.provider == "voyage":
            return self._get_voyage_embedding(text)
        elif self.provider == "openai":
            return self._get_openai_embedding(text)
        elif self.provider == "ollama":
            return self._get_ollama_embedding(text)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _get_voyage_embedding(self, text: str) -> List[float]:
        """Get embedding from Voyage API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": text,
            "model": self.model_name
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]
        except Exception as e:
            self.logger.error(f"Failed to get Voyage embedding: {e}")
            raise
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": text,
            "model": self.model_name
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]
        except Exception as e:
            self.logger.error(f"Failed to get OpenAI embedding: {e}")
            raise
    
    def _get_ollama_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama API"""
        data = {
            "model": self.model_name,
            "prompt": text
        }
        
        try:
            response = requests.post(self.api_url, json=data)
            response.raise_for_status()
            result = response.json()
            return result["embedding"]
        except Exception as e:
            self.logger.error(f"Failed to get Ollama embedding: {e}")
            raise
    


class PropertyEmbeddingPipeline:
    """Generate embeddings for properties with injected dependencies"""
    
    def __init__(self, driver: Driver, embedding_config):
        """
        Initialize embedding pipeline with dependencies
        
        Args:
            driver: Neo4j driver
            embedding_config: Embedding configuration object
        """
        self.driver = driver
        self.embedding_config = embedding_config
        self.model_name = embedding_config.get_model_name()
        self.embed_model = EmbeddingModel(self.model_name, embedding_config)
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