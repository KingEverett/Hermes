import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from services.config.api_key_manager import ApiKeyManager, ApiProvider
from services.config.rate_limiter import RateLimiter
from models.api_configuration import ApiConfiguration
import redis.asyncio as redis


class TestApiKeyManager:
    """Test cases for API key management with keyring integration"""

    @pytest.fixture
    def api_key_manager(self):
        """Create ApiKeyManager instance for testing"""
        with patch('keyring.get_password') as mock_get, \
             patch('keyring.set_password') as mock_set:
            # Mock encryption key retrieval/creation
            mock_get.return_value = None  # No existing key
            mock_set.return_value = None
            manager = ApiKeyManager()
            yield manager

    def test_store_api_key_success(self, api_key_manager):
        """Test successful API key storage"""
        with patch('keyring.set_password') as mock_set:
            mock_set.return_value = None

            result = api_key_manager.store_api_key(ApiProvider.NVD, "test-api-key-123")

            assert result is True
            mock_set.assert_called()

    def test_store_api_key_failure(self, api_key_manager):
        """Test API key storage failure"""
        with patch('keyring.set_password') as mock_set:
            mock_set.side_effect = Exception("Keyring error")

            result = api_key_manager.store_api_key(ApiProvider.NVD, "test-api-key-123")

            assert result is False

    def test_get_api_key_from_keyring(self, api_key_manager):
        """Test retrieving API key from keyring"""
        test_key = "test-api-key-123"

        # Store key first
        with patch('keyring.set_password'), patch('keyring.get_password') as mock_get:
            # Mock encrypted key retrieval
            encrypted_key = api_key_manager._encrypt_api_key(test_key)
            mock_get.return_value = encrypted_key

            result = api_key_manager.get_api_key(ApiProvider.NVD)

            assert result == test_key

    def test_get_api_key_from_environment(self, api_key_manager):
        """Test fallback to environment variable"""
        test_key = "env-api-key-456"

        with patch('keyring.get_password') as mock_get, \
             patch.dict(os.environ, {'NVD_API_KEY': test_key}):
            mock_get.return_value = None  # No key in keyring

            result = api_key_manager.get_api_key(ApiProvider.NVD)

            assert result == test_key

    def test_get_api_key_not_found(self, api_key_manager):
        """Test when API key is not found anywhere"""
        with patch('keyring.get_password') as mock_get, \
             patch.dict(os.environ, {}, clear=True):
            mock_get.return_value = None

            result = api_key_manager.get_api_key(ApiProvider.NVD)

            assert result is None

    def test_delete_api_key_success(self, api_key_manager):
        """Test successful API key deletion"""
        with patch('keyring.delete_password') as mock_delete:
            mock_delete.return_value = None

            result = api_key_manager.delete_api_key(ApiProvider.NVD)

            assert result is True
            mock_delete.assert_called_with("hermes", "nvd")

    def test_delete_api_key_failure(self, api_key_manager):
        """Test API key deletion failure"""
        with patch('keyring.delete_password') as mock_delete:
            mock_delete.side_effect = Exception("Keyring error")

            result = api_key_manager.delete_api_key(ApiProvider.NVD)

            assert result is False

    def test_validate_api_key_format_nvd_valid(self, api_key_manager):
        """Test NVD API key format validation - valid UUID"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"

        result = api_key_manager.validate_api_key_format(ApiProvider.NVD, valid_uuid)

        assert result is True

    def test_validate_api_key_format_nvd_invalid(self, api_key_manager):
        """Test NVD API key format validation - invalid format"""
        invalid_key = "not-a-uuid"

        result = api_key_manager.validate_api_key_format(ApiProvider.NVD, invalid_key)

        assert result is False

    def test_validate_api_key_format_cisa_kev(self, api_key_manager):
        """Test CISA KEV API key format validation"""
        valid_key = "alphanumeric123"

        result = api_key_manager.validate_api_key_format(ApiProvider.CISA_KEV, valid_key)

        assert result is True

    def test_validate_api_key_format_empty(self, api_key_manager):
        """Test validation with empty API key"""
        result = api_key_manager.validate_api_key_format(ApiProvider.NVD, "")

        assert result is False

    def test_list_stored_providers(self, api_key_manager):
        """Test listing providers with stored keys"""
        with patch('keyring.get_password') as mock_get:
            # Mock that NVD has a key but others don't
            def mock_get_side_effect(service, provider):
                if provider == "nvd":
                    return "encrypted_key"
                return None

            mock_get.side_effect = mock_get_side_effect

            result = api_key_manager.list_stored_providers()

            assert ApiProvider.NVD in result
            assert ApiProvider.CISA_KEV not in result
            assert ApiProvider.EXPLOITDB not in result

    def test_encryption_decryption_roundtrip(self, api_key_manager):
        """Test that encryption and decryption work correctly"""
        original_key = "test-secret-key-123"

        encrypted = api_key_manager._encrypt_api_key(original_key)
        decrypted = api_key_manager._decrypt_api_key(encrypted)

        assert decrypted == original_key
        assert encrypted != original_key


class TestRateLimiter:
    """Test cases for rate limiting functionality"""

    @pytest.fixture
    async def redis_client(self):
        """Create mock Redis client for testing"""
        mock_redis = MagicMock()
        mock_redis.eval = MagicMock()
        mock_redis.hmget = MagicMock()
        mock_redis.delete = MagicMock()
        return mock_redis

    @pytest.fixture
    def rate_limiter(self, redis_client):
        """Create RateLimiter instance for testing"""
        return RateLimiter(redis_client)

    @pytest.fixture
    def api_config(self):
        """Create test API configuration"""
        config = MagicMock()
        config.rate_limit_calls = 5
        config.rate_limit_period = 60
        return config

    @pytest.mark.asyncio
    async def test_acquire_token_success(self, rate_limiter, api_config, redis_client):
        """Test successful token acquisition"""
        redis_client.eval.return_value = 1  # Token available

        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)

        assert result is True
        redis_client.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_token_rate_limited(self, rate_limiter, api_config, redis_client):
        """Test token acquisition when rate limited"""
        redis_client.eval.return_value = 0  # No tokens available

        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)

        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_token_redis_failure_fallback(self, rate_limiter, api_config, redis_client):
        """Test fallback to local rate limiting when Redis fails"""
        redis_client.eval.side_effect = Exception("Redis connection error")

        # First call should succeed (bucket starts full)
        result = await rate_limiter.acquire(ApiProvider.NVD, api_config)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_rate_limit_status_redis(self, rate_limiter, redis_client):
        """Test getting rate limit status from Redis"""
        redis_client.hmget.return_value = [b'3', b'1609459200']  # 3 tokens, timestamp

        status = await rate_limiter.get_rate_limit_status(ApiProvider.NVD)

        assert status['provider'] == 'nvd'
        assert status['tokens_available'] == 3.0
        assert status['backend'] == 'redis'

    @pytest.mark.asyncio
    async def test_get_rate_limit_status_local_fallback(self, rate_limiter, redis_client):
        """Test getting rate limit status from local fallback"""
        redis_client.hmget.side_effect = Exception("Redis error")

        # Add local bucket
        rate_limiter.local_buckets['ratelimit:nvd'] = {
            'tokens': 2,
            'last_refill': 1609459200
        }

        status = await rate_limiter.get_rate_limit_status(ApiProvider.NVD)

        assert status['provider'] == 'nvd'
        assert status['tokens_available'] == 2
        assert status['backend'] == 'local'

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limiter, redis_client):
        """Test resetting rate limit for a provider"""
        redis_client.delete.return_value = 1

        result = await rate_limiter.reset_rate_limit(ApiProvider.NVD)

        assert result is True
        redis_client.delete.assert_called_with('ratelimit:nvd')

    @pytest.mark.asyncio
    async def test_wait_for_token_success(self, rate_limiter, api_config, redis_client):
        """Test waiting for token successfully"""
        redis_client.eval.return_value = 1  # Token available immediately

        result = await rate_limiter.wait_for_token(ApiProvider.NVD, api_config, max_wait=5)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_token_timeout(self, rate_limiter, api_config, redis_client):
        """Test timeout when waiting for token"""
        redis_client.eval.return_value = 0  # No tokens ever available

        result = await rate_limiter.wait_for_token(ApiProvider.NVD, api_config, max_wait=1)

        assert result is False


class TestRateLimitDecorator:
    """Test cases for rate limit decorator functionality"""

    @pytest.fixture
    async def rate_limiter(self):
        """Create mock rate limiter for testing"""
        mock_redis = MagicMock()
        return RateLimiter(mock_redis)

    @pytest.fixture
    def api_config(self):
        """Create test API configuration"""
        config = MagicMock()
        config.rate_limit_calls = 5
        config.rate_limit_period = 60
        return config

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_success(self, rate_limiter, api_config):
        """Test rate limit decorator when token is available"""
        from services.config.rate_limiter import RateLimitDecorator

        decorator = RateLimitDecorator(rate_limiter)

        # Mock successful token acquisition
        rate_limiter.wait_for_token = MagicMock(return_value=True)

        @decorator(ApiProvider.NVD, api_config)
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"
        rate_limiter.wait_for_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_timeout(self, rate_limiter, api_config):
        """Test rate limit decorator when rate limited"""
        from services.config.rate_limiter import RateLimitDecorator

        decorator = RateLimitDecorator(rate_limiter)

        # Mock token acquisition timeout
        rate_limiter.wait_for_token = MagicMock(return_value=False)

        @decorator(ApiProvider.NVD, api_config)
        async def test_function():
            return "success"

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await test_function()


class TestApiConfigurationModels:
    """Test cases for API configuration data models"""

    def test_api_provider_enum_values(self):
        """Test ApiProvider enum values"""
        assert ApiProvider.NVD.value == "nvd"
        assert ApiProvider.CISA_KEV.value == "cisa_kev"
        assert ApiProvider.EXPLOITDB.value == "exploitdb"

    def test_default_provider_configs(self):
        """Test default provider configurations"""
        from models.api_configuration import DEFAULT_PROVIDER_CONFIGS

        nvd_config = DEFAULT_PROVIDER_CONFIGS[ApiProvider.NVD]
        assert nvd_config.default_rate_limit_calls == 1
        assert nvd_config.default_rate_limit_period == 6
        assert nvd_config.requires_api_key is True

        cisa_config = DEFAULT_PROVIDER_CONFIGS[ApiProvider.CISA_KEV]
        assert cisa_config.default_rate_limit_calls == 10
        assert cisa_config.default_rate_limit_period == 60
        assert cisa_config.requires_api_key is False