"""
Wikipedia data extraction from SQLite database.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .models import WikipediaArticle, WikipediaLocation, WikipediaPOI, POICategory

logger = logging.getLogger(__name__)


class WikipediaExtractor:
    """Extracts Wikipedia data from the SQLite database."""
    
    def __init__(self, db_path: str = None):
        """Initialize the extractor with database path."""
        if db_path is None:
            # Use relative path from the module location
            # Go up from wikipedia/ to real_estate_search/, then to project root
            module_dir = Path(__file__).parent
            project_root = module_dir.parent.parent
            db_path = project_root / "data" / "wikipedia" / "wikipedia.db"
        else:
            db_path = Path(db_path)
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Wikipedia database not found at {db_path}")
    
    def get_articles_for_location(
        self, 
        city: str, 
        state: str,
        limit: int = 50
    ) -> List[WikipediaArticle]:
        """Get Wikipedia articles for a specific city/state."""
        query = """
            SELECT 
                ps.page_id,
                ps.article_id,
                ps.title,
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
            WHERE ps.best_city = ? AND ps.best_state = ?
            ORDER BY ps.overall_confidence DESC, a.relevance_score DESC
            LIMIT ?
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (city, state, limit))
            
            articles = []
            for row in cursor.fetchall():
                article = WikipediaArticle(
                    page_id=row['page_id'],
                    article_id=row['article_id'],
                    title=row['title'],
                    short_summary=row['short_summary'],
                    long_summary=row['long_summary'],
                    key_topics=row['key_topics'] or "",
                    best_city=row['best_city'],
                    best_county=row['best_county'],
                    best_state=row['best_state'],
                    overall_confidence=row['overall_confidence'] or 0.5,
                    url=row['url'],
                    relevance_score=row['relevance_score']
                )
                articles.append(article)
            
            logger.info(f"Found {len(articles)} Wikipedia articles for {city}, {state}")
            return articles
    
    def get_article_by_page_id(self, page_id: int) -> Optional[WikipediaArticle]:
        """Get a specific Wikipedia article by page ID."""
        query = """
            SELECT 
                ps.page_id,
                ps.article_id,
                ps.title,
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
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (page_id,))
            row = cursor.fetchone()
            
            if row:
                return WikipediaArticle(
                    page_id=row['page_id'],
                    article_id=row['article_id'],
                    title=row['title'],
                    short_summary=row['short_summary'],
                    long_summary=row['long_summary'],
                    key_topics=row['key_topics'] or "",
                    best_city=row['best_city'],
                    best_county=row['best_county'],
                    best_state=row['best_state'],
                    overall_confidence=row['overall_confidence'] or 0.5,
                    url=row['url'],
                    relevance_score=row['relevance_score']
                )
            return None
    
    def get_articles_by_title_pattern(
        self, 
        pattern: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 20
    ) -> List[WikipediaArticle]:
        """Get articles matching a title pattern."""
        query = """
            SELECT 
                ps.page_id,
                ps.article_id,
                ps.title,
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
            WHERE ps.title LIKE ?
        """
        
        params = [f"%{pattern}%"]
        
        if city:
            query += " AND ps.best_city = ?"
            params.append(city)
        
        if state:
            query += " AND ps.best_state = ?"
            params.append(state)
        
        query += " ORDER BY ps.overall_confidence DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            articles = []
            for row in cursor.fetchall():
                article = WikipediaArticle(
                    page_id=row['page_id'],
                    article_id=row['article_id'],
                    title=row['title'],
                    short_summary=row['short_summary'],
                    long_summary=row['long_summary'],
                    key_topics=row['key_topics'] or "",
                    best_city=row['best_city'],
                    best_county=row['best_county'],
                    best_state=row['best_state'],
                    overall_confidence=row['overall_confidence'] or 0.5,
                    url=row['url'],
                    relevance_score=row['relevance_score']
                )
                articles.append(article)
            
            return articles
    
    def extract_pois_from_articles(
        self, 
        articles: List[WikipediaArticle]
    ) -> List[WikipediaPOI]:
        """Extract POIs from Wikipedia articles based on keywords and topics."""
        pois = []
        
        # Category mapping based on keywords
        category_keywords = {
            POICategory.PARK: ['park', 'garden', 'recreation', 'green space'],
            POICategory.MUSEUM: ['museum', 'gallery', 'exhibition', 'cultural center'],
            POICategory.SCHOOL: ['school', 'university', 'college', 'education'],
            POICategory.TRANSIT: ['station', 'bart', 'metro', 'transit', 'transportation'],
            POICategory.LANDMARK: ['landmark', 'historic', 'monument', 'memorial'],
            POICategory.ENTERTAINMENT: ['theater', 'cinema', 'festival', 'venue'],
            POICategory.SPORTS: ['stadium', 'arena', 'sports', 'olympic', 'ski resort'],
            POICategory.CULTURAL: ['cultural', 'library', 'community center', 'arts']
        }
        
        for article in articles:
            # Determine POI category from title and topics
            title_lower = article.title.lower()
            topics_lower = " ".join(article.key_topics).lower()
            combined = f"{title_lower} {topics_lower}"
            
            # Create main POI from article
            category = None
            significance = 0.5
            
            for cat, keywords in category_keywords.items():
                if any(kw in combined for kw in keywords):
                    category = cat
                    # Boost significance for certain categories
                    if cat in [POICategory.LANDMARK, POICategory.MUSEUM]:
                        significance = 0.8
                    elif cat in [POICategory.PARK, POICategory.TRANSIT]:
                        significance = 0.7
                    break
            
            # Create main POI if category matched
            if category:
                poi = WikipediaPOI(
                    name=article.title,
                    wikipedia_page_id=article.page_id,
                    category=category,
                    significance_score=significance * article.overall_confidence,
                    description=article.short_summary[:500] if article.short_summary else None,
                    key_topics=article.key_topics[:5]  # Limit topics
                )
                pois.append(poi)
            
            # For demo purposes, also extract POIs from key topics
            # This creates more searchable POIs from the Wikipedia data
            for topic in article.key_topics[:3]:  # First 3 topics
                topic_lower = topic.lower()
                for cat, keywords in category_keywords.items():
                    if any(kw in topic_lower for kw in keywords):
                        # Create a POI from the topic
                        topic_poi = WikipediaPOI(
                            name=topic.title(),  # Capitalize topic name
                            wikipedia_page_id=article.page_id,  # Link to source article
                            category=cat,
                            significance_score=0.5 * article.overall_confidence,
                            description=f"Related to {article.title}",
                            key_topics=[topic]
                        )
                        pois.append(topic_poi)
                        break  # Only one category per topic
        
        logger.info(f"Extracted {len(pois)} POIs from {len(articles)} articles")
        return pois
    
    def get_location_statistics(self) -> Dict[str, int]:
        """Get statistics about available Wikipedia data."""
        query = """
            SELECT 
                COUNT(DISTINCT ps.page_id) as total_articles,
                COUNT(DISTINCT ps.best_city || ',' || ps.best_state) as unique_locations,
                COUNT(DISTINCT CASE WHEN ps.best_city = 'San Francisco' THEN ps.page_id END) as sf_articles,
                COUNT(DISTINCT CASE WHEN ps.best_city = 'Park City' THEN ps.page_id END) as pc_articles,
                COUNT(DISTINCT CASE WHEN ps.best_city = 'Oakland' THEN ps.page_id END) as oak_articles,
                COUNT(DISTINCT CASE WHEN ps.best_city = 'San Jose' THEN ps.page_id END) as sj_articles
            FROM page_summaries ps
            WHERE ps.best_city IS NOT NULL
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            
            return {
                'total_articles': row[0],
                'unique_locations': row[1],
                'san_francisco_articles': row[2],
                'park_city_articles': row[3],
                'oakland_articles': row[4],
                'san_jose_articles': row[5]
            }