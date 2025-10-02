"""
Performance and concurrent load tests for rate limiter.

This module validates rate limiter accuracy under various load conditions:
- Concurrent request handling
- Token bucket algorithm accuracy under load
- Performance under high throughput
- Fairness across multiple clients
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock
from collections import Counter

from services.config.rate_limiter import RateLimiter
from models.api_configuration import ApiProvider, ApiConfiguration


@pytest.fixture
def mock_redis():
    """Create mock Redis client that simulates real token bucket"""
    class MockRedis:
        def __init__(self):
            self.buckets = {}
            
        async def eval(self, script, num_keys, key, capacity, tokens, interval, now):
            """Simulate Lua script execution"""
            if key not in self.buckets:
                self.buckets[key] = {
                    'tokens': capacity,
                    'last_refill': now
                }
            
            bucket = self.buckets[key]
            
            # Calculate tokens to add
            time_passed = now - bucket['last_refill']
            tokens_to_add = int(time_passed / interval)
            bucket['tokens'] = min(capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now
            
            # Try to consume a token
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return 1
            return 0
        
        async def hmget(self, key, *fields):
            if key in self.buckets:
                bucket = self.buckets[key]
                return [
                    str(bucket['tokens']).encode(),
                    str(bucket['last_refill']).encode()
                ]
            return [None, None]
        
        async def delete(self, key):
            if key in self.buckets:
                del self.buckets[key]
            return 1
    
    return MockRedis()


@pytest.fixture
def api_config():
    """Create test API configuration"""
    config = MagicMock(spec=ApiConfiguration)
    config.rate_limit_calls = 10
    config.rate_limit_period = 10  # 10 requests per 10 seconds
    return config


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis"""
    return RateLimiter(mock_redis)


