"""
Pydantic models for Wikipedia summarization system.
Provides type safety and validation for all data structures.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class ExtractionMethod(str, Enum):
    """Enumeration of extraction methods."""
    HTML_PARSER = "html_parser"
    LLM_EXTRACTION = "llm_extraction"
    COMBINED = "combined"


class LocationMetadata(BaseModel):
    """
    Location metadata extracted from Wikipedia pages.
    Can be used for both HTML and LLM extraction results.
    """
    city: Optional[str] = Field(None, description="City name if identified")
    county: Optional[str] = Field(None, description="County name if identified")
    state: Optional[str] = Field(None, description="State name if identified")
    country: Optional[str] = Field(default="USA", description="Country name")
    coordinates: Optional[str] = Field(None, description="Geographic coordinates if found")
    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each field (0.0-1.0)"
    )
    
    @field_validator('confidence_scores')
    @classmethod
    def validate_confidence_scores(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure confidence scores are between 0 and 1."""
        for key, score in v.items():
            if not 0 <= score <= 1:
                raise ValueError(f"Confidence score for {key} must be between 0 and 1")
        return v
    
    def get_confidence(self, field: str) -> float:
        """Get confidence score for a specific field."""
        return self.confidence_scores.get(field, 0.0)
    
    def to_best_guess(self) -> dict[str, Optional[str]]:
        """Return best guess for each field based on confidence."""
        return {
            'city': self.city if self.get_confidence('city') > 0.5 else None,
            'county': self.county if self.get_confidence('county') > 0.5 else None,
            'state': self.state if self.get_confidence('state') > 0.5 else None,
        }


class HtmlExtractedData(BaseModel):
    """
    Data extracted directly from HTML structure (non-LLM).
    Represents deterministic extraction from Wikipedia markup.
    """
    city: Optional[str] = Field(None, description="City extracted from HTML")
    county: Optional[str] = Field(None, description="County extracted from HTML")
    state: Optional[str] = Field(None, description="State extracted from HTML")
    coordinates: Optional[str] = Field(None, description="Coordinates from geo tags")
    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence based on extraction source"
    )
    categories_found: list[str] = Field(
        default_factory=list,
        description="Wikipedia categories found in page"
    )
    extraction_method: str = Field(
        default="html_parser",
        description="Method used for extraction"
    )
    infobox_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data from infobox"
    )
    
    @field_validator('categories_found')
    @classmethod
    def limit_categories(cls, v: list[str]) -> list[str]:
        """Limit stored categories to prevent excessive storage."""
        return v[:20]  # Keep only first 20 categories
    
    def has_high_confidence(self) -> bool:
        """Check if any extraction has high confidence (>0.8)."""
        return any(score > 0.8 for score in self.confidence_scores.values())


class PageSummary(BaseModel):
    """
    Combined summary from both HTML and LLM extraction.
    This is the main output model for the summarization system.
    """
    # Identifiers
    page_id: int = Field(..., description="Wikipedia page ID")
    article_id: Optional[int] = Field(None, description="Database article ID")
    title: str = Field(..., description="Page title")
    
    # LLM-generated content
    short_summary: str = Field(..., min_length=1, description="Concise 100-word summary")
    long_summary: str = Field(..., min_length=1, description="Comprehensive 500-word summary")
    key_topics: list[str] = Field(
        default_factory=list,
        description="Key topics identified by LLM"
    )
    llm_location: LocationMetadata = Field(
        ...,
        description="Location data extracted by LLM"
    )
    
    # HTML-extracted content
    html_location: HtmlExtractedData = Field(
        ...,
        description="Location data from HTML parser"
    )
    
    # Combined/meta fields
    best_location: LocationMetadata = Field(
        None,
        description="Best guess combining both methods"
    )
    overall_confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Overall confidence in extraction"
    )
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="Processing timestamp"
    )
    
    @field_validator('key_topics')
    @classmethod
    def limit_topics(cls, v: list[str]) -> list[str]:
        """Limit number of key topics."""
        return v[:10]  # Maximum 10 topics
    
    @field_validator('short_summary', 'long_summary')
    @classmethod
    def clean_summary(cls, v: str) -> str:
        """Clean and validate summary text."""
        # Remove excessive whitespace
        v = ' '.join(v.split())
        # Ensure it ends with proper punctuation
        if v and v[-1] not in '.!?':
            v += '.'
        return v
    
    def compute_best_location(self) -> LocationMetadata:
        """
        Compute best location by combining HTML and LLM extraction.
        Prefers higher confidence scores.
        """
        best = LocationMetadata()
        
        # Compare each field and take the one with higher confidence
        for field in ['city', 'county', 'state']:
            html_conf = self.html_location.confidence_scores.get(field, 0)
            llm_conf = self.llm_location.confidence_scores.get(field, 0)
            
            if html_conf > llm_conf:
                setattr(best, field, getattr(self.html_location, field))
                best.confidence_scores[field] = html_conf
            else:
                setattr(best, field, getattr(self.llm_location, field))
                best.confidence_scores[field] = llm_conf
        
        # Coordinates usually come from HTML
        if self.html_location.coordinates:
            best.coordinates = self.html_location.coordinates
        
        return best
    
    def model_post_init(self, __context):
        """Compute best location after initialization."""
        if not self.best_location:
            self.best_location = self.compute_best_location()
        
        # Update overall confidence
        all_scores = (
            list(self.html_location.confidence_scores.values()) +
            list(self.llm_location.confidence_scores.values())
        )
        if all_scores:
            self.overall_confidence = sum(all_scores) / len(all_scores)


