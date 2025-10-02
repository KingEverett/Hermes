from sqlalchemy import Column, String, Text, Integer, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class SourceType(str, enum.Enum):
    """Enum for documentation content source types."""
    AUTOMATED = "automated"
    MANUAL = "manual"
    MIXED = "mixed"

class TemplateCategory(str, enum.Enum):
    """Enum for research template categories."""
    HOST = "host"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    GENERAL = "general"

class DocumentationSection(BaseModel):
    """Model for storing editable documentation sections."""
    __tablename__ = "documentation_sections"
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'section_name', name='uq_entity_section'),
    )

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'host', 'service', 'vulnerability', 'project'
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    section_name = Column(String(100), nullable=False)  # e.g., "executive_summary", "vulnerability_analysis"
    content = Column(Text, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False, default=SourceType.AUTOMATED)
    template_id = Column(UUID(as_uuid=True), ForeignKey("research_templates.id", ondelete="SET NULL"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(255), nullable=True)

    # Relationships
    project = relationship("Project", backref="documentation_sections")
    template = relationship("ResearchTemplate", backref="documentation_sections")
    versions = relationship("DocumentationVersion", back_populates="documentation_section", cascade="all, delete-orphan", order_by="DocumentationVersion.version.desc()")

    def __repr__(self):
        return f"<DocumentationSection(id={self.id}, entity_type='{self.entity_type}', section_name='{self.section_name}', version={self.version})>"

class DocumentationVersion(BaseModel):
    """Model for storing version history of documentation sections."""
    __tablename__ = "documentation_versions"
    __table_args__ = (
        UniqueConstraint('documentation_section_id', 'version', name='uq_section_version'),
    )

    documentation_section_id = Column(UUID(as_uuid=True), ForeignKey("documentation_sections.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    changed_by = Column(String(255), nullable=True)
    change_description = Column(Text, nullable=True)

    # Relationships
    documentation_section = relationship("DocumentationSection", back_populates="versions")

    def __repr__(self):
        return f"<DocumentationVersion(id={self.id}, section_id={self.documentation_section_id}, version={self.version})>"

class ResearchTemplate(BaseModel):
    """Model for storing research templates for manual documentation."""
    __tablename__ = "research_templates"

    name = Column(String(255), nullable=False)
    category = Column(Enum(TemplateCategory), nullable=False)
    description = Column(Text, nullable=True)
    template_content = Column(Text, nullable=False)
    is_system = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<ResearchTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"