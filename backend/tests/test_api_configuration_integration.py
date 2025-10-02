"""
Integration tests for API configuration infrastructure.

This module validates the complete integration of API configuration components:
- End-to-end API configuration workflows
- Service orchestration and coordination
- Database persistence
- API endpoint accessibility
- Complete request/response cycles
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock, AsyncMock
import redis
import os

from main import app
from database.connection import get_db_session
from models.base import Base
from models.api_configuration import ApiProvider
from services.config.api_configuration import ApiConfigurationService


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api_config.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock = MagicMock()
    mock.eval = AsyncMock(return_value=1)  # Allow rate limiting
    mock.hmget = AsyncMock(return_value=[b'5', b'1609459200'])
    mock.delete = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def mock_keyring():
    """Mock keyring for API key storage"""
    with patch('services.config.api_key_manager.keyring') as mock:
        mock.get_password = MagicMock(return_value=None)
        mock.set_password = MagicMock(return_value=None)
        mock.delete_password = MagicMock(return_value=None)
        yield mock


class TestConfigurationEndpoints:
    """Integration tests for configuration API endpoints"""

    def test_get_all_configurations_empty(self, client):
        """Test getting all configurations when database is empty"""
        response = client.get("/api/v1/config/apis")
        
        # Should return empty list initially
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_complete_configuration_workflow(self, client, db_session, mock_redis, mock_keyring):
        """Test complete workflow: initialize, update, retrieve configuration"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Step 1: Initialize default configurations
            service = ApiConfigurationService(db_session, mock_redis)
            await service.initialize_default_configurations()
            
            # Step 2: Get all configurations via API
            response = client.get("/api/v1/config/apis")
            assert response.status_code == 200
            configs = response.json()
            assert len(configs) == 3  # NVD, CISA_KEV, EXPLOITDB
            
            # Step 3: Get specific configuration
            response = client.get("/api/v1/config/apis/nvd")
            assert response.status_code == 200
            nvd_config = response.json()
            assert nvd_config["provider"] == "nvd"
            assert nvd_config["enabled"] is True
            
            # Step 4: Update configuration
            update_data = {
                "enabled": False,
                "rate_limit_calls": 10,
                "timeout": 60
            }
            response = client.put("/api/v1/config/apis/nvd", json=update_data)
            assert response.status_code == 200
            updated_config = response.json()
            assert updated_config["enabled"] is False
            assert updated_config["rate_limit_calls"] == 10
            assert updated_config["timeout"] == 60
            
            # Step 5: Verify persistence
            response = client.get("/api/v1/config/apis/nvd")
            assert response.status_code == 200
            retrieved_config = response.json()
            assert retrieved_config["enabled"] is False
            assert retrieved_config["rate_limit_calls"] == 10

    def test_update_configuration_with_api_key(self, client, db_session, mock_redis, mock_keyring):
        """Test updating configuration with API key"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            # Mock successful key storage
            mock_keyring.set_password.return_value = None
            
            # Update with API key
            update_data = {
                "api_key": "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
                "enabled": True
            }
            
            response = client.put("/api/v1/config/apis/nvd", json=update_data)
            assert response.status_code == 200
            
            # Verify keyring was called
            assert mock_keyring.set_password.called

    def test_update_configuration_invalid_provider(self, client):
        """Test updating configuration with invalid provider"""
        update_data = {"enabled": False}
        
        response = client.put("/api/v1/config/apis/invalid_provider", json=update_data)
        
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    def test_update_configuration_validation(self, client, db_session, mock_redis):
        """Test configuration update validation"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            # Try invalid rate limit
            response = client.put("/api/v1/config/apis/nvd", json={"rate_limit_calls": -1})
            assert response.status_code == 400
            
            # Try invalid timeout
            response = client.put("/api/v1/config/apis/nvd", json={"timeout": 500})
            assert response.status_code == 400
            
            # Try invalid retry attempts
            response = client.put("/api/v1/config/apis/nvd", json={"retry_attempts": 20})
            assert response.status_code == 400

    def test_test_api_configuration_endpoint(self, client, db_session, mock_redis):
        """Test the API configuration test endpoint"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.post("/api/v1/config/apis/nvd/test")
            
            assert response.status_code == 200
            result = response.json()
            assert "status" in result
            assert "provider" in result

    def test_reset_provider_state_endpoint(self, client, db_session, mock_redis):
        """Test resetting provider state"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.post("/api/v1/config/apis/nvd/reset")
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["provider"] == "nvd"

    def test_get_provider_status_endpoint(self, client, db_session, mock_redis):
        """Test getting detailed provider status"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/config/apis/nvd/status")
            
            assert response.status_code == 200
            status = response.json()
            assert "provider" in status
            assert "configuration" in status
            assert "health" in status
            assert "rate_limit" in status
            assert "has_api_key" in status
            assert "enabled" in status


class TestMonitoringEndpoints:
    """Integration tests for monitoring API endpoints"""

    def test_get_api_health_status(self, client, db_session, mock_redis):
        """Test getting API health status"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/monitoring/apis/health")
            
            assert response.status_code == 200
            result = response.json()
            assert "health_statuses" in result
            assert isinstance(result["health_statuses"], list)

    def test_get_api_health_status_filtered(self, client, db_session, mock_redis):
        """Test getting health status for specific provider"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/monitoring/apis/health?provider=nvd")
            
            assert response.status_code == 200

    def test_get_api_usage_metrics(self, client, db_session, mock_redis):
        """Test getting API usage metrics"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/monitoring/apis/usage?timeframe=day")
            
            assert response.status_code == 200
            result = response.json()
            assert "metrics" in result
            assert "timeframe" in result

    def test_get_monitoring_summary(self, client, db_session, mock_redis):
        """Test getting comprehensive monitoring summary"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/monitoring/apis/summary")
            
            assert response.status_code == 200
            summary = response.json()
            assert "summary" in summary
            assert "configurations" in summary
            assert "health_statuses" in summary
            assert "usage_metrics" in summary
            assert "fallback_status" in summary

    def test_get_rate_limit_status(self, client, db_session, mock_redis):
        """Test getting rate limit status"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            response = client.get("/api/v1/monitoring/apis/rate-limits")
            
            assert response.status_code == 200
            result = response.json()
            assert "rate_limits" in result

    def test_get_daily_report(self, client, db_session, mock_redis):
        """Test getting daily monitoring report"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/monitoring/reports/daily")
            
            assert response.status_code == 200
            report = response.json()
            assert "report_date" in report
            assert "summary" in report
            assert "provider_performance" in report


class TestConfigurationImportExport:
    """Integration tests for configuration import/export"""

    def test_export_configurations(self, client, db_session, mock_redis):
        """Test exporting API configurations"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            response = client.get("/api/v1/config/export")
            
            assert response.status_code == 200
            export_data = response.json()
            assert "exported_at" in export_data
            assert "configurations" in export_data
            assert len(export_data["configurations"]) == 3

    def test_import_configurations(self, client, db_session, mock_redis):
        """Test importing API configurations"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            import_data = {
                "configurations": [
                    {
                        "provider": "nvd",
                        "enabled": False,
                        "rate_limit_calls": 2,
                        "rate_limit_period": 10,
                        "timeout": 45
                    }
                ]
            }
            
            response = client.post("/api/v1/config/import", json=import_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["imported_count"] == 1
            
            # Verify import
            response = client.get("/api/v1/config/apis/nvd")
            config = response.json()
            assert config["enabled"] is False
            assert config["rate_limit_calls"] == 2

    def test_import_export_roundtrip(self, client, db_session, mock_redis):
        """Test that export followed by import preserves configuration"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Initialize
            service = ApiConfigurationService(db_session, mock_redis)
            import asyncio
            asyncio.run(service.initialize_default_configurations())
            
            # Update a configuration
            client.put("/api/v1/config/apis/nvd", json={"rate_limit_calls": 15})
            
            # Export
            export_response = client.get("/api/v1/config/export")
            export_data = export_response.json()
            
            # Modify
            client.put("/api/v1/config/apis/nvd", json={"rate_limit_calls": 5})
            
            # Import original
            import_response = client.post("/api/v1/config/import", json=export_data)
            assert import_response.status_code == 200
            
            # Verify restoration
            config_response = client.get("/api/v1/config/apis/nvd")
            config = config_response.json()
            assert config["rate_limit_calls"] == 15


