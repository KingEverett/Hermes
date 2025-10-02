from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from models.scan import ScanStatus, ToolType
from models.service import Protocol
from models.vulnerability import Severity
from models.export_job import ExportFormat, JobStatus
from models.documentation import SourceType, TemplateCategory

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    project_metadata: Optional[dict] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

class ScanBase(BaseModel):
    filename: str
    tool_type: ToolType
    raw_content: Optional[str] = None

class ScanCreate(ScanBase):
    project_id: UUID

class ScanResponse(ScanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: ScanStatus
    parsed_at: Optional[datetime] = None
    error_details: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class HostBase(BaseModel):
    ip_address: str
    hostname: Optional[str] = None
    os_family: Optional[str] = None
    os_details: Optional[str] = None
    mac_address: Optional[str] = None
    status: Optional[str] = "up"
    confidence_score: Optional[float] = None
    host_metadata: Optional[dict] = None

class HostCreate(HostBase):
    project_id: UUID

class HostResponse(HostBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class ServiceBase(BaseModel):
    port: int
    protocol: Protocol
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    banner: Optional[str] = None
    cpe: Optional[str] = None
    confidence: Optional[float] = None

class ServiceCreate(ServiceBase):
    host_id: UUID

class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    created_at: datetime
    updated_at: datetime

class VulnerabilityBase(BaseModel):
    cve_id: str
    cvss_score: Optional[float] = None
    severity: Severity
    description: Optional[str] = None
    remediation: Optional[str] = None
    exploit_available: bool = False
    references: Optional[dict] = None
    cisa_kev: bool = False

class VulnerabilityCreate(VulnerabilityBase):
    pass

class VulnerabilityResponse(VulnerabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

# Scan Import Schemas
class ScanImportResponse(BaseModel):
    """Response for scan import requests"""
    scan_id: UUID
    filename: str
    status: str
    message: str

class ScanImportResult(BaseModel):
    """Result of completed scan import"""
    scan_id: UUID
    success: bool
    hosts_imported: int = 0
    services_imported: int = 0
    hosts_updated: int = 0
    services_updated: int = 0
    processing_time_ms: int = 0
    error_message: Optional[str] = None
    warnings: List[str] = []

class ImportProgress(BaseModel):
    """Progress tracking for scan imports"""
    total_hosts: int = 0
    processed_hosts: int = 0
    total_services: int = 0
    processed_services: int = 0
    current_stage: str = "starting"
    percentage: float = 0.0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


class ExportRequest(BaseModel):
    """Request model for export endpoint."""
    format: ExportFormat = ExportFormat.MARKDOWN
    include_graph: bool = False
    include_attack_chains: bool = True


class ExportJobResponse(BaseModel):
    """Response model for export job."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    format: ExportFormat
    status: JobStatus
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# Documentation Schemas
class DocumentationSectionBase(BaseModel):
    """Base schema for documentation sections."""
    entity_type: str
    entity_id: UUID
    section_name: str
    content: str
    source_type: SourceType = SourceType.AUTOMATED
    template_id: Optional[UUID] = None


class DocumentationSectionCreate(DocumentationSectionBase):
    """Schema for creating a documentation section."""
    project_id: UUID
    created_by: Optional[str] = None


class DocumentationSectionUpdate(BaseModel):
    """Schema for updating a documentation section."""
    content: str
    source_type: Optional[SourceType] = None
    change_description: Optional[str] = None
    changed_by: Optional[str] = None


class DocumentationSectionResponse(DocumentationSectionBase):
    """Response schema for documentation section."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    version: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentationVersionResponse(BaseModel):
    """Response schema for documentation version."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    documentation_section_id: UUID
    version: int
    content: str
    source_type: SourceType
    changed_by: Optional[str] = None
    change_description: Optional[str] = None
    created_at: datetime


class DocumentationEntityResponse(BaseModel):
    """Response schema for all documentation sections of an entity."""
    entity_type: str
    entity_id: UUID
    sections: List[DocumentationSectionResponse]


class ManualNoteCreate(BaseModel):
    """Schema for creating a manual research note."""
    content: str
    section_name: str = "manual_research"
    template_id: Optional[UUID] = None
    created_by: Optional[str] = None


class RollbackRequest(BaseModel):
    """Schema for rollback request."""
    changed_by: Optional[str] = None


# Research Template Schemas
class ResearchTemplateBase(BaseModel):
    """Base schema for research templates."""
    name: str
    category: TemplateCategory
    description: Optional[str] = None
    template_content: str


class ResearchTemplateCreate(ResearchTemplateBase):
    """Schema for creating a research template."""
    is_system: bool = False
    created_by: Optional[str] = None


class ResearchTemplateUpdate(BaseModel):
    """Schema for updating a research template."""
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None


class ResearchTemplateResponse(ResearchTemplateBase):
    """Response schema for research template."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_system: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime