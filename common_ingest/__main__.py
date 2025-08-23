"""
Main entry point for the common_ingest module.

Runs the data ingestion pipeline and displays summary statistics.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from decimal import Decimal

from .loaders import PropertyLoader, NeighborhoodLoader, WikipediaLoader
from .models.property import EnrichedProperty, EnrichedNeighborhood
from .models.wikipedia import EnrichedWikipediaArticle, WikipediaSummary
from .utils.config import get_settings
from .utils.logger import setup_logger

logger = setup_logger(__name__)


def format_price(price: Decimal) -> str:
    """Format price for display."""
    return f"${price:,.0f}"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def print_property_summary(properties: List[EnrichedProperty], sample_size: int = 10):
    """Print summary statistics for properties."""
    if not properties:
        logger.warning("No properties loaded")
        return
    
    logger.info("=" * 80)
    logger.info("PROPERTY DATA SUMMARY")
    logger.info("=" * 80)
    
    # Statistics
    total = len(properties)
    cities = {p.address.city for p in properties}
    states = {p.address.state for p in properties}
    property_types = {}
    for p in properties:
        # Handle both enum and string property types
        prop_type = p.property_type.value if hasattr(p.property_type, 'value') else str(p.property_type)
        property_types[prop_type] = property_types.get(prop_type, 0) + 1
    
    prices = [p.price for p in properties]
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    logger.info(f"Total Properties: {total}")
    logger.info(f"Cities: {', '.join(sorted(cities))}")
    logger.info(f"States: {', '.join(sorted(states))}")
    logger.info(f"Property Types: {property_types}")
    logger.info(f"Price Range: {format_price(min_price)} - {format_price(max_price)}")
    logger.info(f"Average Price: {format_price(avg_price)}")
    
    # Sample data
    logger.info(f"\nSample Properties (first {min(sample_size, total)} of {total}):")
    logger.info("-" * 80)
    logger.info(f"{'ID':<15} {'Type':<12} {'Price':<12} {'Beds':<5} {'City':<15} {'State':<10}")
    logger.info("-" * 80)
    
    for prop in properties[:sample_size]:
        prop_type = prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type)
        logger.info(
            f"{prop.listing_id:<15} "
            f"{prop_type:<12} "
            f"{format_price(prop.price):<12} "
            f"{prop.bedrooms:<5} "
            f"{prop.address.city:<15} "
            f"{prop.address.state:<10}"
        )


def print_neighborhood_summary(neighborhoods: List[EnrichedNeighborhood], sample_size: int = 10):
    """Print summary statistics for neighborhoods."""
    if not neighborhoods:
        logger.warning("No neighborhoods loaded")
        return
    
    logger.info("=" * 80)
    logger.info("NEIGHBORHOOD DATA SUMMARY")
    logger.info("=" * 80)
    
    # Statistics
    total = len(neighborhoods)
    cities = {n.city for n in neighborhoods}
    states = {n.state for n in neighborhoods}
    total_pois = sum(n.poi_count for n in neighborhoods)
    avg_pois = total_pois / total if total > 0 else 0
    
    logger.info(f"Total Neighborhoods: {total}")
    logger.info(f"Cities: {', '.join(sorted(cities))}")
    logger.info(f"States: {', '.join(sorted(states))}")
    logger.info(f"Total POIs: {total_pois}")
    logger.info(f"Average POIs per Neighborhood: {avg_pois:.1f}")
    
    # Sample data
    logger.info(f"\nSample Neighborhoods (first {min(sample_size, total)} of {total}):")
    logger.info("-" * 80)
    logger.info(f"{'ID':<25} {'Name':<25} {'City':<15} {'POIs':<6}")
    logger.info("-" * 80)
    
    for neighborhood in neighborhoods[:sample_size]:
        logger.info(
            f"{neighborhood.neighborhood_id:<25} "
            f"{truncate_text(neighborhood.name, 25):<25} "
            f"{neighborhood.city:<15} "
            f"{neighborhood.poi_count:<6}"
        )


def print_wikipedia_summary(
    articles: List[EnrichedWikipediaArticle], 
    summaries: List[WikipediaSummary],
    sample_size: int = 10
):
    """Print summary statistics for Wikipedia data."""
    logger.info("=" * 80)
    logger.info("WIKIPEDIA DATA SUMMARY")
    logger.info("=" * 80)
    
    # Article statistics
    if articles:
        total_articles = len(articles)
        avg_relevance = sum(a.relevance_score for a in articles) / total_articles
        
        logger.info(f"Total Articles: {total_articles}")
        logger.info(f"Average Relevance Score: {avg_relevance:.3f}")
        
        logger.info(f"\nSample Articles (first {min(sample_size, total_articles)} of {total_articles}):")
        logger.info("-" * 80)
        logger.info(f"{'Page ID':<10} {'Title':<40} {'Relevance':<10}")
        logger.info("-" * 80)
        
        for article in articles[:sample_size]:
            logger.info(
                f"{article.page_id:<10} "
                f"{truncate_text(article.title, 40):<40} "
                f"{article.relevance_score:<10.3f}"
            )
    else:
        logger.warning("No Wikipedia articles loaded")
    
    # Summary statistics
    if summaries:
        total_summaries = len(summaries)
        avg_confidence = sum(s.overall_confidence for s in summaries) / total_summaries
        cities = {s.best_city for s in summaries if s.best_city}
        states = {s.best_state for s in summaries if s.best_state}
        
        logger.info(f"\nTotal Summaries: {total_summaries}")
        logger.info(f"Average Confidence: {avg_confidence:.3f}")
        logger.info(f"Cities Referenced: {len(cities)}")
        logger.info(f"States Referenced: {len(states)}")
        
        logger.info(f"\nSample Summaries (first {min(sample_size, total_summaries)} of {total_summaries}):")
        logger.info("-" * 80)
        logger.info(f"{'Page ID':<10} {'Title':<30} {'City':<15} {'Confidence':<10}")
        logger.info("-" * 80)
        
        for summary in summaries[:sample_size]:
            city_display = summary.best_city or "N/A"
            logger.info(
                f"{summary.page_id:<10} "
                f"{truncate_text(summary.article_title, 30):<30} "
                f"{city_display:<15} "
                f"{summary.overall_confidence:<10.3f}"
            )
    else:
        logger.warning("No Wikipedia summaries loaded")


def main():
    """Run the common ingestion pipeline and display summary statistics."""
    logger.info("=" * 80)
    logger.info("COMMON INGESTION MODULE - DATA SUMMARY")
    logger.info("=" * 80)
    
    settings = get_settings()
    
    # Load property data
    logger.info("\nLoading property data...")
    try:
        property_loader = PropertyLoader(settings.data_paths.get_property_data_path())
        properties = property_loader.load_all()
        logger.info(f"✅ Loaded {len(properties)} properties")
    except Exception as e:
        logger.error(f"❌ Failed to load properties: {e}")
        properties = []
    
    # Load neighborhood data
    logger.info("\nLoading neighborhood data...")
    try:
        neighborhood_loader = NeighborhoodLoader(settings.data_paths.get_property_data_path())
        neighborhoods = neighborhood_loader.load_all()
        logger.info(f"✅ Loaded {len(neighborhoods)} neighborhoods")
    except Exception as e:
        logger.error(f"❌ Failed to load neighborhoods: {e}")
        neighborhoods = []
    
    # Load Wikipedia data
    logger.info("\nLoading Wikipedia data...")
    wikipedia_articles = []
    wikipedia_summaries = []
    
    wikipedia_db_path = settings.data_paths.get_wikipedia_db_path()
    if wikipedia_db_path.exists():
        try:
            wikipedia_loader = WikipediaLoader(wikipedia_db_path)
            wikipedia_articles = wikipedia_loader.load_all()
            wikipedia_summaries = wikipedia_loader.load_summaries()
            logger.info(f"✅ Loaded {len(wikipedia_articles)} articles and {len(wikipedia_summaries)} summaries")
        except Exception as e:
            logger.error(f"❌ Failed to load Wikipedia data: {e}")
    else:
        logger.warning(f"Wikipedia database not found at {wikipedia_db_path}")
    
    # Display summaries
    print("\n")  # Add space before summaries
    print_property_summary(properties)
    print("\n")
    print_neighborhood_summary(neighborhoods)
    print("\n")
    print_wikipedia_summary(wikipedia_articles, wikipedia_summaries)
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total Records Loaded:")
    logger.info(f"  - Properties: {len(properties)}")
    logger.info(f"  - Neighborhoods: {len(neighborhoods)}")
    logger.info(f"  - Wikipedia Articles: {len(wikipedia_articles)}")
    logger.info(f"  - Wikipedia Summaries: {len(wikipedia_summaries)}")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())