"""API endpoints for export functionality."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging
from pathlib import Path
import zipfile
import json
import io
from uuid import uuid4

from database import get_db
from models import ExportJob, ExportFormat, JobStatus
from services.documentation import DocumentationService
from services.graph_service import GraphService
from api.schemas import ExportRequest, ExportJobResponse
from repositories.project import ProjectRepository
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["exports"])


# Batch Export Request Models
class FilterConfig(BaseModel):
    """Filter configuration for graph exports"""
    severities: Optional[List[str]] = None
    host_ids: Optional[List[str]] = None
    service_types: Optional[List[str]] = None
    show_only_vulnerable: Optional[bool] = None
    label: Optional[str] = None


class BatchExportRequest(BaseModel):
    """Request for batch export with multiple filter configurations"""
    filters: List[FilterConfig]
    format: str = 'svg'  # 'svg' or 'png'
    resolution: Optional[int] = 1


@router.post("/{project_id}/export", response_model=ExportJobResponse, status_code=202)
async def export_project_documentation(
    project_id: str,
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Export project documentation in requested format.

    Args:
        project_id: Project identifier
        request: Export request with format specification
        background_tasks: FastAPI background task runner
        db: Database session

    Returns:
        ExportJobResponse with job details

    Raises:
        404: Project not found
        422: Unsupported format
    """
    # Validate project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Create export job
    export_job = ExportJob(
        project_id=project_id,
        format=request.format,
        status=JobStatus.PENDING
    )
    db.add(export_job)
    db.commit()
    db.refresh(export_job)

    # Process export in background
    background_tasks.add_task(
        process_export,
        export_job.id,
        project_id,
        request.format,
        request.include_graph,
        request.include_attack_chains
    )

    return ExportJobResponse(
        id=export_job.id,
        project_id=export_job.project_id,
        format=export_job.format,
        status=export_job.status,
        created_at=export_job.created_at
    )


