import pytest
from uuid import uuid4
from models.project import Project


def test_create_attack_chain_without_nodes(client, sample_project):
    """Test creating an attack chain via API without nodes"""
    response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Test Chain",
            "description": "Test description",
            "color": "#FF6B35",
            "nodes": []
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Chain"
    assert data["color"] == "#FF6B35"
    assert data["project_id"] == str(sample_project.id)
    assert len(data["nodes"]) == 0


def test_create_attack_chain_with_nodes(client, sample_project):
    """Test creating an attack chain with nodes via API"""
    host_id = str(uuid4())
    service_id = str(uuid4())

    response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Web to DC",
            "description": "Attack path from web server to domain controller",
            "color": "#4ECDC4",
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": host_id,
                    "sequence_order": 1,
                    "method_notes": "SQL injection in login form",
                    "is_branch_point": False,
                    "branch_description": None
                },
                {
                    "entity_type": "service",
                    "entity_id": service_id,
                    "sequence_order": 2,
                    "method_notes": "SSH credential reuse",
                    "is_branch_point": True,
                    "branch_description": "Could pivot to mail server"
                }
            ]
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Web to DC"
    assert len(data["nodes"]) == 2
    assert data["nodes"][0]["sequence_order"] == 1
    assert data["nodes"][1]["is_branch_point"] is True


def test_create_attack_chain_project_not_found(client):
    """Test creating attack chain for non-existent project"""
    response = client.post(
        f"/api/v1/projects/{uuid4()}/attack-chains",
        json={
            "name": "Test Chain",
            "color": "#FF6B35",
            "nodes": []
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_attack_chain_invalid_color(client, sample_project):
    """Test creating attack chain with invalid color format"""
    response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Test Chain",
            "color": "red",  # Invalid format
            "nodes": []
        }
    )

    assert response.status_code == 422


def test_list_project_attack_chains(client, sample_project):
    """Test listing all attack chains for a project"""
    # Create two chains
    client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={"name": "Chain 1", "color": "#FF6B35", "nodes": []}
    )
    client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Chain 2",
            "color": "#4ECDC4",
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": str(uuid4()),
                    "sequence_order": 1
                }
            ]
        }
    )

    # List chains
    response = client.get(f"/api/v1/projects/{sample_project.id}/attack-chains")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should include node_count
    chain_with_node = [c for c in data if c["name"] == "Chain 2"][0]
    assert chain_with_node["node_count"] == 1


def test_list_attack_chains_project_not_found(client):
    """Test listing attack chains for non-existent project"""
    response = client.get(f"/api/v1/projects/{uuid4()}/attack-chains")

    assert response.status_code == 404


def test_get_attack_chain_by_id(client, sample_project):
    """Test getting a single attack chain by ID"""
    # Create chain
    create_response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Test Chain",
            "color": "#FF6B35",
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": str(uuid4()),
                    "sequence_order": 1
                }
            ]
        }
    )
    chain_id = create_response.json()["id"]

    # Get chain
    response = client.get(f"/api/v1/attack-chains/{chain_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chain_id
    assert data["name"] == "Test Chain"
    assert len(data["nodes"]) == 1


def test_get_attack_chain_not_found(client):
    """Test getting a non-existent attack chain"""
    response = client.get(f"/api/v1/attack-chains/{uuid4()}")

    assert response.status_code == 404


def test_update_attack_chain_attributes(client, sample_project):
    """Test updating attack chain name, description, color"""
    # Create chain
    create_response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={"name": "Original Name", "color": "#FF6B35", "nodes": []}
    )
    chain_id = create_response.json()["id"]

    # Update chain
    response = client.put(
        f"/api/v1/attack-chains/{chain_id}",
        json={
            "name": "Updated Name",
            "description": "Updated description",
            "color": "#4ECDC4"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"
    assert data["color"] == "#4ECDC4"


def test_update_attack_chain_replace_nodes(client, sample_project):
    """Test updating attack chain and replacing nodes"""
    # Create chain with 1 node
    create_response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Test Chain",
            "color": "#FF6B35",
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": str(uuid4()),
                    "sequence_order": 1
                }
            ]
        }
    )
    chain_id = create_response.json()["id"]

    # Update with 2 new nodes
    response = client.put(
        f"/api/v1/attack-chains/{chain_id}",
        json={
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": str(uuid4()),
                    "sequence_order": 1
                },
                {
                    "entity_type": "service",
                    "entity_id": str(uuid4()),
                    "sequence_order": 2
                }
            ]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2


def test_update_attack_chain_not_found(client):
    """Test updating a non-existent attack chain"""
    response = client.put(
        f"/api/v1/attack-chains/{uuid4()}",
        json={"name": "New Name"}
    )

    assert response.status_code == 404


def test_delete_attack_chain(client, sample_project):
    """Test deleting an attack chain"""
    # Create chain
    create_response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={"name": "Test Chain", "color": "#FF6B35", "nodes": []}
    )
    chain_id = create_response.json()["id"]

    # Delete chain
    response = client.delete(f"/api/v1/attack-chains/{chain_id}")

    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/v1/attack-chains/{chain_id}")
    assert get_response.status_code == 404


def test_delete_attack_chain_not_found(client):
    """Test deleting a non-existent attack chain"""
    response = client.delete(f"/api/v1/attack-chains/{uuid4()}")

    assert response.status_code == 404


def test_cascade_delete_nodes_via_api(client, sample_project):
    """Test that deleting a chain via API cascades to delete nodes"""
    # Create chain with nodes
    create_response = client.post(
        f"/api/v1/projects/{sample_project.id}/attack-chains",
        json={
            "name": "Test Chain",
            "color": "#FF6B35",
            "nodes": [
                {
                    "entity_type": "host",
                    "entity_id": str(uuid4()),
                    "sequence_order": 1
                },
                {
                    "entity_type": "service",
                    "entity_id": str(uuid4()),
                    "sequence_order": 2
                }
            ]
        }
    )
    chain_id = create_response.json()["id"]

    # Delete chain
    delete_response = client.delete(f"/api/v1/attack-chains/{chain_id}")
    assert delete_response.status_code == 204

    # Verify chain is gone
    get_response = client.get(f"/api/v1/attack-chains/{chain_id}")
    assert get_response.status_code == 404
