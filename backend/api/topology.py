"""
Network topology API endpoints.

Provides endpoints for generating and retrieving network topology graphs
for visualization in the frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from functools import lru_cache
from datetime import datetime, timedelta

from database.connection import get_db
from services.graph_service import GraphService
from repositories.project import ProjectRepository
from models.graph import NetworkTopology


router = APIRouter(prefix="/api/v1/projects", tags=["topology"])


# Simple in-memory cache with TTL for topology data
_topology_cache = {}
_cache_ttl = timedelta(minutes=5)


def _get_cached_topology(project_id: UUID) -> NetworkTopology | None:
    """
    Get topology from cache if available and not stale.

    Args:
        project_id: UUID of the project

    Returns:
        NetworkTopology if cached and fresh, None otherwise
    """
    if project_id in _topology_cache:
        cached_data, cached_time = _topology_cache[project_id]
        if datetime.now() - cached_time < _cache_ttl:
            return cached_data
        else:
            # Remove stale entry
            del _topology_cache[project_id]
    return None


def _cache_topology(project_id: UUID, topology: NetworkTopology) -> None:
    """
    Cache topology data with current timestamp.

    Args:
        project_id: UUID of the project
        topology: NetworkTopology object to cache
    """
    _topology_cache[project_id] = (topology, datetime.now())


@router.get("/{project_id}/topology", response_model=NetworkTopology)
def get_project_topology(project_id: UUID, db: Session = Depends(get_db)):
    """
    Get network topology graph for a project.

    Generates a D3.js-compatible network graph showing hosts, services,
    and their relationships. Includes vulnerability indicators and color coding.

    The response is cached for 5 minutes to optimize performance for large graphs.

    Args:
        project_id: UUID of the project
        db: Database session

    Returns:
        NetworkTopology object with nodes, edges, and metadata

    Raises:
        HTTPException 404: Project not found
        HTTPException 500: Graph generation error
    """
    # Check if project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    # Check cache first
    cached_topology = _get_cached_topology(project_id)
    if cached_topology:
        return cached_topology

    # Generate topology
    try:
        graph_service = GraphService(db)
        topology = graph_service.generate_topology(project_id)

        # Cache the result
        _cache_topology(project_id, topology)

        return topology

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate network topology: {str(e)}"
        )
