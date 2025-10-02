import logging
from typing import Dict, Optional, List, Any
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.api_configuration import (
    ApiConfiguration,
    ApiUsageMetrics,
    ApiHealthStatus,
    ApiProvider,
    HealthStatus,
    DEFAULT_PROVIDER_CONFIGS,
    ApiConfigurationResponse,
    ApiConfigurationUpdate
)
from services.config.api_key_manager import ApiKeyManager
from services.config.rate_limiter import RateLimiter
from services.config.api_error_handler import ApiErrorHandler, ApiException
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ApiConfigurationService:
    """Main service for managing API configurations, keys, and monitoring"""

    def __init__(self, db_session: Session, redis_client: redis.Redis):
        self.db = db_session
        self.api_key_manager = ApiKeyManager()
        self.rate_limiter = RateLimiter(redis_client)
        self.error_handler = ApiErrorHandler()
        self.redis = redis_client

    async def initialize_default_configurations(self):
        """Initialize default configurations for all providers"""
        for provider, config in DEFAULT_PROVIDER_CONFIGS.items():
            existing = self.db.query(ApiConfiguration).filter(
                ApiConfiguration.provider == provider.value
            ).first()

            if not existing:
                api_config = ApiConfiguration(
                    id=str(uuid.uuid4()),
                    provider=provider.value,
                    enabled=True,
                    rate_limit_calls=config.default_rate_limit_calls,
                    rate_limit_period=config.default_rate_limit_period,
                    timeout=config.default_timeout,
                    retry_attempts=3,
                    circuit_breaker_threshold=5,
                    health_check_interval=300
                )
                self.db.add(api_config)

                # Initialize health status
                health_status = ApiHealthStatus(
                    id=str(uuid.uuid4()),
                    provider=provider.value,
                    status=HealthStatus.HEALTHY.value,
                    consecutive_failures=0
                )
                self.db.add(health_status)

        self.db.commit()
        logger.info("Initialized default API configurations")

    def get_all_configurations(self) -> List[ApiConfigurationResponse]:
        """Get all API configurations"""
        configs = self.db.query(ApiConfiguration).all()
        return [ApiConfigurationResponse.from_orm(config) for config in configs]

    def get_configuration(self, provider: ApiProvider) -> Optional[ApiConfigurationResponse]:
        """Get configuration for a specific provider"""
        config = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()

        if config:
            return ApiConfigurationResponse.from_orm(config)
        return None

    async def update_configuration(self, provider: ApiProvider,
                                 updates: ApiConfigurationUpdate) -> ApiConfigurationResponse:
        """Update configuration for a provider"""
        config = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()

        if not config:
            raise ValueError(f"Configuration not found for provider {provider.value}")

        # Update API key if provided
        if updates.api_key is not None:
            if updates.api_key.strip():
                # Validate API key format
                if not self.api_key_manager.validate_api_key_format(provider, updates.api_key):
                    raise ValueError(f"Invalid API key format for {provider.value}")

                # Store the API key
                if not self.api_key_manager.store_api_key(provider, updates.api_key):
                    raise RuntimeError(f"Failed to store API key for {provider.value}")
            else:
                # Empty string means delete the key
                self.api_key_manager.delete_api_key(provider)

        # Update configuration fields
        if updates.enabled is not None:
            config.enabled = updates.enabled
        if updates.rate_limit_calls is not None:
            config.rate_limit_calls = updates.rate_limit_calls
        if updates.rate_limit_period is not None:
            config.rate_limit_period = updates.rate_limit_period
        if updates.timeout is not None:
            config.timeout = updates.timeout
        if updates.retry_attempts is not None:
            config.retry_attempts = updates.retry_attempts
        if updates.circuit_breaker_threshold is not None:
            config.circuit_breaker_threshold = updates.circuit_breaker_threshold
        if updates.health_check_interval is not None:
            config.health_check_interval = updates.health_check_interval

        config.updated_at = datetime.now()
        self.db.commit()

        # Reset rate limits when configuration changes
        await self.rate_limiter.reset_rate_limit(provider)

        return ApiConfigurationResponse.from_orm(config)

    def is_provider_enabled(self, provider: ApiProvider) -> bool:
        """Check if a provider is enabled"""
        config = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()
        return config.enabled if config else False

    def get_api_key(self, provider: ApiProvider) -> Optional[str]:
        """Get API key for a provider"""
        return self.api_key_manager.get_api_key(provider)

    async def check_rate_limit(self, provider: ApiProvider) -> bool:
        """Check if API call is allowed by rate limit"""
        config = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()

        if not config or not config.enabled:
            return False

        return await self.rate_limiter.acquire(provider, config)

    async def execute_api_call(self, provider: ApiProvider, api_call_func, *args, **kwargs):
        """Execute an API call with full error handling and monitoring"""
        config = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()

        if not config:
            raise ValueError(f"No configuration found for {provider.value}")

        if not config.enabled:
            raise ValueError(f"Provider {provider.value} is disabled")

        # Check rate limit
        if not await self.rate_limiter.acquire(provider, config):
            raise ApiException(
                f"Rate limit exceeded for {provider.value}",
                "rate_limited",
                provider
            )

        # Execute with error handling
        start_time = datetime.now()
        success = False
        error_message = None

        try:
            result = await self.error_handler.handle_api_call(
                provider, api_call_func, config, config.retry_attempts
            )
            success = True
            return result

        except ApiException as e:
            error_message = str(e)
            raise

        finally:
            # Record usage metrics
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000

            await self._record_usage_metrics(
                provider, success, response_time, error_message
            )

    async def _record_usage_metrics(self, provider: ApiProvider, success: bool,
                                   response_time: float, error_message: Optional[str] = None):
        """Record API usage metrics"""
        # Get or create today's metrics record
        today = datetime.now().date()
        metrics = self.db.query(ApiUsageMetrics).filter(
            ApiUsageMetrics.provider == provider.value,
            ApiUsageMetrics.recorded_at >= today
        ).first()

        if not metrics:
            metrics = ApiUsageMetrics(
                id=str(uuid.uuid4()),
                provider=provider.value,
                calls_made=0,
                calls_successful=0,
                calls_failed=0,
                average_response_time=0.0
            )
            self.db.add(metrics)

        # Update metrics
        metrics.calls_made += 1
        if success:
            metrics.calls_successful += 1
        else:
            metrics.calls_failed += 1

        # Update average response time
        total_calls = metrics.calls_made
        current_avg = metrics.average_response_time
        metrics.average_response_time = (
            (current_avg * (total_calls - 1) + response_time) / total_calls
        )

        # Update health status
        await self._update_health_status(provider, success, response_time, error_message)

        self.db.commit()

    async def _update_health_status(self, provider: ApiProvider, success: bool,
                                   response_time: float, error_message: Optional[str] = None):
        """Update health status based on API call results"""
        health = self.db.query(ApiHealthStatus).filter(
            ApiHealthStatus.provider == provider.value
        ).first()

        if not health:
            health = ApiHealthStatus(
                id=str(uuid.uuid4()),
                provider=provider.value,
                status=HealthStatus.HEALTHY.value,
                consecutive_failures=0
            )
            self.db.add(health)

        health.last_check = datetime.now()
        health.response_time = response_time

        if success:
            health.consecutive_failures = 0
            health.error_message = None
            health.status = HealthStatus.HEALTHY.value
        else:
            health.consecutive_failures += 1
            health.error_message = error_message

            # Determine health status based on consecutive failures
            if health.consecutive_failures >= 5:
                health.status = HealthStatus.DOWN.value
            elif health.consecutive_failures >= 2:
                health.status = HealthStatus.DEGRADED.value

    def get_health_status(self, provider: Optional[ApiProvider] = None) -> List[Dict]:
        """Get health status for providers"""
        query = self.db.query(ApiHealthStatus)
        if provider:
            query = query.filter(ApiHealthStatus.provider == provider.value)

        health_statuses = query.all()
        return [
            {
                "provider": h.provider,
                "status": h.status,
                "last_check": h.last_check,
                "consecutive_failures": h.consecutive_failures,
                "error_message": h.error_message,
                "response_time": h.response_time
            }
            for h in health_statuses
        ]

    def get_usage_metrics(self, provider: Optional[ApiProvider] = None,
                         timeframe: str = "day") -> List[Dict]:
        """Get usage metrics for providers"""
        query = self.db.query(ApiUsageMetrics)
        if provider:
            query = query.filter(ApiUsageMetrics.provider == provider.value)

        # Filter by timeframe
        now = datetime.now()
        if timeframe == "hour":
            cutoff = now.replace(minute=0, second=0, microsecond=0)
        elif timeframe == "day":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == "week":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff = cutoff - timedelta(days=cutoff.weekday())
        else:  # month
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        metrics = query.filter(ApiUsageMetrics.recorded_at >= cutoff).all()

        return [
            {
                "provider": m.provider,
                "calls_made": m.calls_made,
                "calls_successful": m.calls_successful,
                "calls_failed": m.calls_failed,
                "success_rate": (m.calls_successful / m.calls_made * 100) if m.calls_made > 0 else 0,
                "average_response_time": m.average_response_time,
                "recorded_at": m.recorded_at
            }
            for m in metrics
        ]

    async def reset_provider_state(self, provider: ApiProvider):
        """Reset all state for a provider (for testing/recovery)"""
        # Reset rate limits
        await self.rate_limiter.reset_rate_limit(provider)

        # Reset circuit breaker
        self.error_handler.reset_circuit_breaker(provider)

        # Reset health status
        health = self.db.query(ApiHealthStatus).filter(
            ApiHealthStatus.provider == provider.value
        ).first()

        if health:
            health.status = HealthStatus.HEALTHY.value
            health.consecutive_failures = 0
            health.error_message = None
            self.db.commit()

        logger.info(f"Reset state for provider {provider.value}")