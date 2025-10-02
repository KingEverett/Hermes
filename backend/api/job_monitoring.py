"""
Job monitoring API endpoints for background task management.

This module provides comprehensive REST API endpoints for monitoring
Celery task execution, managing dead letter queue, and configuring alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import redis
from celery import Celery

from database.connection import get_session as get_db_session
from middleware.auth import verify_api_key
from services.workers.task_monitor import TaskMonitorService, TaskMetrics
from services.workers.retry_manager import RetryManagerService, RetryConfiguration, RETRY_POLICY
from services.workers.dead_letter_queue import DeadLetterQueueService
from services.workers.alerting_service import AlertingService, AlertThreshold, ALERT_SEVERITY, NotificationConfig
from models.job_monitoring import TASK_STATUS, FAILURE_CATEGORY, ALERT_TYPE


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/monitoring/tasks",
    tags=["job_monitoring"],
    dependencies=[Depends(verify_api_key)]
)


# Pydantic models for request/response schemas
class TaskHistoryResponse(BaseModel):
    """Response model for task execution history"""
    id: str
    task_id: str
    task_name: str
    status: str
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    worker_name: Optional[str]
    retry_count: int
    error_message: Optional[str]
    created_at: datetime


class TaskMetricsResponse(BaseModel):
    """Response model for real-time task metrics"""
    task_id: str
    task_name: str
    status: str
    duration_ms: Optional[int]
    memory_usage_mb: Optional[float]
    cpu_usage_percent: Optional[float]
    worker_name: Optional[str]


class DeadLetterTaskResponse(BaseModel):
    """Response model for dead letter queue tasks"""
    id: str
    original_task_id: str
    task_name: str
    failure_reason: str
    failure_category: str
    first_failed_at: datetime
    last_failed_at: datetime
    total_attempts: int
    processed: bool
    retry_scheduled: bool
    retry_attempts: int
    created_at: datetime


class RetryConfigRequest(BaseModel):
    """Request model for retry configuration"""
    max_retries: int = Field(ge=0, le=10)
    base_delay: int = Field(ge=1, le=300)
    max_delay: int = Field(ge=1, le=3600)
    policy: str = Field(pattern="^(exponential|linear|fixed|fibonacci)$")
    jitter: bool = True
    backoff_multiplier: float = Field(ge=1.0, le=10.0)


class AlertThresholdRequest(BaseModel):
    """Request model for alert threshold configuration"""
    threshold_value: float = Field(ge=0)
    comparison: str = Field(pattern="^(gt|gte|lt|lte|eq)$")
    timeframe_minutes: int = Field(ge=1, le=1440)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class BulkRetryRequest(BaseModel):
    """Request model for bulk retry operations"""
    category: Optional[str] = None
    task_name: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


class ProcessTaskRequest(BaseModel):
    """Request model for processing dead letter tasks"""
    notes: Optional[str] = None


# Dependency functions
def get_redis_client():
    """Get Redis client for dependency injection"""
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


def get_celery_app():
    """Get Celery app for dependency injection"""
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    app = Celery('hermes', broker=redis_url, backend=redis_url)
    return app


def get_task_monitor_service(
    db: Session = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
    celery_app: Celery = Depends(get_celery_app)
):
    """Get task monitor service for dependency injection"""
    return TaskMonitorService(db, redis_client, celery_app)


def get_retry_manager_service(
    db: Session = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
    celery_app: Celery = Depends(get_celery_app)
):
    """Get retry manager service for dependency injection"""
    return RetryManagerService(db, redis_client, celery_app)


def get_dead_letter_service(
    db: Session = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
    celery_app: Celery = Depends(get_celery_app)
):
    """Get dead letter queue service for dependency injection"""
    return DeadLetterQueueService(db, redis_client, celery_app)


def get_alerting_service(
    db: Session = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """Get alerting service for dependency injection"""
    return AlertingService(db, redis_client)


# Task monitoring endpoints
@router.get("", response_model=List[TaskHistoryResponse])
async def get_task_history(
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    monitor_service: TaskMonitorService = Depends(get_task_monitor_service)
):
    """
    Get task execution history with optional filtering.

    Returns paginated list of task execution records with performance metrics,
    error details, and worker information.
    """
    try:
        task_history = monitor_service.get_task_history(limit=limit, status_filter=status)

        # Filter by task name if provided
        if task_name:
            task_history = [t for t in task_history if task_name.lower() in t.task_name.lower()]

        return [
            TaskHistoryResponse(
                id=str(t.id),
                task_id=t.task_id,
                task_name=t.task_name,
                status=t.status,
                queued_at=t.queued_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                duration_ms=t.duration_ms,
                worker_name=t.worker_name,
                retry_count=t.retry_count,
                error_message=t.error_message,
                created_at=t.created_at
            )
            for t in task_history
        ]

    except Exception as e:
        logger.error(f"Error getting task history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task history")


@router.get("/active", response_model=List[TaskMetricsResponse])
async def get_active_tasks(
    monitor_service: TaskMonitorService = Depends(get_task_monitor_service)
):
    """
    Get list of currently active (running) tasks.

    Returns real-time information about tasks that are currently
    queued, processing, or retrying.
    """
    try:
        active_tasks = monitor_service.get_active_tasks()

        return [
            TaskMetricsResponse(
                task_id=task.task_id,
                task_name=task.task_name,
                status=task.status,
                duration_ms=task.duration_ms,
                memory_usage_mb=task.memory_usage_mb,
                cpu_usage_percent=task.cpu_usage_percent,
                worker_name=task.worker_name
            )
            for task in active_tasks
        ]

    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active tasks")


@router.get("/statistics/summary")
async def get_task_statistics(
    timeframe_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    retry_service: RetryManagerService = Depends(get_retry_manager_service)
):
    """
    Get comprehensive task execution statistics.

    Returns summary statistics including success rates, failure rates,
    retry statistics, and performance metrics.
    """
    try:
        stats = retry_service.get_retry_statistics(timeframe_hours=timeframe_hours)

        return {
            "timeframe_hours": timeframe_hours,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting task statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task statistics")


# Retry management endpoints
@router.post("/retry-config/{task_name}")
async def configure_retry_policy(
    task_name: str = Path(..., description="Task name to configure"),
    config: RetryConfigRequest = None,
    retry_service: RetryManagerService = Depends(get_retry_manager_service)
):
    """
    Configure retry policy for a specific task type.

    Allows customization of retry behavior including maximum attempts,
    delay calculation, and retry conditions.
    """
    try:
        # Convert request to RetryConfiguration
        retry_config = RetryConfiguration(
            max_retries=config.max_retries,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            policy=config.policy,
            jitter=config.jitter,
            backoff_multiplier=config.backoff_multiplier
        )

        retry_service.configure_task_retry(task_name, retry_config)

        return {
            "message": f"Retry policy configured for {task_name}",
            "configuration": {
                "max_retries": retry_config.max_retries,
                "base_delay": retry_config.base_delay,
                "max_delay": retry_config.max_delay,
                "policy": retry_config.policy,
                "jitter": retry_config.jitter,
                "backoff_multiplier": retry_config.backoff_multiplier
            }
        }

    except Exception as e:
        logger.error(f"Error configuring retry policy for {task_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure retry policy")


@router.get("/retry-config/{task_name}")
async def get_retry_policy(
    task_name: str = Path(..., description="Task name to retrieve configuration for"),
    retry_service: RetryManagerService = Depends(get_retry_manager_service)
):
    """
    Get current retry policy configuration for a task type.

    Returns the active retry configuration including all policy parameters
    and retry conditions.
    """
    try:
        config = retry_service.get_retry_configuration(task_name)

        return {
            "task_name": task_name,
            "configuration": {
                "max_retries": config.max_retries,
                "base_delay": config.base_delay,
                "max_delay": config.max_delay,
                "policy": config.policy,
                "jitter": config.jitter,
                "backoff_multiplier": config.backoff_multiplier,
                "retry_on_exceptions": config.retry_on_exceptions,
                "no_retry_on_exceptions": config.no_retry_on_exceptions
            }
        }

    except Exception as e:
        logger.error(f"Error getting retry policy for {task_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve retry policy")


# Dead letter queue endpoints
@router.get("/dead-letter", response_model=Dict[str, Any])
async def get_dead_letter_queue(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by failure category"),
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Get paginated list of dead letter queue tasks.

    Returns failed tasks that have exhausted retry attempts,
    with filtering options and detailed failure analysis.
    """
    try:
        result = dlq_service.get_dead_letter_tasks(
            page=page,
            page_size=page_size,
            category_filter=category,
            task_name_filter=task_name,
            processed_filter=processed
        )

        return result

    except Exception as e:
        logger.error(f"Error getting dead letter queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dead letter queue")


