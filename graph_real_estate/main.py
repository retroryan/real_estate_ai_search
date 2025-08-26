"""Simplified main entry point for database initialization only"""

import argparse
import sys
import logging
from graph_real_estate.utils.graph_builder import GraphDatabaseInitializer
from graph_real_estate.utils.demo_runner import DemoRunner
from graph_real_estate.utils.models import DemoConfig


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Initialize Neo4j database for real estate knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This application initializes a Neo4j database with schema, constraints, and indexes
for the real estate knowledge graph. Data loading will be handled separately.

Commands:
  init                Initialize database with schema and indexes
  clear               Clear all data from database
  stats               Show database statistics
  test                Test database connection
  build-relationships Build all relationships in Neo4j
  demo                Run demonstration queries

Examples:
  python main.py init                    # Initialize database schema
  python main.py init --clear            # Clear database and initialize
  python main.py clear                   # Clear database only
  python main.py stats                   # Show current database statistics
  python main.py test                    # Test database connection
  python main.py build-relationships     # Build all relationships
  python main.py demo --demo 1           # Run demo 1 (Basic Graph Queries)
  python main.py demo --demo 2 # Run demo 2 (Hybrid Search Simple)
  python main.py demo --demo 3 # Run demo 3 (Hybrid Search Advanced)
  python main.py demo --demo 4 # Run demo 4 (Graph Analysis)
  python main.py demo --demo 5 # Run demo 5 (Market Intelligence)
  python main.py demo --demo 6 # Run demo 6 (Wikipedia Enhanced)
  python main.py demo --demo 7 # Run demo 7 (Pure Vector Search)
        """
    )
    
    parser.add_argument(
        "action",
        choices=["init", "clear", "stats", "test", "build-relationships", "demo"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before initialization (use with 'init')"
    )
    
    parser.add_argument(
        "--demo",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        help="Demo number to run (1-7, use with 'demo' action)"
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
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for database initialization"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger("main")
    
    # Create database initializer
    initializer = GraphDatabaseInitializer()
    
    try:
        if args.action == "test":
            # Test database connection
            logger.info("Testing database connection...")
            success = initializer.test_connection()
            if success:
                logger.info("✅ Database connection successful")
                sys.exit(0)
            else:
                logger.error("❌ Database connection failed")
                sys.exit(1)
        
        elif args.action == "init":
            # Initialize database
            logger.info("Initializing database...")
            success = initializer.initialize_database(clear=args.clear)
            if success:
                initializer.print_stats()
                logger.info("✅ Database initialization completed successfully")
                sys.exit(0)
            else:
                logger.error("❌ Database initialization failed")
                sys.exit(1)
        
        elif args.action == "clear":
            # Clear database
            response = input("Are you sure you want to clear the entire database? (yes/no): ")
            if response.lower() == 'yes':
                initializer.clear_database()
                logger.info("✅ Database cleared successfully")
                sys.exit(0)
            else:
                logger.info("Clear operation cancelled")
                sys.exit(0)
        
        elif args.action == "stats":
            # Show database statistics
            initializer.print_stats()
            sys.exit(0)
        
        elif args.action == "build-relationships":
            # Build relationships
            logger.info("Building relationships in Neo4j...")
            from .relationships import RelationshipOrchestrator, RelationshipConfig
            
            # Create config (uses defaults)
            config = RelationshipConfig()
            
            # Create orchestrator and build relationships
            orchestrator = RelationshipOrchestrator(initializer.driver, config)
            stats = orchestrator.build_all_relationships()
            
            # Verify relationships
            logger.info("\nVerifying relationships...")
            actual_stats = orchestrator.verify_relationships()
            
            logger.info("\nRelationship verification:")
            for rel_type, count in actual_stats.dict().items():
                logger.info(f"  {rel_type}: {count:,} relationships")
            logger.info(f"  Total: {actual_stats.total:,} relationships")
            
            logger.info("✅ Relationship building completed successfully")
            sys.exit(0)
        
        elif args.action == "demo":
            # Run demo
            if not args.demo:
                logger.error("Demo number required. Use --demo N where N is 1-7")
                parser.print_help()
                sys.exit(1)
            
            logger.info(f"Running demo {args.demo}...")
            
            # Create demo config with Pydantic validation
            demo_config = DemoConfig(
                demo_number=args.demo,
                verbose=args.verbose
            )
            
            # Run the demo
            from .utils.demo_runner import DemoRunner
            demo_runner = DemoRunner(initializer.driver, demo_config)
            demo_runner.run_demo()
            
            logger.info(f"✅ Demo {args.demo} completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Cleanup
        initializer.close()


if __name__ == "__main__":
    main()