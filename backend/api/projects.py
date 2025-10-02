from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database.connection import get_db
from repositories.project import ProjectRepository
from repositories.host import HostRepository
from repositories.vulnerability import VulnerabilityRepository
from api.schemas import ProjectCreate, ProjectResponse, HostResponse, VulnerabilityResponse

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    repo = ProjectRepository(db)

    existing_project = repo.get_by_name(project.name)
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this name already exists"
        )

    return repo.create(**project.model_dump())

@router.get("/", response_model=List[ProjectResponse])
def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all projects"""
    repo = ProjectRepository(db)
    return repo.get_all(skip=skip, limit=limit)

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """Get a specific project"""
    repo = ProjectRepository(db)
    project = repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project

@router.get("/{project_id}/hosts", response_model=List[HostResponse])
def list_project_hosts(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all hosts for a project"""
    repo = HostRepository(db)
    return repo.get_by_project_id(project_id, skip=skip, limit=limit)

@router.get("/{project_id}/vulnerabilities", response_model=List[VulnerabilityResponse])
def list_project_vulnerabilities(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all vulnerabilities for a project (through services)"""
    vuln_repo = VulnerabilityRepository(db)
    return vuln_repo.get_all(skip=skip, limit=limit)