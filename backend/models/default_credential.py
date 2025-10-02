from sqlalchemy import Column, String, Text, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
import enum

class CredentialRisk(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DefaultCredential(BaseModel):
    __tablename__ = "default_credentials"

    # Service reference
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)

    # Credential information
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    description = Column(Text)

    # Risk assessment
    risk_level = Column(Enum(CredentialRisk), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0

    # Detection details
    detection_method = Column(String(100))  # How this was detected
    match_reason = Column(Text)  # Why this credential was flagged
    service_type = Column(String(50))  # SSH, HTTP, FTP, etc.
    product_name = Column(String(255))  # Apache, nginx, OpenSSH, etc.

    # Validation and remediation
    validated = Column(Boolean, default=False)
    false_positive = Column(Boolean, default=False)
    remediation_notes = Column(Text)
    remediation_completed = Column(Boolean, default=False)

    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True))
    remediated_at = Column(DateTime(timezone=True))

    # Additional context
    port = Column(String(10))  # Port where credential was detected
    banner_snippet = Column(Text)  # Relevant banner information

    # Relationships
    service = relationship("Service", back_populates="default_credentials")

    def __repr__(self):
        return f"<DefaultCredential(id={self.id}, service_id={self.service_id}, username='{self.username}', risk='{self.risk_level}')>"

    @property
    def is_critical(self):
        """Check if this is a critical risk credential."""
        return self.risk_level == CredentialRisk.CRITICAL

    @property
    def is_high_risk(self):
        """Check if this is high risk or above."""
        return self.risk_level in [CredentialRisk.CRITICAL, CredentialRisk.HIGH]

    @property
    def needs_immediate_attention(self):
        """Check if this credential needs immediate attention."""
        return self.is_critical and not self.validated and not self.false_positive

    def mark_as_validated(self, notes: str = None):
        """Mark credential as validated."""
        self.validated = True
        self.validated_at = func.now()
        if notes:
            self.remediation_notes = notes

    def mark_as_false_positive(self, notes: str = None):
        """Mark credential as false positive."""
        self.false_positive = True
        self.validated = True
        self.validated_at = func.now()
        if notes:
            self.remediation_notes = notes

    def mark_as_remediated(self, notes: str = None):
        """Mark credential issue as remediated."""
        self.remediation_completed = True
        self.remediated_at = func.now()
        if notes:
            self.remediation_notes = notes