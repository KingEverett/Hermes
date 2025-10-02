"""Integration tests for documentation API endpoints."""
import pytest
from uuid import uuid4


def test_create_documentation_section(client):
    """Test creating a documentation section."""
    # Create a project first
    project_data = {"name": "Test Project"}
    project_response = client.post("/api/v1/projects/", json=project_data)
    project_id = project_response.json()["id"]

    host_id = str(uuid4())

    # Create documentation section
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "executive_summary",
        "content": "# Executive Summary\n\nTest content",
        "source_type": "automated"
    }

    response = client.post("/api/v1/documentation", json=doc_data)
    assert response.status_code == 201

    data = response.json()
    assert data["entity_type"] == "host"
    assert data["entity_id"] == host_id
    assert data["section_name"] == "executive_summary"
    assert data["content"] == "# Executive Summary\n\nTest content"
    assert data["source_type"] == "automated"
    assert data["version"] == 1
    assert "id" in data


def test_get_entity_documentation(client):
    """Test retrieving all documentation for an entity."""
    # Create a project
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]

    host_id = str(uuid4())

    # Create multiple documentation sections
    for i, section_name in enumerate(["summary", "findings", "recommendations"]):
        doc_data = {
            "project_id": project_id,
            "entity_type": "host",
            "entity_id": host_id,
            "section_name": section_name,
            "content": f"Content for {section_name}",
            "source_type": "automated"
        }
        client.post("/api/v1/documentation", json=doc_data)

    # Get all documentation for the entity
    response = client.get(f"/api/v1/documentation/host/{host_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["entity_type"] == "host"
    assert data["entity_id"] == host_id
    assert len(data["sections"]) == 3

    section_names = [s["section_name"] for s in data["sections"]]
    assert "summary" in section_names
    assert "findings" in section_names
    assert "recommendations" in section_names


def test_update_documentation_section(client):
    """Test updating a documentation section and creating version history."""
    # Setup
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]
    host_id = str(uuid4())

    # Create initial documentation
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "summary",
        "content": "Original content",
        "source_type": "automated"
    }
    create_response = client.post("/api/v1/documentation", json=doc_data)
    assert create_response.status_code == 201

    # Update the documentation
    update_data = {
        "content": "Updated content with manual edits",
        "changed_by": "test_user",
        "change_description": "Added manual findings"
    }
    response = client.put(
        f"/api/v1/documentation/host/{host_id}?section_name=summary",
        json=update_data
    )
    assert response.status_code == 200

    data = response.json()
    assert data["content"] == "Updated content with manual edits"
    assert data["version"] == 2
    # Should be mixed since automated content was edited manually
    assert data["source_type"] == "mixed"


def test_get_version_history(client):
    """Test retrieving version history for a documentation section."""
    # Setup
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]
    host_id = str(uuid4())

    # Create documentation
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "summary",
        "content": "Version 1",
        "source_type": "automated"
    }
    create_response = client.post("/api/v1/documentation", json=doc_data)
    doc_id = create_response.json()["id"]

    # Make multiple updates
    for i in range(2, 5):
        update_data = {
            "content": f"Version {i}",
            "changed_by": "test_user",
            "change_description": f"Update {i}"
        }
        client.put(
            f"/api/v1/documentation/host/{host_id}?section_name=summary",
            json=update_data
        )

    # Get version history
    response = client.get(f"/api/v1/documentation/sections/{doc_id}/versions")
    assert response.status_code == 200

    versions = response.json()
    assert len(versions) == 3  # Versions 1, 2, 3 (current is 4)
    # Should be ordered by version descending
    assert versions[0]["version"] == 3
    assert versions[1]["version"] == 2
    assert versions[2]["version"] == 1


def test_rollback_documentation(client):
    """Test rolling back documentation to a previous version."""
    # Setup
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]
    host_id = str(uuid4())

    # Create documentation
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "summary",
        "content": "Version 1 content",
        "source_type": "automated"
    }
    create_response = client.post("/api/v1/documentation", json=doc_data)
    doc_id = create_response.json()["id"]

    # Update to version 2
    update_data = {
        "content": "Version 2 content",
        "changed_by": "test_user"
    }
    client.put(
        f"/api/v1/documentation/host/{host_id}?section_name=summary",
        json=update_data
    )

    # Get version history to find version 1 ID
    versions_response = client.get(f"/api/v1/documentation/sections/{doc_id}/versions")
    versions = versions_response.json()
    version_1_id = versions[-1]["id"]  # Last in list (oldest)

    # Rollback to version 1
    rollback_data = {"changed_by": "test_user"}
    response = client.post(
        f"/api/v1/documentation/sections/{doc_id}/rollback/{version_1_id}",
        json=rollback_data
    )
    assert response.status_code == 200

    data = response.json()
    assert data["content"] == "Version 1 content"
    assert data["version"] == 3  # New version created for rollback