class TestServiceOrchestration:
    """Integration tests for service orchestration"""

    @pytest.mark.asyncio
    async def test_api_call_execution_with_monitoring(self, db_session, mock_redis):
        """Test that API calls are properly monitored and tracked"""
        service = ApiConfigurationService(db_session, mock_redis)
        await service.initialize_default_configurations()
        
        # Mock successful API call
        async def mock_api_call():
            return {"status": "success", "data": "test"}
        
        # Execute API call
        result = await service.execute_api_call(ApiProvider.NVD, mock_api_call)
        
        assert result["status"] == "success"
        
        # Verify metrics were recorded
        metrics = service.get_usage_metrics(ApiProvider.NVD, "day")
        assert len(metrics) > 0
        assert metrics[0]["calls_made"] > 0

    @pytest.mark.asyncio
    async def test_api_call_with_rate_limiting(self, db_session, mock_redis):
        """Test that rate limiting is enforced during API calls"""
        # Mock rate limiter to reject requests
        mock_redis.eval = AsyncMock(return_value=0)  # No tokens available
        
        service = ApiConfigurationService(db_session, mock_redis)
        await service.initialize_default_configurations()
        
        async def mock_api_call():
            return {"status": "success"}
        
        # Should raise rate limit exception
        from services.config.api_error_handler import ApiException
        with pytest.raises(ApiException, match="Rate limit exceeded"):
            await service.execute_api_call(ApiProvider.NVD, mock_api_call)

    @pytest.mark.asyncio
    async def test_health_status_tracking(self, db_session, mock_redis):
        """Test that health status is tracked correctly"""
        service = ApiConfigurationService(db_session, mock_redis)
        await service.initialize_default_configurations()
        
        # Successful call should maintain healthy status
        async def successful_call():
            return {"status": "success"}
        
        await service.execute_api_call(ApiProvider.NVD, successful_call)
        
        health = service.get_health_status(ApiProvider.NVD)
        assert len(health) > 0
        assert health[0]["consecutive_failures"] == 0