class WikipediaPage(BaseModel):
    """
    Input model for Wikipedia pages to be processed.
    """
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Page title")
    html_content: str = Field(..., description="Raw HTML content")
    location_path: str = Field(
        ...,
        description="Location path from database (e.g., 'usa/california/san_francisco')"
    )
    url: Optional[str] = Field(None, description="Wikipedia URL if available")
    html_file_path: Optional[str] = Field(
        None,
        description="Path to HTML file on disk"
    )
    
    @field_validator('html_content')
    @classmethod
    def validate_html_content(cls, v: str) -> str:
        """Ensure HTML content is not empty."""
        if not v or len(v.strip()) < 100:
            raise ValueError("HTML content is too short or empty")
        return v
    
    @field_validator('location_path')
    @classmethod
    def validate_location_path(cls, v: str) -> str:
        """Validate location path format."""
        if not v:
            raise ValueError("Location path cannot be empty")
        # Should have at least country/state format
        parts = v.split('/')
        if len(parts) < 2:
            raise ValueError(f"Invalid location path format: {v}")
        return v
    
    def get_location_parts(self) -> dict[str, str]:
        """Parse location path into components."""
        parts = self.location_path.split('/')
        result = {}
        
        # Standard format: country/state/county/city
        if len(parts) > 0:
            result['country'] = parts[0]
        if len(parts) > 1:
            result['state'] = parts[1]
        if len(parts) > 2:
            result['county_or_city'] = parts[2]
        if len(parts) > 3:
            result['city'] = parts[3]
            
        return result


class ProcessingResult(BaseModel):
    """
    Result of processing a single Wikipedia page.
    Used for tracking and reporting.
    """
    page_id: int
    title: str
    success: bool
    error_message: Optional[str] = None
    summary: Optional[PageSummary] = None
    processing_time_ms: float = Field(0.0, ge=0.0)
    
    def to_log_entry(self) -> str:
        """Format as a log entry."""
        status = "SUCCESS" if self.success else "FAILED"
        msg = f"[{status}] Page {self.page_id}: {self.title}"
        if self.error_message:
            msg += f" - Error: {self.error_message}"
        if self.processing_time_ms > 0:
            msg += f" ({self.processing_time_ms:.1f}ms)"
        return msg


class BatchProcessingStats(BaseModel):
    """
    Statistics for a batch of processed pages.
    """
    total_pages: int = Field(0, ge=0)
    successful: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    total_time_ms: float = Field(0.0, ge=0.0)
    error_messages: list[str] = Field(default_factory=list)
    
    def add_result(self, result: ProcessingResult):
        """Add a processing result to statistics."""
        self.total_pages += 1
        if result.success:
            self.successful += 1
        else:
            self.failed += 1
            if result.error_message:
                self.error_messages.append(result.error_message)
        self.total_time_ms += result.processing_time_ms
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.successful / self.total_pages) * 100
    
    def get_average_time_ms(self) -> float:
        """Calculate average processing time."""
        if self.total_pages == 0:
            return 0.0
        return self.total_time_ms / self.total_pages
