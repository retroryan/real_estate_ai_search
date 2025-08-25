"""Pydantic models for demo data structures"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class PropertyResult(BaseModel):
    """Property search result model"""
    listing_id: str = Field(..., description="Property listing ID")
    address: Optional[str] = Field(None, description="Street address")
    listing_price: float = Field(..., description="Property listing price")
    neighborhood: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    state: Optional[str] = Field(None, description="State")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, description="Square footage")
    property_type: Optional[str] = Field(None, description="Type of property")
    description: Optional[str] = Field(None, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SearchResult(BaseModel):
    """Hybrid search result with scoring"""
    listing_id: str = Field(..., description="Property listing ID")
    address: Optional[str] = Field(None, description="Street address")
    listing_price: float = Field(..., description="Property listing price")
    vector_score: float = Field(0.0, description="Vector similarity score")
    graph_score: float = Field(0.0, description="Graph-based score")
    combined_score: float = Field(0.0, description="Combined search score")
    neighborhood: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    square_feet: Optional[int] = Field(None, description="Square footage")
    description: Optional[str] = Field(None, description="Property description")
    similar_properties: List[str] = Field(default_factory=list, description="Similar property IDs")
    features: List[str] = Field(default_factory=list, description="Property features")


class NeighborhoodStats(BaseModel):
    """Neighborhood statistics model"""
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State")
    property_count: int = Field(0, description="Number of properties")
    avg_price: float = Field(0.0, description="Average listing price")
    min_price: float = Field(0.0, description="Minimum listing price")
    max_price: float = Field(0.0, description="Maximum listing price")
    avg_bedrooms: Optional[float] = Field(None, description="Average bedrooms")
    avg_square_feet: Optional[float] = Field(None, description="Average square feet")
    walkability_score: Optional[float] = Field(None, description="Walkability score")
    lifestyle_tags: List[str] = Field(default_factory=list, description="Lifestyle tags")


class WikipediaArticle(BaseModel):
    """Wikipedia article reference model"""
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    article_type: str = Field("general", description="Type of article")
    confidence: float = Field(0.0, description="Confidence score")
    url: Optional[str] = Field(None, description="Wikipedia URL")


class MarketInsight(BaseModel):
    """Market analysis insight model"""
    insight_type: str = Field(..., description="Type of insight")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Associated metrics")
    properties_affected: int = Field(0, description="Number of properties affected")
    confidence: float = Field(0.0, description="Confidence score")


class FeatureAnalysis(BaseModel):
    """Feature impact analysis model"""
    feature_name: str = Field(..., description="Feature name")
    category: str = Field(..., description="Feature category")
    property_count: int = Field(0, description="Properties with this feature")
    avg_price_impact: float = Field(0.0, description="Average price impact")
    correlation_strength: float = Field(0.0, description="Correlation strength")
    related_features: List[str] = Field(default_factory=list, description="Related features")


class GraphAnalysisResult(BaseModel):
    """Graph analysis result model"""
    analysis_type: str = Field(..., description="Type of analysis")
    node_count: int = Field(0, description="Number of nodes analyzed")
    edge_count: int = Field(0, description="Number of edges analyzed")
    clusters_found: int = Field(0, description="Number of clusters found")
    key_insights: List[str] = Field(default_factory=list, description="Key insights")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Analysis metrics")


class DemoQuery(BaseModel):
    """Demo query configuration"""
    query_text: str = Field(..., description="Search query text")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    use_graph_boost: bool = Field(True, description="Use graph enhancement")
    top_k: int = Field(10, description="Number of results to return")
    min_score: float = Field(0.0, description="Minimum score threshold")
    description: Optional[str] = Field(None, description="Query description")


class DemoSection(BaseModel):
    """Demo section configuration"""
    section_number: int = Field(..., description="Section number")
    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Section description")
    queries: List[DemoQuery] = Field(default_factory=list, description="Queries to run")
    enabled: bool = Field(True, description="Whether section is enabled")


class DemoConfig(BaseModel):
    """Overall demo configuration"""
    demo_name: str = Field(..., description="Demo name")
    description: str = Field(..., description="Demo description")
    sections: List[DemoSection] = Field(default_factory=list, description="Demo sections")
    verbose: bool = Field(False, description="Verbose output")
    show_timings: bool = Field(False, description="Show execution timings")
    max_results_per_query: int = Field(5, description="Max results per query")