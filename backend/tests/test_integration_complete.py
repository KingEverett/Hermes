import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC
import time

from services.research.version_analysis import VersionAnalysisService, VersionMatch, ConfidenceLevel
from services.research.credential_detection import DefaultCredentialDetectionService, CredentialRisk
from services.research.performance_optimizer import PerformanceOptimizer, OptimizationLevel
from services.research.false_positive_tracker import FalsePositiveTracker, FalsePositiveType
from repositories.vulnerability_repository import VulnerabilityRepository
from repositories.service_vulnerability_repository import ServiceVulnerabilityRepository
from repositories.review_queue_repository import ReviewQueueRepository
from repositories.default_credential_repository import DefaultCredentialRepository
from models.vulnerability import Vulnerability, Severity
from models.service_vulnerability import ServiceVulnerability, ValidationMethod
from models.review_queue import ReviewQueue, ReviewStatus
from models.default_credential import DefaultCredential


class TestCompleteWorkflow:
    """Integration tests for the complete vulnerability analysis workflow."""

    def setup_method(self):
        """Set up comprehensive test fixtures."""
        # Mock database session
        self.mock_db = Mock()

        # Create mock repositories
        self.vuln_repo = Mock(spec=VulnerabilityRepository)
        self.service_vuln_repo = Mock(spec=ServiceVulnerabilityRepository)
        self.review_queue_repo = Mock(spec=ReviewQueueRepository)
        self.credential_repo = Mock(spec=DefaultCredentialRepository)

        # Create services
        self.version_service = VersionAnalysisService(
            vulnerability_repo=self.vuln_repo,
            service_vuln_repo=self.service_vuln_repo,
            review_queue_repo=self.review_queue_repo
        )
        self.credential_service = DefaultCredentialDetectionService()
        self.optimizer = PerformanceOptimizer()
        self.fp_tracker = FalsePositiveTracker()

    def test_complete_ssh_analysis_workflow(self):
        """Test complete analysis workflow for SSH service."""
        # Create test service
        service = Mock()
        service.id = "ssh-test-service"
        service.service_name = "ssh"
        service.banner = "SSH-2.0-OpenSSH_7.4"
        service.product = "OpenSSH"
        service.version = "7.4"
        service.port = 22

        # Mock vulnerability data
        mock_vulnerability = Mock()
        mock_vulnerability.id = "vuln-1"
        mock_vulnerability.cve_id = "CVE-2024-1234"
        mock_vulnerability.severity = Severity.HIGH
        mock_vulnerability.cvss_score = 7.5
        mock_vulnerability.description = "SSH vulnerability"
        mock_vulnerability.product = "OpenSSH"

        # Configure repository mocks
        self.vuln_repo.find_by_product_version.return_value = [mock_vulnerability]
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()
        self.review_queue_repo.find_by_service_and_vulnerability.return_value = None
        self.review_queue_repo.create.return_value = Mock()

        # Step 1: Version analysis
        version_results = self.version_service.analyze_service_version(service)
        assert len(version_results) > 0
        assert version_results[0].cve_id == "CVE-2024-1234"

        # Step 2: Complete analysis with review queue
        complete_results = self.version_service.analyze_service_complete(service)
        assert complete_results['vulnerabilities_found'] > 0

        # Step 3: Credential analysis
        credential_results = self.credential_service.analyze_service_credentials(service)
        assert credential_results['service_type'] == 'ssh'
        assert credential_results['credentials_found'] > 0

        # Step 4: Performance validation
        perf_results = self.version_service.validate_performance(service)
        assert perf_results['meets_3_second_requirement']

        # Verify repository calls
        self.vuln_repo.find_by_product_version.assert_called_with("OpenSSH", "7.4")
        self.service_vuln_repo.create.assert_called()

    def test_high_volume_analysis_performance(self):
        """Test performance with high volume of services."""
        # Create 100 test services
        services = []
        for i in range(100):
            service = Mock()
            service.id = f"service-{i}"
            service.service_name = "ssh" if i % 2 == 0 else "http"
            service.banner = f"SSH-2.0-OpenSSH_8.{i % 10}" if i % 2 == 0 else f"Apache/2.4.{i % 50}"
            service.product = "OpenSSH" if i % 2 == 0 else "Apache httpd"
            service.port = 22 if i % 2 == 0 else 80
            services.append(service)

        # Mock repository responses for performance
        self.vuln_repo.find_by_product_version.return_value = []

        # Measure performance with optimization
        start_time = time.time()

        # Run optimized analysis
        optimizer_result = self.optimizer.optimize_analysis_performance(
            self.version_service,
            self.credential_service,
            services,
            OptimizationLevel.AGGRESSIVE
        )

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 30.0  # Should complete 100 services in under 30 seconds
        assert optimizer_result.optimized_metrics.analysis_time_seconds < 10.0
        assert optimizer_result.optimized_metrics.false_positive_rate <= 10.0

    def test_false_positive_feedback_loop(self):
        """Test false positive feedback and learning system."""
        # Report several false positives
        fp_reports = []

        # Version mismatch false positives
        for i in range(5):
            report_id = self.fp_tracker.report_false_positive(
                service_id=f"service-{i}",
                fp_type=FalsePositiveType.VERSION_MISMATCH,
                confidence_score=0.8,
                detection_method="version_extraction",
                banner_snippet=f"SSH-2.0-OpenSSH_8.{i}",
                reason="Version extraction mismatch",
                reported_by="tester"
            )
            fp_reports.append(report_id)

        # Validate some reports
        for i, report_id in enumerate(fp_reports[:3]):
            self.fp_tracker.validate_false_positive(report_id, True, f"validator-{i}")

        # Get recommendations
        recommendations = self.fp_tracker.get_pattern_recommendations()

        # Should recommend version extraction improvements
        version_recommendations = [r for r in recommendations if 'version' in r['message'].lower()]
        assert len(version_recommendations) > 0

        # Test confidence adjustments
        adjustments = self.fp_tracker.get_confidence_adjustment_suggestions()
        assert len(adjustments) > 0

        # Test metrics
        metrics = self.fp_tracker.get_false_positive_metrics(days=7)
        assert metrics.false_positives == 5
        assert metrics.by_type['version_mismatch'] == 5

    def test_review_queue_workflow(self):
        """Test complete review queue workflow."""
        # Create mock review items
        review_items = []
        for i in range(10):
            item = Mock()
            item.id = f"review-{i}"
            item.service_id = f"service-{i}"
            item.vulnerability_id = f"vuln-{i}"
            item.status = ReviewStatus.PENDING
            item.confidence = ConfidenceLevel.MEDIUM if i % 2 == 0 else ConfidenceLevel.LOW
            item.priority = "high" if i < 3 else "medium"
            review_items.append(item)

        # Mock repository responses
        self.review_queue_repo.find_pending.return_value = review_items
        self.review_queue_repo.get_next_for_review.return_value = review_items[0]
        self.review_queue_repo.assign_to_reviewer.return_value = True
        self.review_queue_repo.approve_item.return_value = True

        # Test workflow
        # 1. Get pending items
        pending = self.review_queue_repo.find_pending()
        assert len(pending) == 10

        # 2. Get next item for review
        next_item = self.review_queue_repo.get_next_for_review()
        assert next_item.id == "review-0"

        # 3. Assign to reviewer
        success = self.review_queue_repo.assign_to_reviewer("review-0", "reviewer-1")
        assert success

        # 4. Approve item
        success = self.review_queue_repo.approve_item("review-0", "reviewer-1", "Looks valid")
        assert success

    def test_end_to_end_vulnerability_detection(self):
        """Test end-to-end vulnerability detection with real-like data."""
        # Create comprehensive test service
        service = Mock()
        service.id = "e2e-test-service"
        service.service_name = "http"
        service.banner = "HTTP/1.1 200 OK\r\nServer: Apache/2.2.14 (Win32)\r\n"
        service.product = "Apache httpd"
        service.version = "2.2.14"
        service.port = 80

        # Mock known vulnerable version
        mock_vulnerability = Mock()
        mock_vulnerability.id = "vuln-apache-2214"
        mock_vulnerability.cve_id = "CVE-2020-1927"
        mock_vulnerability.severity = Severity.HIGH
        mock_vulnerability.cvss_score = 6.4
        mock_vulnerability.description = "Apache HTTP Server vulnerability"
        mock_vulnerability.product = "Apache httpd"

        # Configure mocks
        self.vuln_repo.find_by_product_version.return_value = [mock_vulnerability]
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()

        # Run complete analysis
        start_time = time.time()

        # Version analysis
        version_results = self.version_service.analyze_service_version(service)

        # Credential analysis
        credential_results = self.credential_service.analyze_service_credentials(service)

        end_time = time.time()
        analysis_time = end_time - start_time

        # Assertions
        assert len(version_results) == 1
        assert version_results[0].cve_id == "CVE-2020-1927"
        assert version_results[0].severity == "high"

        assert credential_results['service_type'] == 'http'
        assert credential_results['product'] == 'Apache httpd'

        # Performance requirement
        assert analysis_time < 3.0

    def test_confidence_scoring_accuracy(self):
        """Test confidence scoring accuracy across different scenarios."""
        test_cases = [
            # High confidence cases
            {
                'service_name': 'ssh',
                'banner': 'SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5',
                'port': 22,
                'expected_confidence': 'high'
            },
            {
                'service_name': 'http',
                'banner': 'Server: Apache/2.4.41 (Ubuntu)',
                'port': 80,
                'expected_confidence': 'high'
            },
            # Medium confidence cases
            {
                'service_name': 'unknown',
                'banner': 'SSH-2.0-libssh_0.8.7',
                'port': 22,
                'expected_confidence': 'medium'
            },
            # Low confidence cases
            {
                'service_name': 'unknown',
                'banner': 'Generic service v1.0',
                'port': 9999,
                'expected_confidence': None  # Should not detect anything
            }
        ]

        for case in test_cases:
            service = Mock()
            service.service_name = case['service_name']
            service.banner = case['banner']
            service.port = case['port']

            # Extract version
            version_match = self.version_service.extraction_service.extract_version(
                service.banner, service.service_name
            )

            if case['expected_confidence'] is None:
                assert version_match is None
            else:
                assert version_match is not None
                assert version_match.confidence.value == case['expected_confidence']

    def test_memory_and_resource_management(self):
        """Test memory usage and resource management."""
        # Create large dataset
        services = []
        for i in range(500):
            service = Mock()
            service.id = f"large-test-{i}"
            service.service_name = "ssh"
            service.banner = f"SSH-2.0-OpenSSH_8.{i % 10}p{i % 5}"
            service.port = 22
            services.append(service)

        # Mock minimal responses to focus on resource management
        self.vuln_repo.find_by_product_version.return_value = []

        # Test with caching enabled
        initial_cache_size = len(self.optimizer.performance_cache)

        result = self.optimizer.optimize_analysis_performance(
            self.version_service,
            self.credential_service,
            services[:50],  # Process subset
            OptimizationLevel.BASIC
        )

        # Cache should have grown
        final_cache_size = len(self.optimizer.performance_cache)
        assert final_cache_size > initial_cache_size

        # Clear cache and verify
        self.optimizer.clear_cache()
        assert len(self.optimizer.performance_cache) == 0

    def test_error_handling_and_resilience(self):
        """Test error handling and system resilience."""
        # Test with malformed service data
        problematic_services = [
            Mock(id="bad-1", service_name=None, banner=None, port=None),
            Mock(id="bad-2", service_name="", banner="", port=0),
            Mock(id="bad-3", service_name="test", banner="malformed\x00\x01", port=-1),
        ]

        # Should handle errors gracefully
        for service in problematic_services:
            try:
                # Version analysis should not crash
                version_results = self.version_service.analyze_service_version(service)
                assert isinstance(version_results, list)  # Should return empty list, not crash

                # Credential analysis should not crash
                credential_results = self.credential_service.analyze_service_credentials(service)
                assert isinstance(credential_results, dict)  # Should return valid structure

            except Exception as e:
                pytest.fail(f"Analysis should handle malformed data gracefully, but got: {e}")

        # Test with repository errors
        self.vuln_repo.find_by_product_version.side_effect = Exception("Database error")

        service = Mock()
        service.id = "test-resilience"
        service.service_name = "ssh"
        service.banner = "SSH-2.0-OpenSSH_8.2p1"
        service.port = 22

        # Should handle database errors gracefully
        version_results = self.version_service.analyze_service_version(service)
        assert version_results == []  # Should return empty list on error

    def test_concurrent_analysis_simulation(self):
        """Simulate concurrent analysis scenarios."""
        # Create services for different "users"
        user_services = {
            'user1': [Mock(id=f"u1-svc-{i}", service_name="ssh", banner="SSH-2.0-OpenSSH_8.2p1", port=22) for i in range(5)],
            'user2': [Mock(id=f"u2-svc-{i}", service_name="http", banner="Apache/2.4.41", port=80) for i in range(3)],
            'user3': [Mock(id=f"u3-svc-{i}", service_name="ftp", banner="220 (vsFTPd 3.0.3)", port=21) for i in range(2)]
        }

        # Mock responses
        self.vuln_repo.find_by_product_version.return_value = []

        # Simulate concurrent analysis
        results = {}
        for user, services in user_services.items():
            start_time = time.time()

            user_results = []
            for service in services:
                version_results = self.version_service.analyze_service_version(service)
                credential_results = self.credential_service.analyze_service_credentials(service)
                user_results.append({
                    'version_results': version_results,
                    'credential_results': credential_results
                })

            end_time = time.time()
            results[user] = {
                'results': user_results,
                'time': end_time - start_time,
                'service_count': len(services)
            }

        # Verify all users got results
        assert len(results) == 3
        for user, data in results.items():
            assert len(data['results']) == data['service_count']
            assert data['time'] < 5.0  # Should complete quickly

    def test_comprehensive_statistics_collection(self):
        """Test comprehensive statistics collection across all components."""
        # Add test data to various components

        # False positive tracker
        for i in range(10):
            self.fp_tracker.report_false_positive(
                service_id=f"stats-service-{i}",
                fp_type=FalsePositiveType.VERSION_MISMATCH if i % 2 == 0 else FalsePositiveType.LOW_CONFIDENCE,
                confidence_score=0.5 + (i * 0.05),
                detection_method="automated",
                banner_snippet=f"test banner {i}",
                reason="test case",
                reported_by="test_suite"
            )

        # Performance optimizer
        self.optimizer.optimization_history = [
            {
                'timestamp': datetime.now(UTC),
                'services_count': 50,
                'optimization_level': 'basic',
                'improvement': 25.0
            },
            {
                'timestamp': datetime.now(UTC),
                'services_count': 100,
                'optimization_level': 'aggressive',
                'improvement': 45.0
            }
        ]

        # Collect statistics
        fp_stats = self.fp_tracker.get_false_positive_metrics(days=30)
        perf_stats = self.optimizer.get_performance_statistics()
        cred_stats = self.credential_service.get_credential_statistics()

        # Verify comprehensive statistics
        assert fp_stats.false_positives == 10
        assert len(fp_stats.by_type) >= 2

        assert perf_stats['total_optimizations'] == 2
        assert perf_stats['average_improvement'] == 35.0

        assert cred_stats['total_credentials'] > 0
        assert 'by_service_type' in cred_stats

    def test_system_integration_validation(self):
        """Final integration test to validate entire system."""
        # Create realistic test scenario
        test_services = [
            # Vulnerable SSH service
            Mock(
                id="integration-ssh",
                service_name="ssh",
                banner="SSH-2.0-OpenSSH_7.4",
                product="OpenSSH",
                version="7.4",
                port=22
            ),
            # Web server with potential issues
            Mock(
                id="integration-web",
                service_name="http",
                banner="Server: Apache/2.2.14",
                product="Apache httpd",
                version="2.2.14",
                port=80
            ),
            # Database with default credentials
            Mock(
                id="integration-db",
                service_name="mysql",
                banner="5.7.10-MySQL",
                product="MySQL",
                version="5.7.10",
                port=3306
            )
        ]

        # Mock vulnerabilities for older versions
        mock_ssh_vuln = Mock(
            id="ssh-vuln", cve_id="CVE-2018-15473", severity=Severity.MEDIUM,
            cvss_score=5.3, description="SSH user enumeration"
        )
        mock_apache_vuln = Mock(
            id="apache-vuln", cve_id="CVE-2017-7679", severity=Severity.HIGH,
            cvss_score=7.5, description="Apache mod_mime buffer overflow"
        )

        def mock_vuln_lookup(product, version):
            if "OpenSSH" in product and "7.4" in version:
                return [mock_ssh_vuln]
            elif "Apache" in product and "2.2.14" in version:
                return [mock_apache_vuln]
            return []

        self.vuln_repo.find_by_product_version.side_effect = mock_vuln_lookup
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()

        # Run complete system test
        total_vulnerabilities = 0
        total_credentials = 0
        analysis_times = []

        for service in test_services:
            start_time = time.time()

            # Full analysis workflow
            version_results = self.version_service.analyze_service_complete(service)
            credential_results = self.credential_service.analyze_service_credentials(service)

            end_time = time.time()
            analysis_time = end_time - start_time
            analysis_times.append(analysis_time)

            total_vulnerabilities += version_results['vulnerabilities_found']
            total_credentials += credential_results['credentials_found']

        # System-level assertions
        assert total_vulnerabilities >= 2  # Should find SSH and Apache vulnerabilities
        assert total_credentials >= 1  # Should find MySQL default credentials
        assert all(t < 3.0 for t in analysis_times)  # All analyses under 3 seconds
        assert sum(analysis_times) < 10.0  # Total time reasonable

        # Verify repository interactions
        assert self.vuln_repo.find_by_product_version.call_count >= 3
        assert self.service_vuln_repo.create.call_count >= 2

        print(f"Integration test completed successfully:")
        print(f"  - Total vulnerabilities found: {total_vulnerabilities}")
        print(f"  - Total credentials found: {total_credentials}")
        print(f"  - Average analysis time: {sum(analysis_times)/len(analysis_times):.3f}s")
        print(f"  - All performance targets met: ✓")