import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import httpx
from circuitbreaker import circuit
from models.api_configuration import ApiProvider

logger = logging.getLogger(__name__)


class ApiErrorType(Enum):
    """Types of API errors for classification"""
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    QUOTA_EXCEEDED = "quota_exceeded"


class ApiException(Exception):
    """Base exception for API-related errors"""
    def __init__(self, message: str, error_type: ApiErrorType, provider: ApiProvider,
                 status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.error_type = error_type
        self.provider = provider
        self.status_code = status_code
        self.response_data = response_data
        self.timestamp = datetime.now()


class ApiTimeoutException(ApiException):
    """Exception for API timeout errors"""
    def __init__(self, provider: ApiProvider, timeout_seconds: int):
        super().__init__(
            f"API request to {provider.value} timed out after {timeout_seconds} seconds",
            ApiErrorType.TIMEOUT,
            provider
        )
        self.timeout_seconds = timeout_seconds


class ApiRateLimitException(ApiException):
    """Exception for rate limit errors"""
    def __init__(self, provider: ApiProvider, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {provider.value}"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message, ApiErrorType.RATE_LIMITED, provider)
        self.retry_after = retry_after


class ApiAuthenticationException(ApiException):
    """Exception for authentication errors"""
    def __init__(self, provider: ApiProvider, message: str = "Authentication failed"):
        super().__init__(
            f"Authentication error for {provider.value}: {message}",
            ApiErrorType.AUTHENTICATION,
            provider,
            status_code=401
        )


class ApiCircuitBreakerOpen(ApiException):
    """Exception when circuit breaker is open"""
    def __init__(self, provider: ApiProvider):
        super().__init__(
            f"Circuit breaker is open for {provider.value}, API calls are blocked",
            ApiErrorType.SERVER_ERROR,
            provider
        )


class ApiErrorHandler:
    """Comprehensive error handling for API calls with circuit breaker and retry logic"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.circuit_breakers: Dict[str, Any] = {}

    def _get_circuit_breaker(self, provider: ApiProvider, threshold: int = 5,
                           recovery_timeout: int = 30) -> Callable:
        """Get or create circuit breaker for provider"""
        key = provider.value

        if key not in self.circuit_breakers:
            @circuit(failure_threshold=threshold, recovery_timeout=recovery_timeout,
                    expected_exception=ApiException)
            async def provider_circuit_breaker(func: Callable, *args, **kwargs):
                return await func(*args, **kwargs)

            self.circuit_breakers[key] = provider_circuit_breaker

        return self.circuit_breakers[key]

    async def handle_api_call(self,
                            provider: ApiProvider,
                            api_call: Callable[[], Awaitable[Any]],
                            config: Any,
                            max_retries: int = 3) -> Any:
        """
        Handle API call with comprehensive error handling, retries, and circuit breaker
        """
        circuit_breaker = self._get_circuit_breaker(
            provider,
            config.circuit_breaker_threshold,
            30  # 30 second recovery timeout
        )

        async def wrapped_call():
            return await self._execute_with_retries(provider, api_call, config, max_retries)

        try:
            return await circuit_breaker(wrapped_call)
        except Exception as e:
            if "CircuitBreakerOpenException" in str(type(e)):
                raise ApiCircuitBreakerOpen(provider)
            raise

    async def _execute_with_retries(self,
                                  provider: ApiProvider,
                                  api_call: Callable[[], Awaitable[Any]],
                                  config: Any,
                                  max_retries: int) -> Any:
        """Execute API call with exponential backoff retry logic"""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # Create timeout for the API call
                result = await asyncio.wait_for(
                    api_call(),
                    timeout=config.timeout
                )

                # Success - reset error tracking
                self._reset_error_tracking(provider)
                return result

            except asyncio.TimeoutError:
                last_exception = ApiTimeoutException(provider, config.timeout)
                logger.warning(f"Timeout on attempt {attempt + 1} for {provider.value}")

            except httpx.HTTPStatusError as e:
                last_exception = self._handle_http_error(provider, e)
                logger.warning(f"HTTP error on attempt {attempt + 1} for {provider.value}: {e}")

            except httpx.RequestError as e:
                last_exception = ApiException(
                    f"Network error for {provider.value}: {str(e)}",
                    ApiErrorType.NETWORK_ERROR,
                    provider
                )
                logger.warning(f"Network error on attempt {attempt + 1} for {provider.value}: {e}")

            except Exception as e:
                last_exception = ApiException(
                    f"Unexpected error for {provider.value}: {str(e)}",
                    ApiErrorType.SERVER_ERROR,
                    provider
                )
                logger.error(f"Unexpected error on attempt {attempt + 1} for {provider.value}: {e}")

            # Track error
            self._track_error(provider, last_exception)

            # Don't retry on certain error types
            if last_exception and last_exception.error_type in [
                ApiErrorType.AUTHENTICATION,
                ApiErrorType.NOT_FOUND,
                ApiErrorType.INVALID_RESPONSE
            ]:
                break

            # Calculate delay for next retry
            if attempt < max_retries:
                delay = self._calculate_backoff_delay(attempt, provider, last_exception)
                logger.info(f"Retrying {provider.value} in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            raise ApiException(
                f"All retries exhausted for {provider.value}",
                ApiErrorType.SERVER_ERROR,
                provider
            )

    def _handle_http_error(self, provider: ApiProvider, error: httpx.HTTPStatusError) -> ApiException:
        """Convert HTTP errors to appropriate API exceptions"""
        status_code = error.response.status_code

        if status_code == 401:
            return ApiAuthenticationException(provider, "Invalid API key")
        elif status_code == 403:
            return ApiAuthenticationException(provider, "Forbidden - check API key permissions")
        elif status_code == 404:
            return ApiException(
                f"Resource not found for {provider.value}",
                ApiErrorType.NOT_FOUND,
                provider,
                status_code
            )
        elif status_code == 429:
            # Extract retry-after header if available
            retry_after = None
            if "retry-after" in error.response.headers:
                try:
                    retry_after = int(error.response.headers["retry-after"])
                except ValueError:
                    pass
            return ApiRateLimitException(provider, retry_after)
        elif status_code >= 500:
            return ApiException(
                f"Server error for {provider.value}: {status_code}",
                ApiErrorType.SERVER_ERROR,
                provider,
                status_code
            )
        else:
            return ApiException(
                f"HTTP error for {provider.value}: {status_code}",
                ApiErrorType.SERVER_ERROR,
                provider,
                status_code
            )

    def _calculate_backoff_delay(self, attempt: int, provider: ApiProvider,
                               last_exception: ApiException) -> float:
        """Calculate exponential backoff delay with jitter"""
        # Base delay for exponential backoff
        base_delay = min(2 ** attempt, 60)  # Cap at 60 seconds

        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.1, 0.3) * base_delay

        # Special handling for rate limit errors
        if (last_exception and
            last_exception.error_type == ApiErrorType.RATE_LIMITED and
            hasattr(last_exception, 'retry_after') and
            last_exception.retry_after):
            return max(last_exception.retry_after, base_delay + jitter)

        return base_delay + jitter

    def _track_error(self, provider: ApiProvider, exception: ApiException):
        """Track errors for monitoring and circuit breaker logic"""
        key = provider.value
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.last_errors[key] = exception.timestamp

        logger.error(
            f"API error for {provider.value}: {exception.error_type.value} - {str(exception)}",
            extra={
                "provider": provider.value,
                "error_type": exception.error_type.value,
                "error_count": self.error_counts[key],
                "status_code": exception.status_code
            }
        )

    def _reset_error_tracking(self, provider: ApiProvider):
        """Reset error tracking on successful call"""
        key = provider.value
        if key in self.error_counts:
            self.error_counts[key] = 0

    def get_error_stats(self, provider: ApiProvider) -> Dict:
        """Get error statistics for a provider"""
        key = provider.value
        return {
            "provider": provider.value,
            "error_count": self.error_counts.get(key, 0),
            "last_error": self.last_errors.get(key),
            "circuit_breaker_state": "closed"  # Simplified for now
        }

    def reset_circuit_breaker(self, provider: ApiProvider):
        """Manually reset circuit breaker for a provider"""
        key = provider.value
        if key in self.circuit_breakers:
            # Reset the circuit breaker state
            # This is implementation-specific to the circuit breaker library
            pass

    async def health_check(self, provider: ApiProvider, health_check_call: Callable) -> bool:
        """Perform health check for a provider"""
        try:
            await asyncio.wait_for(health_check_call(), timeout=5.0)
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {provider.value}: {e}")
            return False