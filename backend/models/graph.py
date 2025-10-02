"""
Graph data models for network topology visualization.

This module defines Pydantic models for representing network topology graphs
in a format compatible with D3.js force-directed layouts.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime


class GraphNode(BaseModel):
    """
    Represents a node in the network topology graph.

    Nodes can be either hosts or services, with positioning data from
    layout algorithms and metadata for visualization (colors, labels, etc.).
    """
    id: str = Field(..., description="Unique identifier. Format: 'host_{uuid}' or 'service_{uuid}'")
    type: str = Field(..., description="Node type: 'host' or 'service'")
    label: str = Field(..., description="Display label. IP address for hosts, 'port/protocol' for services")
    x: float = Field(..., description="X coordinate from layout algorithm")
    y: float = Field(..., description="Y coordinate from layout algorithm")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node data: os, service_name, vuln_count, max_severity, etc."
    )


class GraphEdge(BaseModel):
    """
    Represents an edge connecting two nodes in the network topology graph.

    Edges connect hosts to their services in the network visualization.
    """
    source: str = Field(..., description="Source node ID (typically host)")
    target: str = Field(..., description="Target node ID (typically service)")


class NetworkTopology(BaseModel):
    """
    Complete network topology graph structure.

    Contains all nodes, edges, and metadata for rendering a D3.js
    force-directed network visualization.
    """
    nodes: List[GraphNode] = Field(..., description="List of all graph nodes (hosts and services)")
    edges: List[GraphEdge] = Field(..., description="List of edges connecting hosts to services")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph metadata: node_count, edge_count, generated_at, layout_algorithm, etc."
    )
