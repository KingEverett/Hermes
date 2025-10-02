"""Integration tests for export with manual documentation content."""

import pytest
from uuid import uuid4
from datetime import datetime

from models.documentation import DocumentationSection, SourceType
from services.documentation import DocumentationService


class TestExportIntegration:
    """Test suite for documentation export with manual research content."""

    def test_merge_documentation_with_manual_sections(self, test_db, sample_project):
        """Test merging automated and manual documentation."""
        service = DocumentationService(test_db)

        # Create manual documentation section
        doc_section = DocumentationSection(
            id=uuid4(),
            project_id=sample_project.id,
            entity_type="host",
            entity_id=uuid4(),
            section_name="manual_notes",
            content="# Manual Research\n\nThis is a manual note.",
            source_type=SourceType.MANUAL,
            version=1,
            created_by="analyst@example.com"
        )
        test_db.add(doc_section)
        test_db.commit()

        # Generate markdown
        automated_content = "# Automated Report\n\nAutomated findings..."
        merged = service._merge_documentation(automated_content, [doc_section])

        # Verify merged content
        assert "# Automated Report" in merged
        assert "# Manual Research Notes" in merged
        assert "✏️ MANUAL" in merged
        assert "This is a manual note" in merged
        assert "analyst@example.com" in merged

    def test_merge_documentation_with_mixed_content(self, test_db, sample_project):
        """Test merging with mixed automated/manual content."""
        service = DocumentationService(test_db)

        doc_section = DocumentationSection(
            id=uuid4(),
            project_id=sample_project.id,
            entity_type="service",
            entity_id=uuid4(),
            section_name="vuln_analysis",
            content="# Mixed Analysis\n\nOriginal automated + manual additions.",
            source_type=SourceType.MIXED,
            version=2,
            created_by="analyst@example.com"
        )
        test_db.add(doc_section)
        test_db.commit()

        automated_content = "# Report\n\nAutomated data"
        merged = service._merge_documentation(automated_content, [doc_section])

        assert "🔀 MIXED" in merged
        assert "Mixed Analysis" in merged

    def test_merge_documentation_no_manual_sections(self, test_db):
        """Test merge with no manual sections returns original content."""
        service = DocumentationService(test_db)

        automated_content = "# Report\n\nOnly automated content"
        merged = service._merge_documentation(automated_content, [])

        assert merged == automated_content
        assert "Manual Research Notes" not in merged

    def test_merge_documentation_multiple_entities(self, test_db, sample_project):
        """Test merging documentation from multiple entities."""
        service = DocumentationService(test_db)

        sections = []
        for entity_type in ["host", "service", "vulnerability"]:
            doc = DocumentationSection(
                id=uuid4(),
                project_id=sample_project.id,
                entity_type=entity_type,
                entity_id=uuid4(),
                section_name="notes",
                content=f"# {entity_type.title()} Notes\n\nDetailed notes here.",
                source_type=SourceType.MANUAL,
                version=1,
                created_by="analyst@example.com"
            )
            sections.append(doc)
            test_db.add(doc)

        test_db.commit()

        automated_content = "# Automated Report"
        merged = service._merge_documentation(automated_content, sections)

        # Verify all entity types are included
        assert "HOST:" in merged
        assert "SERVICE:" in merged
        assert "VULNERABILITY:" in merged

    def test_export_includes_manual_content(self, test_db, sample_project, tmp_path):
        """Test that exported markdown includes manual content."""
        service = DocumentationService(test_db)

        # Create manual documentation
        doc_section = DocumentationSection(
            id=uuid4(),
            project_id=sample_project.id,
            entity_type="host",
            entity_id=uuid4(),
            section_name="manual_analysis",
            content="# Security Analysis\n\nManual vulnerability assessment results.",
            source_type=SourceType.MANUAL,
            version=1,
            created_by="pentester@example.com"
        )
        test_db.add(doc_section)
        test_db.commit()

        # Export to file
        output_file = tmp_path / "test_export.md"
        result_path = service.export_to_file(sample_project.id, str(output_file))

        # Read exported file
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify manual content is included
        assert "Manual Research Notes" in content
        assert "Security Analysis" in content
        assert "pentester@example.com" in content
        assert "✏️ MANUAL" in content

    def test_export_visual_distinction_markers(self, test_db, sample_project, tmp_path):
        """Test that export includes visual distinction markers."""
        service = DocumentationService(test_db)

        # Create sections with different source types
        sections = [
            DocumentationSection(
                id=uuid4(),
                project_id=sample_project.id,
                entity_type="host",
                entity_id=uuid4(),
                section_name="manual",
                content="Manual content",
                source_type=SourceType.MANUAL,
                version=1
            ),
            DocumentationSection(
                id=uuid4(),
                project_id=sample_project.id,
                entity_type="service",
                entity_id=uuid4(),
                section_name="mixed",
                content="Mixed content",
                source_type=SourceType.MIXED,
                version=1
            ),
        ]

        for section in sections:
            test_db.add(section)
        test_db.commit()

        output_file = tmp_path / "test_markers.md"
        result_path = service.export_to_file(sample_project.id, str(output_file))

        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify all markers are present
        assert "<!-- MANUAL RESEARCH -->" in content
        assert "<!-- MIXED CONTENT -->" in content
        assert "✏️ MANUAL" in content
        assert "🔀 MIXED" in content


# Fixtures
@pytest.fixture
def sample_project(test_db):
    """Create a sample project for testing."""
    from models.project import Project

    project = Project(
        id=uuid4(),
        name="Test Project",
        description="Test project for export integration"
    )
    test_db.add(project)
    test_db.commit()
    return project
