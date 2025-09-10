"""
Pydantic models for rich listing functionality.

Clean data models with proper validation, no runtime type checking needed.
All models use Pydantic for validation and computed properties for display values.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

from real_estate_search.models import PropertyListing, WikipediaArticle


class NeighborhoodModel(BaseModel):
    """Neighborhood information with proper typing."""
    neighborhood_id: Optional[str] = Field(default=None)
    name: str = Field(default="Unknown")
    city: str = Field(default="")
    state: str = Field(default="")
    population: Optional[int] = Field(default=None)
    walkability_score: Optional[int] = Field(default=None)
    school_rating: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    amenities: List[str] = Field(default_factory=list)
    demographics: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('amenities', mode='before')
    @classmethod
    def ensure_amenities_list(cls, v):
        """Ensure amenities is always a list."""
        if v is None:
            return []
        try:
            return list(v)
        except (TypeError, ValueError):
            return []
    
    @field_validator('walkability_score')
    @classmethod
    def validate_walkability(cls, v):
        """Ensure walkability score is in valid range."""
        if v is not None:
            return max(0, min(100, v))
        return v
    
    @field_validator('school_rating')
    @classmethod
    def validate_school_rating(cls, v):
        """Ensure school rating is in valid range."""
        if v is not None:
            return max(0.0, min(5.0, v))
        return v
    
    @property
    def full_location(self) -> str:
        """Get full location string."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or ""
    
    @property
    def walkability_category(self) -> str:
        """Get walkability category based on score."""
        if not self.walkability_score:
            return "Unknown"
        if self.walkability_score >= 90:
            return "Walker's Paradise"
        elif self.walkability_score >= 70:
            return "Very Walkable"
        elif self.walkability_score >= 50:
            return "Somewhat Walkable"
        else:
            return "Car-Dependent"
    
    @property
    def school_rating_display(self) -> str:
        """Get formatted school rating."""
        if not self.school_rating:
            return "Not Available"
        return f"{self.school_rating:.1f}/5.0"


class RichListingModel(BaseModel):
    """
    Complete property listing with embedded neighborhood and Wikipedia data.
    
    This model represents the denormalized data structure returned from
    the property_relationships index, containing all related data in a
    single document.
    """
    
    # Core property data
    property_data: PropertyListing = Field(..., alias="property", description="Complete property information")
    
    # Related data (optional as they may not always be present)
    neighborhood: Optional[NeighborhoodModel] = Field(default=None, description="Neighborhood information")
    wikipedia_articles: List[WikipediaArticle] = Field(default_factory=list, description="Related Wikipedia articles")
    
    # Metadata
    retrieved_at: datetime = Field(default_factory=datetime.now, description="When data was retrieved")
    source_index: str = Field(default="property_relationships", description="Source Elasticsearch index")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    @property
    def has_neighborhood_data(self) -> bool:
        """Check if neighborhood data is available."""
        return self.neighborhood is not None
    
    @property
    def has_wikipedia_data(self) -> bool:
        """Check if Wikipedia articles are available."""
        return len(self.wikipedia_articles) > 0
    
    @property
    def wikipedia_count(self) -> int:
        """Get count of Wikipedia articles."""
        return len(self.wikipedia_articles)
    
    @property
    def data_completeness(self) -> Dict[str, bool]:
        """Get data completeness status."""
        return {
            "property": True,  # Always present
            "neighborhood": self.has_neighborhood_data,
            "wikipedia": self.has_wikipedia_data,
            "features": len(self.property_data.features) > 0,
            "description": bool(self.property_data.description),
            "images": len(self.property_data.images) > 0
        }
    
    @property
    def formatted_price(self) -> str:
        """Get formatted price with proper currency display."""
        price = self.property_data.price
        if not price or price == 0:
            return "Price Upon Request"
        if price >= 1000000:
            return f"${price/1000000:.2f}M"
        elif price >= 1000:
            return f"${price/1000:.0f}K"
        else:
            return f"${price:,.0f}"
    
    @property
    def formatted_address(self) -> str:
        """Get formatted full address."""
        return self.property_data.address.full_address
    
    @property
    def listing_age_days(self) -> int:
        """Calculate days since listing."""
        if self.property_data.list_date:
            delta = datetime.now() - self.property_data.list_date
            return delta.days
        return self.property_data.days_on_market or 0


class RichListingSearchResult(BaseModel):
    """
    Search result containing rich listing data.
    
    This model wraps the search results from Elasticsearch with
    additional metadata about the search execution.
    """
    
    # Search results
    listings: List[RichListingModel] = Field(default_factory=list, description="Retrieved listings")
    
    # Search metadata
    total_hits: int = Field(default=0, description="Total number of matching documents")
    returned_hits: int = Field(default=0, description="Number of documents returned")
    execution_time_ms: int = Field(default=0, description="Query execution time in milliseconds")
    
    # Query information
    query_dsl: Dict[str, Any] = Field(default_factory=dict, description="Elasticsearch query DSL")
    searched_indices: List[str] = Field(default_factory=lambda: ["property_relationships"], description="Indices searched")
    
    # Aggregations (optional)
    aggregations: Optional[Dict[str, Any]] = Field(default=None, description="Search aggregations if requested")
    
    model_config = ConfigDict(extra="ignore")
    
    @property
    def has_results(self) -> bool:
        """Check if search returned results."""
        return len(self.listings) > 0
    
    @property
    def first_listing(self) -> Optional[RichListingModel]:
        """Get first listing if available."""
        return self.listings[0] if self.listings else None


class RichListingDisplayConfig(BaseModel):
    """
    Configuration for rich listing display.
    
    This model controls how rich listings are displayed in the console
    and HTML output.
    """
    
    # Display options
    show_neighborhood: bool = Field(default=True, description="Show neighborhood panel")
    show_wikipedia: bool = Field(default=True, description="Show Wikipedia articles")
    show_features: bool = Field(default=True, description="Show property features")
    show_description: bool = Field(default=True, description="Show property description")
    show_details_table: bool = Field(default=True, description="Show property details table")
    
    # Wikipedia display settings
    max_wikipedia_articles: int = Field(default=3, ge=0, le=10, description="Maximum Wikipedia articles to display")
    wikipedia_summary_length: int = Field(default=150, ge=50, le=500, description="Wikipedia summary character limit")
    
    # Feature display settings
    max_features: int = Field(default=10, ge=0, le=50, description="Maximum features to display")
    
    # Description settings
    description_length: int = Field(default=500, ge=100, le=2000, description="Description character limit")
    
    # HTML generation
    generate_html: bool = Field(default=True, description="Generate HTML output")
    open_in_browser: bool = Field(default=True, description="Auto-open HTML in browser")
    html_output_dir: str = Field(default="real_estate_search/out_html", description="HTML output directory")
    
    # Console display
    use_rich_console: bool = Field(default=True, description="Use Rich console for display")
    console_width: Optional[int] = Field(default=None, ge=80, le=200, description="Console width override")
    
    model_config = ConfigDict(extra="ignore")
    
    @field_validator('html_output_dir')
    @classmethod
    def validate_output_dir(cls, v):
        """Ensure output directory is valid."""
        if not v:
            return "real_estate_search/out_html"
        return v