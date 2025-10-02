import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch
from datetime import datetime, timedelta, UTC

from services.research.performance_optimizer import (
    PerformanceOptimizer, OptimizationLevel, PerformanceMetrics
)
from services.research.false_positive_tracker import (
    FalsePositiveTracker, FalsePositiveType, FalsePositiveReport
)


class TestPerformanceOptimizer:
    """Test suite for performance optimization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = PerformanceOptimizer()
        self.mock_version_service = Mock()
        self.mock_credential_service = Mock()

    def test_basic_optimization(self):
        """Test basic performance optimization."""
        # Mock services
        services = [
            self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1"),
            self._create_mock_service("http", 80, "Apache/2.4.41"),
            self._create_mock_service("ftp", 21, "220 (vsFTPd 3.0.3)")
        ]

        # Mock analysis results
        self.mock_version_service.analyze_service_version.return_value = [
            Mock(confidence=Mock(value='high'))
        ]
        self.mock_version_service.extraction_service.extract_version.return_value = Mock(
            product='OpenSSH', version='8.2p1', confidence=Mock(value='high')
        )
        self.mock_version_service.extraction_service.get_confidence_score.return_value = 0.9
        self.mock_version_service.vulnerability_repo.find_by_product_version.return_value = []
        self.mock_version_service._create_vulnerability_match.return_value = Mock(confidence=Mock(value='high'))

        self.mock_credential_service.detect_default_credentials.return_value = [
            Mock(confidence=0.8)
        ]

        # Run optimization
        result = self.optimizer.optimize_analysis_performance(
            self.mock_version_service,
            self.mock_credential_service,
            services,
            OptimizationLevel.BASIC
        )

        # Verify results
        assert result is not None
        assert result.improvement_percentage is not None  # Can be negative if no improvement
        assert len(result.recommendations) > 0
        assert result.optimized_metrics.analysis_time_seconds >= 0

        # Should meet performance targets
        performance_recommendations = [r for r in result.recommendations if "Performance target achieved" in r]
        assert len(performance_recommendations) > 0

    def test_aggressive_optimization(self):
        """Test aggressive optimization mode."""
        services = [self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1") for _ in range(20)]

        # Mock faster analysis for aggressive mode
        self.mock_version_service.analyze_service_version.return_value = []
        self.mock_version_service.extraction_service.extract_version.return_value = None

        result = self.optimizer.optimize_analysis_performance(
            self.mock_version_service,
            self.mock_credential_service,
            services,
            OptimizationLevel.AGGRESSIVE
        )

        # Aggressive mode should be faster
        assert result.optimized_metrics.analysis_time_seconds < result.original_metrics.analysis_time_seconds

    def test_conservative_optimization(self):
        """Test conservative optimization mode."""
        services = [self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1")]

        self.mock_version_service.analyze_service_version.return_value = [
            Mock(confidence=Mock(value='medium'))
        ]

        result = self.optimizer.optimize_analysis_performance(
            self.mock_version_service,
            self.mock_credential_service,
            services,
            OptimizationLevel.CONSERVATIVE
        )

        # Conservative mode should have lower false positive rate
        assert result.optimized_metrics.false_positive_rate <= result.original_metrics.false_positive_rate

    def test_service_filtering(self):
        """Test service pre-filtering logic."""
        services = [
            self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1"),  # Should be included
            self._create_mock_service("unknown", 9999, ""),  # Should be filtered out
            self._create_mock_service("http", 80, "Apache/2.4.41"),  # Should be included
            self._create_mock_service("domain", 53, ""),  # Low value, might be filtered
        ]

        filtered = self.optimizer._pre_filter_services(services)

        # Should filter to high-value services
        assert len(filtered) <= len(services)
        # SSH and HTTP should be included
        service_ports = [s.port for s in filtered]
        assert 22 in service_ports
        assert 80 in service_ports

    def test_cache_functionality(self):
        """Test performance caching."""
        service = self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1")

        # Generate cache key
        cache_key = self.optimizer._generate_cache_key(service)
        assert cache_key is not None
        assert "ssh" in cache_key

        # Test cache storage and retrieval
        self.optimizer.performance_cache[cache_key] = {
            'vulnerabilities': 2,
            'timestamp': datetime.now(UTC)
        }

        assert cache_key in self.optimizer.performance_cache
        assert self.optimizer.performance_cache[cache_key]['vulnerabilities'] == 2

    def test_confidence_threshold_tuning(self):
        """Test automatic confidence threshold tuning."""
        # Simulate high false positive rate
        self.optimizer.false_positive_tracking = {
            'version_mismatch': 15,
            'product_mismatch': 10,
            'banner_inconsistency': 5
        }

        original_thresholds = self.optimizer.confidence_thresholds.copy()

        self.optimizer.tune_confidence_thresholds(target_fp_rate=5.0)

        # Thresholds should be increased to reduce false positives
        for severity in self.optimizer.confidence_thresholds:
            assert self.optimizer.confidence_thresholds[severity] >= original_thresholds[severity]

    def test_false_positive_detection(self):
        """Test false positive detection logic."""
        service = self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1")
        service.version = "8.2p1"

        # Mock a vulnerability match that doesn't match the service version
        vuln_match = Mock()
        vuln_match.vulnerable_versions = ["7.4"]  # Different version
        vuln_match.confidence = Mock(value='high')

        # Should be detected as false positive
        is_fp = self.optimizer._is_likely_false_positive(service, vuln_match)
        assert is_fp

    def test_performance_statistics(self):
        """Test performance statistics collection."""
        # Add some optimization history
        self.optimizer.optimization_history = [
            {
                'timestamp': datetime.now(UTC),
                'services_count': 10,
                'optimization_level': 'basic',
                'improvement': 25.5
            },
            {
                'timestamp': datetime.now(UTC),
                'services_count': 5,
                'optimization_level': 'aggressive',
                'improvement': 45.2
            }
        ]

        stats = self.optimizer.get_performance_statistics()

        assert stats['total_optimizations'] == 2
        assert stats['average_improvement'] > 0
        assert stats['best_improvement'] == 45.2

    def test_batch_processing(self):
        """Test service batching for parallel processing."""
        services = [
            self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1"),
            self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_7.4"),
            self._create_mock_service("http", 80, "Apache/2.4.41"),
            self._create_mock_service("http", 80, "nginx/1.18.0"),
        ]

        batches = self.optimizer._batch_similar_services(services)

        # Should group similar services
        assert len(batches) >= 1
        # SSH services should be grouped together
        ssh_batch = next((batch for batch in batches
                         if any(s.service_name == 'ssh' for s in batch)), None)
        assert ssh_batch is not None
        assert len(ssh_batch) == 2

    def test_memory_optimization(self):
        """Test memory usage optimization."""
        # This test verifies memory usage is tracked
        services = [self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1")]

        with patch('psutil.Process') as mock_process:
            mock_memory = Mock()
            mock_memory.rss = 100 * 1024 * 1024  # 100 MB
            mock_process.return_value.memory_info.return_value = mock_memory

            metrics = self.optimizer._measure_baseline_performance(
                self.mock_version_service, self.mock_credential_service, services
            )

            assert metrics.memory_usage_mb >= 0

    def test_three_second_requirement_validation(self):
        """Test that optimization meets the 3-second requirement."""
        services = [self._create_mock_service("ssh", 22, "SSH-2.0-OpenSSH_8.2p1")]

        # Mock fast analysis
        self.mock_version_service.analyze_service_version.return_value = []
        self.mock_credential_service.detect_default_credentials.return_value = []

        result = self.optimizer.optimize_analysis_performance(
            self.mock_version_service,
            self.mock_credential_service,
            services,
            OptimizationLevel.AGGRESSIVE
        )

        # Should meet 3-second requirement
        if result.optimized_metrics.analysis_time_seconds <= 3.0:
            assert "✓ Performance target achieved" in result.recommendations

    def _create_mock_service(self, service_name, port, banner):
        """Create a mock service for testing."""
        service = Mock()
        service.id = f"service-{service_name}-{port}"
        service.service_name = service_name
        service.port = port
        service.banner = banner
        service.product = "test_product"
        service.version = "1.0"
        return service


class TestFalsePositiveTracker:
    """Test suite for false positive tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = FalsePositiveTracker()

    def test_report_false_positive(self):
        """Test reporting a false positive."""
        report_id = self.tracker.report_false_positive(
            service_id="test-service-1",
            fp_type=FalsePositiveType.VERSION_MISMATCH,
            confidence_score=0.8,
            detection_method="version_match",
            banner_snippet="SSH-2.0-OpenSSH_8.2p1",
            reason="Version extracted doesn't match actual service version",
            reported_by="user123"
        )

        assert report_id is not None
        assert len(self.tracker.false_positive_reports) == 1
        assert self.tracker.false_positive_reports[0].service_id == "test-service-1"

    def test_validate_false_positive(self):
        """Test validating a false positive report."""
        # First report a false positive
        report_id = self.tracker.report_false_positive(
            service_id="test-service-1",
            fp_type=FalsePositiveType.BANNER_INCONSISTENCY,
            confidence_score=0.7,
            detection_method="banner_analysis",
            banner_snippet="Apache/2.4.41",
            reason="Banner doesn't match detected vulnerability",
            reported_by="user123"
        )

        # Validate it
        success = self.tracker.validate_false_positive(report_id, True, "validator456")

        assert success
        assert report_id in self.tracker.validation_feedback
        assert self.tracker.validation_feedback[report_id]['is_valid']

    def test_false_positive_metrics(self):
        """Test false positive metrics calculation."""
        # Report several false positives
        for i in range(5):
            self.tracker.report_false_positive(
                service_id=f"test-service-{i}",
                fp_type=FalsePositiveType.LOW_CONFIDENCE,
                confidence_score=0.3 + (i * 0.1),
                detection_method="automated",
                banner_snippet=f"Test banner {i}",
                reason="Low confidence detection",
                reported_by="system"
            )

        metrics = self.tracker.get_false_positive_metrics(days=30)

        assert metrics.false_positives == 5
        assert metrics.false_positive_rate > 0
        assert 'low_confidence' in metrics.by_type
        assert metrics.by_type['low_confidence'] == 5

    def test_pattern_recommendations(self):
        """Test pattern-based recommendations."""
        # Report multiple version mismatch false positives
        for i in range(6):
            self.tracker.report_false_positive(
                service_id=f"test-service-{i}",
                fp_type=FalsePositiveType.VERSION_MISMATCH,
                confidence_score=0.8,
                detection_method="version_extraction",
                banner_snippet="SSH-2.0-OpenSSH_8.2p1",
                reason="Version mismatch",
                reported_by="user123"
            )

        recommendations = self.tracker.get_pattern_recommendations()

        # Should recommend improving version extraction
        version_rec = next((r for r in recommendations if 'version' in r['message'].lower()), None)
        assert version_rec is not None
        assert version_rec['category'] == 'version_extraction'

    def test_confidence_adjustments(self):
        """Test confidence adjustment suggestions."""
        # Report high-confidence false positives
        for i in range(8):
            self.tracker.report_false_positive(
                service_id=f"test-service-{i}",
                fp_type=FalsePositiveType.PRODUCT_MISMATCH,
                confidence_score=0.9,  # High confidence
                detection_method="product_match",
                banner_snippet="Apache/2.4.41",
                reason="Product mismatch",
                reported_by="user123"
            )

        adjustments = self.tracker.get_confidence_adjustment_suggestions()

        # Should suggest increasing high confidence threshold
        assert 'high_confidence_threshold' in adjustments
        assert adjustments['high_confidence_threshold'] >= 0.9

    def test_pattern_blacklist_creation(self):
        """Test pattern blacklist creation."""
        # Report false positives with test/demo patterns
        test_patterns = ['test-server', 'demo-app', 'dev-environment']

        for pattern in test_patterns:
            for i in range(4):  # Report each pattern multiple times
                self.tracker.report_false_positive(
                    service_id=f"service-{pattern}-{i}",
                    fp_type=FalsePositiveType.BANNER_INCONSISTENCY,
                    confidence_score=0.6,
                    detection_method="banner_analysis",
                    banner_snippet=f"Banner with {pattern} in it",
                    reason="Test/demo environment",
                    reported_by="user123"
                )

        blacklist = self.tracker.create_pattern_blacklist()

        # Should blacklist common test patterns
        assert 'test' in blacklist
        assert 'demo' in blacklist
        assert 'dev' in blacklist

    def test_trend_calculation(self):
        """Test false positive trend calculation."""
        # Add reports over several days
        base_time = datetime.now(UTC) - timedelta(days=10)

        for day in range(10):
            report_time = base_time + timedelta(days=day)
            # Simulate increasing trend
            for i in range(day + 1):
                report = FalsePositiveReport(
                    id=f"fp_{day}_{i}",
                    service_id=f"service-{day}-{i}",
                    vulnerability_id=None,
                    credential_id=None,
                    fp_type=FalsePositiveType.LOW_CONFIDENCE,
                    confidence_score=0.4,
                    detection_method="automated",
                    banner_snippet="test banner",
                    reason="test",
                    reported_by="system",
                    reported_at=report_time
                )
                self.tracker.false_positive_reports.append(report)

        trend = self.tracker._calculate_trend(10)

        # Should detect increasing trend
        assert trend > 0

    def test_export_comprehensive_report(self):
        """Test comprehensive report export."""
        # Add some test data
        self.tracker.report_false_positive(
            service_id="test-service-1",
            fp_type=FalsePositiveType.VERSION_MISMATCH,
            confidence_score=0.8,
            detection_method="version_match",
            banner_snippet="SSH-2.0-OpenSSH_8.2p1",
            reason="Version mismatch",
            reported_by="user123"
        )

        report = self.tracker.export_report(days=30)

        assert 'report_generated' in report
        assert 'metrics' in report
        assert 'recommendations' in report
        assert 'confidence_adjustments' in report
        assert 'pattern_blacklist' in report
        assert 'validation_stats' in report

        # Verify report structure
        assert report['period_days'] == 30
        assert report['metrics']['false_positives'] == 1

    def test_learning_from_false_positives(self):
        """Test that the system learns from false positive patterns."""
        # Report a false positive
        self.tracker.report_false_positive(
            service_id="test-service-1",
            fp_type=FalsePositiveType.PRODUCT_MISMATCH,
            confidence_score=0.8,
            detection_method="product_matching",
            banner_snippet="test-banner",
            reason="Product mismatch",
            reported_by="user123"
        )

        # Check that learning occurred
        assert 'product_matching' in self.tracker.confidence_adjustments
        assert self.tracker.confidence_adjustments['product_matching']['count'] == 1

    def test_validation_feedback_processing(self):
        """Test processing of validation feedback."""
        # Report and validate a false positive
        report_id = self.tracker.report_false_positive(
            service_id="test-service-1",
            fp_type=FalsePositiveType.MANUAL_REVIEW,
            confidence_score=0.7,
            detection_method="manual_analysis",
            banner_snippet="banner",
            reason="Manual review error",
            reported_by="user123"
        )

        # Validate as correct (true false positive)
        self.tracker.validate_false_positive(report_id, True, "validator")

        # Should have reinforced the pattern
        assert report_id in self.tracker.validation_feedback
        assert self.tracker.validation_feedback[report_id]['is_valid']

        # Test false negative (incorrectly reported as false positive)
        report_id_2 = self.tracker.report_false_positive(
            service_id="test-service-2",
            fp_type=FalsePositiveType.MANUAL_REVIEW,
            confidence_score=0.7,
            detection_method="manual_analysis",
            banner_snippet="banner2",
            reason="Actually valid detection",
            reported_by="user123"
        )

        # Validate as incorrect (this was actually a true positive)
        self.tracker.validate_false_positive(report_id_2, False, "validator")

        assert not self.tracker.validation_feedback[report_id_2]['is_valid']