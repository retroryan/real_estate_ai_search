"""Simplified main entry point for database initialization only"""

import argparse
import sys
import logging
from utils.graph_builder import GraphDatabaseInitializer


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Initialize Neo4j database for real estate knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This application initializes a Neo4j database with schema, constraints, and indexes
for the real estate knowledge graph. Data loading will be handled separately.

Commands:
  init      Initialize database with schema and indexes
  clear     Clear all data from database
  stats     Show database statistics
  test      Test database connection

Examples:
  python main.py init          # Initialize database schema
  python main.py init --clear  # Clear database and initialize
  python main.py clear         # Clear database only
  python main.py stats         # Show current database statistics
  python main.py test          # Test database connection
        """
    )
    
    parser.add_argument(
        "action",
        choices=["init", "clear", "stats", "test"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before initialization (use with 'init')"
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