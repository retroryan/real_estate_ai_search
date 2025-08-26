"""
Configuration for entity extractors.

Centralized configuration for all extractors to avoid hard-coding.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PriceRangeConfig(BaseModel):
    """Configuration for a single price range."""
    
    min_price: int = Field(..., description="Minimum price in range")
    max_price: Optional[int] = Field(None, description="Maximum price (None for open-ended)")
    label: str = Field(..., description="Display label")
    segment: str = Field(..., description="Market segment classification")


class FeatureCategoryMapping(BaseModel):
    """Mapping of keywords to feature categories."""
    
    amenity: List[str] = Field(default_factory=lambda: [
        "pool", "gym", "spa", "sauna", "tennis", "concierge", "doorman", "community"
    ])
    structural: List[str] = Field(default_factory=lambda: [
        "hardwood", "granite", "marble", "vaulted", "crown", "basement", "attic", "loft"
    ])
    location: List[str] = Field(default_factory=lambda: [
        "waterfront", "corner", "cul-de-sac", "gated"
    ])
    appliance: List[str] = Field(default_factory=lambda: [
        "stainless", "dishwasher", "microwave", "refrigerator", "washer", "dryer"
    ])
    outdoor: List[str] = Field(default_factory=lambda: [
        "patio", "deck", "balcony", "garden", "yard", "landscap"
    ])
    parking: List[str] = Field(default_factory=lambda: [
        "garage", "carport", "driveway", "parking"
    ])
    view: List[str] = Field(default_factory=lambda: [
        "view", "panoramic", "skyline", "ocean", "mountain", "city view", "water view"
    ])


class TopicCategoryMapping(BaseModel):
    """Mapping of keywords to topic categories."""
    
    education: List[str] = Field(default_factory=lambda: [
        "school", "university", "college", "education", "academic", "student"
    ])
    transportation: List[str] = Field(default_factory=lambda: [
        "transit", "bart", "muni", "caltrain", "highway", "bridge", "airport"
    ])
    recreation: List[str] = Field(default_factory=lambda: [
        "park", "recreation", "sports", "beach", "trail", "golf"
    ])
    culture: List[str] = Field(default_factory=lambda: [
        "museum", "art", "theater", "music", "festival", "cultural"
    ])
    history: List[str] = Field(default_factory=lambda: [
        "history", "historic", "heritage", "landmark", "monument"
    ])
    business: List[str] = Field(default_factory=lambda: [
        "business", "shopping", "restaurant", "retail", "commerce", "downtown"
    ])
    residential: List[str] = Field(default_factory=lambda: [
        "residential", "neighborhood", "housing", "apartment", "condo"
    ])
    nature: List[str] = Field(default_factory=lambda: [
        "nature", "wildlife", "forest", "mountain", "ocean", "bay"
    ])


class ExtractorConfig(BaseModel):
    """Configuration for all entity extractors."""
    
    # Price ranges for property categorization
    price_ranges: List[PriceRangeConfig] = Field(default_factory=lambda: [
        PriceRangeConfig(min_price=0, max_price=500000, label="Under 500K", segment="entry"),
        PriceRangeConfig(min_price=500000, max_price=1000000, label="500K-1M", segment="mid"),
        PriceRangeConfig(min_price=1000000, max_price=2000000, label="1M-2M", segment="upper-mid"),
        PriceRangeConfig(min_price=2000000, max_price=5000000, label="2M-5M", segment="luxury"),
        PriceRangeConfig(min_price=5000000, max_price=None, label="5M+", segment="ultra-luxury")
    ])
    
    # Feature category mappings
    feature_categories: FeatureCategoryMapping = Field(
        default_factory=FeatureCategoryMapping
    )
    
    # Topic category mappings  
    topic_categories: TopicCategoryMapping = Field(
        default_factory=TopicCategoryMapping
    )
    
    # Property type descriptions
    property_type_descriptions: Dict[str, str] = Field(default_factory=lambda: {
        "single_family": "Single-family detached home",
        "condo": "Condominium unit",
        "townhome": "Townhouse or row house",
        "multi_family": "Multi-family property (duplex, triplex, etc.)",
        "land": "Vacant land or lot",
        "other": "Other property type"
    })
    
    # Collection limits for safety
    max_collect_records: Optional[int] = Field(
        None, 
        description="Maximum records to collect in memory (None for unlimited)"
    )
    
    # Logging configuration
    log_stats: bool = Field(True, description="Whether to log extraction statistics")
    
    # Performance settings
    cache_broadcast_variables: bool = Field(
        True, 
        description="Cache broadcast variables for performance"
    )


# Default configuration instance
DEFAULT_CONFIG = ExtractorConfig()