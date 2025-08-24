"""
Data validation framework using Pydantic models.

This module provides comprehensive data validation for all input data,
ensuring data quality and consistency before processing.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class AddressModel(BaseModel):
    """Model for property address validation."""
    
    street: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$")
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate and normalize state."""
        return v.strip().upper()
    
    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        """Validate and normalize city."""
        return v.strip().title()


class PropertyModel(BaseModel):
    """Model for property data validation."""
    
    listing_id: str = Field(..., min_length=1, max_length=100)
    property_type: Optional[str] = Field(None, max_length=50)
    price: Optional[Decimal] = Field(None, ge=0, le=Decimal("999999999.99"))
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[float] = Field(None, ge=0, le=20)
    square_feet: Optional[int] = Field(None, ge=0, le=100000)
    year_built: Optional[int] = Field(None, ge=1800, le=2030)
    lot_size: Optional[int] = Field(None, ge=0, le=1000000)
    features: List[str] = Field(default_factory=list)
    address: AddressModel
    description: Optional[str] = Field(None, max_length=5000)
    
    @field_validator("listing_id")
    @classmethod
    def validate_listing_id(cls, v: str) -> str:
        """Ensure listing ID is not empty."""
        if not v or v.isspace():
            raise ValueError("Listing ID cannot be empty")
        return v.strip()
    
    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate property type."""
        if v:
            valid_types = [
                "single_family", "condo", "townhouse", "multi_family",
                "apartment", "land", "commercial", "other"
            ]
            normalized = v.lower().replace(" ", "_")
            if normalized not in valid_types:
                logger.warning(f"Unknown property type: {v}, setting to 'other'")
                return "other"
            return normalized
        return v
    
    @model_validator(mode="after")
    def validate_price_per_sqft(self) -> "PropertyModel":
        """Validate price per square foot is reasonable."""
        if self.price and self.square_feet and self.square_feet > 0:
            price_per_sqft = float(self.price) / self.square_feet
            if price_per_sqft > 10000:  # $10,000 per sqft seems unreasonable
                logger.warning(
                    f"Unusually high price per sqft: ${price_per_sqft:.2f} "
                    f"for listing {self.listing_id}"
                )
        return self


class DemographicsModel(BaseModel):
    """Model for neighborhood demographics validation."""
    
    population: Optional[int] = Field(None, ge=0, le=10000000)
    median_income: Optional[Decimal] = Field(None, ge=0, le=Decimal("1000000"))
    median_age: Optional[float] = Field(None, ge=0, le=150)
    
    @field_validator("median_age")
    @classmethod
    def validate_median_age(cls, v: Optional[float]) -> Optional[float]:
        """Validate median age is reasonable."""
        if v is not None and (v < 18 or v > 80):
            logger.warning(f"Unusual median age: {v}")
        return v


class NeighborhoodModel(BaseModel):
    """Model for neighborhood data validation."""
    
    neighborhood_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=5000)
    amenities: List[str] = Field(default_factory=list)
    demographics: Optional[DemographicsModel] = None
    
    @field_validator("neighborhood_id")
    @classmethod
    def validate_neighborhood_id(cls, v: str) -> str:
        """Ensure neighborhood ID is not empty."""
        if not v or v.isspace():
            raise ValueError("Neighborhood ID cannot be empty")
        return v.strip()
    
    @field_validator("amenities")
    @classmethod
    def validate_amenities(cls, v: List[str]) -> List[str]:
        """Clean and validate amenities list."""
        return [a.strip() for a in v if a and not a.isspace()]


class WikipediaArticleModel(BaseModel):
    """Model for Wikipedia article data validation."""
    
    page_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=500)
    url: Optional[str] = Field(None, max_length=1000)
    full_text: Optional[str] = Field(None)
    summary: Optional[str] = Field(None, max_length=5000)
    key_topics: Optional[str] = Field(None, max_length=1000)
    best_city: Optional[str] = Field(None, max_length=100)
    best_state: Optional[str] = Field(None, max_length=50)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    overall_confidence: Optional[float] = Field(None, ge=0, le=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Wikipedia URL format."""
        if v and not v.startswith(("http://", "https://")):
            return f"https://en.wikipedia.org/wiki/{v}"
        return v
    
    @field_validator("relevance_score", "overall_confidence")
    @classmethod
    def validate_scores(cls, v: Optional[float]) -> Optional[float]:
        """Ensure scores are between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            logger.warning(f"Score out of range [0, 1]: {v}, clamping")
            return max(0, min(1, v))
        return v


class DataQualityMetrics(BaseModel):
    """Model for data quality metrics."""
    
    total_records: int = Field(ge=0)
    valid_records: int = Field(ge=0)
    invalid_records: int = Field(ge=0)
    missing_fields: Dict[str, int] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0, le=1)
    
    @model_validator(mode="after")
    def validate_totals(self) -> "DataQualityMetrics":
        """Ensure record counts are consistent."""
        if self.valid_records + self.invalid_records != self.total_records:
            raise ValueError("Valid + invalid records must equal total records")
        return self
    
    def add_error(self, error: str) -> None:
        """Add a validation error to the list."""
        self.validation_errors.append(error)
        if len(self.validation_errors) > 100:
            # Keep only last 100 errors to avoid memory issues
            self.validation_errors = self.validation_errors[-100:]
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score."""
        if self.total_records == 0:
            return 0.0
        
        # Base score from valid records ratio
        base_score = self.valid_records / self.total_records
        
        # Penalty for missing fields
        missing_penalty = sum(self.missing_fields.values()) / (self.total_records * 10)
        missing_penalty = min(0.3, missing_penalty)  # Cap penalty at 30%
        
        self.quality_score = max(0, base_score - missing_penalty)
        return self.quality_score


