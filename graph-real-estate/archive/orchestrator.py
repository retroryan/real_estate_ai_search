"""Graph orchestrator with constructor injection"""

import logging
from datetime import datetime
from typing import Optional

from core.dependencies import LoaderDependencies
from models.geographic import GeographicLoadResult
from models.wikipedia import WikipediaLoadResult
from models.neighborhood import NeighborhoodLoadResult
from models.property import PropertyLoadResult
from models.similarity import SimilarityLoadResult
from loaders.validator import ValidationResult


class GraphOrchestrator:
    """Orchestrate the loading of all graph data phases with injected dependencies"""
    
    def __init__(self, loaders: LoaderDependencies):
        """
        Initialize orchestrator with all dependencies injected
        
        Args:
            loaders: Container with all loader dependencies
        """
        self.loaders = loaders
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # All loaders are already initialized through dependency injection
        self.validator = loaders.validator
        self.geographic_loader = loaders.geographic_loader
        self.wikipedia_loader = loaders.wikipedia_loader
        self.neighborhood_loader = loaders.neighborhood_loader
        self.property_loader = loaders.property_loader
        self.similarity_loader = loaders.similarity_loader
    
    def run_phase_1_validation(self) -> ValidationResult:
        """Phase 1: Environment Setup and Data Validation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 1: ENVIRONMENT SETUP & DATA VALIDATION")
        self.logger.info("="*60)
        
        result = self.validator.validate_all()
        
        if result.is_valid:
            self.logger.info("✅ Phase 1 Complete: All validations passed")
        else:
            self.logger.error(f"❌ Phase 1 Failed: {len(result.errors)} errors found")
            for error in result.errors:
                self.logger.error(f"  - {error}")
        
        return result
    
    def run_phase_2_geographic(self) -> GeographicLoadResult:
        """Phase 2: Geographic Foundation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 2: GEOGRAPHIC FOUNDATION")
        self.logger.info("="*60)
        
        result = self.geographic_loader.load()
        
        if result and result.success:
            self.logger.info(f"✅ Phase 2 Complete: {result.total_states} states, "
                           f"{result.total_counties} counties, {result.total_cities} cities")
        else:
            self.logger.error("❌ Phase 2 Failed")
        
        return result
    
    def run_phase_3_wikipedia(self) -> WikipediaLoadResult:
        """Phase 3: Wikipedia Knowledge Layer"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 3: WIKIPEDIA KNOWLEDGE LAYER")
        self.logger.info("="*60)
        
        result = self.wikipedia_loader.load()
        
        if result and result.success:
            self.logger.info(f"✅ Phase 3 Complete: {result.articles_loaded} articles, "
                           f"{result.topics_extracted} topics")
        else:
            self.logger.error("❌ Phase 3 Failed")
        
        return result
    
    def run_phase_4_neighborhoods(self) -> NeighborhoodLoadResult:
        """Phase 4: Neighborhood Loading and Correlation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 4: NEIGHBORHOOD LOADING AND CORRELATION")
        self.logger.info("="*60)
        
        result = self.neighborhood_loader.load()
        
        if result and result.success:
            self.logger.info(f"✅ Phase 4 Complete: {result.neighborhoods_loaded} neighborhoods, "
                           f"{result.wikipedia_correlations} correlations, "
                           f"avg knowledge score: {result.avg_knowledge_score:.2f}")
        else:
            self.logger.error("❌ Phase 4 Failed")
        
        return result
    
    def run_phase_5_properties(self) -> PropertyLoadResult:
        """Phase 5: Property Loading with Multi-Path Relationships"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 5: PROPERTY LOADING WITH MULTI-PATH RELATIONSHIPS")
        self.logger.info("="*60)
        
        result = self.property_loader.load()
        
        if result and result.success:
            self.logger.info(f"✅ Phase 5 Complete: {result.properties_loaded} properties, "
                           f"{result.unique_features} features, "
                           f"{result.neighborhood_relationships} neighborhood connections")
        else:
            self.logger.error("❌ Phase 5 Failed")
        
        return result
    
    def run_phase_6_similarity(self) -> SimilarityLoadResult:
        """Phase 6: Relationship Enhancement and Similarity Calculations"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 6: RELATIONSHIP ENHANCEMENT AND SIMILARITY CALCULATIONS")
        self.logger.info("="*60)
        
        result = self.similarity_loader.load()
        
        if result and result.success:
            self.logger.info(f"✅ Phase 6 Complete: {result.property_similarities_created} similarities, "
                           f"{result.neighborhood_connections_created} connections, "
                           f"{result.topic_clusters_created} clusters")
        else:
            self.logger.error("❌ Phase 6 Failed")
        
        return result
    
    def run_all_phases(self) -> bool:
        """Run all phases in sequence"""
        start_time = datetime.now()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("STARTING COMPLETE GRAPH LOAD")
        self.logger.info("="*60)
        
        phases = [
            ("Phase 1: Validation", self.run_phase_1_validation),
            ("Phase 2: Geographic Foundation", self.run_phase_2_geographic),
            ("Phase 3: Wikipedia Knowledge", self.run_phase_3_wikipedia),
            ("Phase 4: Neighborhoods", self.run_phase_4_neighborhoods),
            ("Phase 5: Properties", self.run_phase_5_properties),
            ("Phase 6: Similarity Relationships", self.run_phase_6_similarity),
        ]
        
        all_success = True
        for phase_name, phase_func in phases:
            result = phase_func()
            if not result or (hasattr(result, 'success') and not result.success) or (hasattr(result, 'is_valid') and not result.is_valid):
                self.logger.error(f"Stopping due to {phase_name} failure")
                all_success = False
                break
        
        # Calculate total time
        duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info("\n" + "="*60)
        if all_success:
            self.logger.info("✅ ALL PHASES COMPLETE")
        else:
            self.logger.info("❌ GRAPH LOAD INCOMPLETE")
        self.logger.info(f"Total execution time: {duration:.1f} seconds")
        self.logger.info("="*60)
        
        return all_success