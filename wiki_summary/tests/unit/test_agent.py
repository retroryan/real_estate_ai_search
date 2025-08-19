#!/usr/bin/env python3
"""
Unit tests for DSPy agent - Phase 5 validation.
"""

import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv('.env')

from shared.llm_utils import setup_llm
from summarize.extract_agent import WikipediaExtractAgent
from summarize.models import WikipediaPage, HtmlExtractedData
from summarize.html_parser import extract_location_hints

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Sample HTML for testing
SAMPLE_HTML = """
<html>
<head><title>Park City, Utah</title></head>
<body>
<link rel="mw:PageProp/Category" href="./Category:Cities_in_Utah"/>
<link rel="mw:PageProp/Category" href="./Category:Summit_County,_Utah"/>
<table class="infobox">
<tr><th class="infobox-above">Park City</th></tr>
<tr><th class="infobox-label">State</th><td class="infobox-data">Utah</td></tr>
<tr><th class="infobox-label">County</th><td class="infobox-data">Summit County</td></tr>
</table>
<h1>Park City, Utah</h1>
<p>Park City is a city in Summit County, Utah, United States. It is considered to be part of the 
Wasatch Back. The city is 32 miles (51 km) southeast of downtown Salt Lake City and 20 miles (32 km) 
from Salt Lake City's east edge of Sugar House along Interstate 80. The population was 8,762 at the 
2020 census. On average, the tourist population greatly exceeds the number of permanent residents.</p>

<p>After a population decline following the shutdown of the area's mining industry, the city rebounded 
during the 1980s and 1990s through an expansion of its tourism business. The city currently brings in a 
yearly average of $529.8 million to the Utah Economy as a tourist hot spot, $80 million of which is 
attributed to the Sundance Film Festival. The city has two major ski resorts: Deer Valley Resort and 
Park City Mountain Resort (combined with Canyons Village at Park City) and one minor resort: Woodward 
Park City (an action sports training and fun center). Both Deer Valley and Park City Mountain Resort 
were the major locations for ski and snowboarding events at the 2002 Winter Olympics.</p>
</body>
</html>
"""


def test_agent_initialization():
    """Test agent initialization with DSPy."""
    print("Testing agent initialization...")
    
    try:
        # Initialize LLM
        llm = setup_llm()
        
        # Initialize agent
        agent = WikipediaExtractAgent(use_chain_of_thought=True)
        
        print("  ✓ Agent initialized with ChainOfThought")
        return True
        
    except Exception as e:
        print(f"  ✗ Initialization failed: {e}")
        return False


def test_basic_extraction():
    """Test basic extraction from a sample page."""
    print("Testing basic extraction...")
    
    try:
        # Initialize agent  
        llm = setup_llm()
        agent = WikipediaExtractAgent(use_chain_of_thought=True)  # Use CoT for better results
        
        # Create test page
        page = WikipediaPage(
            page_id=12345,
            title="Park City, Utah",
            html_content=SAMPLE_HTML,
            location_path="usa/utah/summit_county/park_city"
        )
        
        # Extract HTML hints
        html_hints = extract_location_hints(SAMPLE_HTML)
        html_extracted = HtmlExtractedData(
            city=html_hints.get('city'),
            county=html_hints.get('county'),
            state=html_hints.get('state'),
            confidence_scores=html_hints.get('confidence_scores', {})
        )
        
        # Run extraction
        summary = agent(page, html_extracted)
        
        # Validate results
        assert summary is not None
        assert summary.summary is not None
        assert len(summary.summary) > 10
        assert summary.key_topics is not None
        assert isinstance(summary.key_topics, list)
        
        print(f"  ✓ Extracted summary: {summary.summary[:80]}...")
        print(f"  ✓ Found {len(summary.key_topics)} topics: {summary.key_topics[:3]}")
        
        # Check location extraction
        if summary.llm_location:
            print(f"  ✓ LLM extracted location: {summary.llm_location.city}, {summary.llm_location.state}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_location_extraction():
    """Test location extraction specifically."""
    print("Testing location extraction...")
    
    try:
        # Initialize agent
        llm = setup_llm()
        agent = WikipediaExtractAgent()
        
        # Create test page with clear location info
        page = WikipediaPage(
            page_id=54321,
            title="Test Location Page",
            html_content=SAMPLE_HTML,
            location_path="usa/utah/summit_county"
        )
        
        # Extract without HTML hints to test pure LLM extraction
        summary = agent(page, None)
        
        # Check location extraction
        assert summary.llm_location is not None
        
        # Park City content should extract Utah
        if summary.llm_location.state:
            assert 'utah' in summary.llm_location.state.lower() or \
                   'ut' in summary.llm_location.state.lower()
            print(f"  ✓ Correctly extracted state: {summary.llm_location.state}")
        
        # Should identify Summit County
        if summary.llm_location.county:
            print(f"  ✓ Extracted county: {summary.llm_location.county}")
        
        # Should identify Park City
        if summary.llm_location.city:
            print(f"  ✓ Extracted city: {summary.llm_location.city}")
        
        # Check confidence scores
        if summary.llm_location.confidence_scores:
            avg_conf = sum(summary.llm_location.confidence_scores.values()) / len(summary.llm_location.confidence_scores)
            print(f"  ✓ Average confidence: {avg_conf:.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Location extraction failed: {e}")
        return False


def test_with_html_hints():
    """Test extraction with HTML hints for context."""
    print("Testing with HTML hints...")
    
    try:
        # Initialize agent
        llm = setup_llm()
        agent = WikipediaExtractAgent()
        
        # Create test page
        page = WikipediaPage(
            page_id=99999,
            title="Park City",
            html_content=SAMPLE_HTML,
            location_path="usa/utah/summit_county/park_city"
        )
        
        # Create HTML extracted data
        html_extracted = HtmlExtractedData(
            city="Park City",
            county="Summit",
            state="Utah",
            confidence_scores={'city': 0.9, 'county': 0.85, 'state': 0.95}
        )
        
        # Run extraction with hints
        summary = agent(page, html_extracted)
        
        # Check that HTML hints were used
        assert summary.html_location is not None
        assert summary.html_location.city == "Park City"
        
        # Check confidence boost when HTML and LLM agree
        if summary.llm_location.state and summary.html_location.state:
            if summary.llm_location.state.lower() == summary.html_location.state.lower():
                # Confidence should be boosted
                assert summary.llm_location.confidence_scores.get('state', 0) > 0.8
                print("  ✓ Confidence boosted when HTML and LLM agree")
        
        print(f"  ✓ Overall confidence: {summary.overall_confidence:.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ HTML hints test failed: {e}")
        return False


def main():
    """Run all agent tests."""
    print("=" * 60)
    print("Phase 5: DSPy Agent - Validation Tests")
    print("=" * 60)
    
    # Check for API key
    import os
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠ Warning: No API key found in environment")
        print("  Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        print("  Skipping LLM tests...")
        return 0
    
    tests = [
        ("Agent Initialization", test_agent_initialization),
        ("Basic Extraction", test_basic_extraction),
        ("Location Extraction", test_location_extraction),
        ("HTML Hints Integration", test_with_html_hints),
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
        print("✓ All Phase 5 agent tests passed!")
    else:
        print("✗ Some tests failed - check errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())