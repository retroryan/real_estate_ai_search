"""Main entry point with constructor injection"""

import argparse
import sys
import logging
from pathlib import Path

from src.core import AppDependencies
from src.orchestrator import GraphOrchestrator


class GraphApplication:
    """Main application with injected dependencies"""
    
    def __init__(self, dependencies: AppDependencies):
        """
        Initialize application with all dependencies
        
        Args:
            dependencies: Container with all application dependencies
        """
        self.deps = dependencies
        self.orchestrator = GraphOrchestrator(dependencies.loaders)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute_command(self, command: str) -> bool:
        """
        Execute a command
        
        Args:
            command: Command to execute
            
        Returns:
            True if successful, False otherwise
        """
        # Map commands to methods
        commands = {
            'load': self.orchestrator.run_all_phases,
            'all': self.orchestrator.run_all_phases,
            'validate': lambda: self.orchestrator.run_phase_1_validation().is_valid,
            'geographic': lambda: self.orchestrator.run_phase_2_geographic().success,
            'wikipedia': lambda: self.orchestrator.run_phase_3_wikipedia().success,
            'neighborhoods': lambda: self.orchestrator.run_phase_4_neighborhoods().success,
            'properties': lambda: self.orchestrator.run_phase_5_properties().success,
            'similarity': lambda: self.orchestrator.run_phase_6_similarity().success,
            'verify': self.verify_graph,
            'stats': self.show_stats,
            'clear': self.clear_database,
        }
        
        if command in commands:
            try:
                return commands[command]()
            except Exception as e:
                self.logger.error(f"Command '{command}' failed: {e}")
                return False
        else:
            self.logger.error(f"Unknown command: {command}")
            return False
    
    def verify_graph(self) -> bool:
        """Verify the complete graph state"""
        self.logger.info("\n" + "="*60)
        self.logger.info("GRAPH VERIFICATION SUMMARY")
        self.logger.info("="*60)
        
        stats = self.deps.database.query_executor.get_stats()
        
        # Node counts
        self.logger.info("\n📊 NODE COUNTS:")
        node_types = [
            "State", "County", "City", "WikipediaArticle", 
            "Neighborhood", "Property", "Feature", "PropertyType", "PriceRange"
        ]
        for node_type in node_types:
            count = stats.get(f"nodes_{node_type}", 0)
            self.logger.info(f"  {node_type}: {count}")
        
        # Relationship counts
        self.logger.info("\n🔗 RELATIONSHIP COUNTS:")
        rel_types = [
            "IN_STATE", "IN_COUNTY", "IN_CITY", "IN_NEIGHBORHOOD",
            "HAS_FEATURE", "OF_TYPE", "IN_PRICE_RANGE", "SIMILAR_TO",
            "NEAR", "NEAR_BY", "DESCRIBES", "RELEVANT_TO"
        ]
        for rel_type in rel_types:
            count = stats.get(f"relationships_{rel_type}", 0)
            self.logger.info(f"  {rel_type}: {count}")
        
        # Total counts
        self.logger.info("\n📈 TOTALS:")
        self.logger.info(f"  Total nodes: {stats.get('total_nodes', 0)}")
        self.logger.info(f"  Total relationships: {stats.get('total_relationships', 0)}")
        
        return True
    
    def show_stats(self) -> bool:
        """Show database statistics"""
        stats = self.deps.database.query_executor.get_stats()
        
        print("\n=== Database Statistics ===")
        for key, value in sorted(stats.items()):
            print(f"{key}: {value}")
        print("===========================\n")
        
        return True
    
    def clear_database(self) -> bool:
        """Clear all data from database"""
        response = input("Are you sure you want to clear the entire database? (yes/no): ")
        if response.lower() == 'yes':
            self.deps.database.query_executor.clear_database()
            self.logger.info("Database cleared")
            return True
        else:
            self.logger.info("Clear operation cancelled")
            return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
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
  python main_v2.py load           # Run complete graph load (all phases)
  python main_v2.py validate       # Run data validation only (Phase 1)
  python main_v2.py geographic     # Load geographic foundation (Phase 2)
  python main_v2.py wikipedia      # Load Wikipedia knowledge (Phase 3)
  python main_v2.py neighborhoods  # Load neighborhoods (Phase 4)
  python main_v2.py properties     # Load properties (Phase 5)
  python main_v2.py similarity     # Create similarity relationships (Phase 6)
  python main_v2.py verify         # Verify graph integrity
  python main_v2.py stats          # Show database statistics
  python main_v2.py clear          # Clear all data
        """
    )
    
    parser.add_argument(
        "action",
        choices=[
            "load", "all", "validate", "geographic", "wikipedia", 
            "neighborhoods", "properties", "similarity",
            "verify", "stats", "clear"
        ],
        help="Action to perform"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point with dependency injection"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger("main")
    
    try:
        # Create all dependencies at startup (composition root)
        logger.info(f"Loading configuration from {args.config}")
        dependencies = AppDependencies.create_from_config(args.config)
        
        # Create application with injected dependencies
        app = GraphApplication(dependencies)
        
        # Execute command
        logger.info(f"Executing command: {args.action}")
        success = app.execute_command(args.action)
        
        if success:
            logger.info(f"✅ Command '{args.action}' completed successfully")
            sys.exit(0)
        else:
            logger.error(f"❌ Command '{args.action}' failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Cleanup is handled by dependency container
        if 'dependencies' in locals():
            dependencies.cleanup()
            logger.info("Resources cleaned up")


if __name__ == "__main__":
    main()