@router.post("/dead-letter/bulk-retry")
async def bulk_retry_dead_letter_tasks(
    request: BulkRetryRequest,
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Retry multiple dead letter tasks in bulk.

    Provides efficient batch retry capability with filtering options
    and comprehensive result reporting.
    """
    try:
        result = dlq_service.bulk_retry_tasks(
            category=request.category,
            task_name=request.task_name,
            limit=request.limit,
            user_id="api_user"
        )

        return {
            "message": f"Bulk retry completed: {result['successful']}/{result['total_attempted']} successful",
            "results": result
        }

    except Exception as e:
        logger.error(f"Error in bulk retry: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk retry")


@router.put("/dead-letter/{task_id}/process")
async def process_dead_letter_task(
    request: ProcessTaskRequest,
    task_id: str = Path(..., description="Dead letter task ID to mark as processed"),
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Mark a dead letter task as processed (resolved).

    Allows manual resolution of tasks that don't require retry,
    with optional notes for audit trail.
    """
    try:
        success = dlq_service.mark_task_processed(
            task_id=task_id,
            user_id="api_user",
            notes=request.notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Dead letter task not found")

        return {
            "message": "Dead letter task marked as processed",
            "task_id": task_id,
            "processed_at": datetime.now().isoformat(),
            "notes": request.notes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing dead letter task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process dead letter task")


@router.get("/dead-letter/analysis")
async def get_dead_letter_analysis(
    days_back: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Get comprehensive analysis of dead letter queue patterns.

    Provides insights into failure patterns, recommendations,
    and trend analysis for operational improvement.
    """
    try:
        analysis = dlq_service.analyze_dead_letter_queue(days_back=days_back)

        return {
            "analysis_period_days": days_back,
            "total_tasks": analysis.total_tasks,
            "by_category": analysis.by_category,
            "by_task_name": analysis.by_task_name,
            "by_failure_reason": analysis.by_failure_reason,
            "recent_failures": analysis.recent_failures,
            "top_failing_tasks": analysis.top_failing_tasks,
            "recommendations": analysis.recommendations,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error analyzing dead letter queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze dead letter queue")


@router.get("/dead-letter/{task_id}", response_model=Dict[str, Any])
async def get_dead_letter_task(
    task_id: str = Path(..., description="Dead letter task ID"),
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Get detailed information about a specific dead letter task.

    Returns comprehensive task details including failure analysis,
    execution history, and debugging information.
    """
    try:
        task_details = dlq_service.get_dead_letter_task(task_id)

        if not task_details:
            raise HTTPException(status_code=404, detail="Dead letter task not found")

        return task_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dead letter task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dead letter task")


@router.post("/dead-letter/{task_id}/retry")
async def retry_dead_letter_task(
    task_id: str = Path(..., description="Dead letter task ID to retry"),
    background_tasks: BackgroundTasks = None,
    dlq_service: DeadLetterQueueService = Depends(get_dead_letter_service)
):
    """
    Manually retry a failed task from the dead letter queue.

    Schedules the task for re-execution with original parameters,
    providing debugging and recovery capabilities.
    """
    try:
        result = dlq_service.retry_dead_letter_task(task_id, user_id="api_user")

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)

        return {
            "message": "Task retry scheduled successfully",
            "original_task_id": task_id,
            "new_task_id": result.task_id,
            "scheduled_at": result.retry_scheduled_at.isoformat() if result.retry_scheduled_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying dead letter task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry dead letter task")


# Alert management endpoints
@router.get("/alerts")
async def get_active_alerts(
    alerting_service: AlertingService = Depends(get_alerting_service)
):
    """
    Get list of currently active alerts.

    Returns all unresolved alerts with detailed information
    about threshold breaches and alert conditions.
    """
    try:
        active_alerts = alerting_service.get_active_alerts()

        return {
            "active_alerts": active_alerts,
            "total_count": len(active_alerts),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active alerts")


@router.get("/alerts/history")
async def get_alert_history(
    days_back: int = Query(7, ge=1, le=30, description="Number of days of history"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of alerts"),
    alerting_service: AlertingService = Depends(get_alerting_service)
):
    """
    Get alert history for analysis and reporting.

    Returns historical alert data with filtering options
    for trend analysis and operational reporting.
    """
    try:
        alert_history = alerting_service.get_alert_history(days_back=days_back, limit=limit)

        return {
            "alert_history": alert_history,
            "period_days": days_back,
            "total_count": len(alert_history),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert history")


@router.post("/alerts/thresholds/{alert_type}")
async def configure_alert_threshold(
    request: AlertThresholdRequest,
    alert_type: str = Path(..., description="Alert type to configure"),
    alerting_service: AlertingService = Depends(get_alerting_service)
):
    """
    Configure alert threshold for specific alert type.

    Allows customization of alert conditions, thresholds,
    and severity levels for proactive monitoring.
    """
    try:
        # Validate alert type
        alert_type_lower = alert_type.lower()
        alert_type_value = None
        for key, value in ALERT_TYPE.items():
            if value == alert_type_lower:
                alert_type_value = value
                break
        
        if not alert_type_value:
            raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")

        # Validate severity
        severity_lower = request.severity.lower()
        severity_value = None
        for key, value in ALERT_SEVERITY.items():
            if value == severity_lower:
                severity_value = value
                break
        
        if not severity_value:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {request.severity}")

        # Create threshold configuration
        threshold = AlertThreshold(
            alert_type=alert_type_value,
            threshold_value=request.threshold_value,
            comparison=request.comparison,
            timeframe_minutes=request.timeframe_minutes,
            severity=severity_value,
            enabled=request.enabled
        )

        alerting_service.configure_threshold(alert_type_value, threshold)

        return {
            "message": f"Alert threshold configured for {alert_type}",
            "configuration": {
                "alert_type": alert_type,
                "threshold_value": threshold.threshold_value,
                "comparison": threshold.comparison,
                "timeframe_minutes": threshold.timeframe_minutes,
                "severity": threshold.severity,
                "enabled": threshold.enabled
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring alert threshold for {alert_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure alert threshold")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str = Path(..., description="Alert ID to resolve"),
    alerting_service: AlertingService = Depends(get_alerting_service)
):
    """
    Manually resolve an active alert.

    Allows manual resolution of alerts that have been addressed
    or are false positives, with audit trail tracking.
    """
    try:
        success = alerting_service.resolve_alert(alert_id, user_id="api_user")

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            "message": "Alert resolved successfully",
            "alert_id": alert_id,
            "resolved_at": datetime.now().isoformat(),
            "resolved_by": "api_user"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.post("/alerts/evaluate")
async def trigger_alert_evaluation(
    background_tasks: BackgroundTasks,
    alerting_service: AlertingService = Depends(get_alerting_service)
):
    """
    Manually trigger alert evaluation.

    Forces immediate evaluation of all alert conditions,
    useful for testing and immediate response scenarios.
    """
    try:
        # Run alert evaluation in background
        async def run_evaluation():
            try:
                alerts = await alerting_service.evaluate_alerts()
                logger.info(f"Manual alert evaluation completed: {len(alerts)} alerts triggered")
            except Exception as e:
                logger.error(f"Error in manual alert evaluation: {e}")

        background_tasks.add_task(run_evaluation)

        return {
            "message": "Alert evaluation triggered",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error triggering alert evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger alert evaluation")


# Worker and queue monitoring endpoints
@router.get("/workers")
async def get_worker_metrics(
    monitor_service: TaskMonitorService = Depends(get_task_monitor_service)
):
    """
    Get current worker metrics and health status.

    Returns performance metrics, task counts, and health information
    for all active workers in the cluster.
    """
    try:
        worker_metrics = monitor_service.get_worker_metrics()

        return {
            "workers": [
                {
                    "worker_name": w.worker_name,
                    "is_active": w.is_active,
                    "last_seen": w.last_seen.isoformat(),
                    "current_task_count": w.current_task_count,
                    "tasks_completed_hour": w.tasks_completed_hour,
                    "tasks_completed_day": w.tasks_completed_day,
                    "tasks_failed_hour": w.tasks_failed_hour,
                    "tasks_failed_day": w.tasks_failed_day,
                    "avg_memory_mb": w.avg_memory_mb,
                    "avg_cpu_percent": w.avg_cpu_percent,
                    "uptime_seconds": w.uptime_seconds
                }
                for w in worker_metrics
            ],
            "total_workers": len(worker_metrics),
            "active_workers": len([w for w in worker_metrics if w.is_active]),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting worker metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve worker metrics")


@router.get("/queues")
async def get_queue_metrics(
    monitor_service: TaskMonitorService = Depends(get_task_monitor_service)
):
    """
    Get queue depth and health metrics.

    Returns information about task queue status, depth,
    and processing rates for capacity planning.
    """
    try:
        queue_metrics = monitor_service.get_queue_metrics()

        return {
            "queues": [
                {
                    "queue_name": q.queue_name,
                    "current_depth": q.current_depth,
                    "max_depth_24h": q.max_depth_24h,
                    "avg_depth_24h": q.avg_depth_24h,
                    "tasks_processed_hour": q.tasks_processed_hour,
                    "tasks_processed_day": q.tasks_processed_day,
                    "avg_processing_time_ms": q.avg_processing_time_ms,
                    "active_workers": q.active_workers,
                    "total_workers": q.total_workers,
                    "is_healthy": q.is_healthy,
                    "health_issues": q.health_issues,
                    "last_health_check": q.last_health_check.isoformat()
                }
                for q in queue_metrics
            ],
            "total_queues": len(queue_metrics),
            "healthy_queues": len([q for q in queue_metrics if q.is_healthy]),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting queue metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve queue metrics")


# Generic task details endpoint - MUST be last to avoid matching specific paths
@router.get("/{task_id}", response_model=TaskHistoryResponse)
async def get_task_details(
    task_id: str = Path(..., description="Task ID to retrieve"),
    monitor_service: TaskMonitorService = Depends(get_task_monitor_service)
):
    """
    Get detailed information about a specific task execution.

    Returns comprehensive task details including performance metrics,
    retry history, and error information.
    """
    try:
        task_history = monitor_service._get_task_history(task_id)

        if not task_history:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskHistoryResponse(
            id=str(task_history.id),
            task_id=task_history.task_id,
            task_name=task_history.task_name,
            status=task_history.status,
            queued_at=task_history.queued_at,
            started_at=task_history.started_at,
            completed_at=task_history.completed_at,
            duration_ms=task_history.duration_ms,
            worker_name=task_history.worker_name,
            retry_count=task_history.retry_count,
            error_message=task_history.error_message,
            created_at=task_history.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task details for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task details")