from sqlalchemy import Column, ForeignKey, DateTime, String, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class QualityMetrics(BaseModel):
    """Model for storing quality control metrics"""
    __tablename__ = "quality_metrics"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    metric_type = Column(String(100), nullable=False)  # 'accuracy_rate' | 'false_positive_rate' | 'coverage'
    value = Column(Float, nullable=False)
    metric_metadata = Column(JSON)  # JSONB for flexible metrics storage
    calculated_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    project = relationship("Project")

    def __repr__(self):
        return f"<QualityMetrics(project_id={self.project_id}, metric_type={self.metric_type}, value={self.value})>"
