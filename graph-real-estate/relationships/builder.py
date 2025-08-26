"""
Main relationship orchestrator that coordinates all relationship creation.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from neo4j import Driver

from ..utils.database import run_query
from .config import RelationshipConfig, RelationshipResult
from .geographic import GeographicRelationshipBuilder
from .classification import ClassificationRelationshipBuilder
from .similarity import SimilarityRelationshipBuilder
from .cleanup import PropertyCleanupBuilder

logger = logging.getLogger(__name__)


class RelationshipStats(BaseModel):
    """Statistics about relationships in the database."""
    
    LOCATED_IN: int = Field(default=0, description="Properties -> Neighborhoods")
    IN_ZIP_CODE: int = Field(default=0, description="Properties/Neighborhoods -> ZipCodes")
    IN_CITY: int = Field(default=0, description="ZipCodes -> Cities")
    IN_COUNTY: int = Field(default=0, description="Cities -> Counties")
    IN_STATE: int = Field(default=0, description="Counties -> States")
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


class BuildProcessStats(BaseModel):
    """Complete statistics for the relationship building process."""
    
    relationships: RelationshipStats = Field(default_factory=RelationshipStats)
    nodes_cleaned: int = Field(default=0, description="Nodes cleaned of denormalized properties")
    
    @property
    def total_relationships(self) -> int:
        """Total number of relationships created."""
        return self.relationships.total


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
        self.cleanup_builder = PropertyCleanupBuilder(driver, config)
        
        # Track statistics
        self.stats = BuildProcessStats()
    
    def build_all_relationships(self) -> BuildProcessStats:
        """
        Build all relationships in the correct order.
        
        Returns:
            BuildProcessStats with counts of relationships created and nodes cleaned
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
            
            # Phase 4: Property cleanup (denormalization removal)
            logger.info("\n🧹 Phase 4: Property Cleanup")
            self._cleanup_denormalized_properties()
            
            # Print summary
            self._print_summary()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Relationship building failed: {e}")
            raise
    
    def _build_geographic_relationships(self):
        """Build all geographic relationships in hierarchical order with enhanced error handling."""
        logger.info("Building geographic hierarchy relationships...")
        
        # Track failed operations
        failed_operations = []
        
        # LOCATED_IN: Properties -> Neighborhoods (optional)
        try:
            self.stats.relationships.LOCATED_IN = self.geographic_builder.create_located_in()
        except Exception as e:
            failed_operations.append(f"LOCATED_IN: {str(e)}")
            self.stats.relationships.LOCATED_IN = 0
            logger.warning(f"LOCATED_IN relationships failed: {e}")
        
        # IN_ZIP_CODE: Properties -> ZipCodes (critical)
        try:
            property_zip = self.geographic_builder.create_in_zip_code()
        except Exception as e:
            failed_operations.append(f"Property->ZipCode: {str(e)}")
            property_zip = 0
            logger.error(f"Critical: Property->ZipCode relationships failed: {e}")
        
        # IN_ZIP_CODE: Neighborhoods -> ZipCodes (important but not critical)
        try:
            neighborhood_zip = self.geographic_builder.create_neighborhood_in_zip()
        except Exception as e:
            failed_operations.append(f"Neighborhood->ZipCode: {str(e)}")
            neighborhood_zip = 0
            logger.warning(f"Neighborhood->ZipCode relationships failed: {e}")
        
        # Total IN_ZIP_CODE count
        self.stats.relationships.IN_ZIP_CODE = property_zip + neighborhood_zip
        
        # IN_CITY: ZipCodes -> Cities (critical for hierarchy)
        try:
            self.stats.relationships.IN_CITY = self.geographic_builder.create_zip_in_city()
        except Exception as e:
            failed_operations.append(f"ZipCode->City: {str(e)}")
            self.stats.relationships.IN_CITY = 0
            logger.error(f"Critical: ZipCode->City relationships failed: {e}")
        
        # IN_COUNTY: Cities -> Counties (important)
        try:
            self.stats.relationships.IN_COUNTY = self.geographic_builder.create_city_in_county()
        except Exception as e:
            failed_operations.append(f"City->County: {str(e)}")
            self.stats.relationships.IN_COUNTY = 0
            logger.warning(f"City->County relationships failed: {e}")
        
        # IN_STATE: Counties -> States (important)
        try:
            self.stats.relationships.IN_STATE = self.geographic_builder.create_county_in_state()
        except Exception as e:
            failed_operations.append(f"County->State: {str(e)}")
            self.stats.relationships.IN_STATE = 0
            logger.warning(f"County->State relationships failed: {e}")
        
        # NEAR: Neighborhoods <-> Neighborhoods (optional, depends on hierarchy)
        try:
            self.stats.relationships.NEAR = self.geographic_builder.create_near()
        except Exception as e:
            failed_operations.append(f"NEAR: {str(e)}")
            self.stats.relationships.NEAR = 0
            logger.warning(f"NEAR relationships failed: {e}")
        
        # Report results
        if failed_operations:
            logger.warning(f"Geographic relationships completed with {len(failed_operations)} failures:")
            for failure in failed_operations:
                logger.warning(f"  - {failure}")
        else:
            logger.info("✅ All geographic relationships created successfully")
            
        # Only raise exception if critical relationships failed
        critical_failures = [f for f in failed_operations if any(x in f for x in ["Property->ZipCode", "ZipCode->City"])]
        if critical_failures:
            raise RuntimeError(f"Critical geographic relationships failed: {critical_failures}")
    
    def _build_classification_relationships(self):
        """Build all classification relationships."""
        try:
            # HAS_FEATURE: Properties -> Features
            self.stats.relationships.HAS_FEATURE = self.classification_builder.create_has_feature()
            logger.info(f"  ✓ Created {self.stats.relationships.HAS_FEATURE:,} HAS_FEATURE relationships")
            
            # TYPE_OF: Properties -> PropertyTypes
            self.stats.relationships.TYPE_OF = self.classification_builder.create_of_type()
            logger.info(f"  ✓ Created {self.stats.relationships.TYPE_OF:,} TYPE_OF relationships")
            
            # IN_PRICE_RANGE: Properties -> PriceRanges
            self.stats.relationships.IN_PRICE_RANGE = self.classification_builder.create_in_price_range()
            logger.info(f"  ✓ Created {self.stats.relationships.IN_PRICE_RANGE:,} IN_PRICE_RANGE relationships")
            
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
            self.stats.relationships.SIMILAR_TO = property_similarities + neighborhood_similarities
            
            # DESCRIBES: Wikipedia -> Neighborhoods
            self.stats.relationships.DESCRIBES = self.similarity_builder.create_describes()
            logger.info(f"  ✓ Created {self.stats.relationships.DESCRIBES:,} DESCRIBES relationships")
            
        except Exception as e:
            logger.error(f"Similarity relationship creation failed: {e}")
            raise
    
    def _cleanup_denormalized_properties(self):
        """
        Clean up denormalized properties after relationships are established.
        
        This completes the three-phase normalization:
        1. Create complete nodes (data_pipeline phase)
        2. Create relationships using complete data (relationship phases)
        3. Clean up denormalized properties (this phase)
        """
        try:
            cleanup_stats = self.cleanup_builder.cleanup_all_denormalization()
            self.stats.nodes_cleaned = cleanup_stats.total_nodes_cleaned
            
            logger.info(f"  ✓ Cleaned {cleanup_stats.properties_cleaned:,} Property nodes")
            logger.info(f"  ✓ Cleaned {cleanup_stats.neighborhoods_cleaned:,} Neighborhood nodes")
            logger.info(f"  ✓ Total: {cleanup_stats.total_nodes_cleaned:,} nodes normalized")
            
        except Exception as e:
            logger.error(f"Property cleanup failed: {e}")
            self.stats.nodes_cleaned = 0
            # Don't raise - cleanup failure shouldn't stop the entire process
    
    def _print_summary(self):
        """Print summary statistics."""
        logger.info("\n" + "="*60)
        logger.info("RELATIONSHIP BUILDING SUMMARY")
        logger.info("="*60)
        
        # Print relationship statistics
        for rel_type, count in self.stats.relationships.dict().items():
            logger.info(f"  {rel_type:20} {count:10,} relationships")
        
        logger.info("-"*60)
        logger.info(f"  {'TOTAL':20} {self.stats.total_relationships:10,} relationships")
        
        # Print cleanup statistics if any nodes were cleaned
        if self.stats.nodes_cleaned > 0:
            logger.info(f"  {'NODES_CLEANED':20} {self.stats.nodes_cleaned:10,} nodes")
        
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
        
        # Query each relationship type directly - only actual relationship fields
        relationship_types = [
            "LOCATED_IN", "IN_ZIP_CODE", "IN_CITY", "IN_COUNTY", "IN_STATE", 
            "NEAR", "HAS_FEATURE", "TYPE_OF", "IN_PRICE_RANGE", "SIMILAR_TO", "DESCRIBES"
        ]
        
        for rel_type in relationship_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            count = result[0]["count"] if result else 0
            setattr(stats, rel_type, count)
        
        return stats