from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from database.connection import get_db
from repositories.service import ServiceRepository
from repositories.host import HostRepository
from api.schemas import ServiceCreate, ServiceResponse

router = APIRouter(prefix="/api/v1/services", tags=["services"])

@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate, db: Session = Depends(get_db)):
    """Create a new service"""
    host_repo = HostRepository(db)
    host = host_repo.get_by_id(service.host_id)
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    service_repo = ServiceRepository(db)
    existing_service = service_repo.get_by_host_and_port(
        service.host_id, service.port, service.protocol
    )
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service with this port and protocol already exists on this host"
        )

    return service_repo.create(**service.model_dump())