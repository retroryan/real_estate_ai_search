"""
Resilience patterns for search operations.
Implements circuit breaker and retry logic.
"""

import time
from typing import Callable, Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum

# For Python 3.10 compatibility
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11"""
        pass
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from .exceptions import SearchError, SearchTimeoutError, CircuitBreakerError


logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CircuitState(StrEnum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception_types: tuple = field(default_factory=lambda: (SearchError,))
    excluded_exception_types: tuple = field(default_factory=tuple)


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker pattern implementation for search resilience.
    Prevents cascading failures by temporarily blocking calls to failing services.
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize the circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.logger = logger.bind(component="CircuitBreaker")
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails and circuit allows
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker entering half-open state")
            else:
                raise CircuitBreakerError(
                    "Circuit breaker is open",
                    error_code="CIRCUIT_OPEN"
                )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.excluded_exception_types:
            # Don't count excluded exceptions
            raise
            
        except self.config.expected_exception_types as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt reset.
        
        Returns:
            True if circuit should attempt reset
        """
        if self.last_failure_time is None:
            return False
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.logger.info("Circuit breaker closed after successful call")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.logger.warning("Circuit breaker opened from half-open state")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                "Circuit breaker opened",
                failures=self.failure_count,
                threshold=self.config.failure_threshold
            )
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger.info("Circuit breaker manually reset")
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED


class SearchRetryHandler:
    """
    Retry handler for search operations with exponential backoff.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 10.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_attempts: Maximum number of retry attempts
            min_wait: Minimum wait time between retries (seconds)
            max_wait: Maximum wait time between retries (seconds)
        """
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.logger = logger.bind(component="SearchRetryHandler")
    
    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Wrap a function with retry logic.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function with retry logic
        """
        @retry(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.min_wait,
                max=self.max_wait
            ),
            retry=retry_if_exception_type((SearchTimeoutError, SearchError)),
            reraise=True
        )
        def wrapper(*args, **kwargs):
            try:
                self.logger.debug(f"Executing {func.__name__}")
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(
                    f"Function {func.__name__} failed",
                    error=str(e)
                )
                raise
        
        return wrapper


class ResilientSearchEngine:
    """
    Wrapper for search engine with resilience patterns.
    Combines circuit breaker and retry logic.
    """
    
    def __init__(
        self,
        search_engine,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[dict] = None
    ):
        """
        Initialize resilient search engine.
        
        Args:
            search_engine: Base search engine instance
            circuit_config: Circuit breaker configuration
            retry_config: Retry handler configuration
        """
        self.search_engine = search_engine
        self.circuit_breaker = CircuitBreaker(circuit_config)
        
        retry_config = retry_config or {}
        self.retry_handler = SearchRetryHandler(**retry_config)
        
        self.logger = logger.bind(component="ResilientSearchEngine")
    
    def search(self, request):
        """
        Execute search with resilience patterns.
        
        Args:
            request: Search request
            
        Returns:
            Search response
            
        Raises:
            CircuitBreakerError: If circuit is open
            SearchError: If search fails after retries
        """
        # Wrap search with retry logic
        retryable_search = self.retry_handler.with_retry(
            self.search_engine.search
        )
        
        # Execute with circuit breaker
        try:
            return self.circuit_breaker.call(retryable_search, request)
        except RetryError as e:
            self.logger.error("Search failed after retries", error=str(e))
            raise SearchError(
                "Search failed after maximum retries",
                error_code="MAX_RETRIES_EXCEEDED"
            )
    
    def health_check(self) -> dict:
        """
        Get health status of the resilient search engine.
        
        Returns:
            Health status dictionary
        """
        return {
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "is_healthy": self.circuit_breaker.is_closed
            },
            "retry_handler": {
                "max_attempts": self.retry_handler.max_attempts
            }
        }