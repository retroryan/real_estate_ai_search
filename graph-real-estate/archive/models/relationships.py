"""Relationship models"""
from pydantic import BaseModel, Field

class SimilarityRelationship(BaseModel):
    """Similarity relationship between properties"""
    property1_id: str
    property2_id: str
    score: float = Field(..., ge=0, le=1, description="Similarity score")