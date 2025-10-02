"""
Task monitoring service for background job management.

This service provides comprehensive monitoring of Celery task execution including
real-time status tracking, performance metrics, and task history management.
"""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import redis
import psutil
from celery import Celery
from celery.events.state import State
from celery.events import Event
from sqlalchemy.orm import Session

from models.job_monitoring import (
    TaskExecutionHistory, TASK_STATUS, WorkerMetrics, TaskQueue
)


logger = logging.getLogger(__name__)


@dataclass
class TaskMetrics:
    """Data class for task performance metrics"""
    task_id: str
    task_name: str
    duration_ms: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    worker_name: Optional[str] = None
    status: str = TASK_STATUS['QUEUED']


@dataclass
class WorkerStatus:
    """Data class for worker status information"""
    worker_name: str
    is_active: bool
    last_seen: datetime
    current_tasks: int
    total_processed: int
    total_failed: int
    avg_memory_mb: float
    avg_cpu_percent: float


class TaskMonitorService:
    """
    Service for monitoring Celery task execution and performance.

    Provides real-time task tracking, performance metrics collection,
    and comprehensive task history management.
    """

    def __init__(self, db_session: Session, redis_client: redis.Redis, celery_app: Optional[Celery] = None):
        """
        Initialize the task monitoring service.

        Args:
            db_session: Database session for persisting monitoring data
            redis_client: Redis client for real-time data storage
            celery_app: Optional Celery application instance
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.celery_app = celery_app or self._get_celery_app()

        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        self.task_cache: Dict[str, TaskMetrics] = {}
        self.worker_cache: Dict[str, WorkerStatus] = {}

        # Performance tracking
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.last_cleanup = datetime.now()

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            'task-sent': [],
            'task-started': [],
            'task-succeeded': [],
            'task-failed': [],
            'task-retry': [],
            'worker-online': [],
            'worker-offline': []
        }

        # Cache keys
        self.TASK_CACHE_KEY = "hermes:tasks:active"
        self.WORKER_CACHE_KEY = "hermes:workers:active"
        self.METRICS_CACHE_KEY = "hermes:metrics:tasks"

    def _get_celery_app(self) -> Celery:
        """Get or create Celery application instance"""
        if hasattr(self, '_celery_app_instance'):
            return self._celery_app_instance

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        app = Celery('hermes', broker=redis_url, backend=redis_url)

        app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_send_sent_event=True,
            worker_send_task_events=True,
            result_expires=3600,
        )

        self._celery_app_instance = app
        return app

    def start_monitoring(self) -> bool:
        """
        Start real-time task monitoring.

        Returns:
            bool: True if monitoring started successfully
        """
        if self.is_monitoring:
            logger.warning("Task monitoring is already running")
            return False

        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()

            logger.info("Task monitoring started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start task monitoring: {e}")
            self.is_monitoring = False
            return False

    def stop_monitoring(self) -> bool:
        """
        Stop real-time task monitoring.

        Returns:
            bool: True if monitoring stopped successfully
        """
        if not self.is_monitoring:
            logger.warning("Task monitoring is not running")
            return False

        try:
            self.is_monitoring = False

            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)

            logger.info("Task monitoring stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop task monitoring: {e}")
            return False

    def _monitoring_loop(self):
        """Main monitoring loop for processing Celery events"""
        state = State()

        # Setup event handlers
        def on_task_sent(event: Event):
            self._handle_task_sent(event, state)

        def on_task_started(event: Event):
            self._handle_task_started(event, state)

        def on_task_succeeded(event: Event):
            self._handle_task_completed(event, state, TASK_STATUS['COMPLETED'])

        def on_task_failed(event: Event):
            self._handle_task_completed(event, state, TASK_STATUS['FAILED'])

        def on_task_retry(event: Event):
            self._handle_task_retry(event, state)

        def on_worker_online(event: Event):
            self._handle_worker_online(event)

        def on_worker_offline(event: Event):
            self._handle_worker_offline(event)

        # Register event handlers
        try:
            with self.celery_app.connection() as connection:
                recv = self.celery_app.events.Receiver(connection, handlers={
                    'task-sent': on_task_sent,
                    'task-started': on_task_started,
                    'task-succeeded': on_task_succeeded,
                    'task-failed': on_task_failed,
                    'task-retry': on_task_retry,
                    'worker-online': on_worker_online,
                    'worker-offline': on_worker_offline,
                })

                logger.info("Starting Celery event monitoring loop")
                recv.capture(limit=None, timeout=None, wakeup=True)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            self.is_monitoring = False

    def _handle_task_sent(self, event: Event, state: State):
        """Handle task-sent event"""
        try:
            task_id = event['uuid']
            task_name = event.get('name', 'unknown')

            # Create task metrics
            metrics = TaskMetrics(
                task_id=task_id,
                task_name=task_name,
                status=TASK_STATUS['QUEUED']
            )

            # Cache task
            self.task_cache[task_id] = metrics

            # Store in Redis for real-time access
            self._cache_task_data(task_id, metrics)

            # Create database record
            self._create_task_history(event, TASK_STATUS['QUEUED'])

            # Call registered handlers
            for handler in self.event_handlers.get('task-sent', []):
                handler(event)

            logger.debug(f"Task sent: {task_name} ({task_id})")

        except Exception as e:
            logger.error(f"Error handling task-sent event: {e}")

    def _handle_task_started(self, event: Event, state: State):
        """Handle task-started event"""
        try:
            task_id = event['uuid']
            worker_name = event.get('hostname', 'unknown')

            # Update task metrics
            if task_id in self.task_cache:
                self.task_cache[task_id].status = TASK_STATUS['PROCESSING']
                self.task_cache[task_id].worker_name = worker_name

            # Update Redis cache
            self._cache_task_data(task_id, self.task_cache.get(task_id))

            # Update database record
            self._update_task_history(task_id, TASK_STATUS['PROCESSING'], {
                'started_at': datetime.fromtimestamp(event['timestamp']),
                'worker_name': worker_name
            })

            # Update worker metrics
            self._update_worker_metrics(worker_name, 'task_started')

            # Call registered handlers
            for handler in self.event_handlers.get('task-started', []):
                handler(event)

            logger.debug(f"Task started: {task_id} on {worker_name}")

        except Exception as e:
            logger.error(f"Error handling task-started event: {e}")

    def _handle_task_completed(self, event: Event, state: State, status: str):
        """Handle task-succeeded or task-failed event"""
        try:
            task_id = event['uuid']
            completed_at = datetime.fromtimestamp(event['timestamp'])

            # Calculate duration and update metrics
            if task_id in self.task_cache:
                metrics = self.task_cache[task_id]
                metrics.status = status

                # Calculate duration if we have start time
                task_history = self._get_task_history(task_id)
                if task_history and task_history.started_at:
                    duration = (completed_at - task_history.started_at).total_seconds() * 1000
                    metrics.duration_ms = int(duration)

            # Update database record
            update_data = {
                'completed_at': completed_at,
                'status': status
            }

            if status == TASK_STATUS['FAILED']:
                update_data['error_message'] = event.get('exception', 'Unknown error')
                update_data['error_traceback'] = event.get('traceback', '')

            if task_id in self.task_cache and self.task_cache[task_id].duration_ms:
                update_data['duration_ms'] = self.task_cache[task_id].duration_ms

            self._update_task_history(task_id, status, update_data)

            # Update worker metrics
            worker_name = event.get('hostname', 'unknown')
            metric_type = 'task_completed' if status == TASK_STATUS['COMPLETED'] else 'task_failed'
            self._update_worker_metrics(worker_name, metric_type)

            # Remove from active cache
            if task_id in self.task_cache:
                del self.task_cache[task_id]

            self._remove_task_from_cache(task_id)

            # Call registered handlers
            event_type = 'task-succeeded' if status == TASK_STATUS['COMPLETED'] else 'task-failed'
            for handler in self.event_handlers.get(event_type, []):
                handler(event)

            logger.debug(f"Task {status}: {task_id}")

        except Exception as e:
            logger.error(f"Error handling task completion event: {e}")

    def _handle_task_retry(self, event: Event, state: State):
        """Handle task-retry event"""
        try:
            task_id = event['uuid']
            retry_count = event.get('retries', 0)

            # Update task metrics
            if task_id in self.task_cache:
                self.task_cache[task_id].status = TASK_STATUS['RETRYING']

            # Update database record
            self._update_task_history(task_id, TASK_STATUS['RETRYING'], {
                'retry_count': retry_count,
                'error_message': event.get('reason', 'Retry scheduled')
            })

            # Call registered handlers
            for handler in self.event_handlers.get('task-retry', []):
                handler(event)

            logger.debug(f"Task retry: {task_id} (attempt {retry_count})")

        except Exception as e:
            logger.error(f"Error handling task-retry event: {e}")

    def _handle_worker_online(self, event: Event):
        """Handle worker-online event"""
        try:
            worker_name = event.get('hostname', 'unknown')

            # Update worker status
            worker_status = WorkerStatus(
                worker_name=worker_name,
                is_active=True,
                last_seen=datetime.now(),
                current_tasks=0,
                total_processed=0,
                total_failed=0,
                avg_memory_mb=0.0,
                avg_cpu_percent=0.0
            )

            self.worker_cache[worker_name] = worker_status
            self._cache_worker_data(worker_name, worker_status)

            # Call registered handlers
            for handler in self.event_handlers.get('worker-online', []):
                handler(event)

            logger.info(f"Worker online: {worker_name}")

        except Exception as e:
            logger.error(f"Error handling worker-online event: {e}")

    def _handle_worker_offline(self, event: Event):
        """Handle worker-offline event"""
        try:
            worker_name = event.get('hostname', 'unknown')

            # Update worker status
            if worker_name in self.worker_cache:
                self.worker_cache[worker_name].is_active = False
                self._cache_worker_data(worker_name, self.worker_cache[worker_name])

            # Call registered handlers
            for handler in self.event_handlers.get('worker-offline', []):
                handler(event)

            logger.info(f"Worker offline: {worker_name}")

        except Exception as e:
            logger.error(f"Error handling worker-offline event: {e}")

    def _create_task_history(self, event: Event, status: str):
        """Create task execution history record"""
        try:
            task_history = TaskExecutionHistory(
                task_id=event['uuid'],
                task_name=event.get('name', 'unknown'),
                status=status,
                queued_at=datetime.fromtimestamp(event['timestamp']),
                task_args=event.get('args', []),
                task_kwargs=event.get('kwargs', {}),
                queue_name=event.get('routing_key', 'default')
            )

            self.db_session.add(task_history)
            self.db_session.commit()

        except Exception as e:
            logger.error(f"Error creating task history: {e}")
            self.db_session.rollback()

    def _update_task_history(self, task_id: str, status: str, update_data: Dict[str, Any]):
        """Update task execution history record"""
        try:
            task_history = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task_id
            ).first()

            if task_history:
                task_history.status = status
                task_history.updated_at = datetime.now()

                for key, value in update_data.items():
                    if hasattr(task_history, key):
                        setattr(task_history, key, value)

                self.db_session.commit()

        except Exception as e:
            logger.error(f"Error updating task history: {e}")
            self.db_session.rollback()

    def _get_task_history(self, task_id: str) -> Optional[TaskExecutionHistory]:
        """Get task execution history record"""
        try:
            return self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting task history: {e}")
            return None

    def _update_worker_metrics(self, worker_name: str, metric_type: str):
        """Update worker performance metrics"""
        try:
            # Get or create worker metrics
            worker_metrics = self.db_session.query(WorkerMetrics).filter(
                WorkerMetrics.worker_name == worker_name
            ).first()

            if not worker_metrics:
                worker_metrics = WorkerMetrics(
                    worker_name=worker_name,
                    is_active=True,
                    last_seen=datetime.now()
                )
                self.db_session.add(worker_metrics)

            # Update metrics based on type
            if metric_type == 'task_started':
                worker_metrics.current_task_count += 1
            elif metric_type == 'task_completed':
                worker_metrics.current_task_count = max(0, worker_metrics.current_task_count - 1)
                worker_metrics.tasks_completed_hour += 1
                worker_metrics.tasks_completed_day += 1
            elif metric_type == 'task_failed':
                worker_metrics.current_task_count = max(0, worker_metrics.current_task_count - 1)
                worker_metrics.tasks_failed_hour += 1
                worker_metrics.tasks_failed_day += 1

            worker_metrics.last_seen = datetime.now()
            worker_metrics.updated_at = datetime.now()

            self.db_session.commit()

        except Exception as e:
            logger.error(f"Error updating worker metrics: {e}")
            self.db_session.rollback()

    def _cache_task_data(self, task_id: str, metrics: Optional[TaskMetrics]):
        """Cache task data in Redis"""
        if not metrics:
            return

        try:
            task_data = {
                'task_id': metrics.task_id,
                'task_name': metrics.task_name,
                'status': metrics.status,
                'duration_ms': metrics.duration_ms,
                'memory_usage_mb': metrics.memory_usage_mb,
                'cpu_usage_percent': metrics.cpu_usage_percent,
                'worker_name': metrics.worker_name,
                'timestamp': time.time()
            }

            self.redis_client.hset(f"{self.TASK_CACHE_KEY}:{task_id}", mapping=task_data)
            self.redis_client.expire(f"{self.TASK_CACHE_KEY}:{task_id}", 3600)  # 1 hour

        except Exception as e:
            logger.error(f"Error caching task data: {e}")

    def _remove_task_from_cache(self, task_id: str):
        """Remove task from Redis cache"""
        try:
            self.redis_client.delete(f"{self.TASK_CACHE_KEY}:{task_id}")
        except Exception as e:
            logger.error(f"Error removing task from cache: {e}")

    def _cache_worker_data(self, worker_name: str, worker_status: WorkerStatus):
        """Cache worker data in Redis"""
        try:
            worker_data = {
                'worker_name': worker_status.worker_name,
                'is_active': str(worker_status.is_active),
                'last_seen': worker_status.last_seen.isoformat(),
                'current_tasks': worker_status.current_tasks,
                'total_processed': worker_status.total_processed,
                'total_failed': worker_status.total_failed,
                'avg_memory_mb': worker_status.avg_memory_mb,
                'avg_cpu_percent': worker_status.avg_cpu_percent,
                'timestamp': time.time()
            }

            self.redis_client.hset(f"{self.WORKER_CACHE_KEY}:{worker_name}", mapping=worker_data)
            self.redis_client.expire(f"{self.WORKER_CACHE_KEY}:{worker_name}", 3600)  # 1 hour

        except Exception as e:
            logger.error(f"Error caching worker data: {e}")

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register custom event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)

    def _decode_redis_value(self, value):
        """Decode Redis bytes to string if needed"""
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return value if value else ''

    def get_active_tasks(self) -> List[TaskMetrics]:
        """Get list of currently active tasks"""
        try:
            # Get from Redis cache for real-time data
            active_tasks = []
            task_keys = self.redis_client.keys(f"{self.TASK_CACHE_KEY}:*")

            for key in task_keys:
                task_data = self.redis_client.hgetall(key)
                if task_data:
                    # Decode bytes keys and values from Redis
                    decoded_data = {}
                    for k, v in task_data.items():
                        key_str = self._decode_redis_value(k)
                        val_str = self._decode_redis_value(v)
                        decoded_data[key_str] = val_str

                    metrics = TaskMetrics(
                        task_id=decoded_data.get('task_id', ''),
                        task_name=decoded_data.get('task_name', ''),
                        status=decoded_data.get('status', TASK_STATUS['QUEUED']),
                        duration_ms=int(decoded_data.get('duration_ms', 0)) if decoded_data.get('duration_ms') else None,
                        memory_usage_mb=float(decoded_data.get('memory_usage_mb', 0)) if decoded_data.get('memory_usage_mb') else None,
                        cpu_usage_percent=float(decoded_data.get('cpu_usage_percent', 0)) if decoded_data.get('cpu_usage_percent') else None,
                        worker_name=decoded_data.get('worker_name') if decoded_data.get('worker_name') else None
                    )
                    active_tasks.append(metrics)

            return active_tasks

        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []

    def get_task_history(self, limit: int = 100, status_filter: Optional[str] = None) -> List[TaskExecutionHistory]:
        """Get task execution history"""
        try:
            query = self.db_session.query(TaskExecutionHistory)

            if status_filter:
                query = query.filter(TaskExecutionHistory.status == status_filter)

            return query.order_by(TaskExecutionHistory.created_at.desc()).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting task history: {e}")
            return []

    def get_worker_metrics(self) -> List[WorkerMetrics]:
        """Get current worker metrics"""
        try:
            return self.db_session.query(WorkerMetrics).filter(
                WorkerMetrics.is_active == True
            ).all()
        except Exception as e:
            logger.error(f"Error getting worker metrics: {e}")
            return []

    def get_queue_metrics(self) -> List[TaskQueue]:
        """Get queue metrics and health status"""
        try:
            return self.db_session.query(TaskQueue).all()
        except Exception as e:
            logger.error(f"Error getting queue metrics: {e}")
            return []

    def cleanup_old_data(self, retention_days: int = 7):
        """Clean up old task history and metrics"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Clean up old task history
            deleted_tasks = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.created_at < cutoff_date
            ).delete()

            # Reset daily counters for worker metrics
            if datetime.now().hour == 0:  # Reset at midnight
                self.db_session.query(WorkerMetrics).update({
                    'tasks_completed_day': 0,
                    'tasks_failed_day': 0
                })

            self.db_session.commit()

            logger.info(f"Cleaned up {deleted_tasks} old task records")

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            self.db_session.rollback()