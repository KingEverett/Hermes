import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from models.api_configuration import ApiProvider, HealthStatus
from services.config.api_configuration import ApiConfigurationService

logger = logging.getLogger(__name__)


class FallbackType(Enum):
    """Types of fallback mechanisms available"""
    MANUAL_RESEARCH = "manual_research"
    CACHED_DATA = "cached_data"
    ALTERNATIVE_API = "alternative_api"
    DEGRADED_SERVICE = "degraded_service"


class FallbackResult:
    """Result of a fallback operation"""
    def __init__(self, fallback_type: FallbackType, data: Any, source: str, confidence: float = 0.5):
        self.fallback_type = fallback_type
        self.data = data
        self.source = source
        self.confidence = confidence
        self.timestamp = datetime.now()
        self.is_fallback = True


class FallbackService:
    """Service for handling API fallback mechanisms when primary APIs are unavailable"""

    def __init__(self, api_config_service: ApiConfigurationService):
        self.api_config = api_config_service
        self.fallback_cache = {}
        self.manual_research_links = {
            ApiProvider.NVD: {
                "name": "NVD Manual Search",
                "base_url": "https://nvd.nist.gov/vuln/search",
                "search_params": {"form_type": "Basic", "results_type": "overview"},
                "instructions": "Search for CVE ID or vulnerability keywords manually"
            },
            ApiProvider.CISA_KEV: {
                "name": "CISA KEV Catalog",
                "base_url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                "search_params": {},
                "instructions": "Browse the Known Exploited Vulnerabilities catalog manually"
            },
            ApiProvider.EXPLOITDB: {
                "name": "Exploit Database",
                "base_url": "https://www.exploit-db.com/search",
                "search_params": {"q": ""},
                "instructions": "Search for exploits by CVE, application, or platform"
            }
        }

    async def check_api_availability(self, provider: ApiProvider) -> bool:
        """Check if an API provider is currently available"""
        try:
            health_status = self.api_config.get_health_status(provider)
            if not health_status:
                return False

            current_status = health_status[0]
            return current_status["status"] == HealthStatus.HEALTHY.value

        except Exception as e:
            logger.error(f"Failed to check availability for {provider.value}: {e}")
            return False

    async def get_fallback_options(self, provider: ApiProvider, query_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get available fallback options for a provider and query"""
        options = []

        # Always include manual research links
        manual_option = self._get_manual_research_option(provider, query_context)
        if manual_option:
            options.append(manual_option)

        # Check for cached data
        cached_option = await self._get_cached_data_option(provider, query_context)
        if cached_option:
            options.append(cached_option)

        # Check for alternative APIs
        alternative_option = await self._get_alternative_api_option(provider, query_context)
        if alternative_option:
            options.append(alternative_option)

        # Degraded service option
        degraded_option = self._get_degraded_service_option(provider, query_context)
        if degraded_option:
            options.append(degraded_option)

        return sorted(options, key=lambda x: x.get("confidence", 0), reverse=True)

    def _get_manual_research_option(self, provider: ApiProvider, query_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate manual research fallback option"""
        if provider not in self.manual_research_links:
            return None

        link_info = self.manual_research_links[provider]

        # Construct search URL if query parameters are available
        search_url = link_info["base_url"]
        if query_context.get("cve_id"):
            if provider == ApiProvider.NVD:
                search_url += f"?cve_id={query_context['cve_id']}"
            elif provider == ApiProvider.EXPLOITDB:
                search_url += f"?cve={query_context['cve_id']}"

        return {
            "type": FallbackType.MANUAL_RESEARCH.value,
            "provider": provider.value,
            "name": link_info["name"],
            "url": search_url,
            "instructions": link_info["instructions"],
            "confidence": 0.9,  # High confidence that manual research will work
            "estimated_time": "5-10 minutes",
            "data_quality": "High (manual verification)",
            "description": f"Manually search {link_info['name']} for vulnerability information"
        }

    async def _get_cached_data_option(self, provider: ApiProvider, query_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for relevant cached data"""
        cache_key = f"{provider.value}:{query_context.get('cve_id', 'unknown')}"

        # Check if we have recent cached data (last 24 hours)
        if cache_key in self.fallback_cache:
            cached_entry = self.fallback_cache[cache_key]
            age = datetime.now() - cached_entry["timestamp"]

            if age < timedelta(hours=24):
                return {
                    "type": FallbackType.CACHED_DATA.value,
                    "provider": provider.value,
                    "name": f"Cached {provider.value} Data",
                    "data": cached_entry["data"],
                    "confidence": 0.7 - (age.total_seconds() / 86400 * 0.2),  # Decreases with age
                    "age_hours": age.total_seconds() / 3600,
                    "data_quality": "Medium (cached data)",
                    "description": f"Use cached data from {provider.value} (age: {age.total_seconds() / 3600:.1f} hours)"
                }

        return None

    async def _get_alternative_api_option(self, provider: ApiProvider, query_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find alternative API providers that might have similar data"""
        alternatives = {
            ApiProvider.NVD: [ApiProvider.CISA_KEV],
            ApiProvider.CISA_KEV: [ApiProvider.NVD, ApiProvider.EXPLOITDB],
            ApiProvider.EXPLOITDB: [ApiProvider.NVD, ApiProvider.CISA_KEV]
        }

        if provider not in alternatives:
            return None

        for alt_provider in alternatives[provider]:
            if await self.check_api_availability(alt_provider):
                return {
                    "type": FallbackType.ALTERNATIVE_API.value,
                    "provider": provider.value,
                    "alternative_provider": alt_provider.value,
                    "name": f"Use {alt_provider.value} instead",
                    "confidence": 0.6,  # Lower confidence due to different data sources
                    "data_quality": "Medium (alternative source)",
                    "description": f"Query {alt_provider.value} for similar vulnerability information"
                }

        return None

    def _get_degraded_service_option(self, provider: ApiProvider, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide degraded service option"""
        return {
            "type": FallbackType.DEGRADED_SERVICE.value,
            "provider": provider.value,
            "name": "Degraded Service Mode",
            "confidence": 0.3,
            "data_quality": "Low (limited information)",
            "description": f"Continue with limited {provider.value} functionality",
            "limitations": [
                "No real-time vulnerability data",
                "Reduced confidence in results",
                "Manual verification required"
            ]
        }

    async def execute_fallback(self, provider: ApiProvider, fallback_type: FallbackType,
                             query_context: Dict[str, Any], fallback_data: Dict[str, Any]) -> FallbackResult:
        """Execute a specific fallback mechanism"""

        if fallback_type == FallbackType.MANUAL_RESEARCH:
            return await self._execute_manual_research_fallback(provider, fallback_data, query_context)

        elif fallback_type == FallbackType.CACHED_DATA:
            return await self._execute_cached_data_fallback(provider, fallback_data, query_context)

        elif fallback_type == FallbackType.ALTERNATIVE_API:
            return await self._execute_alternative_api_fallback(provider, fallback_data, query_context)

        elif fallback_type == FallbackType.DEGRADED_SERVICE:
            return await self._execute_degraded_service_fallback(provider, fallback_data, query_context)

        else:
            raise ValueError(f"Unknown fallback type: {fallback_type}")

    async def _execute_manual_research_fallback(self, provider: ApiProvider,
                                              fallback_data: Dict[str, Any],
                                              query_context: Dict[str, Any]) -> FallbackResult:
        """Execute manual research fallback"""
        result_data = {
            "search_url": fallback_data["url"],
            "instructions": fallback_data["instructions"],
            "provider_name": fallback_data["name"],
            "query_context": query_context,
            "requires_manual_action": True,
            "estimated_completion_time": fallback_data.get("estimated_time", "5-10 minutes")
        }

        return FallbackResult(
            FallbackType.MANUAL_RESEARCH,
            result_data,
            f"Manual research: {fallback_data['name']}",
            fallback_data["confidence"]
        )

    async def _execute_cached_data_fallback(self, provider: ApiProvider,
                                          fallback_data: Dict[str, Any],
                                          query_context: Dict[str, Any]) -> FallbackResult:
        """Execute cached data fallback"""
        return FallbackResult(
            FallbackType.CACHED_DATA,
            fallback_data["data"],
            f"Cached data from {provider.value}",
            fallback_data["confidence"]
        )

    async def _execute_alternative_api_fallback(self, provider: ApiProvider,
                                              fallback_data: Dict[str, Any],
                                              query_context: Dict[str, Any]) -> FallbackResult:
        """Execute alternative API fallback"""
        alt_provider = ApiProvider(fallback_data["alternative_provider"])

        # This would normally call the alternative API
        # For now, return instructions for manual alternative
        result_data = {
            "original_provider": provider.value,
            "alternative_provider": alt_provider.value,
            "query_context": query_context,
            "requires_api_call": True,
            "confidence_note": "Data may differ from original provider"
        }

        return FallbackResult(
            FallbackType.ALTERNATIVE_API,
            result_data,
            f"Alternative API: {alt_provider.value}",
            fallback_data["confidence"]
        )

    async def _execute_degraded_service_fallback(self, provider: ApiProvider,
                                               fallback_data: Dict[str, Any],
                                               query_context: Dict[str, Any]) -> FallbackResult:
        """Execute degraded service fallback"""
        result_data = {
            "provider": provider.value,
            "service_mode": "degraded",
            "limitations": fallback_data["limitations"],
            "query_context": query_context,
            "requires_manual_verification": True
        }

        return FallbackResult(
            FallbackType.DEGRADED_SERVICE,
            result_data,
            f"Degraded service for {provider.value}",
            fallback_data["confidence"]
        )

    def cache_api_response(self, provider: ApiProvider, query_key: str, response_data: Any):
        """Cache API response for future fallback use"""
        cache_key = f"{provider.value}:{query_key}"
        self.fallback_cache[cache_key] = {
            "data": response_data,
            "timestamp": datetime.now(),
            "provider": provider.value
        }

        # Clean up old cache entries (keep last 100 per provider)
        provider_keys = [k for k in self.fallback_cache.keys() if k.startswith(f"{provider.value}:")]
        if len(provider_keys) > 100:
            # Remove oldest entries
            sorted_keys = sorted(provider_keys,
                               key=lambda k: self.fallback_cache[k]["timestamp"])
            for old_key in sorted_keys[:-100]:
                del self.fallback_cache[old_key]

    async def notify_api_unavailable(self, provider: ApiProvider, error_details: Dict[str, Any]):
        """Notify users when an API becomes unavailable"""
        notification_data = {
            "provider": provider.value,
            "status": "unavailable",
            "error": error_details,
            "timestamp": datetime.now(),
            "fallback_options_available": True
        }

        # This would normally send notifications via email, webhook, etc.
        logger.warning(f"API {provider.value} is unavailable: {error_details}")

        return notification_data

    async def get_provider_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary for all providers"""
        summary = {
            "overall_health": "healthy",
            "providers": {},
            "fallback_cache_size": len(self.fallback_cache),
            "last_updated": datetime.now()
        }

        degraded_count = 0
        down_count = 0

        for provider in ApiProvider:
            is_available = await self.check_api_availability(provider)
            health_status = self.api_config.get_health_status(provider)

            provider_summary = {
                "available": is_available,
                "health": health_status[0] if health_status else None,
                "fallback_options": len(await self.get_fallback_options(provider, {})),
                "cached_entries": len([k for k in self.fallback_cache.keys()
                                     if k.startswith(f"{provider.value}:")])
            }

            summary["providers"][provider.value] = provider_summary

            if not is_available:
                if health_status and health_status[0]["status"] == HealthStatus.DOWN.value:
                    down_count += 1
                else:
                    degraded_count += 1

        # Determine overall health
        if down_count > 0:
            summary["overall_health"] = "degraded" if down_count < len(ApiProvider) else "critical"
        elif degraded_count > 0:
            summary["overall_health"] = "degraded"

        return summary