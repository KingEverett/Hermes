"""
Test suite for fallback service and mechanisms.

This module validates the fallback functionality when APIs are unavailable:
- Manual research link generation
- Cached data fallback
- Alternative API selection
- Degraded service mode
- Provider status monitoring
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from services.config.fallback_service import (
    FallbackService,
    FallbackType,
    FallbackResult
)
from services.config.api_configuration import ApiConfigurationService
from models.api_configuration import ApiProvider, HealthStatus


class TestFallbackService:
    """Test cases for FallbackService core functionality"""

    @pytest.fixture
    def mock_api_config_service(self):
        """Create mock API configuration service"""
        mock_service = MagicMock(spec=ApiConfigurationService)
        return mock_service

    @pytest.fixture
    def fallback_service(self, mock_api_config_service):
        """Create FallbackService instance for testing"""
        return FallbackService(mock_api_config_service)

    @pytest.mark.asyncio
    async def test_check_api_availability_healthy(self, fallback_service, mock_api_config_service):
        """Test checking API availability when provider is healthy"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.HEALTHY.value,
            "provider": "nvd"
        }]

        result = await fallback_service.check_api_availability(ApiProvider.NVD)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_api_availability_degraded(self, fallback_service, mock_api_config_service):
        """Test checking API availability when provider is degraded"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.DEGRADED.value,
            "provider": "nvd"
        }]

        result = await fallback_service.check_api_availability(ApiProvider.NVD)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_api_availability_down(self, fallback_service, mock_api_config_service):
        """Test checking API availability when provider is down"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.DOWN.value,
            "provider": "nvd"
        }]

        result = await fallback_service.check_api_availability(ApiProvider.NVD)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_api_availability_no_status(self, fallback_service, mock_api_config_service):
        """Test checking API availability when no status exists"""
        mock_api_config_service.get_health_status.return_value = []

        result = await fallback_service.check_api_availability(ApiProvider.NVD)

        assert result is False


class TestManualResearchFallback:
    """Test cases for manual research fallback mechanism"""

    @pytest.fixture
    def fallback_service(self, mock_api_config_service):
        mock_service = MagicMock(spec=ApiConfigurationService)
        return FallbackService(mock_service)

    def test_manual_research_option_nvd(self, fallback_service):
        """Test manual research option generation for NVD"""
        query_context = {"cve_id": "CVE-2024-1234"}

        option = fallback_service._get_manual_research_option(ApiProvider.NVD, query_context)

        assert option is not None
        assert option["type"] == FallbackType.MANUAL_RESEARCH.value
        assert option["provider"] == "nvd"
        assert "CVE-2024-1234" in option["url"]
        assert option["confidence"] == 0.9
        assert "instructions" in option

    def test_manual_research_option_exploitdb(self, fallback_service):
        """Test manual research option generation for ExploitDB"""
        query_context = {"cve_id": "CVE-2024-5678"}

        option = fallback_service._get_manual_research_option(ApiProvider.EXPLOITDB, query_context)

        assert option is not None
        assert option["type"] == FallbackType.MANUAL_RESEARCH.value
        assert "CVE-2024-5678" in option["url"]
        assert "exploit-db.com" in option["url"]

    def test_manual_research_option_cisa_kev(self, fallback_service):
        """Test manual research option generation for CISA KEV"""
        query_context = {}

        option = fallback_service._get_manual_research_option(ApiProvider.CISA_KEV, query_context)

        assert option is not None
        assert option["type"] == FallbackType.MANUAL_RESEARCH.value
        assert "cisa.gov" in option["url"]

    def test_manual_research_without_cve_id(self, fallback_service):
        """Test manual research option without CVE ID"""
        query_context = {}

        option = fallback_service._get_manual_research_option(ApiProvider.NVD, query_context)

        assert option is not None
        assert option["url"]  # Should still have base URL

    @pytest.mark.asyncio
    async def test_execute_manual_research_fallback(self, fallback_service):
        """Test execution of manual research fallback"""
        fallback_data = {
            "url": "https://nvd.nist.gov/vuln/search?cve_id=CVE-2024-1234",
            "instructions": "Search manually",
            "name": "NVD Manual Search",
            "confidence": 0.9,
            "estimated_time": "5-10 minutes"
        }
        query_context = {"cve_id": "CVE-2024-1234"}

        result = await fallback_service._execute_manual_research_fallback(
            ApiProvider.NVD,
            fallback_data,
            query_context
        )

        assert isinstance(result, FallbackResult)
        assert result.fallback_type == FallbackType.MANUAL_RESEARCH
        assert result.confidence == 0.9
        assert result.data["requires_manual_action"] is True
        assert "search_url" in result.data


