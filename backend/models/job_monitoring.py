"""
Data models for background job monitoring and management.

This module contains SQLAlchemy models for tracking task execution history,
managing failed tasks in a dead letter queue, and handling task-related alerts.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base


# Task status map - replaces TaskStatus enum per coding standards
TASK_STATUS = {
    'QUEUED': 'queued',
    'PROCESSING': 'processing',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'RETRYING': 'retrying',
    'DEAD_LETTER': 'dead_letter'
}

# Failure category map - replaces FailureCategory enum per coding standards
FAILURE_CATEGORY = {
    'TIMEOUT': 'timeout',
    'EXCEPTION': 'exception',
    'MEMORY': 'memory',
    'CONNECTION': 'connection',
    'RATE_LIMIT': 'rate_limit',
    'VALIDATION': 'validation',
    'RESOURCE': 'resource',
    'UNKNOWN': 'unknown'
}

# Alert type map - replaces AlertType enum per coding standards
ALERT_TYPE = {
    'HIGH_FAILURE_RATE': 'high_failure_rate',
    'QUEUE_BACKUP': 'queue_backup',
    'DEAD_LETTER_THRESHOLD': 'dead_letter_threshold',
    'WORKER_DOWN': 'worker_down',
    'MEMORY_HIGH': 'memory_high',
    'PROCESSING_SLOW': 'processing_slow'
}


class TaskExecutionHistory(Base):
    """
    Model for tracking task execution history and performance metrics.

    Stores comprehensive information about each task execution including
    performance metrics, worker information, and execution details.
    """
    __tablename__ = "task_execution_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), nullable=False, index=True)
    task_name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default=TASK_STATUS['QUEUED'])

    # Timing information
    queued_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Performance metrics
    memory_usage_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)

    # Worker and execution context
    worker_name = Column(String(255), nullable=True)
    queue_name = Column(String(255), nullable=False, default="default")
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Task data (for debugging and reprocessing)
    task_args = Column(JSON, nullable=True)
    task_kwargs = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<TaskExecutionHistory(id={self.id}, task_name='{self.task_name}', status='{self.status}')>"


class DeadLetterTask(Base):
    """
    Model for managing tasks that have exhausted their retry attempts.

    Provides persistent storage for failed tasks with comprehensive failure
    analysis and manual retry capabilities.
    """
    __tablename__ = "dead_letter_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_task_id = Column(String(255), nullable=False, index=True)
    task_name = Column(String(255), nullable=False, index=True)

    # Task preservation data
    task_args = Column(JSON, nullable=False, default=list)
    task_kwargs = Column(JSON, nullable=False, default=dict)

    # Failure analysis
    failure_reason = Column(Text, nullable=False)
    failure_category = Column(String(50), nullable=False, default=FAILURE_CATEGORY['UNKNOWN'])
    failure_traceback = Column(Text, nullable=True)

    # Timing information
    first_failed_at = Column(DateTime, nullable=False)
    last_failed_at = Column(DateTime, nullable=False)
    total_attempts = Column(Integer, nullable=False, default=0)

    # Processing status
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(255), nullable=True)
    processing_notes = Column(Text, nullable=True)

    # Retry management
    retry_scheduled = Column(Boolean, nullable=False, default=False)
    retry_scheduled_at = Column(DateTime, nullable=True)
    retry_attempts = Column(Integer, nullable=False, default=0)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<DeadLetterTask(id={self.id}, task_name='{self.task_name}', category='{self.failure_category}')>"


class TaskAlert(Base):
    """
    Model for managing task-related alerts and notifications.

    Tracks alert conditions, thresholds, and escalation status for
    proactive monitoring of task execution health.
    """
    __tablename__ = "task_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False)

    # Alert configuration
    threshold_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    alert_condition = Column(String(255), nullable=False)  # e.g., "failure_rate > threshold"

    # Scope
    task_name = Column(String(255), nullable=True, index=True)  # Null for global alerts
    queue_name = Column(String(255), nullable=True, index=True)
    worker_name = Column(String(255), nullable=True, index=True)

    # Alert lifecycle
    triggered_at = Column(DateTime, nullable=False, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)
    auto_resolved = Column(Boolean, nullable=False, default=False)

    # Notification management
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_sent_at = Column(DateTime, nullable=True)
    notification_channels = Column(JSON, nullable=True, default=list)

    # Escalation
    escalation_level = Column(Integer, nullable=False, default=1)
    escalated_at = Column(DateTime, nullable=True)
    max_escalation_level = Column(Integer, nullable=False, default=3)

    # Alert data
    alert_data = Column(JSON, nullable=True, default=dict)
    resolution_data = Column(JSON, nullable=True, default=dict)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<TaskAlert(id={self.id}, type='{self.alert_type}', resolved={'Yes' if self.resolved_at else 'No'})>"


class TaskQueue(Base):
    """
    Model for tracking task queue metrics and health.

    Monitors queue depth, processing rates, and worker availability
    for operational visibility.
    """
    __tablename__ = "task_queues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_name = Column(String(255), nullable=False, unique=True, index=True)

    # Queue metrics
    current_depth = Column(Integer, nullable=False, default=0)
    max_depth_24h = Column(Integer, nullable=False, default=0)
    avg_depth_24h = Column(Float, nullable=False, default=0.0)

    # Processing metrics
    tasks_processed_hour = Column(Integer, nullable=False, default=0)
    tasks_processed_day = Column(Integer, nullable=False, default=0)
    avg_processing_time_ms = Column(Float, nullable=False, default=0.0)

    # Worker metrics
    active_workers = Column(Integer, nullable=False, default=0)
    total_workers = Column(Integer, nullable=False, default=0)

    # Health status
    is_healthy = Column(Boolean, nullable=False, default=True)
    last_health_check = Column(DateTime, nullable=False, default=datetime.now)
    health_issues = Column(JSON, nullable=True, default=list)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<TaskQueue(name='{self.queue_name}', depth={self.current_depth}, workers={self.active_workers})>"


class WorkerMetrics(Base):
    """
    Model for tracking individual worker performance and health.

    Provides detailed metrics per worker for capacity planning and
    performance optimization.
    """
    __tablename__ = "worker_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_name = Column(String(255), nullable=False, index=True)

    # Worker status
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen = Column(DateTime, nullable=False, default=datetime.now)
    uptime_seconds = Column(Integer, nullable=False, default=0)

    # Performance metrics
    tasks_completed_hour = Column(Integer, nullable=False, default=0)
    tasks_completed_day = Column(Integer, nullable=False, default=0)
    tasks_failed_hour = Column(Integer, nullable=False, default=0)
    tasks_failed_day = Column(Integer, nullable=False, default=0)

    # Resource utilization
    avg_memory_mb = Column(Float, nullable=False, default=0.0)
    avg_cpu_percent = Column(Float, nullable=False, default=0.0)
    peak_memory_mb = Column(Float, nullable=False, default=0.0)
    peak_cpu_percent = Column(Float, nullable=False, default=0.0)

    # Processing metrics
    avg_task_duration_ms = Column(Float, nullable=False, default=0.0)
    current_task_count = Column(Integer, nullable=False, default=0)
    max_concurrent_tasks = Column(Integer, nullable=False, default=1)

    # Worker configuration
    queues_handled = Column(JSON, nullable=True, default=list)
    worker_version = Column(String(255), nullable=True)
    worker_config = Column(JSON, nullable=True, default=dict)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<WorkerMetrics(name='{self.worker_name}', active={self.is_active}, tasks_today={self.tasks_completed_day})>"