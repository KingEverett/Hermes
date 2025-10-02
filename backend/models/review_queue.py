from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
from .service_vulnerability import ConfidenceLevel
import enum

class ReviewStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_REVIEW = "in_review"

class ReviewQueue(BaseModel):
    __tablename__ = "review_queue"

    # Foreign keys
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False)
    service_vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("service_vulnerabilities.id", ondelete="CASCADE"))

    # Review status and metadata
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    confidence = Column(Enum(ConfidenceLevel), nullable=False)
    priority = Column(String(10), default="medium")  # 'high', 'medium', 'low'

    # Review assignment and tracking
    reviewer = Column(String(255))  # Username or ID of assigned reviewer
    assigned_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))

    # Review notes and reasoning
    review_notes = Column(Text)
    rejection_reason = Column(Text)
    evidence_notes = Column(Text)  # Additional evidence for manual verification

    # Context information for reviewer
    detection_method = Column(String(100))  # How this vulnerability was detected
    version_extracted = Column(String(255))  # Version that triggered the match
    banner_snippet = Column(Text)  # Relevant part of service banner

    # Auto-assignment metadata
    auto_assigned = Column(DateTime(timezone=True), server_default=func.now())
    escalation_level = Column(String(20), default="standard")  # 'standard', 'urgent', 'critical'

    # Relationships
    service = relationship("Service")
    vulnerability = relationship("Vulnerability")
    service_vulnerability = relationship("ServiceVulnerability")

    def __repr__(self):
        return f"<ReviewQueue(id={self.id}, status='{self.status}', confidence='{self.confidence}')>"

    @property
    def is_pending(self):
        """Check if review item is still pending."""
        return self.status == ReviewStatus.PENDING

    @property
    def is_approved(self):
        """Check if review item was approved."""
        return self.status == ReviewStatus.APPROVED

    @property
    def is_rejected(self):
        """Check if review item was rejected."""
        return self.status == ReviewStatus.REJECTED

    def assign_reviewer(self, reviewer_id: str):
        """Assign a reviewer to this item."""
        self.reviewer = reviewer_id
        self.assigned_at = func.now()
        self.status = ReviewStatus.IN_REVIEW

    def approve(self, reviewer_id: str, notes: str = None):
        """Approve the vulnerability match."""
        self.status = ReviewStatus.APPROVED
        self.reviewer = reviewer_id
        self.reviewed_at = func.now()
        if notes:
            self.review_notes = notes

    def reject(self, reviewer_id: str, reason: str, notes: str = None):
        """Reject the vulnerability match."""
        self.status = ReviewStatus.REJECTED
        self.reviewer = reviewer_id
        self.reviewed_at = func.now()
        self.rejection_reason = reason
        if notes:
            self.review_notes = notes