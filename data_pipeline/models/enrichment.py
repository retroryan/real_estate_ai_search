"""
Enrichment models for Wikipedia integration.

This module defines Pydantic models for structuring Wikipedia enrichment data
that will be integrated into property and neighborhood documents. These models
match the expected structure of the location_context and neighborhood_context
fields in the search pipeline documents.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Landmark(BaseModel):
    """Landmark model for POIs and notable locations."""
    
    name: str = Field(..., description="Landmark name")
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    category: Optional[str] = Field(None, description="Landmark category (e.g., 'museum', 'park', 'historical_site')")
    distance_miles: Optional[float] = Field(None, description="Distance in miles from location")
    significance_score: Optional[float] = Field(None, ge=0, le=1, description="Significance score (0-1)")
    description: Optional[str] = Field(None, description="Brief description of the landmark")


class NearbyPOI(BaseModel):
    """Nearby Point of Interest model for enrichment."""
    
    name: str = Field(..., description="POI name")
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    category: Optional[str] = Field(None, description="POI category (e.g., 'restaurant', 'shopping', 'education')")
    distance_miles: Optional[float] = Field(None, ge=0, description="Distance in miles")
    walking_time_minutes: Optional[int] = Field(None, ge=0, description="Walking time in minutes")
    significance_score: Optional[float] = Field(None, ge=0, le=1, description="Significance score (0-1)")
    description: Optional[str] = Field(None, description="POI description")
    key_topics: List[str] = Field(default_factory=list, description="Key topics associated with POI")


class LocationContext(BaseModel):
    """Location context enrichment from Wikipedia data."""
    
    # Wikipedia metadata
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia article title")
    
    # Content
    location_summary: Optional[str] = Field(None, description="Summary of the location from Wikipedia")
    historical_significance: Optional[str] = Field(None, description="Historical significance of the location")
    key_topics: List[str] = Field(default_factory=list, description="Key topics extracted from Wikipedia")
    
    # Features and amenities
    landmarks: List[Landmark] = Field(default_factory=list, description="Notable landmarks in the area")
    cultural_features: List[str] = Field(default_factory=list, description="Cultural features and attractions")
    recreational_features: List[str] = Field(default_factory=list, description="Parks, recreation, outdoor activities")
    transportation: List[str] = Field(default_factory=list, description="Transportation options and infrastructure")
    
    # Metadata
    location_type: Optional[str] = Field(None, description="Type of location (e.g., 'city', 'neighborhood', 'district')")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score for location match (0-1)")


class NeighborhoodContext(BaseModel):
    """Neighborhood context enrichment from Wikipedia data."""
    
    # Wikipedia metadata
    wikipedia_page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia article title")
    
    # Content
    description: Optional[str] = Field(None, description="General description of the neighborhood")
    history: Optional[str] = Field(None, description="Historical information about the neighborhood")
    character: Optional[str] = Field(None, description="Character and atmosphere of the neighborhood")
    key_topics: List[str] = Field(default_factory=list, description="Key topics from Wikipedia")
    
    # Social and cultural
    notable_residents: List[str] = Field(default_factory=list, description="Notable residents (historical or current)")
    architectural_style: List[str] = Field(default_factory=list, description="Predominant architectural styles")
    
    # Demographics and characteristics
    establishment_year: Optional[int] = Field(None, description="Year the neighborhood was established")
    gentrification_index: Optional[float] = Field(None, ge=0, le=1, description="Gentrification index (0-1)")
    diversity_score: Optional[float] = Field(None, ge=0, le=1, description="Cultural diversity score (0-1)")


class EnrichmentData(BaseModel):
    """Container for all enrichment data for a location."""
    
    # Core contexts
    location_context: Optional[LocationContext] = Field(None, description="Location-specific enrichment")
    neighborhood_context: Optional[NeighborhoodContext] = Field(None, description="Neighborhood-specific enrichment")
    
    # Nearby features
    nearby_poi: List[NearbyPOI] = Field(default_factory=list, description="Nearby points of interest")
    
    # Quality scores
    cultural_richness: Optional[float] = Field(None, ge=0, le=1, description="Cultural richness score")
    historical_importance: Optional[float] = Field(None, ge=0, le=1, description="Historical importance score")
    tourist_appeal: Optional[float] = Field(None, ge=0, le=1, description="Tourist appeal score")
    local_amenities: Optional[float] = Field(None, ge=0, le=1, description="Local amenities score")
    overall_desirability: Optional[float] = Field(None, ge=0, le=1, description="Overall location desirability")
    
    # Combined enriched text for search
    enriched_search_text: Optional[str] = Field(None, description="Combined enriched search text")


class WikipediaEnrichmentResult(BaseModel):
    """Result from Wikipedia enrichment process."""
    
    # Source information
    source_entity_id: str = Field(..., description="ID of the entity being enriched")
    entity_type: str = Field(..., description="Type of entity (property, neighborhood, etc.)")
    
    # Enrichment data
    enrichment: EnrichmentData = Field(..., description="The enrichment data")
    
    # Process metadata
    enrichment_confidence: float = Field(..., ge=0, le=1, description="Overall confidence in enrichment quality")
    wikipedia_articles_used: List[str] = Field(default_factory=list, description="Wikipedia page IDs used for enrichment")
    processing_notes: List[str] = Field(default_factory=list, description="Notes from enrichment processing")