"""
Main relationship orchestrator that coordinates all relationship creation.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from neo4j import Driver

from utils.database import run_query
from relationships.config import RelationshipConfig
from relationships.geographic import GeographicRelationshipBuilder
from relationships.classification import ClassificationRelationshipBuilder
from relationships.similarity import SimilarityRelationshipBuilder

logger = logging.getLogger(__name__)


class RelationshipStats(BaseModel):
    """Statistics about relationships in the database."""
    
    LOCATED_IN: int = Field(default=0, description="Properties -> Neighborhoods")
    IN_CITY: int = Field(default=0, description="Neighborhoods -> Cities")
    IN_COUNTY: int = Field(default=0, description="Cities -> Counties")
    NEAR: int = Field(default=0, description="Neighborhoods <-> Neighborhoods")
    HAS_FEATURE: int = Field(default=0, description="Properties -> Features")
    TYPE_OF: int = Field(default=0, description="Properties -> PropertyTypes")
    IN_PRICE_RANGE: int = Field(default=0, description="Properties -> PriceRanges")
    SIMILAR_TO: int = Field(default=0, description="Properties <-> Properties")
    DESCRIBES: int = Field(default=0, description="Wikipedia -> Neighborhoods")
    
    @property
    def total(self) -> int:
        """Calculate total number of relationships."""
        return sum(self.dict().values())
    
    def summary(self) -> dict:
        """Get summary dictionary with total."""
        result = self.dict()
        result['TOTAL'] = self.total
        return result


class RelationshipOrchestrator:
    """
    Orchestrates the creation of all relationships in Neo4j.
    
    This class coordinates the relationship building process, ensuring
    relationships are created in the correct order with proper error handling.
    """
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the relationship orchestrator.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration (uses defaults if not provided)
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
        
        # Initialize relationship builders
        self.geographic_builder = GeographicRelationshipBuilder(driver, config)
        self.classification_builder = ClassificationRelationshipBuilder(driver, config)
        self.similarity_builder = SimilarityRelationshipBuilder(driver, config)
        
        # Track statistics
        self.stats = RelationshipStats()
    
    def build_all_relationships(self) -> RelationshipStats:
        """
        Build all relationships in the correct order.
        
        Returns:
            RelationshipStats with counts of relationships created
        """
        logger.info("="*60)
        logger.info("Starting relationship building process")
        logger.info("="*60)
        
        try:
            # Phase 1: Geographic relationships (hierarchy)
            logger.info("\n📍 Phase 1: Geographic Relationships")
            self._build_geographic_relationships()
            
            # Phase 2: Classification relationships
            logger.info("\n🏷️ Phase 2: Classification Relationships")
            self._build_classification_relationships()
            
            # Phase 3: Similarity relationships
            logger.info("\n🔗 Phase 3: Similarity Relationships")
            self._build_similarity_relationships()
            
            # Print summary
            self._print_summary()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Relationship building failed: {e}")
            raise
    
    def _build_geographic_relationships(self):
        """Build all geographic relationships."""
        try:
            # LOCATED_IN: Properties -> Neighborhoods
            self.stats.LOCATED_IN = self.geographic_builder.create_located_in()
            logger.info(f"  ✓ Created {self.stats.LOCATED_IN:,} LOCATED_IN relationships")
            
            # IN_CITY: Neighborhoods -> Cities  
            self.stats.IN_CITY = self.geographic_builder.create_in_city()
            logger.info(f"  ✓ Created {self.stats.IN_CITY:,} IN_CITY relationships")
            
            # IN_COUNTY: Cities -> Counties
            self.stats.IN_COUNTY = self.geographic_builder.create_in_county()
            logger.info(f"  ✓ Created {self.stats.IN_COUNTY:,} IN_COUNTY relationships")
            
            # NEAR: Neighborhoods <-> Neighborhoods
            self.stats.NEAR = self.geographic_builder.create_near()
            logger.info(f"  ✓ Created {self.stats.NEAR:,} NEAR relationships")
            
        except Exception as e:
            logger.error(f"Geographic relationship creation failed: {e}")
            raise
    
    def _build_classification_relationships(self):
        """Build all classification relationships."""
        try:
            # HAS_FEATURE: Properties -> Features
            self.stats.HAS_FEATURE = self.classification_builder.create_has_feature()
            logger.info(f"  ✓ Created {self.stats.HAS_FEATURE:,} HAS_FEATURE relationships")
            
            # TYPE_OF: Properties -> PropertyTypes
            self.stats.TYPE_OF = self.classification_builder.create_of_type()
            logger.info(f"  ✓ Created {self.stats.TYPE_OF:,} TYPE_OF relationships")
            
            # IN_PRICE_RANGE: Properties -> PriceRanges
            self.stats.IN_PRICE_RANGE = self.classification_builder.create_in_price_range()
            logger.info(f"  ✓ Created {self.stats.IN_PRICE_RANGE:,} IN_PRICE_RANGE relationships")
            
        except Exception as e:
            logger.error(f"Classification relationship creation failed: {e}")
            raise
    
    def _build_similarity_relationships(self):
        """Build all similarity and knowledge relationships."""
        try:
            # SIMILAR_TO: Properties <-> Properties
            property_similarities = self.similarity_builder.create_property_similarities()
            logger.info(f"  ✓ Created {property_similarities:,} property SIMILAR_TO relationships")
            
            # SIMILAR_TO: Neighborhoods <-> Neighborhoods
            neighborhood_similarities = self.similarity_builder.create_neighborhood_similarities()
            logger.info(f"  ✓ Created {neighborhood_similarities:,} neighborhood SIMILAR_TO relationships")
            
            # Total SIMILAR_TO count
            self.stats.SIMILAR_TO = property_similarities + neighborhood_similarities
            
            # DESCRIBES: Wikipedia -> Neighborhoods
            self.stats.DESCRIBES = self.similarity_builder.create_describes()
            logger.info(f"  ✓ Created {self.stats.DESCRIBES:,} DESCRIBES relationships")
            
        except Exception as e:
            logger.error(f"Similarity relationship creation failed: {e}")
            raise
    
    def _print_summary(self):
        """Print summary statistics."""
        logger.info("\n" + "="*60)
        logger.info("RELATIONSHIP BUILDING SUMMARY")
        logger.info("="*60)
        
        for rel_type, count in self.stats.dict().items():
            logger.info(f"  {rel_type:20} {count:10,} relationships")
        
        logger.info("-"*60)
        logger.info(f"  {'TOTAL':20} {self.stats.total:10,} relationships")
        logger.info("="*60)
        logger.info("✅ Relationship building complete!")
    
    def verify_relationships(self) -> RelationshipStats:
        """
        Verify that relationships were created correctly.
        
        Returns:
            RelationshipStats with actual counts from database
        """
        logger.info("Verifying relationships...")
        
        stats = RelationshipStats()
        
        # Query each relationship type directly
        for rel_type in stats.__fields__.keys():
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            count = result[0]["count"] if result else 0
            setattr(stats, rel_type, count)
        
        return stats