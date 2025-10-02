import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import tempfile
import os
from uuid import uuid4

from models.base import BaseModel
from models.project import Project
from models.host import Host
from models.service import Service, Protocol
from models.vulnerability import Vulnerability, Severity
from models.service_vulnerability import ServiceVulnerability
from database.connection import get_db
from main import app

@pytest.fixture
def test_db():
    """Create a test database"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    test_database_url = f"sqlite:///{db_path}"

    # Create engine and session
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    BaseModel.metadata.create_all(bind=engine)

    # Yield session for tests
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        os.close(db_fd)
        os.unlink(db_path)

@pytest.fixture
def client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_project(test_db):
    """Create a sample project for testing."""
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="Test project for graph generation"
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project

@pytest.fixture
def sample_hosts_with_services(test_db, sample_project):
    """
    Create sample hosts with services for testing.

    Creates:
    - 10 hosts (5 Linux, 3 Windows, 2 Network devices)
    - 50 services (5 per host)
    """
    hosts = []
    os_families = ['Linux'] * 5 + ['Windows'] * 3 + ['Network'] * 2

    for i, os_family in enumerate(os_families):
        host = Host(
            id=uuid4(),
            project_id=sample_project.id,
            ip_address=f"192.168.1.{i + 1}",
            hostname=f"host{i + 1}",
            os_family=os_family,
            status="up"
        )
        test_db.add(host)
        hosts.append(host)

    test_db.commit()

    # Add services to each host
    for host in hosts:
        test_db.refresh(host)
        for port in [22, 80, 443, 3306, 8080]:
            service = Service(
                id=uuid4(),
                host_id=host.id,
                port=port,
                protocol=Protocol.TCP,
                service_name=f"service_{port}",
                product=f"Product {port}",
                version="1.0.0"
            )
            test_db.add(service)

    test_db.commit()
    return hosts

@pytest.fixture
def sample_vulnerabilities(test_db, sample_hosts_with_services):
    """
    Create sample vulnerabilities linked to services.
    """
    vulnerabilities = []
    severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]

    for i, severity in enumerate(severities):
        vuln = Vulnerability(
            id=uuid4(),
            cve_id=f"CVE-2024-{1000 + i}",
            severity=severity,
            cvss_score=9.0 - (i * 2.0),
            description=f"Test vulnerability {i + 1}",
            exploit_available=(i < 2)
        )
        test_db.add(vuln)
        vulnerabilities.append(vuln)

    test_db.commit()

    # Link vulnerabilities to first 5 hosts
    for host in sample_hosts_with_services[:5]:
        for service in host.services[:2]:
            for vuln in vulnerabilities:
                svc_vuln = ServiceVulnerability(
                    service_id=service.id,
                    vulnerability_id=vuln.id,
                    false_positive=False
                )
                test_db.add(svc_vuln)

    test_db.commit()
    return vulnerabilities