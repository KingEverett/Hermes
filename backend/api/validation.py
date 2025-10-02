"""
API endpoints for validation queue management and manual review workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

from database.connection import get_db
from models import ValidationQueue, ValidationFeedback, ServiceVulnerability
from repositories.validation_repository import ValidationRepository
from services.validation_service import ValidationService
from services.staleness_service import StalenessDetectionService

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


# Pydantic models for request/response
class ValidationQueueItemResponse(BaseModel):
    """Response model for validation queue items"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_type: str
    finding_id: str
    priority: str
    status: str
    assigned_to: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]


class ValidationQueueListResponse(BaseModel):
    """Response model for validation queue list"""
    items: List[ValidationQueueItemResponse]
    total: int


class ValidationDecisionRequest(BaseModel):
    """Request model for validation decisions"""
    decision: str = Field(..., description="approve, reject, or override")
    justification: str = Field(..., min_length=10, description="Required justification for decision")
    notes: Optional[str] = Field(None, description="Optional additional notes")
    validated_by: str = Field(..., description="User making the decision")


class ValidationDecisionResponse(BaseModel):
    """Response model for validation decisions"""
    success: bool
    finding_id: str
    decision: str
    validation_status: str
    confidence_score: Optional[float]
    validated_at: Optional[str]
    validated_by: str
    audit_created: bool


class ValidationFeedbackRequest(BaseModel):
    """Request model for validation feedback"""
    finding_id: str = Field(..., description="UUID of the finding")
    feedback_type: str = Field(..., description="false_positive, false_negative, or correct")
    comment: str = Field(..., min_length=10, description="User comment")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class ValidationFeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    feedback_id: str
    created_at: datetime


# Endpoints

@router.get("/queue", response_model=ValidationQueueListResponse)
async def get_validation_queue(
    priority: Optional[str] = Query(None, description="Filter by priority (critical, high, medium, low)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, in_review, completed)"),
    finding_type: Optional[str] = Query(None, description="Filter by finding type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get validation queue items with optional filters.

    Returns paginated list of items requiring validation.
    """
    repository = ValidationRepository(db)
    items, total = repository.get_queue_items(
        priority=priority,
        status=status,
        finding_type=finding_type,
        limit=limit,
        offset=offset
    )

    return ValidationQueueListResponse(
        items=[ValidationQueueItemResponse(
            id=str(item.id),
            finding_type=item.finding_type,
            finding_id=str(item.finding_id),
            priority=item.priority,
            status=item.status,
            assigned_to=item.assigned_to,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
            review_notes=item.review_notes
        ) for item in items],
        total=total
    )


@router.post("/{finding_id}/review", response_model=ValidationDecisionResponse)
async def submit_validation_review(
    finding_id: UUID,
    request: ValidationDecisionRequest,
    db: Session = Depends(get_db)
):
    """
    Submit a validation decision for a finding.

    Supports three decision types:
    - approve: Mark finding as validated and correct
    - reject: Mark finding as false positive
    - override: Override previous decision with elevated justification
    """
    # Validate decision type
    if request.decision not in ['approve', 'reject', 'override']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'approve', 'reject', or 'override'"
        )

    # Override requires extra scrutiny
    if request.decision == 'override' and len(request.justification) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override decisions require detailed justification (min 50 characters)"
        )

    service = ValidationService(db)

    try:
        result = service.process_validation_decision(
            finding_id=finding_id,
            decision=request.decision,
            justification=request.justification,
            validated_by=request.validated_by,
            reviewer_notes=request.notes
        )

        return ValidationDecisionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process validation decision: {str(e)}"
        )


@router.get("/history/{finding_id}")
async def get_validation_history(
    finding_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get validation history for a specific finding.

    Returns timeline of all validation actions and decisions.
    """
    # Get the vulnerability and its validation status
    vuln = db.query(ServiceVulnerability).filter(
        ServiceVulnerability.id == finding_id
    ).first()

    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding {finding_id} not found"
        )

    # Get queue item
    repository = ValidationRepository(db)
    queue_item = repository.get_queue_item_by_finding(finding_id)

    # Get feedback
    feedbacks = repository.get_feedback_by_finding(finding_id)

    history = {
        'finding_id': str(finding_id),
        'validation_status': vuln.validation_status,
        'validated': vuln.validated,
        'validated_at': vuln.validated_at.isoformat() if vuln.validated_at else None,
        'validated_by': vuln.validated_by,
        'confidence_score': vuln.confidence_score,
        'queue_item': {
            'status': queue_item.status if queue_item else None,
            'reviewed_at': queue_item.reviewed_at.isoformat() if queue_item and queue_item.reviewed_at else None,
            'review_notes': queue_item.review_notes if queue_item else None
        },
        'feedback_count': len(feedbacks),
        'feedbacks': [
            {
                'feedback_type': fb.feedback_type,
                'comment': fb.user_comment,
                'created_at': fb.created_at.isoformat()
            } for fb in feedbacks
        ]
    }

    return history


@router.post("/feedback", response_model=ValidationFeedbackResponse)
async def submit_feedback(
    request: ValidationFeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit feedback on research accuracy for a finding.

    Feedback types:
    - false_positive: Finding was incorrect
    - false_negative: Finding was missed
    - correct: Finding was accurate
    """
    if request.feedback_type not in ['false_positive', 'false_negative', 'correct']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback type must be 'false_positive', 'false_negative', or 'correct'"
        )

    repository = ValidationRepository(db)

    try:
        finding_uuid = UUID(request.finding_id)
        feedback = repository.create_feedback(
            finding_id=finding_uuid,
            feedback_type=request.feedback_type,
            user_comment=request.comment,
            user_id=request.user_id
        )

        return ValidationFeedbackResponse(
            feedback_id=str(feedback.id),
            created_at=feedback.created_at
        )

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
