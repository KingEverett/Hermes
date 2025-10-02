"""Performance tests for documentation generation with large datasets."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from services.documentation import DocumentationService
from services.documentation_optimized import OptimizedDocumentationService
from models import Project, Host, Service, Scan
from models.scan import ScanStatus, ToolType


class TestDocumentationPerformance:
    """Performance test suite for documentation generation."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def doc_service(self, mock_db_session):
        """Create DocumentationService instance."""
        return DocumentationService(mock_db_session)

    @pytest.fixture
    def optimized_service(self, mock_db_session):
        """Create OptimizedDocumentationService instance."""
        return OptimizedDocumentationService(mock_db_session)

    def generate_large_dataset(self, host_count: int, services_per_host: int = 10):
        """Generate large dataset for performance testing.

        Args:
            host_count: Number of hosts to generate
            services_per_host: Number of services per host

        Returns:
            Tuple of (project, hosts, scans)
        """
        project = Project(
            id="perf-test-project",
            name="Performance Test Project",
            description="Large dataset for performance testing",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        hosts = []
        for i in range(host_count):
            host = Host(
                id=f"host-{i}",
                project_id="perf-test-project",
                ip_address=f"10.{i // 256}.{i % 256}.1",
                hostname=f"host{i}.test.com" if i % 2 == 0 else None,
                os_family="Linux" if i % 3 == 0 else "Windows",
                os_details="Ubuntu 22.04" if i % 3 == 0 else "Windows Server 2019",
                status="up",
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )

            # Add services
            host.services = []
            for port_idx in range(services_per_host):
                port = 1000 + (port_idx * 100) + (i % 10)
                service = Service(
                    id=f"service-{i}-{port_idx}",
                    host_id=host.id,
                    port=port,
                    protocol="tcp" if port_idx % 2 == 0 else "udp",
                    service_name=f"service-{port_idx}",
                    product=f"Product-{port_idx}",
                    version=f"{port_idx}.0",
                    banner=f"Banner for service on port {port}" if port_idx % 3 == 0 else None
                )
                host.services.append(service)

            hosts.append(host)

        scans = [
            Scan(
                id="scan-perf-1",
                project_id="perf-test-project",
                filename="large_scan.xml",
                tool_type=ToolType.NMAP,
                status=ScanStatus.COMPLETED,
                processing_time_ms=host_count * 10,
                parsed_at=datetime.now()
            )
        ]

        return project, hosts, scans

    def test_performance_100_hosts(self, optimized_service, mock_db_session):
        """Test performance with 100 hosts (should be under 5 seconds)."""
        project, hosts, scans = self.generate_large_dataset(100, 10)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = project
        mock_db_session.query.return_value.filter.return_value.all.return_value = scans
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 100

        # Mock chunked host fetching
        def mock_chunked_fetch():
            chunk_size = 100
            for i in range(0, len(hosts), chunk_size):
                yield hosts[i:i+chunk_size]

        optimized_service._fetch_hosts_chunked = Mock(return_value=mock_chunked_fetch())
        optimized_service._fetch_services_batch = Mock(side_effect=lambda host_ids: [
            service for host in hosts if host.id in host_ids for service in host.services
        ])

        # Measure performance
        start_time = time.time()
        result = optimized_service.generate_markdown_chunked("perf-test-project")
        execution_time = time.time() - start_time

        # Assertions
        assert result is not None
        assert "Performance Test Project" in result
        assert execution_time < 5.0, f"Generation took {execution_time:.2f}s, should be under 5s"
        assert "**Total Hosts**: 100" in result
        assert "**Total Services**: 1000" in result  # 100 hosts * 10 services

    def test_performance_500_hosts(self, optimized_service, mock_db_session):
        """Test performance with 500+ hosts (should be under 10 seconds)."""
        project, hosts, scans = self.generate_large_dataset(500, 10)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = project
        mock_db_session.query.return_value.filter.return_value.all.return_value = scans
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 500

        # Mock chunked host fetching
        def mock_chunked_fetch():
            chunk_size = 100
            for i in range(0, len(hosts), chunk_size):
                yield hosts[i:i+chunk_size]

        optimized_service._fetch_hosts_chunked = Mock(return_value=mock_chunked_fetch())
        optimized_service._fetch_services_batch = Mock(side_effect=lambda host_ids: [
            service for host in hosts if host.id in host_ids for service in host.services
        ])

        # Measure performance
        start_time = time.time()
        result = optimized_service.generate_markdown_chunked("perf-test-project")
        execution_time = time.time() - start_time

        # Assertions
        assert result is not None
        assert "Performance Test Project" in result
        assert execution_time < 10.0, f"Generation took {execution_time:.2f}s, should be under 10s"
        assert "**Total Hosts**: 500" in result
        assert "**Total Services**: 5000" in result  # 500 hosts * 10 services

    def test_chunked_processing(self, optimized_service, mock_db_session):
        """Test that chunked processing works correctly."""
        project, hosts, scans = self.generate_large_dataset(250, 5)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = project
        mock_db_session.query.return_value.filter.return_value.all.return_value = scans
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 250

        # Track chunk processing
        chunks_processed = []

        def mock_chunked_fetch():
            chunk_size = 100
            for i in range(0, len(hosts), chunk_size):
                chunk = hosts[i:i+chunk_size]
                chunks_processed.append(len(chunk))
                yield chunk

        optimized_service._fetch_hosts_chunked = Mock(return_value=mock_chunked_fetch())
        optimized_service._fetch_services_batch = Mock(side_effect=lambda host_ids: [
            service for host in hosts if host.id in host_ids for service in host.services
        ])

        # Generate with chunking
        result = optimized_service.generate_markdown_chunked("perf-test-project")

        # Assertions
        assert len(chunks_processed) == 3  # 250 hosts in chunks of 100 = 3 chunks
        assert chunks_processed[0] == 100
        assert chunks_processed[1] == 100
        assert chunks_processed[2] == 50
        assert "**Total Hosts**: 250" in result

    def test_progress_callback(self, optimized_service, mock_db_session):
        """Test progress callback functionality."""
        project, hosts, scans = self.generate_large_dataset(50, 3)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = project
        mock_db_session.query.return_value.filter.return_value.all.return_value = scans
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 50

        # Mock chunked fetching
        def mock_chunked_fetch():
            chunk_size = 100
            for i in range(0, len(hosts), chunk_size):
                yield hosts[i:i+chunk_size]

        optimized_service._fetch_hosts_chunked = Mock(return_value=mock_chunked_fetch())
        optimized_service._fetch_services_batch = Mock(return_value=[])

        # Track progress
        progress_updates = []

        def progress_callback(progress, processed, total):
            progress_updates.append({
                'progress': progress,
                'processed': processed,
                'total': total
            })

        # Generate with progress tracking
        result = optimized_service.generate_markdown_chunked("perf-test-project", progress_callback)

        # Assertions
        assert len(progress_updates) > 0
        assert progress_updates[-1]['progress'] == 100.0
        assert progress_updates[-1]['processed'] == 50
        assert progress_updates[-1]['total'] == 50

    def test_memory_efficiency(self, optimized_service, mock_db_session):
        """Test memory efficiency with large dataset."""
        # This test verifies the chunking approach doesn't load all data at once
        project, _, scans = self.generate_large_dataset(1000, 20)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = project
        mock_db_session.query.return_value.filter.return_value.all.return_value = scans
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 1000

        # Track memory usage via query patterns
        query_limits = []

        def track_limit(self_mock):
            limit_mock = MagicMock()

            def record_limit(n):
                query_limits.append(n)
                return MagicMock(all=MagicMock(return_value=[]))

            limit_mock.limit = record_limit
            return limit_mock

        mock_db_session.query.return_value.filter.return_value.offset.return_value = track_limit(None)

        # Generate
        with patch.object(optimized_service, '_fetch_services_batch', return_value=[]):
            optimized_service.generate_markdown_chunked("perf-test-project")

        # Verify chunked queries
        assert all(limit <= 100 for limit in query_limits), "Should process in chunks of 100 or less"

    def test_automatic_strategy_selection(self, doc_service, mock_db_session):
        """Test that service automatically selects optimized version for large datasets."""
        # Small dataset - should use regular version
        mock_db_session.query.return_value.filter.return_value.count.return_value = 50
        doc_service.project_repo.get_by_id = Mock(return_value=Project(id="test", name="Test"))
        mock_db_session.query.return_value.filter.return_value.options.return_value.all.return_value = []
        doc_service.scan_repo.get_by_project = Mock(return_value=[])

        with patch('services.documentation_optimized.OptimizedDocumentationService.generate_markdown_chunked') as mock_optimized:
            doc_service.generate_markdown("test-project")
            mock_optimized.assert_not_called()

        # Large dataset - should use optimized version
        mock_db_session.query.return_value.filter.return_value.count.return_value = 150

        with patch('services.documentation_optimized.OptimizedDocumentationService.generate_markdown_chunked') as mock_optimized:
            mock_optimized.return_value = "# Optimized Result"
            result = doc_service.generate_markdown("test-project")
            mock_optimized.assert_called_once()
            assert result == "# Optimized Result"