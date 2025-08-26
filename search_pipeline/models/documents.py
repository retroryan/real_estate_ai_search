"""Document models for search pipeline.

These Pydantic models define the structure of documents that will be indexed
to Elasticsearch. They provide type safety and validation for the transformation
from DataFrames to search documents.

The structure of these models exactly matches the Elasticsearch mappings defined
in real_estate_search.indexer.mappings to ensure proper indexing.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Nested object models matching Elasticsearch mappings
class AddressModel(BaseModel):
    """Address object model matching Elasticsearch address mapping."""
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State code")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    location: Optional[List[float]] = Field(None, description="Geo point as [lon, lat]")


class NeighborhoodModel(BaseModel):
    """Neighborhood object model matching Elasticsearch neighborhood mapping."""
    id: Optional[str] = Field(None, description="Neighborhood ID")
    name: Optional[str] = Field(None, description="Neighborhood name")
    walkability_score: Optional[int] = Field(None, description="Walkability score (0-100)")
    school_rating: Optional[float] = Field(None, description="School rating")


class ParkingModel(BaseModel):
    """Parking object model matching Elasticsearch parking mapping."""
    spaces: Optional[int] = Field(None, description="Number of parking spaces")
    type: Optional[str] = Field(None, description="Type of parking")


class LandmarkModel(BaseModel):
    """Landmark model for nested landmarks in location context."""
    name: str = Field(..., description="Landmark name")
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    category: Optional[str] = Field(None, description="Landmark category")
    distance_miles: Optional[float] = Field(None, description="Distance in miles")
    significance_score: Optional[float] = Field(None, description="Significance score")
    description: Optional[str] = Field(None, description="Landmark description")


class LocationContextModel(BaseModel):
    """Location context from Wikipedia enrichment."""
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia title")
    location_summary: Optional[str] = Field(None, description="Location summary")
    historical_significance: Optional[str] = Field(None, description="Historical significance")
    key_topics: List[str] = Field(default_factory=list, description="Key topics")
    landmarks: List[LandmarkModel] = Field(default_factory=list, description="Nearby landmarks")
    cultural_features: List[str] = Field(default_factory=list, description="Cultural features")
    recreational_features: List[str] = Field(default_factory=list, description="Recreational features")
    transportation: List[str] = Field(default_factory=list, description="Transportation options")
    location_type: Optional[str] = Field(None, description="Location type")
    confidence_score: Optional[float] = Field(None, description="Confidence score")


class NeighborhoodContextModel(BaseModel):
    """Neighborhood context from Wikipedia enrichment."""
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia title")
    description: Optional[str] = Field(None, description="Neighborhood description")
    history: Optional[str] = Field(None, description="Historical information")
    character: Optional[str] = Field(None, description="Neighborhood character")
    notable_residents: List[str] = Field(default_factory=list, description="Notable residents")
    architectural_style: List[str] = Field(default_factory=list, description="Architectural styles")
    establishment_year: Optional[int] = Field(None, description="Year established")
    gentrification_index: Optional[float] = Field(None, description="Gentrification index")
    diversity_score: Optional[float] = Field(None, description="Diversity score")
    key_topics: List[str] = Field(default_factory=list, description="Key topics")


class NearbyPOIModel(BaseModel):
    """Nearby Point of Interest model for nested POI in properties."""
    name: str = Field(..., description="POI name")
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    category: Optional[str] = Field(None, description="POI category")
    distance_miles: Optional[float] = Field(None, description="Distance in miles")
    walking_time_minutes: Optional[int] = Field(None, description="Walking time in minutes")
    significance_score: Optional[float] = Field(None, description="Significance score")
    description: Optional[str] = Field(None, description="POI description")
    key_topics: List[str] = Field(default_factory=list, description="Key topics")


class LocationScoresModel(BaseModel):
    """Location quality scores model."""
    cultural_richness: Optional[float] = Field(None, description="Cultural richness score")
    historical_importance: Optional[float] = Field(None, description="Historical importance score")
    tourist_appeal: Optional[float] = Field(None, description="Tourist appeal score")
    local_amenities: Optional[float] = Field(None, description="Local amenities score")
    overall_desirability: Optional[float] = Field(None, description="Overall desirability score")


class BaseDocument(BaseModel):
    """Base document model with common fields for all entity types."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
    )
    
    # Document metadata
    doc_id: str = Field(..., description="Unique document identifier for Elasticsearch")
    entity_id: str = Field(..., description="Original entity ID (listing_id, neighborhood_id, or page_id)")
    entity_type: str = Field(..., description="Type of entity (property, neighborhood, wikipedia)")
    indexed_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when document was indexed")


