"""
Neo4j Graph Data Models

Clean, simple Pydantic models for the real estate graph database.
These models define the structure of nodes and relationships in Neo4j.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from .spark_converter import SparkModel


# ============================================================================
# Enumerations
# ============================================================================

class PropertyType(str, Enum):
    """Types of properties."""
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOME = "townhome"
    MULTI_FAMILY = "multi_family"
    LAND = "land"
    OTHER = "other"


class FeatureCategory(str, Enum):
    """Categories for property features."""
    AMENITY = "amenity"
    STRUCTURAL = "structural"
    LOCATION = "location"
    APPLIANCE = "appliance"
    OUTDOOR = "outdoor"
    PARKING = "parking"
    VIEW = "view"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Types of relationships between nodes."""
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    DESCRIBES = "DESCRIBES"
    NEAR = "NEAR"
    SIMILAR_TO = "SIMILAR_TO"
    HAS_FEATURE = "HAS_FEATURE"
    OF_TYPE = "OF_TYPE"
    IN_PRICE_RANGE = "IN_PRICE_RANGE"
    IN_COUNTY = "IN_COUNTY"
    IN_TOPIC_CLUSTER = "IN_TOPIC_CLUSTER"


# ============================================================================
# Node Models
# ============================================================================

class PropertyNode(SparkModel):
    """Property node for real estate listings."""
    
    # Unique identifier
    id: str = Field(..., description="Unique property ID")
    
    # Location
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State abbreviation")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    
    # Property details
    property_type: PropertyType = Field(..., description="Type of property")
    bedrooms: int = Field(..., description="Number of bedrooms")
    bathrooms: float = Field(..., description="Number of bathrooms")
    square_feet: int = Field(..., description="Square footage")
    lot_size: Optional[float] = Field(None, description="Lot size in acres")
    year_built: Optional[int] = Field(None, description="Year property was built")
    stories: Optional[int] = Field(None, description="Number of stories")
    garage_spaces: Optional[int] = Field(None, description="Number of garage spaces")
    
    # Listing information
    listing_price: int = Field(..., description="Listing price in USD")
    price_per_sqft: float = Field(..., description="Price per square foot")
    listing_date: date = Field(..., description="Date listed")
    days_on_market: int = Field(0, description="Days on market")
    description: Optional[str] = Field(None, description="Property description")
    
    # Features
    features: List[str] = Field(default_factory=list, description="Property features")
    
    # Media
    virtual_tour_url: Optional[str] = Field(None, description="Virtual tour URL")
    images: List[str] = Field(default_factory=list, description="Property image URLs")
    
    # Price history
    price_history: List[Dict[str, Any]] = Field(default_factory=list, description="Historical price data")
    
    # References
    neighborhood_id: Optional[str] = Field(None, description="Associated neighborhood ID")
    
    # Metadata
    created_at: Optional[datetime] = Field(None, description="When property was first added")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    data_source: Optional[str] = Field(None, description="Source of property data")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Data quality metric")
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class NeighborhoodNode(SparkModel):
    """Neighborhood node for geographic areas."""
    
    # Unique identifier
    id: str = Field(..., description="Unique neighborhood ID")
    
    # Basic information
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State abbreviation")
    county: Optional[str] = Field(None, description="County name")
    
    # Location
    latitude: float = Field(..., description="Center latitude")
    longitude: float = Field(..., description="Center longitude")
    
    # Description
    description: str = Field(..., description="Neighborhood description")
    
    # Characteristics
    walkability_score: Optional[int] = Field(None, ge=0, le=10, description="Walkability score")
    transit_score: Optional[int] = Field(None, ge=0, le=10, description="Transit score")
    school_rating: Optional[int] = Field(None, ge=0, le=10, description="School rating")
    safety_rating: Optional[int] = Field(None, ge=0, le=10, description="Safety rating")
    
    # Market data
    median_home_price: Optional[int] = Field(None, description="Median home price")
    price_trend: Optional[str] = Field(None, description="Price trend")
    median_household_income: Optional[int] = Field(None, description="Median household income")
    population: Optional[int] = Field(None, description="Population")
    
    # Lifestyle
    lifestyle_tags: List[str] = Field(default_factory=list, description="Lifestyle tags")
    amenities: List[str] = Field(default_factory=list, description="Local amenities")
    vibe: Optional[str] = Field(None, description="Neighborhood vibe")
    
    # Additional scores
    nightlife_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Nightlife activity score")
    family_friendly_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Family friendliness score")
    cultural_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Cultural amenities score")
    green_space_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Parks and outdoor space score")
    
    # Knowledge graph metrics
    knowledge_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Wikipedia coverage metric")
    aggregated_topics: List[str] = Field(default_factory=list, description="Topics from related Wikipedia articles")
    wikipedia_count: int = Field(0, description="Number of Wikipedia articles describing neighborhood")
    
    # Metadata
    created_at: Optional[datetime] = Field(None, description="When neighborhood was first added")


