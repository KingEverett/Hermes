"""
Test suite for API error handling, circuit breaker, and retry logic.

This module validates the comprehensive error handling system including:
- Circuit breaker pattern implementation
- Exponential backoff retry logic
- Error classification and exception handling
- Timeout handling
- HTTP status code mapping
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import httpx

from services.config.api_error_handler import (
    ApiErrorHandler,
    ApiException,
    ApiTimeoutException,
    ApiRateLimitException,
    ApiAuthenticationException,
    ApiCircuitBreakerOpen,
    ApiErrorType
)
from models.api_configuration import ApiProvider


class TestApiErrorHandler:
    """Test cases for ApiErrorHandler core functionality"""

    @pytest.fixture
    def error_handler(self):
        """Create ApiErrorHandler instance for testing"""
        return ApiErrorHandler()

    @pytest.fixture
    def mock_config(self):
        """Create mock API configuration"""
        config = MagicMock()
        config.timeout = 30
        config.retry_attempts = 3
        config.circuit_breaker_threshold = 5
        return config

    @pytest.mark.asyncio
    async def test_successful_api_call(self, error_handler, mock_config):
        """Test successful API call with no errors"""
        async def successful_call():
            return {"status": "success", "data": "test"}

        result = await error_handler.handle_api_call(
            ApiProvider.NVD,
            successful_call,
            mock_config,
            max_retries=3
        )

        assert result["status"] == "success"
        assert result["data"] == "test"

    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self, error_handler, mock_config):
        """Test timeout error triggers retry with exponential backoff"""
        call_count = 0

        async def timeout_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                await asyncio.sleep(100)  # Simulate timeout
            return {"status": "success"}

        with pytest.raises(ApiTimeoutException) as exc_info:
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                timeout_call,
                mock_config,
                max_retries=2
            )

        assert exc_info.value.provider == ApiProvider.NVD
        assert exc_info.value.timeout_seconds == 30
        assert call_count >= 2  # Should have retried

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self, error_handler, mock_config):
        """Test that retry delays follow exponential backoff pattern"""
        delays = []
        call_count = 0

        async def failing_call():
            nonlocal call_count
            call_count += 1
            raise httpx.RequestError("Network error", request=MagicMock())

        # Mock sleep to capture delays
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)  # Small delay for test speed

        with patch('asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ApiException):
                await error_handler.handle_api_call(
                    ApiProvider.NVD,
                    failing_call,
                    mock_config,
                    max_retries=3
                )

        # Verify exponential backoff pattern
        assert len(delays) == 3  # Should have 3 delays for 3 retries
        assert delays[0] < delays[1] < delays[2]  # Increasing delays
        assert delays[0] >= 1  # First delay at least 2^0 = 1 second (with jitter)

    @pytest.mark.asyncio
    async def test_no_retry_on_authentication_error(self, error_handler, mock_config):
        """Test that authentication errors do not trigger retries"""
        call_count = 0

        async def auth_error_call():
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 401
            raise httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)

        with pytest.raises(ApiAuthenticationException):
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                auth_error_call,
                mock_config,
                max_retries=3
            )

        assert call_count == 1  # Should not retry on auth errors

    @pytest.mark.asyncio
    async def test_error_tracking(self, error_handler, mock_config):
        """Test that errors are tracked for monitoring"""
        async def failing_call():
            raise httpx.RequestError("Network error", request=MagicMock())

        with pytest.raises(ApiException):
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                failing_call,
                mock_config,
                max_retries=0
            )

        stats = error_handler.get_error_stats(ApiProvider.NVD)
        assert stats["error_count"] > 0
        assert stats["provider"] == "nvd"

    @pytest.mark.asyncio
    async def test_error_tracking_reset_on_success(self, error_handler, mock_config):
        """Test that error tracking resets after successful call"""
        # First cause an error
        async def failing_call():
            raise httpx.RequestError("Network error", request=MagicMock())

        with pytest.raises(ApiException):
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                failing_call,
                mock_config,
                max_retries=0
            )

        # Then succeed
        async def successful_call():
            return {"status": "success"}

        await error_handler.handle_api_call(
            ApiProvider.NVD,
            successful_call,
            mock_config,
            max_retries=0
        )

        stats = error_handler.get_error_stats(ApiProvider.NVD)
        assert stats["error_count"] == 0  # Should be reset


class TestHttpErrorHandling:
    """Test cases for HTTP status code error handling"""

    @pytest.fixture
    def error_handler(self):
        return ApiErrorHandler()

    def test_handle_401_authentication_error(self, error_handler):
        """Test 401 status code mapped to ApiAuthenticationException"""
        response = MagicMock()
        response.status_code = 401
        response.headers = {}
        error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert isinstance(result, ApiAuthenticationException)
        assert result.error_type == ApiErrorType.AUTHENTICATION
        assert result.status_code == 401

    def test_handle_403_forbidden_error(self, error_handler):
        """Test 403 status code mapped to ApiAuthenticationException"""
        response = MagicMock()
        response.status_code = 403
        response.headers = {}
        error = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert isinstance(result, ApiAuthenticationException)
        assert "Forbidden" in str(result)

    def test_handle_404_not_found_error(self, error_handler):
        """Test 404 status code mapped to NOT_FOUND error type"""
        response = MagicMock()
        response.status_code = 404
        response.headers = {}
        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert result.error_type == ApiErrorType.NOT_FOUND
        assert result.status_code == 404

    def test_handle_429_rate_limit_error(self, error_handler):
        """Test 429 status code mapped to ApiRateLimitException"""
        response = MagicMock()
        response.status_code = 429
        response.headers = {"retry-after": "60"}
        error = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert isinstance(result, ApiRateLimitException)
        assert result.retry_after == 60
        assert result.error_type == ApiErrorType.RATE_LIMITED

    def test_handle_429_without_retry_after_header(self, error_handler):
        """Test 429 without retry-after header"""
        response = MagicMock()
        response.status_code = 429
        response.headers = {}
        error = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert isinstance(result, ApiRateLimitException)
        assert result.retry_after is None

    def test_handle_500_server_error(self, error_handler):
        """Test 500 status code mapped to SERVER_ERROR type"""
        response = MagicMock()
        response.status_code = 500
        response.headers = {}
        error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=response)

        result = error_handler._handle_http_error(ApiProvider.NVD, error)

        assert result.error_type == ApiErrorType.SERVER_ERROR
        assert result.status_code == 500


class TestBackoffDelay:
    """Test cases for exponential backoff delay calculation"""

    @pytest.fixture
    def error_handler(self):
        return ApiErrorHandler()

    def test_exponential_backoff_progression(self, error_handler):
        """Test that backoff delay increases exponentially"""
        delays = []
        for attempt in range(5):
            exception = ApiException(
                "Test error",
                ApiErrorType.SERVER_ERROR,
                ApiProvider.NVD
            )
            delay = error_handler._calculate_backoff_delay(attempt, ApiProvider.NVD, exception)
            delays.append(delay)

        # Verify exponential progression with jitter
        for i in range(len(delays) - 1):
            # Each delay should be roughly double the previous (accounting for jitter)
            assert delays[i] < delays[i + 1] * 2

    def test_backoff_delay_cap(self, error_handler):
        """Test that backoff delay is capped at maximum"""
        exception = ApiException(
            "Test error",
            ApiErrorType.SERVER_ERROR,
            ApiProvider.NVD
        )
        
        delay = error_handler._calculate_backoff_delay(10, ApiProvider.NVD, exception)
        
        # Should be capped at 60 seconds + jitter
        assert delay <= 78  # 60 + (0.3 * 60) = 78 max with jitter

    def test_backoff_respects_retry_after_header(self, error_handler):
        """Test that retry-after header overrides exponential backoff"""
        exception = ApiRateLimitException(ApiProvider.NVD, retry_after=120)
        
        delay = error_handler._calculate_backoff_delay(0, ApiProvider.NVD, exception)
        
        # Should use retry-after value
        assert delay >= 120

    def test_backoff_jitter_randomness(self, error_handler):
        """Test that jitter adds randomness to prevent thundering herd"""
        exception = ApiException(
            "Test error",
            ApiErrorType.SERVER_ERROR,
            ApiProvider.NVD
        )
        
        delays = [
            error_handler._calculate_backoff_delay(2, ApiProvider.NVD, exception)
            for _ in range(10)
        ]
        
        # With jitter, delays should not all be identical
        assert len(set(delays)) > 1


class TestCircuitBreaker:
    """Test cases for circuit breaker pattern implementation"""

    @pytest.fixture
    def error_handler(self):
        return ApiErrorHandler()

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.timeout = 5
        config.retry_attempts = 0
        config.circuit_breaker_threshold = 3  # Open after 3 failures
        return config

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, error_handler, mock_config):
        """Test that circuit breaker opens after reaching failure threshold"""
        async def failing_call():
            raise httpx.RequestError("Network error", request=MagicMock())

        # Cause failures up to threshold
        for i in range(mock_config.circuit_breaker_threshold):
            with pytest.raises(ApiException):
                await error_handler.handle_api_call(
                    ApiProvider.NVD,
                    failing_call,
                    mock_config,
                    max_retries=0
                )

        # Next call should trigger circuit breaker
        with pytest.raises(ApiCircuitBreakerOpen):
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                failing_call,
                mock_config,
                max_retries=0
            )

    @pytest.mark.asyncio
    async def test_health_check_execution(self, error_handler):
        """Test health check execution for API providers"""
        health_check_called = False

        async def health_check():
            nonlocal health_check_called
            health_check_called = True
            return True

        result = await error_handler.health_check(ApiProvider.NVD, health_check)

        assert result is True
        assert health_check_called

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, error_handler):
        """Test that health check times out appropriately"""
        async def slow_health_check():
            await asyncio.sleep(10)
            return True

        result = await error_handler.health_check(ApiProvider.NVD, slow_health_check)

        assert result is False  # Should timeout and return False


class TestExceptionTypes:
    """Test cases for custom exception types"""

    def test_api_exception_attributes(self):
        """Test ApiException stores all required attributes"""
        exception = ApiException(
            "Test error",
            ApiErrorType.TIMEOUT,
            ApiProvider.NVD,
            status_code=504,
            response_data={"error": "timeout"}
        )

        assert str(exception) == "Test error"
        assert exception.error_type == ApiErrorType.TIMEOUT
        assert exception.provider == ApiProvider.NVD
        assert exception.status_code == 504
        assert exception.response_data == {"error": "timeout"}
        assert isinstance(exception.timestamp, datetime)

    def test_api_timeout_exception(self):
        """Test ApiTimeoutException formatting"""
        exception = ApiTimeoutException(ApiProvider.NVD, 30)

        assert "timed out" in str(exception).lower()
        assert "30 seconds" in str(exception)
        assert exception.timeout_seconds == 30
        assert exception.error_type == ApiErrorType.TIMEOUT

    def test_api_rate_limit_exception_with_retry_after(self):
        """Test ApiRateLimitException with retry_after"""
        exception = ApiRateLimitException(ApiProvider.NVD, retry_after=60)

        assert "rate limit" in str(exception).lower()
        assert "60 seconds" in str(exception)
        assert exception.retry_after == 60

    def test_api_rate_limit_exception_without_retry_after(self):
        """Test ApiRateLimitException without retry_after"""
        exception = ApiRateLimitException(ApiProvider.NVD)

        assert "rate limit" in str(exception).lower()
        assert exception.retry_after is None

    def test_api_authentication_exception(self):
        """Test ApiAuthenticationException"""
        exception = ApiAuthenticationException(ApiProvider.NVD, "Invalid API key")

        assert "authentication" in str(exception).lower()
        assert "Invalid API key" in str(exception)
        assert exception.status_code == 401

    def test_api_circuit_breaker_open_exception(self):
        """Test ApiCircuitBreakerOpen exception"""
        exception = ApiCircuitBreakerOpen(ApiProvider.NVD)

        assert "circuit breaker" in str(exception).lower()
        assert exception.error_type == ApiErrorType.SERVER_ERROR


class TestErrorStatistics:
    """Test cases for error statistics and monitoring"""

    @pytest.fixture
    def error_handler(self):
        return ApiErrorHandler()

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.timeout = 5
        config.retry_attempts = 0
        config.circuit_breaker_threshold = 5
        return config

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, error_handler, mock_config):
        """Test that error statistics are properly tracked"""
        async def failing_call():
            raise httpx.RequestError("Network error", request=MagicMock())

        # Generate some errors
        for _ in range(3):
            with pytest.raises(ApiException):
                await error_handler.handle_api_call(
                    ApiProvider.NVD,
                    failing_call,
                    mock_config,
                    max_retries=0
                )

        stats = error_handler.get_error_stats(ApiProvider.NVD)
        
        assert stats["provider"] == "nvd"
        assert stats["error_count"] == 3
        assert stats["last_error"] is not None

    @pytest.mark.asyncio
    async def test_error_statistics_per_provider(self, error_handler, mock_config):
        """Test that error statistics are tracked separately per provider"""
        async def failing_call():
            raise httpx.RequestError("Network error", request=MagicMock())

        # Generate errors for NVD
        with pytest.raises(ApiException):
            await error_handler.handle_api_call(
                ApiProvider.NVD,
                failing_call,
                mock_config,
                max_retries=0
            )

        # Generate errors for CISA
        for _ in range(2):
            with pytest.raises(ApiException):
                await error_handler.handle_api_call(
                    ApiProvider.CISA_KEV,
                    failing_call,
                    mock_config,
                    max_retries=0
                )

        nvd_stats = error_handler.get_error_stats(ApiProvider.NVD)
        cisa_stats = error_handler.get_error_stats(ApiProvider.CISA_KEV)

        assert nvd_stats["error_count"] == 1
        assert cisa_stats["error_count"] == 2
