"""
Wikipedia Location Crawler - Main entry point
"""

import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional
import logging

# Import the modules
from .models import (
    WikipediaPage, CrawlerConfig, CrawlStatistics, 
    CrawlMetadata, Coordinates, PageStatus
)
from .crawler import WikipediaLocationCrawler


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




def crawl_location(city: str, state: str, max_depth: int = 2) -> WikipediaLocationCrawler:
    """
    Main function to crawl Wikipedia for a location.
    
    Args:
        city: City name (e.g., "Park City")
        state: State name (e.g., "UT" or "Utah")
        max_depth: Maximum crawl depth
    """
    # Create configuration
    config = CrawlerConfig(
        city=city,
        state=state,
        max_depth=max_depth,
        max_articles_per_level=20,
        delay=0.5,  # Increased delay to avoid rate limiting
        download_html=True
    )
    
    # Create and run crawler
    crawler = WikipediaLocationCrawler(config)
    
    # Perform the crawl
    articles = crawler.crawl_bfs()
    
    # Save results
    if articles:
        crawler.save_all()
        
        # Print statistics
        crawler.metadata.statistics.print_summary(city, state)
    
    return crawler


def analyze_crawled_data(db_path: Path):
    """Analyze and query the crawled SQLite database."""
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get most relevant articles
    print("\nTop 10 Most Relevant Articles:")
    cursor.execute('''
        SELECT title, relevance_score, depth, url, html_file
        FROM articles
        ORDER BY relevance_score DESC
        LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        print(f"  {row[0]}: Score {row[1]:.1f}, Depth {row[2]}")
        print(f"    URL: {row[3]}")
        if row[4]:
            print(f"    Local file: {row[4]}")
    
    # Get articles with coordinates (mappable places)
    print("\nPlaces with coordinates:")
    cursor.execute('''
        SELECT title, latitude, longitude
        FROM articles
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        print(f"  {row[0]}: ({row[1]:.4f}, {row[2]:.4f})")
    
    conn.close()


# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Wikipedia Location Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl Wikipedia for a location')
    crawl_parser.add_argument('city', help='City name (e.g., "Park City")')
    crawl_parser.add_argument('state', help='State name (e.g., "Utah")')
    crawl_parser.add_argument('--depth', type=int, default=2, help='Maximum crawl depth (default: 2)')
    crawl_parser.add_argument('--max-articles', type=int, default=20, help='Max articles per level (default: 20)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze crawled data')
    analyze_parser.add_argument('--db', default="data/wikipedia/wikipedia.db", help='Database path')
    
    args = parser.parse_args()
    
    if args.command == 'crawl':
        # Create configuration
        config = CrawlerConfig(
            city=args.city,
            state=args.state,
            max_depth=args.depth,
            max_articles_per_level=args.max_articles,
            delay=0.5,
            download_html=True
        )
        
        # Create and run crawler
        crawler = WikipediaLocationCrawler(config)
        articles = crawler.crawl_bfs()
        
        if articles:
            crawler.save_all()
            crawler.metadata.statistics.print_summary(args.city, args.state)
            
            # Show tourist attractions if found
            if crawler.articles_data:
                print("\n" + "=" * 50)
                print("Tourist Attractions and Ski Resorts Found:")
                print("=" * 50)
                
                attractions = []
                for title, page in crawler.articles_data.items():
                    categories_lower = [c.lower() for c in page.categories]
                    text_lower = (page.extract.lower() if page.extract else "") + (page.title.lower())
                    
                    if any(keyword in cat or keyword in text_lower 
                           for keyword in ['tourist', 'attraction', 'landmark', 'ski', 'resort', 'park', 'mountain', 'canyon', 'national']
                           for cat in categories_lower):
                        attractions.append((title, page.relevance_score))
                
                # Sort by relevance score
                attractions.sort(key=lambda x: x[1], reverse=True)
                
                for title, score in attractions[:15]:
                    page = crawler.articles_data[title]
                    print(f"  • {title} (Score: {score:.1f})")
                    if page.extract:
                        print(f"    {page.extract[:150]}...")
                    if page.local_filename:
                        print(f"    Downloaded: data/wikipedia/pages/{page.local_filename}")
    
    elif args.command == 'analyze':
        db_path = Path(args.db)
        if db_path.exists():
            analyze_crawled_data(db_path)
        else:
            print(f"Database not found: {db_path}")
    
    else:
        parser.print_help()