def test_create_research_template(client):
    """Test creating a research template."""
    template_data = {
        "name": "Custom Service Assessment",
        "category": "service",
        "description": "Template for service assessment",
        "template_content": "# Service Assessment\n\n{service_name}",
        "is_system": False,
        "created_by": "test_user"
    }

    response = client.post("/api/v1/templates", json=template_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Custom Service Assessment"
    assert data["category"] == "service"
    assert data["is_system"] is False
    assert "id" in data


def test_list_templates(client):
    """Test listing research templates."""
    # Create multiple templates
    for i in range(3):
        template_data = {
            "name": f"Template {i}",
            "category": "general",
            "template_content": f"Content {i}",
            "is_system": False
        }
        client.post("/api/v1/templates", json=template_data)

    # List all templates
    response = client.get("/api/v1/templates")
    assert response.status_code == 200

    templates = response.json()
    assert len(templates) >= 3


def test_list_templates_by_category(client):
    """Test filtering templates by category."""
    # Create templates in different categories
    categories = ["host", "service", "vulnerability"]
    for category in categories:
        template_data = {
            "name": f"{category} template",
            "category": category,
            "template_content": f"{category} content"
        }
        client.post("/api/v1/templates", json=template_data)

    # Filter by service category
    response = client.get("/api/v1/templates?category=service")
    assert response.status_code == 200

    templates = response.json()
    assert all(t["category"] == "service" for t in templates)


def test_get_template(client):
    """Test retrieving a specific template."""
    # Create template
    template_data = {
        "name": "Test Template",
        "category": "general",
        "template_content": "Test content"
    }
    create_response = client.post("/api/v1/templates", json=template_data)
    template_id = create_response.json()["id"]

    # Get template
    response = client.get(f"/api/v1/templates/{template_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == "Test Template"


def test_update_template(client):
    """Test updating a research template."""
    # Create template
    template_data = {
        "name": "Original Name",
        "category": "general",
        "template_content": "Original content",
        "is_system": False
    }
    create_response = client.post("/api/v1/templates", json=template_data)
    template_id = create_response.json()["id"]

    # Update template
    update_data = {
        "name": "Updated Name",
        "template_content": "Updated content"
    }
    response = client.put(f"/api/v1/templates/{template_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["template_content"] == "Updated content"


def test_cannot_update_system_template(client):
    """Test that system templates cannot be updated."""
    # Create system template
    template_data = {
        "name": "System Template",
        "category": "general",
        "template_content": "System content",
        "is_system": True
    }
    create_response = client.post("/api/v1/templates", json=template_data)
    template_id = create_response.json()["id"]

    # Try to update
    update_data = {"name": "Hacked Name"}
    response = client.put(f"/api/v1/templates/{template_id}", json=update_data)
    assert response.status_code == 403


def test_delete_template(client):
    """Test deleting a research template."""
    # Create template
    template_data = {
        "name": "Deletable Template",
        "category": "general",
        "template_content": "Content",
        "is_system": False
    }
    create_response = client.post("/api/v1/templates", json=template_data)
    template_id = create_response.json()["id"]

    # Delete template
    response = client.delete(f"/api/v1/templates/{template_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/api/v1/templates/{template_id}")
    assert get_response.status_code == 404


def test_cannot_delete_system_template(client):
    """Test that system templates cannot be deleted."""
    # Create system template
    template_data = {
        "name": "System Template",
        "category": "general",
        "template_content": "System content",
        "is_system": True
    }
    create_response = client.post("/api/v1/templates", json=template_data)
    template_id = create_response.json()["id"]

    # Try to delete
    response = client.delete(f"/api/v1/templates/{template_id}")
    assert response.status_code == 403


def test_create_duplicate_documentation_section(client):
    """Test that duplicate sections for same entity are rejected."""
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]
    host_id = str(uuid4())

    # Create first section
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "summary",
        "content": "Content 1",
        "source_type": "automated"
    }
    response1 = client.post("/api/v1/documentation", json=doc_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = client.post("/api/v1/documentation", json=doc_data)
    assert response2.status_code == 400


def test_update_nonexistent_section(client):
    """Test updating a section that doesn't exist."""
    fake_host_id = str(uuid4())
    update_data = {
        "content": "New content",
        "changed_by": "test_user"
    }

    response = client.put(
        f"/api/v1/documentation/host/{fake_host_id}?section_name=summary",
        json=update_data
    )
    assert response.status_code == 404


def test_rollback_with_invalid_version(client):
    """Test rollback with non-existent version ID."""
    project_response = client.post("/api/v1/projects/", json={"name": "Test Project"})
    project_id = project_response.json()["id"]
    host_id = str(uuid4())

    # Create documentation
    doc_data = {
        "project_id": project_id,
        "entity_type": "host",
        "entity_id": host_id,
        "section_name": "summary",
        "content": "Content",
        "source_type": "automated"
    }
    create_response = client.post("/api/v1/documentation", json=doc_data)
    doc_id = create_response.json()["id"]

    # Try to rollback to non-existent version
    fake_version_id = str(uuid4())
    rollback_data = {"changed_by": "test_user"}
    response = client.post(
        f"/api/v1/documentation/sections/{doc_id}/rollback/{fake_version_id}",
        json=rollback_data
    )
    assert response.status_code == 404