"""Base API Client Models."""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

DataType = TypeVar('DataType')


class BaseRequest(BaseModel):
    """Base class for API request models."""
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class BaseResponse(BaseModel):
    """Base class for API response models."""
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class PaginatedRequest(BaseRequest):
    """Base class for paginated requests."""
    
    page: int = Field(default=1, description="Page number", ge=1)
    page_size: int = Field(default=50, description="Number of items per page", ge=1, le=1000)


class PaginatedResponse(BaseResponse, Generic[DataType]):
    """Base class for paginated responses."""
    
    data: List[DataType] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    
    @property
    def has_next(self) -> bool:
        """Check if there are more pages available."""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there are previous pages available."""
        return self.page > 1