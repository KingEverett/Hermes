"""API endpoints for documentation management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database.connection import get_db
from repositories.documentation_repository import (
    DocumentationSectionRepository,
    DocumentationVersionRepository,
    ResearchTemplateRepository
)
from api.schemas import (
    DocumentationSectionCreate,
    DocumentationSectionUpdate,
    DocumentationSectionResponse,
    DocumentationVersionResponse,
    DocumentationEntityResponse,
    ManualNoteCreate,
    RollbackRequest,
    ResearchTemplateCreate,
    ResearchTemplateUpdate,
    ResearchTemplateResponse
)
from models.documentation import SourceType, TemplateCategory

router = APIRouter(prefix="/api/v1", tags=["documentation"])


# Documentation section endpoints
@router.get(
    "/documentation/{entity_type}/{entity_id}",
    response_model=DocumentationEntityResponse
)
def get_entity_documentation(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all documentation sections for a specific entity."""
    repo = DocumentationSectionRepository(db)
    sections = repo.get_by_entity(entity_type, entity_id)

    return DocumentationEntityResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        sections=[DocumentationSectionResponse.model_validate(s) for s in sections]
    )


@router.post(
    "/documentation",
    response_model=DocumentationSectionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_documentation_section(
    section: DocumentationSectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new documentation section."""
    repo = DocumentationSectionRepository(db)

    # Check if section already exists
    existing = repo.get_by_entity_and_section(
        section.entity_type,
        section.entity_id,
        section.section_name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Documentation section '{section.section_name}' already exists for this entity"
        )

    new_section = repo.create(**section.model_dump())
    return DocumentationSectionResponse.model_validate(new_section)


@router.put(
    "/documentation/{entity_type}/{entity_id}",
    response_model=DocumentationSectionResponse
)
def update_documentation_section(
    entity_type: str,
    entity_id: UUID,
    update: DocumentationSectionUpdate,
    section_name: str = "default",
    db: Session = Depends(get_db)
):
    """Update a documentation section and create version history."""
    repo = DocumentationSectionRepository(db)

    # Find existing section
    section = repo.get_by_entity_and_section(entity_type, entity_id, section_name)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documentation section '{section_name}' not found for this entity"
        )

    # Determine new source type
    new_source_type = update.source_type
    if not new_source_type:
        # If updating automated content with manual edits, mark as mixed
        if section.source_type == SourceType.AUTOMATED:
            new_source_type = SourceType.MIXED
        else:
            new_source_type = section.source_type

    # Update with version history
    updated_section = repo.update_with_version(
        section.id,
        update.content,
        new_source_type,
        update.changed_by,
        update.change_description
    )

    return DocumentationSectionResponse.model_validate(updated_section)


@router.post(
    "/documentation/{entity_type}/{entity_id}/notes",
    response_model=DocumentationSectionResponse,
    status_code=status.HTTP_201_CREATED
)
def add_manual_research_note(
    entity_type: str,
    entity_id: UUID,
    note: ManualNoteCreate,
    db: Session = Depends(get_db)
):
    """Add a manual research note to an entity."""
    repo = DocumentationSectionRepository(db)

    # Check if note section exists
    existing = repo.get_by_entity_and_section(
        entity_type,
        entity_id,
        note.section_name
    )

    if existing:
        # Append to existing note
        new_content = f"{existing.content}\n\n---\n\n{note.content}"
        updated = repo.update_with_version(
            existing.id,
            new_content,
            SourceType.MANUAL,
            note.created_by,
            "Added manual research note"
        )
        return DocumentationSectionResponse.model_validate(updated)
    else:
        # Create new note section
        # Note: We need project_id - in a real implementation, we'd look this up
        # For now, raise an error requiring the project_id to be passed differently
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual note section does not exist. Create documentation section first."
        )


@router.get(
    "/documentation/sections/{doc_section_id}/versions",
    response_model=List[DocumentationVersionResponse]
)
def get_version_history(
    doc_section_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get version history for a documentation section."""
    version_repo = DocumentationVersionRepository(db)
    versions = version_repo.get_by_section(doc_section_id, skip=skip, limit=limit)

    return [DocumentationVersionResponse.model_validate(v) for v in versions]


@router.post(
    "/documentation/sections/{doc_section_id}/rollback/{version_id}",
    response_model=DocumentationSectionResponse
)
def rollback_to_version(
    doc_section_id: UUID,
    version_id: UUID,
    rollback_req: RollbackRequest,
    db: Session = Depends(get_db)
):
    """Rollback a documentation section to a previous version."""
    repo = DocumentationSectionRepository(db)

    section = repo.get_by_id(doc_section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documentation section not found"
        )

    rolled_back = repo.rollback_to_version(
        doc_section_id,
        version_id,
        rollback_req.changed_by
    )

    if not rolled_back:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found or does not belong to this section"
        )

    return DocumentationSectionResponse.model_validate(rolled_back)


# Template management endpoints
@router.get(
    "/templates",
    response_model=List[ResearchTemplateResponse]
)
def list_templates(
    category: TemplateCategory = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List research templates, optionally filtered by category."""
    repo = ResearchTemplateRepository(db)

    if category:
        templates = repo.get_by_category(category, skip=skip, limit=limit)
    else:
        templates = repo.get_all(skip=skip, limit=limit)

    return [ResearchTemplateResponse.model_validate(t) for t in templates]


@router.post(
    "/templates",
    response_model=ResearchTemplateResponse,
    status_code=status.HTTP_201_CREATED
)
def create_template(
    template: ResearchTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new research template."""
    repo = ResearchTemplateRepository(db)
    new_template = repo.create(**template.model_dump())
    return ResearchTemplateResponse.model_validate(new_template)


@router.get(
    "/templates/{template_id}",
    response_model=ResearchTemplateResponse
)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific research template."""
    repo = ResearchTemplateRepository(db)
    template = repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return ResearchTemplateResponse.model_validate(template)


@router.put(
    "/templates/{template_id}",
    response_model=ResearchTemplateResponse
)
def update_template(
    template_id: UUID,
    update: ResearchTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a research template."""
    repo = ResearchTemplateRepository(db)

    template = repo.get_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Don't allow updating system templates
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update system templates"
        )

    # Update only provided fields
    update_data = update.model_dump(exclude_unset=True)
    updated_template = repo.update(template_id, **update_data)

    return ResearchTemplateResponse.model_validate(updated_template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a research template."""
    repo = ResearchTemplateRepository(db)

    template = repo.get_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Don't allow deleting system templates
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system templates"
        )

    repo.delete(template_id)
    return None