"""
Attack Chain API endpoints.

Provides endpoints for managing attack chains - documented exploitation paths
during penetration testing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from database.connection import get_db
from repositories.attack_chain_repository import AttackChainRepository
from repositories.project import ProjectRepository


# Pydantic Schemas
class AttackChainNodeBase(BaseModel):
    """Base schema for attack chain nodes"""
    entity_type: str = Field(..., pattern="^(host|service)$")
    entity_id: UUID
    sequence_order: int = Field(..., ge=1)
    method_notes: Optional[str] = None
    is_branch_point: bool = False
    branch_description: Optional[str] = None


class AttackChainNodeCreate(AttackChainNodeBase):
    """Schema for creating an attack chain node"""
    pass


class AttackChainNodeResponse(AttackChainNodeBase):
    """Schema for attack chain node responses"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attack_chain_id: UUID
    created_at: datetime


class AttackChainBase(BaseModel):
    """Base schema for attack chains"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#FF6B35", pattern="^#[0-9A-Fa-f]{6}$")


class AttackChainCreate(AttackChainBase):
    """Schema for creating an attack chain"""
    nodes: List[AttackChainNodeCreate] = []


class AttackChainUpdate(BaseModel):
    """Schema for updating an attack chain"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    nodes: Optional[List[AttackChainNodeCreate]] = None


class AttackChainResponse(AttackChainBase):
    """Schema for attack chain responses"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    nodes: List[AttackChainNodeResponse] = []


class AttackChainListItem(BaseModel):
    """Schema for attack chain list items (without nodes)"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    color: str
    node_count: int
    created_at: datetime
    updated_at: datetime


# Router
router = APIRouter(prefix="/api/v1", tags=["attack-chains"])


@router.post("/projects/{project_id}/attack-chains",
             response_model=AttackChainResponse,
             status_code=status.HTTP_201_CREATED)
def create_attack_chain(
    project_id: UUID,
    chain_data: AttackChainCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new attack chain for a project.

    Args:
        project_id: UUID of the project
        chain_data: Attack chain data including nodes
        db: Database session

    Returns:
        Created AttackChain with nodes

    Raises:
        HTTPException 404: Project not found
        HTTPException 422: Validation error (duplicate sequence_order, etc.)
    """
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    # Create attack chain
    try:
        repo = AttackChainRepository(db)
        nodes_data = [node.model_dump() for node in chain_data.nodes]

        chain = repo.create_chain(
            project_id=project_id,
            name=chain_data.name,
            description=chain_data.description,
            color=chain_data.color,
            nodes=nodes_data if nodes_data else None
        )

        return chain
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error creating attack chain: {str(e)}"
        )


@router.get("/projects/{project_id}/attack-chains",
            response_model=List[AttackChainListItem])
def list_project_attack_chains(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    List all attack chains for a project.

    Args:
        project_id: UUID of the project
        db: Database session

    Returns:
        List of attack chains with node counts (without full node data)

    Raises:
        HTTPException 404: Project not found
    """
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    # Get chains
    repo = AttackChainRepository(db)
    chains = repo.get_project_chains(project_id)

    # Build response with node counts
    result = []
    for chain in chains:
        result.append({
            "id": chain.id,
            "project_id": chain.project_id,
            "name": chain.name,
            "description": chain.description,
            "color": chain.color,
            "node_count": len(chain.nodes) if chain.nodes else 0,
            "created_at": chain.created_at,
            "updated_at": chain.updated_at
        })

    return result


@router.get("/attack-chains/{chain_id}",
            response_model=AttackChainResponse)
def get_attack_chain(
    chain_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a single attack chain by ID with all nodes.

    Args:
        chain_id: UUID of the attack chain
        db: Database session

    Returns:
        AttackChain with all nodes

    Raises:
        HTTPException 404: Chain not found
    """
    repo = AttackChainRepository(db)
    chain = repo.get_chain_by_id(chain_id)

    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attack chain with ID {chain_id} not found"
        )

    return chain


@router.put("/attack-chains/{chain_id}",
            response_model=AttackChainResponse)
def update_attack_chain(
    chain_id: UUID,
    chain_data: AttackChainUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an attack chain.

    Can update name, description, color, and/or replace all nodes.

    Args:
        chain_id: UUID of the attack chain
        chain_data: Updated attack chain data
        db: Database session

    Returns:
        Updated AttackChain

    Raises:
        HTTPException 404: Chain not found
        HTTPException 422: Validation error
    """
    repo = AttackChainRepository(db)

    # Check if chain exists
    if not repo.chain_exists(chain_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attack chain with ID {chain_id} not found"
        )

    try:
        # Convert nodes to dict if provided
        nodes_data = None
        if chain_data.nodes is not None:
            nodes_data = [node.model_dump() for node in chain_data.nodes]

        chain = repo.update_chain(
            chain_id=chain_id,
            name=chain_data.name,
            description=chain_data.description,
            color=chain_data.color,
            nodes=nodes_data
        )

        return chain
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error updating attack chain: {str(e)}"
        )


@router.delete("/attack-chains/{chain_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_attack_chain(
    chain_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete an attack chain (cascade deletes nodes).

    Args:
        chain_id: UUID of the attack chain
        db: Database session

    Raises:
        HTTPException 404: Chain not found
    """
    repo = AttackChainRepository(db)

    if not repo.delete_chain(chain_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attack chain with ID {chain_id} not found"
        )

    return None
