"""Repository for documentation data access operations."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.documentation import (
    DocumentationSection,
    DocumentationVersion,
    ResearchTemplate,
    SourceType,
    TemplateCategory
)
from repositories.base import BaseRepository


class DocumentationSectionRepository(BaseRepository[DocumentationSection]):
    """Repository for DocumentationSection model."""

    def __init__(self, session: Session):
        super().__init__(session, DocumentationSection)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> List[DocumentationSection]:
        """Get all documentation sections for a specific entity."""
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.entity_type == entity_type,
                    self.model.entity_id == entity_id
                )
            )
            .all()
        )

    def get_by_entity_and_section(
        self,
        entity_type: str,
        entity_id: UUID,
        section_name: str
    ) -> Optional[DocumentationSection]:
        """Get a specific documentation section for an entity."""
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.entity_type == entity_type,
                    self.model.entity_id == entity_id,
                    self.model.section_name == section_name
                )
            )
            .first()
        )

    def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentationSection]:
        """Get all documentation sections for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_with_version(
        self,
        doc_id: UUID,
        content: str,
        source_type: SourceType,
        changed_by: Optional[str] = None,
        change_description: Optional[str] = None
    ) -> Optional[DocumentationSection]:
        """Update a documentation section and create a version history entry."""
        doc = self.get_by_id(doc_id)
        if not doc:
            return None

        # Create version history entry with previous content
        version_entry = DocumentationVersion(
            documentation_section_id=doc.id,
            version=doc.version,
            content=doc.content,
            source_type=doc.source_type,
            changed_by=changed_by,
            change_description=change_description
        )
        self.session.add(version_entry)

        # Update the section
        doc.content = content
        doc.source_type = source_type
        doc.version += 1

        self.session.commit()
        self.session.refresh(doc)
        return doc

    def rollback_to_version(
        self,
        doc_id: UUID,
        version_id: UUID,
        changed_by: Optional[str] = None
    ) -> Optional[DocumentationSection]:
        """Rollback a documentation section to a previous version."""
        doc = self.get_by_id(doc_id)
        if not doc:
            return None

        version_repo = DocumentationVersionRepository(self.session)
        target_version = version_repo.get_by_id(version_id)
        if not target_version or target_version.documentation_section_id != doc_id:
            return None

        # Create version entry for current state before rollback
        current_version_entry = DocumentationVersion(
            documentation_section_id=doc.id,
            version=doc.version,
            content=doc.content,
            source_type=doc.source_type,
            changed_by=changed_by,
            change_description=f"Rollback to version {target_version.version}"
        )
        self.session.add(current_version_entry)

        # Rollback to target version
        doc.content = target_version.content
        doc.source_type = target_version.source_type
        doc.version += 1

        self.session.commit()
        self.session.refresh(doc)
        return doc


class DocumentationVersionRepository(BaseRepository[DocumentationVersion]):
    """Repository for DocumentationVersion model."""

    def __init__(self, session: Session):
        super().__init__(session, DocumentationVersion)

    def get_by_section(
        self,
        section_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[DocumentationVersion]:
        """Get version history for a documentation section."""
        return (
            self.session.query(self.model)
            .filter(self.model.documentation_section_id == section_id)
            .order_by(self.model.version.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_specific_version(
        self,
        section_id: UUID,
        version_number: int
    ) -> Optional[DocumentationVersion]:
        """Get a specific version of a documentation section."""
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.documentation_section_id == section_id,
                    self.model.version == version_number
                )
            )
            .first()
        )


class ResearchTemplateRepository(BaseRepository[ResearchTemplate]):
    """Repository for ResearchTemplate model."""

    def __init__(self, session: Session):
        super().__init__(session, ResearchTemplate)

    def get_by_category(
        self,
        category: TemplateCategory,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResearchTemplate]:
        """Get all templates for a specific category."""
        return (
            self.session.query(self.model)
            .filter(self.model.category == category)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_system_templates(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResearchTemplate]:
        """Get all system templates."""
        return (
            self.session.query(self.model)
            .filter(self.model.is_system == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_templates(
        self,
        created_by: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ResearchTemplate]:
        """Get all user-created templates."""
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.is_system == False,
                    self.model.created_by == created_by
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )