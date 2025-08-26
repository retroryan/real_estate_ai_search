"""
Classification relationship builders for Neo4j.
"""

import logging
from typing import Optional
from neo4j import Driver

from ..utils.database import run_query
from .config import RelationshipConfig

logger = logging.getLogger(__name__)


class ClassificationRelationshipBuilder:
    """Handles creation of classification relationships."""
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the classification relationship builder.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
    
    def create_has_feature(self) -> int:
        """
        Create HAS_FEATURE relationships between Properties and Features.
        
        Returns:
            Number of relationships created
        """
        # Properties have a features array field
        query = """
        MATCH (p:Property)
        WHERE p.features IS NOT NULL
        UNWIND p.features AS feature_name
        MATCH (f:Feature {name: feature_name})
        MERGE (p)-[:HAS_FEATURE]->(f)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating HAS_FEATURE relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_of_type(self) -> int:
        """
        Create TYPE_OF relationships between Properties and PropertyTypes.
        
        Returns:
            Number of relationships created
        """
        query = """
        MATCH (p:Property)
        WHERE p.property_type IS NOT NULL
        MATCH (pt:PropertyType {name: p.property_type})
        MERGE (p)-[:TYPE_OF]->(pt)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating TYPE_OF relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0
    
    def create_in_price_range(self) -> int:
        """
        Create IN_PRICE_RANGE relationships between Properties and PriceRanges.
        
        Returns:
            Number of relationships created
        """
        # Build CASE statement for price ranges
        case_statements = []
        for price_range in self.config.price_ranges:
            if price_range == "5M+":
                case_statements.append("WHEN p.listing_price >= 5000000 THEN '5M+'")
            elif "-" in price_range:
                parts = price_range.replace("K", "000").replace("M", "000000").split("-")
                min_val = int(parts[0])
                max_val = int(parts[1])
                case_statements.append(
                    f"WHEN p.listing_price >= {min_val} AND p.listing_price < {max_val} THEN '{price_range}'"
                )
        
        case_query = "\n".join(case_statements)
        
        query = f"""
        MATCH (p:Property)
        WHERE p.listing_price IS NOT NULL
        WITH p, 
        CASE 
            {case_query}
            ELSE 'Unknown'
        END AS price_range
        MATCH (pr:PriceRange {{range: price_range}})
        MERGE (p)-[:IN_PRICE_RANGE]->(pr)
        RETURN count(*) as count
        """
        
        if self.config.verbose:
            logger.debug("Creating IN_PRICE_RANGE relationships...")
        
        result = run_query(self.driver, query)
        return result[0]["count"] if result else 0