"""
Wikipedia data loader implementation with integrated enrichment.

Loads Wikipedia articles and summaries from SQLite database and returns enriched Pydantic models.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager

from .base import BaseLoader, log_operation
from property_finder_models import (
    EnrichedWikipediaArticle,
    WikipediaSummary,
    LocationInfo
)
from ..enrichers.address_utils import expand_city_name, expand_state_code
from ..enrichers.feature_utils import normalize_feature_list
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class WikipediaLoader(BaseLoader[Union[EnrichedWikipediaArticle, WikipediaSummary]]):
    """
    Loader for Wikipedia data from SQLite database.
    
    Loads articles and summaries from the Wikipedia database,
    applies enrichment, and returns Pydantic models.
    """
    
    def __init__(self, database_path: Path):
        """
        Initialize Wikipedia loader with database path.
        
        Args:
            database_path: Path to the Wikipedia SQLite database
        """
        super().__init__(database_path)
        
        if not database_path.suffix == '.db':
            logger.warning(f"Database path {database_path} doesn't have .db extension")
        
        # Test database connection
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test that we can connect to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Check if required tables exist
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('articles', 'page_summaries')"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                if 'articles' not in tables:
                    logger.warning("Table 'articles' not found in database")
                if 'page_summaries' not in tables:
                    logger.warning("Table 'page_summaries' not found in database")
                
                logger.debug(f"Database connection successful. Found tables: {tables}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """
        Get a database connection context manager.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.source_path))
            conn.row_factory = sqlite3.Row  # Enable column name access
            yield conn
        finally:
            if conn:
                conn.close()
    
    @log_operation("load_all_articles")
    def load_all(self) -> List[EnrichedWikipediaArticle]:
        """
        Load all Wikipedia articles from the database.
        
        Returns:
            List of EnrichedWikipediaArticle models
        """
        articles = []
        
        query = """
            SELECT 
                a.id as article_id,
                a.pageid as page_id,
                a.title,
                a.url,
                a.extract as full_text,
                a.depth,
                a.relevance_score,
                a.latitude,
                a.longitude,
                a.crawled_at as created_at
            FROM articles a
            ORDER BY a.pageid
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                for row in cursor:
                    try:
                        article = self._convert_to_enriched_article(dict(row))
                        articles.append(article)
                    except Exception as e:
                        page_id = dict(row).get('page_id', 'unknown')
                        logger.warning(f"Failed to convert article with page_id {page_id}: {e}")
                
            logger.info(f"Loaded {len(articles)} Wikipedia articles")
            
        except sqlite3.Error as e:
            logger.error(f"Database error loading articles: {e}")
        
        return articles
    
    @log_operation("load_articles_by_location")
    def load_by_filter(
        self, 
        city: Optional[str] = None,
        state: Optional[str] = None,
        with_summaries: bool = False,
        **filters
    ) -> List[EnrichedWikipediaArticle]:
        """
        Load Wikipedia articles filtered by location.
        
        Args:
            city: City name to filter by
            state: State name to filter by
            with_summaries: If True, only return articles that have summaries
            **filters: Additional filters
            
        Returns:
            List of EnrichedWikipediaArticle models matching the filters
        """
        if city is None and state is None and not with_summaries:
            # No filters, load all
            return self.load_all()
        
        articles = []
        
        # Build query with filters
        query_parts = ["""
            SELECT DISTINCT
                a.id as article_id,
                a.pageid as page_id,
                a.title,
                a.url,
                a.extract as full_text,
                a.depth,
                a.relevance_score,
                a.latitude,
                a.longitude,
                a.crawled_at as created_at
            FROM articles a
        """]
        
        conditions = []
        params = []
        
        if with_summaries:
            query_parts.append("INNER JOIN page_summaries ps ON a.id = ps.article_id")
            
            if city:
                conditions.append("(LOWER(ps.best_city) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
                params.extend([city, f'%{city}%'])
            
            if state:
                # Expand state codes if needed
                state_full = self._expand_state_code(state)
                conditions.append("(LOWER(ps.best_state) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
                params.extend([state_full, f'%{state_full}%'])
        else:
            # Search in title only if no summaries table join
            if city:
                conditions.append("LOWER(a.title) LIKE LOWER(?)")
                params.append(f'%{city}%')
            
            if state:
                state_full = self._expand_state_code(state)
                conditions.append("LOWER(a.title) LIKE LOWER(?)")
                params.append(f'%{state_full}%')
        
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append("ORDER BY a.relevance_score DESC, a.pageid")
        
        query = " ".join(query_parts)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                for row in cursor:
                    try:
                        article = self._convert_to_enriched_article(dict(row))
                        articles.append(article)
                    except Exception as e:
                        page_id = dict(row).get('page_id', 'unknown')
                        logger.warning(f"Failed to convert article with page_id {page_id}: {e}")
            
            logger.info(f"Loaded {len(articles)} Wikipedia articles with filters")
            
        except sqlite3.Error as e:
            logger.error(f"Database error loading filtered articles: {e}")
        
        return articles
    
    @log_operation("load_all_summaries")
    def load_summaries(self) -> List[WikipediaSummary]:
        """
        Load all Wikipedia summaries from the database.
        
        Returns:
            List of WikipediaSummary models
        """
        summaries = []
        
        query = """
            SELECT 
                ps.page_id,
                ps.article_id,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                ps.processed_at as created_at,
                ps.title as article_title,
                a.url as article_url
            FROM page_summaries ps
            LEFT JOIN articles a ON ps.article_id = a.id
            ORDER BY ps.page_id
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                for row in cursor:
                    try:
                        summary = self._convert_to_enriched_summary(dict(row))
                        summaries.append(summary)
                    except Exception as e:
                        page_id = dict(row).get('page_id', 'unknown')
                        logger.warning(f"Failed to convert summary with page_id {page_id}: {e}")
            
            logger.info(f"Loaded {len(summaries)} Wikipedia summaries")
            
        except sqlite3.Error as e:
            logger.error(f"Database error loading summaries: {e}")
        
        return summaries
    
    @log_operation("load_summaries_by_location")
    def load_summaries_by_location(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[WikipediaSummary]:
        """
        Load Wikipedia summaries filtered by location.
        
        Args:
            city: City name to filter by
            state: State name to filter by
            
        Returns:
            List of WikipediaSummary models matching the filters
        """
        if city is None and state is None:
            return self.load_summaries()
        
        summaries = []
        
        query_parts = ["""
            SELECT 
                ps.page_id,
                ps.article_id,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                ps.processed_at as created_at,
                ps.title as article_title,
                a.url as article_url
            FROM page_summaries ps
            LEFT JOIN articles a ON ps.article_id = a.id
        """]
        
        conditions = []
        params = []
        
        if city:
            conditions.append("(LOWER(ps.best_city) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
            params.extend([city, f'%{city}%'])
        
        if state:
            state_full = self._expand_state_code(state)
            conditions.append("(LOWER(ps.best_state) = LOWER(?) OR LOWER(a.title) LIKE LOWER(?))")
            params.extend([state_full, f'%{state_full}%'])
        
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append("ORDER BY ps.overall_confidence DESC, ps.page_id")
        
        query = " ".join(query_parts)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                for row in cursor:
                    summary_dict = dict(row)
                    
                    # Parse key_topics if it's a JSON string
                    if summary_dict.get('key_topics'):
                        try:
                            summary_dict['key_topics'] = json.loads(summary_dict['key_topics'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    summaries.append(summary_dict)
            
            logger.info(f"Loaded {len(summaries)} Wikipedia summaries with location filters")
            
        except sqlite3.Error as e:
            logger.error(f"Database error loading filtered summaries: {e}")
        
        return summaries
    
    def _expand_state_code(self, state: str) -> str:
        """
        Expand state code to full name if needed.
        
        Args:
            state: State code or name
            
        Returns:
            Full state name
        """
        # Use the centralized expand_state_code function from enrichers
        return expand_state_code(state)
    
    def _convert_to_enriched_article(self, raw_data: Dict[str, Any]) -> EnrichedWikipediaArticle:
        """
        Convert raw article data to EnrichedWikipediaArticle model with enrichment.
        
        Args:
            raw_data: Raw article dictionary from database
            
        Returns:
            EnrichedWikipediaArticle model
        """
        # Extract and validate required fields
        page_id = raw_data.get('page_id')
        if not page_id:
            raise ValueError("Article missing required page_id")
        
        article_id = raw_data.get('article_id', raw_data.get('id'))
        if not article_id:
            raise ValueError("Article missing required article_id")
        
        # Extract location information
        location = LocationInfo()
        
        # Extract city and state from title if available
        title = raw_data.get('title', '')
        if ',' in title:
            # Try to parse location from title (e.g., "Park City, Utah")
            parts = title.split(',')
            if len(parts) >= 2:
                potential_city = parts[0].strip()
                potential_state = parts[1].strip()
                location.city = expand_city_name(potential_city)
                location.state = expand_state_code(potential_state)
        
        # Use coordinates if available
        if raw_data.get('latitude') is not None and raw_data.get('longitude') is not None:
            location.latitude = float(raw_data['latitude'])
            location.longitude = float(raw_data['longitude'])
        
        # Create EnrichedWikipediaArticle
        article = EnrichedWikipediaArticle(
            page_id=int(page_id),
            article_id=int(article_id),
            title=title or 'Untitled',
            url=raw_data.get('url', ''),
            full_text=raw_data.get('full_text', ''),
            relevance_score=float(raw_data.get('relevance_score', 0.0)),
            location=location,
            depth=raw_data.get('depth')
        )
        
        return article
    
    def _convert_to_enriched_summary(self, raw_data: Dict[str, Any]) -> WikipediaSummary:
        """
        Convert raw summary data to WikipediaSummary model with enrichment.
        
        Args:
            raw_data: Raw summary dictionary from database
            
        Returns:
            WikipediaSummary model
        """
        # Extract and validate required fields
        page_id = raw_data.get('page_id')
        if not page_id:
            raise ValueError("Summary missing required page_id")
        
        # Parse key_topics if it's a JSON string
        key_topics = raw_data.get('key_topics', [])
        if isinstance(key_topics, str):
            try:
                key_topics = json.loads(key_topics)
            except (json.JSONDecodeError, TypeError):
                # Keep as empty list if not valid JSON
                logger.debug(f"Could not parse key_topics for page_id {page_id}")
                key_topics = []
        
        # Ensure key_topics is a list
        if not isinstance(key_topics, list):
            key_topics = []
        
        # Normalize key topics
        key_topics = normalize_feature_list(key_topics)
        
        # Expand city and state names
        best_city = raw_data.get('best_city')
        if best_city:
            best_city = expand_city_name(best_city)
        
        best_state = raw_data.get('best_state')
        if best_state:
            best_state = expand_state_code(best_state)
        
        # Create WikipediaSummary
        summary = WikipediaSummary(
            page_id=int(page_id),
            article_title=raw_data.get('article_title', 'Untitled'),
            short_summary=raw_data.get('short_summary', ''),
            long_summary=raw_data.get('long_summary', raw_data.get('short_summary', '')),
            key_topics=key_topics,
            best_city=best_city,
            best_county=raw_data.get('best_county'),
            best_state=best_state,
            overall_confidence=float(raw_data.get('overall_confidence', 0.0))
        )
        
        return summary