"""Integration tests for documentation export with attack chains."""

import pytest
from pathlib import Path
from uuid import uuid4
import time

from fastapi.testclient import TestClient
from models.project import Project
from models.host import Host
from models.service import Service, Protocol
from models.attack_chain import AttackChain, AttackChainNode
from models.export_job import ExportFormat, JobStatus


@pytest.fixture
def client(test_db):
    """Create FastAPI test client."""
    from main import app
    return TestClient(app)


@pytest.fixture
def integration_project(test_db):
    """Create a complete project with hosts, services, and attack chains."""
    project = Project(
        id=uuid4(),
        name="Integration Test Project",
        description="Full project for integration testing"
    )
    test_db.add(project)
    test_db.flush()

    # Create hosts
    web_host = Host(
        id=uuid4(),
        project_id=project.id,
        ip_address="192.168.1.100",
        hostname="web-app",
        status="up",
        os_family="Linux"
    )
    db_host = Host(
        id=uuid4(),
        project_id=project.id,
        ip_address="192.168.1.200",
        hostname="database",
        status="up",
        os_family="Linux"
    )
    admin_host = Host(
        id=uuid4(),
        project_id=project.id,
        ip_address="192.168.1.10",
        hostname="admin-panel",
        status="up",
        os_family="Windows"
    )
    test_db.add_all([web_host, db_host, admin_host])
    test_db.flush()

    # Create services
    http_service = Service(
        id=uuid4(),
        host_id=web_host.id,
        port=80,
        protocol=Protocol.TCP,
        service_name="http",
        product="Apache",
        version="2.4.41"
    )
    ssh_service = Service(
        id=uuid4(),
        host_id=web_host.id,
        port=22,
        protocol=Protocol.TCP,
        service_name="ssh",
        product="OpenSSH",
        version="8.2p1"
    )
    mysql_service = Service(
        id=uuid4(),
        host_id=db_host.id,
        port=3306,
        protocol=Protocol.TCP,
        service_name="mysql",
        product="MySQL",
        version="5.7.31"
    )
    rdp_service = Service(
        id=uuid4(),
        host_id=admin_host.id,
        port=3389,
        protocol=Protocol.TCP,
        service_name="rdp",
        product="Microsoft Terminal Services"
    )
    test_db.add_all([http_service, ssh_service, mysql_service, rdp_service])
    test_db.flush()

    # Create attack chain 1: Web to Database
    chain1 = AttackChain(
        id=uuid4(),
        project_id=project.id,
        name="Web to Database Compromise",
        description="Attack path from web application to database server",
        color="#FF6B35"
    )
    test_db.add(chain1)
    test_db.flush()

    chain1_nodes = [
        AttackChainNode(
            attack_chain_id=chain1.id,
            entity_type='host',
            entity_id=web_host.id,
            sequence_order=1,
            method_notes="Initial access via SQL injection in login form"
        ),
        AttackChainNode(
            attack_chain_id=chain1.id,
            entity_type='service',
            entity_id=http_service.id,
            sequence_order=2,
            method_notes="Exploit vulnerable Apache module",
            is_branch_point=True,
            branch_description="Alternative: Could use SSH brute force"
        ),
        AttackChainNode(
            attack_chain_id=chain1.id,
            entity_type='host',
            entity_id=db_host.id,
            sequence_order=3,
            method_notes="Lateral movement via credential reuse"
        ),
        AttackChainNode(
            attack_chain_id=chain1.id,
            entity_type='service',
            entity_id=mysql_service.id,
            sequence_order=4,
            method_notes="Direct MySQL access with stolen credentials"
        )
    ]
    test_db.add_all(chain1_nodes)

    # Create attack chain 2: Web to Admin
    chain2 = AttackChain(
        id=uuid4(),
        project_id=project.id,
        name="Admin Panel Takeover",
        description="Privilege escalation to admin panel",
        color="#4ECDC4"
    )
    test_db.add(chain2)
    test_db.flush()

    chain2_nodes = [
        AttackChainNode(
            attack_chain_id=chain2.id,
            entity_type='service',
            entity_id=http_service.id,
            sequence_order=1,
            method_notes="XSS to steal admin session token"
        ),
        AttackChainNode(
            attack_chain_id=chain2.id,
            entity_type='host',
            entity_id=admin_host.id,
            sequence_order=2,
            method_notes="Session hijacking with stolen token"
        ),
        AttackChainNode(
            attack_chain_id=chain2.id,
            entity_type='service',
            entity_id=rdp_service.id,
            sequence_order=3,
            method_notes="RDP access via Pass-the-Hash"
        )
    ]
    test_db.add_all(chain2_nodes)

    test_db.commit()
    test_db.refresh(project)
    return {
        'project': project,
        'hosts': [web_host, db_host, admin_host],
        'services': [http_service, ssh_service, mysql_service, rdp_service],
        'chains': [chain1, chain2]
    }