class CityNode(SparkModel):
    """City node for geographic hierarchy."""
    
    # Unique identifier (city_state format)
    id: Optional[str] = Field(None, description="Unique city ID (city_state)")
    
    # Basic information
    name: str = Field(..., description="City name")
    state: str = Field(..., description="State abbreviation")
    county: Optional[str] = Field(None, description="County name")
    
    # Location (city center or average)
    latitude: float = Field(..., description="City center latitude")
    longitude: float = Field(..., description="City center longitude")
    
    # Statistics
    population: Optional[int] = Field(None, description="City population")
    median_home_price: Optional[int] = Field(None, description="Median home price")
    
    def __init__(self, **data):
        """Initialize with auto-generated ID if not provided."""
        if 'id' not in data or data['id'] is None:
            name = data.get('name', '').lower().replace(' ', '_')
            state = data.get('state', '').lower()
            data['id'] = f"{name}_{state}"
        super().__init__(**data)


class StateNode(SparkModel):
    """State node for geographic hierarchy."""
    
    # Unique identifier
    id: str = Field(..., description="State abbreviation")
    
    # Basic information
    name: str = Field(..., description="Full state name")
    abbreviation: str = Field(..., description="State abbreviation")
    
    # Location (geographic center)
    latitude: Optional[float] = Field(None, description="State center latitude")
    longitude: Optional[float] = Field(None, description="State center longitude")


class WikipediaArticleNode(SparkModel):
    """Wikipedia article node for location information."""
    
    # Unique identifier
    id: str = Field(..., description="Unique article ID (page_id)")
    page_id: int = Field(..., description="Wikipedia page ID")
    
    # Article information
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Wikipedia URL")
    
    # Content
    short_summary: str = Field(..., description="Short summary")
    long_summary: Optional[str] = Field(None, description="Long summary")
    key_topics: List[str] = Field(default_factory=list, description="Key topics")
    
    # Location data
    best_city: Optional[str] = Field(None, description="Best matched city")
    best_state: Optional[str] = Field(None, description="Best matched state")
    best_county: Optional[str] = Field(None, description="Best matched county")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Location confidence")
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Composite confidence score")
    location_type: Optional[str] = Field(None, description="Classification (city, neighborhood, landmark, etc.)")
    
    # Coordinates
    latitude: Optional[float] = Field(None, description="Article location latitude")
    longitude: Optional[float] = Field(None, description="Article location longitude")
    
    # Extraction metadata
    extraction_method: Optional[str] = Field(None, description="How location was determined")
    topics_extracted_at: Optional[datetime] = Field(None, description="Timestamp of topic extraction")
    amenities_count: int = Field(0, description="Number of amenities extracted")
    content_length: int = Field(0, description="Article content size for relevance scoring")
    
    # Metadata
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")


class FeatureNode(SparkModel):
    """Feature node for property features."""
    
    # Unique identifier
    id: str = Field(..., description="Unique feature ID")
    
    # Basic information
    name: str = Field(..., description="Feature name")
    category: FeatureCategory = Field(..., description="Feature category")
    
    # Description
    description: Optional[str] = Field(None, description="Feature description")
    
    # Metadata
    count: int = Field(1, description="Number of properties with this feature")
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class PropertyTypeNode(SparkModel):
    """Property type node for categorizing properties."""
    
    # Unique identifier
    id: str = Field(..., description="Unique property type ID")
    
    # Basic information
    name: str = Field(..., description="Property type name")
    label: str = Field(..., description="Display label")
    
    # Description
    description: Optional[str] = Field(None, description="Property type description")
    
    # Metadata
    property_count: int = Field(0, description="Number of properties of this type")


class PriceRangeNode(SparkModel):
    """Price range node for categorizing properties by price."""
    
    # Unique identifier
    id: str = Field(..., description="Unique price range ID")
    
    # Range definition
    label: str = Field(..., description="Display label (e.g., '500K-1M')")
    min_price: int = Field(..., description="Minimum price in range")
    max_price: Optional[int] = Field(None, description="Maximum price in range (None for open-ended)")
    
    # Market segment
    market_segment: str = Field(..., description="Market segment (e.g., 'entry', 'mid', 'luxury')")
    
    # Metadata
    property_count: int = Field(0, description="Number of properties in this range")


class CountyNode(SparkModel):
    """County node for geographic hierarchy."""
    
    # Unique identifier
    id: str = Field(..., description="Unique county ID")
    
    # Basic information
    name: str = Field(..., description="County name")
    state: str = Field(..., description="State abbreviation")
    
    # Location
    latitude: Optional[float] = Field(None, description="County center latitude")
    longitude: Optional[float] = Field(None, description="County center longitude")
    
    # Statistics
    population: Optional[int] = Field(None, description="County population")
    median_home_price: Optional[int] = Field(None, description="Median home price")
    
    # Metadata
    city_count: int = Field(0, description="Number of cities in county")


class TopicClusterNode(SparkModel):
    """Topic cluster node for grouping related topics."""
    
    # Unique identifier
    id: str = Field(..., description="Unique topic cluster ID")
    
    # Basic information
    name: str = Field(..., description="Topic cluster name")
    category: str = Field(..., description="Topic category")
    
    # Topics
    topics: List[str] = Field(default_factory=list, description="Topics in this cluster")
    
    # Metadata
    entity_count: int = Field(0, description="Number of entities associated with this cluster")


