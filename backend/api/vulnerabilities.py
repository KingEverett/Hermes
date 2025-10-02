from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field, ConfigDict

from database.connection import get_db
from models.service_vulnerability import ServiceVulnerability, ConfidenceLevel, ValidationMethod
from models.review_queue import ReviewQueue, ReviewStatus
from models.vulnerability import Vulnerability, Severity
from models.default_credential import DefaultCredential, CredentialRisk
from repositories.vulnerability_repository import VulnerabilityRepository
from repositories.service_vulnerability_repository import ServiceVulnerabilityRepository
from repositories.review_queue_repository import ReviewQueueRepository
from repositories.default_credential_repository import DefaultCredentialRepository
from services.research.version_analysis import VersionAnalysisService
from services.research.credential_detection import DefaultCredentialDetectionService

router = APIRouter(prefix="/api/v1", tags=["vulnerabilities"])

# Pydantic models for request/response
class VulnerabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    cve_id: str
    severity: str
    cvss_score: Optional[float]
    description: Optional[str]
    product: Optional[str]
    vendor: Optional[str]

class ServiceVulnerabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    service_id: str
    vulnerability: VulnerabilityResponse
    confidence: str
    confidence_score: Optional[float]
    version_matched: Optional[str]
    validated: bool
    false_positive: bool
    detected_at: Optional[datetime]

class ReviewQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    service_id: str
    vulnerability_id: str
    status: str
    confidence: str
    priority: Optional[str]
    reviewer: Optional[str]
    assigned_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    rejection_reason: Optional[str]
    detection_method: Optional[str]
    version_extracted: Optional[str]
    auto_assigned: Optional[datetime]

class ReviewRequest(BaseModel):
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = Field(None, description="Review notes")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (required if action is reject)")

class DefaultCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    service_id: str
    username: str
    password: str
    description: Optional[str]
    risk_level: str
    confidence: float
    service_type: Optional[str]
    product_name: Optional[str]
    validated: bool
    false_positive: bool
    remediation_completed: bool
    detected_at: Optional[datetime]

class AnalysisRequest(BaseModel):
    include_credentials: bool = Field(True, description="Include default credential detection")
    confidence_threshold: float = Field(0.4, description="Minimum confidence threshold for results")

