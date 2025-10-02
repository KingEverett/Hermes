from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime
from models.api_configuration import (
    ApiProvider,
    ApiConfigurationResponse,
    ApiConfigurationUpdate
)
from services.config.api_configuration import ApiConfigurationService
from database.connection import get_session as get_db_session
from middleware.auth import verify_api_key
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/config",
    tags=["configuration"],
    dependencies=[Depends(verify_api_key)]
)


def get_redis_client():
    """Get Redis client for dependency injection"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


def get_api_config_service(db: Session = Depends(get_db_session)):
    """Get API configuration service for dependency injection"""
    redis_client = get_redis_client()
    return ApiConfigurationService(db, redis_client)


@router.get("/apis", response_model=List[ApiConfigurationResponse])
async def get_all_api_configurations(
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get all API configurations with current status"""
    try:
        return service.get_all_configurations()
    except Exception as e:
        logger.error(f"Failed to get API configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API configurations")


@router.get("/apis/{provider}", response_model=ApiConfigurationResponse)
async def get_api_configuration(
    provider: str,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get configuration for a specific API provider"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        config = service.get_configuration(api_provider)
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {provider}")

        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.put("/apis/{provider}", response_model=ApiConfigurationResponse)
async def update_api_configuration(
    provider: str,
    updates: ApiConfigurationUpdate,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Update configuration for a specific API provider"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        # Validate update data
        if updates.rate_limit_calls is not None and updates.rate_limit_calls <= 0:
            raise HTTPException(status_code=400, detail="Rate limit calls must be positive")

        if updates.rate_limit_period is not None and updates.rate_limit_period <= 0:
            raise HTTPException(status_code=400, detail="Rate limit period must be positive")

        if updates.timeout is not None and (updates.timeout <= 0 or updates.timeout > 300):
            raise HTTPException(status_code=400, detail="Timeout must be between 1 and 300 seconds")

        if updates.retry_attempts is not None and (updates.retry_attempts < 0 or updates.retry_attempts > 10):
            raise HTTPException(status_code=400, detail="Retry attempts must be between 0 and 10")

        config = await service.update_configuration(api_provider, updates)
        return config

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.post("/apis/{provider}/test")
async def test_api_configuration(
    provider: str,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Test API configuration by performing a health check"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        # Check if provider is enabled
        if not service.is_provider_enabled(api_provider):
            raise HTTPException(status_code=400, detail=f"Provider {provider} is disabled")

        # Simple health check function for testing
        async def health_check():
            # This would normally make a simple API call to test connectivity
            # For now, we'll just check if we have an API key and configuration
            api_key = service.get_api_key(api_provider)
            config = service.get_configuration(api_provider)

            if not config:
                raise Exception("No configuration found")

            # For providers that require API keys, check if we have one
            from models.api_configuration import DEFAULT_PROVIDER_CONFIGS
            provider_config = DEFAULT_PROVIDER_CONFIGS.get(api_provider)
            if provider_config and provider_config.requires_api_key and not api_key:
                raise Exception("API key required but not configured")

            return {"status": "ok"}

        # Execute the health check with error handling
        try:
            result = await service.execute_api_call(api_provider, health_check)
            return {
                "provider": provider,
                "status": "success",
                "message": "API configuration test passed",
                "details": result
            }
        except Exception as e:
            return {
                "provider": provider,
                "status": "error",
                "message": f"API configuration test failed: {str(e)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test configuration for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test configuration")


@router.post("/apis/{provider}/reset")
async def reset_api_provider_state(
    provider: str,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Reset all state for an API provider (rate limits, circuit breakers, health status)"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        await service.reset_provider_state(api_provider)

        return {
            "provider": provider,
            "status": "success",
            "message": "Provider state reset successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset state for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset provider state")


@router.get("/apis/{provider}/status")
async def get_api_provider_status(
    provider: str,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get detailed status information for an API provider"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        # Get configuration
        config = service.get_configuration(api_provider)
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {provider}")

        # Get health status
        health_status = service.get_health_status(api_provider)
        health = health_status[0] if health_status else None

        # Get rate limit status
        rate_limit_status = await service.rate_limiter.get_rate_limit_status(api_provider)

        # Check if API key is configured
        has_api_key = service.get_api_key(api_provider) is not None

        return {
            "provider": provider,
            "configuration": config,
            "health": health,
            "rate_limit": rate_limit_status,
            "has_api_key": has_api_key,
            "enabled": config.enabled
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider status")


# Configuration export/import endpoints

@router.get("/export")
async def export_configurations(
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Export all API configurations (without API keys for security)"""
    try:
        configurations = service.get_all_configurations()

        export_data = {
            "exported_at": str(datetime.now()),
            "configurations": [
                {
                    "provider": config.provider,
                    "enabled": config.enabled,
                    "rate_limit_calls": config.rate_limit_calls,
                    "rate_limit_period": config.rate_limit_period,
                    "timeout": config.timeout,
                    "retry_attempts": config.retry_attempts,
                    "circuit_breaker_threshold": config.circuit_breaker_threshold,
                    "health_check_interval": config.health_check_interval
                }
                for config in configurations
            ]
        }

        return export_data

    except Exception as e:
        logger.error(f"Failed to export configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to export configurations")


@router.post("/import")
async def import_configurations(
    import_data: dict,
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Import API configurations from exported data"""
    try:
        if "configurations" not in import_data:
            raise HTTPException(status_code=400, detail="Invalid import data format")

        imported_count = 0
        errors = []

        for config_data in import_data["configurations"]:
            try:
                # Validate provider
                provider_str = config_data.get("provider")
                if not provider_str:
                    errors.append("Missing provider in configuration")
                    continue

                try:
                    api_provider = ApiProvider(provider_str.lower())
                except ValueError:
                    errors.append(f"Invalid provider: {provider_str}")
                    continue

                # Create update object
                updates = ApiConfigurationUpdate(
                    enabled=config_data.get("enabled"),
                    rate_limit_calls=config_data.get("rate_limit_calls"),
                    rate_limit_period=config_data.get("rate_limit_period"),
                    timeout=config_data.get("timeout"),
                    retry_attempts=config_data.get("retry_attempts"),
                    circuit_breaker_threshold=config_data.get("circuit_breaker_threshold"),
                    health_check_interval=config_data.get("health_check_interval")
                )

                await service.update_configuration(api_provider, updates)
                imported_count += 1

            except Exception as e:
                errors.append(f"Failed to import {config_data.get('provider', 'unknown')}: {str(e)}")

        return {
            "status": "completed",
            "imported_count": imported_count,
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to import configurations")