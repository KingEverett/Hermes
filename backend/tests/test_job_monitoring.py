"""
Comprehensive test suite for job monitoring functionality.

Tests cover task monitoring, retry management, dead letter queue operations,
alerting, and API endpoints with various scenarios and edge cases.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database.connection import get_session as get_db_session
from middleware.auth import verify_api_key
from models.base import Base
from models.job_monitoring import (
    TaskExecutionHistory, DeadLetterTask, TaskAlert, TaskQueue, WorkerMetrics,
    TASK_STATUS, FAILURE_CATEGORY, ALERT_TYPE
)
from services.workers.task_monitor import TaskMonitorService, TaskMetrics
from services.workers.retry_manager import RetryManagerService, RetryConfiguration, RETRY_POLICY
from services.workers.dead_letter_queue import DeadLetterQueueService
from services.workers.alerting_service import AlertingService, AlertThreshold, ALERT_SEVERITY


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_job_monitoring.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create mock Redis and Celery for dependency injection
global_mock_redis = Mock()
global_mock_redis.keys.return_value = []
global_mock_redis.hgetall.return_value = {}
global_mock_redis.setex = Mock()
global_mock_redis.get = Mock(return_value=None)

global_mock_celery = Mock()


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


async def override_auth():
    """Override authentication for tests"""
    return "test-api-key"


def override_redis_client():
    """Override Redis client for tests"""
    return global_mock_redis


def override_celery_app():
    """Override Celery app for tests"""
    return global_mock_celery


# Import job_monitoring dependencies AFTER creating mocks
from api.job_monitoring import get_redis_client, get_celery_app

app.dependency_overrides[get_db_session] = override_get_db
app.dependency_overrides[verify_api_key] = override_auth
app.dependency_overrides[get_redis_client] = override_redis_client
app.dependency_overrides[get_celery_app] = override_celery_app

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    redis_mock = Mock()
    redis_mock.hgetall.return_value = {}
    redis_mock.keys.return_value = []
    redis_mock.exists.return_value = False
    redis_mock.setex = Mock()
    redis_mock.hset = Mock()
    redis_mock.expire = Mock()
    redis_mock.delete = Mock()
    redis_mock.hincrby = Mock()
    return redis_mock


@pytest.fixture
def mock_celery():
    """Mock Celery app for testing"""
    celery_mock = Mock()
    celery_mock.send_task.return_value = Mock(id="test-task-id")
    return celery_mock


class TestTaskMonitorService:
    """Test cases for TaskMonitorService"""

    def test_task_monitor_initialization(self, db_session, mock_redis, mock_celery):
        """Test TaskMonitorService initialization"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        assert monitor.db_session == db_session
        assert monitor.redis_client == mock_redis
        assert monitor.celery_app == mock_celery
        assert not monitor.is_monitoring
        assert monitor.task_cache == {}

    def test_create_task_history(self, db_session, mock_redis, mock_celery):
        """Test creating task execution history record"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        # Mock Celery event
        event = {
            'uuid': 'test-task-123',
            'name': 'test_task',
            'timestamp': datetime.now().timestamp(),
            'args': ['arg1'],
            'kwargs': {'key': 'value'},
            'routing_key': 'default'
        }

        monitor._create_task_history(event, TASK_STATUS['QUEUED'])

        # Verify database record
        task_history = db_session.query(TaskExecutionHistory).filter(
            TaskExecutionHistory.task_id == 'test-task-123'
        ).first()

        assert task_history is not None
        assert task_history.task_name == 'test_task'
        assert task_history.status == TASK_STATUS['QUEUED']
        assert task_history.task_args == ['arg1']
        assert task_history.task_kwargs == {'key': 'value'}

    def test_update_task_history(self, db_session, mock_redis, mock_celery):
        """Test updating task execution history"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        # Create initial task history
        task_history = TaskExecutionHistory(
            task_id='test-task-123',
            task_name='test_task',
            status=TASK_STATUS['QUEUED']
        )
        db_session.add(task_history)
        db_session.commit()

        # Update task
        update_data = {
            'started_at': datetime.now(),
            'worker_name': 'worker-1'
        }

        monitor._update_task_history('test-task-123', TASK_STATUS['PROCESSING'], update_data)

        # Verify update
        updated_task = db_session.query(TaskExecutionHistory).filter(
            TaskExecutionHistory.task_id == 'test-task-123'
        ).first()

        assert updated_task.status == TASK_STATUS['PROCESSING']
        assert updated_task.worker_name == 'worker-1'
        assert updated_task.started_at is not None

    def test_get_active_tasks(self, db_session, mock_redis, mock_celery):
        """Test retrieving active tasks from cache"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        # Mock Redis response
        mock_redis.keys.return_value = [b'hermes:tasks:active:task-1', b'hermes:tasks:active:task-2']
        mock_redis.hgetall.side_effect = [
            {
                b'task_id': b'task-1',
                b'task_name': b'test_task_1',
                b'status': b'processing',
                b'duration_ms': b'1000',
                b'worker_name': b'worker-1'
            },
            {
                b'task_id': b'task-2',
                b'task_name': b'test_task_2',
                b'status': b'queued',
                b'duration_ms': b'',
                b'worker_name': b''
            }
        ]

        active_tasks = monitor.get_active_tasks()

        assert len(active_tasks) == 2
        assert active_tasks[0].task_id == 'task-1'
        assert active_tasks[0].status == 'processing'
        assert active_tasks[0].duration_ms == 1000
        assert active_tasks[1].task_id == 'task-2'
        assert active_tasks[1].status == 'queued'

    def test_get_task_history(self, db_session, mock_redis, mock_celery):
        """Test retrieving task execution history"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        # Create test data
        for i in range(5):
            task_history = TaskExecutionHistory(
                task_id=f'task-{i}',
                task_name=f'test_task_{i}',
                status=TASK_STATUS['COMPLETED'] if i % 2 == 0 else TASK_STATUS['FAILED'],
                created_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(task_history)
        db_session.commit()

        # Test without filter
        all_history = monitor.get_task_history(limit=10)
        assert len(all_history) == 5

        # Test with status filter
        completed_history = monitor.get_task_history(limit=10, status_filter=TASK_STATUS['COMPLETED'])
        assert len(completed_history) == 3
        assert all(h.status == TASK_STATUS['COMPLETED'] for h in completed_history)

    def test_cache_task_data(self, db_session, mock_redis, mock_celery):
        """Test caching task data in Redis"""
        monitor = TaskMonitorService(db_session, mock_redis, mock_celery)

        metrics = TaskMetrics(
            task_id='test-task-123',
            task_name='test_task',
            status='processing',
            duration_ms=1500,
            memory_usage_mb=128.5,
            worker_name='worker-1'
        )

        monitor._cache_task_data('test-task-123', metrics)

        # Verify Redis calls
        expected_key = 'hermes:tasks:active:test-task-123'
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == expected_key

        # Verify mapping data
        mapping_data = call_args[1]['mapping']
        assert mapping_data['task_id'] == 'test-task-123'
        assert mapping_data['status'] == 'processing'
        assert mapping_data['duration_ms'] == 1500


class TestRetryManagerService:
    """Test cases for RetryManagerService"""

    def test_retry_manager_initialization(self, db_session, mock_redis, mock_celery):
        """Test RetryManagerService initialization"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        assert retry_manager.db_session == db_session
        assert retry_manager.redis_client == mock_redis
        assert retry_manager.celery_app == mock_celery
        assert 'default' in retry_manager.default_configs
        assert 'nvd_research_task' in retry_manager.default_configs

    def test_configure_task_retry(self, db_session, mock_redis, mock_celery):
        """Test configuring retry policy for a task"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        config = RetryConfiguration(
            max_retries=5,
            base_delay=3,
            max_delay=180,
            policy=RETRY_POLICY['EXPONENTIAL']
        )

        retry_manager.configure_task_retry('custom_task', config)

        # Verify configuration stored
        assert 'custom_task' in retry_manager.default_configs
        stored_config = retry_manager.default_configs['custom_task']
        assert stored_config.max_retries == 5
        assert stored_config.base_delay == 3
        assert stored_config.policy == RETRY_POLICY['EXPONENTIAL']

    def test_calculate_retry_delay_exponential(self, db_session, mock_redis, mock_celery):
        """Test exponential backoff delay calculation"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        config = RetryConfiguration(
            base_delay=2,
            max_delay=300,
            policy=RETRY_POLICY['EXPONENTIAL'],
            backoff_multiplier=2.0,
            jitter=False  # Disable jitter for predictable testing
        )

        # Test exponential progression
        assert retry_manager.calculate_retry_delay(1, config) == 2
        assert retry_manager.calculate_retry_delay(2, config) == 4
        assert retry_manager.calculate_retry_delay(3, config) == 8
        assert retry_manager.calculate_retry_delay(4, config) == 16

        # Test max delay cap
        assert retry_manager.calculate_retry_delay(10, config) == 300

    def test_calculate_retry_delay_linear(self, db_session, mock_redis, mock_celery):
        """Test linear delay calculation"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        config = RetryConfiguration(
            base_delay=5,
            max_delay=100,
            policy=RETRY_POLICY['LINEAR'],
            jitter=False
        )

        assert retry_manager.calculate_retry_delay(1, config) == 5
        assert retry_manager.calculate_retry_delay(2, config) == 10
        assert retry_manager.calculate_retry_delay(3, config) == 15
        assert retry_manager.calculate_retry_delay(20, config) == 100  # Capped at max

    def test_should_retry_task_success_cases(self, db_session, mock_redis, mock_celery):
        """Test task retry decision logic - success cases"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        # Configure retry policy
        config = RetryConfiguration(
            max_retries=3,
            retry_on_exceptions=['requests.exceptions.Timeout']
        )
        retry_manager.configure_task_retry('test_task', config)

        # Test retry allowed cases
        timeout_exception = Exception("requests.exceptions.Timeout")
        assert retry_manager.should_retry_task('task-1', 'test_task', timeout_exception, 1)
        assert retry_manager.should_retry_task('task-1', 'test_task', timeout_exception, 2)

        # Test max retries exceeded
        assert not retry_manager.should_retry_task('task-1', 'test_task', timeout_exception, 3)

    def test_should_retry_task_failure_cases(self, db_session, mock_redis, mock_celery):
        """Test task retry decision logic - failure cases"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        # Configure with no-retry exceptions
        config = RetryConfiguration(
            max_retries=3,
            no_retry_on_exceptions=['ValidationError', 'KeyError']
        )
        retry_manager.configure_task_retry('test_task', config)

        # Test no-retry exceptions
        validation_error = Exception("ValidationError")
        assert not retry_manager.should_retry_task('task-1', 'test_task', validation_error, 1)

        key_error = Exception("KeyError")
        assert not retry_manager.should_retry_task('task-1', 'test_task', key_error, 1)

    def test_analyze_failure_category(self, db_session, mock_redis, mock_celery):
        """Test failure categorization logic"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        # Test timeout failures
        timeout_exc = Exception("Request timeout occurred")
        assert retry_manager.analyze_failure_category(timeout_exc) == FAILURE_CATEGORY['TIMEOUT']

        # Test memory failures
        memory_exc = Exception("MemoryError: out of memory")
        assert retry_manager.analyze_failure_category(memory_exc) == FAILURE_CATEGORY['MEMORY']

        # Test connection failures
        conn_exc = Exception("ConnectionError: connection refused")
        assert retry_manager.analyze_failure_category(conn_exc) == FAILURE_CATEGORY['CONNECTION']

        # Test rate limit failures
        rate_exc = Exception("Rate limit exceeded, too many requests")
        assert retry_manager.analyze_failure_category(rate_exc) == FAILURE_CATEGORY['RATE_LIMIT']

    def test_move_to_dead_letter_queue(self, db_session, mock_redis, mock_celery):
        """Test moving failed task to dead letter queue"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        # Create task history first
        task_history = TaskExecutionHistory(
            task_id='failed-task-123',
            task_name='failing_task',
            status=TASK_STATUS['FAILED']
        )
        db_session.add(task_history)
        db_session.commit()

        # Move to dead letter queue
        success = retry_manager.move_to_dead_letter_queue(
            task_id='failed-task-123',
            task_name='failing_task',
            failure_reason='Exception: Task failed repeatedly',
            task_args=['arg1'],
            task_kwargs={'key': 'value'},
            total_attempts=3
        )

        assert success

        # Verify dead letter record created
        dlq_task = db_session.query(DeadLetterTask).filter(
            DeadLetterTask.original_task_id == 'failed-task-123'
        ).first()

        assert dlq_task is not None
        assert dlq_task.task_name == 'failing_task'
        assert dlq_task.total_attempts == 3
        assert dlq_task.task_args == ['arg1']
        assert dlq_task.task_kwargs == {'key': 'value'}

        # Verify task history updated
        updated_history = db_session.query(TaskExecutionHistory).filter(
            TaskExecutionHistory.task_id == 'failed-task-123'
        ).first()
        assert updated_history.status == TASK_STATUS['DEAD_LETTER']

    def test_get_retry_statistics(self, db_session, mock_redis, mock_celery):
        """Test retry statistics calculation"""
        retry_manager = RetryManagerService(db_session, mock_redis, mock_celery)

        # Create test data
        now = datetime.now()

        # Create various task histories
        tasks_data = [
            ('task-1', TASK_STATUS['COMPLETED'], 0),
            ('task-2', TASK_STATUS['FAILED'], 2),
            ('task-3', TASK_STATUS['COMPLETED'], 1),
            ('task-4', TASK_STATUS['DEAD_LETTER'], 3),
            ('task-5', TASK_STATUS['COMPLETED'], 0)
        ]

        for task_id, status, retry_count in tasks_data:
            task_history = TaskExecutionHistory(
                task_id=task_id,
                task_name='test_task',
                status=status,
                retry_count=retry_count,
                created_at=now - timedelta(hours=1)
            )
            db_session.add(task_history)

        # Add dead letter task
        dlq_task = DeadLetterTask(
            original_task_id='task-4',
            task_name='test_task',
            failure_reason='Failed after retries',
            total_attempts=3,
            first_failed_at=now - timedelta(minutes=60),
            last_failed_at=now - timedelta(minutes=30),
            created_at=now - timedelta(minutes=30)
        )
        db_session.add(dlq_task)
        db_session.commit()

        # Get statistics
        stats = retry_manager.get_retry_statistics(timeframe_hours=24)

        assert stats['total_tasks'] == 5
        assert stats['failed_tasks'] == 2  # FAILED + DEAD_LETTER
        assert stats['retried_tasks'] == 2  # Tasks with retry_count > 0
        assert stats['dead_letter_tasks'] == 1
        assert stats['failure_rate_percent'] == 40.0  # 2/5 * 100
        assert stats['retry_rate_percent'] == 40.0    # 2/5 * 100


