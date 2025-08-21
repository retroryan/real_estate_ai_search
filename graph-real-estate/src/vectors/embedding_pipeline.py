"""Property embedding pipeline using LlamaIndex patterns from wiki_embed"""
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm

from llama_index.core import Document
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.google import GeminiEmbedding

from neo4j import Driver
from .models import EmbeddingConfig, VectorIndexConfig
from .vector_manager import PropertyVectorManager
from .config_loader import get_embedding_config, get_vector_index_config


class PropertyEmbeddingPipeline:
    """
    LlamaIndex-based embedding pipeline for property data.
    Follows patterns from wiki_embed for consistency.
    """
    
    def __init__(
        self, 
        driver: Driver,
        config: Optional[EmbeddingConfig] = None,
        vector_config: Optional[VectorIndexConfig] = None
    ):
        """
        Initialize the embedding pipeline
        
        Args:
            driver: Neo4j database driver
            config: Embedding configuration (loads from file if not provided)
            vector_config: Vector index configuration (loads from file if not provided)
        """
        self.driver = driver
        self.config = config or get_embedding_config()
        self.vector_config = vector_config or get_vector_index_config()
        
        # Create embedding model
        self.embed_model = self._create_embedding_model()
        
        # Initialize vector manager
        self.vector_manager = PropertyVectorManager(driver, self.vector_config)
    
    def _create_embedding_model(self):
        """
        Create embedding model based on configuration.
        Pattern copied from wiki_embed/pipeline.py
        """
        if self.config.provider == "ollama":
            return OllamaEmbedding(
                model_name=self.config.ollama_model,
                base_url=self.config.ollama_base_url
            )
        elif self.config.provider == "openai":
            if not self.config.openai_api_key:
                # Try to get from environment
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API key not provided")
                self.config.openai_api_key = api_key
            
            return OpenAIEmbedding(
                api_key=self.config.openai_api_key,
                model=self.config.openai_model
            )
        elif self.config.provider == "gemini":
            if not self.config.gemini_api_key:
                # Try to get from environment
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("Gemini API key not provided")
                self.config.gemini_api_key = api_key
            
            return GeminiEmbedding(
                api_key=self.config.gemini_api_key,
                model_name=self.config.gemini_model
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {self.config.provider}")
    
    def process_properties(self, force_recreate: bool = False) -> Dict[str, Any]:
        """
        Generate embeddings for all properties in the database
        
        Args:
            force_recreate: If True, regenerate all embeddings even if they exist
            
        Returns:
            Statistics about the embedding process
        """
        print("=" * 60)
        print("PROPERTY EMBEDDING GENERATION")
        print("=" * 60)
        print(f"Provider: {self.config.provider}")
        print(f"Model: {self._get_model_name()}")
        print(f"Dimensions: {self.config.get_dimensions()}")
        print(f"Batch size: {self.config.batch_size}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Check existing embeddings
        status = self.vector_manager.check_embeddings_exist()
        print(f"\nCurrent status:")
        print(f"  Total properties: {status['total']}")
        print(f"  With embeddings: {status['with_embeddings']}")
        print(f"  Without embeddings: {status['without_embeddings']}")
        
        # Determine what to process
        if force_recreate:
            print("\nWarning: Force recreate mode - clearing existing embeddings")
            self.vector_manager.clear_embeddings()
            properties_to_process = self._get_all_properties()
        elif status['without_embeddings'] == 0:
            print("\nAll properties already have embeddings")
            return {
                "total": status['total'],
                "processed": 0,
                "existing": status['with_embeddings'],
                "errors": 0,
                "time": 0
            }
        else:
            print(f"\nProcessing {status['without_embeddings']} properties without embeddings")
            properties_to_process = self.vector_manager.get_properties_without_embeddings(limit=10000)
        
        # Process properties in batches
        processed = 0
        errors = 0
        embeddings_batch = []
        
        # Use tqdm for progress tracking (pattern from wiki_embed)
        with tqdm(total=len(properties_to_process), desc="Generating embeddings") as pbar:
            for i, prop in enumerate(properties_to_process):
                try:
                    # Create property text
                    text = self._create_property_text(prop)
                    
                    # Generate embedding
                    embedding = self.embed_model.get_text_embedding(text)
                    
                    # Add to batch
                    embeddings_batch.append({
                        "listing_id": prop["listing_id"],
                        "embedding": embedding
                    })
                    
                    # Store batch when it reaches batch_size
                    if len(embeddings_batch) >= self.config.batch_size:
                        batch_result = self.vector_manager.store_embeddings_batch(embeddings_batch)
                        processed += batch_result["success"]
                        errors += batch_result["errors"]
                        embeddings_batch = []
                        pbar.update(self.config.batch_size)
                    
                except Exception as e:
                    errors += 1
                    print(f"\nError: Error processing {prop.get('listing_id', 'unknown')}: {e}")
                    pbar.update(1)
        
        # Store remaining embeddings
        if embeddings_batch:
            batch_result = self.vector_manager.store_embeddings_batch(embeddings_batch)
            processed += batch_result["success"]
            errors += batch_result["errors"]
        
        elapsed = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("EMBEDDING GENERATION COMPLETE")
        print("=" * 60)
        print(f"Processed: {processed}")
        print(f"Errors: {errors}")
        print(f"Time: {elapsed:.2f}s")
        if processed > 0:
            print(f"Rate: {processed/elapsed:.1f} properties/second")
        
        return {
            "total": len(properties_to_process),
            "processed": processed,
            "existing": status['with_embeddings'] if not force_recreate else 0,
            "errors": errors,
            "time": elapsed,
            "rate": processed / elapsed if elapsed > 0 else 0
        }
    
    def _create_property_text(self, prop: Dict[str, Any]) -> str:
        """
        Create rich text representation for embedding.
        Combines multiple property attributes for better semantic understanding.
        Pattern inspired by real_estate_embed/pipeline.py
        """
        parts = []
        
        # Location information
        neighborhood = prop.get("neighborhood", "Unknown")
        city = prop.get("city", "Unknown")
        parts.append(f"Property in {neighborhood} neighborhood, {city}")
        
        # Property type and details
        property_type = prop.get("property_type", "residential")
        parts.append(f"Type: {property_type}")
        
        # Price
        price = prop.get("price")
        if price:
            parts.append(f"Price: ${price:,.0f}")
        
        # Property details
        bedrooms = prop.get("bedrooms")
        bathrooms = prop.get("bathrooms")
        square_feet = prop.get("square_feet")
        
        if bedrooms or bathrooms:
            details = []
            if bedrooms:
                details.append(f"{bedrooms} bedrooms")
            if bathrooms:
                details.append(f"{bathrooms} bathrooms")
            parts.append(", ".join(details))
        
        if square_feet and square_feet > 0:
            parts.append(f"{square_feet} square feet")
        
        # Description
        description = prop.get("description")
        if description:
            # Limit description length to avoid too long embeddings
            if len(description) > 500:
                description = description[:497] + "..."
            parts.append(f"Description: {description}")
        
        # Features (limit to top 10)
        features = prop.get("features")
        if features and isinstance(features, list):
            top_features = features[:10]
            if top_features:
                parts.append(f"Features: {', '.join(top_features)}")
        
        # Address if available
        address = prop.get("address")
        if address:
            parts.append(f"Location: {address}")
        
        return "\n".join(parts)
    
    def _get_model_name(self) -> str:
        """Get the display name for the current model"""
        if self.config.provider == "ollama":
            return self.config.ollama_model
        elif self.config.provider == "openai":
            return self.config.openai_model
        elif self.config.provider == "gemini":
            return self.config.gemini_model.split("/")[-1]
        return "unknown"
    
    def _get_all_properties(self) -> List[Dict[str, Any]]:
        """Get all properties from the database with their features"""
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, n, c, collect(DISTINCT f.name) as features
        RETURN p.listing_id as listing_id,
               p.description as description,
               p.address as address,
               p.listing_price as price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               p.property_type as property_type,
               features,
               n.name as neighborhood,
               c.name as city
        """
        
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(record) for record in results]