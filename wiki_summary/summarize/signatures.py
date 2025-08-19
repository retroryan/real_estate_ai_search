"""
DSPy signatures for Wikipedia summarization following best practices.
Uses modern type hints and comprehensive docstrings for better LLM guidance.
"""

import dspy
from typing import Optional


class ExtractPageSummaryWithContext(dspy.Signature):
    """Extract comprehensive location information and summary from a Wikipedia page.
    
    Analyze the provided Wikipedia article to identify the primary location being described,
    extract key topics, and generate a concise summary. Use the HTML location hints and 
    known path to validate and improve accuracy of location extraction. The goal is to 
    create structured data suitable for location-based search and analysis.
    
    Follow these steps:
    1. Identify the main location (city, county, state) from the article content
    2. Validate against the provided HTML hints and known path
    3. Extract 3-5 key topics that characterize this location
    4. Generate a 2-3 sentence summary highlighting the location's significance
    5. Assign confidence score based on clarity and agreement with hints
    """
    
    # Input fields with comprehensive descriptions
    page_title: str = dspy.InputField(
        desc="Title of the Wikipedia page being analyzed"
    )
    
    page_content: str = dspy.InputField(
        desc="Clean text content from Wikipedia page with scripts/styles removed, limited to ~4000 chars"
    )
    
    html_location_hints: str = dspy.InputField(
        desc="Pre-extracted location hints from HTML metadata, format: 'City: Name (confidence), County: Name (confidence), State: Name (confidence)'"
    )
    
    known_path: str = dspy.InputField(
        desc="Known hierarchical location path from database, format: 'country/state/county/city' or 'unknown'"
    )
    
    # Output fields with constraints and guidance
    short_summary: str = dspy.OutputField(
        desc="Concise 100-word summary capturing the essential characteristics and significance of this location. Focus on key facts and what makes this place notable.",
        prefix="Short Summary (100 words): "
    )
    
    long_summary: str = dspy.OutputField(
        desc="Comprehensive 500-word summary providing detailed information about this location. Include historical context, demographics, amenities, geography, and significance. Be thorough but focused.",
        prefix="Long Summary (500 words): "
    )
    
    key_topics: list[str] = dspy.OutputField(
        desc="List of 3-5 key topics/themes that characterize this location (e.g., 'tourism', 'technology hub', 'historic site')",
        prefix="Key topics: "
    )
    
    city: str = dspy.OutputField(
        desc="Extracted city name, or 'unknown' if not identifiable",
        prefix="City: "
    )
    
    county: str = dspy.OutputField(
        desc="Extracted county/district name, or 'unknown' if not identifiable",
        prefix="County: "
    )
    
    state: str = dspy.OutputField(
        desc="Extracted state/province name, or 'unknown' if not identifiable",
        prefix="State: "
    )
    
    confidence: float = dspy.OutputField(
        desc="Confidence score from 0.0 to 1.0 indicating extraction reliability. Consider: clarity of location mentions, agreement with hints, article focus on single location.",
        prefix="Confidence (0.0-1.0): "
    )


class ExtractLocationClassification(dspy.Signature):
    """Classify geographic entity type and determine if article is relevant to Utah/California.
    
    Analyze the Wikipedia article to:
    1. Identify what type of geographic entity this article describes
    2. Determine specific location details (name, state, county)
    3. Assess if this is relevant to Utah or California real estate
    
    Be flexible with location types - suggest the most accurate type even if uncommon.
    Examples of types: city, county, neighborhood, ski_resort, state_park, lake, mountain,
    recreation_area, trail, landmark, golf_course, marina, resort_town, etc.
    
    For compound entities (e.g., Deer Valley is both ski resort and neighborhood), 
    use the primary function or suggest a compound type like "ski_resort_and_neighborhood".
    
    CRITICAL: Articles NOT primarily about Utah or California locations should be flagged.
    """
    
    # Input fields
    page_title: str = dspy.InputField(
        desc="Title of the Wikipedia page"
    )
    
    page_content: str = dspy.InputField(
        desc="First 4000 characters of article content for analysis"
    )
    
    html_hints: Optional[str] = dspy.InputField(
        desc="Location hints from HTML: coordinates, infobox data, categories",
        default=None
    )
    
    # Location classification outputs
    location_name: str = dspy.OutputField(
        desc="Primary name of the geographic entity",
        prefix="Location Name: "
    )
    
    location_type: str = dspy.OutputField(
        desc="Type of entity (be specific and accurate, any type is acceptable)",
        prefix="Location Type: "
    )
    
    location_type_category: str = dspy.OutputField(
        desc="Broader category: administrative, natural_feature, recreation, infrastructure, or other",
        prefix="Category: "
    )
    
    state: str = dspy.OutputField(
        desc="Full state name (e.g., 'Utah' not 'UT'), or 'unknown' if unclear",
        prefix="State: "
    )
    
    county: str = dspy.OutputField(
        desc="County name if applicable, 'unknown' otherwise",
        prefix="County: "
    )
    
    # Relevance assessment
    is_utah_california: bool = dspy.OutputField(
        desc="True if primarily about a location in Utah or California",
        prefix="Is Utah/California: "
    )
    
    should_flag: bool = dspy.OutputField(
        desc="True if article should be flagged (not Utah/California relevant)",
        prefix="Should Flag: "
    )
    
    confidence: float = dspy.OutputField(
        desc="Confidence in classification (0.0-1.0)",
        prefix="Confidence: "
    )
    
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of classification and any ambiguities",
        prefix="Reasoning: "
    )