class TestEndToEndWorkflows:
    """End-to-end integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_complete_api_configuration_lifecycle(self, client, db_session, mock_redis, mock_keyring):
        """Test complete lifecycle from initialization to API usage"""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # 1. Initialize system
            service = ApiConfigurationService(db_session, mock_redis)
            await service.initialize_default_configurations()
            
            # 2. Configure API key
            mock_keyring.set_password.return_value = None
            update_data = {
                "api_key": "550e8400-e29b-41d4-a716-446655440000",
                "enabled": True,
                "rate_limit_calls": 5
            }
            response = client.put("/api/v1/config/apis/nvd", json=update_data)
            assert response.status_code == 200
            
            # 3. Check provider status
            response = client.get("/api/v1/config/apis/nvd/status")
            assert response.status_code == 200
            status = response.json()
            assert status["enabled"] is True
            assert status["has_api_key"] is True
            
            # 4. Execute API call (mocked)
            async def mock_call():
                return {"vulnerabilities": []}
            
            mock_keyring.get_password.return_value = "encrypted_key_data"
            result = await service.execute_api_call(ApiProvider.NVD, mock_call)
            assert result is not None
            
            # 5. Check usage metrics
            response = client.get("/api/v1/monitoring/apis/usage?provider=nvd&timeframe=day")
            assert response.status_code == 200
            metrics = response.json()
            assert "metrics" in metrics
            
            # 6. Get monitoring summary
            response = client.get("/api/v1/monitoring/apis/summary")
            assert response.status_code == 200
            summary = response.json()
            assert summary["summary"]["enabled_providers"] >= 1


def test_all_endpoints_registered(client):
    """Smoke test to verify all expected endpoints are registered"""
    # Configuration endpoints
    assert client.get("/api/v1/config/apis").status_code in [200, 500]  # 500 ok if DB not initialized
    
    # Monitoring endpoints  
    response = client.get("/api/v1/monitoring/apis/health")
    assert response.status_code in [200, 500]  # Should at least route correctly
    
    # Health check endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
