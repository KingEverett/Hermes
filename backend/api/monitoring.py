from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from models.api_configuration import ApiProvider
from services.config.api_configuration import ApiConfigurationService
from services.config.fallback_service import FallbackService
from database.connection import get_session as get_db_session
from middleware.auth import verify_api_key
import redis.asyncio as redis
import os
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SystemStatusResponse(BaseModel):
    """System status response model"""
    database_status: bool
    redis_status: bool
    celery_workers: int
    active_scans: int
    queued_research_tasks: int
    failed_jobs: int

router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["monitoring"],
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


def get_fallback_service(api_config: ApiConfigurationService = Depends(get_api_config_service)):
    """Get fallback service for dependency injection"""
    return FallbackService(api_config)


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_db_session)):
    """
    Get comprehensive system status for CLI integration
    Returns database, Redis, Celery, and job queue status
    """
    try:
        # Check database status
        database_status = False
        try:
            db.execute("SELECT 1")
            database_status = True
        except Exception as e:
            logger.error(f"Database check failed: {e}")

        # Check Redis status
        redis_status = False
        try:
            redis_client = get_redis_client()
            await redis_client.ping()
            redis_status = True
            await redis_client.close()
        except Exception as e:
            logger.error(f"Redis check failed: {e}")

        # Check Celery workers (placeholder - requires Celery app instance)
        celery_workers = 0
        try:
            # This would require importing and inspecting the Celery app
            # For now, we'll return 0 or check via Redis/backend
            pass
        except Exception as e:
            logger.error(f"Celery check failed: {e}")

        # Query active scans
        active_scans = 0
        try:
            from models.scan import Scan
            active_scans = db.query(Scan).filter(Scan.status == 'processing').count()
        except Exception as e:
            logger.error(f"Active scans query failed: {e}")

        # Query queued research tasks (placeholder - requires job queue model)
        queued_research_tasks = 0
        try:
            # This would query from a jobs table or Celery queue
            pass
        except Exception as e:
            logger.error(f"Queued tasks query failed: {e}")

        # Query failed jobs
        failed_jobs = 0
        try:
            from models.scan import Scan
            failed_jobs = db.query(Scan).filter(Scan.status == 'failed').count()
        except Exception as e:
            logger.error(f"Failed jobs query failed: {e}")

        return SystemStatusResponse(
            database_status=database_status,
            redis_status=redis_status,
            celery_workers=celery_workers,
            active_scans=active_scans,
            queued_research_tasks=queued_research_tasks,
            failed_jobs=failed_jobs
        )

    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")


