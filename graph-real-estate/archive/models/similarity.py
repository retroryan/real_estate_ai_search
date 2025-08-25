"""Pydantic models for similarity and relationship calculations"""
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class SimilarityMethod(str, Enum):
    """Methods used for calculating similarity"""
    PROPERTY_FEATURES = "property_features"
    PRICE_SIZE = "price_size"
    LOCATION = "location"
    TYPE_MATCH = "type_match"
    COMPOSITE = "composite"


class ProximityType(str, Enum):
    """Types of proximity relationships"""
    GEOGRAPHIC = "geographic"
    NEIGHBORHOOD = "neighborhood"
    MARKET = "market"
    TOPIC = "topic"


class PropertySimilarity(BaseModel):
    """Property-to-property similarity relationship"""
    property_a: str = Field(..., description="First property listing ID")
    property_b: str = Field(..., description="Second property listing ID")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Overall similarity score")
    
    # Component scores
    price_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    size_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    feature_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    location_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    type_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Metadata
    method: SimilarityMethod = Field(default=SimilarityMethod.COMPOSITE)
    shared_features: List[str] = Field(default_factory=list)
    similarity_reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('similarity_score')
    def validate_similarity_score(cls, v, values):
        """Ensure similarity score is reasonable"""
        if v < 0.3:  # Minimum threshold for creating relationships
            return 0.3
        return min(v, 1.0)
    
    def get_similarity_explanation(self) -> str:
        """Get human-readable explanation of similarity"""
        explanations = []
        if self.price_similarity > 0.7:
            explanations.append("similar pricing")
        if self.size_similarity > 0.7:
            explanations.append("comparable size")
        if self.feature_similarity > 0.5:
            explanations.append(f"{len(self.shared_features)} shared features")
        if self.location_similarity > 0.8:
            explanations.append("same neighborhood")
        if self.type_similarity > 0.9:
            explanations.append("same property type")
        
        return ", ".join(explanations) if explanations else "general compatibility"


class NeighborhoodConnection(BaseModel):
    """Neighborhood-to-neighborhood connection"""
    neighborhood_a: str = Field(..., description="First neighborhood ID")
    neighborhood_b: str = Field(..., description="Second neighborhood ID")
    connection_strength: float = Field(..., ge=0.0, le=1.0, description="Connection strength")
    
    # Connection factors
    geographic_proximity: float = Field(default=0.0, ge=0.0, le=1.0)
    lifestyle_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    price_range_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    wikipedia_topic_overlap: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Shared attributes
    shared_lifestyle_tags: List[str] = Field(default_factory=list)
    shared_wikipedia_topics: List[str] = Field(default_factory=list)
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    
    connection_type: str = Field(default="NEAR", description="Type of connection")
    created_at: datetime = Field(default_factory=datetime.now)


class GeographicProximity(BaseModel):
    """Geographic proximity relationship"""
    entity_a: str = Field(..., description="First entity ID")
    entity_b: str = Field(..., description="Second entity ID")
    entity_type: str = Field(..., description="Type of entities (Property, Neighborhood)")
    
    distance_km: float = Field(..., ge=0.0, description="Distance in kilometers")
    distance_miles: float = Field(..., ge=0.0, description="Distance in miles")
    
    proximity_type: ProximityType = Field(default=ProximityType.GEOGRAPHIC)
    within_walking_distance: bool = Field(default=False)
    within_driving_distance: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('distance_miles', pre=True, always=True)
    def calculate_miles_from_km(cls, v, values):
        """Calculate miles from kilometers"""
        if 'distance_km' in values:
            return values['distance_km'] * 0.621371
        return v
    
    @validator('within_walking_distance', pre=True, always=True)
    def calculate_walking_distance(cls, v, values):
        """Determine if within walking distance (1.5km)"""
        if 'distance_km' in values:
            return values['distance_km'] <= 1.5
        return v
    
    @validator('within_driving_distance', pre=True, always=True)
    def calculate_driving_distance(cls, v, values):
        """Determine if within reasonable driving distance (50km)"""
        if 'distance_km' in values:
            return values['distance_km'] <= 50.0
        return v


class TopicCluster(BaseModel):
    """Wikipedia topic-based cluster"""
    cluster_id: str = Field(..., description="Unique cluster identifier")
    topic: str = Field(..., description="Primary topic/theme")
    related_topics: List[str] = Field(default_factory=list, description="Related topics")
    
    neighborhoods: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    wikipedia_articles: List[str] = Field(default_factory=list)
    
    cluster_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    member_count: int = Field(default=0, ge=0)
    
    created_at: datetime = Field(default_factory=datetime.now)


class SimilarityLoadResult(BaseModel):
    """Result of similarity calculation and loading operation"""
    
    # Property similarities
    property_similarities_calculated: int = 0
    property_similarities_created: int = 0
    avg_property_similarity: float = 0.0
    high_similarity_pairs: int = 0  # > 0.8
    
    # Neighborhood connections
    neighborhood_connections_calculated: int = 0
    neighborhood_connections_created: int = 0
    avg_neighborhood_connection: float = 0.0
    
    # Geographic proximities
    proximity_relationships_created: int = 0
    avg_distance_km: float = 0.0
    walking_distance_pairs: int = 0
    
    # Topic clusters
    topic_clusters_created: int = 0
    total_cluster_members: int = 0
    avg_cluster_size: float = 0.0
    
    # Knowledge graph enrichment
    topic_based_connections: int = 0
    recommendation_paths_created: int = 0
    
    # Performance metrics
    properties_processed: int = 0
    neighborhoods_processed: int = 0
    calculation_time_seconds: float = 0.0
    
    # Quality metrics
    similarity_score_distribution: Dict[str, int] = Field(default_factory=dict)
    feature_overlap_stats: Dict[str, float] = Field(default_factory=dict)
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    duration_seconds: float = 0.0
    success: bool = True
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def calculate_averages(self):
        """Calculate average metrics"""
        if self.property_similarities_created > 0:
            # These would be calculated during processing
            pass
        
        if self.topic_clusters_created > 0:
            self.avg_cluster_size = self.total_cluster_members / self.topic_clusters_created


class SimilarityCalculationConfig(BaseModel):
    """Configuration for similarity calculations"""
    
    # Property similarity settings
    property_similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_property_comparisons: int = Field(default=10000, ge=100)
    same_neighborhood_bonus: float = Field(default=0.2, ge=0.0, le=0.5)
    
    # Weight factors for composite similarity
    price_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    size_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    feature_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    location_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    type_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    
    # Neighborhood connection settings
    neighborhood_connection_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    max_neighborhood_distance_km: float = Field(default=25.0, ge=1.0)
    
    # Geographic proximity settings
    max_proximity_distance_km: float = Field(default=50.0, ge=1.0)
    walking_distance_threshold_km: float = Field(default=1.5, ge=0.1)
    
    # Topic clustering settings
    min_cluster_size: int = Field(default=2, ge=1)
    topic_overlap_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    
    @validator('price_weight', 'size_weight', 'feature_weight', 'location_weight', 'type_weight')
    def validate_weights_sum(cls, v, values):
        """Ensure weights sum to approximately 1.0"""
        weights = [
            values.get('price_weight', 0.25),
            values.get('size_weight', 0.20),
            values.get('feature_weight', 0.30),
            values.get('location_weight', 0.15),
            values.get('type_weight', 0.10)
        ]
        total = sum(weights)
        if abs(total - 1.0) > 0.01:  # Allow small floating point differences
            # Normalize weights if they don't sum to 1.0
            return v / total
        return v