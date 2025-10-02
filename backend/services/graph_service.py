"""
Graph service for generating network topology visualizations.

This service transforms host and service data into D3.js-compatible
network graphs using NetworkX for layout calculations.
"""

import networkx as nx
from typing import Dict, List, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from repositories.graph_repository import GraphRepository
from models.graph import NetworkTopology, GraphNode, GraphEdge


class GraphService:
    """
    Service for generating network topology graphs.

    Uses NetworkX for graph construction and layout algorithms,
    then converts to D3.js-compatible JSON format for frontend rendering.
    """

    # Severity ordering for determining max severity
    SEVERITY_ORDER = {
        'critical': 1,
        'high': 2,
        'medium': 3,
        'low': 4,
        'info': 5
    }

    # Host color mapping based on OS family
    HOST_COLORS = {
        'linux': '#3B82F6',      # Blue
        'windows': '#8B5CF6',    # Purple
        'network': '#6B7280',    # Gray
        'unknown': '#9CA3AF'     # Light gray
    }

    # Service color mapping based on vulnerability severity
    SEVERITY_COLORS = {
        'critical': '#DC2626',   # Red
        'high': '#F59E0B',       # Orange
        'medium': '#FBBF24',     # Yellow
        'low': '#10B981',        # Green
        'info': '#10B981',       # Green
        'none': '#10B981'        # Green (no vulnerabilities)
    }

    def __init__(self, session: Session):
        """
        Initialize GraphService.

        Args:
            session: SQLAlchemy database session
        """
        self.graph_repo = GraphRepository(session)

    def generate_topology(self, project_id: UUID) -> NetworkTopology:
        """
        Generate network topology graph from project hosts and services.

        Algorithm:
        1. Fetch all hosts and services for the project
        2. Build NetworkX graph with host and service nodes
        3. Add edges connecting hosts to their services
        4. Calculate layout using force-directed algorithm
        5. Enrich nodes with vulnerability metadata
        6. Convert to D3.js-compatible format

        Performance: O(n + m) where n=nodes, m=edges
        Layout: O(n^2) for spring layout, O(n^3) for kamada_kawai

        Args:
            project_id: UUID of the project

        Returns:
            NetworkTopology object with nodes, edges, and metadata
        """
        # Fetch hosts with services
        hosts = self.graph_repo.get_project_hosts_with_services(project_id)

        # Collect all service IDs for vulnerability lookup
        service_ids = []
        for host in hosts:
            service_ids.extend([service.id for service in host.services])

        # Fetch vulnerability summaries for all services
        vuln_summaries = self.graph_repo.get_vulnerability_summary_by_service(service_ids)

        # Build NetworkX graph
        G = nx.Graph()

        for host in hosts:
            host_node_id = f"host_{host.id}"
            G.add_node(
                host_node_id,
                type='host',
                label=host.ip_address,
                os=host.os_family,
                hostname=host.hostname,
                status=host.status
            )

            for service in host.services:
                service_node_id = f"service_{service.id}"
                service_label = f"{service.port}/{service.protocol.value}"

                # Get vulnerability summary for this service
                vuln_summary = vuln_summaries.get(service.id, {
                    'vuln_count': 0,
                    'max_severity': 'none',
                    'has_exploit': False
                })

                G.add_node(
                    service_node_id,
                    type='service',
                    label=service_label,
                    service_name=service.service_name,
                    product=service.product,
                    version=service.version,
                    vuln_count=vuln_summary['vuln_count'],
                    max_severity=vuln_summary['max_severity'],
                    has_exploit=vuln_summary['has_exploit']
                )

                # Add edge between host and service
                G.add_edge(host_node_id, service_node_id)

        # Calculate layout based on graph size
        node_count = len(G.nodes)
        if node_count == 0:
            # Empty graph
            pos = {}
            layout_algorithm = 'none'
        elif node_count < 50:
            # Spring layout for small graphs
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
            layout_algorithm = 'spring'
        else:
            # Kamada-Kawai layout for larger graphs
            pos = nx.kamada_kawai_layout(G)
            layout_algorithm = 'kamada_kawai'

        # Convert to D3 format with 1000x scale for better visualization
        nodes = []
        for node in G.nodes:
            node_data = G.nodes[node]
            x_coord = pos[node][0] * 1000 if node in pos else 0
            y_coord = pos[node][1] * 1000 if node in pos else 0

            nodes.append(
                GraphNode(
                    id=node,
                    type=node_data['type'],
                    label=node_data['label'],
                    x=x_coord,
                    y=y_coord,
                    metadata=self._build_node_metadata(node_data)
                )
            )

        edges = [
            GraphEdge(source=u, target=v)
            for u, v in G.edges
        ]

        return NetworkTopology(
            nodes=nodes,
            edges=edges,
            metadata={
                'node_count': len(nodes),
                'edge_count': len(edges),
                'generated_at': datetime.now().isoformat(),
                'layout_algorithm': layout_algorithm
            }
        )

    def _build_node_metadata(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build metadata dictionary for a node.

        Includes different fields based on node type (host vs service)
        and calculates color assignments.

        Args:
            node_data: Raw node data from NetworkX graph

        Returns:
            Metadata dictionary for GraphNode
        """
        node_type = node_data['type']

        if node_type == 'host':
            # Host node metadata
            os_family = (node_data.get('os') or 'unknown').lower()
            color = self.HOST_COLORS.get(os_family, self.HOST_COLORS['unknown'])

            return {
                'os': node_data.get('os'),
                'hostname': node_data.get('hostname'),
                'status': node_data.get('status'),
                'color': color
            }
        else:
            # Service node metadata
            max_severity = node_data.get('max_severity', 'none')
            color = self.SEVERITY_COLORS.get(max_severity, self.SEVERITY_COLORS['none'])

            return {
                'service_name': node_data.get('service_name'),
                'product': node_data.get('product'),
                'version': node_data.get('version'),
                'vuln_count': node_data.get('vuln_count', 0),
                'max_severity': max_severity,
                'has_exploit': node_data.get('has_exploit', False),
                'color': color
            }

    def get_max_severity(self, severities: List[str]) -> str:
        """
        Determine the maximum severity from a list of severity levels.

        Args:
            severities: List of severity strings

        Returns:
            The most severe level from the list
        """
        if not severities:
            return 'none'

        # Find minimum order value (highest severity)
        min_order = min(
            self.SEVERITY_ORDER.get(s.lower(), 99)
            for s in severities
        )

        # Return corresponding severity
        for severity, order in self.SEVERITY_ORDER.items():
            if order == min_order:
                return severity

        return 'none'
