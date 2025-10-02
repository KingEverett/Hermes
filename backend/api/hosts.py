from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database.connection import get_db
from repositories.host import HostRepository
from repositories.service import ServiceRepository
from api.schemas import HostCreate, HostResponse, ServiceResponse

router = APIRouter(prefix="/api/v1/hosts", tags=["hosts"])

@router.post("/", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
def create_host(host: HostCreate, db: Session = Depends(get_db)):
    """Create a new host"""
    repo = HostRepository(db)

    existing_host = repo.get_by_ip_address(host.project_id, host.ip_address)
    if existing_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host with this IP address already exists in this project"
        )

    return repo.create(**host.model_dump())

@router.get("/{host_id}", response_model=HostResponse)
def get_host(host_id: UUID, db: Session = Depends(get_db)):
    """Get a specific host"""
    repo = HostRepository(db)
    host = repo.get_by_id(host_id)
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    return host

@router.get("/{host_id}/services", response_model=List[ServiceResponse])
def list_host_services(
    host_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all services for a host"""
    repo = ServiceRepository(db)
    return repo.get_by_host_id(host_id, skip=skip, limit=limit)