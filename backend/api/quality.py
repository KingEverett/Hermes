"""
API endpoints for quality control metrics and trends.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from uuid import UUID

from database.connection import get_db
from services.quality_metrics_service import QualityMetricsService
from repositories.quality_repository import QualityRepository

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


# Pydantic models
class QualityMetricsResponse(BaseModel):
    """Response model for project quality metrics"""
    total_findings: int
    validated_findings: int
    false_positives: int
    accuracy_rate: float
    false_positive_rate: float
    confidence_distribution: dict
    validation_queue_size: int
    calculated_at: str


class TrendDataPoint(BaseModel):
    """Single trend data point"""
    metric_type: str
    value: float
    calculated_at: str
    metadata: dict


class TrendDataResponse(BaseModel):
    """Response model for trend data"""
    data_points: List[TrendDataPoint]
    start_date: str
    end_date: str


class FeedbackSubmission(BaseModel):
    """Request model for feedback submission"""
    finding_id: str
    feedback_type: str = Field(..., description="false_positive, false_negative, or correct")
    user_comment: str = Field(..., min_length=10)


class AccuracyIssue(BaseModel):
    """Model for accuracy issues"""
    type: str
    severity: str
    description: str
    recommendation: str


class AccuracyIssuesResponse(BaseModel):
    """Response model for accuracy issues"""
    issues: List[AccuracyIssue]
    total_issues: int


class CoverageMetricsResponse(BaseModel):
    """Response model for coverage metrics"""
    total_services: int
    services_researched: int
    coverage_rate: float
    services_pending: int


@router.get("/metrics/{project_id}", response_model=QualityMetricsResponse)
async def get_project_quality_metrics(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive quality metrics for a project.

    Returns accuracy rates, false positive rates, confidence distribution,
    and validation queue size.
    """
    service = QualityMetricsService(db)

    try:
        metrics = service.calculate_project_metrics(project_id)
        return QualityMetricsResponse(**metrics)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate quality metrics: {str(e)}"
        )


@router.get("/trends/{project_id}", response_model=TrendDataResponse)
async def get_quality_trends(
    project_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date for trend data"),
    end_date: Optional[datetime] = Query(None, description="End date for trend data"),
    metric_type: Optional[str] = Query(None, description="Filter by specific metric type"),
    days: int = Query(30, description="Number of days to look back (if dates not specified)"),
    db: Session = Depends(get_db)
):
    """
    Get historical trend data for quality metrics.

    Can specify exact date range or use 'days' parameter for relative range.
    """
    # Use default date range if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=days)

    service = QualityMetricsService(db)

    try:
        trend_data = service.get_trend_data(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            metric_type=metric_type
        )

        return TrendDataResponse(
            data_points=[TrendDataPoint(**dp) for dp in trend_data],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trend data: {str(e)}"
        )


@router.post("/feedback")
async def submit_quality_feedback(
    feedback: FeedbackSubmission,
    db: Session = Depends(get_db)
):
    """
    Submit feedback on research accuracy.

    This helps improve automated research accuracy over time by collecting
    user corrections and validations.
    """
    from repositories.validation_repository import ValidationRepository

    if feedback.feedback_type not in ['false_positive', 'false_negative', 'correct']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback type must be 'false_positive', 'false_negative', or 'correct'"
        )

    try:
        finding_uuid = UUID(feedback.finding_id)
        repository = ValidationRepository(db)

        feedback_entry = repository.create_feedback(
            finding_id=finding_uuid,
            feedback_type=feedback.feedback_type,
            user_comment=feedback.user_comment
        )

        return {
            'feedback_id': str(feedback_entry.id),
            'status': 'submitted',
            'created_at': feedback_entry.created_at.isoformat()
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid finding_id format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/issues/{project_id}", response_model=AccuracyIssuesResponse)
async def get_accuracy_issues(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Identify systematic accuracy issues in research results.

    Analyzes patterns to detect high false positive rates, validation backlogs,
    and other quality concerns.
    """
    service = QualityMetricsService(db)

    try:
        issues = service.identify_accuracy_issues(project_id)

        return AccuracyIssuesResponse(
            issues=[AccuracyIssue(**issue) for issue in issues],
            total_issues=len(issues)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to identify accuracy issues: {str(e)}"
        )


@router.get("/coverage/{project_id}", response_model=CoverageMetricsResponse)
async def get_coverage_metrics(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get research coverage metrics for a project.

    Shows what percentage of services have been researched for vulnerabilities.
    """
    service = QualityMetricsService(db)

    try:
        coverage = service.calculate_coverage_metrics(project_id)
        return CoverageMetricsResponse(**coverage)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate coverage metrics: {str(e)}"
        )
