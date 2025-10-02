"""
Tests for authentication middleware.

Tests API key authentication for Epic 2 monitoring endpoints.
"""

import os
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from unittest.mock import patch

from middleware.auth import verify_api_key, optional_api_key


# Test application with authentication
app = FastAPI()


@app.get("/protected")
async def protected_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Success", "api_key": api_key}


@app.get("/optional")
async def optional_endpoint(api_key: str = Depends(optional_api_key)):
    return {"message": "Success", "api_key": api_key}


@app.get("/public")
async def public_endpoint():
    return {"message": "Public endpoint"}


client = TestClient(app)


class TestAuthenticationMiddleware:
    """Test suite for authentication middleware"""

    def test_valid_api_key_grants_access(self):
        """Test that valid API key grants access to protected endpoint"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "test-key-123"}
            )

        assert response.status_code == 200
        assert response.json()["message"] == "Success"
        assert response.json()["api_key"] == "test-key-123"

    def test_invalid_api_key_returns_401(self):
        """Test that invalid API key returns 401 Unauthorized"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "wrong-key"}
            )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        assert response.headers.get("WWW-Authenticate") == "ApiKey"

    def test_missing_api_key_returns_401(self):
        """Test that missing API key returns 401 Unauthorized"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get("/protected")

        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]
        assert response.headers.get("WWW-Authenticate") == "ApiKey"

    def test_development_mode_without_api_key_configured(self):
        """Test that endpoints work without API key when not configured (dev mode)"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get("/protected")

        assert response.status_code == 200
        assert response.json()["api_key"] == "development-mode"

    def test_optional_auth_allows_access_without_key(self):
        """Test that optional auth allows access without API key"""
        response = client.get("/optional")

        assert response.status_code == 200
        assert response.json()["api_key"] is None

    def test_optional_auth_validates_key_when_provided(self):
        """Test that optional auth validates API key when provided"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/optional",
                headers={"X-API-Key": "test-key-123"}
            )

        assert response.status_code == 200
        assert response.json()["api_key"] == "test-key-123"

    def test_optional_auth_ignores_invalid_key(self):
        """Test that optional auth ignores invalid key (doesn't raise 401)"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/optional",
                headers={"X-API-Key": "wrong-key"}
            )

        # Should still allow access but return None for api_key
        assert response.status_code == 200
        assert response.json()["api_key"] is None

    def test_public_endpoint_works_without_auth(self):
        """Test that public endpoints work without any authentication"""
        response = client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "Public endpoint"

    def test_case_sensitivity_of_header_name(self):
        """Test that X-API-Key header is case-insensitive"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            # FastAPI/Starlette normalizes headers to lowercase
            response = client.get(
                "/protected",
                headers={"x-api-key": "test-key-123"}
            )

        assert response.status_code == 200

    def test_empty_string_api_key_returns_401(self):
        """Test that empty string API key is treated as missing"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/protected",
                headers={"X-API-Key": ""}
            )

        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_whitespace_api_key_returns_401(self):
        """Test that whitespace-only API key is invalid"""
        with patch.dict(os.environ, {"HERMES_API_KEY": "test-key-123"}):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "   "}
            )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]


class TestAuthenticationIntegration:
    """Integration tests for authentication with real endpoints"""

    def test_monitoring_endpoints_require_authentication(self):
        """Test that monitoring endpoints require authentication"""
        # Note: This is a placeholder - actual integration test would need
        # the full app with all routers included
        pass

    def test_health_check_does_not_require_auth(self):
        """Test that main health check endpoint doesn't require auth"""
        # The /health endpoint at root level should remain public
        pass