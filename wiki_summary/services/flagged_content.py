"""
Service for managing flagged content with immediate database writes.
Ensures data is persisted immediately, not batched.
"""

import sqlite3
import logging
from typing import Optional
from wiki_summary.models.relevance import RelevanceScore
from wiki_summary.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class FlaggedContentService:
    """Service for immediate persistence of flagged content evaluations."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the flagged_content table exists with proper schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flagged_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER UNIQUE,
                    title TEXT NOT NULL,
                    overall_score REAL,
                    location_score REAL,
                    re_score REAL,
                    geo_score REAL,
                    relevance_category TEXT,
                    reasons_to_flag TEXT,
                    reasons_to_keep TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
    
    def save_evaluation_immediately(self, evaluation: RelevanceScore) -> bool:
        """
        Save a single evaluation immediately to the database.
        
        Args:
            evaluation: The relevance score to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Only save articles that should actually be flagged (same logic as relevance_filter.py)
            should_flag = False
            category = None
            
            # Flag if it's outside Utah/California (location_relevance = 0.0)
            if evaluation.location_relevance <= 0.0:
                should_flag = True
                category = "non_target_location"
            # Flag if it has critical issues (like wrong state explicitly mentioned)
            elif any("CRITICAL" in r for r in evaluation.reasons_to_flag):
                should_flag = True
                category = "critical_issues"
            # Flag if overall score is very low despite being in Utah/California
            elif evaluation.overall_score < 0.3 and evaluation.location_relevance > 0.0:
                should_flag = True
                category = "low_relevance"
            
            # Only save if it should be flagged
            if should_flag:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO flagged_content 
                        (article_id, title, overall_score, location_score, re_score, geo_score,
                         relevance_category, reasons_to_flag, reasons_to_keep)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        evaluation.article_id,
                        evaluation.title,
                        round(evaluation.overall_score, 2),
                        round(evaluation.location_relevance, 2),
                        round(evaluation.real_estate_relevance, 2),
                        round(evaluation.geographic_scope, 2),
                        category,
                        ', '.join(evaluation.reasons_to_flag) if evaluation.reasons_to_flag else None,
                        ', '.join(evaluation.reasons_to_keep) if evaluation.reasons_to_keep else None
                    ))
                    conn.commit()
                    
                    logger.debug(f"Flagged article {evaluation.article_id} for {category}: {evaluation.title}")
                    return True
            else:
                # Article is good (Utah/California), don't flag it
                logger.debug(f"Article {evaluation.article_id} is relevant, not flagging: {evaluation.title}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Database error saving flagged_content for {evaluation.title}: {e}")
            raise DatabaseException(f"Failed to save flagged content: {e}") from e
        except (ValueError, AttributeError) as e:
            logger.error(f"Data error saving flagged_content for {evaluation.title}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get statistics from flagged_content table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN relevance_category = 'highly_relevant' THEN 1 ELSE 0 END) as highly_relevant,
                    SUM(CASE WHEN relevance_category = 'marginal_relevance' THEN 1 ELSE 0 END) as marginal_relevance,
                    SUM(CASE WHEN relevance_category = 'flagged_for_removal' THEN 1 ELSE 0 END) as flagged_for_removal
                FROM flagged_content
            """)
            
            row = cursor.fetchone()
            return {
                'total': row[0] or 0,
                'highly_relevant': row[1] or 0,
                'marginal_relevance': row[2] or 0,
                'flagged_for_removal': row[3] or 0
            }