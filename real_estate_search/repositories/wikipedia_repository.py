"""
Repository for Wikipedia data access with constructor injection.
All database operations for Wikipedia data go through this repository.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from infrastructure.database import DatabaseConnection
from wikipedia.models import WikipediaArticle, WikipediaPOI, POICategory

logger = logging.getLogger(__name__)


class WikipediaRepository:
    """
    Repository for Wikipedia data access.
    All dependencies injected through constructor.
    """
    
    def __init__(self, database: DatabaseConnection):
        """
        Initialize repository with database connection.
        
        Args:
            database: Database connection object
        """
        self.database = database
        logger.info("Wikipedia repository initialized")
    
    def get_articles_for_location(
        self, 
        city: str, 
        state: str,
        limit: int = 10
    ) -> List[WikipediaArticle]:
        """
        Get Wikipedia articles for a specific location.
        
        Args:
            city: City name
            state: State name or code
            limit: Maximum number of articles to return
            
        Returns:
            List of WikipediaArticle objects
        """
        # Convert state code to full name if needed
        state_map = {
            'CA': 'California', 'UT': 'Utah', 'NY': 'New York', 
            'TX': 'Texas', 'FL': 'Florida', 'CO': 'Colorado',
            'WA': 'Washington', 'OR': 'Oregon', 'NV': 'Nevada',
            'AZ': 'Arizona', 'IL': 'Illinois', 'MA': 'Massachusetts'
        }
        if len(state) == 2:
            state = state_map.get(state.upper(), state)
        
        query = """
            SELECT 
                ps.page_id,
                a.id as article_id,
                a.title,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                a.url,
                a.relevance_score
            FROM page_summaries ps
            JOIN articles a ON ps.article_id = a.id
            WHERE (
                LOWER(ps.best_city) = LOWER(?) OR
                LOWER(a.title) LIKE LOWER(?)
            ) AND (
                LOWER(ps.best_state) = LOWER(?) OR
                LOWER(a.title) LIKE LOWER(?)
            )
            ORDER BY ps.overall_confidence DESC, a.relevance_score DESC
            LIMIT ?
        """
        
        params = (
            city, f'%{city}%',
            state, f'%{state}%',
            limit
        )
        
        rows = self.database.execute_query(query, params)
        
        articles = []
        for row in rows:
            article = WikipediaArticle(
                page_id=row['page_id'],
                article_id=row['article_id'],
                title=row['title'],
                short_summary=row['short_summary'] or '',
                long_summary=row['long_summary'] or '',
                key_topics=row['key_topics'] or '',
                best_city=row['best_city'],
                best_county=row['best_county'],
                best_state=row['best_state'],
                overall_confidence=row['overall_confidence'] or 0.0,
                url=row['url'],
                relevance_score=row['relevance_score']
            )
            articles.append(article)
        
        logger.info(f"Found {len(articles)} articles for {city}, {state}")
        return articles
    
    def get_article_by_page_id(self, page_id: int) -> Optional[WikipediaArticle]:
        """
        Get a specific Wikipedia article by page ID.
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            WikipediaArticle object or None if not found
        """
        query = """
            SELECT 
                ps.page_id,
                a.id as article_id,
                a.title,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                a.url,
                a.relevance_score
            FROM page_summaries ps
            JOIN articles a ON ps.article_id = a.id
            WHERE ps.page_id = ?
        """
        
        rows = self.database.execute_query(query, (page_id,))
        
        if not rows:
            return None
        
        row = rows[0]
        return WikipediaArticle(
            page_id=row['page_id'],
            article_id=row['article_id'],
            title=row['title'],
            short_summary=row['short_summary'] or '',
            long_summary=row['long_summary'] or '',
            key_topics=row['key_topics'] or '',
            best_city=row['best_city'],
            best_county=row['best_county'],
            best_state=row['best_state'],
            overall_confidence=row['overall_confidence'] or 0.0,
            url=row['url'],
            relevance_score=row['relevance_score']
        )
    
    def get_articles_by_title_pattern(
        self,
        pattern: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 5
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
        query_parts = ["""
            SELECT 
                ps.page_id,
                a.id as article_id,
                a.title,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                a.url,
                a.relevance_score
            FROM page_summaries ps
            JOIN articles a ON ps.article_id = a.id
            WHERE LOWER(a.title) LIKE LOWER(?)
        """]
        
        params = [f'%{pattern}%']
        
        if city:
            query_parts.append("AND (LOWER(ps.best_city) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
            params.extend([city, f'%{city}%'])
        
        if state:
            # Convert state code to full name if needed
            state_map = {
                'CA': 'California', 'UT': 'Utah', 'NY': 'New York',
                'TX': 'Texas', 'FL': 'Florida', 'CO': 'Colorado'
            }
            if len(state) == 2:
                state = state_map.get(state.upper(), state)
            
            query_parts.append("AND (LOWER(ps.best_state) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
            params.extend([state, f'%{state}%'])
        
        query_parts.append("ORDER BY ps.overall_confidence DESC, a.relevance_score DESC")
        query_parts.append("LIMIT ?")
        params.append(limit)
        
        query = " ".join(query_parts)
        rows = self.database.execute_query(query, tuple(params))
        
        articles = []
        for row in rows:
            article = WikipediaArticle(
                page_id=row['page_id'],
                article_id=row['article_id'],
                title=row['title'],
                short_summary=row['short_summary'] or '',
                long_summary=row['long_summary'] or '',
                key_topics=row['key_topics'] or '',
                best_city=row['best_city'],
                best_county=row['best_county'],
                best_state=row['best_state'],
                overall_confidence=row['overall_confidence'] or 0.0,
                url=row['url'],
                relevance_score=row['relevance_score']
            )
            articles.append(article)
        
        logger.info(f"Found {len(articles)} articles matching pattern '{pattern}'")
        return articles
    
    def extract_pois_from_articles(
        self,
        articles: List[WikipediaArticle],
        max_pois: int = 20
    ) -> List[WikipediaPOI]:
        """
        Extract points of interest from Wikipedia articles.
        
        Args:
            articles: List of Wikipedia articles
            max_pois: Maximum number of POIs to return
            
        Returns:
            List of WikipediaPOI objects
        """
        pois = []
        seen_names = set()
        
        for article in articles:
            # Extract POIs from article content
            # This is a simplified extraction - in production would use NLP
            
            # Look for common POI patterns in the summary
            poi_keywords = {
                'park': POICategory.PARK,
                'museum': POICategory.MUSEUM,
                'school': POICategory.SCHOOL,
                'university': POICategory.SCHOOL,
                'station': POICategory.TRANSIT,
                'airport': POICategory.TRANSIT,
                'mall': POICategory.SHOPPING,
                'market': POICategory.SHOPPING,
                'monument': POICategory.LANDMARK,
                'theater': POICategory.ENTERTAINMENT,
                'stadium': POICategory.SPORTS,
                'gallery': POICategory.CULTURAL,
                'library': POICategory.CULTURAL
            }
            
            # Extract from title if it's a specific place
            title_lower = article.title.lower()
            for keyword, category in poi_keywords.items():
                if keyword in title_lower and article.title not in seen_names:
                    poi = WikipediaPOI(
                        name=article.title,
                        wikipedia_page_id=article.page_id,
                        category=category,
                        significance_score=min(article.overall_confidence * 1.2, 1.0),
                        description=article.short_summary[:500] if article.short_summary else None,
                        key_topics=article.key_topics[:5] if article.key_topics else []
                    )
                    pois.append(poi)
                    seen_names.add(article.title)
                    break
            
            # Extract from key topics
            for topic in article.key_topics[:10]:
                topic_lower = topic.lower()
                for keyword, category in poi_keywords.items():
                    if keyword in topic_lower and topic not in seen_names:
                        poi = WikipediaPOI(
                            name=topic,
                            wikipedia_page_id=article.page_id,
                            category=category,
                            significance_score=article.overall_confidence * 0.8,
                            description=f"Related to {article.title}",
                            key_topics=[article.title]
                        )
                        pois.append(poi)
                        seen_names.add(topic)
                        
                        if len(pois) >= max_pois:
                            break
                
                if len(pois) >= max_pois:
                    break
            
            if len(pois) >= max_pois:
                break
        
        # Sort by significance score
        pois.sort(key=lambda x: x.significance_score, reverse=True)
        
        logger.info(f"Extracted {len(pois)} POIs from {len(articles)} articles")
        return pois[:max_pois]
    
    def get_location_stats(self, city: str, state: str) -> Dict[str, Any]:
        """
        Get statistics about Wikipedia coverage for a location.
        
        Args:
            city: City name
            state: State name or code
            
        Returns:
            Dictionary with location statistics
        """
        # Convert state code if needed
        state_map = {
            'CA': 'California', 'UT': 'Utah', 'NY': 'New York',
            'TX': 'Texas', 'FL': 'Florida', 'CO': 'Colorado'
        }
        if len(state) == 2:
            state = state_map.get(state.upper(), state)
        
        query = """
            SELECT 
                COUNT(*) as article_count,
                AVG(ps.overall_confidence) as avg_confidence,
                MAX(ps.overall_confidence) as max_confidence,
                MIN(ps.overall_confidence) as min_confidence
            FROM page_summaries ps
            JOIN articles a ON ps.article_id = a.id
            WHERE (
                LOWER(ps.best_city) = LOWER(?) OR
                LOWER(a.title) LIKE LOWER(?)
            ) AND (
                LOWER(ps.best_state) = LOWER(?) OR
                LOWER(a.title) LIKE LOWER(?)
            )
        """
        
        params = (city, f'%{city}%', state, f'%{state}%')
        rows = self.database.execute_query(query, params)
        
        if rows:
            row = rows[0]
            return {
                'article_count': row['article_count'] or 0,
                'avg_confidence': row['avg_confidence'] or 0.0,
                'max_confidence': row['max_confidence'] or 0.0,
                'min_confidence': row['min_confidence'] or 0.0
            }
        
        return {
            'article_count': 0,
            'avg_confidence': 0.0,
            'max_confidence': 0.0,
            'min_confidence': 0.0
        }