# ============================================================================
# Relationship Models
# ============================================================================

class BaseRelationship(BaseModel):
    """Base class for all relationships."""
    
    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class LocatedInRelationship(BaseRelationship):
    """LOCATED_IN relationship (Property/Neighborhood -> Neighborhood/City)."""
    
    relationship_type: Literal[RelationshipType.LOCATED_IN] = RelationshipType.LOCATED_IN
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Location match confidence")
    distance_meters: Optional[float] = Field(None, description="Distance in meters")


class PartOfRelationship(BaseRelationship):
    """PART_OF relationship (City -> State, Neighborhood -> City)."""
    
    relationship_type: Literal[RelationshipType.PART_OF] = RelationshipType.PART_OF


class DescribesRelationship(BaseRelationship):
    """DESCRIBES relationship (WikipediaArticle -> City/Neighborhood)."""
    
    relationship_type: Literal[RelationshipType.DESCRIBES] = RelationshipType.DESCRIBES
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Match confidence")
    match_type: str = Field("title", description="Type of match (title, content, location)")


class NearRelationship(BaseRelationship):
    """NEAR relationship between nodes."""
    
    relationship_type: Literal[RelationshipType.NEAR] = RelationshipType.NEAR
    distance_meters: float = Field(..., description="Distance in meters")
    distance_miles: Optional[float] = Field(None, description="Distance in miles")
    
    def __init__(self, **data):
        """Initialize with calculated miles if not provided."""
        if 'distance_miles' not in data or data['distance_miles'] is None:
            if 'distance_meters' in data:
                data['distance_miles'] = data['distance_meters'] * 0.000621371
        super().__init__(**data)


class SimilarToRelationship(BaseRelationship):
    """SIMILAR_TO relationship (Property -> Property)."""
    
    relationship_type: Literal[RelationshipType.SIMILAR_TO] = RelationshipType.SIMILAR_TO
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    
    # Similarity factors
    price_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    size_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    feature_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)


class HasFeatureRelationship(BaseRelationship):
    """HAS_FEATURE relationship (Property -> Feature)."""
    
    relationship_type: Literal[RelationshipType.HAS_FEATURE] = RelationshipType.HAS_FEATURE
    is_primary: bool = Field(False, description="Whether this is a primary feature")
    verified: bool = Field(True, description="Whether the feature is verified")


class OfTypeRelationship(BaseRelationship):
    """OF_TYPE relationship (Property -> PropertyType)."""
    
    relationship_type: Literal[RelationshipType.OF_TYPE] = RelationshipType.OF_TYPE
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Type classification confidence")
    is_primary: bool = Field(True, description="Whether this is the primary type")


class InPriceRangeRelationship(BaseRelationship):
    """IN_PRICE_RANGE relationship (Property -> PriceRange)."""
    
    relationship_type: Literal[RelationshipType.IN_PRICE_RANGE] = RelationshipType.IN_PRICE_RANGE
    price_percentile: float = Field(..., ge=0.0, le=1.0, description="Percentile within range")
    actual_price: float = Field(..., description="Actual property price")


class InCountyRelationship(BaseRelationship):
    """IN_COUNTY relationship (City/Neighborhood -> County)."""
    
    relationship_type: Literal[RelationshipType.IN_COUNTY] = RelationshipType.IN_COUNTY
    hierarchy_level: str = Field(..., description="Level in hierarchy (city, neighborhood)")


class InTopicClusterRelationship(BaseRelationship):
    """IN_TOPIC_CLUSTER relationship (Entity -> TopicCluster)."""
    
    relationship_type: Literal[RelationshipType.IN_TOPIC_CLUSTER] = RelationshipType.IN_TOPIC_CLUSTER
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Topic relevance score")
    extraction_source: str = Field(..., description="Source of topic extraction")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Topic assignment confidence")


# ============================================================================
# Configuration Models
# ============================================================================

class GraphConfiguration(BaseModel):
    """Configuration for graph construction."""
    
    # Distance thresholds
    near_distance_meters: float = Field(1609.34, description="NEAR relationship threshold (1 mile)")
    located_in_radius_meters: float = Field(5000, description="LOCATED_IN matching radius")
    
    # Similarity thresholds
    similarity_threshold: float = Field(0.7, description="Minimum similarity score")
    max_similar_properties: int = Field(10, description="Max similar properties per node")
    
    # Confidence thresholds
    min_location_confidence: float = Field(0.5, description="Minimum location confidence")
    min_extraction_confidence: float = Field(0.3, description="Minimum extraction confidence")
    
    # Batch sizes
    node_batch_size: int = Field(1000, description="Batch size for node creation")
    relationship_batch_size: int = Field(5000, description="Batch size for relationship creation")


# ============================================================================
# Utility Functions
# ============================================================================

def create_node_id(node_type: str, *components) -> str:
    """Create a standardized node ID."""
    parts = [str(c).lower().replace(' ', '_') for c in components if c]
    return f"{node_type}:{':'.join(parts)}"


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude."""
    return -90 <= lat <= 90 and -180 <= lon <= 180