"""Base API Client Implementation."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Type, TypeVar, Union
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .config import APIClientConfig
from .exceptions import (
    APIError, 
    ClientError, 
    NotFoundError, 
    ServerError, 
    TimeoutError, 
    ValidationError
)
from .models import BaseRequest, BaseResponse, PaginatedRequest, PaginatedResponse

T = TypeVar('T', bound=BaseModel)


class BaseAPIClient(ABC):
    """Abstract base class for API clients."""
    
    def __init__(
        self, 
        config: APIClientConfig, 
        logger: logging.Logger,
        http_client: Optional[httpx.Client] = None
    ):
        """Initialize the API client.
        
        Args:
            config: API client configuration
            logger: Logger instance for structured logging
            http_client: Optional HTTP client for testing/mocking
        """
        self.config = config
        self.logger = logger
        self._http_client = http_client or httpx.Client(
            base_url=str(config.base_url),
            timeout=config.timeout,
            headers=config.default_headers or {}
        )
        
        self.logger.info(
            "Initialized API client",
            extra={
                "base_url": str(config.base_url),
                "timeout": config.timeout
            }
        )
    
    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, '_http_client'):
            try:
                self._http_client.close()
            except Exception:
                pass
    
    def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Union[Dict[str, Any], T]:
        """Make a GET request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            response_model: Optional Pydantic model for response validation
            
        Returns:
            Response data as dict or validated model
            
        Raises:
            APIError: If request fails
        """
        return self._execute_request(
            method="GET",
            endpoint=endpoint, 
            params=params,
            response_model=response_model
        )
    
    def post(
        self,
        endpoint: str,
        data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Union[Dict[str, Any], T]:
        """Make a POST request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            response_model: Optional Pydantic model for response validation
            
        Returns:
            Response data as dict or validated model
            
        Raises:
            APIError: If request fails
        """
        json_data = None
        if data:
            json_data = data.model_dump() if isinstance(data, BaseModel) else data
        
        return self._execute_request(
            method="POST",
            endpoint=endpoint,
            json=json_data,
            response_model=response_model
        )
    
    def put(
        self,
        endpoint: str,
        data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Union[Dict[str, Any], T]:
        """Make a PUT request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            response_model: Optional Pydantic model for response validation
            
        Returns:
            Response data as dict or validated model
            
        Raises:
            APIError: If request fails
        """
        json_data = None
        if data:
            json_data = data.model_dump() if isinstance(data, BaseModel) else data
        
        return self._execute_request(
            method="PUT",
            endpoint=endpoint,
            json=json_data,
            response_model=response_model
        )
    
    def delete(self, endpoint: str) -> None:
        """Make a DELETE request.
        
        Args:
            endpoint: API endpoint path
            
        Raises:
            APIError: If request fails
        """
        self._execute_request(method="DELETE", endpoint=endpoint)
    
    def paginate(
        self,
        endpoint: str,
        request_model: Type[PaginatedRequest],
        response_model: Type[PaginatedResponse],
        page_size: int = 50,
        **kwargs
    ) -> Iterator[List[BaseModel]]:
        """Iterate through paginated results.
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model for request
            response_model: Pydantic model for response
            page_size: Number of items per page
            **kwargs: Additional parameters for request
            
        Yields:
            Lists of items from each page
            
        Raises:
            APIError: If request fails
        """
        page = 1
        
        while True:
            # Create request with current page
            request_data = request_model(page=page, page_size=page_size, **kwargs)
            
            self.logger.debug(
                f"Fetching page {page}",
                extra={"endpoint": endpoint, "page_size": page_size}
            )
            
            # Make request
            response_data = self.get(endpoint, params=request_data.model_dump())
            
            # Validate response
            try:
                response = response_model(**response_data)
            except PydanticValidationError as e:
                raise ValidationError(f"Response validation failed: {e}") from e
            
            # Yield data from this page
            if response.data:
                yield response.data
            
            # Check if there are more pages
            if not response.has_next:
                break
                
            page += 1
            
        self.logger.info(
            f"Completed pagination for {endpoint}",
            extra={"total_pages": page}
        )
    
    def _execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Union[Dict[str, Any], T, None]:
        """Execute an HTTP request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json: JSON body data
            response_model: Optional Pydantic model for response validation
            
        Returns:
            Response data or None for DELETE
            
        Raises:
            APIError: If request fails
        """
        # Prepare request
        url = endpoint if endpoint.startswith('http') else endpoint
        
        self.logger.debug(
            f"Making {method} request",
            extra={
                "endpoint": endpoint,
                "params": params,
                "has_json": json is not None
            }
        )
        
        try:
            # Make HTTP request
            response = self._http_client.request(
                method=method,
                url=url,
                params=params,
                json=json
            )
            
            # Log response
            self.logger.debug(
                f"Received response",
                extra={
                    "status_code": response.status_code,
                    "endpoint": endpoint
                }
            )
            
            # Handle different status codes
            if response.status_code == 404:
                raise NotFoundError(
                    f"Resource not found: {endpoint}",
                    status_code=response.status_code
                )
            elif 400 <= response.status_code < 500:
                raise ClientError(
                    f"Client error: {response.text}",
                    status_code=response.status_code,
                    response_data=self._safe_json(response)
                )
            elif 500 <= response.status_code:
                raise ServerError(
                    f"Server error: {response.text}",
                    status_code=response.status_code,
                    response_data=self._safe_json(response)
                )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Handle DELETE requests (no response body expected)
            if method == "DELETE":
                return None
            
            # Parse JSON response
            try:
                response_data = response.json()
            except Exception as e:
                raise APIError(f"Failed to parse JSON response: {e}") from e
            
            # Validate response if model provided
            if response_model:
                try:
                    return response_model(**response_data)
                except PydanticValidationError as e:
                    raise ValidationError(f"Response validation failed: {e}") from e
            
            return response_data
            
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {endpoint}") from e
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}") from e
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"Unexpected error: {e}") from e
    
    def _safe_json(self, response: httpx.Response) -> Optional[Dict[str, Any]]:
        """Safely parse JSON response.
        
        Args:
            response: HTTP response
            
        Returns:
            Parsed JSON data or None if parsing fails
        """
        try:
            return response.json()
        except Exception:
            return None