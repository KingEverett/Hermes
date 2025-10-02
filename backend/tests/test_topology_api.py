"""
Tests for topology API endpoints.

Tests API endpoint responses, error handling, and caching behavior.
"""

import pytest
from uuid import uuid4


class TestTopologyAPI:
    """Test topology API endpoint."""

    def test_get_topology_for_valid_project(
        self, client, sample_project, sample_hosts_with_services
    ):
        """Test retrieving topology for a valid project."""
        response = client.get(f"/api/v1/projects/{sample_project.id}/topology")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'nodes' in data
        assert 'edges' in data
        assert 'metadata' in data

        # Verify node and edge counts
        assert len(data['nodes']) == 60  # 10 hosts + 50 services
        assert len(data['edges']) == 50
        assert data['metadata']['node_count'] == 60
        assert data['metadata']['edge_count'] == 50

    def test_get_topology_for_nonexistent_project(self, client):
        """Test 404 response for non-existent project."""
        random_id = uuid4()
        response = client.get(f"/api/v1/projects/{random_id}/topology")

        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        assert 'not found' in data['detail'].lower()

    def test_get_topology_for_empty_project(self, client, sample_project):
        """Test topology generation for project with no hosts."""
        response = client.get(f"/api/v1/projects/{sample_project.id}/topology")

        assert response.status_code == 200
        data = response.json()

        assert len(data['nodes']) == 0
        assert len(data['edges']) == 0
        assert data['metadata']['node_count'] == 0

    def test_topology_response_schema(
        self, client, sample_project, sample_hosts_with_services
    ):
        """Test that response matches expected schema."""
        response = client.get(f"/api/v1/projects/{sample_project.id}/topology")

        assert response.status_code == 200
        data = response.json()

        # Verify node schema
        for node in data['nodes']:
            assert 'id' in node
            assert 'type' in node
            assert 'label' in node
            assert 'x' in node
            assert 'y' in node
            assert 'metadata' in node
            assert node['type'] in ['host', 'service']

        # Verify edge schema
        for edge in data['edges']:
            assert 'source' in edge
            assert 'target' in edge

        # Verify metadata schema
        assert 'node_count' in data['metadata']
        assert 'edge_count' in data['metadata']
        assert 'generated_at' in data['metadata']

    def test_topology_with_vulnerabilities(
        self, client, sample_project, sample_hosts_with_services, sample_vulnerabilities
    ):
        """Test that topology includes vulnerability information."""
        response = client.get(f"/api/v1/projects/{sample_project.id}/topology")

        assert response.status_code == 200
        data = response.json()

        # Find service nodes with vulnerabilities
        service_nodes = [n for n in data['nodes'] if n['type'] == 'service']
        vulnerable_services = [
            n for n in service_nodes
            if n['metadata'].get('vuln_count', 0) > 0
        ]

        assert len(vulnerable_services) > 0

        # Verify vulnerability metadata
        for node in vulnerable_services:
            assert node['metadata']['vuln_count'] > 0
            assert 'max_severity' in node['metadata']
            assert node['metadata']['max_severity'] in [
                'critical', 'high', 'medium', 'low', 'info'
            ]

    def test_invalid_project_id_format(self, client):
        """Test response for invalid UUID format."""
        response = client.get("/api/v1/projects/invalid-uuid/topology")

        # Should return 422 for validation error
        assert response.status_code == 422
