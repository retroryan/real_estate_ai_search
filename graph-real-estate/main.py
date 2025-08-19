"""Main entry point for the Real Estate Graph Builder application"""
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.controllers import RealEstateGraphBuilder
from src.database import clear_database, print_stats, get_neo4j_driver, close_neo4j_driver

def main():
    """Main function to run the graph builder"""
    parser = argparse.ArgumentParser(
        description="Build real estate graph database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This application demonstrates building
a Neo4j graph database from real estate data.

Folder Structure:
  src/models/     - Pydantic data models
  src/data/       - Data loading and processing
  src/database/   - Neo4j connection and utilities
  src/controllers - Business logic and orchestration
  config/         - Application configuration

Examples:
  python main.py all            # Run complete setup
  python main.py setup          # Setup environment & validate data
  python main.py schema         # Create core graph schema
  python main.py relationships  # Create graph relationships
  python main.py queries        # Run sample queries
  python main.py interactive    # Interactive query mode
  python main.py stats          # Show database statistics
  python main.py clear          # Clear all data
        """
    )
    parser.add_argument(
        "action",
        choices=["all", "setup", "schema", "relationships", "queries", "interactive", "stats", "clear"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    # For stats and clear operations, we don't need the full builder
    if args.action == "stats":
        driver = get_neo4j_driver()
        print_stats(driver)
        close_neo4j_driver(driver)
        return
    elif args.action == "clear":
        driver = get_neo4j_driver()
        clear_database(driver)
        print("✓ Database cleared")
        close_neo4j_driver(driver)
        return
    
    # For other operations, use the graph builder
    builder = RealEstateGraphBuilder()
    
    try:
        if args.action == "setup":
            builder.setup_environment()
        elif args.action == "schema":
            if builder.setup_environment():
                builder.create_schema()
        elif args.action == "relationships":
            if builder.setup_environment():
                if builder.create_schema():
                    builder.create_relationships()
        elif args.action == "all":
            print("\n" + "="*60)
            print("REAL ESTATE GRAPH BUILDER")
            print("Modular Architecture with Pydantic Validation")
            print("="*60)
            
            if builder.setup_environment():
                if builder.create_schema():
                    if builder.create_relationships():
                        builder.run_sample_queries()
                        
            print("\n" + "="*60)
            print("GRAPH BUILD COMPLETE")
            print("="*60)
            print("\nFolder Structure:")
            print("  src/models/     - Data validation models")
            print("  src/data/       - Data loading logic")
            print("  src/database/   - Database operations")
            print("  src/controllers - Business logic")
            print("  config/         - Configuration")
            
        elif args.action == "queries":
            builder.run_sample_queries()
        
        elif args.action == "interactive":
            from src.queries import QueryRunner
            runner = QueryRunner(builder.driver)
            runner.run_interactive()
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        builder.close()

if __name__ == "__main__":
    main()