"""
DSPy extraction agent for Wikipedia summarization.
Simplified to trust DSPy's type handling and validation with optional caching.
"""

import dspy
import logging
from typing import Optional

from .models import (
    WikipediaPage,
    PageSummary,
    LocationMetadata,
    HtmlExtractedData
)
from .signatures import ExtractPageSummaryWithContext
from .location_classifier import LocationClassificationCoT
from .html_parser import clean_html_for_llm
from .cache import SummaryCache

logger = logging.getLogger(__name__)


class WikipediaExtractAgent(dspy.Module):
    """
    Agent for extracting summaries from Wikipedia pages using DSPy.
    Trusts DSPy's type system for clean, simple implementation with caching.
    """
    
    def __init__(self, use_chain_of_thought: bool = True, use_cache: bool = True, use_location_classifier: bool = True):
        """
        Initialize the extraction agent.
        
        Args:
            use_chain_of_thought: Use CoT for better reasoning (default: True)
            use_cache: Enable file-based caching for cost efficiency (default: True)
            use_location_classifier: Use flexible location classification (default: True)
        """
        super().__init__()
        
        # Use ChainOfThought for better reasoning, or simple Predict
        if use_chain_of_thought:
            self.extract = dspy.ChainOfThought(ExtractPageSummaryWithContext)
        else:
            self.extract = dspy.Predict(ExtractPageSummaryWithContext)
        
        # Initialize location classifier if enabled
        if use_location_classifier:
            self.location_classifier = LocationClassificationCoT(use_chain_of_thought=True)
        else:
            self.location_classifier = None
        
        # Initialize cache if enabled
        self.cache = SummaryCache() if use_cache else None
        
        logger.info(f"Initialized WikipediaExtractAgent (CoT={use_chain_of_thought}, cache={use_cache}, classifier={use_location_classifier})")
    
    def forward(self, page: WikipediaPage, html_extracted: Optional[HtmlExtractedData] = None) -> PageSummary:
        """
        Process a Wikipedia page to extract summary and location data.
        
        Args:
            page: The Wikipedia page to process
            html_extracted: Pre-extracted HTML data for context
        
        Returns:
            PageSummary with all extracted information
        """
        # Prepare inputs
        clean_text = clean_html_for_llm(page.html_content, max_length=4000)
        html_hints = self._format_html_hints(html_extracted)
        
        # Check cache if enabled
        if self.cache:
            cached = self.cache.get(page.page_id, clean_text)
            if cached:
                logger.info(f"Using cached summary for page {page.page_id}")
                return self._reconstruct_from_cache(page, cached, html_extracted)
        
        # Single extraction call with enhanced error handling
        logger.debug(f"Starting DSPy extraction for page {page.page_id}: {page.title}")
        logger.debug(f"Content length: {len(clean_text)} chars, HTML hints: {len(html_hints)} chars")
        
        try:
            result = self.extract(
                page_title=page.title,
                page_content=clean_text,
                html_location_hints=html_hints,
                known_path=page.location_path or "unknown"
            )
            logger.debug(f"DSPy extraction successful for page {page.page_id}")
            
        except Exception as e:
            error_msg = str(e)
            if 'dspy' in error_msg.lower() or hasattr(e, '__module__') and e.__module__ and 'dspy' in e.__module__:
                logger.error(f"DSPy extraction failed for page {page.page_id} ({page.title}): {e}")
            else:
                logger.error(f"Processing error in extraction for page {page.page_id} ({page.title}): {type(e).__name__}: {e}")
            raise
        
        # Build structured response
        summary = self._build_page_summary(page, result, html_extracted)
        
        # Cache if enabled
        if self.cache:
            self._cache_summary(page.page_id, clean_text, summary)
        
        return summary
    
    def _format_html_hints(self, html_extracted: Optional[HtmlExtractedData]) -> str:
        """Format HTML extraction data as simple string for LLM context."""
        if not html_extracted:
            return "No HTML location hints available"
        
        hints = []
        if html_extracted.city:
            conf = html_extracted.confidence_scores.get('city', 0.0)
            hints.append(f"City: {html_extracted.city} ({conf:.2f})")
        if html_extracted.county:
            conf = html_extracted.confidence_scores.get('county', 0.0)
            hints.append(f"County: {html_extracted.county} ({conf:.2f})")
        if html_extracted.state:
            conf = html_extracted.confidence_scores.get('state', 0.0)
            hints.append(f"State: {html_extracted.state} ({conf:.2f})")
        if html_extracted.coordinates:
            hints.append(f"Coordinates: {html_extracted.coordinates}")
        
        return ", ".join(hints) if hints else "No location hints found"
    
    def _build_page_summary(self, page: WikipediaPage, result: dspy.Prediction, 
                           html_extracted: Optional[HtmlExtractedData]) -> PageSummary:
        """Build PageSummary from DSPy result, trusting its type handling."""
        
        logger.debug(f"Building summary from DSPy result for page {page.page_id}")
        
        # Validate DSPy result has required fields
        required_fields = ['city', 'county', 'state', 'short_summary', 'long_summary', 'key_topics']
        missing_fields = [field for field in required_fields if not hasattr(result, field)]
        if missing_fields:
            logger.warning(f"DSPy result missing fields for page {page.page_id}: {missing_fields}")
        
        # DSPy handles type conversion - we just map to our model
        # Handle 'unknown' as None for cleaner data
        city = None if getattr(result, 'city', None) == 'unknown' else getattr(result, 'city', None)
        county = None if getattr(result, 'county', None) == 'unknown' else getattr(result, 'county', None)  
        state = None if getattr(result, 'state', None) == 'unknown' else getattr(result, 'state', None)
        
        # Get confidence score safely (handle None cases)
        confidence = getattr(result, 'confidence', None)
        if confidence is None:
            confidence = 0.5  # Default fallback
        
        # Build location metadata with confidence scores
        llm_location = LocationMetadata(
            city=city,
            county=county,
            state=state,
            country="USA",  # Default for this project
            confidence_scores={
                'city': confidence if city else 0.0,
                'county': confidence if county else 0.0,
                'state': confidence if state else 0.0,
                'overall': confidence
            }
        )
        
        # Create final summary with all extracted data
        try:
            summary = PageSummary(
                page_id=page.page_id,
                title=page.title,
                short_summary=self._clean_summary(getattr(result, 'short_summary', None) or ''),
                long_summary=self._clean_summary(getattr(result, 'long_summary', None) or ''),
                key_topics=(getattr(result, 'key_topics', None) or [])[:5],  # Handle None case and limit to 5 topics
                llm_location=llm_location,
                html_location=html_extracted or HtmlExtractedData(),
                overall_confidence=confidence
            )
            logger.debug(f"Successfully built PageSummary for page {page.page_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to build PageSummary for page {page.page_id}: {type(e).__name__}: {e}")
            logger.error(f"DSPy result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
            raise
    
    def _clean_summary(self, summary: str) -> str:
        """Minimal summary cleaning for consistency."""
        if not summary or summary == "None" or summary == "null":
            return "No summary available for this page."
        
        # Remove excess whitespace
        summary = ' '.join(summary.split())
        
        # If still empty after cleaning
        if not summary:
            return "No summary available for this page."
        
        # Ensure sentence ending
        if summary[-1] not in '.!?':
            summary += '.'
        
        return summary
    
    def _cache_summary(self, page_id: int, content: str, summary: PageSummary):
        """Cache the summary for future use."""
        cache_data = {
            'short_summary': summary.short_summary,
            'long_summary': summary.long_summary,
            'key_topics': summary.key_topics,
            'city': summary.llm_location.city,
            'county': summary.llm_location.county,
            'state': summary.llm_location.state,
            'confidence': summary.overall_confidence
        }
        self.cache.set(page_id, content, cache_data)
    
    def _reconstruct_from_cache(self, page: WikipediaPage, cached: dict, 
                               html_extracted: Optional[HtmlExtractedData]) -> PageSummary:
        """Reconstruct PageSummary from cached data."""
        llm_location = LocationMetadata(
            city=cached.get('city'),
            county=cached.get('county'),
            state=cached.get('state'),
            country="USA",
            confidence_scores={'overall': cached.get('confidence', 0.5)}
        )
        
        return PageSummary(
            page_id=page.page_id,
            title=page.title,
            short_summary=cached.get('short_summary', ''),
            long_summary=cached.get('long_summary', ''),
            key_topics=cached.get('key_topics', []),
            llm_location=llm_location,
            html_location=html_extracted or HtmlExtractedData(),
            overall_confidence=cached.get('confidence', 0.5)
        )