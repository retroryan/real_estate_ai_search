#!/usr/bin/env python3
"""
Unit tests for database integration - Phase 4 validation.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from summarize.database import WikipediaDatabase
from summarize.models import (
    WikipediaPage,
    PageSummary,
    HtmlExtractedData,
    LocationMetadata
)


def test_database_init():
    """Test database initialization."""
    print("Testing database initialization...")
    
    db_path = "../data/wikipedia/wikipedia.db"
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"  ⚠ Database not found at {db_path}, skipping tests")
        return False
    
    # Initialize database
    db = WikipediaDatabase(db_path)
    
    # Check if page_summaries table was created
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='page_summaries'
        """)
        table_exists = cursor.fetchone() is not None
    
    assert table_exists, "page_summaries table not created"
    print("  ✓ Database initialized with page_summaries table")
    
    return True


def test_get_unprocessed_pages():
    """Test retrieving unprocessed pages."""
    print("Testing get_unprocessed_pages...")
    
    db_path = "../data/wikipedia/wikipedia.db"
    if not Path(db_path).exists():
        print("  ⚠ Database not found, skipping")
        return False
    
    db = WikipediaDatabase(db_path)
    
    # Get first batch of unprocessed pages
    pages = db.get_unprocessed_pages(limit=2)
    
    if len(pages) == 0:
        print("  ⚠ No unprocessed pages found (may all be processed)")
        return True
    
    # Check structure of returned data
    for page, metadata in pages:
        assert isinstance(page, WikipediaPage)
        assert isinstance(metadata, dict)
        assert 'article_id' in metadata
        assert 'location_city' in metadata
        assert 'location_state' in metadata
        
        print(f"  ✓ Found page: {page.title} in {metadata['location_state']}")
        break  # Just check first one
    
    return True


def test_save_and_retrieve_summary():
    """Test saving and retrieving a summary."""
    print("Testing save and retrieve summary...")
    
    db_path = "../data/wikipedia/wikipedia.db"
    if not Path(db_path).exists():
        print("  ⚠ Database not found, skipping")
        return False
    
    db = WikipediaDatabase(db_path)
    
    # Get an unprocessed page
    pages = db.get_unprocessed_pages(limit=1)
    if not pages:
        print("  ⚠ No unprocessed pages to test with")
        return True
    
    page, metadata = pages[0]
    
    # Create test extraction data
    html_extracted = HtmlExtractedData(
        city="Test City",
        county="Test County",
        state="California",
        confidence_scores={'city': 0.9, 'county': 0.85, 'state': 0.95},
        categories_found=["Test Category 1", "Test Category 2"]
    )
    
    llm_location = LocationMetadata(
        city="Test City",
        state="California",
        confidence_scores={'city': 0.8, 'state': 0.9}
    )
    
    # Create test summary
    summary = PageSummary(
        page_id=page.page_id,
        article_id=metadata['article_id'],
        title=page.title,
        summary="This is a test summary for validation purposes.",
        key_topics=["test", "validation", "database"],
        llm_location=llm_location,
        html_location=html_extracted,
        overall_confidence=0.85
    )
    
    # Save summary
    db.save_combined_summary(summary, metadata)
    print(f"  ✓ Saved summary for page {page.page_id}")
    
    # Verify it was saved
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT page_id, summary, best_city, best_state 
            FROM page_summaries 
            WHERE page_id = ?
        """, (page.page_id,))
        row = cursor.fetchone()
    
    assert row is not None, "Summary not found in database"
    assert row[1] == summary.summary, "Summary text mismatch"
    print(f"  ✓ Retrieved summary: {row[1][:50]}...")
    
    # Clean up test data
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM page_summaries WHERE page_id = ?", (page.page_id,))
        conn.commit()
    
    return True


def test_location_correlation():
    """Test location correlation verification."""
    print("Testing location correlation...")
    
    db_path = "../data/wikipedia/wikipedia.db"
    if not Path(db_path).exists():
        print("  ⚠ Database not found, skipping")
        return False
    
    db = WikipediaDatabase(db_path)
    
    # Check if we have any processed pages
    count = db.get_processed_count()
    if count == 0:
        print("  ⚠ No processed pages to test correlation")
        return True
    
    # Get statistics
    stats = db.get_location_statistics()
    
    if stats['total_processed'] > 0:
        print(f"  ✓ Found {stats['total_processed']} processed pages")
        if 'accuracy' in stats:
            print(f"  ✓ HTML State Accuracy: {stats['accuracy']['html']['state']:.1%}")
    
    return True


def test_categories_fetch():
    """Test fetching categories for an article."""
    print("Testing category fetching...")
    
    db_path = "../data/wikipedia/wikipedia.db"
    if not Path(db_path).exists():
        print("  ⚠ Database not found, skipping")
        return False
    
    db = WikipediaDatabase(db_path)
    
    # Get a page with categories
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT DISTINCT article_id 
            FROM categories 
            LIMIT 1
        """)
        row = cursor.fetchone()
    
    if row:
        article_id = row[0]
        categories = db.get_article_categories(article_id)
        
        assert isinstance(categories, list)
        if categories:
            print(f"  ✓ Found {len(categories)} categories for article {article_id}")
            print(f"  ✓ Sample category: {categories[0]}")
    else:
        print("  ⚠ No articles with categories found")
    
    return True


def main():
    """Run all database tests."""
    print("=" * 60)
    print("Phase 4: Database Integration - Validation Tests")
    print("=" * 60)
    
    tests = [
        ("Database Initialization", test_database_init),
        ("Get Unprocessed Pages", test_get_unprocessed_pages),
        ("Save and Retrieve Summary", test_save_and_retrieve_summary),
        ("Location Correlation", test_location_correlation),
        ("Categories Fetch", test_categories_fetch),
    ]
    
    all_passed = True
    for name, test_func in tests:
        try:
            passed = test_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"  ✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All Phase 4 database tests passed!")
    else:
        print("✗ Some tests failed - check errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())