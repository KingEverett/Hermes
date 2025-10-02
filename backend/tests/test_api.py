import pytest
from uuid import uuid4

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

def test_create_project(client):
    """Test creating a project"""
    project_data = {
        "name": "Test Project",
        "description": "A test project",
        "project_metadata": {"env": "test"}
    }

    response = client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["project_metadata"] == {"env": "test"}
    assert "id" in data
    assert "created_at" in data

def test_list_projects(client):
    """Test listing projects"""
    # Create a project first
    project_data = {"name": "Test Project"}
    client.post("/api/v1/projects/", json=project_data)

    # List projects
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "Test Project"

def test_get_project(client):
    """Test getting a specific project"""
    # Create a project
    project_data = {"name": "Test Project"}
    create_response = client.post("/api/v1/projects/", json=project_data)
    project_id = create_response.json()["id"]

    # Get the project
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Test Project"

def test_get_nonexistent_project(client):
    """Test getting a project that doesn't exist"""
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/projects/{fake_id}")
    assert response.status_code == 404

def test_create_host(client):
    """Test creating a host"""
    # Create a project first
    project_data = {"name": "Test Project"}
    project_response = client.post("/api/v1/projects/", json=project_data)
    project_id = project_response.json()["id"]

    # Create a host
    host_data = {
        "project_id": project_id,
        "ip_address": "192.168.1.1",
        "hostname": "test-host",
        "os_family": "Linux"
    }

    response = client.post("/api/v1/hosts/", json=host_data)
    assert response.status_code == 201

    data = response.json()
    assert data["ip_address"] == "192.168.1.1"
    assert data["hostname"] == "test-host"
    assert data["os_family"] == "Linux"
    assert data["project_id"] == project_id

def test_create_duplicate_host(client):
    """Test creating a duplicate host (same IP in same project)"""
    # Create a project first
    project_data = {"name": "Test Project"}
    project_response = client.post("/api/v1/projects/", json=project_data)
    project_id = project_response.json()["id"]

    # Create first host
    host_data = {
        "project_id": project_id,
        "ip_address": "192.168.1.1",
        "hostname": "host1"
    }
    client.post("/api/v1/hosts/", json=host_data)

    # Try to create duplicate host
    duplicate_host_data = {
        "project_id": project_id,
        "ip_address": "192.168.1.1",  # Same IP
        "hostname": "host2"
    }
    response = client.post("/api/v1/hosts/", json=duplicate_host_data)
    assert response.status_code == 400

def test_create_scan(client):
    """Test creating a scan"""
    # Create a project first
    project_data = {"name": "Test Project"}
    project_response = client.post("/api/v1/projects/", json=project_data)
    project_id = project_response.json()["id"]

    # Create a scan
    scan_data = {
        "project_id": project_id,
        "filename": "test_scan.xml",
        "tool_type": "nmap",
        "raw_content": "<nmaprun>test content</nmaprun>"
    }

    response = client.post(f"/api/v1/projects/{project_id}/scans", json=scan_data)
    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "test_scan.xml"
    assert data["tool_type"] == "nmap"
    assert data["status"] == "pending"
    assert data["project_id"] == project_id