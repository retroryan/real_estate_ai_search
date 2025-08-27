"""
Enhanced Pydantic models for demo query results with strong typing.

This module provides type-safe models for handling Elasticsearch query results,
ensuring data integrity and making the code more maintainable and self-documenting.
"""

from typing import Dict, Any, Optional, List, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from enum import Enum


class EntityType(str, Enum):
    """Enumeration of entity types in the search system."""
    PROPERTY = "property"
    NEIGHBORHOOD = "neighborhood"
    WIKIPEDIA = "wikipedia"
    WIKIPEDIA_PRIMARY = "wikipedia_primary"
    WIKIPEDIA_RELATED = "wikipedia_related"


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    PRIMARY_ARTICLE = "primary_article"
    NEIGHBORHOOD_ARTICLE = "neighborhood_article"
    PARK_ARTICLE = "park_article"
    REFERENCE_ARTICLE = "reference_article"
    RELATED = "related"


class Address(BaseModel):
    """Address model for properties."""
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State abbreviation")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    location: Optional[Dict[str, float]] = Field(None, description="Lat/lon coordinates")
    
    model_config = ConfigDict(extra="allow")
    
    @computed_field  # type: ignore
    @property
    def full_address(self) -> str:
        """Generate full address string."""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        if self.zip_code:
            parts.append(self.zip_code)
        return " ".join(parts) if parts else "Unknown Address"


class Demographics(BaseModel):
    """Demographics data for neighborhoods."""
    population: Optional[int] = Field(None, description="Population count")
    median_income: Optional[float] = Field(None, description="Median household income")
    median_age: Optional[float] = Field(None, description="Median age of residents")
    
    model_config = ConfigDict(extra="allow")


class WikipediaCorrelation(BaseModel):
    """Correlation between a neighborhood and Wikipedia article."""
    page_id: str = Field(..., description="Wikipedia page ID")
    title: Optional[str] = Field(None, description="Article title")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    relationship: RelationshipType = Field(RelationshipType.RELATED, description="Type of relationship")
    
    model_config = ConfigDict(extra="allow")


class PropertyEntity(BaseModel):
    """
    Strongly-typed property entity from Elasticsearch.
    
    This model ensures all property data is properly validated and typed,
    preventing the undefined mutation issues in the original code.
    """
    # Core identifiers
    listing_id: str = Field(..., description="Unique property listing ID")
    neighborhood_id: Optional[str] = Field(None, description="Associated neighborhood ID")
    
    # Property details
    property_type: Optional[str] = Field(None, description="Type of property (e.g., Single Family)")
    price: Optional[float] = Field(None, ge=0, description="Property price")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, ge=0, description="Square footage")
    year_built: Optional[int] = Field(None, description="Year property was built")
    
    # Location
    address: Optional[Address] = Field(None, description="Property address")
    
    # Features
    amenities: List[str] = Field(default_factory=list, description="List of amenities")
    description: Optional[str] = Field(None, description="Property description")
    
    # Metadata
    entity_type: Literal[EntityType.PROPERTY] = Field(
        EntityType.PROPERTY,
        alias="_entity_type",
        description="Entity type identifier"
    )
    score: Optional[float] = Field(None, alias="_score", description="Elasticsearch relevance score")
    
    model_config = ConfigDict(extra="allow", use_enum_values=True, populate_by_name=True)


class NeighborhoodEntity(BaseModel):
    """
    Strongly-typed neighborhood entity from Elasticsearch.
    
    Includes wikipedia correlations and demographic data.
    """
    # Core identifiers
    neighborhood_id: str = Field(..., description="Unique neighborhood ID")
    name: str = Field(..., description="Neighborhood name")
    
    # Location
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State abbreviation")
    county: Optional[str] = Field(None, description="County name")
    
    # Description and features
    description: Optional[str] = Field(None, description="Neighborhood description")
    amenities: List[str] = Field(default_factory=list, description="Neighborhood amenities")
    demographics: Optional[Demographics] = Field(None, description="Demographic information")
    
    # Wikipedia relationships
    wikipedia_correlations: Optional[Dict[str, Any]] = Field(
        None,
        description="Wikipedia article correlations"
    )
    
    # Metadata
    entity_type: Literal[EntityType.NEIGHBORHOOD] = Field(
        EntityType.NEIGHBORHOOD,
        alias="_entity_type",
        description="Entity type identifier"
    )
    score: Optional[float] = Field(None, alias="_score", description="Elasticsearch relevance score")
    
    model_config = ConfigDict(extra="allow", use_enum_values=True, populate_by_name=True)
    
    @computed_field  # type: ignore
    @property
    def primary_wiki_article(self) -> Optional[WikipediaCorrelation]:
        """Extract primary Wikipedia article if exists."""
        if self.wikipedia_correlations and 'primary_wiki_article' in self.wikipedia_correlations:
            data = self.wikipedia_correlations['primary_wiki_article']
            if data and isinstance(data, dict) and 'page_id' in data:
                return WikipediaCorrelation(**data)
        return None
    
    @computed_field  # type: ignore
    @property
    def related_wiki_articles(self) -> List[WikipediaCorrelation]:
        """Extract related Wikipedia articles."""
        articles = []
        if self.wikipedia_correlations and 'related_wiki_articles' in self.wikipedia_correlations:
            related = self.wikipedia_correlations['related_wiki_articles']
            if isinstance(related, list):
                for article_data in related:
                    if isinstance(article_data, dict) and 'page_id' in article_data:
                        articles.append(WikipediaCorrelation(**article_data))
        return articles


class WikipediaEntity(BaseModel):
    """
    Strongly-typed Wikipedia article entity from Elasticsearch.
    
    Includes relationship metadata for context.
    """
    # Core identifiers
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    
    # Content
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Article content")
    full_content: Optional[str] = Field(None, description="Full HTML content")
    content_length: Optional[int] = Field(None, ge=0, description="Content length in characters")
    
    # Location
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    best_city: Optional[str] = Field(None, description="Best matched city")
    best_state: Optional[str] = Field(None, description="Best matched state")
    
    # Categories and topics
    categories: List[str] = Field(default_factory=list, description="Wikipedia categories")
    topics: List[str] = Field(default_factory=list, description="Article topics")
    
    # URL
    url: Optional[str] = Field(None, description="Wikipedia article URL")
    
    # Relationship metadata (added during query processing)
    entity_type: EntityType = Field(
        EntityType.WIKIPEDIA,
        alias="_entity_type",
        description="Entity type identifier"
    )
    relationship: Optional[RelationshipType] = Field(
        None,
        alias="_relationship",
        description="Type of relationship to parent entity"
    )
    confidence: Optional[float] = Field(
        None,
        alias="_confidence",
        ge=0.0, le=1.0,
        description="Confidence score for relationship"
    )
    score: Optional[float] = Field(None, alias="_score", description="Elasticsearch relevance score")
    
    model_config = ConfigDict(extra="allow", use_enum_values=True, populate_by_name=True)
    
    @field_validator('entity_type', mode='before')
    def normalize_entity_type(cls, v):
        """Handle various wikipedia entity type formats."""
        if isinstance(v, str):
            if 'wikipedia' in v.lower():
                if 'primary' in v.lower():
                    return EntityType.WIKIPEDIA_PRIMARY
                elif 'related' in v.lower():
                    return EntityType.WIKIPEDIA_RELATED
                return EntityType.WIKIPEDIA
        return v


class SearchResult(BaseModel):
    """
    Container for any type of search result entity.
    
    This is a union type that can hold any entity type with proper validation.
    """
    entity: Union[PropertyEntity, NeighborhoodEntity, WikipediaEntity] = Field(
        ...,
        discriminator='entity_type',
        description="The search result entity"
    )
    
    @computed_field  # type: ignore
    @property
    def get_entity_type(self) -> EntityType:
        """Get the entity type."""
        return self.entity.entity_type
    
    @computed_field  # type: ignore
    @property
    def display_title(self) -> str:
        """Generate a display title for the entity."""
        if isinstance(self.entity, PropertyEntity):
            return self.entity.address.full_address if self.entity.address else f"Property {self.entity.listing_id}"
        elif isinstance(self.entity, NeighborhoodEntity):
            return f"{self.entity.name}, {self.entity.city}"
        elif isinstance(self.entity, WikipediaEntity):
            return self.entity.title
        return "Unknown Entity"


class ElasticsearchHit(BaseModel):
    """
    Model for a raw Elasticsearch hit.
    
    This provides type safety when processing Elasticsearch responses.
    """
    index: str = Field(..., alias="_index", description="Index name")
    id: str = Field(..., alias="_id", description="Document ID")
    score: Optional[float] = Field(None, alias="_score", description="Relevance score")
    source: Dict[str, Any] = Field(..., alias="_source", description="Document source")
    highlight: Optional[Dict[str, List[str]]] = Field(None, description="Highlighted fields")
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    
    def to_entity(self) -> Optional[Union[PropertyEntity, NeighborhoodEntity, WikipediaEntity]]:
        """
        Convert Elasticsearch hit to appropriate entity type.
        
        This method examines the index name and source data to determine
        the correct entity type and returns a validated Pydantic model.
        """
        source = self.source.copy()
        
        # Add score if available
        if self.score is not None:
            source['_score'] = self.score
        
        # Determine entity type based on index
        if self.index == "properties":
            source['_entity_type'] = EntityType.PROPERTY
            return PropertyEntity(**source)
        elif self.index == "neighborhoods":
            source['_entity_type'] = EntityType.NEIGHBORHOOD
            return NeighborhoodEntity(**source)
        elif self.index == "wikipedia":
            # Default to wikipedia, will be refined based on context
            if '_entity_type' not in source:
                source['_entity_type'] = EntityType.WIKIPEDIA
            return WikipediaEntity(**source)
        
        return None


class QueryContext(BaseModel):
    """
    Context for a query execution, providing metadata about the search.
    
    This helps track query flow and relationships between entities.
    """
    query_type: str = Field(..., description="Type of query being executed")
    parent_entity: Optional[Union[PropertyEntity, NeighborhoodEntity]] = Field(
        None,
        description="Parent entity this query relates to"
    )
    relationship_chain: List[str] = Field(
        default_factory=list,
        description="Chain of relationships being traversed"
    )
    execution_time_ms: int = Field(0, description="Query execution time")
    
    def add_relationship(self, relationship: str):
        """Add a relationship to the chain."""
        self.relationship_chain.append(relationship)