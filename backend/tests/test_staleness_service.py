"""
Tests for StalenessDetectionService.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.staleness_service import StalenessDetectionService


class TestStalenessDetection:
    """Tests for staleness detection logic"""

    def test_is_stale_never_refreshed(self):
        """Test that never-refreshed data is considered stale"""
        service = StalenessDetectionService(None)

        is_stale, reason = service.is_stale(None, 30)

        assert is_stale is True
        assert reason == "Never refreshed"

    def test_is_stale_fresh_data(self):
        """Test that recently refreshed data is not stale"""
        service = StalenessDetectionService(None)
        recent_time = datetime.utcnow() - timedelta(days=5)

        is_stale, reason = service.is_stale(recent_time, 30)

        assert is_stale is False
        assert reason is None

    def test_is_stale_old_data(self):
        """Test that old data is correctly identified as stale"""
        service = StalenessDetectionService(None)
        old_time = datetime.utcnow() - timedelta(days=45)

        is_stale, reason = service.is_stale(old_time, 30)

        assert is_stale is True
        assert "45 days old" in reason
        assert "TTL: 30 days" in reason

    def test_is_stale_boundary_condition(self):
        """Test staleness at exact TTL boundary"""
        service = StalenessDetectionService(None)
        boundary_time = datetime.utcnow() - timedelta(days=30)

        is_stale, reason = service.is_stale(boundary_time, 30)

        # Should not be stale at exactly TTL (30 days, not > 30 days)
        assert is_stale is False

    def test_configure_ttl(self):
        """Test TTL configuration"""
        service = StalenessDetectionService(None)

        # Default values
        assert service.cve_ttl_days == 30
        assert service.exploit_ttl_days == 7

        # Configure custom values
        service.configure_ttl(cve_ttl_days=60, exploit_ttl_days=14)

        assert service.cve_ttl_days == 60
        assert service.exploit_ttl_days == 14

    def test_default_ttl_values(self):
        """Test default TTL constants"""
        service = StalenessDetectionService(None)

        assert service.DEFAULT_CVE_TTL == 30
        assert service.DEFAULT_EXPLOIT_TTL == 7


class TestStalenessStatistics:
    """Tests for staleness statistics calculation"""

    def test_get_staleness_statistics_empty(self):
        """Test statistics with no vulnerabilities"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass

    def test_get_staleness_statistics_with_data(self):
        """Test statistics calculation with sample data"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass


class TestRefreshTrigger:
    """Tests for refresh triggering logic"""

    def test_trigger_refresh_returns_task_info(self):
        """Test that trigger_refresh returns appropriate task info"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass

    def test_trigger_refresh_not_found(self):
        """Test refresh trigger for non-existent vulnerability"""
        # This would require database mocking for full test
        # Placeholder for integration testing
        pass
