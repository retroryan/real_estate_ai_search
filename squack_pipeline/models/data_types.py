"""Pydantic models for data types used throughout the pipeline."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationInfo, ValidationError


class PipelineMetrics(BaseModel):
    """Pipeline execution metrics."""
    
    model_config = ConfigDict(extra='forbid')
    
    bronze_records: int = Field(default=0, ge=0, description="Number of bronze tier records")
    silver_records: int = Field(default=0, ge=0, description="Number of silver tier records")
    gold_records: int = Field(default=0, ge=0, description="Number of gold tier records")
    elasticsearch_records: int = Field(default=0, ge=0, description="Number of records written to Elasticsearch")
    pipeline_duration: float = Field(default=0.0, ge=0.0, description="Total pipeline duration in seconds")
    entity_metrics: Dict[str, 'EntityMetrics'] = Field(default_factory=dict, description="Per-entity metrics")
    total_records: int = Field(default=0, ge=0, description="Total records processed")
    total_embeddings: int = Field(default=0, ge=0, description="Total embeddings generated")


class ValidationResult(BaseModel):
    """Result of validating records through Pydantic models."""
    
    model_config = ConfigDict(extra='forbid')
    
    successful_records: int = Field(default=0, ge=0, description="Number of successfully validated records")
    failed_records: int = Field(default=0, ge=0, description="Number of records that failed validation")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation error messages")
    
    def add_error(self, error: ValidationError, row_index: Optional[int] = None) -> None:
        """Add a validation error to the results."""
        error_msg = f"Row {row_index}: {str(error)}" if row_index is not None else str(error)
        self.validation_errors.append(error_msg)
        self.failed_records += 1
    
    def add_success(self) -> None:
        """Record a successful validation."""
        self.successful_records += 1
    
    @property
    def total_records(self) -> int:
        """Total records processed."""
        return self.successful_records + self.failed_records
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_records == 0:
            return 100.0
        return (self.successful_records / self.total_records) * 100.0
    
    def get_error_summary(self) -> str:
        """Get a summary of validation errors."""
        if not self.validation_errors:
            return "No validation errors"
        
        # Group similar errors
        error_counts = {}
        for error in self.validation_errors:
            # Extract error type from the message
            if ": " in error:
                error_type = error.split(": ", 1)[1].split("(")[0].strip()
            else:
                error_type = error[:50] + "..." if len(error) > 50 else error
            
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        summary_lines = [f"  - {error_type}: {count} occurrences" 
                        for error_type, count in sorted(error_counts.items())]
        
        return f"Validation errors ({self.failed_records} total):\n" + "\n".join(summary_lines)


class EntityMetrics(BaseModel):
    """Metrics for a single entity type."""
    
    model_config = ConfigDict(extra='forbid')
    
    bronze_records: int = Field(default=0, ge=0)
    silver_records: int = Field(default=0, ge=0)
    gold_records: int = Field(default=0, ge=0)
    elasticsearch_records: int = Field(default=0, ge=0)
    embeddings_generated: int = Field(default=0, ge=0, description="Number of embeddings generated")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")


class Coordinates(BaseModel):
    """Geographic coordinates."""
    
    model_config = ConfigDict(extra='forbid')
    
    latitude: float = Field(ge=-90, le=90, description="Latitude")
    longitude: float = Field(ge=-180, le=180, description="Longitude")


class Address(BaseModel):
    """Property address information."""
    
    model_config = ConfigDict(extra='forbid')
    
    street: str = Field(description="Street address")
    city: str = Field(description="City name")
    county: Optional[str] = Field(default=None, description="County name")
    state: str = Field(description="State code")
    zip: str = Field(description="ZIP code")


class PriceHistoryEntry(BaseModel):
    """Single price history entry."""
    
    model_config = ConfigDict(extra='forbid')
    
    date: str = Field(description="Date of price change")
    price: int = Field(gt=0, description="Price at this date")
    event: Optional[str] = Field(default=None, description="Event type (listed, sold, etc.)")


class PropertyDetails(BaseModel):
    """Detailed property information."""
    
    model_config = ConfigDict(extra='forbid')
    
    square_feet: int = Field(gt=0, description="Square footage")
    bedrooms: int = Field(ge=0, description="Number of bedrooms")
    bathrooms: float = Field(ge=0, description="Number of bathrooms")
    property_type: str = Field(description="Type of property")
    year_built: Optional[int] = Field(default=None, ge=1800, le=2100, description="Year built")
    lot_size: Optional[float] = Field(default=None, ge=0, description="Lot size in acres")
    stories: Optional[int] = Field(default=None, ge=1, description="Number of stories")
    garage_spaces: Optional[int] = Field(default=None, ge=0, description="Number of garage spaces")


class PropertyRecord(BaseModel):
    """Property data record."""
    
    model_config = ConfigDict(extra='allow')  # Allow extra fields for flexibility
    
    listing_id: str = Field(description="Unique listing identifier")
    neighborhood_id: Optional[str] = Field(default=None, description="Neighborhood identifier")
    address: Address = Field(description="Property address")
    coordinates: Coordinates = Field(description="Geographic coordinates")
    property_details: PropertyDetails = Field(description="Property details")
    listing_price: int = Field(gt=0, description="Listing price in dollars")
    price_per_sqft: Optional[float] = Field(default=None, ge=0, description="Price per square foot")
    description: str = Field(description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    listing_date: str = Field(description="Listing date")
    days_on_market: int = Field(ge=0, description="Days on market")
    virtual_tour_url: Optional[str] = Field(default=None, description="Virtual tour URL")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    price_history: List[PriceHistoryEntry] = Field(default_factory=list, description="Price history")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(default=None, description="Property embedding vector")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model used")
    embedding_dimension: Optional[int] = Field(default=None, ge=1, le=4096, description="Embedding vector dimension")
    
    @field_validator('price_per_sqft')
    @classmethod
    def validate_price_per_sqft(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        """Validate price_per_sqft consistency with listing_price and square_feet."""
        if v is None or not info.data:
            return v
            
        listing_price = info.data.get('listing_price')
        property_details = info.data.get('property_details')
        
        if (listing_price and 
            property_details and 
            hasattr(property_details, 'square_feet') and 
            property_details.square_feet and 
            property_details.square_feet > 0):
            
            calculated = listing_price / property_details.square_feet
            if abs(v - calculated) > 1.0:  # Allow $1 tolerance for rounding
                raise ValueError(
                    f"price_per_sqft ({v}) doesn't match calculated value ({calculated:.2f}) "
                    f"based on listing_price ({listing_price}) / square_feet ({property_details.square_feet})"
                )
        
        return v
    
    @field_validator('embedding_dimension')
    @classmethod
    def validate_embedding_dimension(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        """Validate embedding_dimension matches actual embedding length."""
        if v is None or not info.data:
            return v
            
        embedding = info.data.get('embedding')
        if embedding and len(embedding) != v:
            raise ValueError(f"embedding_dimension ({v}) doesn't match embedding length ({len(embedding)})")
        
        return v
    
    @field_validator('days_on_market')
    @classmethod
    def validate_days_on_market(cls, v: int, info: ValidationInfo) -> int:
        """Validate days_on_market is reasonable."""
        if v > 3650:  # 10 years
            raise ValueError(f"days_on_market ({v}) seems unreasonably high (>10 years)")
        return v


class GeoBoundary(BaseModel):
    """Geographic boundary definition."""
    
    model_config = ConfigDict(extra='forbid')
    
    north: float = Field(ge=-90, le=90, description="Northern boundary")
    south: float = Field(ge=-90, le=90, description="Southern boundary")
    east: float = Field(ge=-180, le=180, description="Eastern boundary")
    west: float = Field(ge=-180, le=180, description="Western boundary")
    polygon: Optional[List[List[float]]] = Field(default=None, description="Polygon coordinates")


class Demographics(BaseModel):
    """Demographic information."""
    
    model_config = ConfigDict(extra='forbid')
    
    population: Optional[int] = Field(default=None, ge=0, description="Total population")
    median_age: Optional[float] = Field(default=None, ge=0, le=150, description="Median age")
    median_income: Optional[float] = Field(default=None, ge=0, description="Median household income")
    households: Optional[int] = Field(default=None, ge=0, description="Number of households")
    education_bachelors_plus: Optional[float] = Field(default=None, ge=0, le=100, description="Percentage with bachelor's degree or higher")
    employment_rate: Optional[float] = Field(default=None, ge=0, le=100, description="Employment rate percentage")


class NeighborhoodStatistics(BaseModel):
    """Neighborhood statistics."""
    
    model_config = ConfigDict(extra='forbid')
    
    median_home_price: Optional[float] = Field(default=None, ge=0)
    average_home_size: Optional[float] = Field(default=None, ge=0)
    walkability_score: Optional[int] = Field(default=None, ge=0, le=100)
    transit_score: Optional[int] = Field(default=None, ge=0, le=100)
    bike_score: Optional[int] = Field(default=None, ge=0, le=100)
    crime_rate: Optional[float] = Field(default=None, ge=0)
    school_rating: Optional[float] = Field(default=None, ge=0, le=10)


class NeighborhoodRecord(BaseModel):
    """Neighborhood data record."""
    
    model_config = ConfigDict(extra='allow')
    
    neighborhood_id: str = Field(description="Unique neighborhood identifier")
    name: str = Field(description="Neighborhood name")
    city: str = Field(description="City name")
    state: str = Field(description="State code")
    coordinates: Optional[Coordinates] = Field(default=None, description="Center coordinates")
    description: Optional[str] = Field(default=None, description="Neighborhood description")
    characteristics: List[str] = Field(default_factory=list, description="Neighborhood characteristics")
    amenities: List[str] = Field(default_factory=list, description="Nearby amenities")
    statistics: Optional[NeighborhoodStatistics] = Field(default=None, description="Statistical data")
    boundaries: Optional[GeoBoundary] = Field(default=None, description="Geographic boundaries")
    demographics: Optional[Demographics] = Field(default=None, description="Demographic information")


class InfoboxData(BaseModel):
    """Wikipedia infobox structured data."""
    
    model_config = ConfigDict(extra='allow')  # Allow extra fields since infobox can have various fields
    
    name: Optional[str] = Field(default=None, description="Name field")
    location: Optional[str] = Field(default=None, description="Location field")
    established: Optional[str] = Field(default=None, description="Establishment date")
    population: Optional[str] = Field(default=None, description="Population")
    area: Optional[str] = Field(default=None, description="Area")
    elevation: Optional[str] = Field(default=None, description="Elevation")
    timezone: Optional[str] = Field(default=None, description="Timezone")
    website: Optional[str] = Field(default=None, description="Official website")


class WikipediaRecord(BaseModel):
    """Wikipedia article record."""
    
    model_config = ConfigDict(extra='allow')
    
    page_id: int = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    summary: Optional[str] = Field(default=None, description="Article summary")
    text: Optional[str] = Field(default=None, description="Full article text")
    categories: List[str] = Field(default_factory=list, description="Article categories")
    keywords: List[str] = Field(default_factory=list, description="Article keywords")
    sections: List[str] = Field(default_factory=list, description="Article sections")
    references: List[str] = Field(default_factory=list, description="Reference URLs")
    related_articles: List[str] = Field(default_factory=list, description="Related article titles")
    coordinates: Optional[Coordinates] = Field(default=None, description="Geographic coordinates if applicable")
    infobox_data: Optional[InfoboxData] = Field(default=None, description="Infobox structured data")
    relevance_score: Optional[float] = Field(default=None, ge=0, le=1, description="Relevance score")
    links_count: int = Field(default=0, ge=0, description="Number of links")
    crawled_at: Optional[str] = Field(default=None, description="Crawl timestamp")


# Model update to support nested validation
PipelineMetrics.model_rebuild()