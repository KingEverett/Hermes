"""
Dead letter queue service for managing repeatedly failed tasks.

This service provides comprehensive management of tasks that have exhausted
their retry attempts, including analysis, manual retry capabilities, and
debugging support.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from uuid import UUID

import redis
from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from models.job_monitoring import (
    DeadLetterTask, FAILURE_CATEGORY, TaskExecutionHistory, TASK_STATUS
)


logger = logging.getLogger(__name__)


@dataclass
class DeadLetterAnalysis:
    """Analysis result for dead letter tasks"""
    total_tasks: int
    by_category: Dict[str, int]
    by_task_name: Dict[str, int]
    by_failure_reason: Dict[str, int]
    recent_failures: List[str]
    top_failing_tasks: List[Tuple[str, int]]
    recommendations: List[str]


@dataclass
class RetryResult:
    """Result of manual retry operation"""
    success: bool
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_scheduled_at: Optional[datetime] = None


class DeadLetterQueueService:
    """
    Service for managing dead letter queue operations.

    Provides comprehensive management of failed tasks including analysis,
    manual retry capabilities, batch operations, and failure pattern detection.
    """

    def __init__(self, db_session: Session, redis_client: redis.Redis, celery_app: Optional[Celery] = None):
        """
        Initialize the dead letter queue service.

        Args:
            db_session: Database session for accessing dead letter data
            redis_client: Redis client for caching and state management
            celery_app: Optional Celery application instance for task scheduling
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.celery_app = celery_app

        # Cache keys
        self.DLQ_CACHE_KEY = "hermes:dlq:tasks"
        self.DLQ_ANALYSIS_KEY = "hermes:dlq:analysis"
        self.DLQ_RETRY_KEY = "hermes:dlq:retry"

        # Configuration
        self.DEFAULT_PAGE_SIZE = 50
        self.MAX_RETRY_ATTEMPTS = 3
        self.ANALYSIS_CACHE_DURATION = 3600  # 1 hour

    def _ensure_uuid(self, task_id: Union[str, UUID]) -> UUID:
        """Convert string to UUID if needed"""
        if isinstance(task_id, str):
            return UUID(task_id)
        return task_id

    def get_dead_letter_tasks(self, page: int = 1, page_size: int = None,
                             category_filter: Optional[str] = None,
                             task_name_filter: Optional[str] = None,
                             processed_filter: Optional[bool] = None) -> Dict[str, Any]:
        """
        Get paginated list of dead letter tasks with filtering.

        Args:
            page: Page number (1-based)
            page_size: Number of tasks per page
            category_filter: Filter by failure category
            task_name_filter: Filter by task name
            processed_filter: Filter by processed status

        Returns:
            Dict containing tasks, pagination info, and metadata
        """
        try:
            page_size = page_size or self.DEFAULT_PAGE_SIZE
            offset = (page - 1) * page_size

            # Build query with filters
            query = self.db_session.query(DeadLetterTask)

            if category_filter:
                query = query.filter(DeadLetterTask.failure_category == category_filter)

            if task_name_filter:
                query = query.filter(DeadLetterTask.task_name.like(f"%{task_name_filter}%"))

            if processed_filter is not None:
                query = query.filter(DeadLetterTask.processed == processed_filter)

            # Get total count
            total_tasks = query.count()

            # Get paginated results
            tasks = query.order_by(desc(DeadLetterTask.created_at)).offset(offset).limit(page_size).all()

            # Calculate pagination info
            total_pages = (total_tasks + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            return {
                'tasks': [self._serialize_dead_letter_task(task) for task in tasks],
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_tasks': total_tasks,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                },
                'filters': {
                    'category': category_filter,
                    'task_name': task_name_filter,
                    'processed': processed_filter
                }
            }

        except Exception as e:
            logger.error(f"Error getting dead letter tasks: {e}")
            return {
                'tasks': [],
                'pagination': {'page': 1, 'page_size': page_size, 'total_tasks': 0, 'total_pages': 0},
                'error': str(e)
            }

    def get_dead_letter_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dead letter task.

        Args:
            task_id: Dead letter task ID

        Returns:
            Dict containing detailed task information or None if not found
        """
        try:
            task = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.id == task_id
            ).first()

            if not task:
                return None

            # Get related task execution history
            task_history = self.db_session.query(TaskExecutionHistory).filter(
                TaskExecutionHistory.task_id == task.original_task_id
            ).order_by(desc(TaskExecutionHistory.created_at)).all()

            task_data = self._serialize_dead_letter_task(task)
            task_data['execution_history'] = [self._serialize_task_history(h) for h in task_history]

            return task_data

        except Exception as e:
            logger.error(f"Error getting dead letter task {task_id}: {e}")
            return None

    def analyze_dead_letter_queue(self, days_back: int = 7) -> DeadLetterAnalysis:
        """
        Analyze dead letter queue patterns and provide insights.

        Args:
            days_back: Number of days to analyze

        Returns:
            DeadLetterAnalysis: Comprehensive analysis of failed tasks
        """
        try:
            # Check cache first
            cached_analysis = self._get_cached_analysis(days_back)
            if cached_analysis:
                return cached_analysis

            # Calculate date range
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Get tasks within timeframe
            tasks = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at >= cutoff_date
            ).all()

            total_tasks = len(tasks)

            # Analyze by category
            by_category = {}
            for category_key, category_value in FAILURE_CATEGORY.items():
                count = len([t for t in tasks if t.failure_category == category_value])
                if count > 0:
                    by_category[category_value] = count

            # Analyze by task name
            by_task_name = {}
            for task in tasks:
                by_task_name[task.task_name] = by_task_name.get(task.task_name, 0) + 1

            # Analyze by failure reason
            by_failure_reason = {}
            for task in tasks:
                # Extract main error type from failure reason
                reason_key = self._extract_error_type(task.failure_reason)
                by_failure_reason[reason_key] = by_failure_reason.get(reason_key, 0) + 1

            # Get recent failures (last 24 hours)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_failures = [
                f"{task.task_name}: {self._extract_error_type(task.failure_reason)}"
                for task in tasks
                if task.created_at >= recent_cutoff
            ]

            # Top failing tasks
            top_failing_tasks = sorted(by_task_name.items(), key=lambda x: x[1], reverse=True)[:10]

            # Generate recommendations
            recommendations = self._generate_recommendations(
                total_tasks, by_category, by_task_name, by_failure_reason
            )

            analysis = DeadLetterAnalysis(
                total_tasks=total_tasks,
                by_category=by_category,
                by_task_name=by_task_name,
                by_failure_reason=by_failure_reason,
                recent_failures=recent_failures[-20:],  # Last 20 recent failures
                top_failing_tasks=top_failing_tasks,
                recommendations=recommendations
            )

            # Cache the analysis
            self._cache_analysis(days_back, analysis)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing dead letter queue: {e}")
            return DeadLetterAnalysis(
                total_tasks=0, by_category={}, by_task_name={}, by_failure_reason={},
                recent_failures=[], top_failing_tasks=[], recommendations=[]
            )

    def retry_dead_letter_task(self, task_id: str, user_id: str = None) -> RetryResult:
        """
        Manually retry a dead letter task.

        Args:
            task_id: Dead letter task ID
            user_id: ID of user performing the retry

        Returns:
            RetryResult: Result of retry operation
        """
        try:
            # Convert string ID to UUID if needed
            task_uuid = self._ensure_uuid(task_id)

            # Get the dead letter task
            dlq_task = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.id == task_uuid
            ).first()

            if not dlq_task:
                return RetryResult(success=False, error_message="Dead letter task not found")

            if dlq_task.retry_scheduled:
                return RetryResult(
                    success=False,
                    error_message="Task retry is already scheduled"
                )

            # Check retry attempts limit
            if dlq_task.retry_attempts >= self.MAX_RETRY_ATTEMPTS:
                return RetryResult(
                    success=False,
                    error_message=f"Maximum retry attempts ({self.MAX_RETRY_ATTEMPTS}) exceeded"
                )

            # Schedule the retry
            if not self.celery_app:
                return RetryResult(success=False, error_message="Celery app not available")

            # Send task to Celery
            result = self.celery_app.send_task(
                dlq_task.task_name,
                args=dlq_task.task_args,
                kwargs=dlq_task.task_kwargs
            )

            # Update dead letter task
            dlq_task.retry_scheduled = True
            dlq_task.retry_scheduled_at = datetime.now()
            dlq_task.retry_attempts += 1
            dlq_task.processed_by = user_id
            dlq_task.updated_at = datetime.now()

            self.db_session.commit()

            # Cache retry information
            self._cache_retry_info(task_id, result.id, datetime.now())

            logger.info(f"Scheduled retry for dead letter task {task_id} with new task ID {result.id}")

            return RetryResult(
                success=True,
                task_id=result.id,
                retry_scheduled_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error retrying dead letter task {task_id}: {e}")
            self.db_session.rollback()
            return RetryResult(success=False, error_message=str(e))

    def bulk_retry_tasks(self, category: Optional[str] = None, task_name: Optional[str] = None,
                        limit: int = 10, user_id: str = None) -> Dict[str, Any]:
        """
        Retry multiple dead letter tasks in bulk.

        Args:
            category: Filter by failure category
            task_name: Filter by task name
            limit: Maximum number of tasks to retry
            user_id: ID of user performing the bulk retry

        Returns:
            Dict containing bulk retry results
        """
        try:
            # Build query
            query = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.retry_scheduled == False,
                DeadLetterTask.retry_attempts < self.MAX_RETRY_ATTEMPTS
            )

            if category:
                query = query.filter(DeadLetterTask.failure_category == category)

            if task_name:
                query = query.filter(DeadLetterTask.task_name == task_name)

            # Get tasks to retry
            tasks_to_retry = query.order_by(DeadLetterTask.created_at).limit(limit).all()

            results = {
                'total_attempted': len(tasks_to_retry),
                'successful': 0,
                'failed': 0,
                'results': []
            }

            for task in tasks_to_retry:
                retry_result = self.retry_dead_letter_task(str(task.id), user_id)

                result_entry = {
                    'dlq_task_id': str(task.id),
                    'task_name': task.task_name,
                    'success': retry_result.success,
                    'new_task_id': retry_result.task_id,
                    'error': retry_result.error_message
                }

                if retry_result.success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1

                results['results'].append(result_entry)

            logger.info(f"Bulk retry completed: {results['successful']}/{results['total_attempted']} successful")
            return results

        except Exception as e:
            logger.error(f"Error in bulk retry: {e}")
            return {
                'total_attempted': 0,
                'successful': 0,
                'failed': 0,
                'error': str(e),
                'results': []
            }

    def mark_task_processed(self, task_id: Union[str, UUID], user_id: str = None, notes: str = None) -> bool:
        """
        Mark a dead letter task as processed (resolved).

        Args:
            task_id: Dead letter task ID (string or UUID)
            user_id: ID of user marking as processed
            notes: Optional processing notes

        Returns:
            bool: True if successfully marked as processed
        """
        try:
            # Convert string ID to UUID if needed
            task_uuid = self._ensure_uuid(task_id)

            dlq_task = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.id == task_uuid
            ).first()

            if not dlq_task:
                return False

            dlq_task.processed = True
            dlq_task.processed_at = datetime.now()
            dlq_task.processed_by = user_id
            dlq_task.processing_notes = notes
            dlq_task.updated_at = datetime.now()

            self.db_session.commit()

            logger.info(f"Marked dead letter task {task_id} as processed by {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error marking task {task_id} as processed: {e}")
            self.db_session.rollback()
            return False

    def purge_old_tasks(self, days_old: int = 30, keep_unprocessed: bool = True) -> int:
        """
        Purge old dead letter tasks to manage storage.

        Args:
            days_old: Age threshold for purging
            keep_unprocessed: Whether to keep unprocessed tasks regardless of age

        Returns:
            int: Number of tasks purged
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)

            query = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at < cutoff_date
            )

            if keep_unprocessed:
                query = query.filter(DeadLetterTask.processed == True)

            tasks_to_delete = query.all()
            count = len(tasks_to_delete)

            for task in tasks_to_delete:
                self.db_session.delete(task)

            self.db_session.commit()

            logger.info(f"Purged {count} old dead letter tasks")
            return count

        except Exception as e:
            logger.error(f"Error purging old dead letter tasks: {e}")
            self.db_session.rollback()
            return 0

    def get_failure_statistics(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive failure statistics for monitoring.

        Args:
            days_back: Number of days to analyze

        Returns:
            Dict containing failure statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Total dead letter tasks
            total_dlq = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at >= cutoff_date
            ).count()

            # Processed vs unprocessed
            processed_dlq = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at >= cutoff_date,
                DeadLetterTask.processed == True
            ).count()

            unprocessed_dlq = total_dlq - processed_dlq

            # Retry statistics
            retried_dlq = self.db_session.query(DeadLetterTask).filter(
                DeadLetterTask.created_at >= cutoff_date,
                DeadLetterTask.retry_attempts > 0
            ).count()

            # Category breakdown
            category_stats = {}
            for category_key, category_value in FAILURE_CATEGORY.items():
                count = self.db_session.query(DeadLetterTask).filter(
                    DeadLetterTask.created_at >= cutoff_date,
                    DeadLetterTask.failure_category == category_value
                ).count()
                if count > 0:
                    category_stats[category_value] = count

            # Resolution rate
            resolution_rate = (processed_dlq / total_dlq * 100) if total_dlq > 0 else 0

            return {
                'timeframe_days': days_back,
                'total_dead_letter_tasks': total_dlq,
                'processed_tasks': processed_dlq,
                'unprocessed_tasks': unprocessed_dlq,
                'retried_tasks': retried_dlq,
                'resolution_rate_percent': round(resolution_rate, 2),
                'category_breakdown': category_stats,
                'trends': self._calculate_failure_trends(cutoff_date)
            }

        except Exception as e:
            logger.error(f"Error getting failure statistics: {e}")
            return {}

    def _serialize_dead_letter_task(self, task: DeadLetterTask) -> Dict[str, Any]:
        """Serialize dead letter task to dictionary"""
        return {
            'id': str(task.id),
            'original_task_id': task.original_task_id,
            'task_name': task.task_name,
            'task_args': task.task_args,
            'task_kwargs': task.task_kwargs,
            'failure_reason': task.failure_reason,
            'failure_category': task.failure_category,
            'failure_traceback': task.failure_traceback,
            'first_failed_at': task.first_failed_at.isoformat() if task.first_failed_at else None,
            'last_failed_at': task.last_failed_at.isoformat() if task.last_failed_at else None,
            'total_attempts': task.total_attempts,
            'processed': task.processed,
            'processed_at': task.processed_at.isoformat() if task.processed_at else None,
            'processed_by': task.processed_by,
            'processing_notes': task.processing_notes,
            'retry_scheduled': task.retry_scheduled,
            'retry_scheduled_at': task.retry_scheduled_at.isoformat() if task.retry_scheduled_at else None,
            'retry_attempts': task.retry_attempts,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
        }

    def _serialize_task_history(self, history: TaskExecutionHistory) -> Dict[str, Any]:
        """Serialize task execution history to dictionary"""
        return {
            'id': str(history.id),
            'task_id': history.task_id,
            'task_name': history.task_name,
            'status': history.status,
            'queued_at': history.queued_at.isoformat() if history.queued_at else None,
            'started_at': history.started_at.isoformat() if history.started_at else None,
            'completed_at': history.completed_at.isoformat() if history.completed_at else None,
            'duration_ms': history.duration_ms,
            'worker_name': history.worker_name,
            'retry_count': history.retry_count,
            'error_message': history.error_message,
            'created_at': history.created_at.isoformat()
        }

    def _extract_error_type(self, failure_reason: str) -> str:
        """Extract the main error type from failure reason"""
        if not failure_reason:
            return "Unknown"

        # Common patterns to extract error types
        if ":" in failure_reason:
            return failure_reason.split(":")[0].strip()
        elif "Exception" in failure_reason:
            parts = failure_reason.split()
            for part in parts:
                if "Exception" in part:
                    return part

        # Return first 50 characters as fallback
        return failure_reason[:50] + "..." if len(failure_reason) > 50 else failure_reason

    def _generate_recommendations(self, total_tasks: int, by_category: Dict,
                                by_task_name: Dict, by_failure_reason: Dict) -> List[str]:
        """Generate actionable recommendations based on failure analysis"""
        recommendations = []

        if total_tasks == 0:
            return ["No failed tasks found in the analyzed period."]

        # High failure rate
        if total_tasks > 10:
            recommendations.append(f"High number of failed tasks ({total_tasks}). Consider reviewing task reliability.")

        # Category-specific recommendations
        if by_category.get(FAILURE_CATEGORY['TIMEOUT'], 0) > total_tasks * 0.3:
            recommendations.append("High timeout failures detected. Consider increasing task timeouts or optimizing performance.")

        if by_category.get(FAILURE_CATEGORY['CONNECTION'], 0) > total_tasks * 0.2:
            recommendations.append("High connection failures detected. Review network connectivity and service availability.")

        if by_category.get(FAILURE_CATEGORY['MEMORY'], 0) > 0:
            recommendations.append("Memory errors detected. Consider optimizing memory usage or increasing worker memory limits.")

        if by_category.get(FAILURE_CATEGORY['RATE_LIMIT'], 0) > 0:
            recommendations.append("Rate limiting errors detected. Review API usage patterns and implement proper rate limiting.")

        # Task-specific recommendations
        top_failing_task = max(by_task_name.items(), key=lambda x: x[1]) if by_task_name else None
        if top_failing_task and top_failing_task[1] > total_tasks * 0.4:
            recommendations.append(f"Task '{top_failing_task[0]}' has high failure rate. Focus debugging efforts here.")

        if len(recommendations) == 0:
            recommendations.append("Failure patterns look normal. Continue monitoring for trends.")

        return recommendations

    def _cache_analysis(self, days_back: int, analysis: DeadLetterAnalysis):
        """Cache analysis results"""
        try:
            cache_key = f"{self.DLQ_ANALYSIS_KEY}:{days_back}"
            cache_data = {
                'total_tasks': analysis.total_tasks,
                'by_category': json.dumps(analysis.by_category),
                'by_task_name': json.dumps(analysis.by_task_name),
                'by_failure_reason': json.dumps(analysis.by_failure_reason),
                'recent_failures': json.dumps(analysis.recent_failures),
                'top_failing_tasks': json.dumps(analysis.top_failing_tasks),
                'recommendations': json.dumps(analysis.recommendations),
                'timestamp': time.time()
            }

            self.redis_client.hset(cache_key, mapping=cache_data)
            self.redis_client.expire(cache_key, self.ANALYSIS_CACHE_DURATION)

        except Exception as e:
            logger.error(f"Error caching analysis: {e}")

    def _get_cached_analysis(self, days_back: int) -> Optional[DeadLetterAnalysis]:
        """Get cached analysis results"""
        try:
            cache_key = f"{self.DLQ_ANALYSIS_KEY}:{days_back}"
            cached_data = self.redis_client.hgetall(cache_key)

            if not cached_data:
                return None

            return DeadLetterAnalysis(
                total_tasks=int(cached_data.get('total_tasks', 0)),
                by_category=json.loads(cached_data.get('by_category', '{}')),
                by_task_name=json.loads(cached_data.get('by_task_name', '{}')),
                by_failure_reason=json.loads(cached_data.get('by_failure_reason', '{}')),
                recent_failures=json.loads(cached_data.get('recent_failures', '[]')),
                top_failing_tasks=json.loads(cached_data.get('top_failing_tasks', '[]')),
                recommendations=json.loads(cached_data.get('recommendations', '[]'))
            )

        except Exception as e:
            logger.error(f"Error loading cached analysis: {e}")
            return None

    def _cache_retry_info(self, dlq_task_id: str, new_task_id: str, scheduled_at: datetime):
        """Cache retry information"""
        try:
            retry_data = {
                'dlq_task_id': dlq_task_id,
                'new_task_id': new_task_id,
                'scheduled_at': scheduled_at.isoformat(),
                'timestamp': time.time()
            }

            self.redis_client.hset(f"{self.DLQ_RETRY_KEY}:{dlq_task_id}", mapping=retry_data)
            self.redis_client.expire(f"{self.DLQ_RETRY_KEY}:{dlq_task_id}", 86400)  # 24 hours

        except Exception as e:
            logger.error(f"Error caching retry info: {e}")

    def _calculate_failure_trends(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate failure trends over time"""
        try:
            # Get daily failure counts for the period
            daily_failures = {}
            current_date = cutoff_date.date()
            today = datetime.now().date()

            while current_date <= today:
                start_of_day = datetime.combine(current_date, datetime.min.time())
                end_of_day = datetime.combine(current_date, datetime.max.time())

                count = self.db_session.query(DeadLetterTask).filter(
                    and_(
                        DeadLetterTask.created_at >= start_of_day,
                        DeadLetterTask.created_at <= end_of_day
                    )
                ).count()

                daily_failures[current_date.isoformat()] = count
                current_date += timedelta(days=1)

            # Calculate trend direction
            values = list(daily_failures.values())
            if len(values) >= 2:
                recent_avg = sum(values[-3:]) / min(3, len(values))
                older_avg = sum(values[:-3]) / max(1, len(values) - 3) if len(values) > 3 else recent_avg
                trend = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
            else:
                trend = "insufficient_data"

            return {
                'daily_failures': daily_failures,
                'trend_direction': trend,
                'total_period_failures': sum(values),
                'average_daily_failures': sum(values) / len(values) if values else 0
            }

        except Exception as e:
            logger.error(f"Error calculating failure trends: {e}")
            return {}