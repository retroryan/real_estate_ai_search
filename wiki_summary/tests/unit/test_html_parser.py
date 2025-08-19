#!/usr/bin/env python3
"""
Unit tests for HTML parser - Phase 3 validation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from summarize.html_parser import (
    clean_html_for_llm,
    extract_location_hints,
    correlate_with_categories,
    extract_infobox_data,
    extract_coordinates_detailed
)


# Sample HTML snippets for testing
SAMPLE_HTML_SF = """
<html>
<head><title>San Francisco</title></head>
<body>
<link rel="mw:PageProp/Category" href="./Category:Cities_in_California"/>
<link rel="mw:PageProp/Category" href="./Category:San_Francisco_County,_California"/>
<table class="infobox">
<tr><th class="infobox-above">San Francisco</th></tr>
<tr><th class="infobox-label">State</th><td class="infobox-data">California</td></tr>
<tr><th class="infobox-label">County</th><td class="infobox-data">San Francisco County</td></tr>
</table>
<p>San Francisco is a city in California, United States.</p>
<span class="geo">37.7749; -122.4194</span>
</body>
</html>
"""

SAMPLE_HTML_UTAH = """
<html>
<head><title>Park City, Utah</title></head>
<body>
<link rel="mw:PageProp/Category" href="./Category:Cities_in_Utah"/>
<link rel="mw:PageProp/Category" href="./Category:Summit_County,_Utah"/>
<div class="fn org">Park City</div>
<p>Park City is a city in Summit County, Utah.</p>
<a href="https://geohack.toolforge.org/geohack.php?params=40.6461_N_111.4980_W">Coordinates</a>
<script>console.log('test');</script>
<style>.test { color: red; }</style>
<div class="navbox">Navigation stuff</div>
<div class="reflist">References here</div>
</body>
</html>
"""


def test_clean_html_for_llm():
    """Test HTML cleaning for LLM processing."""
    print("Testing clean_html_for_llm...")
    
    # Clean the HTML
    clean_text = clean_html_for_llm(SAMPLE_HTML_UTAH, max_length=500)
    
    # Check that unwanted elements are removed
    assert 'console.log' not in clean_text  # Script removed
    assert 'color: red' not in clean_text  # Style removed
    assert 'Navigation stuff' not in clean_text  # Navbox removed
    assert 'References here' not in clean_text  # Reflist removed
    
    # Check that content is preserved
    assert 'Park City' in clean_text
    assert 'Summit County' in clean_text
    
    print(f"  ✓ Cleaned text length: {len(clean_text)} chars")
    print(f"  ✓ Sample: {clean_text[:100]}...")
    
    return True


def test_extract_location_hints():
    """Test location extraction from HTML."""
    print("Testing extract_location_hints...")
    
    # Test San Francisco HTML
    hints_sf = extract_location_hints(SAMPLE_HTML_SF)
    assert hints_sf['state'] == 'California'
    assert hints_sf['county'] == 'San Francisco'
    assert hints_sf['city'] == 'San Francisco'
    assert hints_sf['coordinates'] == '37.7749; -122.4194'
    assert hints_sf['confidence_scores']['state'] >= 0.9
    print("  ✓ San Francisco extraction correct")
    
    # Test Utah HTML
    hints_utah = extract_location_hints(SAMPLE_HTML_UTAH)
    assert hints_utah['state'] == 'Utah'
    assert hints_utah['county'] == 'Summit'
    assert hints_utah['city'] == 'Park City'
    assert hints_utah['coordinates'] is not None
    print("  ✓ Park City extraction correct")
    
    return True


def test_extract_infobox():
    """Test infobox data extraction."""
    print("Testing extract_infobox_data...")
    
    infobox_data = extract_infobox_data(SAMPLE_HTML_SF)
    
    assert infobox_data['title'] == 'San Francisco'
    assert infobox_data['state'] == 'California'
    assert infobox_data['county'] == 'San Francisco County'
    
    print(f"  ✓ Extracted {len(infobox_data)} infobox fields")
    
    return True


def test_correlate_categories():
    """Test category correlation."""
    print("Testing correlate_with_categories...")
    
    existing_cats = ['Geography of California', 'Tourist attractions in San Francisco']
    correlations = correlate_with_categories(SAMPLE_HTML_SF, existing_cats)
    
    assert len(correlations['state_categories']) > 0
    assert any('California' in cat for cat in correlations['state_categories'])
    assert len(correlations['county_categories']) > 0
    
    print(f"  ✓ Found {len(correlations['state_categories'])} state categories")
    print(f"  ✓ Found {len(correlations['county_categories'])} county categories")
    
    return True


def test_coordinate_extraction():
    """Test detailed coordinate extraction."""
    print("Testing extract_coordinates_detailed...")
    
    # Test geo microformat
    coords_sf = extract_coordinates_detailed(SAMPLE_HTML_SF)
    assert coords_sf is not None
    assert coords_sf['latitude'] == 37.7749
    assert coords_sf['longitude'] == -122.4194
    assert coords_sf['source'] == 'geo_microformat'
    print("  ✓ Geo microformat extraction works")
    
    # Test geohack link (Utah example)
    coords_utah = extract_coordinates_detailed(SAMPLE_HTML_UTAH)
    assert coords_utah is not None
    assert coords_utah['source'] == 'geohack_link'
    assert coords_utah['latitude'] == 40.6461
    assert coords_utah['longitude'] == -111.4980
    print("  ✓ Geohack link extraction works")
    
    return True


def test_with_real_file():
    """Test with a real Wikipedia file if available."""
    print("Testing with real Wikipedia file...")
    
    test_file = Path("../data/wikipedia/usa/california/san_francisco_county/san_francisco/pages/27169_d9e023c0.html")
    
    if test_file.exists():
        with open(test_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Test cleaning
        clean = clean_html_for_llm(html, max_length=1000)
        assert len(clean) > 100
        assert len(clean) <= 1000
        print(f"  ✓ Cleaned real file to {len(clean)} chars")
        
        # Test extraction
        hints = extract_location_hints(html)
        print(f"  ✓ Extracted location: {hints.get('city')}, {hints.get('state')}")
        
        return True
    else:
        print("  ⚠ Real file not found, skipping")
        return True


def main():
    """Run all HTML parser tests."""
    print("=" * 60)
    print("Phase 3: HTML Parser - Validation Tests")
    print("=" * 60)
    
    tests = [
        ("HTML Cleaning", test_clean_html_for_llm),
        ("Location Extraction", test_extract_location_hints),
        ("Infobox Extraction", test_extract_infobox),
        ("Category Correlation", test_correlate_categories),
        ("Coordinate Extraction", test_coordinate_extraction),
        ("Real File Test", test_with_real_file),
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
        print("✓ All Phase 3 HTML parser tests passed!")
    else:
        print("✗ Some tests failed - check errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())