class TestCachedDataFallback:
    """Test cases for cached data fallback mechanism"""

    @pytest.fixture
    def fallback_service(self):
        mock_service = MagicMock(spec=ApiConfigurationService)
        return FallbackService(mock_service)

    @pytest.mark.asyncio
    async def test_cached_data_option_recent(self, fallback_service):
        """Test cached data option when data is recent"""
        # Add recent cached data
        cache_key = "nvd:CVE-2024-1234"
        fallback_service.fallback_cache[cache_key] = {
            "data": {"cve_id": "CVE-2024-1234", "severity": "HIGH"},
            "timestamp": datetime.now() - timedelta(hours=1)
        }

        query_context = {"cve_id": "CVE-2024-1234"}
        option = await fallback_service._get_cached_data_option(ApiProvider.NVD, query_context)

        assert option is not None
        assert option["type"] == FallbackType.CACHED_DATA.value
        assert option["data"]["cve_id"] == "CVE-2024-1234"
        assert option["confidence"] > 0.5
        assert option["age_hours"] < 2

    @pytest.mark.asyncio
    async def test_cached_data_option_old(self, fallback_service):
        """Test cached data option when data is old (beyond 24 hours)"""
        # Add old cached data
        cache_key = "nvd:CVE-2024-1234"
        fallback_service.fallback_cache[cache_key] = {
            "data": {"cve_id": "CVE-2024-1234"},
            "timestamp": datetime.now() - timedelta(hours=25)
        }

        query_context = {"cve_id": "CVE-2024-1234"}
        option = await fallback_service._get_cached_data_option(ApiProvider.NVD, query_context)

        assert option is None  # Should not use data older than 24 hours

    @pytest.mark.asyncio
    async def test_cached_data_option_not_found(self, fallback_service):
        """Test cached data option when no cached data exists"""
        query_context = {"cve_id": "CVE-2024-9999"}
        option = await fallback_service._get_cached_data_option(ApiProvider.NVD, query_context)

        assert option is None

    @pytest.mark.asyncio
    async def test_cached_data_confidence_decreases_with_age(self, fallback_service):
        """Test that confidence decreases as cached data ages"""
        cache_key = "nvd:CVE-2024-1234"
        
        # Recent data
        fallback_service.fallback_cache[cache_key] = {
            "data": {"cve_id": "CVE-2024-1234"},
            "timestamp": datetime.now() - timedelta(hours=1)
        }
        recent_option = await fallback_service._get_cached_data_option(
            ApiProvider.NVD,
            {"cve_id": "CVE-2024-1234"}
        )
        recent_confidence = recent_option["confidence"]

        # Older data
        fallback_service.fallback_cache[cache_key] = {
            "data": {"cve_id": "CVE-2024-1234"},
            "timestamp": datetime.now() - timedelta(hours=20)
        }
        old_option = await fallback_service._get_cached_data_option(
            ApiProvider.NVD,
            {"cve_id": "CVE-2024-1234"}
        )
        old_confidence = old_option["confidence"]

        assert old_confidence < recent_confidence

    def test_cache_api_response(self, fallback_service):
        """Test caching API response for fallback"""
        response_data = {"cve_id": "CVE-2024-1234", "severity": "HIGH"}

        fallback_service.cache_api_response(ApiProvider.NVD, "CVE-2024-1234", response_data)

        cache_key = "nvd:CVE-2024-1234"
        assert cache_key in fallback_service.fallback_cache
        assert fallback_service.fallback_cache[cache_key]["data"] == response_data

    def test_cache_cleanup_on_overflow(self, fallback_service):
        """Test that cache is cleaned up when it exceeds limit"""
        # Fill cache beyond limit
        for i in range(105):
            fallback_service.cache_api_response(
                ApiProvider.NVD,
                f"CVE-2024-{i}",
                {"data": i}
            )

        # Count NVD cache entries
        nvd_entries = [k for k in fallback_service.fallback_cache.keys() if k.startswith("nvd:")]
        
        # Should be capped at 100
        assert len(nvd_entries) <= 100

    @pytest.mark.asyncio
    async def test_execute_cached_data_fallback(self, fallback_service):
        """Test execution of cached data fallback"""
        fallback_data = {
            "data": {"cve_id": "CVE-2024-1234", "severity": "HIGH"},
            "confidence": 0.6
        }
        query_context = {"cve_id": "CVE-2024-1234"}

        result = await fallback_service._execute_cached_data_fallback(
            ApiProvider.NVD,
            fallback_data,
            query_context
        )

        assert isinstance(result, FallbackResult)
        assert result.fallback_type == FallbackType.CACHED_DATA
        assert result.confidence == 0.6
        assert result.data["cve_id"] == "CVE-2024-1234"


