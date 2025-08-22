"""Main entry point for the Real Estate Graph Builder application"""
import argparse
import sys
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.database import clear_database, print_stats, get_neo4j_driver, close_neo4j_driver
from src.loaders.geographic_loader import GeographicFoundationLoader
from src.loaders.wikipedia_loader import WikipediaKnowledgeLoader
from src.loaders.neighborhood_loader import NeighborhoodLoader
from src.loaders.property_loader import PropertyLoader
from src.loaders.similarity_loader import SimilarityLoader
from src.validators.data_validator import DataValidator


class GraphOrchestrator:
    """Orchestrate the loading of all graph data phases"""
    
    def __init__(self):
        """Initialize the orchestrator"""
        self.logger = self._setup_logger()
        self.validator: Optional[DataValidator] = None
        self.geographic_loader: Optional[GeographicFoundationLoader] = None
        self.wikipedia_loader: Optional[WikipediaKnowledgeLoader] = None
        self.neighborhood_loader: Optional[NeighborhoodLoader] = None
        self.property_loader: Optional[PropertyLoader] = None
        self.similarity_loader: Optional[SimilarityLoader] = None
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger("GraphOrchestrator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run_phase_1_validation(self) -> bool:
        """Phase 1: Environment Setup and Data Validation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 1: ENVIRONMENT SETUP & DATA VALIDATION")
        self.logger.info("="*60)
        
        try:
            self.validator = DataValidator()
            result = self.validator.validate_all()
            
            if result.is_valid:
                self.logger.info("✅ Phase 1 Complete: All validations passed")
                return True
            else:
                self.logger.error(f"❌ Phase 1 Failed: {len(result.errors)} errors found")
                for error in result.errors:
                    self.logger.error(f"  - {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Phase 1 failed with exception: {e}")
            return False
    
    def run_phase_2_geographic(self) -> bool:
        """Phase 2: Geographic Foundation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 2: GEOGRAPHIC FOUNDATION")
        self.logger.info("="*60)
        
        try:
            with GeographicFoundationLoader() as loader:
                result = loader.load()
                
                if result:
                    self.logger.info(f"✅ Phase 2 Complete: {result.total_states} states, "
                                   f"{result.total_counties} counties, {result.total_cities} cities")
                    self.geographic_loader = loader
                    return True
                else:
                    self.logger.error("❌ Phase 2 Failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Phase 2 failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_phase_3_wikipedia(self) -> bool:
        """Phase 3: Wikipedia Knowledge Layer"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 3: WIKIPEDIA KNOWLEDGE LAYER")
        self.logger.info("="*60)
        
        try:
            # Get geographic index if available
            geographic_index = {}
            if self.geographic_loader:
                geographic_index = self.geographic_loader.get_geographic_index()
            
            with WikipediaKnowledgeLoader() as loader:
                result = loader.load()
                
                if result and result.success:
                    self.logger.info(f"✅ Phase 3 Complete: {result.articles_loaded} articles, "
                                   f"{result.topics_extracted} topics")
                    self.wikipedia_loader = loader
                    return True
                else:
                    self.logger.error("❌ Phase 3 Failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Phase 3 failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_phase_4_neighborhoods(self) -> bool:
        """Phase 4: Neighborhood Loading and Correlation"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 4: NEIGHBORHOOD LOADING AND CORRELATION")
        self.logger.info("="*60)
        
        try:
            with NeighborhoodLoader() as loader:
                result = loader.load()
                
                if result and result.success:
                    self.logger.info(f"✅ Phase 4 Complete: {result.neighborhoods_loaded} neighborhoods, "
                                   f"{result.wikipedia_correlations} correlations, "
                                   f"avg knowledge score: {result.avg_knowledge_score:.2f}")
                    self.neighborhood_loader = loader
                    return True
                else:
                    self.logger.error("❌ Phase 4 Failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Phase 4 failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_phase_5_properties(self) -> bool:
        """Phase 5: Property Loading with Multi-Path Relationships"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 5: PROPERTY LOADING WITH MULTI-PATH RELATIONSHIPS")
        self.logger.info("="*60)
        
        try:
            with PropertyLoader() as loader:
                result = loader.load()
                
                if result and result.success:
                    self.logger.info(f"✅ Phase 5 Complete: {result.properties_loaded} properties, "
                                   f"{result.unique_features} features, "
                                   f"{result.neighborhood_relationships} neighborhood connections")
                    self.property_loader = loader
                    return True
                else:
                    self.logger.error("❌ Phase 5 Failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Phase 5 failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    def run_phase_6_similarity(self) -> bool:
        """Phase 6: Relationship Enhancement and Similarity Calculations"""
        self.logger.info("\n" + "="*60)
        self.logger.info("PHASE 6: RELATIONSHIP ENHANCEMENT AND SIMILARITY CALCULATIONS")
        self.logger.info("="*60)
        
        try:
            with SimilarityLoader() as loader:
                result = loader.load()
                
                if result and result.success:
                    self.logger.info(f"✅ Phase 6 Complete: {result.property_similarities_created} similarities, "
                                   f"{result.neighborhood_connections_created} connections, "
                                   f"{result.topic_clusters_created} clusters")
                    self.similarity_loader = loader
                    return True
                else:
                    self.logger.error("❌ Phase 6 Failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Phase 6 failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
        
        for phase_name, phase_func in phases:
            if not phase_func():
                self.logger.error(f"Stopping due to {phase_name} failure")
                return False
        
        # Calculate total time
        duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("✅ ALL PHASES COMPLETE")
        self.logger.info(f"Total execution time: {duration:.1f} seconds")
        self.logger.info("="*60)
        
        return True
    
    def verify_graph(self) -> None:
        """Verify the complete graph state"""
        driver = get_neo4j_driver()
        
        print("\n" + "="*60)
        print("GRAPH VERIFICATION SUMMARY")
        print("="*60)
        
        # Node counts
        print("\n📊 NODE COUNTS:")
        node_queries = [
            ("States", "MATCH (s:State) RETURN count(s) as count"),
            ("Counties", "MATCH (c:County) RETURN count(c) as count"),
            ("Cities", "MATCH (c:City) RETURN count(c) as count"),
            ("Wikipedia Articles", "MATCH (w:WikipediaArticle) RETURN count(w) as count"),
            ("Neighborhoods", "MATCH (n:Neighborhood) RETURN count(n) as count"),
            ("Properties", "MATCH (p:Property) RETURN count(p) as count"),
            ("Features", "MATCH (f:Feature) RETURN count(f) as count"),
            ("Property Types", "MATCH (pt:PropertyType) RETURN count(pt) as count"),
            ("Price Ranges", "MATCH (pr:PriceRange) RETURN count(pr) as count"),
        ]
        
        for name, query in node_queries:
            from src.database import run_query
            result = run_query(driver, query)
            count = result[0]['count'] if result else 0
            print(f"  {name}: {count}")
        
        # Relationship counts
        print("\n🔗 RELATIONSHIP COUNTS:")
        rel_queries = [
            ("County→State", "MATCH ()-[r:IN_STATE]->(:State) RETURN count(r) as count"),
            ("City→County", "MATCH ()-[r:IN_COUNTY]->(:County) RETURN count(r) as count"),
            ("Neighborhood→City", "MATCH (:Neighborhood)-[r:IN_CITY]->(:City) RETURN count(r) as count"),
            ("Property→Neighborhood", "MATCH (:Property)-[r:IN_NEIGHBORHOOD]->(:Neighborhood) RETURN count(r) as count"),
            ("Property→City", "MATCH (:Property)-[r:IN_CITY]->(:City) RETURN count(r) as count"),
            ("Property→Feature", "MATCH (:Property)-[r:HAS_FEATURE]->(:Feature) RETURN count(r) as count"),
            ("Property→Type", "MATCH (:Property)-[r:OF_TYPE]->(:PropertyType) RETURN count(r) as count"),
            ("Property→PriceRange", "MATCH (:Property)-[r:IN_PRICE_RANGE]->(:PriceRange) RETURN count(r) as count"),
            ("Wikipedia→Neighborhood", "MATCH (:WikipediaArticle)-[r:DESCRIBES]->(:Neighborhood) RETURN count(r) as count"),
            ("Wikipedia→State", "MATCH (:WikipediaArticle)-[r:IN_STATE]->() RETURN count(r) as count"),
            ("Property Similarities", "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count"),
            ("Neighborhood Connections", "MATCH ()-[r:NEAR]->() RETURN count(r) as count"),
            ("Geographic Proximities", "MATCH ()-[r:NEAR_BY]->() RETURN count(r) as count"),
        ]
        
        for name, query in rel_queries:
            from src.database import run_query
            result = run_query(driver, query)
            count = result[0]['count'] if result else 0
            print(f"  {name}: {count}")
        
        # Hierarchical label counts (from FIX_v7 improvements)
        print("\n🏷️ HIERARCHICAL LABELS:")
        hierarchy_queries = [
            ("Location nodes", "MATCH (n:Location) RETURN count(n) as count"),
            ("Asset nodes", "MATCH (n:Asset) RETURN count(n) as count"),
        ]
        
        for name, query in hierarchy_queries:
            result = run_query(driver, query)
            count = result[0]['count'] if result else 0
            print(f"  {name}: {count}")
        
        close_neo4j_driver(driver)


def main():
    """Main function to run the graph builder"""
    parser = argparse.ArgumentParser(
        description="Build real estate knowledge graph with Wikipedia enhancement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This application builds a Neo4j knowledge graph from real estate data
enriched with Wikipedia content for semantic search and analysis.

PHASES:
  Phase 1: Environment Setup & Data Validation
  Phase 2: Geographic Foundation (States, Counties, Cities)
  Phase 3: Wikipedia Knowledge Layer
  Phase 4: Neighborhood Loading and Correlation
  Phase 5: Property Loading with Multi-Path Relationships
  Phase 6: Relationship Enhancement and Similarity Calculations

Examples:
  python main.py load           # Run complete graph load (all phases)
  python main.py validate       # Run data validation only (Phase 1)
  python main.py geographic     # Load geographic foundation (Phase 2)
  python main.py wikipedia      # Load Wikipedia knowledge (Phase 3)
  python main.py neighborhoods  # Load neighborhoods (Phase 4)
  python main.py properties     # Load properties (Phase 5)
  python main.py similarity     # Create similarity relationships (Phase 6)
  python main.py verify         # Verify graph integrity
  python main.py stats          # Show database statistics
  python main.py clear          # Clear all data

Legacy Commands (for backward compatibility):
  python main.py all            # Same as 'load'
        """
    )
    parser.add_argument(
        "action",
        choices=[
            "load", "all", "validate", "geographic", "wikipedia", "neighborhoods", "properties", "similarity",
            "verify", "stats", "clear",
            # Legacy commands for backward compatibility
            "setup", "schema", "relationships", "queries", "interactive"
        ],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    # Handle database operations
    if args.action == "stats":
        driver = get_neo4j_driver()
        print_stats(driver)
        close_neo4j_driver(driver)
        return
    elif args.action == "clear":
        driver = get_neo4j_driver()
        clear_database(driver)
        print("Database cleared")
        close_neo4j_driver(driver)
        return
    
    # Initialize orchestrator for loading operations
    orchestrator = GraphOrchestrator()
    
    # Map actions to orchestrator methods
    if args.action in ["load", "all"]:
        orchestrator.run_all_phases()
        orchestrator.verify_graph()
    elif args.action == "validate":
        orchestrator.run_phase_1_validation()
    elif args.action == "geographic":
        orchestrator.run_phase_2_geographic()
    elif args.action == "wikipedia":
        orchestrator.run_phase_3_wikipedia()
    elif args.action == "neighborhoods":
        orchestrator.run_phase_4_neighborhoods()
    elif args.action == "properties":
        orchestrator.run_phase_5_properties()
    elif args.action == "similarity":
        orchestrator.run_phase_6_similarity()
    elif args.action == "verify":
        orchestrator.verify_graph()
    
    # Handle legacy commands for backward compatibility
    elif args.action in ["setup", "schema", "relationships", "queries", "interactive"]:
        print(f"\n⚠️  Legacy command '{args.action}' detected.")
        print("This application has been refactored to use a phased loading approach.")
        print("\nPlease use one of these commands instead:")
        print("  python main.py load         # Load complete graph (recommended)")
        print("  python main.py validate     # Validate data sources")
        print("  python main.py verify       # Verify graph after loading")
        print("\nFor the old functionality, the previous implementation has been archived.")
        
        if args.action == "interactive":
            print("\n💡 For interactive queries, first load the graph with 'python main.py load'")
            print("   Then use the query_runner.py script for interactive querying.")


if __name__ == "__main__":
    main()