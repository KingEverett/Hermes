from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import asyncio

from database.connection import get_db
from repositories.scan import ScanRepository
from repositories.project import ProjectRepository
from api.schemas import ScanCreate, ScanResponse, ScanImportResponse, ScanImportResult
from services import ScanImportService

router = APIRouter(prefix="/api/v1", tags=["scans"])

@router.post("/projects/{project_id}/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(project_id: UUID, scan: ScanCreate, db: Session = Depends(get_db)):
    """Create a new scan for a project"""
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    scan_repo = ScanRepository(db)
    scan_data = scan.model_dump()
    scan_data["project_id"] = project_id
    return scan_repo.create(**scan_data)

@router.get("/scans/{scan_id}/status", response_model=ScanResponse)
def get_scan_status(scan_id: UUID, db: Session = Depends(get_db)):
    """Get scan status and details"""
    repo = ScanRepository(db)
    scan = repo.get_by_id(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    return scan

@router.post("/projects/{project_id}/scans/import", response_model=ScanImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_scan(
    project_id: UUID,
    file: UploadFile = File(...),
    tool_type: str = Form("auto"),
    db: Session = Depends(get_db)
):
    """
    Import scan file for processing.

    Args:
        project_id: UUID of the project to import into
        file: Scan file to upload (XML, JSON, etc.)
        tool_type: Type of scan tool ('auto', 'nmap', 'masscan', 'nuclei', 'custom')

    Returns:
        ScanImportResponse with scan ID and initial status

    Raises:
        HTTPException: If project not found, file too large, or unsupported format
    """
    # Validate project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Validate file size (max 50MB)
    max_file_size = 50 * 1024 * 1024  # 50MB
    if file.size and file.size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file.size} exceeds maximum allowed size of {max_file_size} bytes"
        )

    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')

        # Initialize import service
        import_service = ScanImportService(db)

        # Start import (this will be synchronous for now, can be made async later)
        result = import_service.import_scan(
            project_id=project_id,
            filename=file.filename,
            content=content_str,
            tool_type=tool_type
        )

        if result.success:
            return ScanImportResponse(
                scan_id=result.scan_id,
                filename=file.filename,
                status="completed",
                message=f"Successfully imported {result.hosts_imported} hosts and {result.services_imported} services"
            )
        else:
            # Import failed but we still have a scan record
            return ScanImportResponse(
                scan_id=result.scan_id,
                filename=file.filename,
                status="failed",
                message=result.error_message or "Import failed with unknown error"
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded text"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process scan import: {str(e)}"
        )

@router.get("/scans/{scan_id}/import-result", response_model=ScanImportResult)
def get_import_result(scan_id: UUID, db: Session = Depends(get_db)):
    """
    Get detailed import results for a completed scan.

    Args:
        scan_id: UUID of the scan

    Returns:
        ScanImportResult with detailed statistics

    Raises:
        HTTPException: If scan not found
    """
    # Get scan to ensure it exists
    scan_repo = ScanRepository(db)
    scan = scan_repo.get_by_id(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    # Get import statistics
    import_service = ScanImportService(db)
    stats = import_service.get_import_statistics(scan_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import statistics not found"
        )

    # Convert to response format
    return ScanImportResult(
        scan_id=scan_id,
        success=stats.get('status') == 'completed',
        hosts_imported=stats.get('total_hosts_in_project', 0),
        services_imported=stats.get('total_services_in_project', 0),
        processing_time_ms=stats.get('processing_time_ms', 0),
        error_message=stats.get('error_details'),
        warnings=[]  # TODO: Add warnings support to statistics
    )