class TestAlternativeApiFallback:
    """Test cases for alternative API fallback mechanism"""

    @pytest.fixture
    def mock_api_config_service(self):
        return MagicMock(spec=ApiConfigurationService)

    @pytest.fixture
    def fallback_service(self, mock_api_config_service):
        return FallbackService(mock_api_config_service)

    @pytest.mark.asyncio
    async def test_alternative_api_option_nvd_to_cisa(self, fallback_service, mock_api_config_service):
        """Test alternative API option when NVD is down, CISA is available"""
        # Mock CISA as healthy
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.HEALTHY.value,
            "provider": "cisa_kev"
        }]

        query_context = {"cve_id": "CVE-2024-1234"}
        option = await fallback_service._get_alternative_api_option(ApiProvider.NVD, query_context)

        assert option is not None
        assert option["type"] == FallbackType.ALTERNATIVE_API.value
        assert option["alternative_provider"] == "cisa_kev"
        assert option["confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_alternative_api_option_no_alternatives_available(self, fallback_service, mock_api_config_service):
        """Test alternative API option when no alternatives are available"""
        # Mock all alternatives as down
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.DOWN.value
        }]

        query_context = {}
        option = await fallback_service._get_alternative_api_option(ApiProvider.NVD, query_context)

        assert option is None

    @pytest.mark.asyncio
    async def test_execute_alternative_api_fallback(self, fallback_service):
        """Test execution of alternative API fallback"""
        fallback_data = {
            "alternative_provider": "cisa_kev",
            "confidence": 0.6
        }
        query_context = {"cve_id": "CVE-2024-1234"}

        result = await fallback_service._execute_alternative_api_fallback(
            ApiProvider.NVD,
            fallback_data,
            query_context
        )

        assert isinstance(result, FallbackResult)
        assert result.fallback_type == FallbackType.ALTERNATIVE_API
        assert result.data["original_provider"] == "nvd"
        assert result.data["alternative_provider"] == "cisa_kev"


class TestDegradedServiceFallback:
    """Test cases for degraded service fallback mechanism"""

    @pytest.fixture
    def fallback_service(self):
        mock_service = MagicMock(spec=ApiConfigurationService)
        return FallbackService(mock_service)

    def test_degraded_service_option(self, fallback_service):
        """Test degraded service option generation"""
        query_context = {}
        option = fallback_service._get_degraded_service_option(ApiProvider.NVD, query_context)

        assert option is not None
        assert option["type"] == FallbackType.DEGRADED_SERVICE.value
        assert option["confidence"] == 0.3  # Low confidence
        assert "limitations" in option
        assert len(option["limitations"]) > 0

    @pytest.mark.asyncio
    async def test_execute_degraded_service_fallback(self, fallback_service):
        """Test execution of degraded service fallback"""
        fallback_data = {
            "limitations": [
                "No real-time data",
                "Reduced confidence"
            ],
            "confidence": 0.3
        }
        query_context = {"cve_id": "CVE-2024-1234"}

        result = await fallback_service._execute_degraded_service_fallback(
            ApiProvider.NVD,
            fallback_data,
            query_context
        )

        assert isinstance(result, FallbackResult)
        assert result.fallback_type == FallbackType.DEGRADED_SERVICE
        assert result.confidence == 0.3
        assert result.data["requires_manual_verification"] is True


