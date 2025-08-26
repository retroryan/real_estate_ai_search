"""
Similarity and knowledge relationship builders for Neo4j.
"""

import logging
from typing import Optional
from neo4j import Driver

from ..utils.database import run_query
from .config import RelationshipConfig

logger = logging.getLogger(__name__)


class SimilarityRelationshipBuilder:
    """Handles creation of similarity and knowledge relationships."""
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the similarity relationship builder.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
    
    def create_property_similarities(self) -> int:
        """
        Create SIMILAR_TO relationships between similar Properties.
        
        Uses a simplified similarity calculation based on:
        - Same neighborhood
        - Similar price (within 20%)
        - Same property type
        - Similar size (within 30%)
        - Similar bedrooms (within 1)
        
        Returns:
            Number of relationships created
        """
        # Create similarity relationships with calculated score
        query = f"""
        MATCH (p1:Property)-[:LOCATED_IN]->(n:Neighborhood)<-[:LOCATED_IN]-(p2:Property)
        WHERE p1.listing_id < p2.listing_id
        AND abs(p1.listing_price - p2.listing_price) / p1.listing_price < 0.2
        AND p1.property_type = p2.property_type
        AND abs(p1.bedrooms - p2.bedrooms) <= 1
        AND abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.3
        WITH p1, p2, 
             (1.0 - abs(p1.listing_price - p2.listing_price) / p1.listing_price) * 0.4 +
             (1.0 - abs(p1.square_feet - p2.square_feet) / p1.square_feet) * 0.3 +
             (CASE WHEN p1.bedrooms = p2.bedrooms THEN 0.2 ELSE 0.1 END) +
             (CASE WHEN p1.bathrooms = p2.bathrooms THEN 0.1 ELSE 0.0 END) as similarity_score
        WHERE similarity_score > {self.config.similarity_threshold}
        CREATE (p1)-[:SIMILAR_TO {{score: similarity_score}}]->(p2)
        CREATE (p2)-[:SIMILAR_TO {{score: similarity_score}}]->(p1)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating SIMILAR_TO relationships...")
        
        result = run_query(self.driver, query)
        # Divide by 2 since we create bidirectional relationships
        return (result[0]["count"] // 2) if result else 0
    
    def create_describes(self) -> int:
        """
        Create DESCRIBES relationships between Wikipedia articles and Neighborhoods.
        
        Matches based on:
        - WikipediaArticle city field matching Neighborhood city field
        - WikipediaArticle has valid location data
        
        Includes relationship properties:
        - confidence: The location confidence score from Wikipedia data
        - relationship_type: The content category from Wikipedia data
        
        Returns:
            Number of relationships created
        """
        # Match WikipediaArticles to Neighborhoods based on city
        query = """
        MATCH (w:WikipediaArticle)
        WHERE w.best_city IS NOT NULL AND w.has_valid_location = true
        MATCH (n:Neighborhood)
        WHERE n.city = w.best_city
        MERGE (w)-[r:DESCRIBES]->(n)
        ON CREATE SET 
            r.confidence = COALESCE(w.location_confidence, 0.5),
            r.relationship_type = COALESCE(w.content_category, 'general'),
            r.relevance_score = COALESCE(w.location_relevance_score, 0.5)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating DESCRIBES relationships between WikipediaArticles and Neighborhoods...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_neighborhood_similarities(self) -> int:
        """
        Create SIMILAR_TO relationships between similar Neighborhoods.
        
        Calculates similarity based on:
        - Lifestyle tags overlap
        - Wikipedia article overlap
        - Same city location
        
        Returns:
            Number of relationships created
        """
        # First get neighborhoods with their data
        query = """
        MATCH (n:Neighborhood)
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:WikipediaArticle)
        RETURN n.neighborhood_id as id,
               n.name as name,
               n.city as city,
               n.lifestyle_tags as tags,
               collect(DISTINCT w.relationship_type) as wiki_types
        """
        
        neighborhoods = run_query(self.driver, query)
        
        if not neighborhoods:
            return 0
        
        # Calculate similarities and create relationships
        similarity_count = 0
        for i, n1 in enumerate(neighborhoods):
            for n2 in neighborhoods[i+1:]:
                # Only compare neighborhoods in the same city
                if n1.get('city') != n2.get('city'):
                    continue
                
                # Calculate lifestyle tag similarity
                tags1 = set(n1.get('tags') or [])
                tags2 = set(n2.get('tags') or [])
                tag_sim = len(tags1 & tags2) / len(tags1 | tags2) if (tags1 | tags2) else 0
                
                # Calculate Wikipedia overlap
                wiki1 = set(n1.get('wiki_types') or [])
                wiki2 = set(n2.get('wiki_types') or [])
                wiki_sim = len(wiki1 & wiki2) / len(wiki1 | wiki2) if (wiki1 | wiki2) else 0
                
                # Overall similarity (weighted)
                overall_sim = (tag_sim * 0.6 + wiki_sim * 0.4)
                
                # Only create relationship if similarity is significant
                if overall_sim > 0.3:
                    query = """
                    MATCH (n1:Neighborhood {neighborhood_id: $id1})
                    MATCH (n2:Neighborhood {neighborhood_id: $id2})
                    CREATE (n1)-[:SIMILAR_TO {
                        similarity_score: $overall,
                        lifestyle_similarity: $lifestyle,
                        wikipedia_overlap: $wiki
                    }]->(n2)
                    CREATE (n2)-[:SIMILAR_TO {
                        similarity_score: $overall,
                        lifestyle_similarity: $lifestyle,
                        wikipedia_overlap: $wiki
                    }]->(n1)
                    """
                    
                    run_query(self.driver, query, {
                        'id1': n1['id'],
                        'id2': n2['id'],
                        'overall': overall_sim,
                        'lifestyle': tag_sim,
                        'wiki': wiki_sim
                    })
                    similarity_count += 1
        
        if self.config.verbose:
            logger.debug(f"Created {similarity_count} neighborhood similarity relationships")
        
        return similarity_count