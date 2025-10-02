"""
Alerting service for task failure monitoring and notifications.

This service provides comprehensive alerting capabilities including configurable
thresholds, notification mechanisms, escalation rules, and alert deduplication.
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from uuid import UUID

import redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from models.job_monitoring import (
    TaskAlert, ALERT_TYPE, TaskExecutionHistory, DeadLetterTask,
    TaskQueue, WorkerMetrics, TASK_STATUS, FAILURE_CATEGORY
)


logger = logging.getLogger(__name__)


# Alert severity map - replaces AlertSeverity enum per coding standards
ALERT_SEVERITY = {
    'LOW': 'low',
    'MEDIUM': 'medium',
    'HIGH': 'high',
    'CRITICAL': 'critical'
}

# Notification channel map - replaces NotificationChannel enum per coding standards
NOTIFICATION_CHANNEL = {
    'LOG': 'log',
    'WEBHOOK': 'webhook',
    'EMAIL': 'email',
    'SLACK': 'slack'
}


@dataclass
class AlertThreshold:
    """Configuration for alert thresholds"""
    alert_type: str
    threshold_value: float
    comparison: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    timeframe_minutes: int = 60
    severity: str = ALERT_SEVERITY['MEDIUM']
    enabled: bool = True


@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    channel: str
    endpoint: Optional[str] = None  # URL for webhook, email address, etc.
    enabled: bool = True
    severity_filter: List[str] = None  # Only send for these severities
    rate_limit_minutes: int = 60  # Minimum time between similar notifications


@dataclass
class AlertEvent:
    """Alert event data"""
    alert_type: str
    severity: str
    current_value: float
    threshold_value: float
    message: str
    context: Dict[str, Any]
    timestamp: datetime


class AlertingService:
    """
    Service for monitoring task execution and generating alerts.

    Provides configurable alerting with thresholds, notifications,
    escalation rules, and intelligent deduplication.
    """

    def __init__(self, db_session: Session, redis_client: redis.Redis):
        """
        Initialize the alerting service.

        Args:
            db_session: Database session for alert persistence
            redis_client: Redis client for caching and rate limiting
        """
        self.db_session = db_session
        self.redis_client = redis_client

        # Default alert thresholds
        self.default_thresholds = {
            ALERT_TYPE['HIGH_FAILURE_RATE']: AlertThreshold(
                alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
                threshold_value=20.0,  # 20% failure rate
                comparison='gte',
                timeframe_minutes=60,
                severity=ALERT_SEVERITY['HIGH']
            ),
            ALERT_TYPE['QUEUE_BACKUP']: AlertThreshold(
                alert_type=ALERT_TYPE['QUEUE_BACKUP'],
                threshold_value=100,  # 100 tasks in queue
                comparison='gte',
                timeframe_minutes=30,
                severity=ALERT_SEVERITY['MEDIUM']
            ),
            ALERT_TYPE['DEAD_LETTER_THRESHOLD']: AlertThreshold(
                alert_type=ALERT_TYPE['DEAD_LETTER_THRESHOLD'],
                threshold_value=10,  # 10 dead letter tasks
                comparison='gte',
                timeframe_minutes=60,
                severity=ALERT_SEVERITY['HIGH']
            ),
            ALERT_TYPE['WORKER_DOWN']: AlertThreshold(
                alert_type=ALERT_TYPE['WORKER_DOWN'],
                threshold_value=1,  # 1 worker down
                comparison='gte',
                timeframe_minutes=5,
                severity=ALERT_SEVERITY['CRITICAL']
            ),
            ALERT_TYPE['MEMORY_HIGH']: AlertThreshold(
                alert_type=ALERT_TYPE['MEMORY_HIGH'],
                threshold_value=85.0,  # 85% memory usage
                comparison='gte',
                timeframe_minutes=30,
                severity=ALERT_SEVERITY['MEDIUM']
            ),
            ALERT_TYPE['PROCESSING_SLOW']: AlertThreshold(
                alert_type=ALERT_TYPE['PROCESSING_SLOW'],
                threshold_value=30000,  # 30 seconds average processing time
                comparison='gte',
                timeframe_minutes=60,
                severity=ALERT_SEVERITY['MEDIUM']
            )
        }

        # Active thresholds (can be customized)
        self.active_thresholds = self.default_thresholds.copy()

        # Notification configurations
        self.notification_configs: List[NotificationConfig] = [
            NotificationConfig(
                channel=NOTIFICATION_CHANNEL['LOG'],
                enabled=True
            )
        ]

        # Alert handlers
        self.alert_handlers: Dict[str, Callable] = {
            NOTIFICATION_CHANNEL['LOG']: self._handle_log_notification,
            NOTIFICATION_CHANNEL['WEBHOOK']: self._handle_webhook_notification,
            NOTIFICATION_CHANNEL['EMAIL']: self._handle_email_notification,
        }

        # Cache keys
        self.ALERT_CACHE_KEY = "hermes:alerts:active"
        self.NOTIFICATION_RATE_LIMIT_KEY = "hermes:alerts:rate_limit"
        self.ALERT_STATS_KEY = "hermes:alerts:stats"

        # Configuration
        self.EVALUATION_INTERVAL = 300  # 5 minutes
        self.MAX_ESCALATION_LEVEL = 3
        self.DEDUPLICATION_WINDOW = 3600  # 1 hour

    def configure_threshold(self, alert_type: str, threshold: AlertThreshold):
        """
        Configure alert threshold for specific alert type.

        Args:
            alert_type: Type of alert to configure
            threshold: Threshold configuration
        """
        self.active_thresholds[alert_type] = threshold

        # Cache threshold configuration
        try:
            threshold_data = asdict(threshold)
            threshold_data['alert_type'] = threshold.alert_type
            threshold_data['severity'] = threshold.severity

            self.redis_client.hset(
                f"hermes:alert:threshold:{alert_type}",
                mapping=threshold_data
            )
            self.redis_client.expire(f"hermes:alert:threshold:{alert_type}", 86400)

            logger.info(f"Configured alert threshold for {alert_type}: {threshold}")

        except Exception as e:
            logger.error(f"Error caching alert threshold: {e}")

    def add_notification_config(self, config: NotificationConfig):
        """
        Add notification configuration.

        Args:
            config: Notification configuration to add
        """
        self.notification_configs.append(config)
        logger.info(f"Added notification config for {config.channel}")

    async def evaluate_alerts(self) -> List[AlertEvent]:
        """
        Evaluate all alert conditions and generate alerts.

        Returns:
            List[AlertEvent]: List of triggered alerts
        """
        triggered_alerts = []

        try:
            for alert_type, threshold in self.active_thresholds.items():
                if not threshold.enabled:
                    continue

                alert_event = await self._evaluate_threshold(threshold)
                if alert_event:
                    triggered_alerts.append(alert_event)

            # Process triggered alerts
            for alert_event in triggered_alerts:
                await self._process_alert(alert_event)

            return triggered_alerts

        except Exception as e:
            logger.error(f"Error evaluating alerts: {e}")
            return []

    async def _evaluate_threshold(self, threshold: AlertThreshold) -> Optional[AlertEvent]:
        """Evaluate a specific threshold and return alert if triggered"""
        try:
            current_value = await self._calculate_metric_value(threshold)

            if current_value is None:
                return None

            # Check if threshold is breached
            threshold_breached = self._check_threshold(current_value, threshold.threshold_value, threshold.comparison)

            if not threshold_breached:
                # Check if we should resolve an existing alert
                await self._resolve_alert_if_exists(threshold.alert_type)
                return None

            # Check for deduplication
            if await self._is_alert_deduplicated(threshold.alert_type, current_value):
                return None

            # Create alert event
            alert_event = AlertEvent(
                alert_type=threshold.alert_type,
                severity=threshold.severity,
                current_value=current_value,
                threshold_value=threshold.threshold_value,
                message=self._generate_alert_message(threshold, current_value),
                context=await self._get_alert_context(threshold.alert_type),
                timestamp=datetime.now()
            )

            return alert_event

        except Exception as e:
            logger.error(f"Error evaluating threshold {threshold.alert_type}: {e}")
            return None

    async def _calculate_metric_value(self, threshold: AlertThreshold) -> Optional[float]:
        """Calculate the current metric value for the threshold"""
        try:
            timeframe_start = datetime.now() - timedelta(minutes=threshold.timeframe_minutes)

            if threshold.alert_type == ALERT_TYPE['HIGH_FAILURE_RATE']:
                # Calculate failure rate percentage
                total_tasks = self.db_session.query(TaskExecutionHistory).filter(
                    TaskExecutionHistory.created_at >= timeframe_start
                ).count()

                if total_tasks == 0:
                    return 0.0

                failed_tasks = self.db_session.query(TaskExecutionHistory).filter(
                    TaskExecutionHistory.created_at >= timeframe_start,
                    TaskExecutionHistory.status.in_([TASK_STATUS['FAILED'], TASK_STATUS['DEAD_LETTER']])
                ).count()

                return (failed_tasks / total_tasks) * 100

            elif threshold.alert_type == ALERT_TYPE['QUEUE_BACKUP']:
                # Calculate current queue depth
                queue_metrics = self.db_session.query(TaskQueue).all()
                total_depth = sum(q.current_depth for q in queue_metrics)
                return float(total_depth)

            elif threshold.alert_type == ALERT_TYPE['DEAD_LETTER_THRESHOLD']:
                # Count dead letter tasks in timeframe
                dlq_count = self.db_session.query(DeadLetterTask).filter(
                    DeadLetterTask.created_at >= timeframe_start
                ).count()
                return float(dlq_count)

            elif threshold.alert_type == ALERT_TYPE['WORKER_DOWN']:
                # Count inactive workers
                inactive_workers = self.db_session.query(WorkerMetrics).filter(
                    WorkerMetrics.is_active == False,
                    WorkerMetrics.last_seen >= timeframe_start
                ).count()
                return float(inactive_workers)

            elif threshold.alert_type == ALERT_TYPE['MEMORY_HIGH']:
                # Calculate average memory usage across active workers
                active_workers = self.db_session.query(WorkerMetrics).filter(
                    WorkerMetrics.is_active == True
                ).all()

                if not active_workers:
                    return 0.0

                avg_memory = sum(w.avg_memory_mb for w in active_workers) / len(active_workers)
                # Convert to percentage (assuming 1GB = 1024MB as baseline)
                return (avg_memory / 1024) * 100

            elif threshold.alert_type == ALERT_TYPE['PROCESSING_SLOW']:
                # Calculate average processing time
                avg_duration = self.db_session.query(func.avg(TaskExecutionHistory.duration_ms)).filter(
                    TaskExecutionHistory.created_at >= timeframe_start,
                    TaskExecutionHistory.status == TASK_STATUS['COMPLETED'],
                    TaskExecutionHistory.duration_ms.isnot(None)
                ).scalar()

                return float(avg_duration) if avg_duration else 0.0

            return None

        except Exception as e:
            logger.error(f"Error calculating metric for {threshold.alert_type}: {e}")
            return None

    def _check_threshold(self, current_value: float, threshold_value: float, comparison: str) -> bool:
        """Check if current value breaches threshold"""
        if comparison == 'gt':
            return current_value > threshold_value
        elif comparison == 'gte':
            return current_value >= threshold_value
        elif comparison == 'lt':
            return current_value < threshold_value
        elif comparison == 'lte':
            return current_value <= threshold_value
        elif comparison == 'eq':
            return current_value == threshold_value
        else:
            logger.warning(f"Unknown comparison operator: {comparison}")
            return False

    async def _is_alert_deduplicated(self, alert_type: str, current_value: float) -> bool:
        """Check if alert should be deduplicated"""
        try:
            # Check for recent similar alert
            recent_alert = self.redis_client.get(f"hermes:alert:recent:{alert_type}")
            if recent_alert:
                return True

            # Check database for active alert
            active_alert = self.db_session.query(TaskAlert).filter(
                TaskAlert.alert_type == alert_type,
                TaskAlert.resolved_at.is_(None)
            ).first()

            if active_alert:
                # Update current value but don't create new alert
                active_alert.current_value = current_value
                active_alert.updated_at = datetime.now()
                self.db_session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking alert deduplication: {e}")
            return False

    async def _process_alert(self, alert_event: AlertEvent):
        """Process and handle an alert event"""
        try:
            # Create database record
            alert_record = TaskAlert(
                alert_type=alert_event.alert_type,
                threshold_value=alert_event.threshold_value,
                current_value=alert_event.current_value,
                alert_condition=f"{alert_event.alert_type} >= {alert_event.threshold_value}",
                triggered_at=alert_event.timestamp,
                alert_data=alert_event.context
            )

            self.db_session.add(alert_record)
            self.db_session.commit()

            # Cache alert for deduplication
            self.redis_client.setex(
                f"hermes:alert:recent:{alert_event.alert_type}",
                self.DEDUPLICATION_WINDOW,
                json.dumps({
                    'value': alert_event.current_value,
                    'timestamp': alert_event.timestamp.isoformat()
                })
            )

            # Send notifications
            await self._send_notifications(alert_event, alert_record.id)

            # Update alert statistics
            await self._update_alert_statistics(alert_event)

            logger.info(f"Processed alert: {alert_event.alert_type} "
                       f"(value: {alert_event.current_value}, threshold: {alert_event.threshold_value})")

        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            self.db_session.rollback()

    async def _send_notifications(self, alert_event: AlertEvent, alert_id: str):
        """Send notifications for an alert"""
        for config in self.notification_configs:
            if not config.enabled:
                continue

            # Check severity filter
            if config.severity_filter and alert_event.severity not in config.severity_filter:
                continue

            # Check rate limiting
            if await self._is_rate_limited(config, alert_event.alert_type):
                continue

            # Send notification
            try:
                handler = self.alert_handlers.get(config.channel)
                if handler:
                    await handler(alert_event, config, alert_id)

                # Set rate limit
                await self._set_rate_limit(config, alert_event.alert_type)

            except Exception as e:
                logger.error(f"Error sending {config.channel} notification: {e}")

    async def _handle_log_notification(self, alert_event: AlertEvent, config: NotificationConfig, alert_id: str):
        """Handle log notification"""
        log_level = {
            ALERT_SEVERITY['LOW']: logging.INFO,
            ALERT_SEVERITY['MEDIUM']: logging.WARNING,
            ALERT_SEVERITY['HIGH']: logging.ERROR,
            ALERT_SEVERITY['CRITICAL']: logging.CRITICAL
        }.get(alert_event.severity, logging.WARNING)

        logger.log(log_level, f"ALERT [{alert_event.severity.upper()}] {alert_event.message}")

    async def _handle_webhook_notification(self, alert_event: AlertEvent, config: NotificationConfig, alert_id: str):
        """Handle webhook notification"""
        if not config.endpoint:
            logger.warning("Webhook notification configured but no endpoint provided")
            return

        try:
            import httpx

            payload = {
                'alert_id': alert_id,
                'alert_type': alert_event.alert_type,
                'severity': alert_event.severity,
                'message': alert_event.message,
                'current_value': alert_event.current_value,
                'threshold_value': alert_event.threshold_value,
                'timestamp': alert_event.timestamp.isoformat(),
                'context': alert_event.context
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.endpoint,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info(f"Webhook notification sent successfully to {config.endpoint}")

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

    async def _handle_email_notification(self, alert_event: AlertEvent, config: NotificationConfig, alert_id: str):
        """Handle email notification (placeholder)"""
        # This would integrate with an email service
        logger.info(f"Email notification would be sent to {config.endpoint}: {alert_event.message}")

    async def _resolve_alert_if_exists(self, alert_type: str):
        """Resolve an existing alert if conditions are no longer met"""
        try:
            active_alert = self.db_session.query(TaskAlert).filter(
                TaskAlert.alert_type == alert_type,
                TaskAlert.resolved_at.is_(None)
            ).first()

            if active_alert:
                active_alert.resolved_at = datetime.now()
                active_alert.auto_resolved = True
                active_alert.updated_at = datetime.now()
                self.db_session.commit()

                # Remove from cache
                self.redis_client.delete(f"hermes:alert:recent:{alert_type}")

                logger.info(f"Auto-resolved alert: {alert_type}")

        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            self.db_session.rollback()

    async def _get_alert_context(self, alert_type: str) -> Dict[str, Any]:
        """Get additional context for an alert"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type
        }

        try:
            if alert_type == ALERT_TYPE['HIGH_FAILURE_RATE']:
                # Get top failing tasks
                timeframe_start = datetime.now() - timedelta(hours=1)
                failing_tasks = self.db_session.query(
                    TaskExecutionHistory.task_name,
                    func.count(TaskExecutionHistory.id).label('failure_count')
                ).filter(
                    TaskExecutionHistory.created_at >= timeframe_start,
                    TaskExecutionHistory.status.in_([TASK_STATUS['FAILED'], TASK_STATUS['DEAD_LETTER']])
                ).group_by(TaskExecutionHistory.task_name).order_by(desc('failure_count')).limit(5).all()

                context['top_failing_tasks'] = [
                    {'task_name': task.task_name, 'failure_count': task.failure_count}
                    for task in failing_tasks
                ]

            elif alert_type == ALERT_TYPE['WORKER_DOWN']:
                # Get details of down workers
                inactive_workers = self.db_session.query(WorkerMetrics).filter(
                    WorkerMetrics.is_active == False
                ).all()

                context['down_workers'] = [
                    {
                        'worker_name': worker.worker_name,
                        'last_seen': worker.last_seen.isoformat(),
                        'tasks_today': worker.tasks_completed_day
                    }
                    for worker in inactive_workers
                ]

        except Exception as e:
            logger.error(f"Error getting alert context: {e}")

        return context

    def _generate_alert_message(self, threshold: AlertThreshold, current_value: float) -> str:
        """Generate human-readable alert message"""
        alert_type = threshold.alert_type.replace('_', ' ').title()

        if threshold.alert_type == ALERT_TYPE['HIGH_FAILURE_RATE']:
            return f"{alert_type}: {current_value:.1f}% failure rate exceeds threshold of {threshold.threshold_value}%"
        elif threshold.alert_type == ALERT_TYPE['QUEUE_BACKUP']:
            return f"{alert_type}: {int(current_value)} tasks in queue exceeds threshold of {int(threshold.threshold_value)}"
        elif threshold.alert_type == ALERT_TYPE['DEAD_LETTER_THRESHOLD']:
            return f"{alert_type}: {int(current_value)} dead letter tasks exceeds threshold of {int(threshold.threshold_value)}"
        elif threshold.alert_type == ALERT_TYPE['WORKER_DOWN']:
            return f"{alert_type}: {int(current_value)} workers are down"
        elif threshold.alert_type == ALERT_TYPE['MEMORY_HIGH']:
            return f"{alert_type}: {current_value:.1f}% memory usage exceeds threshold of {threshold.threshold_value}%"
        elif threshold.alert_type == ALERT_TYPE['PROCESSING_SLOW']:
            return f"{alert_type}: {current_value:.0f}ms average processing time exceeds threshold of {threshold.threshold_value}ms"
        else:
            return f"{alert_type}: Current value {current_value} exceeds threshold {threshold.threshold_value}"

    async def _is_rate_limited(self, config: NotificationConfig, alert_type: str) -> bool:
        """Check if notification is rate limited"""
        rate_limit_key = f"{self.NOTIFICATION_RATE_LIMIT_KEY}:{config.channel}:{alert_type}"
        return self.redis_client.exists(rate_limit_key)

    async def _set_rate_limit(self, config: NotificationConfig, alert_type: str):
        """Set rate limit for notification"""
        rate_limit_key = f"{self.NOTIFICATION_RATE_LIMIT_KEY}:{config.channel}:{alert_type}"
        self.redis_client.setex(rate_limit_key, config.rate_limit_minutes * 60, "1")

    async def _update_alert_statistics(self, alert_event: AlertEvent):
        """Update alert statistics"""
        try:
            stats_key = f"{self.ALERT_STATS_KEY}:{datetime.now().date().isoformat()}"
            field_key = f"{alert_event.alert_type}:{alert_event.severity}"

            self.redis_client.hincrby(stats_key, field_key, 1)
            self.redis_client.expire(stats_key, 86400 * 7)  # Keep for 7 days

        except Exception as e:
            logger.error(f"Error updating alert statistics: {e}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of currently active alerts"""
        try:
            active_alerts = self.db_session.query(TaskAlert).filter(
                TaskAlert.resolved_at.is_(None)
            ).order_by(desc(TaskAlert.triggered_at)).all()

            return [self._serialize_alert(alert) for alert in active_alerts]

        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    def get_alert_history(self, days_back: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            alerts = self.db_session.query(TaskAlert).filter(
                TaskAlert.triggered_at >= cutoff_date
            ).order_by(desc(TaskAlert.triggered_at)).limit(limit).all()

            return [self._serialize_alert(alert) for alert in alerts]

        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []

    def _ensure_uuid(self, alert_id: Union[str, UUID]) -> UUID:
        """Convert string to UUID if needed"""
        if isinstance(alert_id, str):
            return UUID(alert_id)
        return alert_id

    def resolve_alert(self, alert_id: Union[str, UUID], user_id: str = None) -> bool:
        """Manually resolve an alert"""
        try:
            # Convert string ID to UUID if needed
            alert_uuid = self._ensure_uuid(alert_id)

            alert = self.db_session.query(TaskAlert).filter(
                TaskAlert.id == alert_uuid
            ).first()

            if not alert:
                return False

            alert.resolved_at = datetime.now()
            alert.auto_resolved = False
            alert.resolution_data = {'resolved_by': user_id} if user_id else {}
            alert.updated_at = datetime.now()

            self.db_session.commit()

            logger.info(f"Alert {alert_id} resolved by {user_id or 'system'}")
            return True

        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            self.db_session.rollback()
            return False

    def _serialize_alert(self, alert: TaskAlert) -> Dict[str, Any]:
        """Serialize alert to dictionary"""
        return {
            'id': str(alert.id),
            'alert_type': alert.alert_type,
            'threshold_value': alert.threshold_value,
            'current_value': alert.current_value,
            'alert_condition': alert.alert_condition,
            'task_name': alert.task_name,
            'queue_name': alert.queue_name,
            'worker_name': alert.worker_name,
            'triggered_at': alert.triggered_at.isoformat(),
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
            'auto_resolved': alert.auto_resolved,
            'notification_sent': alert.notification_sent,
            'notification_sent_at': alert.notification_sent_at.isoformat() if alert.notification_sent_at else None,
            'escalation_level': alert.escalation_level,
            'alert_data': alert.alert_data,
            'resolution_data': alert.resolution_data,
            'created_at': alert.created_at.isoformat(),
            'updated_at': alert.updated_at.isoformat()
        }