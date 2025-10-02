import pytest
from models.project import Project
from models.scan import Scan, ScanStatus, ToolType
from models.host import Host
from models.service import Service, Protocol
from models.vulnerability import Vulnerability, Severity
from repositories.project import ProjectRepository
from repositories.host import HostRepository
from repositories.service import ServiceRepository

def test_project_model_creation(test_db):
    """Test Project model creation"""
    repo = ProjectRepository(test_db)
    project = repo.create(
        name="Test Project",
        description="A test project",
        project_metadata={"env": "test"}
    )

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "A test project"
    assert project.project_metadata == {"env": "test"}

def test_host_model_with_unique_constraint(test_db):
    """Test Host model unique constraint"""
    project_repo = ProjectRepository(test_db)
    project = project_repo.create(name="Test Project")

    host_repo = HostRepository(test_db)

    # Create first host
    host1 = host_repo.create(
        project_id=project.id,
        ip_address="192.168.1.1",
        hostname="host1"
    )
    assert host1.id is not None

    # Try to create duplicate host (same project_id + ip_address)
    with pytest.raises(Exception):  # Should raise integrity error
        host_repo.create(
            project_id=project.id,
            ip_address="192.168.1.1",
            hostname="host2"
        )

def test_service_model_with_relationships(test_db):
    """Test Service model relationships"""
    project_repo = ProjectRepository(test_db)
    project = project_repo.create(name="Test Project")

    host_repo = HostRepository(test_db)
    host = host_repo.create(
        project_id=project.id,
        ip_address="192.168.1.1"
    )

    service_repo = ServiceRepository(test_db)
    service = service_repo.create(
        host_id=host.id,
        port=80,
        protocol=Protocol.TCP,
        service_name="http"
    )

    assert service.host_id == host.id
    assert service.port == 80
    assert service.protocol == Protocol.TCP

def test_vulnerability_model_creation(test_db):
    """Test Vulnerability model creation"""
    from repositories.vulnerability import VulnerabilityRepository

    repo = VulnerabilityRepository(test_db)
    vuln = repo.create(
        cve_id="CVE-2021-44228",
        cvss_score=10.0,
        severity=Severity.CRITICAL,
        description="Log4j RCE",
        exploit_available=True,
        cisa_kev=True
    )

    assert vuln.cve_id == "CVE-2021-44228"
    assert vuln.cvss_score == 10.0
    assert vuln.severity == Severity.CRITICAL
    assert vuln.exploit_available is True
    assert vuln.cisa_kev is True