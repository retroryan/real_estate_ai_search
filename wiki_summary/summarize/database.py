"""
Database operations for Wikipedia summarization system.
Handles integration with existing wikipedia.db and manages page summaries.
"""

import sqlite3
import json
from typing import Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from .models import (
    PageSummary, 
    WikipediaPage,
    HtmlExtractedData,
    LocationMetadata
)
from wiki_summary.exceptions import FileReadException, DatabaseException

logger = logging.getLogger(__name__)


class WikipediaDatabase:
    """
    Handle database operations for Wikipedia summaries.
    Integrates with existing articles, locations, and categories tables.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database connection and ensure tables exist.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Verify database exists
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        # Initialize tables
        self._init_tables()
        logger.info(f"Database initialized at {db_path}")
    
    def _init_tables(self):
        """Initialize page_summaries table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Create main summaries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_summaries (
                    page_id INTEGER PRIMARY KEY,
                    article_id INTEGER,
                    title TEXT,
                    short_summary TEXT NOT NULL,
                    long_summary TEXT NOT NULL,
                    key_topics TEXT,
                    best_city TEXT,
                    best_county TEXT,
                    best_state TEXT,
                    overall_confidence REAL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES articles(pageid)
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_page_summaries_article 
                ON page_summaries(article_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_summaries_best_location 
                ON page_summaries(best_city, best_county, best_state)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_summaries_processed 
                ON page_summaries(processed_at)
            """)
            
            conn.commit()
            logger.debug("Page summaries table initialized")
    
    def get_unprocessed_pages(self, limit: int = None) -> list[tuple[WikipediaPage, dict]]:
        """
        Get pages that haven't been summarized yet, along with metadata.
        
        Args:
            limit: Maximum number of pages to return (None for unlimited)
            
        Returns:
            List of tuples containing (WikipediaPage, metadata_dict)
        """
        with sqlite3.connect(self.db_path) as conn:
            # Handle limit - None means no limit
            if limit is not None:
                limit = int(limit)
            
            # Build query with or without LIMIT
            query = """
                SELECT 
                    a.id,
                    a.pageid,
                    a.title,
                    a.html_file,
                    a.extract,
                    a.categories as category_list,
                    a.latitude,
                    a.longitude,
                    l.path as location_path,
                    l.city as location_city,
                    l.county as location_county,
                    l.state as location_state,
                    l.country as location_country,
                    l.location_type
                FROM articles a
                JOIN locations l ON a.location_id = l.location_id
                LEFT JOIN page_summaries ps ON CAST(a.pageid AS INTEGER) = CAST(ps.page_id AS INTEGER)
                WHERE ps.page_id IS NULL
                ORDER BY a.relevance_score DESC, a.id
            """
            
            if limit is not None:
                query += " LIMIT ?"
                cursor = conn.execute(query, (limit,))
            else:
                cursor = conn.execute(query)
            
            pages = []
            for row in cursor:
                (article_id, page_id, title, html_file, extract, category_list,
                 latitude, longitude, location_path, location_city, location_county,
                 location_state, location_country, location_type) = row
                
                # Read HTML content from file
                html_content = self._read_html_file(html_file)
                if not html_content:
                    logger.warning(f"Skipping page {page_id}: Could not read HTML file")
                    continue
                
                # Create WikipediaPage object
                page = WikipediaPage(
                    page_id=page_id,
                    title=title,
                    html_content=html_content,
                    location_path=location_path,
                    html_file_path=html_file
                )
                
                # Parse categories (handle both JSON arrays and pipe-delimited strings)
                stored_categories = []
                if category_list:
                    try:
                        # Try JSON first
                        stored_categories = json.loads(category_list)
                    except json.JSONDecodeError:
                        # Fall back to pipe-delimited format
                        stored_categories = [cat.strip() for cat in category_list.split('|') if cat.strip()]
                
                # Create metadata dictionary
                metadata = {
                    'article_id': article_id,
                    'extract': extract,
                    'stored_categories': stored_categories,
                    'location_city': location_city,
                    'location_county': location_county,
                    'location_state': location_state,
                    'location_country': location_country,
                    'location_type': location_type,
                    'latitude': latitude,
                    'longitude': longitude
                }
                
                pages.append((page, metadata))
            
            logger.info(f"Retrieved {len(pages)} unprocessed pages")
            return pages
    
    def get_article_categories(self, article_id: int) -> list[str]:
        """
        Get all categories for a specific article from categories table.
        
        Args:
            article_id: ID from articles table
            
        Returns:
            List of category names
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT category 
                FROM categories 
                WHERE article_id = ?
                ORDER BY category
            """, (article_id,))
            
            categories = [row[0] for row in cursor]
            logger.debug(f"Found {len(categories)} categories for article {article_id}")
            return categories
    
    def save_combined_summary(self, summary: PageSummary, metadata: dict[str, Any]):
        """
        Save page summary (simplified version - only best location).
        Note: This method is kept for compatibility but uses simplified schema.
        
        Args:
            summary: PageSummary object with all extraction results
            metadata: Dictionary with article_id and other metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            # Prepare data for insertion
            article_id = metadata.get('article_id', 0)
            
            # Get best location (computed by model)
            best_loc = summary.best_location if summary.best_location else summary.compute_best_location()
            
            # Insert or replace summary - using simplified schema
            conn.execute("""
                INSERT OR REPLACE INTO page_summaries (
                    page_id, article_id, title,
                    short_summary, long_summary, key_topics,
                    best_city, best_county, best_state,
                    overall_confidence, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.page_id,
                article_id,
                summary.title,
                summary.short_summary,
                summary.long_summary,
                json.dumps(summary.key_topics) if isinstance(summary.key_topics, list) else summary.key_topics,
                best_loc.city if best_loc else None,
                best_loc.county if best_loc else None,
                best_loc.state if best_loc else None,
                summary.overall_confidence,
                summary.processed_at.isoformat()
            ))
            
            conn.commit()
            logger.info(f"Saved summary for page {summary.page_id}: {summary.title}")
    
    def verify_location_correlation(self, page_id: int) -> dict[str, Any]:
        """
        Verify how well extracted locations correlate with stored location data.
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Dictionary with correlation metrics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    ps.best_city, ps.best_county, ps.best_state,
                    ps.overall_confidence,
                    l.city, l.county, l.state
                FROM page_summaries ps
                JOIN articles a ON ps.article_id = a.id
                JOIN locations l ON a.location_id = l.location_id
                WHERE ps.page_id = ?
            """, (page_id,))
            
            row = cursor.fetchone()
            if not row:
                return {}
            
            (best_city, best_county, best_state, confidence,
             actual_city, actual_county, actual_state) = row
            
            # Normalize for comparison (handle None values)
            def normalize(s):
                return s.lower().strip() if s else None
            
            # Calculate matches
            best_city_match = normalize(best_city) == normalize(actual_city) if best_city and actual_city else None
            best_county_match = normalize(best_county) == normalize(actual_county) if best_county and actual_county else None
            best_state_match = normalize(best_state) == normalize(actual_state) if best_state and actual_state else None
            
            return {
                'extracted': {
                    'city': best_city,
                    'county': best_county,
                    'state': best_state
                },
                'actual': {
                    'city': actual_city,
                    'county': actual_county,
                    'state': actual_state
                },
                'confidence': confidence,
                'matches': {
                    'city': best_city_match,
                    'county': best_county_match,
                    'state': best_state_match
                }
            }
    
    def get_location_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics on location extraction accuracy.
        
        Returns:
            Dictionary with comprehensive statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Overall statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    
                    -- Best guess matches
                    SUM(CASE WHEN LOWER(ps.best_city) = LOWER(l.city) THEN 1 ELSE 0 END) as best_city_matches,
                    SUM(CASE WHEN LOWER(ps.best_county) = LOWER(l.county) THEN 1 ELSE 0 END) as best_county_matches,
                    SUM(CASE WHEN LOWER(ps.best_state) = LOWER(l.state) THEN 1 ELSE 0 END) as best_state_matches,
                    
                    -- Average confidence scores
                    AVG(ps.overall_confidence) as avg_overall_conf
                    
                FROM page_summaries ps
                JOIN articles a ON ps.article_id = a.id
                JOIN locations l ON a.location_id = l.location_id
            """)
            
            row = cursor.fetchone()
            if not row or row[0] == 0:
                return {'total_processed': 0}
            
            total = row[0]
            
            return {
                'total_processed': total,
                'accuracy': {
                    'city': row[1] / total if total > 0 else 0,
                    'county': row[2] / total if total > 0 else 0,
                    'state': row[3] / total if total > 0 else 0
                },
                'average_confidence': row[4]
            }
    
    def get_processing_summary(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent processing summaries for review.
        
        Args:
            limit: Number of recent summaries to return
            
        Returns:
            List of summary dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    ps.page_id,
                    ps.title,
                    ps.short_summary,
                    ps.best_city,
                    ps.best_county,
                    ps.best_state,
                    ps.overall_confidence,
                    ps.processed_at,
                    l.city as actual_city,
                    l.county as actual_county,
                    l.state as actual_state
                FROM page_summaries ps
                JOIN articles a ON ps.article_id = a.id
                JOIN locations l ON a.location_id = l.location_id
                ORDER BY ps.processed_at DESC
                LIMIT ?
            """, (limit,))
            
            summaries = []
            for row in cursor:
                summaries.append({
                    'page_id': row[0],
                    'title': row[1],
                    'summary': row[2],
                    'extracted_location': f"{row[3]}, {row[4]}, {row[5]}",
                    'actual_location': f"{row[8]}, {row[9]}, {row[10]}",
                    'confidence': row[6],
                    'processed_at': row[7]
                })
            
            return summaries
    
    def _read_html_file(self, file_path: str) -> Optional[str]:
        """
        Read HTML content from file.
        
        Args:
            file_path: Simple filename (after migration) or path to HTML file
            
        Returns:
            HTML content or None if error
        """
        try:
            # Extract just the filename
            filename = Path(file_path).name
            
            # Files are now stored in a flat structure: data/wikipedia/pages/
            base_dir = Path(self.db_path).parent  # Get wikipedia directory from db path
            pages_dir = base_dir / "pages"
            full_path = pages_dir / filename
            
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.debug(f"Read HTML file: {full_path} ({len(content)} bytes)")
                return content
            
            # Fallback: search in old directory structure (for backward compatibility)
            matching_files = list(base_dir.glob(f"**/pages/{filename}"))
            if matching_files:
                full_path = matching_files[0]
                logger.debug(f"Found HTML file at: {full_path}")
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                logger.debug(f"Read HTML file: {full_path} ({len(content)} bytes)")
                return content
            
            logger.error(f"HTML file not found: {filename}")
            return None
            
        except (IOError, OSError) as e:
            logger.error(f"Error reading HTML file {file_path}: {e}")
            return None
        except UnicodeDecodeError as e:
            logger.error(f"Error decoding HTML file {file_path}: {e}")
            return None
    
    def reset_processing(self):
        """Reset all processing (delete all summaries) - useful for testing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM page_summaries")
            conn.commit()
            logger.warning("Reset: All page summaries deleted")
    
    def get_processed_count(self) -> int:
        """Get count of processed pages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM page_summaries")
            return cursor.fetchone()[0]