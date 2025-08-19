"""
Utilities for loading and managing Wikipedia summaries from SQLite database.
"""

import sqlite3
import json
from typing import Dict, Optional
from pathlib import Path
from wiki_embed.models import PageSummary


def load_summaries_from_db(db_path: str) -> Dict[int, PageSummary]:
    """
    Load all page summaries from the Wikipedia SQLite database.
    
    Args:
        db_path: Path to the wikipedia.db SQLite database
        
    Returns:
        Dictionary mapping page_id to PageSummary objects
    """
    summaries = {}
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"Warning: Summary database not found at {db_path}")
        return summaries
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if page_summaries table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='page_summaries'
        """)
        
        if not cursor.fetchone():
            print("Warning: page_summaries table not found in database")
            conn.close()
            return summaries
        
        # Load all summaries
        query = """
        SELECT 
            page_id,
            short_summary,
            key_topics,
            best_city,
            best_county,
            best_state,
            overall_confidence
        FROM page_summaries
        """
        
        cursor.execute(query)
        
        for row in cursor.fetchall():
            page_id, summary, key_topics_json, city, county, state, confidence = row
            
            # Parse key_topics JSON
            key_topics = []
            if key_topics_json:
                try:
                    key_topics = json.loads(key_topics_json)
                except json.JSONDecodeError:
                    pass
            
            # Create PageSummary object
            summaries[page_id] = PageSummary(
                page_id=page_id,
                summary=summary or "",
                key_topics=key_topics,
                best_city=city,
                best_county=county,
                best_state=state,
                overall_confidence=confidence or 0.0
            )
        
        conn.close()
        print(f"Loaded {len(summaries)} summaries from database")
        
    except sqlite3.Error as e:
        print(f"Error loading summaries from database: {e}")
    
    return summaries


def get_summary_for_article(page_id: str, summaries: Dict[int, PageSummary]) -> Optional[PageSummary]:
    """
    Get summary data for a specific article by page_id.
    
    Args:
        page_id: The page ID (as string, will be converted to int)
        summaries: Dictionary of loaded summaries
        
    Returns:
        PageSummary object if found, None otherwise
    """
    try:
        # Convert string page_id to int for lookup
        page_id_int = int(page_id)
        return summaries.get(page_id_int)
    except (ValueError, TypeError):
        return None


def build_summary_context(summary: PageSummary, article_title: str, max_words: int = 100) -> str:
    """
    Build the summary context string to prepend to chunks.
    
    Args:
        summary: PageSummary object with summary data
        article_title: Title of the article (fallback if no summary)
        max_words: Maximum number of words for the summary context (default 100)
        
    Returns:
        Formatted summary context string (kept under max_words limit)
    """
    parts = []
    
    # Add the article summary
    if summary and summary.summary:
        # Truncate summary if needed to fit word limit
        summary_text = summary.summary
        summary_words = summary_text.split()
        if len(summary_words) > max_words * 0.7:  # Reserve 30% for topics/location
            summary_text = ' '.join(summary_words[:int(max_words * 0.7)]) + '...'
        parts.append(f"This article is about: {summary_text}")
    else:
        # Fallback to title if no summary
        parts.append(f"This article is about: {article_title}")
    
    # Add key topics if available (and we have word budget)
    current_text = ' '.join(parts)
    current_words = len(current_text.split())
    
    if summary and summary.key_topics and current_words < max_words * 0.85:
        # Limit topics based on remaining word budget
        topics = summary.key_topics[:5]
        topics_str = ', '.join(topics)
        topics_text = f"Key topics: {topics_str}"
        
        # Check if adding topics would exceed limit
        if current_words + len(topics_text.split()) <= max_words * 0.95:
            parts.append(topics_text)
            current_text = ' '.join(parts)
            current_words = len(current_text.split())
    
    # Add location hierarchy if we still have word budget
    if summary and current_words < max_words * 0.95:
        location_parts = []
        if summary.best_city:
            location_parts.append(summary.best_city)
        if summary.best_county:
            location_parts.append(summary.best_county)
        if summary.best_state:
            location_parts.append(summary.best_state)
        
        if location_parts:
            location_text = f"Location: {', '.join(location_parts)}"
            # Only add if it doesn't exceed limit
            if current_words + len(location_text.split()) <= max_words:
                parts.append(location_text)
    
    final_text = '\n'.join(parts)
    
    # Final check: ensure we're under the limit
    final_words = len(final_text.split())
    if final_words > max_words:
        # Aggressive truncation if somehow still over
        words = final_text.split()[:max_words]
        final_text = ' '.join(words)
    
    return final_text