#!/usr/bin/env python
"""Standalone query runner for the real estate graph database"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_neo4j_driver, close_neo4j_driver
from queries import QueryRunner, QueryLibrary

def main():
    """Main function for query runner"""
    parser = argparse.ArgumentParser(
        description="Run queries against the real estate graph database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_runner.py --demo           # Run demonstration queries
  python query_runner.py --interactive    # Interactive query selection
  python query_runner.py --category basic # Run all basic queries
  python query_runner.py --list           # List all available queries
  python query_runner.py --export         # Export all results to file
        """
    )
    
    parser.add_argument("--demo", action="store_true", 
                       help="Run demonstration queries")
    parser.add_argument("--interactive", action="store_true",
                       help="Interactive query selection mode")
    parser.add_argument("--category", choices=["basic", "neighborhood", "feature", 
                                               "price", "similarity", "advanced"],
                       help="Run all queries in a category")
    parser.add_argument("--query", type=str,
                       help="Run a specific query by name")
    parser.add_argument("--list", action="store_true",
                       help="List all available queries")
    parser.add_argument("--export", action="store_true",
                       help="Export all query results to file")
    parser.add_argument("--output", type=str, default="query_results.txt",
                       help="Output file for export (default: query_results.txt)")
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # List queries if requested
    if args.list:
        print("\nAvailable Queries:")
        print("=" * 60)
        for query_path in QueryLibrary.list_all_queries():
            print(f"  {query_path}")
        return
    
    # Initialize driver and runner
    driver = get_neo4j_driver()
    runner = QueryRunner(driver)
    
    try:
        if args.demo:
            runner.run_demo_queries()
        
        elif args.interactive:
            runner.run_interactive()
        
        elif args.category:
            print(f"\nRunning all {args.category} queries...")
            print("=" * 60)
            
            queries = QueryLibrary.get_all_queries().get(args.category, [])
            for query in queries:
                print(f"\n{query.description}")
                print("-" * 40)
                results = runner.run_query(query)
                print(runner.format_results(results, limit=10))
                if len(results) > 10:
                    print(f"... and {len(results) - 10} more results")
        
        elif args.query:
            try:
                query = QueryLibrary.get_query_by_name(args.query)
                print(f"\n{query.description}")
                print("=" * 60)
                results = runner.run_query(query)
                print(runner.format_results(results, limit=20))
                print(f"\nTotal results: {len(results)}")
            except ValueError as e:
                print(f"Error: {e}")
                print("Use --list to see available queries")
        
        elif args.export:
            print(f"Exporting all query results to {args.output}...")
            runner.export_results(output_file=args.output)
            print(f"Export complete: {args.output}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_neo4j_driver()

if __name__ == "__main__":
    main()