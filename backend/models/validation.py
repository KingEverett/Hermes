from sqlalchemy import Column, ForeignKey, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class ValidationQueue(BaseModel):
    """Model for tracking findings that require manual validation"""
    __tablename__ = "validation_queue"

    finding_type = Column(String(100), nullable=False)  # 'service_vulnerability' | 'host_finding'
    finding_id = Column(UUID(as_uuid=True), nullable=False)
    priority = Column(String(20), nullable=False)  # 'critical' | 'high' | 'medium' | 'low'
    status = Column(String(50), nullable=False, default='pending')  # 'pending' | 'in_review' | 'completed'
    assigned_to = Column(String(255))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)

    def __repr__(self):
        return f"<ValidationQueue(finding_type={self.finding_type}, finding_id={self.finding_id}, priority={self.priority})>"


class ValidationFeedback(BaseModel):
    """Model for collecting user feedback on research accuracy"""
    __tablename__ = "validation_feedback"

    finding_id = Column(UUID(as_uuid=True), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # 'false_positive' | 'false_negative' | 'correct'
    user_comment = Column(Text, nullable=False)
    user_id = Column(String(255))

    def __repr__(self):
        return f"<ValidationFeedback(finding_id={self.finding_id}, feedback_type={self.feedback_type})>"
