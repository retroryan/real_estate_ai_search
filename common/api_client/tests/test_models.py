"""Tests for API Client Models."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from ..models import BaseRequest, BaseResponse, PaginatedRequest, PaginatedResponse


class TestUser:
    """Test data model."""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class TestPaginatedRequest(PaginatedRequest):
    """Test paginated request model."""
    category: str = "default"


class TestPaginatedResponse(PaginatedResponse[dict]):
    """Test paginated response model."""
    pass


class TestModels:
    """Tests for API Client Models."""
    
    def test_base_request_creation(self):
        """Test BaseRequest creation."""
        request = BaseRequest()
        assert isinstance(request, BaseRequest)
    
    def test_base_request_validation(self):
        """Test BaseRequest validation."""
        # BaseRequest should forbid extra fields
        with pytest.raises(PydanticValidationError):
            BaseRequest(extra_field="not allowed")
    
    def test_base_response_creation(self):
        """Test BaseResponse creation."""
        response = BaseResponse()
        assert isinstance(response, BaseResponse)
    
    def test_base_response_validation(self):
        """Test BaseResponse validation."""
        # BaseResponse should forbid extra fields
        with pytest.raises(PydanticValidationError):
            BaseResponse(extra_field="not allowed")
    
    def test_paginated_request_defaults(self):
        """Test PaginatedRequest default values."""
        request = PaginatedRequest()
        
        assert request.page == 1
        assert request.page_size == 50
    
    def test_paginated_request_custom_values(self):
        """Test PaginatedRequest with custom values."""
        request = PaginatedRequest(page=2, page_size=25)
        
        assert request.page == 2
        assert request.page_size == 25
    
    def test_paginated_request_validation_page_too_small(self):
        """Test PaginatedRequest validation for page too small."""
        with pytest.raises(PydanticValidationError):
            PaginatedRequest(page=0)
    
    def test_paginated_request_validation_page_size_too_small(self):
        """Test PaginatedRequest validation for page_size too small."""
        with pytest.raises(PydanticValidationError):
            PaginatedRequest(page_size=0)
    
    def test_paginated_request_validation_page_size_too_large(self):
        """Test PaginatedRequest validation for page_size too large."""
        with pytest.raises(PydanticValidationError):
            PaginatedRequest(page_size=1001)
    
    def test_paginated_request_inheritance(self):
        """Test PaginatedRequest inheritance."""
        request = TestPaginatedRequest(page=2, category="test")
        
        assert request.page == 2
        assert request.page_size == 50
        assert request.category == "test"
    
    def test_paginated_response_creation(self):
        """Test PaginatedResponse creation."""
        data = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        response = TestPaginatedResponse(
            data=data,
            total=2,
            page=1,
            page_size=50,
            total_pages=1
        )
        
        assert response.data == data
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 50
        assert response.total_pages == 1
    
    def test_paginated_response_has_next_true(self):
        """Test PaginatedResponse.has_next when there are more pages."""
        response = TestPaginatedResponse(
            data=[],
            total=100,
            page=1,
            page_size=50,
            total_pages=2
        )
        
        assert response.has_next is True
    
    def test_paginated_response_has_next_false(self):
        """Test PaginatedResponse.has_next when on last page."""
        response = TestPaginatedResponse(
            data=[],
            total=50,
            page=1,
            page_size=50,
            total_pages=1
        )
        
        assert response.has_next is False
    
    def test_paginated_response_has_previous_true(self):
        """Test PaginatedResponse.has_previous when not on first page."""
        response = TestPaginatedResponse(
            data=[],
            total=100,
            page=2,
            page_size=50,
            total_pages=2
        )
        
        assert response.has_previous is True
    
    def test_paginated_response_has_previous_false(self):
        """Test PaginatedResponse.has_previous when on first page."""
        response = TestPaginatedResponse(
            data=[],
            total=50,
            page=1,
            page_size=50,
            total_pages=1
        )
        
        assert response.has_previous is False
    
    def test_paginated_response_validation_negative_total(self):
        """Test PaginatedResponse validation for negative total."""
        with pytest.raises(PydanticValidationError):
            TestPaginatedResponse(
                data=[],
                total=-1,
                page=1,
                page_size=50,
                total_pages=0
            )
    
    def test_paginated_response_validation_page_too_small(self):
        """Test PaginatedResponse validation for page too small."""
        with pytest.raises(PydanticValidationError):
            TestPaginatedResponse(
                data=[],
                total=0,
                page=0,
                page_size=50,
                total_pages=0
            )
    
    def test_paginated_response_validation_page_size_too_small(self):
        """Test PaginatedResponse validation for page_size too small."""
        with pytest.raises(PydanticValidationError):
            TestPaginatedResponse(
                data=[],
                total=0,
                page=1,
                page_size=0,
                total_pages=0
            )
    
    def test_paginated_response_validation_negative_total_pages(self):
        """Test PaginatedResponse validation for negative total_pages."""
        with pytest.raises(PydanticValidationError):
            TestPaginatedResponse(
                data=[],
                total=0,
                page=1,
                page_size=50,
                total_pages=-1
            )