class TestConcurrentRequests:
    """Test rate limiter under concurrent load"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_within_limit(self, rate_limiter, api_config, mock_redis):
        """Test that requests within rate limit succeed concurrently"""
        allowed_requests = api_config.rate_limit_calls
        
        # Make concurrent requests equal to the limit
        tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(allowed_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        successful = sum(results)
        assert successful == allowed_requests, \
            f"Expected {allowed_requests} successful requests, got {successful}"

    @pytest.mark.asyncio
    async def test_concurrent_requests_exceeding_limit(self, rate_limiter, api_config, mock_redis):
        """Test that requests exceeding rate limit are rejected"""
        allowed_requests = api_config.rate_limit_calls
        total_requests = allowed_requests + 5
        
        # Make concurrent requests exceeding the limit
        tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(total_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        successful = sum(results)
        rejected = total_requests - successful
        
        # Should allow exactly the configured limit
        assert successful <= allowed_requests, \
            f"Rate limiter allowed {successful} requests, expected max {allowed_requests}"
        assert rejected > 0, "Rate limiter should have rejected some requests"

    @pytest.mark.asyncio
    async def test_high_concurrency_accuracy(self, rate_limiter, api_config, mock_redis):
        """Test rate limiter accuracy with very high concurrency"""
        allowed_requests = api_config.rate_limit_calls
        concurrent_requests = 100  # Much higher than limit
        
        # Fire many concurrent requests
        tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        successful = sum(results)
        
        # Should never exceed the limit
        assert successful <= allowed_requests, \
            f"Rate limiter failed under high concurrency: {successful} > {allowed_requests}"

    @pytest.mark.asyncio
    async def test_burst_handling(self, rate_limiter, api_config, mock_redis):
        """Test that initial burst is handled correctly"""
        # First burst should succeed up to limit
        burst1_tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(api_config.rate_limit_calls)
        ]
        burst1_results = await asyncio.gather(*burst1_tasks)
        assert sum(burst1_results) == api_config.rate_limit_calls
        
        # Immediate second burst should be rejected
        burst2_tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(api_config.rate_limit_calls)
        ]
        burst2_results = await asyncio.gather(*burst2_tasks)
        assert sum(burst2_results) == 0, "Second burst should be completely rejected"


class TestTokenRefill:
    """Test token bucket refill behavior"""

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self, rate_limiter, api_config, mock_redis):
        """Test that tokens are refilled over time"""
        # Exhaust tokens
        for _ in range(api_config.rate_limit_calls):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        # Immediate request should fail
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is False
        
        # Wait for one token to refill
        refill_time = api_config.rate_limit_period / api_config.rate_limit_calls
        await asyncio.sleep(refill_time + 0.1)
        
        # Now should succeed
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is True, "Token should have been refilled"

    @pytest.mark.asyncio
    async def test_gradual_refill(self, rate_limiter, api_config, mock_redis):
        """Test that tokens refill gradually, not all at once"""
        # Exhaust all tokens
        for _ in range(api_config.rate_limit_calls):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        refill_interval = api_config.rate_limit_period / api_config.rate_limit_calls
        successful_refills = 0
        
        # Wait and check for gradual refill
        for _ in range(3):
            await asyncio.sleep(refill_interval + 0.1)
            if await rate_limiter.acquire(ApiProvider.NVD, api_config):
                successful_refills += 1
        
        # Should have refilled at least 2 tokens
        assert successful_refills >= 2, \
            f"Expected gradual refill, got {successful_refills} refills"


class TestPerformance:
    """Test rate limiter performance characteristics"""

    @pytest.mark.asyncio
    async def test_acquisition_latency(self, rate_limiter, api_config, mock_redis):
        """Test that token acquisition has low latency"""
        iterations = 100
        start_time = time.time()
        
        # Reset for clean test
        await rate_limiter.reset_rate_limit(ApiProvider.NVD)
        
        # Make sequential requests (up to limit)
        for _ in range(min(iterations, api_config.rate_limit_calls)):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        end_time = time.time()
        avg_latency = (end_time - start_time) / min(iterations, api_config.rate_limit_calls)
        
        # Average latency should be under 10ms
        assert avg_latency < 0.01, \
            f"Token acquisition too slow: {avg_latency*1000:.2f}ms average"

    @pytest.mark.asyncio
    async def test_concurrent_throughput(self, rate_limiter, api_config, mock_redis):
        """Test throughput under concurrent load"""
        num_requests = 50
        start_time = time.time()
        
        tasks = [
            rate_limiter.acquire(ApiProvider.NVD, api_config)
            for _ in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = num_requests / duration
        
        # Should process at least 100 requests per second
        assert throughput > 100, \
            f"Throughput too low: {throughput:.0f} req/s"


class TestProviderIsolation:
    """Test that rate limits are isolated per provider"""

    @pytest.mark.asyncio
    async def test_provider_isolation(self, rate_limiter, api_config, mock_redis):
        """Test that each provider has independent rate limits"""
        # Exhaust NVD tokens
        nvd_results = []
        for _ in range(api_config.rate_limit_calls):
            result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
            nvd_results.append(result)
        
        # NVD should be exhausted
        nvd_exhausted = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert nvd_exhausted is False
        
        # CISA should still have tokens
        cisa_result = await rate_limiter.acquire(ApiProvider.CISA_KEV, api_config)
        assert cisa_result is True, "CISA tokens should be independent of NVD"

    @pytest.mark.asyncio
    async def test_concurrent_multi_provider(self, rate_limiter, api_config, mock_redis):
        """Test concurrent requests across multiple providers"""
        providers = [ApiProvider.NVD, ApiProvider.CISA_KEV, ApiProvider.EXPLOITDB]
        requests_per_provider = api_config.rate_limit_calls
        
        # Create tasks for all providers
        tasks = []
        for provider in providers:
            for _ in range(requests_per_provider):
                tasks.append(rate_limiter.acquire(provider, api_config))
        
        results = await asyncio.gather(*tasks)
        successful = sum(results)
        
        # Each provider should allow its full quota
        expected_successful = len(providers) * requests_per_provider
        assert successful == expected_successful, \
            f"Expected {expected_successful} successful requests across providers, got {successful}"


class TestWaitForToken:
    """Test wait_for_token functionality"""

    @pytest.mark.asyncio
    async def test_wait_for_token_success(self, rate_limiter, api_config, mock_redis):
        """Test waiting for token when one becomes available"""
        # Exhaust tokens
        for _ in range(api_config.rate_limit_calls):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        # Start waiting for token (should succeed when one refills)
        result = await rate_limiter.wait_for_token(
            ApiProvider.NVD, 
            api_config, 
            max_wait=3
        )
        
        assert result is True, "Should have acquired token after waiting"

    @pytest.mark.asyncio
    async def test_wait_for_token_timeout(self, rate_limiter, api_config, mock_redis):
        """Test that wait_for_token times out appropriately"""
        # Exhaust tokens
        for _ in range(api_config.rate_limit_calls):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        start_time = time.time()
        
        # Wait with very short timeout (shorter than refill time)
        result = await rate_limiter.wait_for_token(
            ApiProvider.NVD,
            api_config,
            max_wait=0.1  # Very short timeout
        )
        
        end_time = time.time()
        wait_duration = end_time - start_time
        
        assert result is False, "Should timeout when no tokens available"
        assert wait_duration < 0.5, "Timeout should be respected"


class TestFallbackToLocal:
    """Test fallback to local rate limiting when Redis fails"""

    @pytest.mark.asyncio
    async def test_redis_failure_fallback(self, api_config):
        """Test that local fallback works when Redis fails"""
        # Create a Redis mock that fails
        failing_redis = MagicMock()
        failing_redis.eval = MagicMock(side_effect=Exception("Redis connection failed"))
        
        rate_limiter = RateLimiter(failing_redis)
        
        # Should fall back to local rate limiting
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is True, "Should fall back to local rate limiting"

    @pytest.mark.asyncio
    async def test_local_rate_limiting_accuracy(self, api_config):
        """Test that local fallback rate limiting is accurate"""
        failing_redis = MagicMock()
        failing_redis.eval = MagicMock(side_effect=Exception("Redis failed"))
        
        rate_limiter = RateLimiter(failing_redis)
        
        # Try to acquire all tokens
        results = []
        for _ in range(api_config.rate_limit_calls + 5):
            result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
            results.append(result)
        
        successful = sum(results)
        
        # Should respect rate limit even in local mode
        assert successful == api_config.rate_limit_calls, \
            f"Local fallback should enforce rate limit: {successful} vs {api_config.rate_limit_calls}"


class TestRateLimitStatus:
    """Test rate limit status reporting"""

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limiter, api_config, mock_redis):
        """Test getting current rate limit status"""
        # Consume some tokens
        for _ in range(5):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        status = await rate_limiter.get_rate_limit_status(ApiProvider.NVD)
        
        assert "provider" in status
        assert status["provider"] == "nvd"
        assert "tokens_available" in status
        assert "last_refill" in status
        assert "backend" in status

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limiter, api_config, mock_redis):
        """Test resetting rate limit"""
        # Exhaust tokens
        for _ in range(api_config.rate_limit_calls):
            await rate_limiter.acquire(ApiProvider.NVD, api_config)
        
        # Should be exhausted
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is False
        
        # Reset
        await rate_limiter.reset_rate_limit(ApiProvider.NVD)
        
        # Should have tokens again
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is True, "Rate limit should be reset"


class TestFairness:
    """Test fairness of token distribution"""

    @pytest.mark.asyncio
    async def test_no_token_starvation(self, rate_limiter, api_config, mock_redis):
        """Test that no client is starved of tokens under contention"""
        num_clients = 5
        requests_per_client = 20
        
        async def client_requests(client_id):
            """Simulate a client making requests"""
            acquired = 0
            for _ in range(requests_per_client):
                if await rate_limiter.acquire(ApiProvider.NVD, api_config):
                    acquired += 1
                await asyncio.sleep(0.01)  # Small delay between requests
            return acquired
        
        # Run multiple clients concurrently
        tasks = [client_requests(i) for i in range(num_clients)]
        results = await asyncio.gather(*tasks)
        
        # Check that all clients got at least some tokens
        assert all(r > 0 for r in results), \
            "Some clients were starved of tokens"
        
        # Check that no single client dominated
        max_acquired = max(results)
        min_acquired = min(results)
        
        # Difference shouldn't be too extreme (within 2x)
        assert max_acquired / min_acquired < 2.0, \
            f"Unfair distribution: max={max_acquired}, min={min_acquired}"
