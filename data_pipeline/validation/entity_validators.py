"""
Entity-specific data validation framework using Pydantic models.

This module provides separate validators for each entity type,
using entity-specific validation logic for each data type.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import the models from the original data_validation.py
from data_pipeline.validation.data_validation import (
    PropertyModel,
    NeighborhoodModel, 
    WikipediaArticleModel,
    DataQualityMetrics,
)


class BaseValidator(ABC):
    """Base class for entity-specific validators."""
    
    def __init__(self):
        """Initialize the validator with metrics tracking."""
        self.metrics = DataQualityMetrics(
            total_records=0,
            valid_records=0,
            invalid_records=0,
            quality_score=0.0
        )
    
    @abstractmethod
    def validate_single(self, data: Dict[str, Any]) -> Optional[BaseModel]:
        """
        Validate a single data record.
        
        Must be implemented by entity-specific validators.
        """
        pass
    
    def validate_batch(self, data_list: List[Dict[str, Any]]) -> List[BaseModel]:
        """
        Validate a batch of data records.
        
        Args:
            data_list: List of raw data dictionaries
            
        Returns:
            List of validated models
        """
        self.metrics.total_records = len(data_list)
        validated = []
        
        for data in data_list:
            model = self.validate_single(data)
            if model:
                validated.append(model)
        
        self.metrics.calculate_quality_score()
        return validated
    
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


class PropertyValidator(BaseValidator):
    """Validator specifically for property data."""
    
    def validate_single(self, data: Dict[str, Any]) -> Optional[PropertyModel]:
        """
        Validate a single property record.
        
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
    
    def validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """
        Check if property has minimum required fields.
        
        Args:
            data: Raw property data dictionary
            
        Returns:
            True if all required fields are present
        """
        required_fields = ["listing_id", "address"]
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required property field: {field}")
                return False
        return True


class NeighborhoodValidator(BaseValidator):
    """Validator specifically for neighborhood data."""
    
    def validate_single(self, data: Dict[str, Any]) -> Optional[NeighborhoodModel]:
        """
        Validate a single neighborhood record.
        
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
    
    def validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """
        Check if neighborhood has minimum required fields.
        
        Args:
            data: Raw neighborhood data dictionary
            
        Returns:
            True if all required fields are present
        """
        required_fields = ["neighborhood_id", "name", "city", "state"]
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required neighborhood field: {field}")
                return False
        return True


class WikipediaValidator(BaseValidator):
    """Validator specifically for Wikipedia article data."""
    
    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize Wikipedia validator.
        
        Args:
            min_confidence: Minimum confidence threshold for articles
        """
        super().__init__()
        self.min_confidence = min_confidence
    
    def validate_single(self, data: Dict[str, Any]) -> Optional[WikipediaArticleModel]:
        """
        Validate a single Wikipedia article record.
        
        Args:
            data: Raw Wikipedia article data dictionary
            
        Returns:
            Validated WikipediaArticleModel or None if invalid
        """
        try:
            model = WikipediaArticleModel(**data)
            
            # Apply confidence threshold check
            if (model.overall_confidence is not None and 
                model.overall_confidence < self.min_confidence):
                logger.debug(f"Wikipedia article {model.page_id} below confidence threshold")
                self.metrics.invalid_records += 1
                return None
            
            self.metrics.valid_records += 1
            return model
        except Exception as e:
            self.metrics.invalid_records += 1
            self.metrics.add_error(f"Wikipedia validation error: {str(e)}")
            logger.error(f"Failed to validate Wikipedia article: {e}")
            return None
    
    def validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """
        Check if Wikipedia article has minimum required fields.
        
        Args:
            data: Raw Wikipedia article data dictionary
            
        Returns:
            True if all required fields are present
        """
        required_fields = ["page_id", "title"]
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required Wikipedia field: {field}")
                return False
        return True
    
    def has_location_data(self, data: Dict[str, Any]) -> bool:
        """
        Check if Wikipedia article has location information.
        
        Args:
            data: Raw Wikipedia article data dictionary
            
        Returns:
            True if article has location data
        """
        location_fields = ["best_city", "best_state", "latitude", "longitude"]
        return any(data.get(field) is not None for field in location_fields)


# Factory function for creating appropriate validators
def create_validator(entity_type: str, **kwargs) -> BaseValidator:
    """
    Create an appropriate validator for the given entity type.
    
    Args:
        entity_type: Type of entity ("property", "neighborhood", "wikipedia")
        **kwargs: Additional arguments for validator initialization
        
    Returns:
        Appropriate validator instance
    """
    entity_type_lower = entity_type.lower()
    
    if entity_type_lower == "property":
        return PropertyValidator()
    elif entity_type_lower == "neighborhood":
        return NeighborhoodValidator() 
    elif entity_type_lower in ["wikipedia", "wikipedia_article"]:
        return WikipediaValidator(**kwargs)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")