@router.get("/{project_id}/export/{job_id}", response_model=ExportJobResponse)
async def get_export_job_status(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get export job status.

    Args:
        project_id: Project identifier
        job_id: Export job identifier
        db: Database session

    Returns:
        ExportJobResponse with current job status

    Raises:
        404: Job not found
    """
    job = db.query(ExportJob).filter(
        ExportJob.id == job_id,
        ExportJob.project_id == project_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    return ExportJobResponse(
        id=job.id,
        project_id=job.project_id,
        format=job.format,
        status=job.status,
        file_path=job.file_path,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.get("/{project_id}/export/{job_id}/download")
async def download_export(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """Download exported documentation.

    Args:
        project_id: Project identifier
        job_id: Export job identifier
        db: Database session

    Returns:
        File response or markdown content

    Raises:
        404: Job not found or file not available
        425: Export not ready
    """
    job = db.query(ExportJob).filter(
        ExportJob.id == job_id,
        ExportJob.project_id == project_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=425, detail="Export not ready yet")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Export failed: {job.error_message}")

    if job.format == ExportFormat.MARKDOWN:
        # For markdown, we can return content directly or as file
        if job.file_path and Path(job.file_path).exists():
            content = Path(job.file_path).read_text()
            return PlainTextResponse(content, media_type="text/markdown")
        else:
            # Generate on-the-fly if file doesn't exist
            doc_service = DocumentationService(db)
            content = doc_service.generate_markdown(project_id, include_attack_chains=True)
            return PlainTextResponse(content, media_type="text/markdown")

    # For other formats, return file
    if job.file_path and Path(job.file_path).exists():
        return FileResponse(
            job.file_path,
            media_type="application/octet-stream",
            filename=Path(job.file_path).name
        )
    else:
        raise HTTPException(status_code=404, detail="Export file not found")


@router.post("/{project_id}/exports/batch", response_model=ExportJobResponse, status_code=202)
async def create_batch_export(
    project_id: str,
    request: BatchExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create batch export with multiple filter configurations.

    Args:
        project_id: Project identifier
        request: Batch export request with filters
        background_tasks: FastAPI background task runner
        db: Database session

    Returns:
        ExportJobResponse with batch job details

    Raises:
        404: Project not found
        422: Invalid request (too many filters, etc.)
    """
    # Validate project exists
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Limit batch size
    if len(request.filters) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 filter configurations per batch")

    if len(request.filters) == 0:
        raise HTTPException(status_code=422, detail="At least one filter configuration required")

    # Create export job
    export_job = ExportJob(
        project_id=project_id,
        format="zip",  # Batch exports are ZIP files
        status=JobStatus.PENDING
    )
    db.add(export_job)
    db.commit()
    db.refresh(export_job)

    # Process batch export in background
    background_tasks.add_task(
        process_batch_export,
        export_job.id,
        project_id,
        request.filters,
        request.format,
        request.resolution
    )

    return ExportJobResponse(
        id=export_job.id,
        project_id=export_job.project_id,
        format=export_job.format,
        status=export_job.status,
        created_at=export_job.created_at
    )


@router.get("/{project_id}/exports", response_model=List[ExportJobResponse])
async def list_exports(
    project_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """List export history for a project.

    Args:
        project_id: Project identifier
        limit: Maximum number of results
        db: Database session

    Returns:
        List of export jobs ordered by creation date (newest first)
    """
    jobs = db.query(ExportJob).filter(
        ExportJob.project_id == project_id
    ).order_by(
        ExportJob.created_at.desc()
    ).limit(limit).all()

    return [
        ExportJobResponse(
            id=job.id,
            project_id=job.project_id,
            format=job.format,
            status=job.status,
            file_path=job.file_path,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
        for job in jobs
    ]


@router.get("/exports/{export_id}/download")
async def download_export_by_id(
    export_id: str,
    db: Session = Depends(get_db)
):
    """Download completed export by ID (cross-project).

    Args:
        export_id: Export job identifier
        db: Database session

    Returns:
        File response

    Raises:
        404: Export not found
        425: Export not ready
    """
    job = db.query(ExportJob).filter(ExportJob.id == export_id).first()

    if not job:
        raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

    if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=425, detail="Export not ready yet")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Export failed: {job.error_message}")

    if job.file_path and Path(job.file_path).exists():
        return FileResponse(
            job.file_path,
            media_type="application/octet-stream",
            filename=Path(job.file_path).name
        )
    else:
        raise HTTPException(status_code=404, detail="Export file not found")


def process_export(job_id: str, project_id: str, format: ExportFormat, include_graph: bool = False, include_attack_chains: bool = True):
    """Process export job in background.

    Args:
        job_id: Export job identifier
        project_id: Project identifier
        format: Export format
        include_graph: Whether to include network topology graph
        include_attack_chains: Whether to include attack chains
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        # Update job status to processing
        job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        # Generate documentation based on format
        if format == ExportFormat.MARKDOWN:
            doc_service = DocumentationService(db)

            # Generate markdown with flags
            content = doc_service.generate_markdown(
                project_id,
                include_graph=include_graph,
                include_attack_chains=include_attack_chains
            )

            # Export SVGs for attack chains if included
            if include_attack_chains:
                from uuid import UUID
                chains = doc_service._fetch_attack_chains(project_id)
                project_dir = Path('exports') / project_id
                for chain in chains:
                    doc_service.export_chain_svg(str(chain.id), project_dir)

            # Save to file
            project = doc_service.project_repo.get_by_id(project_id)
            filename = f"{project.name.replace(' ', '_').lower()}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            output_path = Path('exports') / project_id / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding='utf-8')

            job.file_path = str(output_path)
            job.status = JobStatus.COMPLETED
        else:
            # Other formats not implemented yet
            job.status = JobStatus.FAILED
            job.error_message = f"Format {format} not implemented yet"

        job.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        logger.error(f"Export job {job_id} failed: {str(e)}")
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
    finally:
        db.close()


def process_batch_export(
    job_id: str,
    project_id: str,
    filters: List[FilterConfig],
    export_format: str,
    resolution: int
):
    """Process batch export job in background.

    Args:
        job_id: Export job identifier
        project_id: Project identifier
        filters: List of filter configurations
        export_format: Export format (svg or png)
        resolution: PNG resolution multiplier
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        # Update job status to processing
        job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        # Create exports directory
        exports_dir = Path("exports") / project_id
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Generate ZIP file
        zip_filename = f"batch-export-{uuid4()}.zip"
        zip_path = exports_dir / zip_filename

        manifest = []
        graph_service = GraphService(db)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, filter_config in enumerate(filters):
                try:
                    # Generate filtered topology
                    topology = graph_service.generate_topology(
                        project_id,
                        severity_filter=filter_config.severities
                    )

                    # Create descriptive filename
                    filter_label = filter_config.label or f"filter-{i+1}"
                    safe_label = filter_label.replace(' ', '-').lower()
                    filename = f"graph-{i+1}-{safe_label}.json"

                    # Add topology JSON to ZIP
                    zip_file.writestr(
                        filename,
                        json.dumps(topology, indent=2)
                    )

                    # Add to manifest
                    manifest.append({
                        'filename': filename,
                        'filter': filter_config.dict(),
                        'timestamp': datetime.now().isoformat(),
                        'node_count': len(topology.get('nodes', [])),
                        'edge_count': len(topology.get('edges', []))
                    })

                except Exception as e:
                    logger.error(f"Failed to process filter {i}: {str(e)}")
                    manifest.append({
                        'filename': f"filter-{i+1}-FAILED",
                        'error': str(e)
                    })

            # Add manifest
            zip_file.writestr(
                'manifest.json',
                json.dumps(manifest, indent=2)
            )

        job.file_path = str(zip_path)
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        logger.error(f"Batch export job {job_id} failed: {str(e)}")
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
    finally:
        db.close()