"""Common API Client Framework."""

from .base import BaseAPIClient
from .config import APIClientConfig
from .config_loader import ConfigLoader
from .exceptions import APIError, ValidationError, NotFoundError, TimeoutError, ServerError, ClientError
from .models import BaseRequest, BaseResponse, PaginatedRequest, PaginatedResponse
from .property_client import PropertyAPIClient
from .property_models import (
    PropertyListRequest,
    PropertyListResponse,
    PropertyResponse,
    NeighborhoodListRequest,
    NeighborhoodListResponse,
    NeighborhoodResponse
)
from .wikipedia_client import WikipediaAPIClient
from .wikipedia_models import (
    WikipediaArticleListRequest,
    WikipediaArticleListResponse,
    WikipediaArticleResponse,
    WikipediaSummaryListRequest,
    WikipediaSummaryListResponse,
    WikipediaSummaryResponse
)

__all__ = [
    'BaseAPIClient',
    'APIClientConfig',
    'ConfigLoader', 
    'APIError',
    'ValidationError',
    'NotFoundError', 
    'TimeoutError',
    'ServerError',
    'ClientError',
    'BaseRequest',
    'BaseResponse',
    'PaginatedRequest',
    'PaginatedResponse',
    'PropertyAPIClient',
    'PropertyListRequest',
    'PropertyListResponse',
    'PropertyResponse',
    'NeighborhoodListRequest',
    'NeighborhoodListResponse',
    'NeighborhoodResponse',
    'WikipediaAPIClient',
    'WikipediaArticleListRequest',
    'WikipediaArticleListResponse',
    'WikipediaArticleResponse',
    'WikipediaSummaryListRequest',
    'WikipediaSummaryListResponse',
    'WikipediaSummaryResponse'
]