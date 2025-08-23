"""Wikipedia data source implementation"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json

from src.core.interfaces import IWikipediaDataSource


class WikipediaFileDataSource(IWikipediaDataSource):
    """File and SQLite-based Wikipedia data source"""
    
    def __init__(self, data_path: Path):
        """
        Initialize Wikipedia data source
        
        Args:
            data_path: Path to Wikipedia data directory
        """
        self.data_path = data_path
        self.pages_path = data_path / "pages"
        self.db_path = data_path / "wikipedia.db"
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def exists(self) -> bool:
        """Check if data source exists"""
        return self.db_path.exists() and self.pages_path.exists()
    
    def load(self) -> Dict[str, Any]:
        """Load all Wikipedia data"""
        return {
            "articles": self.load_articles(),
            "summaries": self.load_summaries()
        }
    
    def load_articles(self) -> List[Dict[str, Any]]:
        """
        Load Wikipedia articles from database
        
        Returns:
            List of article dictionaries
        """
        if not self.db_path.exists():
            self.logger.warning(f"Wikipedia database not found: {self.db_path}")
            return []
        
        articles = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query all articles
                query = """
                SELECT 
                    page_id,
                    title,
                    url,
                    full_text,
                    depth,
                    relevance_score,
                    latitude,
                    longitude,
                    created_at
                FROM articles
                ORDER BY page_id
                """
                
                cursor.execute(query)
                
                for row in cursor:
                    articles.append(dict(row))
                
                self.logger.info(f"Loaded {len(articles)} Wikipedia articles")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database error loading articles: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load articles: {e}")
        
        return articles
    
    def load_summaries(self) -> List[Dict[str, Any]]:
        """
        Load Wikipedia summaries from database
        
        Returns:
            List of summary dictionaries
        """
        if not self.db_path.exists():
            self.logger.warning(f"Wikipedia database not found: {self.db_path}")
            return []
        
        summaries = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query all summaries with article info
                query = """
                SELECT 
                    ps.page_id,
                    ps.article_id,
                    ps.summary,
                    ps.key_topics,
                    ps.best_city,
                    ps.best_state,
                    ps.overall_confidence,
                    ps.created_at,
                    a.title as article_title,
                    a.url as article_url
                FROM page_summaries ps
                JOIN articles a ON ps.article_id = a.id
                ORDER BY ps.page_id
                """
                
                cursor.execute(query)
                
                for row in cursor:
                    summary_dict = dict(row)
                    
                    # Parse key_topics if it's a JSON string
                    if summary_dict.get("key_topics"):
                        try:
                            summary_dict["key_topics"] = json.loads(summary_dict["key_topics"])
                        except (json.JSONDecodeError, TypeError):
                            # Keep as string if not valid JSON
                            pass
                    
                    summaries.append(summary_dict)
                
                self.logger.info(f"Loaded {len(summaries)} Wikipedia summaries")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database error loading summaries: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load summaries: {e}")
        
        return summaries
    
    def get_html_file(self, page_id: int) -> Optional[Path]:
        """
        Get path to HTML file for a Wikipedia page
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Path to HTML file if it exists, None otherwise
        """
        html_file = self.pages_path / f"{page_id}.html"
        return html_file if html_file.exists() else None
    
    def list_html_files(self) -> List[Path]:
        """
        List all HTML files in pages directory
        
        Returns:
            List of HTML file paths
        """
        if not self.pages_path.exists():
            return []
        
        return list(self.pages_path.glob("*.html"))
    
    def get_article_by_page_id(self, page_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific article by page ID
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Article dictionary if found, None otherwise
        """
        if not self.db_path.exists():
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                SELECT * FROM articles WHERE page_id = ?
                """
                
                cursor.execute(query, (page_id,))
                row = cursor.fetchone()
                
                return dict(row) if row else None
                
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting article {page_id}: {e}")
            return None
    
    def get_summary_by_page_id(self, page_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific summary by page ID
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Summary dictionary if found, None otherwise
        """
        if not self.db_path.exists():
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    ps.*,
                    a.title as article_title,
                    a.url as article_url
                FROM page_summaries ps
                JOIN articles a ON ps.article_id = a.id
                WHERE ps.page_id = ?
                """
                
                cursor.execute(query, (page_id,))
                row = cursor.fetchone()
                
                if row:
                    summary_dict = dict(row)
                    
                    # Parse key_topics if it's a JSON string
                    if summary_dict.get("key_topics"):
                        try:
                            summary_dict["key_topics"] = json.loads(summary_dict["key_topics"])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    return summary_dict
                
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting summary {page_id}: {e}")
            return None