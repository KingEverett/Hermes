"""
Tests for ValidationService confidence scoring and validation workflows.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from services.validation_service import ValidationService
from models import ServiceVulnerability, ConfidenceLevel


class TestConfidenceScoring:
    """Tests for confidence scoring algorithm"""

    def test_calculate_confidence_score_high_quality(self):
        """Test confidence calculation with high-quality data"""
        service = ValidationService(None)

        # High reliability, fresh data, validated
        score, factors = service.calculate_confidence_score(
            source_reliability=1.0,
            data_age_days=5,
            validation_status='approved'
        )

        assert score >= 0.9
        assert factors['source_reliability'] == 1.0
        assert factors['data_freshness'] == 1.0
        assert factors['validation_status'] == 1.0

    def test_calculate_confidence_score_medium_quality(self):
        """Test confidence calculation with medium-quality data"""
        service = ValidationService(None)

        # Medium reliability, moderate age, pending validation
        score, factors = service.calculate_confidence_score(
            source_reliability=0.8,
            data_age_days=20,
            validation_status='pending'
        )

        assert 0.5 <= score < 0.8
        assert factors['data_freshness'] == 0.8

    def test_calculate_confidence_score_low_quality(self):
        """Test confidence calculation with low-quality data"""
        service = ValidationService(None)

        # Low reliability, old data, needs review
        score, factors = service.calculate_confidence_score(
            source_reliability=0.3,
            data_age_days=100,
            validation_status='needs_review'
        )

        assert score < 0.5
        assert factors['data_freshness'] == 0.4
        assert factors['validation_status'] == 0.3

    def test_calculate_confidence_score_rejected(self):
        """Test confidence score for rejected findings"""
        service = ValidationService(None)

        score, factors = service.calculate_confidence_score(
            source_reliability=0.9,
            data_age_days=10,
            validation_status='rejected'
        )

        # Rejected status should heavily impact score
        assert score < 0.7
        assert factors['validation_status'] == 0.0

    def test_get_confidence_level_mapping(self):
        """Test confidence score to level mapping"""
        service = ValidationService(None)

        assert service.get_confidence_level(0.9) == ConfidenceLevel.HIGH
        assert service.get_confidence_level(0.8) == ConfidenceLevel.HIGH
        assert service.get_confidence_level(0.7) == ConfidenceLevel.MEDIUM
        assert service.get_confidence_level(0.5) == ConfidenceLevel.MEDIUM
        assert service.get_confidence_level(0.4) == ConfidenceLevel.LOW
        assert service.get_confidence_level(0.0) == ConfidenceLevel.LOW

    def test_data_freshness_scoring(self):
        """Test data freshness component of scoring"""
        service = ValidationService(None)

        # < 7 days
        score_fresh, _ = service.calculate_confidence_score(0.5, 5, 'pending')
        # 7-30 days
        score_recent, _ = service.calculate_confidence_score(0.5, 20, 'pending')
        # 30-90 days
        score_old, _ = service.calculate_confidence_score(0.5, 60, 'pending')
        # > 90 days
        score_stale, _ = service.calculate_confidence_score(0.5, 100, 'pending')

        assert score_fresh > score_recent > score_old > score_stale

    def test_source_reliability_scores(self):
        """Test source reliability score mappings"""
        service = ValidationService(None)

        assert service.get_source_reliability_score('nvd_api') == 1.0
        assert service.get_source_reliability_score('exploitdb_verified') == 0.9
        assert service.get_source_reliability_score('cached_data') == 0.8
        assert service.get_source_reliability_score('version_heuristics') == 0.5
        assert service.get_source_reliability_score('manual_links') == 0.3
        assert service.get_source_reliability_score('unknown_source') == 0.5


class TestReviewQueueLogic:
    """Tests for validation queue logic"""

    def test_should_add_to_queue_high_cvss(self):
        """Test that high CVSS scores trigger queue addition"""
        service = ValidationService(None)

        vuln = ServiceVulnerability(
            id=uuid4(),
            service_id=uuid4(),
            vulnerability_id=uuid4(),
            confidence_score=0.8
        )

        assert service.should_add_to_review_queue(vuln, cvss_score=7.5) is True
        assert service.should_add_to_review_queue(vuln, cvss_score=9.0) is True

    def test_should_add_to_queue_low_confidence(self):
        """Test that low confidence triggers queue addition"""
        service = ValidationService(None)

        vuln = ServiceVulnerability(
            id=uuid4(),
            service_id=uuid4(),
            vulnerability_id=uuid4(),
            confidence_score=0.5
        )

        assert service.should_add_to_review_queue(vuln, cvss_score=3.0) is True

    def test_should_not_add_to_queue_high_confidence_low_severity(self):
        """Test that high confidence + low severity doesn't trigger queue"""
        service = ValidationService(None)

        vuln = ServiceVulnerability(
            id=uuid4(),
            service_id=uuid4(),
            vulnerability_id=uuid4(),
            confidence_score=0.9
        )

        assert service.should_add_to_review_queue(vuln, cvss_score=3.0) is False


class TestValidationDecisionProcessing:
    """Tests for validation decision logic"""

    def test_process_validation_decision_approve(self):
        """Test approval decision processing"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass

    def test_process_validation_decision_reject(self):
        """Test rejection decision processing"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass

    def test_process_validation_decision_override(self):
        """Test override decision processing"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass
