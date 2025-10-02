"""Unit tests for documentation models."""
import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from models.documentation import (
    DocumentationSection,
    DocumentationVersion,
    ResearchTemplate,
    SourceType,
    TemplateCategory
)
from models.project import Project


def test_create_documentation_section(test_db):
    """Test creating a documentation section."""
    # Create a project first
    project = Project(name="Test Project", description="Test")
    test_db.add(project)
    test_db.commit()

    # Create documentation section
    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="executive_summary",
        content="# Executive Summary\n\nTest content",
        source_type=SourceType.AUTOMATED,
        version=1
    )
    test_db.add(doc_section)
    test_db.commit()

    # Verify
    assert doc_section.id is not None
    assert doc_section.project_id == project.id
    assert doc_section.source_type == SourceType.AUTOMATED
    assert doc_section.version == 1
    assert doc_section.created_at is not None


def test_documentation_section_unique_constraint(test_db):
    """Test that duplicate entity_type/entity_id/section_name combinations are rejected."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    entity_id = uuid4()

    # Create first section
    doc_section1 = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=entity_id,
        section_name="summary",
        content="Content 1",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(doc_section1)
    test_db.commit()

    # Try to create duplicate section
    doc_section2 = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=entity_id,
        section_name="summary",
        content="Content 2",
        source_type=SourceType.MANUAL
    )
    test_db.add(doc_section2)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_source_type_enum_validation(test_db):
    """Test that only valid source types are accepted."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    # Valid source types
    valid_types = [SourceType.AUTOMATED, SourceType.MANUAL, SourceType.MIXED]
    for source_type in valid_types:
        doc = DocumentationSection(
            project_id=project.id,
            entity_type="service",
            entity_id=uuid4(),
            section_name=f"section_{source_type.value}",
            content="Test",
            source_type=source_type
        )
        test_db.add(doc)
    test_db.commit()

    # Verify all were created
    sections = test_db.query(DocumentationSection).all()
    assert len(sections) == 3


def test_create_documentation_version(test_db):
    """Test creating a documentation version."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    # Create section
    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="summary",
        content="Version 1 content",
        source_type=SourceType.AUTOMATED,
        version=1
    )
    test_db.add(doc_section)
    test_db.commit()

    # Create version history entry
    doc_version = DocumentationVersion(
        documentation_section_id=doc_section.id,
        version=1,
        content="Version 1 content",
        source_type=SourceType.AUTOMATED,
        changed_by="system"
    )
    test_db.add(doc_version)
    test_db.commit()

    assert doc_version.id is not None
    assert doc_version.version == 1
    assert doc_version.changed_by == "system"


def test_documentation_version_unique_constraint(test_db):
    """Test that duplicate section_id/version combinations are rejected."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="summary",
        content="Content",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(doc_section)
    test_db.commit()

    # Create first version
    version1 = DocumentationVersion(
        documentation_section_id=doc_section.id,
        version=1,
        content="Version 1",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(version1)
    test_db.commit()

    # Try to create duplicate version
    version2 = DocumentationVersion(
        documentation_section_id=doc_section.id,
        version=1,
        content="Also version 1",
        source_type=SourceType.MANUAL
    )
    test_db.add(version2)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_documentation_cascade_delete(test_db):
    """Test that deleting a section cascades to versions."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="summary",
        content="Content",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(doc_section)
    test_db.commit()

    # Create multiple versions
    for i in range(1, 4):
        version = DocumentationVersion(
            documentation_section_id=doc_section.id,
            version=i,
            content=f"Version {i}",
            source_type=SourceType.AUTOMATED
        )
        test_db.add(version)
    test_db.commit()

    # Verify versions exist
    versions = test_db.query(DocumentationVersion).filter_by(
        documentation_section_id=doc_section.id
    ).all()
    assert len(versions) == 3

    # Delete section
    test_db.delete(doc_section)
    test_db.commit()

    # Verify versions were also deleted
    versions = test_db.query(DocumentationVersion).filter_by(
        documentation_section_id=doc_section.id
    ).all()
    assert len(versions) == 0


def test_create_research_template(test_db):
    """Test creating a research template."""
    template = ResearchTemplate(
        name="Service Assessment Template",
        category=TemplateCategory.SERVICE,
        description="Template for service vulnerability assessment",
        template_content="# Service Assessment\n\n{service_name}",
        is_system=True,
        created_by="system"
    )
    test_db.add(template)
    test_db.commit()

    assert template.id is not None
    assert template.category == TemplateCategory.SERVICE
    assert template.is_system is True


def test_template_category_enum_validation(test_db):
    """Test that only valid template categories are accepted."""
    valid_categories = [
        TemplateCategory.HOST,
        TemplateCategory.SERVICE,
        TemplateCategory.VULNERABILITY,
        TemplateCategory.GENERAL
    ]

    for category in valid_categories:
        template = ResearchTemplate(
            name=f"Test {category.value}",
            category=category,
            template_content="Test content",
            is_system=False
        )
        test_db.add(template)
    test_db.commit()

    templates = test_db.query(ResearchTemplate).all()
    assert len(templates) == 4


def test_documentation_section_template_relationship(test_db):
    """Test the relationship between documentation sections and templates."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    # Create template
    template = ResearchTemplate(
        name="Test Template",
        category=TemplateCategory.HOST,
        template_content="Test content",
        is_system=True
    )
    test_db.add(template)
    test_db.commit()

    # Create section using template
    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="assessment",
        content="Content from template",
        source_type=SourceType.MANUAL,
        template_id=template.id
    )
    test_db.add(doc_section)
    test_db.commit()

    # Verify relationship
    assert doc_section.template is not None
    assert doc_section.template.id == template.id
    assert doc_section.template.name == "Test Template"


