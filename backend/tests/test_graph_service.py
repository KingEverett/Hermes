"""
Tests for GraphService.

Tests graph generation, layout algorithms, node metadata, and performance.
"""

import pytest
from uuid import uuid4
from services.graph_service import GraphService


class TestGraphService:
    """Test GraphService graph generation functionality."""

    def test_generate_topology_with_no_hosts(self, test_db, sample_project):
        """Test graph generation for a project with no hosts."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        assert len(topology.nodes) == 0
        assert len(topology.edges) == 0
        assert topology.metadata['node_count'] == 0
        assert topology.metadata['edge_count'] == 0
        assert topology.metadata['layout_algorithm'] == 'none'

    def test_generate_topology_with_hosts_and_services(
        self, test_db, sample_project, sample_hosts_with_services
    ):
        """Test graph generation with hosts and services."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        # Verify node count (10 hosts + 50 services = 60 nodes)
        assert len(topology.nodes) == 60
        assert len(topology.edges) == 50
        assert topology.metadata['node_count'] == 60
        assert topology.metadata['edge_count'] == 50

        # Verify host nodes
        host_nodes = [n for n in topology.nodes if n.type == 'host']
        assert len(host_nodes) == 10

        # Verify all host nodes have IP address labels
        for node in host_nodes:
            assert node.label.count('.') == 3  # IP format xxx.xxx.xxx.xxx

        # Verify service nodes
        service_nodes = [n for n in topology.nodes if n.type == 'service']
        assert len(service_nodes) == 50

        # Verify service labels have port/protocol format
        for node in service_nodes:
            assert '/' in node.label

    def test_layout_algorithm_selection(
        self, test_db, sample_project, sample_hosts_with_services
    ):
        """Test that correct layout algorithm is chosen based on graph size."""
        graph_service = GraphService(test_db)

        # Medium graph (60 nodes) uses kamada_kawai layout (>= 50 nodes)
        topology = graph_service.generate_topology(sample_project.id)
        assert topology.metadata['layout_algorithm'] == 'kamada_kawai'

        # Verify all nodes have position coordinates
        for node in topology.nodes:
            assert isinstance(node.x, (int, float))
            assert isinstance(node.y, (int, float))

    def test_node_metadata_for_hosts(
        self, test_db, sample_project, sample_hosts_with_services
    ):
        """Test that host nodes have correct metadata."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        host_nodes = [n for n in topology.nodes if n.type == 'host']

        for node in host_nodes:
            assert 'os' in node.metadata
            assert 'hostname' in node.metadata
            assert 'status' in node.metadata
            assert 'color' in node.metadata

        # Verify OS-based coloring
        linux_nodes = [n for n in host_nodes if n.metadata.get('os') == 'Linux']
        assert len(linux_nodes) == 5
        for node in linux_nodes:
            assert node.metadata['color'] == '#3B82F6'  # Blue

        windows_nodes = [n for n in host_nodes if n.metadata.get('os') == 'Windows']
        assert len(windows_nodes) == 3
        for node in windows_nodes:
            assert node.metadata['color'] == '#8B5CF6'  # Purple

    def test_node_metadata_for_services(
        self, test_db, sample_project, sample_hosts_with_services
    ):
        """Test that service nodes have correct metadata."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        service_nodes = [n for n in topology.nodes if n.type == 'service']

        for node in service_nodes:
            assert 'service_name' in node.metadata
            assert 'vuln_count' in node.metadata
            assert 'max_severity' in node.metadata
            assert 'color' in node.metadata

    def test_vulnerability_color_coding(
        self, test_db, sample_project, sample_hosts_with_services, sample_vulnerabilities
    ):
        """Test that services with vulnerabilities are colored correctly."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        service_nodes = [n for n in topology.nodes if n.type == 'service']

        # Find services with critical vulnerabilities
        critical_services = [
            n for n in service_nodes
            if n.metadata.get('max_severity') == 'critical'
        ]
        assert len(critical_services) > 0

        for node in critical_services:
            assert node.metadata['color'] == '#DC2626'  # Red
            assert node.metadata['vuln_count'] > 0

    def test_edge_creation(
        self, test_db, sample_project, sample_hosts_with_services
    ):
        """Test that edges correctly connect hosts to services."""
        graph_service = GraphService(test_db)
        topology = graph_service.generate_topology(sample_project.id)

        # Verify all edges connect host to service
        host_node_ids = {n.id for n in topology.nodes if n.type == 'host'}
        service_node_ids = {n.id for n in topology.nodes if n.type == 'service'}

        for edge in topology.edges:
            # Source should be a host
            assert edge.source in host_node_ids
            # Target should be a service
            assert edge.target in service_node_ids

    def test_empty_project_id(self, test_db):
        """Test handling of non-existent project."""
        graph_service = GraphService(test_db)
        random_id = uuid4()

        # Should return empty topology for non-existent project
        topology = graph_service.generate_topology(random_id)
        assert len(topology.nodes) == 0
        assert len(topology.edges) == 0

    def test_max_severity_calculation(self):
        """Test the max severity calculation method."""
        graph_service = GraphService(None)

        assert graph_service.get_max_severity(['low', 'medium', 'high']) == 'high'
        assert graph_service.get_max_severity(['critical', 'low']) == 'critical'
        assert graph_service.get_max_severity(['medium']) == 'medium'
        assert graph_service.get_max_severity([]) == 'none'
        assert graph_service.get_max_severity(['info', 'low']) == 'low'
