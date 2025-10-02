import asyncio
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
from models.api_configuration import ApiProvider, ApiConfiguration

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with Redis backend for distributed rate limiting"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.local_buckets: Dict[str, Dict] = {}  # In-memory fallback

    async def acquire(self, provider: ApiProvider, config: ApiConfiguration) -> bool:
        """
        Acquire a rate limit token using token bucket algorithm
        Returns True if request is allowed, False if rate limited
        """
        bucket_key = f"ratelimit:{provider.value}"

        try:
            # Use Redis for distributed rate limiting
            return await self._acquire_from_redis(bucket_key, config)
        except Exception as e:
            logger.warning(f"Redis rate limiting failed for {provider.value}: {e}")
            # Fallback to local rate limiting
            return self._acquire_from_local(bucket_key, config)

    async def _acquire_from_redis(self, bucket_key: str, config: ApiConfiguration) -> bool:
        """Redis-based token bucket implementation"""
        now = time.time()
        pipeline = self.redis.pipeline()

        # Lua script for atomic token bucket operations
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local tokens = tonumber(ARGV[2])
        local interval = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        -- Calculate tokens to add based on time elapsed
        local time_passed = math.max(0, now - last_refill)
        local tokens_to_add = math.floor(time_passed / interval) * tokens
        current_tokens = math.min(capacity, current_tokens + tokens_to_add)

        -- Check if we can consume a token
        if current_tokens >= 1 then
            current_tokens = current_tokens - 1
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return 1
        else
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return 0
        end
        """

        # Calculate refill rate (tokens per interval)
        refill_interval = config.rate_limit_period / config.rate_limit_calls
        result = await self.redis.eval(
            lua_script,
            1,
            bucket_key,
            config.rate_limit_calls,  # capacity
            1,  # tokens to add per interval
            refill_interval,  # interval in seconds
            now
        )

        return bool(result)

    def _acquire_from_local(self, bucket_key: str, config: ApiConfiguration) -> bool:
        """Local fallback token bucket implementation"""
        now = time.time()

        if bucket_key not in self.local_buckets:
            self.local_buckets[bucket_key] = {
                'tokens': config.rate_limit_calls,
                'last_refill': now
            }

        bucket = self.local_buckets[bucket_key]

        # Calculate tokens to add
        time_passed = now - bucket['last_refill']
        refill_interval = config.rate_limit_period / config.rate_limit_calls
        tokens_to_add = int(time_passed / refill_interval)

        if tokens_to_add > 0:
            bucket['tokens'] = min(config.rate_limit_calls, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now

        # Check if we can consume a token
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True

        return False

    async def get_rate_limit_status(self, provider: ApiProvider) -> Dict:
        """Get current rate limit status for a provider"""
        bucket_key = f"ratelimit:{provider.value}"

        try:
            bucket_data = await self.redis.hmget(bucket_key, 'tokens', 'last_refill')
            tokens = float(bucket_data[0]) if bucket_data[0] else 0
            last_refill = float(bucket_data[1]) if bucket_data[1] else time.time()

            return {
                'provider': provider.value,
                'tokens_available': tokens,
                'last_refill': datetime.fromtimestamp(last_refill),
                'backend': 'redis'
            }
        except Exception:
            # Check local buckets
            bucket_key = f"ratelimit:{provider.value}"
            if bucket_key in self.local_buckets:
                bucket = self.local_buckets[bucket_key]
                return {
                    'provider': provider.value,
                    'tokens_available': bucket['tokens'],
                    'last_refill': datetime.fromtimestamp(bucket['last_refill']),
                    'backend': 'local'
                }

            return {
                'provider': provider.value,
                'tokens_available': 0,
                'last_refill': None,
                'backend': 'none'
            }

    async def reset_rate_limit(self, provider: ApiProvider) -> bool:
        """Reset rate limit for a provider (admin function)"""
        bucket_key = f"ratelimit:{provider.value}"

        try:
            await self.redis.delete(bucket_key)
            if bucket_key in self.local_buckets:
                del self.local_buckets[bucket_key]
            logger.info(f"Reset rate limit for {provider.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {provider.value}: {e}")
            return False

    async def wait_for_token(self, provider: ApiProvider, config: ApiConfiguration, max_wait: int = 30) -> bool:
        """
        Wait for a rate limit token to become available
        Returns True if token acquired, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if await self.acquire(provider, config):
                return True

            # Calculate wait time based on rate limit
            wait_time = min(config.rate_limit_period / config.rate_limit_calls, 1.0)
            await asyncio.sleep(wait_time)

        return False


class RateLimitDecorator:
    """Decorator for applying rate limiting to async functions"""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    def __call__(self, provider: ApiProvider, config: ApiConfiguration, max_wait: int = 30):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if await self.rate_limiter.wait_for_token(provider, config, max_wait):
                    return await func(*args, **kwargs)
                else:
                    raise Exception(f"Rate limit exceeded for {provider.value}, max wait time reached")
            return wrapper
        return decorator