# Service Analysis Endpoints
@router.post("/services/{service_id}/analyze")
async def analyze_service(
    service_id: str,
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """Trigger vulnerability and credential analysis for a service."""
    from repositories.service import ServiceRepository

    service_repo = ServiceRepository(db)
    vuln_repo = VulnerabilityRepository(db)
    service_vuln_repo = ServiceVulnerabilityRepository(db)
    review_queue_repo = ReviewQueueRepository(db)
    credential_repo = DefaultCredentialRepository(db)

    # Get service
    service = service_repo.get_by_id(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    results = {
        "service_id": service_id,
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "vulnerability_analysis": {},
        "credential_analysis": {},
        "performance_metrics": {}
    }

    # Vulnerability analysis
    version_service = VersionAnalysisService(
        vulnerability_repo=vuln_repo,
        service_vuln_repo=service_vuln_repo,
        review_queue_repo=review_queue_repo
    )

    vuln_results = version_service.analyze_service_complete(service)
    results["vulnerability_analysis"] = vuln_results

    # Performance validation
    perf_results = version_service.validate_performance(service)
    results["performance_metrics"] = perf_results

    # Credential analysis if requested
    if request.include_credentials:
        credential_service = DefaultCredentialDetectionService()
        cred_results = credential_service.analyze_service_credentials(service)

        # Store credential findings
        for match in cred_results.get('matches', []):
            if match['confidence'] >= request.confidence_threshold:
                credential_repo.create_credential_finding(
                    service_id=service_id,
                    username=match['username'],
                    password=match['password'],
                    description=match['description'],
                    risk_level=CredentialRisk(match['risk_level']),
                    confidence=match['confidence'],
                    detection_method="automated_analysis",
                    match_reason=match['match_reason'],
                    service_type=cred_results['service_type'],
                    product_name=cred_results['product'],
                    port=str(cred_results['port'])
                )

        results["credential_analysis"] = cred_results

    return results

@router.get("/services/{service_id}/vulnerabilities", response_model=List[ServiceVulnerabilityResponse])
async def get_service_vulnerabilities(
    service_id: str,
    validated_only: bool = Query(False, description="Return only validated vulnerabilities"),
    db: Session = Depends(get_db)
):
    """Get vulnerabilities identified for a service."""
    service_vuln_repo = ServiceVulnerabilityRepository(db)

    if validated_only:
        vulnerabilities = service_vuln_repo.find_validated()
        vulnerabilities = [v for v in vulnerabilities if v.service_id == service_id]
    else:
        vulnerabilities = service_vuln_repo.find_by_service_id(service_id)

    return vulnerabilities

@router.get("/services/{service_id}/credentials", response_model=List[DefaultCredentialResponse])
async def get_service_credentials(
    service_id: str,
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    unvalidated_only: bool = Query(False, description="Return only unvalidated credentials"),
    db: Session = Depends(get_db)
):
    """Get default credentials identified for a service."""
    credential_repo = DefaultCredentialRepository(db)

    credentials = credential_repo.find_by_service_id(service_id)

    # Apply filters
    if risk_level:
        credentials = [c for c in credentials if c.risk_level.value == risk_level.lower()]

    if unvalidated_only:
        credentials = [c for c in credentials if not c.validated]

    return credentials

# Review Queue Management Endpoints
@router.get("/review-queue", response_model=List[ReviewQueueResponse])
async def get_review_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    confidence: Optional[str] = Query(None, description="Filter by confidence level"),
    reviewer: Optional[str] = Query(None, description="Filter by assigned reviewer"),
    limit: int = Query(50, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
):
    """Get manual review queue items."""
    review_repo = ReviewQueueRepository(db)

    if status:
        items = review_repo.find_by_status(ReviewStatus(status.upper()))
    elif priority:
        items = review_repo.find_by_priority(priority.lower())
    elif confidence:
        items = review_repo.find_by_confidence(ConfidenceLevel(confidence.upper()))
    elif reviewer:
        items = review_repo.find_by_reviewer(reviewer)
    else:
        items = review_repo.find_pending()

    return items[:limit]

@router.get("/review-queue/next")
async def get_next_review_item(
    priority_order: List[str] = Query(["high", "medium", "low"], description="Priority order for selection"),
    db: Session = Depends(get_db)
):
    """Get the next item that should be reviewed."""
    review_repo = ReviewQueueRepository(db)

    next_item = review_repo.get_next_for_review(priority_order)
    if not next_item:
        raise HTTPException(status_code=404, detail="No items pending review")

    return next_item

@router.post("/review-queue/{item_id}/assign")
async def assign_review_item(
    item_id: str,
    reviewer_id: str,
    db: Session = Depends(get_db)
):
    """Assign a review item to a reviewer."""
    review_repo = ReviewQueueRepository(db)

    success = review_repo.assign_to_reviewer(item_id, reviewer_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not assign item (may already be assigned or completed)")

    return {"message": "Item assigned successfully", "reviewer_id": reviewer_id}

@router.put("/review-queue/{item_id}")
async def update_review_item(
    item_id: str,
    request: ReviewRequest,
    reviewer_id: str,
    db: Session = Depends(get_db)
):
    """Update review queue item status (approve/reject)."""
    review_repo = ReviewQueueRepository(db)
    service_vuln_repo = ServiceVulnerabilityRepository(db)

    if request.action == "approve":
        success = review_repo.approve_item(item_id, reviewer_id, request.notes)
        if success:
            # Also mark the associated ServiceVulnerability as validated
            item = review_repo.get_by_id(item_id)
            if item and item.service_vulnerability_id:
                service_vuln_repo.mark_as_validated(
                    item.service_vulnerability_id,
                    ValidationMethod.MANUAL,
                    f"Approved in review queue: {request.notes or 'No notes'}"
                )
    elif request.action == "reject":
        if not request.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        success = review_repo.reject_item(item_id, reviewer_id, request.rejection_reason, request.notes)
        if success:
            # Mark associated ServiceVulnerability as false positive
            item = review_repo.get_by_id(item_id)
            if item and item.service_vulnerability_id:
                service_vuln_repo.mark_as_false_positive(
                    item.service_vulnerability_id,
                    f"Rejected in review queue: {request.rejection_reason}"
                )
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    if not success:
        raise HTTPException(status_code=400, detail="Could not update review item")

    action_past_tense = "approved" if request.action == "approve" else "rejected"
    return {"message": f"Item {action_past_tense} successfully"}

# Bulk Operations
@router.post("/review-queue/bulk-approve")
async def bulk_approve_low_risk(
    max_cvss_score: float = Query(4.0, description="Maximum CVSS score for auto-approval"),
    db: Session = Depends(get_db)
):
    """Bulk approve low-risk items."""
    review_repo = ReviewQueueRepository(db)

    count = review_repo.bulk_approve_low_risk(max_cvss_score)
    return {"message": f"Approved {count} low-risk items"}

@router.post("/vulnerabilities/bulk-validate")
async def bulk_validate_high_confidence(db: Session = Depends(get_db)):
    """Bulk validate all high confidence vulnerability matches."""
    service_vuln_repo = ServiceVulnerabilityRepository(db)

    count = service_vuln_repo.bulk_validate_high_confidence()
    return {"message": f"Validated {count} high confidence matches"}

@router.post("/credentials/bulk-validate")
async def bulk_validate_low_confidence_credentials(
    max_confidence: float = Query(0.5, description="Maximum confidence for auto-validation"),
    db: Session = Depends(get_db)
):
    """Bulk validate low confidence credential detections."""
    credential_repo = DefaultCredentialRepository(db)

    count = credential_repo.bulk_validate_low_confidence(max_confidence)
    return {"message": f"Validated {count} low confidence credential detections"}

# Statistics and Reporting
@router.get("/review-queue/statistics")
async def get_review_queue_statistics(db: Session = Depends(get_db)):
    """Get review queue statistics."""
    review_repo = ReviewQueueRepository(db)
    return review_repo.get_queue_statistics()

@router.get("/vulnerabilities/statistics")
async def get_vulnerability_statistics(db: Session = Depends(get_db)):
    """Get vulnerability detection statistics."""
    vuln_repo = VulnerabilityRepository(db)
    service_vuln_repo = ServiceVulnerabilityRepository(db)

    return {
        "vulnerability_database": vuln_repo.get_statistics(),
        "service_vulnerabilities": service_vuln_repo.get_validation_statistics()
    }

@router.get("/credentials/statistics")
async def get_credential_statistics(db: Session = Depends(get_db)):
    """Get default credential detection statistics."""
    credential_repo = DefaultCredentialRepository(db)
    detection_service = DefaultCredentialDetectionService()

    return {
        "detection_database": detection_service.get_credential_statistics(),
        "findings": credential_repo.get_statistics()
    }

@router.get("/reviewer/{reviewer_id}/workload")
async def get_reviewer_workload(
    reviewer_id: str,
    db: Session = Depends(get_db)
):
    """Get workload statistics for a specific reviewer."""
    review_repo = ReviewQueueRepository(db)
    return review_repo.get_reviewer_workload(reviewer_id)

# Project-level Analysis
@router.post("/projects/{project_id}/analyze")
async def analyze_project_services(
    project_id: str,
    include_credentials: bool = Query(True, description="Include credential analysis"),
    db: Session = Depends(get_db)
):
    """Trigger vulnerability analysis for all services in a project."""
    from repositories.service import ServiceRepository

    service_repo = ServiceRepository(db)

    # Get all services for the project
    services = service_repo.find_by_project_id(project_id)
    if not services:
        raise HTTPException(status_code=404, detail="No services found for project")

    results = {
        "project_id": project_id,
        "total_services": len(services),
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "services_analyzed": 0,
        "total_vulnerabilities": 0,
        "total_credentials": 0,
        "average_analysis_time": 0
    }

    total_time = 0

    for service in services:
        # Analyze each service
        analysis_request = AnalysisRequest(include_credentials=include_credentials)
        service_results = await analyze_service(service.id, analysis_request, db)

        results["services_analyzed"] += 1
        results["total_vulnerabilities"] += service_results["vulnerability_analysis"]["vulnerabilities_found"]

        if include_credentials:
            results["total_credentials"] += service_results["credential_analysis"]["credentials_found"]

        total_time += service_results["performance_metrics"]["analysis_time_seconds"]

    results["average_analysis_time"] = total_time / len(services) if services else 0

    return results

@router.get("/projects/{project_id}/review-queue", response_model=List[ReviewQueueResponse])
async def get_project_review_queue(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get review queue items for a specific project."""
    from repositories.service import ServiceRepository

    service_repo = ServiceRepository(db)
    review_repo = ReviewQueueRepository(db)

    # Get all services for the project
    services = service_repo.find_by_project_id(project_id)
    service_ids = [service.id for service in services]

    # Get review items for these services
    all_items = []
    for service_id in service_ids:
        items = review_repo.find_by_service_id(service_id)
        if status:
            items = [item for item in items if item.status.value.lower() == status.lower()]
        all_items.extend(items)

    # Sort by priority and date
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_items.sort(key=lambda x: (priority_order.get(x.priority, 3), x.auto_assigned))

    return all_items