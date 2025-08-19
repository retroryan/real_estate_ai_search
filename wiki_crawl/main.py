#!/usr/bin/env python3
"""
Wikipedia Data Acquisition Tool

A unified interface for crawling and attributing Wikipedia content.
"""

import sys
from pathlib import Path
import argparse

# Import crawling functionality
from .wikipedia_location_crawler import crawl_location, analyze_crawled_data
from .models import CrawlerConfig
from .crawler import WikipediaLocationCrawler


def crawl_location_command(args):
    """Execute deep crawl for a location."""
    print(f"\n🕷️  Starting deep crawl for {args.city}, {args.state}")
    print("=" * 60)
    
    config = CrawlerConfig(
        city=args.city,
        state=args.state,
        max_depth=args.depth,
        max_articles_per_level=args.max_articles,
        delay=0.1,
        download_html=args.download_html,
        data_dir=Path(args.data_dir)
    )
    
    crawler = WikipediaLocationCrawler(config)
    articles = crawler.crawl_bfs()
    
    if articles:
        crawler.save_all()
        crawler.metadata.statistics.print_summary(args.city, args.state)
        print(f"\n✅ Crawl complete! Found {len(articles)} relevant articles")
    else:
        print("❌ No articles found")


def generate_attribution_command(args):
    """Generate attribution files from crawl data."""
    print("\n📝 Generating Wikipedia attribution for CC BY-SA 3.0 compliance")
    print("=" * 60)
    
    data_dir = Path(args.data_dir)
    
    # Import and use the database-based attribution generator
    try:
        from .generate_attribution import generate_attribution_from_database
        attribution_data = generate_attribution_from_database(data_dir)
        
        if attribution_data:
            print("\n✅ Attribution files generated successfully!")
            print(f"   Total articles: {attribution_data['total_articles']}")
            print("\nFiles created:")
            print("  - WIKIPEDIA_ATTRIBUTION.json (machine-readable)")
            print("  - WIKIPEDIA_ATTRIBUTION.md (markdown documentation)")  
            print("  - WIKIPEDIA_ATTRIBUTION.html (web viewable)")
        else:
            print("❌ No articles found in database")
    except Exception as e:
        print(f"❌ Error generating attribution: {e}")


def analyze_command(args):
    """Analyze a crawled SQLite database."""
    print(f"\n📊 Analyzing Wikipedia database: {args.database}")
    print("=" * 60)
    
    db_path = Path(args.database)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        analyze_crawled_data(db_path)
        print("\n✅ Analysis complete!")
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")


def main():
    """Main entry point for the Wikipedia tool."""
    parser = argparse.ArgumentParser(
        description="Wikipedia Data Acquisition Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deep crawl for a location
  python main.py crawl "Park City" "Utah" --depth 2 --max-articles 20
  
  # Generate attribution files
  python main.py attribution
  
  # Analyze the database
  python main.py analyze ../data/wikipedia/wikipedia.db
        """
    )
    
    parser.add_argument('--data-dir', default='../data', help='Data directory (default: ../data)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Deep crawl for a location')
    crawl_parser.add_argument('city', help='City name (e.g., "Park City")')
    crawl_parser.add_argument('state', help='State name (e.g., "Utah")')
    crawl_parser.add_argument('--depth', type=int, default=2, help='Maximum crawl depth (default: 2)')
    crawl_parser.add_argument('--max-articles', type=int, default=20, help='Max articles per level (default: 20)')
    crawl_parser.add_argument('--no-download', dest='download_html', action='store_false', 
                            help='Skip downloading HTML files')
    
    # Attribution command
    attr_parser = subparsers.add_parser('attribution', help='Generate attribution files')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze Wikipedia database')
    analyze_parser.add_argument('database', help='Path to SQLite database file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute the appropriate command
    command_map = {
        'crawl': crawl_location_command,
        'attribution': generate_attribution_command,
        'analyze': analyze_command
    }
    
    command_func = command_map.get(args.command)
    if command_func:
        try:
            command_func(args)
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()