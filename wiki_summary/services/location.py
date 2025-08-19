"""
Location management service following SOLID principles.
Handles location matching, creation, and article location fixes.

USAGE:
- Use this service for location mismatch detection and fixing
- LocationRepository: Database operations for locations
- LocationMismatchDetector: Detects when article location doesn't match extracted location  
- LocationFixService: Fixes location mismatches (including removing out-of-scope articles)
- LocationManager: Orchestrates the above services

For flexible location type classification (ski_resort, mountain, etc.), 
see flexible_location.py or integrated_location_evaluator.py
"""

import sqlite3
import logging
from typing import Optional, Tuple, Dict, Any
from contextlib import contextmanager
from wiki_summary.exceptions import DatabaseException

from wiki_summary.models import (
    LocationData, ArticleData, LocationMismatch, LocationFixResult,
    ConfidenceThreshold, Country, LocationType
)
from wiki_summary.summarize.models import PageSummary


logger = logging.getLogger(__name__)


class LocationRepository:
    """Repository pattern for location database operations."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    
    def create_location(self, location: LocationData) -> int:
        """Create location using INSERT OR IGNORE - no race conditions."""
        with self.get_connection() as conn:
            # Try to insert, ignore if already exists
            conn.execute("""
                INSERT OR IGNORE INTO locations (
                    country, state, county, location, location_type
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                location.country,
                location.state,
                location.county or '',
                location.city or '',
                location.location_type.value
            ))
            conn.commit()
            
            # Always safe to SELECT after INSERT OR IGNORE
            cursor = conn.execute(
                """SELECT location_id FROM locations 
                   WHERE country = ? AND state = ? 
                   AND (county = ? OR (county IS NULL AND ? IS NULL))
                   AND (location = ? OR (location IS NULL AND ? IS NULL))
                   AND location_type = ?""",
                (location.country, location.state, 
                 location.county or '', location.county,
                 location.city or '', location.city,
                 location.location_type.value)
            )
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"Failed to create or find location: {location.path}")
    
    def get_or_create_location(self, location: LocationData) -> int:
        """Get existing location or create if not exists - simplified with INSERT OR IGNORE."""
        # The create_location method now handles both cases atomically
        location_id = self.create_location(location)
        logger.debug(f"Location ensured: {location.path} (ID: {location_id})")
        return location_id
    
    def get_article_by_id(self, article_id: int) -> Optional[ArticleData]:
        """Get article data by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, pageid, title, location_id, url, extract, categories,
                       latitude, longitude, relevance_score, depth, crawled_at,
                       html_file, file_hash, image_url, links_count, infobox_data
                FROM articles WHERE id = ?
            """, (article_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ArticleData(
                id=row[0],
                pageid=row[1],
                title=row[2],
                location_id=row[3],
                url=row[4],
                extract=row[5],
                categories=row[6],
                latitude=row[7],
                longitude=row[8],
                relevance_score=row[9],
                depth=row[10],
                crawled_at=row[11],
                html_file=row[12],
                file_hash=row[13],
                image_url=row[14],
                links_count=row[15],
                infobox_data=row[16]
            )
    
    def update_article_location(self, article_id: int, new_location_id: int) -> bool:
        """Update an article's location_id - simple and atomic."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE articles SET location_id = ? WHERE id = ?",
                (new_location_id, article_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_out_of_scope_article(self, article: ArticleData, location: LocationData) -> bool:
        """
        Remove an article that's outside our Utah/California scope.
        Logs the removal to removed_content table and moves HTML file to removed_pages.
        
        DEMO: This is a simple cleanup to keep the demo focused on relevant content.
        """
        with self.get_connection() as conn:
            try:
                # First, ensure the removed_content table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS removed_content (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        page_id INTEGER,
                        title TEXT NOT NULL,
                        html_file TEXT,
                        detected_state TEXT,
                        detected_city TEXT,
                        detected_county TEXT,
                        removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reason TEXT DEFAULT 'Outside Utah/California scope'
                    )
                """)
                
                # Log the removal
                conn.execute("""
                    INSERT INTO removed_content 
                    (page_id, title, html_file, detected_state, detected_city, detected_county)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article.pageid,
                    article.title,
                    article.html_file,
                    location.state,
                    location.city,
                    location.county
                ))
                
                # Move the HTML file if it exists
                if article.html_file:
                    import os
                    import shutil
                    from pathlib import Path
                    
                    # Get the project root (parent of wiki_summary)
                    project_root = Path(__file__).parent.parent
                    
                    # Define source and destination paths
                    source_file = project_root / "data" / "wikipedia" / "pages" / article.html_file
                    removed_dir = project_root / "data" / "wikipedia" / "removed_pages"
                    dest_file = removed_dir / article.html_file
                    
                    # Create removed_pages directory if it doesn't exist
                    removed_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Move the file if it exists
                    if source_file.exists():
                        try:
                            shutil.move(str(source_file), str(dest_file))
                            logger.info(f"Moved HTML file to removed_pages: {article.html_file}")
                        except Exception as move_error:
                            logger.warning(f"Could not move HTML file {article.html_file}: {move_error}")
                    else:
                        logger.debug(f"HTML file not found, skipping move: {source_file}")
                
                # Remove from related tables first (maintain referential integrity)
                conn.execute("DELETE FROM flagged_content WHERE article_id = ?", (article.id,))
                # Use both article_id and page_id to ensure we remove the summary
                conn.execute("DELETE FROM page_summaries WHERE article_id = ? OR page_id = ?", 
                            (article.id, article.pageid))
                
                # Finally remove the article
                conn.execute("DELETE FROM articles WHERE id = ?", (article.id,))
                
                conn.commit()
                logger.info(f"Removed out-of-scope article: {article.title} -> {location.state}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to remove article {article.title}: {e}")
                conn.rollback()
                return False


class LocationMismatchDetector:
    """Service for detecting location mismatches."""
    
    @staticmethod
    def detect_mismatch(
        article_data: Dict[str, Any],
        summary: PageSummary,
        confidence_threshold: float = ConfidenceThreshold.MINIMUM_FOR_FIX.value
    ) -> Optional[LocationMismatch]:
        """
        Detect if there's a location mismatch between database and LLM extraction.
        
        Args:
            article_data: Dictionary with article data from database
            summary: Page summary with LLM-extracted location
            confidence_threshold: Minimum confidence to consider a mismatch
            
        Returns:
            LocationMismatch if detected, None otherwise
        """
        # Get location components to compare
        llm_state = summary.llm_location.state
        llm_city = summary.llm_location.city
        llm_county = summary.llm_location.county
        
        db_state = article_data.get('state')
        db_city = article_data.get('city')
        db_county = article_data.get('county')
        
        # Special case: Article is NOT about a geographic location at all
        # (LLM found no location with very low confidence)
        if db_state and not llm_state and summary.overall_confidence < 0.1:
            # Create a mismatch with empty corrected location to trigger removal
            current_location = LocationData.from_components(
                state=db_state,
                city=db_city,
                county=db_county
            )
            
            corrected_location = LocationData.from_components(
                state='',  # Empty state to trigger removal logic
                city=None,
                county=None
            )
            
            # Create article data
            article = ArticleData(
                id=article_data['id'],
                pageid=article_data['pageid'],
                title=article_data['title'],
                location_id=article_data.get('location_id', article_data['id']),
                extract=article_data.get('extract'),
                html_file=article_data.get('html_file')
            )
            
            return LocationMismatch(
                article=article,
                current_location=current_location,
                corrected_location=corrected_location,
                confidence=summary.overall_confidence
            )
        
        # Skip if confidence is too low for reliable correction
        if summary.overall_confidence < confidence_threshold:
            return None
        
        # IMPORTANT: Detect mismatch if LLM found a location but DB has none
        if llm_state and not db_state:
            # LLM found a location but article has no location assigned
            current_location = LocationData.from_components(
                state='',
                city='',
                county=''
            )
            corrected_location = LocationData.from_components(
                state=llm_state,
                city=llm_city,
                county=llm_county
            )
            # This IS a mismatch - article needs location assignment
            
        # Or if DB has location but LLM found none (with good confidence)
        elif db_state and not llm_state:
            # DB has location but LLM is confident there's no location
            # This should be rare if confidence is high
            return None  # Don't change if LLM isn't sure
            
        # Both have states - check if they match
        elif llm_state and db_state:
            # Create location objects for comparison
            current_location = LocationData.from_components(
                state=db_state,
                city=db_city,
                county=db_county
            )
            
            corrected_location = LocationData.from_components(
                state=llm_state,
                city=llm_city,
                county=llm_county
            )
            
            # Comprehensive mismatch detection:
            # 1. Different states -> definitely a mismatch
            if not current_location.matches_state(corrected_location.state):
                pass  # Will create mismatch below
                
            # 2. Same state but different cities -> mismatch
            elif (current_location.city and corrected_location.city and 
                  current_location.city.lower() != corrected_location.city.lower()):
                pass  # Will create mismatch below
                
            # 3. Same state, city missing from one side but present in other -> mismatch
            elif (current_location.city and not corrected_location.city) or \
                 (not current_location.city and corrected_location.city):
                pass  # Will create mismatch below
                
            # 4. Same state and city but different counties -> mismatch
            elif (current_location.county and corrected_location.county and
                  current_location.county.lower() != corrected_location.county.lower()):
                pass  # Will create mismatch below
                
            # 5. Everything matches (or is equivalently None) -> no mismatch
            else:
                return None
        else:
            # Shouldn't reach here, but handle gracefully
            return None
        
        # Create article data
        article = ArticleData(
            id=article_data['id'],
            pageid=article_data['pageid'],
            title=article_data['title'],
            location_id=article_data.get('location_id', article_data['id']),
            extract=article_data.get('extract'),
            html_file=article_data.get('html_file')
        )
        
        # Return mismatch
        return LocationMismatch(
            article=article,
            current_location=current_location,
            corrected_location=corrected_location,
            confidence=summary.overall_confidence
        )


class LocationFixService:
    """Service for fixing location mismatches."""
    
    def __init__(self, repository: LocationRepository):
        """Initialize with repository."""
        self.repository = repository
    
    def fix_location_mismatch(self, mismatch: LocationMismatch) -> LocationFixResult:
        """
        Handle location mismatches - for demo simplicity, we remove articles 
        that are clearly outside Utah/California scope.
        
        DEMO SIMPLIFICATION: Rather than trying to fix complex location mismatches,
        we simply remove articles that are definitively outside our target states.
        This keeps the demo data clean and focused on Utah/California content.
        
        Args:
            mismatch: The location mismatch to fix
            
        Returns:
            LocationFixResult indicating success or failure
        """
        if not mismatch.should_fix:
            return LocationFixResult(
                success=False,
                article_title=mismatch.article.title,
                article_id=mismatch.article.id,
                old_location_id=mismatch.article.location_id,
                new_location_id=mismatch.article.location_id,
                error_message=f"Confidence too low: {mismatch.confidence}"
            )
        
        # DEMO: Check if the corrected location is outside Utah/California
        # OR if the LLM couldn't identify any location with reasonable confidence
        target_states = {'Utah', 'UT', 'California', 'CA', 'Cal', 'Calif'}
        corrected_state = mismatch.corrected_location.state
        
        # Remove if: 1) State is outside Utah/California, OR 
        #           2) No state detected and very low confidence (likely not a location article)
        should_remove = False
        removal_reason = ""
        
        if not corrected_state and mismatch.confidence < 0.1:
            # LLM couldn't identify any location with even minimal confidence
            # This is likely not a location-based article at all (e.g., "Asteroid mining")
            should_remove = True
            removal_reason = "no identifiable location"
        elif corrected_state and corrected_state not in target_states:
            # Article is clearly about a location outside our scope
            should_remove = True
            removal_reason = f"outside scope ({corrected_state})"
        
        if should_remove:
            logger.info(
                f"Removing out-of-scope article: {mismatch.article.title} "
                f"(reason: {removal_reason})"
            )
            
            if self.repository.remove_out_of_scope_article(
                mismatch.article, 
                mismatch.corrected_location
            ):
                return LocationFixResult(
                    success=True,
                    article_title=mismatch.article.title,
                    article_id=mismatch.article.id,
                    old_location_id=mismatch.article.location_id,
                    new_location_id=-1,  # Special marker for removed
                    error_message=f"Article removed - {removal_reason}"
                )
        
        # For Utah/California articles, try to fix the location
        try:
            # Get or create the correct location
            new_location_id = self.repository.get_or_create_location(
                mismatch.corrected_location
            )
            
            # If it's the same location ID, no fix needed
            if new_location_id == mismatch.article.location_id:
                return LocationFixResult(
                    success=False,
                    article_title=mismatch.article.title,
                    article_id=mismatch.article.id,
                    old_location_id=mismatch.article.location_id,
                    new_location_id=new_location_id,
                    error_message="Location IDs are the same"
                )
            
            # Simply UPDATE the location_id - clean and atomic
            if self.repository.update_article_location(mismatch.article.id, new_location_id):
                logger.info(
                    f"Fixed location for {mismatch.article.title}: "
                    f"{mismatch.current_location.state} -> {mismatch.corrected_location.state}"
                )
                
                return LocationFixResult(
                    success=True,
                    article_title=mismatch.article.title,
                    article_id=mismatch.article.id,
                    old_location_id=mismatch.article.location_id,
                    new_location_id=new_location_id
                )
            else:
                return LocationFixResult(
                    success=False,
                    article_title=mismatch.article.title,
                    article_id=mismatch.article.id,
                    old_location_id=mismatch.article.location_id,
                    new_location_id=new_location_id,
                    error_message="Article not found or update failed"
                )
            
        except sqlite3.Error as e:
            logger.error(f"Database error fixing location for {mismatch.article.title}: {e}")
            raise DatabaseException(f"Failed to fix location: {e}") from e
        except (ValueError, KeyError) as e:
            logger.error(f"Data error fixing location for {mismatch.article.title}: {e}")
            return LocationFixResult(
                success=False,
                article_title=mismatch.article.title,
                article_id=mismatch.article.id,
                old_location_id=mismatch.article.location_id,
                new_location_id=mismatch.article.location_id,
                error_message=str(e)
            )


class LocationManager:
    """Facade for all location-related operations."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.repository = LocationRepository(db_path)
        self.detector = LocationMismatchDetector()
        self.fixer = LocationFixService(self.repository)
    
    def process_location_fix(
        self,
        article_data: Dict[str, Any],
        summary: PageSummary
    ) -> Optional[LocationFixResult]:
        """
        Process a potential location fix for an article.
        
        Args:
            article_data: Article data from database
            summary: Page summary with LLM-extracted location
            
        Returns:
            LocationFixResult if a fix was attempted, None otherwise
        """
        # Detect mismatch
        mismatch = self.detector.detect_mismatch(article_data, summary)
        if not mismatch:
            return None
        
        # Log the detection
        logger.info(
            f"Detected location mismatch for {mismatch.article.title}: "
            f"{mismatch.current_location.state} -> {mismatch.corrected_location.state} "
            f"(confidence: {mismatch.confidence:.2f})"
        )
        
        # Fix the mismatch
        result = self.fixer.fix_location_mismatch(mismatch)
        
        if result.success:
            logger.info(f"✓ Fixed location for {result.article_title}")
        else:
            logger.warning(
                f"Failed to fix location for {result.article_title}: {result.error_message}"
            )
        
        return result