from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from datetime import datetime, timedelta
from models.api_configuration import (
    ApiConfiguration,
    ApiUsageMetrics,
    ApiHealthStatus,
    ApiProvider,
    HealthStatus
)
import uuid


class ApiConfigurationRepository:
    """Repository for API configuration data access"""

    def __init__(self, db_session: Session):
        self.db = db_session

    # Configuration CRUD operations

    def get_all_configurations(self) -> List[ApiConfiguration]:
        """Get all API configurations"""
        return self.db.query(ApiConfiguration).all()

    def get_configuration_by_provider(self, provider: ApiProvider) -> Optional[ApiConfiguration]:
        """Get configuration for a specific provider"""
        return self.db.query(ApiConfiguration).filter(
            ApiConfiguration.provider == provider.value
        ).first()

    def create_configuration(self, provider: ApiProvider, **kwargs) -> ApiConfiguration:
        """Create a new API configuration"""
        config = ApiConfiguration(
            id=str(uuid.uuid4()),
            provider=provider.value,
            **kwargs
        )
        self.db.add(config)
        self.db.commit()
        return config

    def update_configuration(self, config: ApiConfiguration, **updates) -> ApiConfiguration:
        """Update an existing API configuration"""
        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        config.updated_at = datetime.now()
        self.db.commit()
        return config

    def delete_configuration(self, provider: ApiProvider) -> bool:
        """Delete configuration for a provider"""
        config = self.get_configuration_by_provider(provider)
        if config:
            self.db.delete(config)
            self.db.commit()
            return True
        return False

    # Usage metrics operations

    def get_usage_metrics(self, provider: Optional[ApiProvider] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[ApiUsageMetrics]:
        """Get usage metrics with optional filtering"""
        query = self.db.query(ApiUsageMetrics)

        if provider:
            query = query.filter(ApiUsageMetrics.provider == provider.value)

        if start_date:
            query = query.filter(ApiUsageMetrics.recorded_at >= start_date)

        if end_date:
            query = query.filter(ApiUsageMetrics.recorded_at <= end_date)

        return query.order_by(desc(ApiUsageMetrics.recorded_at)).all()

    def create_usage_metrics(self, provider: ApiProvider, **kwargs) -> ApiUsageMetrics:
        """Create new usage metrics record"""
        metrics = ApiUsageMetrics(
            id=str(uuid.uuid4()),
            provider=provider.value,
            **kwargs
        )
        self.db.add(metrics)
        self.db.commit()
        return metrics

    def get_or_create_daily_metrics(self, provider: ApiProvider,
                                   date: Optional[datetime] = None) -> ApiUsageMetrics:
        """Get or create daily metrics record for a provider"""
        if date is None:
            date = datetime.now()

        # Normalize to start of day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        metrics = self.db.query(ApiUsageMetrics).filter(
            and_(
                ApiUsageMetrics.provider == provider.value,
                ApiUsageMetrics.recorded_at >= start_of_day,
                ApiUsageMetrics.recorded_at < end_of_day
            )
        ).first()

        if not metrics:
            metrics = self.create_usage_metrics(
                provider,
                calls_made=0,
                calls_successful=0,
                calls_failed=0,
                average_response_time=0.0,
                recorded_at=start_of_day
            )

        return metrics

    def update_usage_metrics(self, metrics: ApiUsageMetrics,
                           calls_made: int = 0,
                           calls_successful: int = 0,
                           calls_failed: int = 0,
                           response_time: float = 0.0) -> ApiUsageMetrics:
        """Update usage metrics with new call data"""
        # Update counters
        metrics.calls_made += calls_made
        metrics.calls_successful += calls_successful
        metrics.calls_failed += calls_failed

        # Update average response time
        if response_time > 0 and metrics.calls_made > 0:
            total_calls = metrics.calls_made
            current_avg = metrics.average_response_time
            metrics.average_response_time = (
                (current_avg * (total_calls - 1) + response_time) / total_calls
            )

        self.db.commit()
        return metrics

    def get_aggregated_metrics(self, provider: Optional[ApiProvider] = None,
                             timeframe: str = "day") -> List[Dict[str, Any]]:
        """Get aggregated metrics for reporting"""
        # Calculate date range based on timeframe
        now = datetime.now()
        if timeframe == "hour":
            cutoff = now - timedelta(hours=24)
            date_format = "%Y-%m-%d %H:00"
        elif timeframe == "day":
            cutoff = now - timedelta(days=30)
            date_format = "%Y-%m-%d"
        elif timeframe == "week":
            cutoff = now - timedelta(weeks=12)
            date_format = "%Y-W%W"
        else:  # month
            cutoff = now - timedelta(days=365)
            date_format = "%Y-%m"

        query = self.db.query(
            ApiUsageMetrics.provider,
            func.sum(ApiUsageMetrics.calls_made).label('total_calls'),
            func.sum(ApiUsageMetrics.calls_successful).label('total_successful'),
            func.sum(ApiUsageMetrics.calls_failed).label('total_failed'),
            func.avg(ApiUsageMetrics.average_response_time).label('avg_response_time'),
            func.strftime(date_format, ApiUsageMetrics.recorded_at).label('period')
        ).filter(ApiUsageMetrics.recorded_at >= cutoff)

        if provider:
            query = query.filter(ApiUsageMetrics.provider == provider.value)

        results = query.group_by(
            ApiUsageMetrics.provider,
            func.strftime(date_format, ApiUsageMetrics.recorded_at)
        ).all()

        return [
            {
                "provider": r.provider,
                "period": r.period,
                "total_calls": r.total_calls or 0,
                "total_successful": r.total_successful or 0,
                "total_failed": r.total_failed or 0,
                "success_rate": (r.total_successful / r.total_calls * 100) if r.total_calls > 0 else 0,
                "average_response_time": float(r.avg_response_time or 0)
            }
            for r in results
        ]

    # Health status operations

    def get_health_status(self, provider: Optional[ApiProvider] = None) -> List[ApiHealthStatus]:
        """Get health status for providers"""
        query = self.db.query(ApiHealthStatus)
        if provider:
            query = query.filter(ApiHealthStatus.provider == provider.value)
        return query.all()

    def get_health_status_by_provider(self, provider: ApiProvider) -> Optional[ApiHealthStatus]:
        """Get health status for a specific provider"""
        return self.db.query(ApiHealthStatus).filter(
            ApiHealthStatus.provider == provider.value
        ).first()

    def create_health_status(self, provider: ApiProvider, **kwargs) -> ApiHealthStatus:
        """Create new health status record"""
        status = ApiHealthStatus(
            id=str(uuid.uuid4()),
            provider=provider.value,
            status=HealthStatus.HEALTHY.value,
            consecutive_failures=0,
            **kwargs
        )
        self.db.add(status)
        self.db.commit()
        return status

    def update_health_status(self, status: ApiHealthStatus,
                           success: bool,
                           response_time: Optional[float] = None,
                           error_message: Optional[str] = None) -> ApiHealthStatus:
        """Update health status based on API call result"""
        status.last_check = datetime.now()
        status.response_time = response_time

        if success:
            status.consecutive_failures = 0
            status.error_message = None
            status.status = HealthStatus.HEALTHY.value
        else:
            status.consecutive_failures += 1
            status.error_message = error_message

            # Determine health status based on consecutive failures
            if status.consecutive_failures >= 5:
                status.status = HealthStatus.DOWN.value
            elif status.consecutive_failures >= 2:
                status.status = HealthStatus.DEGRADED.value

        self.db.commit()
        return status

    def reset_health_status(self, provider: ApiProvider) -> bool:
        """Reset health status for a provider"""
        status = self.get_health_status_by_provider(provider)
        if status:
            status.status = HealthStatus.HEALTHY.value
            status.consecutive_failures = 0
            status.error_message = None
            status.last_check = datetime.now()
            self.db.commit()
            return True
        return False

    # Utility methods

    def get_provider_summary(self, provider: ApiProvider) -> Dict[str, Any]:
        """Get comprehensive summary for a provider"""
        config = self.get_configuration_by_provider(provider)
        health = self.get_health_status_by_provider(provider)

        # Get recent metrics (last 24 hours)
        recent_metrics = self.get_usage_metrics(
            provider,
            start_date=datetime.now() - timedelta(hours=24)
        )

        total_calls = sum(m.calls_made for m in recent_metrics)
        total_successful = sum(m.calls_successful for m in recent_metrics)
        total_failed = sum(m.calls_failed for m in recent_metrics)

        return {
            "provider": provider.value,
            "configuration": {
                "enabled": config.enabled if config else False,
                "rate_limit_calls": config.rate_limit_calls if config else 0,
                "rate_limit_period": config.rate_limit_period if config else 0,
                "timeout": config.timeout if config else 0
            } if config else None,
            "health": {
                "status": health.status if health else "unknown",
                "consecutive_failures": health.consecutive_failures if health else 0,
                "last_check": health.last_check if health else None,
                "response_time": health.response_time if health else None
            } if health else None,
            "recent_usage": {
                "total_calls": total_calls,
                "successful_calls": total_successful,
                "failed_calls": total_failed,
                "success_rate": (total_successful / total_calls * 100) if total_calls > 0 else 0
            }
        }

    def cleanup_old_metrics(self, days_to_keep: int = 90) -> int:
        """Clean up old metrics records"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        deleted_count = self.db.query(ApiUsageMetrics).filter(
            ApiUsageMetrics.recorded_at < cutoff_date
        ).delete()

        self.db.commit()
        return deleted_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for all providers"""
        # Total configurations
        total_configs = self.db.query(ApiConfiguration).count()
        enabled_configs = self.db.query(ApiConfiguration).filter(
            ApiConfiguration.enabled == True
        ).count()

        # Recent metrics (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_metrics = self.get_usage_metrics(start_date=week_ago)

        total_calls = sum(m.calls_made for m in recent_metrics)
        total_successful = sum(m.calls_successful for m in recent_metrics)
        total_failed = sum(m.calls_failed for m in recent_metrics)

        # Health summary
        all_health = self.get_health_status()
        healthy_count = len([h for h in all_health if h.status == HealthStatus.HEALTHY.value])
        degraded_count = len([h for h in all_health if h.status == HealthStatus.DEGRADED.value])
        down_count = len([h for h in all_health if h.status == HealthStatus.DOWN.value])

        return {
            "configurations": {
                "total": total_configs,
                "enabled": enabled_configs,
                "disabled": total_configs - enabled_configs
            },
            "health_summary": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "down": down_count
            },
            "recent_usage": {
                "total_calls": total_calls,
                "successful_calls": total_successful,
                "failed_calls": total_failed,
                "success_rate": (total_successful / total_calls * 100) if total_calls > 0 else 0
            }
        }