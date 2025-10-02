"""
API endpoints for staleness detection and data refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

from database.connection import get_db
from services.staleness_service import StalenessDetectionService

router = APIRouter(prefix="/api/v1/vulnerabilities", tags=["staleness"])


class RefreshResponse(BaseModel):
    """Response model for refresh requests"""
    task_id: str
    status: str
    vulnerability_id: str
    message: str


class StalenessStatsResponse(BaseModel):
    """Response model for staleness statistics"""
    total_vulnerabilities: int
    stale_count: int
    fresh_count: int
    stale_percentage: float


@router.post("/{vuln_id}/refresh", response_model=RefreshResponse)
async def refresh_vulnerability_data(
    vuln_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Trigger a refresh of vulnerability research data.

    This endpoint queues a background task to re-fetch and update
    vulnerability information from authoritative sources.
    """
    service = StalenessDetectionService(db)

    try:
        result = service.trigger_refresh(vuln_id)
        return RefreshResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger refresh: {str(e)}"
        )


@router.get("/staleness/stats", response_model=StalenessStatsResponse)
async def get_staleness_statistics(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Get staleness statistics for vulnerabilities.

    Optionally filter by project_id to get project-specific stats.
    """
    service = StalenessDetectionService(db)

    try:
        stats = service.get_staleness_statistics(project_id)
        return StalenessStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve staleness statistics: {str(e)}"
        )


@router.post("/staleness/detect")
async def detect_stale_vulnerabilities(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Run staleness detection on all vulnerabilities.

    Optionally filter by project_id to detect stale data for a specific project.
    Returns count of stale vulnerabilities found.
    """
    service = StalenessDetectionService(db)

    try:
        stale_vulns = service.detect_stale_vulnerabilities(project_id)

        return {
            'stale_count': len(stale_vulns),
            'vulnerability_ids': [str(v.id) for v in stale_vulns],
            'message': f'Detected {len(stale_vulns)} stale vulnerabilities'
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect stale vulnerabilities: {str(e)}"
        )
