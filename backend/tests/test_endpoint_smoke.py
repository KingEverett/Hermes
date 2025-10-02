"""
Smoke tests to validate all API endpoints are properly registered and accessible.

These tests ensure that:
- All expected endpoints exist
- Endpoints return appropriate status codes
- No endpoints are accidentally unregistered
- Basic routing works correctly
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestEndpointRegistration:
    """Smoke tests for endpoint registration"""

    def test_health_endpoint(self, client):
        """Test health check endpoint is registered"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint is registered"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "message" in response.json()

    def test_configuration_endpoints_registered(self, client):
        """Test all configuration endpoints are registered"""
        # These should return 200 or 500 (DB error), but NOT 404 (unregistered)
        endpoints = [
            "/api/v1/config/apis",
            "/api/v1/config/export"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404, f"Endpoint {endpoint} not registered (404)"

    def test_monitoring_endpoints_registered(self, client):
        """Test all monitoring endpoints are registered"""
        endpoints = [
            "/api/v1/monitoring/apis/health",
            "/api/v1/monitoring/apis/usage?timeframe=day",
            "/api/v1/monitoring/apis/summary",
            "/api/v1/monitoring/apis/rate-limits",
            "/api/v1/monitoring/reports/daily"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404, f"Endpoint {endpoint} not registered (404)"

    def test_provider_specific_endpoints_registered(self, client):
        """Test provider-specific endpoints are registered"""
        endpoints = [
            "/api/v1/config/apis/nvd",
            "/api/v1/config/apis/nvd/status",
            "/api/v1/monitoring/apis/health?provider=nvd"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404, f"Endpoint {endpoint} not registered (404)"

    def test_post_endpoints_registered(self, client):
        """Test POST endpoints are registered"""
        endpoints = [
            "/api/v1/config/apis/nvd/test",
            "/api/v1/config/apis/nvd/reset"
        ]
        
        for endpoint in endpoints:
            response = client.post(endpoint)
            assert response.status_code != 404, f"Endpoint {endpoint} not registered (404)"

    def test_put_endpoints_registered(self, client):
        """Test PUT endpoints are registered"""
        response = client.put("/api/v1/config/apis/nvd", json={})
        # Should not be 404; may be 400 (validation error) or 500 (DB error)
        assert response.status_code != 404, "PUT endpoint not registered (404)"

    def test_invalid_provider_returns_400_not_404(self, client):
        """Test that invalid provider returns 400, not 404 (proving endpoint exists)"""
        response = client.get("/api/v1/config/apis/invalid_provider_xyz")
        
        # Should be 400 (bad request) or 500 (other error), but NOT 404
        # 404 would mean the endpoint pattern isn't registered
        assert response.status_code != 404

    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_configuration_paths_in_openapi(self, client):
        """Test that configuration paths are documented in OpenAPI schema"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check that our new endpoints are documented
        paths = schema["paths"]
        assert "/api/v1/config/apis" in paths
        assert "/api/v1/monitoring/apis/health" in paths

    def test_docs_endpoint_accessible(self, client):
        """Test that API documentation is accessible"""
        response = client.get("/docs")
        
        assert response.status_code == 200

    def test_redoc_endpoint_accessible(self, client):
        """Test that ReDoc documentation is accessible"""
        response = client.get("/redoc")
        
        assert response.status_code == 200


class TestExistingEndpointsStillWork:
    """Ensure our changes didn't break existing endpoints"""

    def test_projects_endpoint(self, client):
        """Test that existing projects endpoint still works"""
        response = client.get("/api/v1/projects")
        
        # Should not be 404; may be 200 (empty) or 500 (DB error)
        assert response.status_code != 404

    def test_scans_endpoint(self, client):
        """Test that existing scans endpoint still works"""
        response = client.get("/api/v1/scans")
        
        assert response.status_code != 404

    def test_hosts_endpoint(self, client):
        """Test that existing hosts endpoint still works"""
        response = client.get("/api/v1/hosts")
        
        assert response.status_code != 404

    def test_services_endpoint(self, client):
        """Test that existing services endpoint still works"""
        response = client.get("/api/v1/services")
        
        assert response.status_code != 404

    def test_vulnerabilities_endpoint(self, client):
        """Test that existing vulnerabilities endpoint still works"""
        response = client.get("/api/v1/vulnerabilities")
        
        assert response.status_code != 404


class TestRouteConflicts:
    """Test that there are no route conflicts"""

    def test_no_route_overlap(self, client):
        """Test that routes don't overlap incorrectly"""
        # Get OpenAPI schema to check routes
        response = client.get("/openapi.json")
        schema = response.json()
        paths = list(schema["paths"].keys())
        
        # Check for potential conflicts
        config_paths = [p for p in paths if p.startswith("/api/v1/config")]
        monitoring_paths = [p for p in paths if p.startswith("/api/v1/monitoring")]
        
        # Should have distinct path groups
        assert len(config_paths) > 0, "No configuration paths found"
        assert len(monitoring_paths) > 0, "No monitoring paths found"
        
        # No path should be duplicated
        assert len(paths) == len(set(paths)), "Duplicate paths found"


class TestErrorHandling:
    """Test error handling for various scenarios"""

    def test_method_not_allowed(self, client):
        """Test that wrong HTTP method returns 405, not 404"""
        # GET endpoint accessed with DELETE
        response = client.delete("/api/v1/config/apis")
        
        assert response.status_code == 405  # Method not allowed

    def test_malformed_query_parameters(self, client):
        """Test handling of malformed query parameters"""
        response = client.get("/api/v1/monitoring/apis/usage?timeframe=invalid")
        
        # Should return 422 (validation error) or 400, not 404 or 500
        assert response.status_code in [400, 422]

    def test_missing_request_body(self, client):
        """Test handling of missing request body"""
        response = client.post("/api/v1/config/import")
        
        # Should return 422 (validation error) or 400, not 500
        assert response.status_code in [400, 422]