def test_template_delete_sets_null_in_section(test_db):
    """Test that deleting a template sets template_id to NULL in sections."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    template = ResearchTemplate(
        name="Test Template",
        category=TemplateCategory.HOST,
        template_content="Test",
        is_system=False
    )
    test_db.add(template)
    test_db.commit()

    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="test",
        content="Content",
        source_type=SourceType.MANUAL,
        template_id=template.id
    )
    test_db.add(doc_section)
    test_db.commit()

    # Delete template
    test_db.delete(template)
    test_db.commit()

    # Refresh section and verify template_id is NULL
    test_db.refresh(doc_section)
    assert doc_section.template_id is None


def test_documentation_section_versions_relationship(test_db):
    """Test the relationship between sections and their versions."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="summary",
        content="Current content",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(doc_section)
    test_db.commit()

    # Add versions
    for i in range(1, 4):
        version = DocumentationVersion(
            documentation_section_id=doc_section.id,
            version=i,
            content=f"Version {i} content",
            source_type=SourceType.AUTOMATED
        )
        test_db.add(version)
    test_db.commit()

    # Refresh and verify relationship
    test_db.refresh(doc_section)
    assert len(doc_section.versions) == 3
    # Versions should be ordered by version descending
    assert doc_section.versions[0].version == 3
    assert doc_section.versions[1].version == 2
    assert doc_section.versions[2].version == 1


def test_version_change_description(test_db):
    """Test that change descriptions are stored correctly."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    doc_section = DocumentationSection(
        project_id=project.id,
        entity_type="host",
        entity_id=uuid4(),
        section_name="summary",
        content="Content",
        source_type=SourceType.AUTOMATED
    )
    test_db.add(doc_section)
    test_db.commit()

    version = DocumentationVersion(
        documentation_section_id=doc_section.id,
        version=1,
        content="Original content",
        source_type=SourceType.AUTOMATED,
        changed_by="user@example.com",
        change_description="Initial automated generation"
    )
    test_db.add(version)
    test_db.commit()

    assert version.change_description == "Initial automated generation"
    assert version.changed_by == "user@example.com"