"""Enriched neighborhood model with computed fields and relationships."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict


class EnrichedNeighborhood(BaseModel):
    """Enriched neighborhood with all computed fields and relationships."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    neighborhood_id: str = Field(description="Neighborhood ID")
    name: str = Field(description="Neighborhood name")
    
    # Location
    city: str = Field(description="City")
    state: str = Field(description="State")
    county: str = Field(description="County")
    
    # Demographics
    population: int = Field(description="Population")
    households: int = Field(description="Households")
    median_age: float = Field(description="Median age")
    median_income: float = Field(description="Median income")
    
    # Housing statistics
    median_home_price: float = Field(description="Median home price")
    median_rent: float = Field(description="Median rent")
    home_ownership_rate: float = Field(description="Ownership rate")
    
    # Quality metrics
    crime_score: float = Field(description="Crime score 0-10")
    school_score: float = Field(description="School score 0-10")
    walkability_score: int = Field(description="Walkability 0-100")
    transit_score: int = Field(description="Transit 0-100")
    
    # Geographic
    center_latitude: float = Field(description="Center latitude")
    center_longitude: float = Field(description="Center longitude")
    area_sqmi: float = Field(description="Area square miles")
    
    # Enriched property statistics
    total_properties: int = Field(default=0, description="Total properties")
    active_listings: int = Field(default=0, description="Active listings")
    avg_days_on_market: float = Field(default=0, description="Avg days on market")
    price_trend_3mo: float = Field(default=0, description="3-month price trend %")
    price_trend_1yr: float = Field(default=0, description="1-year price trend %")
    
    # Market analysis
    market_temperature: str = Field(default="balanced", description="hot/warm/balanced/cool/cold")
    inventory_level: str = Field(default="normal", description="low/normal/high")
    buyer_seller_ratio: float = Field(default=1.0, description="Buyer to seller ratio")
    
    # Lifestyle scores
    family_friendly_score: float = Field(ge=0, le=10, description="Family friendly score")
    nightlife_score: float = Field(ge=0, le=10, description="Nightlife score")
    dining_score: float = Field(ge=0, le=10, description="Dining score")
    shopping_score: float = Field(ge=0, le=10, description="Shopping score")
    outdoor_score: float = Field(ge=0, le=10, description="Outdoor activities score")
    
    # Affordability metrics
    affordability_index: float = Field(ge=0, description="Affordability index")
    income_to_price_ratio: float = Field(ge=0, description="Income to home price ratio")
    rent_to_income_ratio: float = Field(ge=0, description="Rent to income ratio")
    
    # Growth metrics
    population_growth_rate: float = Field(description="Annual population growth %")
    economic_growth_score: float = Field(ge=0, le=10, description="Economic growth score")
    development_activity: str = Field(default="moderate", description="low/moderate/high")
    
    # Text and search
    description: str = Field(description="Description")
    highlights: list[str] = Field(description="Key highlights")
    embedding_text: str = Field(description="Text for embeddings")
    search_keywords: list[str] = Field(description="Search keywords")
    
    # Related entities
    adjacent_neighborhoods: list[str] = Field(default_factory=list, description="Adjacent neighborhoods")
    similar_neighborhoods: list[str] = Field(default_factory=list, description="Similar neighborhoods")
    wikipedia_articles: list[str] = Field(default_factory=list, description="Related Wikipedia")
    top_properties: list[str] = Field(default_factory=list, description="Top property IDs")
    
    # Metadata
    data_quality_score: float = Field(ge=0, le=1, description="Data quality")
    enrichment_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Enrichment time")
    
    @computed_field
    @property
    def population_density(self) -> float:
        """Calculate population density per square mile."""
        if self.area_sqmi > 0:
            return self.population / self.area_sqmi
        return 0
    
    @computed_field
    @property
    def overall_livability_score(self) -> float:
        """Calculate overall livability score."""
        scores = [
            self.crime_score,
            self.school_score,
            self.walkability_score / 10,
            self.transit_score / 10,
            self.family_friendly_score,
        ]
        return sum(scores) / len(scores)
    
    @computed_field
    @property
    def investment_potential(self) -> str:
        """Determine investment potential."""
        growth_factors = (
            self.population_growth_rate > 2 and
            self.economic_growth_score > 6 and
            self.development_activity in ["moderate", "high"]
        )
        
        if growth_factors and self.affordability_index > 0.5:
            return "high"
        elif growth_factors or self.price_trend_1yr > 5:
            return "medium"
        return "low"
    
    @computed_field
    @property
    def demographic_profile(self) -> str:
        """Determine primary demographic profile."""
        if self.median_age < 30:
            return "young_professionals"
        elif self.median_age < 40 and self.family_friendly_score > 7:
            return "young_families"
        elif self.median_age < 50:
            return "established_families"
        elif self.median_age < 65:
            return "empty_nesters"
        return "retirees"