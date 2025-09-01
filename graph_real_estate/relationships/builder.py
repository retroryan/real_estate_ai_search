"""
Main relationship orchestrator that coordinates all relationship creation.

This module handles relationships not covered by the pipeline (NEAR, similarity, etc).
Basic relationships are created by squack_pipeline_v2.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from neo4j import Driver

from graph_real_estate.utils.database import run_query
from graph_real_estate.relationships.config import RelationshipConfig
from graph_real_estate.relationships.geographic import GeographicRelationshipBuilder
from graph_real_estate.relationships.classification import ClassificationRelationshipBuilder
from graph_real_estate.relationships.similarity import SimilarityRelationshipBuilder

logger = logging.getLogger(__name__)


class RelationshipStats(BaseModel):
    """Statistics about relationships in the database."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    # Pipeline-created relationships (for reporting only)
    located_in: int = Field(default=0, description="Properties -> Neighborhoods")
    in_zip_code: int = Field(default=0, description="Properties/Neighborhoods -> ZipCodes")
    in_city: int = Field(default=0, description="ZipCodes -> Cities")
    in_county: int = Field(default=0, description="Cities -> Counties")
    in_state: int = Field(default=0, description="Counties -> States")
    has_feature: int = Field(default=0, description="Properties -> Features")
    of_type: int = Field(default=0, description="Properties -> PropertyTypes")
    in_price_range: int = Field(default=0, description="Properties -> PriceRanges")
    
    # Graph module relationships
    near: int = Field(default=0, description="Neighborhoods <-> Neighborhoods")
    similar_to: int = Field(default=0, description="Properties/Neighborhoods similarity")
    describes: int = Field(default=0, description="Wikipedia -> Neighborhoods")
    
    @property
    def total(self) -> int:
        """Calculate total number of relationships."""
        return sum(self.model_dump().values())
    
    def summary(self) -> dict:
        """Get summary dictionary with total."""
        result = self.model_dump()
        result['total'] = self.total
        return result