class TestFallbackOptions:
    """Test cases for getting fallback options"""

    @pytest.fixture
    def mock_api_config_service(self):
        return MagicMock(spec=ApiConfigurationService)

    @pytest.fixture
    def fallback_service(self, mock_api_config_service):
        return FallbackService(mock_api_config_service)

    @pytest.mark.asyncio
    async def test_get_fallback_options_all_types(self, fallback_service, mock_api_config_service):
        """Test getting all fallback option types"""
        # Setup: Add cached data
        cache_key = "nvd:CVE-2024-1234"
        fallback_service.fallback_cache[cache_key] = {
            "data": {"cve_id": "CVE-2024-1234"},
            "timestamp": datetime.now() - timedelta(hours=1)
        }

        # Mock alternative API available
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.HEALTHY.value,
            "provider": "cisa_kev"
        }]

        query_context = {"cve_id": "CVE-2024-1234"}
        options = await fallback_service.get_fallback_options(ApiProvider.NVD, query_context)

        # Should have multiple fallback options
        assert len(options) >= 3  # Manual, cached, alternative, degraded

        # Options should be sorted by confidence
        confidences = [opt["confidence"] for opt in options]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_get_fallback_options_minimal(self, fallback_service, mock_api_config_service):
        """Test getting minimal fallback options when nothing is cached"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.DOWN.value
        }]

        query_context = {}
        options = await fallback_service.get_fallback_options(ApiProvider.NVD, query_context)

        # Should have at least manual research and degraded service
        assert len(options) >= 2
        
        types = [opt["type"] for opt in options]
        assert FallbackType.MANUAL_RESEARCH.value in types
        assert FallbackType.DEGRADED_SERVICE.value in types

    @pytest.mark.asyncio
    async def test_execute_fallback_manual_research(self, fallback_service):
        """Test execute_fallback dispatches to correct handler"""
        fallback_data = {
            "url": "https://nvd.nist.gov/",
            "instructions": "Search manually",
            "name": "NVD",
            "confidence": 0.9
        }
        
        result = await fallback_service.execute_fallback(
            ApiProvider.NVD,
            FallbackType.MANUAL_RESEARCH,
            {"cve_id": "CVE-2024-1234"},
            fallback_data
        )

        assert result.fallback_type == FallbackType.MANUAL_RESEARCH

    @pytest.mark.asyncio
    async def test_execute_fallback_invalid_type(self, fallback_service):
        """Test execute_fallback raises error for invalid type"""
        with pytest.raises(ValueError, match="Unknown fallback type"):
            await fallback_service.execute_fallback(
                ApiProvider.NVD,
                "invalid_type",  # Invalid type
                {},
                {}
            )


class TestProviderStatusSummary:
    """Test cases for provider status summary"""

    @pytest.fixture
    def mock_api_config_service(self):
        return MagicMock(spec=ApiConfigurationService)

    @pytest.fixture
    def fallback_service(self, mock_api_config_service):
        service = FallbackService(mock_api_config_service)
        # Add some cached entries
        service.fallback_cache["nvd:CVE-1"] = {"data": {}, "timestamp": datetime.now()}
        service.fallback_cache["nvd:CVE-2"] = {"data": {}, "timestamp": datetime.now()}
        service.fallback_cache["cisa_kev:CVE-1"] = {"data": {}, "timestamp": datetime.now()}
        return service

    @pytest.mark.asyncio
    async def test_get_provider_status_summary_all_healthy(self, fallback_service, mock_api_config_service):
        """Test provider status summary when all providers are healthy"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.HEALTHY.value,
            "provider": "nvd"
        }]

        summary = await fallback_service.get_provider_status_summary()

        assert summary["overall_health"] == "healthy"
        assert summary["fallback_cache_size"] == 3
        assert "providers" in summary

    @pytest.mark.asyncio
    async def test_get_provider_status_summary_with_degraded(self, fallback_service, mock_api_config_service):
        """Test provider status summary with degraded providers"""
        def mock_health_status(provider):
            if provider == ApiProvider.NVD:
                return [{"status": HealthStatus.DEGRADED.value, "provider": "nvd"}]
            return [{"status": HealthStatus.HEALTHY.value}]

        mock_api_config_service.get_health_status.side_effect = mock_health_status

        summary = await fallback_service.get_provider_status_summary()

        assert summary["overall_health"] == "degraded"

    @pytest.mark.asyncio
    async def test_get_provider_status_summary_all_down(self, fallback_service, mock_api_config_service):
        """Test provider status summary when all providers are down"""
        mock_api_config_service.get_health_status.return_value = [{
            "status": HealthStatus.DOWN.value
        }]

        summary = await fallback_service.get_provider_status_summary()

        assert summary["overall_health"] in ["degraded", "critical"]

    @pytest.mark.asyncio
    async def test_notify_api_unavailable(self, fallback_service):
        """Test notification when API becomes unavailable"""
        error_details = {
            "error": "Connection timeout",
            "status_code": 504
        }

        notification = await fallback_service.notify_api_unavailable(ApiProvider.NVD, error_details)

        assert notification["provider"] == "nvd"
        assert notification["status"] == "unavailable"
        assert notification["fallback_options_available"] is True


class TestFallbackResult:
    """Test cases for FallbackResult class"""

    def test_fallback_result_creation(self):
        """Test creating a FallbackResult"""
        result = FallbackResult(
            FallbackType.MANUAL_RESEARCH,
            {"url": "https://example.com"},
            "Manual Research",
            confidence=0.8
        )

        assert result.fallback_type == FallbackType.MANUAL_RESEARCH
        assert result.data["url"] == "https://example.com"
        assert result.source == "Manual Research"
        assert result.confidence == 0.8
        assert result.is_fallback is True
        assert isinstance(result.timestamp, datetime)

    def test_fallback_result_default_confidence(self):
        """Test FallbackResult with default confidence"""
        result = FallbackResult(
            FallbackType.DEGRADED_SERVICE,
            {},
            "Degraded"
        )

        assert result.confidence == 0.5  # Default confidence
