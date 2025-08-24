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
from .stats_client import StatsAPIClient
from .stats_models import (
    DataSummaryStats,
    PropertyStats,
    NeighborhoodStats,
    WikipediaStats,
    CoverageStats,
    EnrichmentStats,
    StatsSummaryResponse,
    PropertyStatsResponse,
    NeighborhoodStatsResponse,
    WikipediaStatsResponse,
    CoverageStatsResponse,
    EnrichmentStatsResponse
)
from .system_client import SystemAPIClient, HealthStatus, RootInfo
from .client_factory import APIClientFactory

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
    'WikipediaSummaryResponse',
    'StatsAPIClient',
    'DataSummaryStats',
    'PropertyStats',
    'NeighborhoodStats',
    'WikipediaStats',
    'CoverageStats',
    'EnrichmentStats',
    'StatsSummaryResponse',
    'PropertyStatsResponse',
    'NeighborhoodStatsResponse',
    'WikipediaStatsResponse',
    'CoverageStatsResponse',
    'EnrichmentStatsResponse',
    'SystemAPIClient',
    'HealthStatus',
    'RootInfo',
    'APIClientFactory'
]