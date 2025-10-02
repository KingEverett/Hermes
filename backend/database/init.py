from sqlalchemy.orm import Session
from database.connection import get_session, init_db
from repositories.project import ProjectRepository
from repositories.scan import ScanRepository
from repositories.host import HostRepository
from repositories.service import ServiceRepository
from repositories.vulnerability import VulnerabilityRepository
from models.scan import ToolType, ScanStatus
from models.service import Protocol
from models.vulnerability import Severity
import logging

logger = logging.getLogger(__name__)

def create_sample_data():
    """Create sample data for development"""
    logger.info("Creating sample data...")

    session = get_session()
    try:
        # Create sample project
        project_repo = ProjectRepository(session)
        sample_project = project_repo.create(
            name="Sample Network Assessment",
            description="A sample project demonstrating Hermes functionality",
            project_metadata={"environment": "development", "scope": "internal"}
        )
        logger.info(f"Created sample project: {sample_project.id}")

        # Create sample scan
        scan_repo = ScanRepository(session)
        sample_scan = scan_repo.create(
            project_id=sample_project.id,
            filename="sample_nmap.xml",
            tool_type=ToolType.NMAP,
            status=ScanStatus.COMPLETED,
            raw_content="<nmaprun>...</nmaprun>"
        )
        logger.info(f"Created sample scan: {sample_scan.id}")

        # Create sample host
        host_repo = HostRepository(session)
        sample_host = host_repo.create(
            project_id=sample_project.id,
            ip_address="192.168.1.100",
            hostname="webserver.local",
            os_family="Linux",
            os_details="Ubuntu 20.04",
            status="up",
            confidence_score=0.95,
            host_metadata={"location": "DMZ", "criticality": "high"}
        )
        logger.info(f"Created sample host: {sample_host.id}")

        # Create sample services
        service_repo = ServiceRepository(session)
        web_service = service_repo.create(
            host_id=sample_host.id,
            port=80,
            protocol=Protocol.TCP,
            service_name="http",
            product="Apache",
            version="2.4.41",
            banner="Apache/2.4.41 (Ubuntu)"
        )

        ssh_service = service_repo.create(
            host_id=sample_host.id,
            port=22,
            protocol=Protocol.TCP,
            service_name="ssh",
            product="OpenSSH",
            version="8.2p1",
            banner="SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"
        )
        logger.info(f"Created sample services: {web_service.id}, {ssh_service.id}")

        # Create sample vulnerabilities
        vuln_repo = VulnerabilityRepository(session)
        critical_vuln = vuln_repo.create(
            cve_id="CVE-2021-44228",
            cvss_score=10.0,
            severity=Severity.CRITICAL,
            description="Apache Log4j2 Remote Code Execution",
            remediation="Update Log4j to version 2.17.0 or later",
            exploit_available=True,
            cisa_kev=True,
            references={"nist": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"}
        )

        medium_vuln = vuln_repo.create(
            cve_id="CVE-2021-3156",
            cvss_score=7.8,
            severity=Severity.HIGH,
            description="Sudo Heap-Based Buffer Overflow",
            remediation="Update sudo to version 1.9.5p2 or later",
            exploit_available=True,
            cisa_kev=False,
            references={"nist": "https://nvd.nist.gov/vuln/detail/CVE-2021-3156"}
        )
        logger.info(f"Created sample vulnerabilities: {critical_vuln.id}, {medium_vuln.id}")

        session.commit()
        logger.info("Sample data created successfully")

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating sample data: {e}")
        raise
    finally:
        session.close()

def reset_database():
    """Reset database by dropping and recreating all tables"""
    logger.info("Resetting database...")
    init_db()
    logger.info("Database reset complete")

def initialize_database():
    """Initialize database with schema and sample data"""
    logger.info("Initializing database...")
    init_db()
    create_sample_data()
    logger.info("Database initialization complete")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()