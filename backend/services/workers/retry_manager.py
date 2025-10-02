"""
Retry manager service for intelligent task retry handling.

This service provides configurable retry policies with exponential backoff,
intelligent failure categorization, and dead letter queue management.
"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

import redis
from celery import Celery
from celery.exceptions import Retry
from sqlalchemy.orm import Session

from models.job_monitoring import (
    TaskExecutionHistory, DeadLetterTask, TASK_STATUS, FAILURE_CATEGORY
)


logger = logging.getLogger(__name__)


# Retry policy map - replaces RetryPolicy enum per coding standards
RETRY_POLICY = {
    'EXPONENTIAL': 'exponential',
    'LINEAR': 'linear',
    'FIXED': 'fixed',
    'FIBONACCI': 'fibonacci'
}


@dataclass
class RetryConfiguration:
    """Configuration for task retry behavior"""
    max_retries: int = 3
    base_delay: int = 2  # seconds
    max_delay: int = 300  # seconds
    policy: str = RETRY_POLICY['EXPONENTIAL']
    jitter: bool = True
    jitter_range: tuple = (0.1, 0.3)  # percentage of delay
    backoff_multiplier: float = 2.0
    retry_on_exceptions: List[str] = None
    no_retry_on_exceptions: List[str] = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    delay_seconds: int
    scheduled_at: datetime
    reason: str
    exception_type: str
    exception_message: str


class RetryManagerService:
    """
    Service for managing task retry logic with exponential backoff.

    Provides intelligent retry handling with configurable policies,
    failure analysis, and automatic dead letter queue management.
    """

    def __init__(self, db_session: Session, redis_client: redis.Redis, celery_app: Optional[Celery] = None):
        """
        Initialize the retry manager service.

        Args:
            db_session: Database session for persisting retry data
            redis_client: Redis client for retry state management
            celery_app: Optional Celery application instance
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.celery_app = celery_app

        # Default retry configurations by task type
        self.default_configs: Dict[str, RetryConfiguration] = {
            'default': RetryConfiguration(),
            'nvd_research_task': RetryConfiguration(
                max_retries=3,
                base_delay=6,  # Respect NVD rate limits
                max_delay=300,
                retry_on_exceptions=['requests.exceptions.Timeout', 'requests.exceptions.ConnectionError']
            ),
            'documentation_generation': RetryConfiguration(
                max_retries=2,
                base_delay=2,
                max_delay=60,
                no_retry_on_exceptions=['MemoryError', 'ValidationError']
            ),
            'version_analysis': RetryConfiguration(
                max_retries=5,
                base_delay=1,
                max_delay=30,
                retry_on_exceptions=['requests.exceptions.RequestException']
            ),
            'scan_import': RetryConfiguration(
                max_retries=2,
                base_delay=5,
                max_delay=120,
                no_retry_on_exceptions=['xml.etree.ElementTree.ParseError', 'ValidationError']
            ),
            'api_request': RetryConfiguration(
                max_retries=4,
                base_delay=3,
                max_delay=180,
                retry_on_exceptions=['requests.exceptions.Timeout', 'ConnectionError']
            )
        }

        # Cache keys
        self.RETRY_CACHE_KEY = "hermes:retry:attempts"
        self.RETRY_CONFIG_KEY = "hermes:retry:config"

    def configure_task_retry(self, task_name: str, config: RetryConfiguration):
        """
        Configure retry policy for a specific task type.

        Args:
            task_name: Name of the task type
            config: Retry configuration
        """
        self.default_configs[task_name] = config

        # Cache configuration in Redis
        try:
            config_data = asdict(config)
            config_data['policy'] = config.policy  # Policy is already a string
            self.redis_client.hset(
                f"{self.RETRY_CONFIG_KEY}:{task_name}",
                mapping=config_data
            )
            self.redis_client.expire(f"{self.RETRY_CONFIG_KEY}:{task_name}", 86400)  # 24 hours

            logger.info(f"Configured retry policy for {task_name}: {config}")

        except Exception as e:
            logger.error(f"Error caching retry configuration: {e}")

    def get_retry_configuration(self, task_name: str) -> RetryConfiguration:
        """
        Get retry configuration for a task type.

        Args:
            task_name: Name of the task type

        Returns:
            RetryConfiguration: Retry configuration for the task
        """
        # Try to get from cache first
        try:
            cached_config = self.redis_client.hgetall(f"{self.RETRY_CONFIG_KEY}:{task_name}")
            if cached_config:
                # Convert back from strings
                config_dict = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
                             for k, v in cached_config.items()}

                # Convert numeric values
                for key in ['max_retries', 'base_delay', 'max_delay']:
                    if key in config_dict:
                        config_dict[key] = int(config_dict[key])

                if 'backoff_multiplier' in config_dict:
                    config_dict['backoff_multiplier'] = float(config_dict['backoff_multiplier'])

                if 'jitter' in config_dict:
                    config_dict['jitter'] = config_dict['jitter'].lower() == 'true'

                # policy is already a string, no conversion needed

                return RetryConfiguration(**config_dict)

        except Exception as e:
            logger.error(f"Error loading cached retry configuration: {e}")

        # Fall back to default configurations
        return self.default_configs.get(task_name, self.default_configs['default'])

    def calculate_retry_delay(self, attempt: int, config: RetryConfiguration) -> int:
        """
        Calculate retry delay based on the retry policy.

        Args:
            attempt: Current retry attempt number (starting from 1)
            config: Retry configuration

        Returns:
            int: Delay in seconds
        """
        if config.policy == RETRY_POLICY['EXPONENTIAL']:
            delay = min(config.base_delay * (config.backoff_multiplier ** (attempt - 1)), config.max_delay)
        elif config.policy == RETRY_POLICY['LINEAR']:
            delay = min(config.base_delay * attempt, config.max_delay)
        elif config.policy == RETRY_POLICY['FIXED']:
            delay = config.base_delay
        elif config.policy == RETRY_POLICY['FIBONACCI']:
            # Fibonacci sequence for delay calculation
            if attempt <= 2:
                delay = config.base_delay
            else:
                # Calculate Fibonacci number for attempt
                a, b = 1, 1
                for _ in range(attempt - 2):
                    a, b = b, a + b
                delay = min(config.base_delay * b, config.max_delay)
        else:
            delay = config.base_delay

        # Add jitter if enabled
        if config.jitter:
            jitter_min, jitter_max = config.jitter_range
            jitter_amount = delay * random.uniform(jitter_min, jitter_max)
            delay += jitter_amount

        return int(delay)

    def should_retry_task(self, task_id: str, task_name: str, exception: Exception, attempt: int) -> bool:
        """
        Determine if a task should be retried based on configuration and failure analysis.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task type
            exception: Exception that caused the failure
            attempt: Current attempt number

        Returns:
            bool: True if task should be retried
        """
        config = self.get_retry_configuration(task_name)

        # Check if we've exceeded max retries
        if attempt >= config.max_retries:
            logger.info(f"Task {task_id} exceeded max retries ({config.max_retries})")
            return False

        exception_type = type(exception).__name__
        exception_module = type(exception).__module__
        full_exception_name = f"{exception_module}.{exception_type}"
        exception_message = str(exception)

        # Check if exception is explicitly excluded from retries
        if config.no_retry_on_exceptions:
            for no_retry_exc in config.no_retry_on_exceptions:
                # Match by type name, full name, or message content
                if (no_retry_exc in [exception_type, full_exception_name] or
                    no_retry_exc in exception_message):
                    logger.info(f"Task {task_id} failed with non-retryable exception: {exception_type}")
                    return False

        # Check if exception is explicitly included for retries
        if config.retry_on_exceptions:
            for retry_exc in config.retry_on_exceptions:
                # Match by type name, full name, or message content
                if (retry_exc in [exception_type, full_exception_name] or
                    retry_exc in exception_message):
                    return True

            # If we have a whitelist and exception is not in it, don't retry
            logger.info(f"Task {task_id} failed with exception not in retry whitelist: {exception_type}")
            return False

        # Default: retry for most exceptions except critical ones
        non_retryable_exceptions = [
            'KeyboardInterrupt',
            'SystemExit',
            'MemoryError',
            'SyntaxError',
            'ImportError',
            'AttributeError',
            'TypeError',
            'ValueError'  # Only for validation errors
        ]

        if exception_type in non_retryable_exceptions:
            logger.info(f"Task {task_id} failed with non-retryable system exception: {exception_type}")
            return False

        return True

    def schedule_retry(self, task_id: str, task_name: str, exception: Exception,
                      attempt: int, task_args: List = None, task_kwargs: Dict = None) -> Optional[RetryAttempt]:
        """
        Schedule a task retry with appropriate delay.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task type
            exception: Exception that caused the failure
            attempt: Current attempt number
            task_args: Original task arguments
            task_kwargs: Original task keyword arguments

        Returns:
            Optional[RetryAttempt]: Retry attempt information if scheduled
        """
        if not self.should_retry_task(task_id, task_name, exception, attempt):
            return None

        config = self.get_retry_configuration(task_name)
        delay = self.calculate_retry_delay(attempt, config)
        scheduled_at = datetime.now() + timedelta(seconds=delay)

        retry_attempt = RetryAttempt(
            attempt_number=attempt,
            delay_seconds=delay,
            scheduled_at=scheduled_at,
            reason=f"Retry after {type(exception).__name__}",
            exception_type=type(exception).__name__,
            exception_message=str(exception)
        )

        try:
            # Cache retry information
            self._cache_retry_attempt(task_id, retry_attempt)

            # Update task history
            self._update_task_retry_info(task_id, retry_attempt, exception)

            # Schedule the actual retry if Celery app is available
            if self.celery_app and hasattr(self.celery_app, 'send_task'):
                self.celery_app.send_task(
                    task_name,
                    args=task_args or [],
                    kwargs=task_kwargs or {},
                    countdown=delay,
                    retry=True
                )

            logger.info(f"Scheduled retry for task {task_id} in {delay} seconds (attempt {attempt})")
            return retry_attempt

        except Exception as e:
            logger.error(f"Error scheduling retry for task {task_id}: {e}")
            return None

    def analyze_failure_category(self, exception: Exception, task_context: Dict = None) -> str:
        """
        Analyze the failure and categorize it for better handling.

        Args:
            exception: Exception that caused the failure
            task_context: Additional context about the task

        Returns:
            FailureCategory: Categorized failure type
        """
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()

        # Timeout-related failures
        if 'timeout' in exception_message or exception_type in ['TimeoutError', 'RequestTimeout']:
            return FAILURE_CATEGORY['TIMEOUT']

        # Memory-related failures
        if exception_type in ['MemoryError'] or 'memory' in exception_message:
            return FAILURE_CATEGORY['MEMORY']

        # Connection-related failures
        if exception_type in ['ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError']:
            return FAILURE_CATEGORY['CONNECTION']
        if 'connection' in exception_message or 'network' in exception_message:
            return FAILURE_CATEGORY['CONNECTION']

        # Rate limiting failures
        if 'rate limit' in exception_message or 'too many requests' in exception_message:
            return FAILURE_CATEGORY['RATE_LIMIT']
        if exception_type in ['RateLimitExceeded']:
            return FAILURE_CATEGORY['RATE_LIMIT']

        # Validation failures
        if exception_type in ['ValidationError', 'ValueError', 'KeyError']:
            return FAILURE_CATEGORY['VALIDATION']

        # Resource failures
        if 'resource' in exception_message or 'quota' in exception_message:
            return FAILURE_CATEGORY['RESOURCE']

        # Default to generic exception
        return FAILURE_CATEGORY['EXCEPTION']

    def move_to_dead_letter_queue(self, task_id: str, task_name: str, failure_reason: str,
                                 task_args: List = None, task_kwargs: Dict = None,
                                 total_attempts: int = 0) -> bool:
        """
        Move a repeatedly failed task to the dead letter queue.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task type
            failure_reason: Reason for final failure
            task_args: Original task arguments
            task_kwargs: Original task keyword arguments
            total_attempts: Total number of attempts made

        Returns:
            bool: True if successfully moved to dead letter queue
        """
        try:
            # Categorize the failure
            failure_category = FAILURE_CATEGORY['UNKNOWN']
            try:
                # Try to extract exception from failure reason
                if 'Exception:' in failure_reason:
                    exception_class = failure_reason.split('Exception:')[0].strip()
                    failure_category = self._categorize_by_exception_name(exception_class)
            except Exception:
                pass

            # Create dead letter task record
            dead_letter_task = DeadLetterTask(
                original_task_id=task_id,
                task_name=task_name,
                task_args=task_args or [],
                task_kwargs=task_kwargs or {},
                failure_reason=failure_reason,
                failure_category=failure_category,
                first_failed_at=datetime.now(),
                last_failed_at=datetime.now(),
                total_attempts=total_attempts
            )

            self.db_session.add(dead_letter_task)

            # Update original task status
            task_history = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task_id
            ).first()

            if task_history:
                task_history.status = TASK_STATUS['DEAD_LETTER']
                task_history.updated_at = datetime.now()

            self.db_session.commit()

            # Remove retry information from cache
            self._remove_retry_cache(task_id)

            logger.info(f"Moved task {task_id} to dead letter queue after {total_attempts} attempts")
            return True

        except Exception as e:
            logger.error(f"Error moving task {task_id} to dead letter queue: {e}")
            self.db_session.rollback()
            return False

    def get_retry_statistics(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """
        Get retry statistics for monitoring and analysis.

        Args:
            timeframe_hours: Time window for statistics

        Returns:
            Dict: Retry statistics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=timeframe_hours)

            # Get task statistics
            total_tasks = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.created_at >= cutoff_time
            ).count()

            failed_tasks = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.created_at >= cutoff_time,
                TaskExecutionHistory.status.in_([TASK_STATUS['FAILED'], TASK_STATUS['DEAD_LETTER']])
            ).count()

            retried_tasks = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.created_at >= cutoff_time,
                TaskExecutionHistory.retry_count > 0,
                TaskExecutionHistory.status != TASK_STATUS['DEAD_LETTER']
            ).count()

            dead_letter_tasks = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at >= cutoff_time
            ).count()

            # Calculate rates
            failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            retry_rate = (retried_tasks / total_tasks * 100) if total_tasks > 0 else 0
            dead_letter_rate = (dead_letter_tasks / total_tasks * 100) if total_tasks > 0 else 0

            return {
                'timeframe_hours': timeframe_hours,
                'total_tasks': total_tasks,
                'failed_tasks': failed_tasks,
                'retried_tasks': retried_tasks,
                'dead_letter_tasks': dead_letter_tasks,
                'failure_rate_percent': round(failure_rate, 2),
                'retry_rate_percent': round(retry_rate, 2),
                'dead_letter_rate_percent': round(dead_letter_rate, 2),
                'success_rate_percent': round(100 - failure_rate, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating retry statistics: {e}")
            return {}

    def _cache_retry_attempt(self, task_id: str, retry_attempt: RetryAttempt):
        """Cache retry attempt information in Redis"""
        try:
            retry_data = {
                'attempt_number': retry_attempt.attempt_number,
                'delay_seconds': retry_attempt.delay_seconds,
                'scheduled_at': retry_attempt.scheduled_at.isoformat(),
                'reason': retry_attempt.reason,
                'exception_type': retry_attempt.exception_type,
                'exception_message': retry_attempt.exception_message,
                'timestamp': time.time()
            }

            self.redis_client.hset(f"{self.RETRY_CACHE_KEY}:{task_id}", mapping=retry_data)
            self.redis_client.expire(f"{self.RETRY_CACHE_KEY}:{task_id}", 86400)  # 24 hours

        except Exception as e:
            logger.error(f"Error caching retry attempt: {e}")

    def _remove_retry_cache(self, task_id: str):
        """Remove retry cache for a task"""
        try:
            self.redis_client.delete(f"{self.RETRY_CACHE_KEY}:{task_id}")
        except Exception as e:
            logger.error(f"Error removing retry cache: {e}")

    def _update_task_retry_info(self, task_id: str, retry_attempt: RetryAttempt, exception: Exception):
        """Update task history with retry information"""
        try:
            task_history = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task_id
            ).first()

            if task_history:
                task_history.status = TASK_STATUS['RETRYING']
                task_history.retry_count = retry_attempt.attempt_number
                task_history.error_message = retry_attempt.exception_message
                task_history.updated_at = datetime.now()

                self.db_session.commit()

        except Exception as e:
            logger.error(f"Error updating task retry info: {e}")
            self.db_session.rollback()

    def _categorize_by_exception_name(self, exception_name: str) -> str:
        """Categorize failure by exception class name"""
        exception_name = exception_name.lower()

        if 'timeout' in exception_name:
            return FAILURE_CATEGORY['TIMEOUT']
        elif 'memory' in exception_name:
            return FAILURE_CATEGORY['MEMORY']
        elif 'connection' in exception_name:
            return FAILURE_CATEGORY['CONNECTION']
        elif 'ratelimit' in exception_name or 'rate_limit' in exception_name:
            return FAILURE_CATEGORY['RATE_LIMIT']
        elif 'validation' in exception_name or 'value' in exception_name:
            return FAILURE_CATEGORY['VALIDATION']
        elif 'resource' in exception_name:
            return FAILURE_CATEGORY['RESOURCE']
        else:
            return FAILURE_CATEGORY['EXCEPTION']