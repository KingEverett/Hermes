"""Export job model for tracking documentation export tasks."""

from sqlalchemy import Column, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from models.base import Base
import uuid


class ExportFormat(str, enum.Enum):
    """Supported export formats."""
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


class JobStatus(str, enum.Enum):
    """Export job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJob(Base):
    """Model for tracking export job status and results."""

    __tablename__ = "export_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    format = Column(Enum(ExportFormat), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    file_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="export_jobs")

    def __repr__(self):
        return f"<ExportJob(id={self.id}, project_id={self.project_id}, format={self.format}, status={self.status})>"