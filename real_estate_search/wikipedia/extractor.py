"""
Wikipedia data extraction using repository pattern with constructor injection.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
import logging

from .models import WikipediaArticle, WikipediaLocation, WikipediaPOI, POICategory

if TYPE_CHECKING:
    from repositories.wikipedia_repository import WikipediaRepository

logger = logging.getLogger(__name__)


class WikipediaExtractor:
    """
    Extracts Wikipedia data using repository pattern.
    All dependencies injected through constructor.
    """
    
    def __init__(self, wikipedia_repository: 'WikipediaRepository'):
        """
        Initialize extractor with Wikipedia repository.
        
        Args:
            wikipedia_repository: Repository for Wikipedia data access
        """
        self.repository = wikipedia_repository
        logger.info("Wikipedia extractor initialized with repository")
    
    def get_articles_for_location(
        self, 
        city: str, 
        state: str,
        limit: int = 50
    ) -> List[WikipediaArticle]:
        """
        Get Wikipedia articles for a specific city/state.
        
        Args:
            city: City name
            state: State name or code
            limit: Maximum number of articles
            
        Returns:
            List of WikipediaArticle objects
        """
        return self.repository.get_articles_for_location(city, state, limit)
    
    def get_article_by_page_id(self, page_id: int) -> Optional[WikipediaArticle]:
        """
        Get a specific Wikipedia article by page ID.
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            WikipediaArticle object or None
        """
        return self.repository.get_article_by_page_id(page_id)
    
    def get_articles_by_title_pattern(
        self, 
        pattern: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 20
    ) -> List[WikipediaArticle]:
        """
        Get articles matching a title pattern.
        
        Args:
            pattern: Pattern to match in title
            city: Optional city filter
            state: Optional state filter
            limit: Maximum number of results
            
        Returns:
            List of WikipediaArticle objects
        """
        return self.repository.get_articles_by_title_pattern(pattern, city, state, limit)
    
    def extract_pois_from_articles(
        self, 
        articles: List[WikipediaArticle]
    ) -> List[WikipediaPOI]:
        """
        Extract POIs from Wikipedia articles.
        
        Args:
            articles: List of Wikipedia articles
            
        Returns:
            List of WikipediaPOI objects
        """
        return self.repository.extract_pois_from_articles(articles)
    
    def get_location_statistics(self) -> Dict[str, int]:
        """
        Get statistics about available Wikipedia data.
        
        Returns:
            Dictionary with location statistics
        """
        # Get stats for key cities
        stats = {
            'san_francisco': self.repository.get_location_stats('San Francisco', 'California'),
            'park_city': self.repository.get_location_stats('Park City', 'Utah'),
            'oakland': self.repository.get_location_stats('Oakland', 'California'),
            'san_jose': self.repository.get_location_stats('San Jose', 'California')
        }
        
        # Calculate totals
        total_articles = sum(s['article_count'] for s in stats.values())
        unique_locations = len([s for s in stats.values() if s['article_count'] > 0])
        
        return {
            'total_articles': total_articles,
            'unique_locations': unique_locations,
            'san_francisco_articles': stats['san_francisco']['article_count'],
            'park_city_articles': stats['park_city']['article_count'],
            'oakland_articles': stats['oakland']['article_count'],
            'san_jose_articles': stats['san_jose']['article_count']
        }