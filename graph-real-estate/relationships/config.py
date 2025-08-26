"""
Configuration models for relationship building using Pydantic.
"""

from typing import List
from pydantic import BaseModel, Field


class RelationshipConfig(BaseModel):
    """Configuration for relationship building."""
    
    batch_size: int = Field(
        default=1000, 
        ge=100, 
        le=10000,
        description="Batch size for processing relationships"
    )
    
    similarity_threshold: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0,
        description="Minimum similarity score for SIMILAR_TO relationships"
    )
    
    price_ranges: List[str] = Field(
        default=[
            "0-250K",
            "250K-500K",
            "500K-750K",
            "750K-1M",
            "1M-2M",
            "2M-5M",
            "5M+"
        ],
        description="Price ranges for IN_PRICE_RANGE relationships"
    )
    
    verbose: bool = Field(
        default=True,
        description="Enable verbose logging"
    )
    
    class Config:
        validate_assignment = True  # Validates when fields are changed after creation