class DataValidator:
    """Validates data using Pydantic models."""
    
    def __init__(self):
        """Initialize the data validator."""
        self.metrics = DataQualityMetrics(
            total_records=0,
            valid_records=0,
            invalid_records=0,
            quality_score=0.0
        )
    
    def validate_property(self, data: Dict[str, Any]) -> Optional[PropertyModel]:
        """
        Validate property data.
        
        Args:
            data: Raw property data dictionary
            
        Returns:
            Validated PropertyModel or None if invalid
        """
        try:
            model = PropertyModel(**data)
            self.metrics.valid_records += 1
            return model
        except Exception as e:
            self.metrics.invalid_records += 1
            self.metrics.add_error(f"Property validation error: {str(e)}")
            logger.error(f"Failed to validate property: {e}")
            return None
    
    def validate_neighborhood(self, data: Dict[str, Any]) -> Optional[NeighborhoodModel]:
        """
        Validate neighborhood data.
        
        Args:
            data: Raw neighborhood data dictionary
            
        Returns:
            Validated NeighborhoodModel or None if invalid
        """
        try:
            model = NeighborhoodModel(**data)
            self.metrics.valid_records += 1
            return model
        except Exception as e:
            self.metrics.invalid_records += 1
            self.metrics.add_error(f"Neighborhood validation error: {str(e)}")
            logger.error(f"Failed to validate neighborhood: {e}")
            return None
    
    def validate_wikipedia(self, data: Dict[str, Any]) -> Optional[WikipediaArticleModel]:
        """
        Validate Wikipedia article data.
        
        Args:
            data: Raw Wikipedia article data dictionary
            
        Returns:
            Validated WikipediaArticleModel or None if invalid
        """
        try:
            model = WikipediaArticleModel(**data)
            self.metrics.valid_records += 1
            return model
        except Exception as e:
            self.metrics.invalid_records += 1
            self.metrics.add_error(f"Wikipedia validation error: {str(e)}")
            logger.error(f"Failed to validate Wikipedia article: {e}")
            return None
    
    
    def get_metrics(self) -> DataQualityMetrics:
        """Get current validation metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset validation metrics."""
        self.metrics = DataQualityMetrics(
            total_records=0,
            valid_records=0,
            invalid_records=0,
            quality_score=0.0
        )