class PropertyDocument(BaseDocument):
    """Document model for property listings matching Elasticsearch mappings exactly."""
    
    # Original property ID
    listing_id: Optional[str] = Field(None, description="Original property listing ID")
    
    # Core property fields
    property_type: Optional[str] = Field(None, description="Type of property")
    price: Optional[float] = Field(None, description="Property price")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, description="Square footage")
    year_built: Optional[int] = Field(None, description="Year property was built")
    lot_size: Optional[int] = Field(None, description="Lot size in square feet")
    
    # Nested address object
    address: Optional[AddressModel] = Field(None, description="Address object")
    
    # Nested neighborhood object
    neighborhood: Optional[NeighborhoodModel] = Field(None, description="Neighborhood object")
    
    # Description and features
    description: Optional[str] = Field(None, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    
    # Status and dates
    status: Optional[str] = Field(None, description="Listing status")
    listing_date: Optional[datetime] = Field(None, description="Listing date")
    last_updated: Optional[datetime] = Field(None, description="Last updated date")
    days_on_market: Optional[int] = Field(None, description="Days on market")
    
    # Financial fields
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    hoa_fee: Optional[float] = Field(None, description="HOA fee")
    tax_assessed_value: Optional[int] = Field(None, description="Tax assessed value")
    annual_tax: Optional[float] = Field(None, description="Annual tax")
    
    # Parking
    parking: Optional[ParkingModel] = Field(None, description="Parking information")
    
    # Media
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    
    # Other fields
    mls_number: Optional[str] = Field(None, description="MLS number")
    search_tags: Optional[str] = Field(None, description="Search tags")
    
    # Wikipedia enrichment fields
    location_context: Optional[LocationContextModel] = Field(None, description="Location context from Wikipedia")
    neighborhood_context: Optional[NeighborhoodContextModel] = Field(None, description="Neighborhood context from Wikipedia")
    nearby_poi: List[NearbyPOIModel] = Field(default_factory=list, description="Nearby points of interest")
    enriched_search_text: Optional[str] = Field(None, description="Combined search text with Wikipedia data")
    location_scores: Optional[LocationScoresModel] = Field(None, description="Location quality scores")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding generation")
    embedding_dimension: Optional[int] = Field(None, description="Dimension of the embedding vector")
    embedded_at: Optional[datetime] = Field(None, description="Timestamp when embedding was generated")
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        """Ensure price is positive if provided."""
        if v is not None and v < 0:
            raise ValueError('Price must be non-negative')
        return v
    
    @field_validator('bedrooms', 'bathrooms', 'square_feet', 'lot_size')
    @classmethod
    def validate_positive_numbers(cls, v: Optional[float]) -> Optional[float]:
        """Ensure numeric fields are positive if provided."""
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class NeighborhoodDocument(BaseDocument):
    """Document model for neighborhoods matching Elasticsearch mappings exactly."""
    
    # Core neighborhood fields  
    neighborhood_id: str = Field(..., description="Neighborhood identifier")
    name: str = Field(..., description="Neighborhood name")
    
    # Nested address object for location
    address: Optional[AddressModel] = Field(None, description="Address object with location")
    
    # Additional location fields
    boundaries: Optional[str] = Field(None, description="Neighborhood boundaries as JSON string")
    
    # Basic scores (if available)
    walkability_score: Optional[int] = Field(None, description="Walkability score (0-100)")
    transit_score: Optional[int] = Field(None, description="Transit score (0-100)")
    school_rating: Optional[float] = Field(None, description="School rating")
    
    # Description
    description: Optional[str] = Field(None, description="Neighborhood description")
    
    # Wikipedia enrichment fields
    location_context: Optional[LocationContextModel] = Field(None, description="Location context from Wikipedia")
    neighborhood_context: Optional[NeighborhoodContextModel] = Field(None, description="Neighborhood context from Wikipedia")
    nearby_poi: List[NearbyPOIModel] = Field(default_factory=list, description="Nearby points of interest")
    enriched_search_text: Optional[str] = Field(None, description="Combined search text with Wikipedia data")
    location_scores: Optional[LocationScoresModel] = Field(None, description="Location quality scores")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding generation")
    embedding_dimension: Optional[int] = Field(None, description="Dimension of the embedding vector")
    embedded_at: Optional[datetime] = Field(None, description="Timestamp when embedding was generated")
    
    # Note: Property statistics will be calculated via Elasticsearch aggregations
    
    @field_validator('walkability_score', 'transit_score')
    @classmethod
    def validate_scores(cls, v: Optional[int]) -> Optional[int]:
        """Ensure scores are in valid range."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError('Score must be between 0 and 100')
        return v


class WikipediaDocument(BaseDocument):
    """Document model for Wikipedia articles matching Elasticsearch mappings exactly."""
    
    # Core Wikipedia fields
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    
    # Content fields
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Full article content")
    
    # Nested address object for location
    address: Optional[AddressModel] = Field(None, description="Address object with location")
    
    # Topics
    topics: List[str] = Field(default_factory=list, description="List of topics or categories")
    
    # Metadata
    last_modified: Optional[datetime] = Field(None, description="Last modification date")
    
    # Wikipedia enrichment fields (for self-referential enrichment)
    location_context: Optional[LocationContextModel] = Field(None, description="Location context")
    neighborhood_context: Optional[NeighborhoodContextModel] = Field(None, description="Neighborhood context")
    nearby_poi: List[NearbyPOIModel] = Field(default_factory=list, description="Nearby points of interest")
    enriched_search_text: Optional[str] = Field(None, description="Combined search text")
    location_scores: Optional[LocationScoresModel] = Field(None, description="Location quality scores")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding generation")
    embedding_dimension: Optional[int] = Field(None, description="Dimension of the embedding vector")
    embedded_at: Optional[datetime] = Field(None, description="Timestamp when embedding was generated")