@router.get("/apis/health")
async def get_api_health_status(
    provider: Optional[str] = Query(None, description="Filter by specific provider"),
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get health status of all or specific API providers"""
    try:
        api_provider = None
        if provider:
            try:
                api_provider = ApiProvider(provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        health_statuses = service.get_health_status(api_provider)

        return {
            "timestamp": datetime.now(),
            "provider_filter": provider,
            "health_statuses": health_statuses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health status")


@router.get("/apis/usage")
async def get_api_usage_metrics(
    provider: Optional[str] = Query(None, description="Filter by specific provider"),
    timeframe: str = Query("day", pattern="^(hour|day|week|month)$", description="Timeframe for metrics"),
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get API usage statistics for specified timeframe"""
    try:
        api_provider = None
        if provider:
            try:
                api_provider = ApiProvider(provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        usage_metrics = service.get_usage_metrics(api_provider, timeframe)

        return {
            "timestamp": datetime.now(),
            "provider_filter": provider,
            "timeframe": timeframe,
            "metrics": usage_metrics
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage metrics")


@router.get("/apis/summary")
async def get_monitoring_summary(
    service: ApiConfigurationService = Depends(get_api_config_service),
    fallback_service: FallbackService = Depends(get_fallback_service)
):
    """Get comprehensive monitoring summary for all APIs"""
    try:
        # Get all configurations
        configurations = service.get_all_configurations()

        # Get health status for all providers
        health_statuses = service.get_health_status()

        # Get usage metrics for the last 24 hours
        usage_metrics = service.get_usage_metrics(timeframe="day")

        # Get fallback status
        fallback_summary = await fallback_service.get_provider_status_summary()

        # Calculate summary statistics
        total_providers = len(configurations)
        enabled_providers = len([c for c in configurations if c.enabled])
        healthy_providers = len([h for h in health_statuses if h["status"] == "healthy"])
        total_calls_today = sum(m["calls_made"] for m in usage_metrics)
        total_successful_today = sum(m["calls_successful"] for m in usage_metrics)
        overall_success_rate = (total_successful_today / total_calls_today * 100) if total_calls_today > 0 else 0

        return {
            "timestamp": datetime.now(),
            "summary": {
                "total_providers": total_providers,
                "enabled_providers": enabled_providers,
                "healthy_providers": healthy_providers,
                "overall_health": fallback_summary["overall_health"],
                "total_calls_today": total_calls_today,
                "successful_calls_today": total_successful_today,
                "overall_success_rate": round(overall_success_rate, 2)
            },
            "configurations": configurations,
            "health_statuses": health_statuses,
            "usage_metrics": usage_metrics,
            "fallback_status": fallback_summary
        }

    except Exception as e:
        logger.error(f"Failed to get monitoring summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve monitoring summary")


@router.get("/apis/{provider}/details")
async def get_provider_detailed_monitoring(
    provider: str,
    service: ApiConfigurationService = Depends(get_api_config_service),
    fallback_service: FallbackService = Depends(get_fallback_service)
):
    """Get detailed monitoring information for a specific provider"""
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

        # Get usage metrics for different timeframes
        usage_hour = service.get_usage_metrics(api_provider, "hour")
        usage_day = service.get_usage_metrics(api_provider, "day")
        usage_week = service.get_usage_metrics(api_provider, "week")

        # Get rate limit status
        rate_limit_status = await service.rate_limiter.get_rate_limit_status(api_provider)

        # Get fallback options
        fallback_options = await fallback_service.get_fallback_options(api_provider, {})

        # Check API key status
        has_api_key = service.get_api_key(api_provider) is not None

        return {
            "timestamp": datetime.now(),
            "provider": provider,
            "configuration": config,
            "health": health,
            "api_key_configured": has_api_key,
            "rate_limit": rate_limit_status,
            "usage_metrics": {
                "last_hour": usage_hour,
                "last_day": usage_day,
                "last_week": usage_week
            },
            "fallback_options": fallback_options
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get detailed monitoring for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve detailed monitoring")


@router.get("/apis/rate-limits")
async def get_rate_limit_status(
    provider: Optional[str] = Query(None, description="Filter by specific provider"),
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get current rate limit status for all or specific providers"""
    try:
        providers_to_check = []

        if provider:
            try:
                api_provider = ApiProvider(provider.lower())
                providers_to_check = [api_provider]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        else:
            providers_to_check = list(ApiProvider)

        rate_limit_statuses = {}
        for api_provider in providers_to_check:
            status = await service.rate_limiter.get_rate_limit_status(api_provider)
            rate_limit_statuses[api_provider.value] = status

        return {
            "timestamp": datetime.now(),
            "provider_filter": provider,
            "rate_limits": rate_limit_statuses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rate limit status")


@router.get("/fallback/{provider}")
async def get_fallback_options(
    provider: str,
    cve_id: Optional[str] = Query(None, description="CVE ID for context"),
    service: ApiConfigurationService = Depends(get_api_config_service),
    fallback_service: FallbackService = Depends(get_fallback_service)
):
    """Get available fallback options for a provider"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        # Build query context
        query_context = {}
        if cve_id:
            query_context["cve_id"] = cve_id

        # Get fallback options
        options = await fallback_service.get_fallback_options(api_provider, query_context)

        return {
            "timestamp": datetime.now(),
            "provider": provider,
            "query_context": query_context,
            "fallback_options": options,
            "options_count": len(options)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fallback options for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fallback options")


@router.post("/fallback/{provider}/execute")
async def execute_fallback(
    provider: str,
    fallback_request: Dict[str, Any],
    service: ApiConfigurationService = Depends(get_api_config_service),
    fallback_service: FallbackService = Depends(get_fallback_service)
):
    """Execute a specific fallback mechanism"""
    try:
        # Validate provider
        try:
            api_provider = ApiProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

        # Validate request
        if "fallback_type" not in fallback_request:
            raise HTTPException(status_code=400, detail="fallback_type is required")

        from services.config.fallback_service import FallbackType
        try:
            fallback_type = FallbackType(fallback_request["fallback_type"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid fallback_type: {fallback_request['fallback_type']}")

        query_context = fallback_request.get("query_context", {})
        fallback_data = fallback_request.get("fallback_data", {})

        # Execute fallback
        result = await fallback_service.execute_fallback(
            api_provider, fallback_type, query_context, fallback_data
        )

        return {
            "timestamp": datetime.now(),
            "provider": provider,
            "fallback_type": result.fallback_type.value,
            "source": result.source,
            "confidence": result.confidence,
            "data": result.data,
            "execution_timestamp": result.timestamp
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute fallback for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute fallback")


@router.get("/reports/daily")
async def get_daily_report(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    service: ApiConfigurationService = Depends(get_api_config_service)
):
    """Get daily monitoring report"""
    try:
        # Parse date
        if date:
            try:
                report_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
        else:
            report_date = datetime.now().date()

        # Get usage metrics for the day
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)

        usage_metrics = service.get_usage_metrics(timeframe="day")

        # Get health status summary
        health_statuses = service.get_health_status()

        # Calculate daily statistics
        total_calls = sum(m["calls_made"] for m in usage_metrics)
        total_successful = sum(m["calls_successful"] for m in usage_metrics)
        total_failed = sum(m["calls_failed"] for m in usage_metrics)
        success_rate = (total_successful / total_calls * 100) if total_calls > 0 else 0

        provider_performance = {}
        for metric in usage_metrics:
            provider_performance[metric["provider"]] = {
                "calls": metric["calls_made"],
                "success_rate": metric["success_rate"],
                "avg_response_time": metric["average_response_time"]
            }

        return {
            "report_date": report_date,
            "generated_at": datetime.now(),
            "summary": {
                "total_api_calls": total_calls,
                "successful_calls": total_successful,
                "failed_calls": total_failed,
                "overall_success_rate": round(success_rate, 2)
            },
            "provider_performance": provider_performance,
            "health_summary": {
                "healthy_providers": len([h for h in health_statuses if h["status"] == "healthy"]),
                "degraded_providers": len([h for h in health_statuses if h["status"] == "degraded"]),
                "down_providers": len([h for h in health_statuses if h["status"] == "down"])
            },
            "usage_details": usage_metrics
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate daily report")