class TestDocumentationExportIntegration:
    """Integration tests for full documentation export workflow."""

    def test_export_with_attack_chains_api(self, client, test_db, integration_project):
        """Test full documentation export includes attack chains via API."""
        project = integration_project['project']

        # Create export job
        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={
                "format": "markdown",
                "include_graph": False,
                "include_attack_chains": True
            }
        )

        assert response.status_code == 202
        job = response.json()
        assert job['project_id'] == str(project.id)
        assert job['format'] == 'markdown'
        assert job['status'] == 'pending'

        # Wait for job completion (poll with timeout)
        job_id = job['id']
        max_wait = 10  # seconds
        elapsed = 0
        completed = False

        while elapsed < max_wait:
            status_response = client.get(
                f"/api/v1/projects/{project.id}/export/{job_id}"
            )
            status = status_response.json()

            if status['status'] in ['completed', 'failed']:
                completed = True
                break

            time.sleep(0.5)
            elapsed += 0.5

        assert completed, "Export job did not complete in time"
        assert status['status'] == 'completed', f"Export failed: {status.get('error_message')}"

    def test_export_markdown_contains_attack_chains(self, client, test_db, integration_project):
        """Test exported markdown contains attack chain section."""
        project = integration_project['project']
        chains = integration_project['chains']

        # Create export job
        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={
                "format": "markdown",
                "include_attack_chains": True
            }
        )

        job_id = response.json()['id']

        # Wait for completion
        time.sleep(2)

        # Download export
        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        assert download_response.status_code == 200
        markdown = download_response.text

        # Verify attack chains section exists
        assert "## Attack Chains" in markdown

        # Verify both chains are present
        assert chains[0].name in markdown
        assert chains[1].name in markdown
        assert chains[0].description in markdown
        assert chains[1].description in markdown

        # Verify metadata
        assert "Total Chains: 2" in markdown
        assert "Total Nodes: 7" in markdown  # 4 + 3 nodes

    def test_export_markdown_structure(self, client, test_db, integration_project):
        """Test exported markdown has correct structure and all sections."""
        project = integration_project['project']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Verify all main sections exist
        assert f"# {project.name}" in markdown
        assert "## Executive Summary" in markdown
        assert "## Project Overview" in markdown
        assert "## Network Discovery Results" in markdown
        assert "## Attack Chains" in markdown
        assert "## Detailed Host Information" in markdown
        assert "## Service Distribution" in markdown

    def test_export_chain_node_sequences(self, client, test_db, integration_project):
        """Test attack chain node sequences display correctly."""
        project = integration_project['project']
        hosts = integration_project['hosts']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Verify node sequences with resolved entities
        assert "web-app (192.168.1.100)" in markdown
        assert "database (192.168.1.200)" in markdown
        assert "admin-panel (192.168.1.10)" in markdown
        assert "http (80/tcp)" in markdown
        assert "mysql (3306/tcp)" in markdown

        # Verify arrows
        assert "↓" in markdown

    def test_export_chain_method_notes(self, client, test_db, integration_project):
        """Test method annotations appear in exported markdown."""
        project = integration_project['project']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Verify method notes
        assert "**Method**: Initial access via SQL injection in login form" in markdown
        assert "**Method**: Exploit vulnerable Apache module" in markdown
        assert "**Method**: XSS to steal admin session token" in markdown
        assert "**Method**: RDP access via Pass-the-Hash" in markdown

    def test_export_chain_branch_points(self, client, test_db, integration_project):
        """Test branch points render correctly in exported markdown."""
        project = integration_project['project']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Verify branch point
        assert "> **Branch Point**:" in markdown
        assert "Alternative: Could use SSH brute force" in markdown

    def test_export_svg_files_created(self, client, test_db, integration_project):
        """Test SVG files are created in graphs directory."""
        project = integration_project['project']
        chains = integration_project['chains']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        # Check SVG files exist
        exports_dir = Path("exports") / str(project.id) / "graphs"

        for chain in chains:
            svg_path = exports_dir / f"attack-chain-{chain.id}.svg"
            assert svg_path.exists(), f"SVG not created for chain {chain.id}"

            # Verify SVG content
            content = svg_path.read_text()
            assert "<svg" in content
            assert chain.name in content

    def test_export_svg_references_in_markdown(self, client, test_db, integration_project):
        """Test SVG image references are correct in markdown."""
        project = integration_project['project']
        chains = integration_project['chains']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={"format": "markdown", "include_attack_chains": True}
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Verify SVG references
        for chain in chains:
            expected_path = f"./graphs/attack-chain-{chain.id}.svg"
            assert expected_path in markdown
            assert f"![Attack Chain: {chain.name}]({expected_path})" in markdown

    def test_export_without_attack_chains_flag(self, client, test_db, integration_project):
        """Test export respects include_attack_chains=False flag."""
        project = integration_project['project']
        chains = integration_project['chains']

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={
                "format": "markdown",
                "include_attack_chains": False
            }
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Attack chains section should not exist
        assert "## Attack Chains" not in markdown
        assert chains[0].name not in markdown
        assert chains[1].name not in markdown

    def test_export_empty_project_no_attack_chains(self, client, test_db):
        """Test export of project with no attack chains."""
        # Create empty project
        project = Project(
            id=uuid4(),
            name="Empty Project",
            description="Project without attack chains"
        )
        test_db.add(project)
        test_db.commit()

        response = client.post(
            f"/api/v1/projects/{project.id}/export",
            json={
                "format": "markdown",
                "include_attack_chains": True
            }
        )

        job_id = response.json()['id']
        time.sleep(2)

        download_response = client.get(
            f"/api/v1/projects/{project.id}/export/{job_id}/download"
        )

        markdown = download_response.text

        # Should not include attack chains section
        assert "## Attack Chains" not in markdown

    def test_export_list_shows_jobs(self, client, test_db, integration_project):
        """Test export history listing includes created jobs."""
        project = integration_project['project']

        # Create multiple export jobs
        for _ in range(3):
            client.post(
                f"/api/v1/projects/{project.id}/export",
                json={"format": "markdown", "include_attack_chains": True}
            )

        # List exports
        list_response = client.get(f"/api/v1/projects/{project.id}/exports")

        assert list_response.status_code == 200
        jobs = list_response.json()
        assert len(jobs) >= 3

        # Verify job data
        for job in jobs:
            assert job['project_id'] == str(project.id)
            assert job['format'] == 'markdown'
            assert 'created_at' in job
