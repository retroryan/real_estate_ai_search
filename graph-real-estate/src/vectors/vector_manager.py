"""Neo4j vector index management for property embeddings"""
from typing import List, Dict, Any, Optional
from neo4j import Driver
import numpy as np
from .models import VectorIndexConfig


class PropertyVectorManager:
    """Manages vector embeddings for properties in Neo4j"""
    
    def __init__(self, driver: Driver, config: VectorIndexConfig):
        """
        Initialize the vector manager
        
        Args:
            driver: Neo4j database driver
            config: Vector index configuration
        """
        self.driver = driver
        self.config = config
    
    def create_vector_index(self) -> bool:
        """
        Create or recreate vector index for property embeddings
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                # Drop existing index if it exists
                drop_query = f"DROP INDEX {self.config.index_name} IF EXISTS"
                session.run(drop_query)
                
                # Create new vector index
                create_query = f"""
                CREATE VECTOR INDEX `{self.config.index_name}` IF NOT EXISTS
                FOR (n:{self.config.node_label}) 
                ON (n.{self.config.embedding_property})
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {self.config.vector_dimensions},
                        `vector.similarity_function`: '{self.config.similarity_function}'
                    }}
                }}
                """
                
                session.run(create_query)
                print(f"✓ Created vector index '{self.config.index_name}' with {self.config.vector_dimensions} dimensions")
                return True
                
        except Exception as e:
            print(f"✗ Error creating vector index: {e}")
            return False
    
    def store_embedding(self, listing_id: str, embedding: List[float]) -> bool:
        """
        Store embedding for a single property
        
        Args:
            listing_id: Property listing ID
            embedding: Embedding vector
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"""
            MATCH (p:{self.config.node_label} {{listing_id: $listing_id}})
            SET p.{self.config.embedding_property} = $embedding
            RETURN p.listing_id
            """
            
            with self.driver.session() as session:
                result = session.run(query, listing_id=listing_id, embedding=embedding)
                return result.single() is not None
                
        except Exception as e:
            print(f"Error storing embedding for {listing_id}: {e}")
            return False
    
    def store_embeddings_batch(self, embeddings: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store multiple embeddings in a batch
        
        Args:
            embeddings: List of dicts with 'listing_id' and 'embedding' keys
            
        Returns:
            Dictionary with counts of successful and failed operations
        """
        success_count = 0
        error_count = 0
        
        query = f"""
        UNWIND $embeddings AS item
        MATCH (p:{self.config.node_label} {{listing_id: item.listing_id}})
        SET p.{self.config.embedding_property} = item.embedding
        RETURN count(p) as updated_count
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, embeddings=embeddings)
                record = result.single()
                if record:
                    success_count = record["updated_count"]
                    error_count = len(embeddings) - success_count
                    
        except Exception as e:
            print(f"Error in batch embedding storage: {e}")
            error_count = len(embeddings)
        
        return {"success": success_count, "errors": error_count}
    
    def vector_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar properties using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of search results with property details and scores
        """
        try:
            # Neo4j vector search query
            query = f"""
            CALL db.index.vector.queryNodes(
                '{self.config.index_name}', 
                {top_k}, 
                $query_embedding
            ) 
            YIELD node, score
            WHERE score >= $min_score
            MATCH (node)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
            RETURN node.listing_id as listing_id,
                   node.address as address,
                   node.listing_price as price,
                   node.{self.config.source_property} as description,
                   node.bedrooms as bedrooms,
                   node.bathrooms as bathrooms,
                   node.square_feet as square_feet,
                   n.name as neighborhood,
                   c.name as city,
                   score
            ORDER BY score DESC
            """
            
            with self.driver.session() as session:
                results = session.run(
                    query, 
                    query_embedding=query_embedding,
                    min_score=min_score
                )
                return [dict(record) for record in results]
                
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    def check_embeddings_exist(self) -> Dict[str, int]:
        """
        Check how many properties have embeddings
        
        Returns:
            Dictionary with total properties and properties with embeddings
        """
        try:
            query = f"""
            MATCH (p:{self.config.node_label})
            WITH count(p) as total,
                 count(p.{self.config.embedding_property}) as with_embeddings
            RETURN total, with_embeddings
            """
            
            with self.driver.session() as session:
                result = session.run(query).single()
                if result:
                    return {
                        "total": result["total"],
                        "with_embeddings": result["with_embeddings"],
                        "without_embeddings": result["total"] - result["with_embeddings"]
                    }
                    
        except Exception as e:
            print(f"Error checking embeddings: {e}")
        
        return {"total": 0, "with_embeddings": 0, "without_embeddings": 0}
    
    def clear_embeddings(self) -> bool:
        """
        Clear all embeddings from properties
        
        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"""
            MATCH (p:{self.config.node_label})
            WHERE p.{self.config.embedding_property} IS NOT NULL
            REMOVE p.{self.config.embedding_property}
            RETURN count(p) as cleared_count
            """
            
            with self.driver.session() as session:
                result = session.run(query).single()
                if result:
                    print(f"✓ Cleared {result['cleared_count']} embeddings")
                    return True
                    
        except Exception as e:
            print(f"Error clearing embeddings: {e}")
        
        return False
    
    def get_properties_without_embeddings(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get properties that don't have embeddings yet
        
        Args:
            limit: Maximum number of properties to return
            
        Returns:
            List of properties without embeddings
        """
        try:
            query = f"""
            MATCH (p:{self.config.node_label})
            WHERE p.{self.config.embedding_property} IS NULL
            OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
            RETURN p.listing_id as listing_id,
                   p.{self.config.source_property} as description,
                   p.address as address,
                   p.listing_price as price,
                   p.bedrooms as bedrooms,
                   p.bathrooms as bathrooms,
                   p.square_feet as square_feet,
                   p.property_type as property_type,
                   p.features as features,
                   n.name as neighborhood,
                   c.name as city
            LIMIT $limit
            """
            
            with self.driver.session() as session:
                results = session.run(query, limit=limit)
                return [dict(record) for record in results]
                
        except Exception as e:
            print(f"Error getting properties without embeddings: {e}")
            return []