class TestDeadLetterQueueService:
    """Test cases for DeadLetterQueueService"""

    def test_dlq_service_initialization(self, db_session, mock_redis, mock_celery):
        """Test DeadLetterQueueService initialization"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        assert dlq_service.db_session == db_session
        assert dlq_service.redis_client == mock_redis
        assert dlq_service.celery_app == mock_celery
        assert dlq_service.DEFAULT_PAGE_SIZE == 50

    def test_get_dead_letter_tasks_pagination(self, db_session, mock_redis, mock_celery):
        """Test paginated dead letter task retrieval"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create test data
        for i in range(25):
            dlq_task = DeadLetterTask(
                original_task_id=f'task-{i}',
                task_name=f'test_task_{i % 3}',  # 3 different task names
                failure_reason=f'Error {i}',
                failure_category=FAILURE_CATEGORY['EXCEPTION'],
                total_attempts=3,
                first_failed_at=datetime.now() - timedelta(hours=i),
                last_failed_at=datetime.now() - timedelta(hours=i),
                created_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Test first page
        result = dlq_service.get_dead_letter_tasks(page=1, page_size=10)

        assert result['pagination']['page'] == 1
        assert result['pagination']['page_size'] == 10
        assert result['pagination']['total_tasks'] == 25
        assert result['pagination']['total_pages'] == 3
        assert result['pagination']['has_next'] == True
        assert result['pagination']['has_prev'] == False
        assert len(result['tasks']) == 10

        # Test last page
        result = dlq_service.get_dead_letter_tasks(page=3, page_size=10)
        assert len(result['tasks']) == 5
        assert result['pagination']['has_next'] == False
        assert result['pagination']['has_prev'] == True

    def test_get_dead_letter_tasks_filtering(self, db_session, mock_redis, mock_celery):
        """Test dead letter task filtering"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create test data with different categories
        categories = [FAILURE_CATEGORY['TIMEOUT'], FAILURE_CATEGORY['CONNECTION'], FAILURE_CATEGORY['MEMORY']]
        task_names = ['task_a', 'task_b', 'task_c']

        for i in range(9):
            dlq_task = DeadLetterTask(
                original_task_id=f'task-{i}',
                task_name=task_names[i % 3],
                failure_reason=f'Error {i}',
                failure_category=categories[i % 3],
                total_attempts=3,
                first_failed_at=datetime.now() - timedelta(hours=i),
                last_failed_at=datetime.now() - timedelta(hours=i),
                processed=(i % 2 == 0)  # Half processed, half not
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Test category filter
        timeout_tasks = dlq_service.get_dead_letter_tasks(category_filter=FAILURE_CATEGORY['TIMEOUT'])
        assert len(timeout_tasks['tasks']) == 3
        assert all(t['failure_category'] == FAILURE_CATEGORY['TIMEOUT'] for t in timeout_tasks['tasks'])

        # Test task name filter
        task_a_tasks = dlq_service.get_dead_letter_tasks(task_name_filter='task_a')
        assert len(task_a_tasks['tasks']) == 3
        assert all('task_a' in t['task_name'] for t in task_a_tasks['tasks'])

        # Test processed filter
        unprocessed_tasks = dlq_service.get_dead_letter_tasks(processed_filter=False)
        assert len(unprocessed_tasks['tasks']) == 4  # Unprocessed tasks

    def test_retry_dead_letter_task_success(self, db_session, mock_redis, mock_celery):
        """Test successful retry of dead letter task"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create dead letter task
        dlq_task = DeadLetterTask(
            original_task_id='failed-task-123',
            task_name='test_task',
            task_args=['arg1'],
            task_kwargs={'key': 'value'},
            failure_reason='Connection timeout',
            total_attempts=3,
            first_failed_at=datetime.now() - timedelta(hours=1),
            last_failed_at=datetime.now(),
            retry_scheduled=False,
            retry_attempts=0
        )
        db_session.add(dlq_task)
        db_session.commit()

        # Configure Celery mock
        mock_result = Mock()
        mock_result.id = 'new-task-456'
        mock_celery.send_task.return_value = mock_result

        # Retry the task
        result = dlq_service.retry_dead_letter_task(str(dlq_task.id), user_id='test_user')

        assert result.success == True
        assert result.task_id == 'new-task-456'

        # Verify Celery call
        mock_celery.send_task.assert_called_once_with(
            'test_task',
            args=['arg1'],
            kwargs={'key': 'value'}
        )

        # Verify database update
        db_session.refresh(dlq_task)
        assert dlq_task.retry_scheduled == True
        assert dlq_task.retry_attempts == 1
        assert dlq_task.processed_by == 'test_user'

    def test_retry_dead_letter_task_max_attempts(self, db_session, mock_redis, mock_celery):
        """Test retry failure when max attempts exceeded"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create dead letter task with max retry attempts
        dlq_task = DeadLetterTask(
            original_task_id='failed-task-123',
            task_name='test_task',
            task_args=[],
            task_kwargs={},
            failure_reason='Repeated failures',
            total_attempts=5,
            first_failed_at=datetime.now() - timedelta(hours=2),
            last_failed_at=datetime.now(),
            retry_attempts=3  # At max
        )
        db_session.add(dlq_task)
        db_session.commit()

        # Attempt retry
        result = dlq_service.retry_dead_letter_task(str(dlq_task.id))

        assert result.success == False
        assert "Maximum retry attempts" in result.error_message

    def test_bulk_retry_tasks(self, db_session, mock_redis, mock_celery):
        """Test bulk retry functionality"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create dead letter tasks with different categories
        for i in range(5):
            dlq_task = DeadLetterTask(
                original_task_id=f'task-{i}',
                task_name='timeout_task' if i < 3 else 'connection_task',
                task_args=[],
                task_kwargs={},
                failure_reason='Test failure',
                failure_category=FAILURE_CATEGORY['TIMEOUT'] if i < 3 else FAILURE_CATEGORY['CONNECTION'],
                total_attempts=2,
                first_failed_at=datetime.now() - timedelta(hours=i+1),
                last_failed_at=datetime.now() - timedelta(hours=i),
                retry_scheduled=False,
                retry_attempts=0
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Configure Celery mock
        mock_celery.send_task.side_effect = [Mock(id=f'new-task-{i}') for i in range(5)]

        # Bulk retry timeout tasks
        result = dlq_service.bulk_retry_tasks(
            category=FAILURE_CATEGORY['TIMEOUT'],
            limit=10,
            user_id='test_user'
        )

        assert result['total_attempted'] == 3
        assert result['successful'] == 3
        assert result['failed'] == 0
        assert len(result['results']) == 3

        # Verify all results are for timeout tasks
        for result_entry in result['results']:
            assert result_entry['success'] == True
            assert result_entry['new_task_id'] is not None

    def test_analyze_dead_letter_queue(self, db_session, mock_redis, mock_celery):
        """Test dead letter queue analysis"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create test data with various patterns
        categories = [FAILURE_CATEGORY['TIMEOUT'], FAILURE_CATEGORY['CONNECTION'], FAILURE_CATEGORY['MEMORY']]
        task_names = ['api_task', 'db_task', 'file_task']

        for i in range(12):
            dlq_task = DeadLetterTask(
                original_task_id=f'task-{i}',
                task_name=task_names[i % 3],
                failure_reason=f'{categories[i % 3].title()}Error: test error {i}',
                failure_category=categories[i % 3],
                total_attempts=3,
                first_failed_at=datetime.now() - timedelta(hours=i+2),
                last_failed_at=datetime.now() - timedelta(hours=i),
                created_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Analyze the queue
        analysis = dlq_service.analyze_dead_letter_queue(days_back=7)

        assert analysis.total_tasks == 12
        assert len(analysis.by_category) == 3
        assert analysis.by_category[FAILURE_CATEGORY['TIMEOUT']] == 4
        assert analysis.by_category[FAILURE_CATEGORY['CONNECTION']] == 4
        assert analysis.by_category[FAILURE_CATEGORY['MEMORY']] == 4

        assert len(analysis.by_task_name) == 3
        assert analysis.by_task_name['api_task'] == 4
        assert analysis.by_task_name['db_task'] == 4
        assert analysis.by_task_name['file_task'] == 4

        assert len(analysis.recommendations) > 0

    def test_mark_task_processed(self, db_session, mock_redis, mock_celery):
        """Test marking dead letter task as processed"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create dead letter task
        dlq_task = DeadLetterTask(
            original_task_id='processed-task-123',
            task_name='test_task',
            failure_reason='Test failure',
            total_attempts=3,
            first_failed_at=datetime.now() - timedelta(hours=1),
            last_failed_at=datetime.now(),
            processed=False
        )
        db_session.add(dlq_task)
        db_session.commit()

        # Mark as processed
        success = dlq_service.mark_task_processed(
            str(dlq_task.id),
            user_id='test_user',
            notes='Resolved by manual intervention'
        )

        assert success == True

        # Verify database update
        db_session.refresh(dlq_task)
        assert dlq_task.processed == True
        assert dlq_task.processed_by == 'test_user'
        assert dlq_task.processing_notes == 'Resolved by manual intervention'
        assert dlq_task.processed_at is not None

    def test_get_failure_statistics(self, db_session, mock_redis, mock_celery):
        """Test failure statistics calculation"""
        dlq_service = DeadLetterQueueService(db_session, mock_redis, mock_celery)

        # Create test data
        now = datetime.now()

        # Create dead letter tasks
        for i in range(10):
            dlq_task = DeadLetterTask(
                original_task_id=f'task-{i}',
                task_name='test_task',
                failure_reason='Test failure',
                failure_category=FAILURE_CATEGORY['TIMEOUT'] if i < 6 else FAILURE_CATEGORY['CONNECTION'],
                total_attempts=3,
                first_failed_at=now - timedelta(hours=i+2),
                last_failed_at=now - timedelta(hours=i),
                processed=(i < 4),  # 4 processed, 6 unprocessed
                retry_attempts=1 if i < 3 else 0,  # 3 with retries
                created_at=now - timedelta(hours=i)
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Get statistics
        stats = dlq_service.get_failure_statistics(days_back=7)

        assert stats['total_dead_letter_tasks'] == 10
        assert stats['processed_tasks'] == 4
        assert stats['unprocessed_tasks'] == 6
        assert stats['retried_tasks'] == 3
        assert stats['resolution_rate_percent'] == 40.0  # 4/10 * 100

        # Check category breakdown
        assert stats['category_breakdown'][FAILURE_CATEGORY['TIMEOUT']] == 6
        assert stats['category_breakdown'][FAILURE_CATEGORY['CONNECTION']] == 4


class TestAlertingService:
    """Test cases for AlertingService"""

    def test_alerting_service_initialization(self, db_session, mock_redis):
        """Test AlertingService initialization"""
        alerting = AlertingService(db_session, mock_redis)

        assert alerting.db_session == db_session
        assert alerting.redis_client == mock_redis
        assert len(alerting.default_thresholds) == 6  # All alert types
        assert ALERT_TYPE['HIGH_FAILURE_RATE'] in alerting.default_thresholds

    def test_configure_threshold(self, db_session, mock_redis):
        """Test configuring alert threshold"""
        alerting = AlertingService(db_session, mock_redis)

        threshold = AlertThreshold(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=15.0,
            comparison='gte',
            timeframe_minutes=30,
            severity=ALERT_SEVERITY['HIGH']
        )

        alerting.configure_threshold(ALERT_TYPE['HIGH_FAILURE_RATE'], threshold)

        # Verify threshold stored
        stored_threshold = alerting.active_thresholds[ALERT_TYPE['HIGH_FAILURE_RATE']]
        assert stored_threshold.threshold_value == 15.0
        assert stored_threshold.timeframe_minutes == 30
        assert stored_threshold.severity == ALERT_SEVERITY['HIGH']

    @pytest.mark.asyncio
    async def test_calculate_failure_rate_metric(self, db_session, mock_redis):
        """Test failure rate metric calculation"""
        alerting = AlertingService(db_session, mock_redis)

        # Create test task history data
        now = datetime.now()

        # 10 total tasks: 3 failed, 7 completed
        statuses = [TASK_STATUS['FAILED']] * 3 + [TASK_STATUS['COMPLETED']] * 7

        for i, status in enumerate(statuses):
            task_history = TaskExecutionHistory(
                task_id=f'task-{i}',
                task_name='test_task',
                status=status,
                created_at=now - timedelta(minutes=30)
            )
            db_session.add(task_history)
        db_session.commit()

        # Test failure rate calculation
        threshold = alerting.default_thresholds[ALERT_TYPE['HIGH_FAILURE_RATE']]
        failure_rate = await alerting._calculate_metric_value(threshold)

        assert failure_rate == 30.0  # 3/10 * 100

    @pytest.mark.asyncio
    async def test_calculate_queue_backup_metric(self, db_session, mock_redis):
        """Test queue backup metric calculation"""
        alerting = AlertingService(db_session, mock_redis)

        # Create test queue data
        queue1 = TaskQueue(queue_name='queue1', current_depth=50)
        queue2 = TaskQueue(queue_name='queue2', current_depth=75)
        db_session.add(queue1)
        db_session.add(queue2)
        db_session.commit()

        # Test queue depth calculation
        threshold = alerting.default_thresholds[ALERT_TYPE['QUEUE_BACKUP']]
        queue_depth = await alerting._calculate_metric_value(threshold)

        assert queue_depth == 125.0  # 50 + 75

    def test_check_threshold_comparisons(self, db_session, mock_redis):
        """Test threshold comparison logic"""
        alerting = AlertingService(db_session, mock_redis)

        # Test greater than or equal
        assert alerting._check_threshold(25.0, 20.0, 'gte') == True
        assert alerting._check_threshold(20.0, 20.0, 'gte') == True
        assert alerting._check_threshold(15.0, 20.0, 'gte') == False

        # Test greater than
        assert alerting._check_threshold(25.0, 20.0, 'gt') == True
        assert alerting._check_threshold(20.0, 20.0, 'gt') == False

        # Test less than
        assert alerting._check_threshold(15.0, 20.0, 'lt') == True
        assert alerting._check_threshold(25.0, 20.0, 'lt') == False

    @pytest.mark.asyncio
    async def test_is_alert_deduplicated(self, db_session, mock_redis):
        """Test alert deduplication logic"""
        alerting = AlertingService(db_session, mock_redis)

        # Mock Redis to return existing alert
        mock_redis.get.return_value = '{"value": 25.0, "timestamp": "2023-01-01T00:00:00"}'

        is_duplicated = await alerting._is_alert_deduplicated(ALERT_TYPE['HIGH_FAILURE_RATE'], 25.0)
        assert is_duplicated == True

        # Mock Redis to return no existing alert
        mock_redis.get.return_value = None

        # Create active alert in database
        active_alert = TaskAlert(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=20.0,
            current_value=25.0,
            alert_condition='failure_rate >= 20.0'
        )
        db_session.add(active_alert)
        db_session.commit()

        is_duplicated = await alerting._is_alert_deduplicated(ALERT_TYPE['HIGH_FAILURE_RATE'], 30.0)
        assert is_duplicated == True

        # Verify current value was updated
        db_session.refresh(active_alert)
        assert active_alert.current_value == 30.0

    def test_get_active_alerts(self, db_session, mock_redis):
        """Test retrieving active alerts"""
        alerting = AlertingService(db_session, mock_redis)

        # Create test alerts
        alert1 = TaskAlert(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=20.0,
            current_value=25.0,
            alert_condition='failure_rate >= 20.0',
            triggered_at=datetime.now() - timedelta(hours=1)
        )

        alert2 = TaskAlert(
            alert_type=ALERT_TYPE['QUEUE_BACKUP'],
            threshold_value=100.0,
            current_value=150.0,
            alert_condition='queue_depth >= 100',
            triggered_at=datetime.now() - timedelta(minutes=30),
            resolved_at=datetime.now() - timedelta(minutes=10)  # Resolved
        )

        alert3 = TaskAlert(
            alert_type=ALERT_TYPE['WORKER_DOWN'],
            threshold_value=1.0,
            current_value=2.0,
            alert_condition='workers_down >= 1',
            triggered_at=datetime.now() - timedelta(minutes=15)
        )

        db_session.add_all([alert1, alert2, alert3])
        db_session.commit()

        # Get active alerts (should exclude resolved)
        active_alerts = alerting.get_active_alerts()

        assert len(active_alerts) == 2  # alert1 and alert3, not alert2 (resolved)
        alert_types = [alert['alert_type'] for alert in active_alerts]
        assert ALERT_TYPE['HIGH_FAILURE_RATE'] in alert_types
        assert ALERT_TYPE['WORKER_DOWN'] in alert_types
        assert ALERT_TYPE['QUEUE_BACKUP'] not in alert_types  # Resolved

    def test_resolve_alert(self, db_session, mock_redis):
        """Test manual alert resolution"""
        alerting = AlertingService(db_session, mock_redis)

        # Create active alert
        alert = TaskAlert(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=20.0,
            current_value=25.0,
            alert_condition='failure_rate >= 20.0'
        )
        db_session.add(alert)
        db_session.commit()

        alert_id = str(alert.id)

        # Resolve the alert
        success = alerting.resolve_alert(alert_id, user_id='test_user')
        assert success == True

        # Verify alert resolved
        db_session.refresh(alert)
        assert alert.resolved_at is not None
        assert alert.auto_resolved == False
        assert alert.resolution_data == {'resolved_by': 'test_user'}

    def test_get_alert_history(self, db_session, mock_redis):
        """Test retrieving alert history"""
        alerting = AlertingService(db_session, mock_redis)

        # Create historical alerts
        now = datetime.now()

        for i in range(5):
            alert = TaskAlert(
                alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
                threshold_value=20.0,
                current_value=25.0 + i,
                alert_condition='failure_rate >= 20.0',
                triggered_at=now - timedelta(days=i),
                resolved_at=now - timedelta(days=i, hours=1) if i < 3 else None
            )
            db_session.add(alert)
        db_session.commit()

        # Get recent history
        history = alerting.get_alert_history(days_back=7, limit=10)

        assert len(history) == 5

        # Verify ordering (most recent first)
        timestamps = [datetime.fromisoformat(alert['triggered_at'].replace('Z', '+00:00')) for alert in history]
        assert timestamps == sorted(timestamps, reverse=True)


class TestJobMonitoringAPI:
    """Test cases for job monitoring API endpoints"""

    def test_get_task_history_endpoint(self, db_session):
        """Test GET /api/v1/monitoring/tasks endpoint"""
        # Create test data
        for i in range(3):
            task_history = TaskExecutionHistory(
                task_id=f'task-{i}',
                task_name=f'test_task_{i}',
                status=TASK_STATUS['COMPLETED'] if i % 2 == 0 else TASK_STATUS['FAILED'],
                created_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(task_history)
        db_session.commit()

        # Test endpoint
        response = client.get("/api/v1/monitoring/tasks")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3
        assert all('task_id' in task for task in data)
        assert all('task_name' in task for task in data)
        assert all('status' in task for task in data)

    def test_get_task_history_with_filters(self, db_session):
        """Test task history endpoint with filters"""
        # Create test data
        statuses = [TASK_STATUS['COMPLETED'], TASK_STATUS['FAILED'], TASK_STATUS['COMPLETED']]

        for i, status in enumerate(statuses):
            task_history = TaskExecutionHistory(
                task_id=f'task-{i}',
                task_name=f'test_task_{i}',
                status=status,
                created_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(task_history)
        db_session.commit()

        # Test status filter
        response = client.get("/api/v1/monitoring/tasks?status=completed")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert all(task['status'] == 'completed' for task in data)

    def test_get_task_details_endpoint(self, db_session):
        """Test GET /api/v1/monitoring/tasks/{task_id} endpoint"""
        # Create test task
        task_history = TaskExecutionHistory(
            task_id='specific-task-123',
            task_name='specific_test_task',
            status=TASK_STATUS['COMPLETED'],
            duration_ms=5000,
            worker_name='worker-1',
            retry_count=1
        )
        db_session.add(task_history)
        db_session.commit()

        # Test endpoint
        response = client.get("/api/v1/monitoring/tasks/specific-task-123")
        assert response.status_code == 200

        data = response.json()
        assert data['task_id'] == 'specific-task-123'
        assert data['task_name'] == 'specific_test_task'
        assert data['status'] == 'completed'
        assert data['duration_ms'] == 5000
        assert data['worker_name'] == 'worker-1'
        assert data['retry_count'] == 1

    def test_get_task_details_not_found(self, db_session):
        """Test task details endpoint with non-existent task"""
        response = client.get("/api/v1/monitoring/tasks/non-existent-task")
        assert response.status_code == 404
        assert response.json()['detail'] == "Task not found"

    def test_get_active_tasks_endpoint(self):
        """Test GET /api/v1/monitoring/tasks/active endpoint"""
        # Setup mock Redis to return active tasks data
        global_mock_redis.keys.return_value = [b'hermes:tasks:active:task-1', b'hermes:tasks:active:task-2']
        global_mock_redis.hgetall.side_effect = [
            {
                b'task_id': b'active-task-1',
                b'task_name': b'active_test_task',
                b'status': b'processing',
                b'duration_ms': b'3000',
                b'worker_name': b'worker-1'
            },
            {
                b'task_id': b'active-task-2',
                b'task_name': b'active_test_task_2',
                b'status': b'queued',
                b'duration_ms': b'',
                b'worker_name': b''
            }
        ]

        # Test endpoint
        response = client.get("/api/v1/monitoring/tasks/active")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]['task_id'] == 'active-task-1'
        assert data[0]['status'] == 'processing'
        assert data[0]['duration_ms'] == 3000
        assert data[1]['task_id'] == 'active-task-2'
        assert data[1]['status'] == 'queued'

        # Reset mock
        global_mock_redis.keys.return_value = []
        global_mock_redis.hgetall.side_effect = None

    def test_get_dead_letter_queue_endpoint(self, db_session):
        """Test GET /api/v1/monitoring/tasks/dead-letter endpoint"""
        # Create test dead letter tasks
        for i in range(3):
            dlq_task = DeadLetterTask(
                original_task_id=f'failed-task-{i}',
                task_name=f'failed_test_task_{i}',
                failure_reason=f'Error {i}',
                failure_category=FAILURE_CATEGORY['TIMEOUT'],
                total_attempts=3,
                first_failed_at=datetime.now() - timedelta(hours=i+1),
                last_failed_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Test endpoint
        response = client.get("/api/v1/monitoring/tasks/dead-letter")
        assert response.status_code == 200

        data = response.json()
        assert 'tasks' in data
        assert 'pagination' in data
        assert len(data['tasks']) == 3

        # Verify task structure
        task = data['tasks'][0]
        assert 'id' in task
        assert 'original_task_id' in task
        assert 'task_name' in task
        assert 'failure_reason' in task
        assert 'failure_category' in task

    def test_get_dead_letter_queue_with_pagination(self, db_session):
        """Test dead letter queue endpoint with pagination"""
        # Create more test data
        for i in range(15):
            dlq_task = DeadLetterTask(
                original_task_id=f'failed-task-{i}',
                task_name='failed_test_task',
                failure_reason=f'Error {i}',
                failure_category=FAILURE_CATEGORY['EXCEPTION'],
                total_attempts=3,
                first_failed_at=datetime.now() - timedelta(hours=i+1),
                last_failed_at=datetime.now() - timedelta(hours=i)
            )
            db_session.add(dlq_task)
        db_session.commit()

        # Test first page
        response = client.get("/api/v1/monitoring/tasks/dead-letter?page=1&page_size=10")
        assert response.status_code == 200

        data = response.json()
        assert len(data['tasks']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total_tasks'] == 15
        assert data['pagination']['has_next'] == True

    def test_configure_retry_policy_endpoint(self, db_session):
        """Test POST /api/v1/monitoring/tasks/retry-config/{task_name} endpoint"""
        config_data = {
            "max_retries": 5,
            "base_delay": 3,
            "max_delay": 180,
            "policy": "exponential",
            "jitter": True,
            "backoff_multiplier": 2.5
        }

        response = client.post("/api/v1/monitoring/tasks/retry-config/custom_task", json=config_data)
        assert response.status_code == 200

        data = response.json()
        assert "Retry policy configured for custom_task" in data['message']
        assert data['configuration']['max_retries'] == 5
        assert data['configuration']['policy'] == 'exponential'
        assert data['configuration']['backoff_multiplier'] == 2.5

    def test_get_retry_policy_endpoint(self, db_session):
        """Test GET /api/v1/monitoring/tasks/retry-config/{task_name} endpoint"""
        # The endpoint should return default configuration for unknown task
        response = client.get("/api/v1/monitoring/tasks/retry-config/unknown_task")
        assert response.status_code == 200

        data = response.json()
        assert data['task_name'] == 'unknown_task'
        assert 'configuration' in data
        assert 'max_retries' in data['configuration']
        assert 'policy' in data['configuration']

    def test_get_alerts_endpoint(self, db_session):
        """Test GET /api/v1/monitoring/tasks/alerts endpoint"""
        # Create test alerts
        alert1 = TaskAlert(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=20.0,
            current_value=25.0,
            alert_condition='failure_rate >= 20.0'
        )
        alert2 = TaskAlert(
            alert_type=ALERT_TYPE['QUEUE_BACKUP'],
            threshold_value=100.0,
            current_value=150.0,
            alert_condition='queue_depth >= 100'
        )
        db_session.add_all([alert1, alert2])
        db_session.commit()

        # Test endpoint
        response = client.get("/api/v1/monitoring/tasks/alerts")
        assert response.status_code == 200

        data = response.json()
        assert 'active_alerts' in data
        assert 'total_count' in data
        assert data['total_count'] == 2
        assert len(data['active_alerts']) == 2

    def test_resolve_alert_endpoint(self, db_session):
        """Test POST /api/v1/monitoring/tasks/alerts/{alert_id}/resolve endpoint"""
        # Create test alert
        alert = TaskAlert(
            alert_type=ALERT_TYPE['HIGH_FAILURE_RATE'],
            threshold_value=20.0,
            current_value=25.0,
            alert_condition='failure_rate >= 20.0'
        )
        db_session.add(alert)
        db_session.commit()

        alert_id = str(alert.id)

        # Test endpoint
        response = client.post(f"/api/v1/monitoring/tasks/alerts/{alert_id}/resolve")
        assert response.status_code == 200

        data = response.json()
        assert "Alert resolved successfully" in data['message']
        assert data['alert_id'] == alert_id
        assert data['resolved_by'] == 'api_user'

        # Verify alert was resolved in database
        db_session.refresh(alert)
        assert alert.resolved_at is not None

    def test_resolve_alert_not_found(self, db_session):
        """Test resolving non-existent alert"""
        response = client.post("/api/v1/monitoring/tasks/alerts/non-existent-id/resolve")
        assert response.status_code == 404
        assert response.json()['detail'] == "Alert not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])