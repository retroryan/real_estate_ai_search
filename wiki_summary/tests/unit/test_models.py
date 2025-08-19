#!/usr/bin/env python3
"""
Unit tests for Pydantic models - Phase 2 validation.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from summarize.models import (
    LocationMetadata,
    HtmlExtractedData, 
    PageSummary,
    WikipediaPage,
    ProcessingResult,
    BatchProcessingStats
)


def test_location_metadata():
    """Test LocationMetadata model."""
    print("Testing LocationMetadata...")
    
    # Test basic creation
    loc = LocationMetadata(
        city="San Francisco",
        state="California",
        confidence_scores={"city": 0.9, "state": 0.95}
    )
    assert loc.city == "San Francisco"
    assert loc.get_confidence("city") == 0.9
    assert loc.get_confidence("county") == 0.0  # Default for missing
    
    # Test best guess
    best = loc.to_best_guess()
    assert best['city'] == "San Francisco"  # High confidence
    assert best['county'] is None  # No data
    
    # Test validation
    try:
        # Should fail - confidence > 1
        bad_loc = LocationMetadata(confidence_scores={"city": 1.5})
        assert False, "Should have raised validation error"
    except ValueError:
        pass  # Expected
    
    print("  ✓ LocationMetadata tests passed")
    return True


def test_html_extracted_data():
    """Test HtmlExtractedData model."""
    print("Testing HtmlExtractedData...")
    
    # Test creation with categories
    html_data = HtmlExtractedData(
        city="Park City",
        state="Utah",
        categories_found=["Cities in Utah"] * 30,  # Should be limited
        confidence_scores={"city": 0.85, "state": 0.9}
    )
    
    assert len(html_data.categories_found) == 20  # Limited to 20
    assert html_data.has_high_confidence() == True  # state=0.9 > 0.8
    
    print("  ✓ HtmlExtractedData tests passed")
    return True


def test_wikipedia_page():
    """Test WikipediaPage model."""
    print("Testing WikipediaPage...")
    
    # Test valid page
    page = WikipediaPage(
        page_id=12345,
        title="Test Page",
        html_content="<html>" + "x" * 100 + "</html>",  # Minimum content
        location_path="usa/california/san_francisco"
    )
    
    parts = page.get_location_parts()
    assert parts['country'] == "usa"
    assert parts['state'] == "california"
    assert parts.get('county_or_city') == "san_francisco"
    
    # Test validation
    try:
        # Should fail - content too short
        bad_page = WikipediaPage(
            page_id=1,
            title="Bad",
            html_content="short",
            location_path="usa/ca"
        )
        assert False, "Should have raised validation error"
    except ValueError:
        pass  # Expected
    
    print("  ✓ WikipediaPage tests passed")
    return True


def test_page_summary():
    """Test PageSummary model."""
    print("Testing PageSummary...")
    
    # Create test data
    html_loc = HtmlExtractedData(
        city="San Francisco",
        state="California",
        confidence_scores={"city": 0.9, "state": 0.95}
    )
    
    llm_loc = LocationMetadata(
        city="San Francisco",
        county="San Francisco County",
        state="California",
        confidence_scores={"city": 0.8, "county": 0.7, "state": 0.85}
    )
    
    summary = PageSummary(
        page_id=123,
        title="San Francisco",
        summary="San Francisco is a city in California",
        key_topics=["city", "california", "bay area"],
        llm_location=llm_loc,
        html_location=html_loc
    )
    
    # Test best location computation
    assert summary.best_location.city == "San Francisco"  # HTML has higher confidence
    assert summary.best_location.state == "California"  # HTML has higher confidence
    assert summary.best_location.county == "San Francisco County"  # Only from LLM
    
    # Test overall confidence
    assert 0.7 < summary.overall_confidence < 0.9
    
    # Test summary cleaning
    summary2 = PageSummary(
        page_id=124,
        title="Test",
        summary="This is a test   with   spaces",  # Extra spaces
        llm_location=llm_loc,
        html_location=html_loc
    )
    assert summary2.summary == "This is a test with spaces."  # Cleaned and punctuated
    
    print("  ✓ PageSummary tests passed")
    return True


def test_processing_stats():
    """Test ProcessingResult and BatchProcessingStats."""
    print("Testing Processing Statistics...")
    
    # Create results
    result1 = ProcessingResult(
        page_id=1,
        title="Page 1",
        success=True,
        processing_time_ms=100.5
    )
    
    result2 = ProcessingResult(
        page_id=2,
        title="Page 2", 
        success=False,
        error_message="Parsing failed",
        processing_time_ms=50.0
    )
    
    # Test batch stats
    stats = BatchProcessingStats()
    stats.add_result(result1)
    stats.add_result(result2)
    
    assert stats.total_pages == 2
    assert stats.successful == 1
    assert stats.failed == 1
    assert stats.get_success_rate() == 50.0
    assert stats.get_average_time_ms() == 75.25
    assert len(stats.error_messages) == 1
    
    print("  ✓ Processing Statistics tests passed")
    return True


def main():
    """Run all model tests."""
    print("=" * 60)
    print("Phase 2: Data Models - Validation Tests")
    print("=" * 60)
    
    tests = [
        ("LocationMetadata", test_location_metadata),
        ("HtmlExtractedData", test_html_extracted_data),
        ("WikipediaPage", test_wikipedia_page),
        ("PageSummary", test_page_summary),
        ("Processing Stats", test_processing_stats),
    ]
    
    all_passed = True
    for name, test_func in tests:
        try:
            passed = test_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"  ✗ {name} failed: {e}")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All Phase 2 model tests passed!")
    else:
        print("✗ Some tests failed - check errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
