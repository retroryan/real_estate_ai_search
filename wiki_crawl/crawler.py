"""Main Wikipedia crawler implementation."""

import time
import logging
from collections import deque, defaultdict
from typing import Set, Dict, List
from datetime import datetime

from .models import (
    WikipediaPage, CrawlerConfig, CrawlStatistics, 
    CrawlMetadata
)
from .wikipedia_api import WikipediaAPI
from .relevance import RelevanceScorer
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class WikipediaLocationCrawler:
    """
    Deep crawler for Wikipedia articles related to a specific location.
    """
    
    def __init__(self, config: CrawlerConfig):
        """Initialize the crawler with configuration."""
        self.config = config
        self.visited: Set[str] = set()
        self.articles_data: Dict[str, WikipediaPage] = {}
        self.link_graph: Dict[str, Set[str]] = defaultdict(set)
        self.metadata = CrawlMetadata(config=config)
        
        # Initialize components
        pages_dir = config.data_dir / "wikipedia" / "pages"
        self.api = WikipediaAPI(pages_dir)
        self.scorer = RelevanceScorer(config.city, config.state)
        self.db = DatabaseManager(config)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def search_starting_points(self) -> List[str]:
        """Find starting Wikipedia pages for the city and state."""
        starting_points = []
        
        # Search for city, state combination
        search_terms = [
            f"{self.config.city}, {self.config.state}",
            f"{self.config.city}",
            f"History of {self.config.city}",
            f"Geography of {self.config.state}",
            f"List of places in {self.config.state}"
        ]
        
        for term in search_terms:
            results = self.api.search_pages(term, limit=5)
            starting_points.extend(results)
        
        # Remove duplicates and filter for relevance
        unique_points = list(set(starting_points))
        
        # Sort by relevance to city/state
        filtered_starts = []
        for point in unique_points:
            point_lower = point.lower()
            if self.config.city.lower() in point_lower or self.config.state.lower() in point_lower:
                filtered_starts.insert(0, point)
            else:
                filtered_starts.append(point)
        
        self.metadata.starting_points = filtered_starts[:10]
        return filtered_starts[:10]
    
    def crawl_bfs(self) -> Dict[str, WikipediaPage]:
        """
        Perform breadth-first search crawl starting from city/state pages.
        Returns dictionary of all crawled articles with their data.
        """
        start_time = time.time()
        logger.info(f"Starting crawl for {self.config.city}, {self.config.state}")
        
        # Get starting points
        starting_points = self.search_starting_points()
        
        if not starting_points:
            logger.error("No starting points found!")
            return {}
        
        logger.info(f"Found {len(starting_points)} starting points: {starting_points[:5]}")
        
        # Initialize queue with starting points at depth 0
        queue = deque([(page, 0) for page in starting_points[:5]])
        
        articles_by_depth = defaultdict(list)
        
        while queue:
            current_title, depth = queue.popleft()
            
            # Skip if already visited or max depth reached
            if current_title in self.visited or depth > self.config.max_depth:
                continue
            
            # Check articles limit for this depth level
            if len(articles_by_depth[depth]) >= self.config.max_articles_per_level:
                continue
            
            # Mark as visited
            self.visited.add(current_title)
            
            # Get page data
            logger.info(f"Crawling: {current_title} (depth: {depth})")
            page = self.api.get_page_data(current_title, self.config.download_html)
            
            if not page:
                self.metadata.error_count += 1
                continue
            
            # Set depth and calculate relevance
            page.depth = depth
            page.relevance_score = self.scorer.calculate_score(page)
            
            # Store data if relevant enough
            if page.relevance_score > 5 or depth == 0:
                self.articles_data[current_title] = page
                articles_by_depth[depth].append(current_title)
                
                # Update statistics
                if page.local_filename:
                    self.metadata.statistics.pages_downloaded += 1
                
                # Add links to queue if not at max depth
                if depth < self.config.max_depth:
                    # Score and filter links
                    scored_links = []
                    for link in page.links:
                        if link not in self.visited:
                            link_score = self.scorer.score_link_title(link)
                            if link_score > 0 or depth == 0:
                                scored_links.append((link, link_score))
                    
                    # Sort by score and take top N
                    scored_links.sort(key=lambda x: x[1], reverse=True)
                    
                    # Calculate how many links to add based on remaining capacity
                    remaining_at_next_depth = self.config.max_articles_per_level - len(articles_by_depth[depth + 1])
                    max_links_to_add = min(5, remaining_at_next_depth)
                    
                    for link, _ in scored_links[:max_links_to_add]:
                        queue.append((link, depth + 1))
                        self.link_graph[current_title].add(link)
            
            # Rate limiting
            time.sleep(self.config.delay)
            
            # Progress report
            if len(self.visited) % 10 == 0:
                logger.info(f"Processed {len(self.visited)} articles, "
                           f"kept {len(self.articles_data)} relevant ones, "
                           f"downloaded {self.metadata.statistics.pages_downloaded} pages")
        
        # Update metadata
        self.metadata.end_time = datetime.now()
        self.metadata.statistics = self.get_statistics()
        self.metadata.statistics.crawl_duration_seconds = time.time() - start_time
        
        logger.info(f"Crawl complete! Found {len(self.articles_data)} relevant articles")
        
        # Print summary by depth
        for depth in range(self.config.max_depth + 1):
            count = len(articles_by_depth[depth])
            if count > 0:
                logger.info(f"  Depth {depth}: {count} articles")
        
        return self.articles_data
    
    def get_statistics(self) -> CrawlStatistics:
        """Get statistics about the crawled data."""
        stats = CrawlStatistics()
        stats.total_articles = len(self.articles_data)
        
        total_score = 0
        for page in self.articles_data.values():
            # Count by depth
            if page.depth not in stats.articles_by_depth:
                stats.articles_by_depth[page.depth] = 0
            stats.articles_by_depth[page.depth] += 1
            
            # Count features
            if page.coordinates:
                stats.articles_with_coordinates += 1
            
            if page.image_url:
                stats.articles_with_images += 1
            
            total_score += page.relevance_score
            
            # Count categories
            for category in page.categories:
                if category not in stats.top_categories:
                    stats.top_categories[category] = 0
                stats.top_categories[category] += 1
        
        if stats.total_articles > 0:
            stats.average_relevance_score = total_score / stats.total_articles
        
        # Get top 10 categories
        stats.top_categories = dict(
            sorted(stats.top_categories.items(),
                   key=lambda x: x[1], reverse=True)[:10]
        )
        
        stats.pages_downloaded = self.metadata.statistics.pages_downloaded
        
        return stats
    
    def save_all(self):
        """Save all crawled data to the database."""
        self.db.save_articles(self.articles_data)
        
        # Generate attribution files for CC BY-SA 3.0 compliance
        try:
            from .generate_attribution import generate_attribution_from_database
            generate_attribution_from_database(self.config.data_dir)
            logger.info("Generated Wikipedia attribution files for CC BY-SA 3.0 compliance")
        except Exception as e:
            logger.warning(f"Could not generate attribution files: {e}")