from sqlalchemy import Column, String, Text, Integer, ForeignKey, Float, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class Protocol(enum.Enum):
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"

class Service(BaseModel):
    __tablename__ = "services"

    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(Enum(Protocol), nullable=False)
    service_name = Column(String(100))
    product = Column(String(255))
    version = Column(String(255))
    banner = Column(Text)
    cpe = Column(String(255))
    confidence = Column(Float)

    # Relationships
    host = relationship("Host", back_populates="services")
    vulnerabilities = relationship("ServiceVulnerability", back_populates="service", cascade="all, delete-orphan")
    default_credentials = relationship("DefaultCredential", back_populates="service", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('host_id', 'port', 'protocol', name='unique_host_port_protocol'),
    )

    def __repr__(self):
        return f"<Service(id={self.id}, port={self.port}, protocol='{self.protocol}', service_name='{self.service_name}')>"