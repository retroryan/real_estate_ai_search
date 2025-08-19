"""
Wikipedia crawling and data acquisition module.

This module provides comprehensive tools for acquiring Wikipedia data
for real estate neighborhood analysis.
"""

# Core crawler
from .wikipedia_location_crawler import (
    WikipediaLocationCrawler,
    crawl_location,
    analyze_crawled_data
)

from .models import (
    CrawlerConfig,
    CrawlStatistics,
    WikipediaPage
)

__version__ = "1.0.0"

__all__ = [
    'WikipediaLocationCrawler',
    'CrawlerConfig',
    'CrawlStatistics',
    'WikipediaPage',
    'crawl_location',
    'analyze_crawled_data'
]