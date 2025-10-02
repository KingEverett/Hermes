from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Project(BaseModel):
    __tablename__ = "projects"

    name = Column(String(255), nullable=False)
    description = Column(Text)
    project_metadata = Column(JSON)

    # Relationships
    scans = relationship("Scan", back_populates="project", cascade="all, delete-orphan")
    hosts = relationship("Host", back_populates="project", cascade="all, delete-orphan")
    export_jobs = relationship("ExportJob", back_populates="project", cascade="all, delete-orphan")
    attack_chains = relationship("AttackChain", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"