"""
Performance benchmark tests for scan import functionality.

Tests validate AC #3 (1000+ hosts without memory errors) and 
AC #6 (100 hosts in under 5 seconds).
"""
import pytest
import time
import psutil
import os
from uuid import uuid4
from unittest.mock import Mock

from parsers.base import ParsedHost, ParsedService
from services import ScanImportService


def generate_test_hosts(count: int, services_per_host: int = 3) -> list:
    """
    Generate test host data for performance benchmarking.
    
    Args:
        count: Number of hosts to generate
        services_per_host: Number of services per host
        
    Returns:
        List of ParsedHost objects
    """
    hosts = []
    # Common ports to use, extended for high service counts
    base_ports = [22, 80, 443, 3306, 5432, 8080, 8443, 9000, 27017, 6379]
    for i in range(1, count + 1):
        # Generate requested number of services
        services = [
            ParsedService(
                port=base_ports[j % len(base_ports)] + (j // len(base_ports)) * 10000,
                protocol='tcp',
                service_name=f'service-{j}',
                product=f'Product-{j}',
                version='1.0.0',
                confidence='high'
            )
            for j in range(services_per_host)
        ]
        
        host = ParsedHost(
            ip_address=f"192.168.{(i // 256)}.{(i % 256)}",
            hostname=f"host-{i}.test.local",
            os_family="Linux",
            os_details=f"Linux 5.4 (host {i})",
            status="up",
            services=services
        )
        hosts.append(host)
    
    return hosts


class TestPerformanceBenchmarks:
    """Performance benchmark tests for scan import"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.session = Mock()
        self.service = ScanImportService(self.session)
        self.project_id = uuid4()
        
        # Mock repositories to avoid actual database operations
        self.service.scan_repo = Mock()
        self.service.host_repo = Mock()
        self.service.service_repo = Mock()
        
        # Track memory usage
        self.process = psutil.Process(os.getpid())
        
    def test_ac3_handle_1000_plus_hosts_without_memory_errors(self):
        """
        AC #3: Handle 1000+ hosts without memory errors
        
        This test validates that the system can process 1000+ hosts
        without excessive memory usage or errors.
        """
        # Generate 1500 hosts (exceeding 1000 requirement)
        host_count = 1500
        hosts = generate_test_hosts(host_count, services_per_host=3)
        
        # Record initial memory usage
        initial_memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        # Mock parser to return large host list
        mock_parser = Mock()
        mock_parser.parse.return_value = hosts
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)
        
        # Mock scan creation
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan
        self.service.scan_repo.update.return_value = mock_scan
        
        # Mock host operations
        self.service.host_repo.get_by_ip_address.return_value = None  # No existing hosts
        self.service.host_repo.create.return_value = Mock(id=uuid4())
        self.service.service_repo.get_by_host_id.return_value = []
        self.service.service_repo.create.return_value = Mock()
        
        # Execute import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="large_scan.xml",
            content='<?xml version="1.0"?><nmaprun>test</nmaprun>',
            tool_type="nmap"
        )
        
        # Record final memory usage
        final_memory_mb = self.process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_memory_mb - initial_memory_mb
        
        # Assertions
        assert result.success is True, "Import should succeed"
        assert result.hosts_imported == host_count, f"Should import all {host_count} hosts"
        
        # Memory increase should be reasonable (< 500MB for 1500 hosts)
        # This validates batch processing is working
        assert memory_increase_mb < 500, \
            f"Memory increase ({memory_increase_mb:.2f}MB) exceeds reasonable limit for {host_count} hosts"
        
        print(f"\n✅ AC #3 PASS: Processed {host_count} hosts successfully")
        print(f"   Memory increase: {memory_increase_mb:.2f}MB")
        print(f"   Hosts imported: {result.hosts_imported}")
        print(f"   Services imported: {result.services_imported}")
        
    def test_ac6_process_100_hosts_under_5_seconds(self):
        """
        AC #6: Process 100 hosts in under 5 seconds
        
        This test validates processing speed meets performance requirements.
        """
        # Generate exactly 100 hosts
        host_count = 100
        hosts = generate_test_hosts(host_count, services_per_host=3)
        
        # Mock parser
        mock_parser = Mock()
        mock_parser.parse.return_value = hosts
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)
        
        # Mock scan creation
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan
        self.service.scan_repo.update.return_value = mock_scan
        
        # Mock host operations
        self.service.host_repo.get_by_ip_address.return_value = None
        self.service.host_repo.create.return_value = Mock(id=uuid4())
        self.service.service_repo.get_by_host_id.return_value = []
        self.service.service_repo.create.return_value = Mock()
        
        # Measure execution time
        start_time = time.time()
        
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="scan_100_hosts.xml",
            content='<?xml version="1.0"?><nmaprun>test</nmaprun>',
            tool_type="nmap"
        )
        
        elapsed_time = time.time() - start_time
        
        # Assertions
        assert result.success is True, "Import should succeed"
        assert result.hosts_imported == host_count, f"Should import all {host_count} hosts"
        assert elapsed_time < 5.0, \
            f"Processing time ({elapsed_time:.2f}s) exceeds 5 second requirement"
        
        print(f"\n✅ AC #6 PASS: Processed {host_count} hosts in {elapsed_time:.2f} seconds")
        print(f"   Processing time: {elapsed_time:.2f}s (requirement: < 5.0s)")
        print(f"   Hosts imported: {result.hosts_imported}")
        print(f"   Services imported: {result.services_imported}")
        
    def test_batch_processing_efficiency(self):
        """
        Test that batch processing works correctly with different batch sizes.
        
        This validates the configurable batch size feature.
        """
        # Test with custom batch size
        custom_batch_size = 25
        self.service = ScanImportService(
            self.session,
            batch_size=custom_batch_size
        )
        
        # Re-mock repositories
        self.service.scan_repo = Mock()
        self.service.host_repo = Mock()
        self.service.service_repo = Mock()
        
        # Generate 75 hosts (should create 3 batches of 25)
        host_count = 75
        hosts = generate_test_hosts(host_count, services_per_host=2)
        
        # Mock parser
        mock_parser = Mock()
        mock_parser.parse.return_value = hosts
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)
        
        # Mock operations
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan
        self.service.scan_repo.update.return_value = mock_scan
        self.service.host_repo.get_by_ip_address.return_value = None
        self.service.host_repo.create.return_value = Mock(id=uuid4())
        self.service.service_repo.get_by_host_id.return_value = []
        self.service.service_repo.create.return_value = Mock()
        
        # Execute import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="batch_test.xml",
            content='<?xml version="1.0"?><nmaprun>test</nmaprun>',
            tool_type="nmap"
        )
        
        # Verify batch size configuration is used
        assert self.service.batch_size == custom_batch_size
        assert result.success is True
        assert result.hosts_imported == host_count
        
        # Verify session.commit() was called for each batch (3 times for 75 hosts / 25 batch size)
        expected_commits = (host_count + custom_batch_size - 1) // custom_batch_size
        assert self.session.commit.call_count == expected_commits, \
            f"Expected {expected_commits} batch commits, got {self.session.commit.call_count}"
        
        print(f"\n✅ Batch processing test PASS")
        print(f"   Batch size: {custom_batch_size}")
        print(f"   Total hosts: {host_count}")
        print(f"   Expected batches: {expected_commits}")
        print(f"   Actual commits: {self.session.commit.call_count}")
        
    def test_memory_efficiency_with_large_services(self):
        """
        Test memory efficiency when processing hosts with many services.
        
        This validates that the batch processing handles high service counts.
        """
        # Generate hosts with many services (10 per host)
        host_count = 500
        services_per_host = 10
        hosts = generate_test_hosts(host_count, services_per_host=services_per_host)
        
        initial_memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        # Mock operations
        mock_parser = Mock()
        mock_parser.parse.return_value = hosts
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)
        
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan
        self.service.scan_repo.update.return_value = mock_scan
        self.service.host_repo.get_by_ip_address.return_value = None
        self.service.host_repo.create.return_value = Mock(id=uuid4())
        self.service.service_repo.get_by_host_id.return_value = []
        self.service.service_repo.create.return_value = Mock()
        
        # Execute import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="high_service_scan.xml",
            content='<?xml version="1.0"?><nmaprun>test</nmaprun>',
            tool_type="nmap"
        )
        
        final_memory_mb = self.process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_memory_mb - initial_memory_mb
        
        # Verify results
        assert result.success is True
        assert result.hosts_imported == host_count
        total_services = host_count * services_per_host
        assert result.services_imported == total_services
        
        # Memory should still be reasonable despite high service count
        assert memory_increase_mb < 400, \
            f"Memory increase ({memory_increase_mb:.2f}MB) too high for {host_count} hosts with {services_per_host} services each"
        
        print(f"\n✅ High service count test PASS")
        print(f"   Hosts: {host_count}")
        print(f"   Services per host: {services_per_host}")
        print(f"   Total services: {total_services}")
        print(f"   Memory increase: {memory_increase_mb:.2f}MB")


class TestConfigurability:
    """Test configurable parameters via environment variables"""
    
    def test_batch_size_environment_variable(self, monkeypatch):
        """Test that batch size can be configured via environment variable"""
        # Set environment variable
        monkeypatch.setenv('SCAN_IMPORT_BATCH_SIZE', '100')
        
        # Reimport to pick up env var (in practice this would be set before app starts)
        import importlib
        import services.scan_import
        importlib.reload(services.scan_import)
        from services import ScanImportService as ReloadedService
        
        # Create service (should use env var default)
        session = Mock()
        service = ReloadedService(session)
        
        assert service.batch_size == 100, "Should use environment variable value"
        
    def test_max_content_size_environment_variable(self, monkeypatch):
        """Test that max raw content size can be configured via environment variable"""
        # Set environment variable
        monkeypatch.setenv('SCAN_IMPORT_MAX_RAW_CONTENT_SIZE', '100000')
        
        # Reimport to pick up env var
        import importlib
        import services.scan_import
        importlib.reload(services.scan_import)
        from services import ScanImportService as ReloadedService
        
        # Create service (should use env var default)
        session = Mock()
        service = ReloadedService(session)
        
        assert service.max_raw_content_size == 100000, "Should use environment variable value"
        
    def test_constructor_parameters_override_defaults(self):
        """Test that constructor parameters override environment defaults"""
        session = Mock()
        custom_batch = 75
        custom_max_size = 75000
        
        service = ScanImportService(
            session,
            batch_size=custom_batch,
            max_raw_content_size=custom_max_size
        )
        
        assert service.batch_size == custom_batch, "Constructor param should override default"
        assert service.max_raw_content_size == custom_max_size, "Constructor param should override default"
