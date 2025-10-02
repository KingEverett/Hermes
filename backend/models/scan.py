from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ScanStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ToolType(enum.Enum):
    NMAP = "nmap"
    MASSCAN = "masscan"
    NUCLEI = "nuclei"
    CUSTOM = "custom"

class Scan(BaseModel):
    __tablename__ = "scans"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    tool_type = Column(Enum(ToolType), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    raw_content = Column(Text)
    parsed_at = Column(DateTime(timezone=True))
    error_details = Column(Text)
    processing_time_ms = Column(Integer)

    # Relationships
    project = relationship("Project", back_populates="scans")

    def __repr__(self):
        return f"<Scan(id={self.id}, filename='{self.filename}', status='{self.status}')>"