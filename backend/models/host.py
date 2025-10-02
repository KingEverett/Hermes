from sqlalchemy import Column, String, Text, ForeignKey, Integer, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from .base import BaseModel

class Host(BaseModel):
    __tablename__ = "hosts"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=False)  # String for SQLite compatibility (INET for PostgreSQL)
    hostname = Column(String(255))
    os_family = Column(String(100))
    os_details = Column(Text)
    mac_address = Column(String(17))
    status = Column(String(20), default="up")
    confidence_score = Column(Float)
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    host_metadata = Column(JSON)

    # Relationships
    project = relationship("Project", back_populates="hosts")
    services = relationship("Service", back_populates="host", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('project_id', 'ip_address', name='unique_project_ip'),
    )

    def __repr__(self):
        return f"<Host(id={self.id}, ip_address='{self.ip_address}', hostname='{self.hostname}')>"