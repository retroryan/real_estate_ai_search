"""Similarity calculator loader with constructor injection"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import math

from core.query_executor import QueryExecutor
from core.config import SimilarityConfig, LoaderConfig
from models.similarity import SimilarityLoadResult


class SimilarityLoader:
    """Calculate and create similarity relationships with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        config: SimilarityConfig,
        loader_config: LoaderConfig
    ):
        """
        Initialize similarity loader with dependencies
        
        Args:
            query_executor: Database query executor
            config: Similarity configuration
            loader_config: Loader batch configuration
        """
        self.query_executor = query_executor
        self.config = config
        self.loader_config = loader_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load result tracking
        self.load_result = SimilarityLoadResult()
    
    def load(self) -> SimilarityLoadResult:
        """
        Main loading method
        
        Returns:
            SimilarityLoadResult with statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("RELATIONSHIP ENHANCEMENT AND SIMILARITY CALCULATIONS")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Create property similarity relationships
            self._create_property_similarities()
            
            # Create neighborhood proximity relationships
            self._create_neighborhood_connections()
            
            # Create topic clusters
            self._create_topic_clusters()
            
            # Create geographic proximity relationships
            self._create_geographic_proximities()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self.load_result.success = True
            
            self.logger.info("=" * 60)
            self.logger.info("✅ SIMILARITY CALCULATIONS COMPLETE")
            self.logger.info(f"  Property similarities: {self.load_result.property_similarities_created}")
            self.logger.info(f"  Neighborhood connections: {self.load_result.neighborhood_connections_created}")
            self.logger.info(f"  Topic clusters: {self.load_result.topic_clusters_created}")
            self.logger.info(f"  Geographic proximities: {self.load_result.proximity_relationships_created}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to calculate similarities: {e}")
            self.load_result.add_error(str(e))
            self.load_result.success = False
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _create_property_similarities(self) -> None:
        """Create SIMILAR_TO relationships between properties"""
        self.logger.info("Calculating property similarities...")
        
        # Get all properties with their features
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        RETURN p.listing_id as listing_id,
               p.listing_price as price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               p.neighborhood_id as neighborhood_id,
               collect(f.feature_id) as features
        """
        
        properties = self.query_executor.execute_read(query)
        
        if not properties:
            self.logger.warning("No properties found for similarity calculation")
            return
        
        # Calculate similarities
        similarities = []
        for i, prop1 in enumerate(properties):
            for prop2 in properties[i+1:]:
                score = self._calculate_property_similarity(prop1, prop2)
                
                if score >= self.config.property_similarity_threshold:
                    similarities.append({
                        'id1': prop1['listing_id'],
                        'id2': prop2['listing_id'],
                        'score': score
                    })
        
        # Create relationships in batches
        if similarities:
            query = """
            UNWIND $batch AS sim
            MATCH (p1:Property {listing_id: sim.id1})
            MATCH (p2:Property {listing_id: sim.id2})
            MERGE (p1)-[r:SIMILAR_TO]-(p2)
            SET r.similarity_score = sim.score,
                r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(similarities), batch_size):
                batch = similarities[i:i + batch_size]
                self.query_executor.execute_write(query, {'batch': batch})
                total_created += len(batch)
            
            self.load_result.property_similarities_created = total_created
            self.logger.info(f"  Created {total_created} property similarity relationships")
    
    def _calculate_property_similarity(self, prop1: Dict, prop2: Dict) -> float:
        """Calculate similarity score between two properties"""
        score = 0.0
        
        # Feature similarity
        if prop1.get('features') and prop2.get('features'):
            features1 = set(prop1['features'])
            features2 = set(prop2['features'])
            if features1 and features2:
                jaccard = len(features1 & features2) / len(features1 | features2)
                score += jaccard * self.config.feature_weight
        
        # Price similarity
        if prop1.get('price') and prop2.get('price'):
            price_diff = abs(prop1['price'] - prop2['price'])
            max_price = max(prop1['price'], prop2['price'])
            price_sim = 1 - (price_diff / max_price)
            score += price_sim * self.config.price_weight
        
        # Size similarity
        if prop1.get('square_feet') and prop2.get('square_feet'):
            size_diff = abs(prop1['square_feet'] - prop2['square_feet'])
            max_size = max(prop1['square_feet'], prop2['square_feet'])
            size_sim = 1 - (size_diff / max_size)
            score += size_sim * self.config.size_weight
        
        # Location similarity (same neighborhood)
        if prop1.get('neighborhood_id') == prop2.get('neighborhood_id'):
            score += self.config.location_weight
        
        return score
    
    def _create_neighborhood_connections(self) -> None:
        """Create NEAR relationships between neighborhoods"""
        self.logger.info("Creating neighborhood proximity connections...")
        
        # Get neighborhoods with coordinates
        query = """
        MATCH (n:Neighborhood)
        WHERE n.latitude IS NOT NULL AND n.longitude IS NOT NULL
        RETURN n.neighborhood_id as id,
               n.latitude as lat,
               n.longitude as lng,
               n.city as city
        """
        
        neighborhoods = self.query_executor.execute_read(query)
        
        if not neighborhoods:
            self.logger.warning("No neighborhoods with coordinates found")
            return
        
        # Calculate proximities
        connections = []
        for i, n1 in enumerate(neighborhoods):
            for n2 in neighborhoods[i+1:]:
                # Only connect neighborhoods in the same city
                if n1['city'] != n2['city']:
                    continue
                
                distance = self._haversine_distance(
                    n1['lat'], n1['lng'],
                    n2['lat'], n2['lng']
                )
                
                if distance <= self.config.neighborhood_proximity_threshold:
                    connections.append({
                        'id1': n1['id'],
                        'id2': n2['id'],
                        'distance': distance
                    })
        
        # Create relationships
        if connections:
            query = """
            UNWIND $batch AS conn
            MATCH (n1:Neighborhood {neighborhood_id: conn.id1})
            MATCH (n2:Neighborhood {neighborhood_id: conn.id2})
            MERGE (n1)-[r:NEAR]-(n2)
            SET r.distance_miles = conn.distance,
                r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(connections), batch_size):
                batch = connections[i:i + batch_size]
                self.query_executor.execute_write(query, {'batch': batch})
                total_created += len(batch)
            
            self.load_result.neighborhood_connections_created = total_created
            self.logger.info(f"  Created {total_created} neighborhood proximity relationships")
    
    def _create_topic_clusters(self) -> None:
        """Create clusters of related topics"""
        self.logger.info("Creating topic clusters...")
        
        # Find topics that appear together frequently
        query = """
        MATCH (w:WikipediaArticle)-[:HAS_TOPIC]->(t1:Topic)
        MATCH (w)-[:HAS_TOPIC]->(t2:Topic)
        WHERE id(t1) < id(t2)
        WITH t1, t2, count(w) as cooccurrence
        WHERE cooccurrence >= 2
        RETURN t1.topic_id as topic1,
               t2.topic_id as topic2,
               cooccurrence
        """
        
        topic_pairs = self.query_executor.execute_read(query)
        
        if topic_pairs:
            query = """
            UNWIND $batch AS pair
            MATCH (t1:Topic {topic_id: pair.topic1})
            MATCH (t2:Topic {topic_id: pair.topic2})
            MERGE (t1)-[r:RELATED_TO]-(t2)
            SET r.cooccurrence = pair.cooccurrence,
                r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(topic_pairs), batch_size):
                batch = topic_pairs[i:i + batch_size]
                self.query_executor.execute_write(query, {'batch': batch})
                total_created += len(batch)
            
            self.load_result.topic_clusters_created = total_created
            self.logger.info(f"  Created {total_created} topic cluster relationships")
    
    def _create_geographic_proximities(self) -> None:
        """Create NEAR_BY relationships between properties in nearby neighborhoods"""
        self.logger.info("Creating geographic proximity relationships...")
        
        # Find properties in connected neighborhoods
        query = """
        MATCH (n1:Neighborhood)-[:NEAR]-(n2:Neighborhood)
        MATCH (p1:Property)-[:IN_NEIGHBORHOOD]->(n1)
        MATCH (p2:Property)-[:IN_NEIGHBORHOOD]->(n2)
        WHERE id(p1) < id(p2)
        WITH p1, p2, n1, n2
        LIMIT 10000
        RETURN p1.listing_id as id1,
               p2.listing_id as id2,
               n1.neighborhood_id as n1_id,
               n2.neighborhood_id as n2_id
        """
        
        proximities = self.query_executor.execute_read(query)
        
        if proximities:
            query = """
            UNWIND $batch AS prox
            MATCH (p1:Property {listing_id: prox.id1})
            MATCH (p2:Property {listing_id: prox.id2})
            MERGE (p1)-[r:NEAR_BY]-(p2)
            SET r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(proximities), batch_size):
                batch = proximities[i:i + batch_size]
                self.query_executor.execute_write(query, {'batch': batch})
                total_created += len(batch)
            
            self.load_result.proximity_relationships_created = total_created
            self.logger.info(f"  Created {total_created} geographic proximity relationships")
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates in miles"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c