class RelationshipOrchestrator:
    """
    Orchestrates the creation of complex relationships in Neo4j.
    
    This class handles relationships not covered by the pipeline:
    - NEAR relationships between neighborhoods
    - Similarity relationships (if enabled)
    - Other complex graph analytics
    """
    
    def __init__(self, driver: Driver, config: Optional[RelationshipConfig] = None):
        """
        Initialize the relationship orchestrator.
        
        Args:
            driver: Neo4j driver instance
            config: Relationship configuration
        """
        self.driver = driver
        self.config = config or RelationshipConfig()
        
        # Initialize builders for complex relationships
        self.geographic_builder = GeographicRelationshipBuilder(driver, config)
        self.classification_builder = ClassificationRelationshipBuilder(driver, config)
        self.similarity_builder = SimilarityRelationshipBuilder(driver, config)
        
        self.stats = RelationshipStats()
    
    def build_all_relationships(self) -> RelationshipStats:
        """
        Build complex relationships not handled by the pipeline.
        
        Returns:
            RelationshipStats with counts of all relationships
        """
        logger.info("="*60)
        logger.info("Building complex graph relationships")
        logger.info("="*60)
        
        # First, get existing relationship counts from pipeline
        self._count_existing_relationships()
        
        # Build NEAR relationships (requires geographic hierarchy)
        logger.info("\n📍 Building NEAR relationships...")
        try:
            self.stats.near = self.geographic_builder.create_near()
            logger.info(f"✓ Created {self.stats.near:,} NEAR relationships")
        except Exception as e:
            logger.warning(f"NEAR relationships failed: {e}")
            self.stats.near = 0
        
        # Optionally build similarity relationships
        if self.config.enable_similarity:
            logger.info("\n🔗 Building similarity relationships...")
            try:
                property_sim = self.similarity_builder.create_property_similarities()
                neighborhood_sim = self.similarity_builder.create_neighborhood_similarities()
                self.stats.similar_to = property_sim + neighborhood_sim
                logger.info(f"✓ Created {self.stats.similar_to:,} SIMILAR_TO relationships")
            except Exception as e:
                logger.warning(f"Similarity relationships failed: {e}")
                self.stats.similar_to = 0
        
        # Build Wikipedia relationships if available
        logger.info("\n📚 Building Wikipedia relationships...")
        try:
            self.stats.describes = self.similarity_builder.create_describes()
            logger.info(f"✓ Created {self.stats.describes:,} DESCRIBES relationships")
        except Exception as e:
            logger.warning(f"Wikipedia relationships failed: {e}")
            self.stats.describes = 0
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _count_existing_relationships(self):
        """Count relationships already created by the pipeline."""
        logger.info("Counting existing pipeline relationships...")
        
        relationship_queries = {
            'located_in': "MATCH ()-[r:LOCATED_IN]->() RETURN count(r) as count",
            'in_zip_code': "MATCH ()-[r:IN_ZIP_CODE]->() RETURN count(r) as count",
            'in_city': "MATCH ()-[r:IN_CITY]->() RETURN count(r) as count",
            'in_county': "MATCH ()-[r:IN_COUNTY]->() RETURN count(r) as count",
            'in_state': "MATCH ()-[r:IN_STATE]->() RETURN count(r) as count",
            'has_feature': "MATCH ()-[r:HAS_FEATURE]->() RETURN count(r) as count",
            'of_type': "MATCH ()-[r:OF_TYPE]->() RETURN count(r) as count",
            'in_price_range': "MATCH ()-[r:IN_PRICE_RANGE]->() RETURN count(r) as count"
        }
        
        for field, query in relationship_queries.items():
            try:
                result = run_query(self.driver, query)
                count = result[0]["count"] if result else 0
                setattr(self.stats, field, count)
            except Exception as e:
                logger.warning(f"Could not count {field}: {e}")
                setattr(self.stats, field, 0)
    
    def _print_summary(self):
        """Print summary statistics."""
        logger.info("\n" + "="*60)
        logger.info("RELATIONSHIP SUMMARY")
        logger.info("="*60)
        
        logger.info("\n📊 Pipeline-created relationships:")
        logger.info(f"  LOCATED_IN:     {self.stats.located_in:10,}")
        logger.info(f"  IN_ZIP_CODE:    {self.stats.in_zip_code:10,}")
        logger.info(f"  IN_CITY:        {self.stats.in_city:10,}")
        logger.info(f"  IN_COUNTY:      {self.stats.in_county:10,}")
        logger.info(f"  IN_STATE:       {self.stats.in_state:10,}")
        logger.info(f"  HAS_FEATURE:    {self.stats.has_feature:10,}")
        logger.info(f"  OF_TYPE:        {self.stats.of_type:10,}")
        logger.info(f"  IN_PRICE_RANGE: {self.stats.in_price_range:10,}")
        
        logger.info("\n🔗 Graph module relationships:")
        logger.info(f"  NEAR:           {self.stats.near:10,}")
        logger.info(f"  SIMILAR_TO:     {self.stats.similar_to:10,}")
        logger.info(f"  DESCRIBES:      {self.stats.describes:10,}")
        
        logger.info("-"*60)
        logger.info(f"  TOTAL:          {self.stats.total:10,}")
        logger.info("="*60)
    
    def verify_relationships(self) -> RelationshipStats:
        """
        Verify all relationships in the database.
        
        Returns:
            RelationshipStats with actual counts from database
        """
        logger.info("Verifying all relationships...")
        
        # Re-count everything
        self._count_existing_relationships()
        
        # Count graph module relationships
        for field, rel_type in [('near', 'NEAR'), ('similar_to', 'SIMILAR_TO'), ('describes', 'DESCRIBES')]:
            try:
                query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
                result = run_query(self.driver, query)
                count = result[0]["count"] if result else 0
                setattr(self.stats, field, count)
            except Exception as e:
                logger.warning(f"Could not verify {rel_type}: {e}")
        
        return self.stats