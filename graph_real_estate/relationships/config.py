"""
Configuration models for relationship building using Pydantic.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator


class RelationshipResult(BaseModel):
    """Result model for relationship creation operations."""
    
    relationship_type: str = Field(..., description="Type of relationship created")
    count: int = Field(ge=0, description="Number of relationships created")
    success: bool = Field(default=True, description="Whether operation succeeded")
    error_message: str = Field(default="", description="Error message if failed")
    execution_time: float = Field(ge=0.0, description="Execution time in seconds")
    
    class Config:
        validate_assignment = True


class RelationshipBatchConfig(BaseModel):
    """Configuration for batch processing relationships."""
    
    batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Size of batches for processing large datasets"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed operations"
    )
    
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        description="Delay between retry attempts in seconds"
    )


class RelationshipConfig(BaseModel):
    """Configuration for relationship building."""
    
    batch_size: int = Field(
        default=1000, 
        ge=100, 
        le=10000,
        description="Batch size for processing relationships"
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
    
    batch_config: RelationshipBatchConfig = Field(
        default_factory=RelationshipBatchConfig,
        description="Batch processing configuration"
    )
    
    enable_performance_monitoring: bool = Field(
        default=True,
        description="Enable performance monitoring and timing"
    )
    
    @validator('price_ranges')
    def validate_price_ranges(cls, v):
        """Validate price ranges format."""
        for price_range in v:
            if not (price_range.endswith('+') or '-' in price_range):
                raise ValueError(f"Invalid price range format: {price_range}")
        return v
    
    class Config:
        validate_assignment = True  # Validates when fields are changed after creation