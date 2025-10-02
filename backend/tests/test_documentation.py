"""Unit tests for documentation generation service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from services.documentation import DocumentationService
from models import Project, Host, Service, Scan
from models.scan import ScanStatus, ToolType


class TestDocumentationService:
    """Test suite for DocumentationService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def doc_service(self, mock_db_session):
        """Create DocumentationService instance with mocked session."""
        return DocumentationService(mock_db_session)

    @pytest.fixture
    def sample_project(self):
        """Create sample project data."""
        project = Project(
            id="test-project-123",
            name="Test Project",
            description="Test penetration testing project",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return project

    @pytest.fixture
    def sample_hosts(self):
        """Create sample host data with services."""
        hosts = []
        for i in range(5):
            host = Host(
                id=f"host-{i}",
                project_id="test-project-123",
                ip_address=f"192.168.1.{i+1}",
                hostname=f"host{i+1}.example.com",
                os_family="Linux",
                os_details="Ubuntu 22.04",
                status="up",
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )

            # Add services to host
            host.services = []
            for port in [22, 80, 443]:
                service = Service(
                    id=f"service-{i}-{port}",
                    host_id=host.id,
                    port=port,
                    protocol="tcp",
                    service_name="ssh" if port == 22 else "http" if port == 80 else "https",
                    product="OpenSSH" if port == 22 else "Apache",
                    version="8.0" if port == 22 else "2.4.41"
                )
                host.services.append(service)

            hosts.append(host)
        return hosts

    @pytest.fixture
    def sample_scans(self):
        """Create sample scan data."""
        scans = [
            Scan(
                id="scan-1",
                project_id="test-project-123",
                filename="nmap_scan.xml",
                tool_type=ToolType.NMAP,
                status=ScanStatus.COMPLETED,
                processing_time_ms=1500,
                parsed_at=datetime.now()
            ),
            Scan(
                id="scan-2",
                project_id="test-project-123",
                filename="masscan_results.json",
                tool_type=ToolType.MASSCAN,
                status=ScanStatus.COMPLETED,
                processing_time_ms=800,
                parsed_at=datetime.now()
            )
        ]
        return scans

    def test_generate_markdown_small_project(self, doc_service, mock_db_session, sample_project, sample_hosts, sample_scans):
        """Test markdown generation for small project."""
        # Setup mocks
        doc_service.project_repo.get_by_id = Mock(return_value=sample_project)
        mock_db_session.query.return_value.filter.return_value.count.return_value = 5  # Small project
        mock_db_session.query.return_value.filter.return_value.options.return_value.all.return_value = sample_hosts
        doc_service.scan_repo.get_by_project = Mock(return_value=sample_scans)

        # Generate markdown
        result = doc_service.generate_markdown("test-project-123")

        # Assertions
        assert result is not None
        assert "Test Project" in result
        assert "Penetration Test Report" in result
        assert "192.168.1.1" in result
        assert "**Total Hosts**: 5" in result
        assert "**Total Services**: 15" in result  # 5 hosts * 3 services each
        doc_service.project_repo.get_by_id.assert_called_once_with("test-project-123")

    def test_generate_markdown_project_not_found(self, doc_service, mock_db_session):
        """Test markdown generation when project not found."""
        # Setup mocks
        doc_service.project_repo.get_by_id = Mock(return_value=None)
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0

        # Test exception
        with pytest.raises(RuntimeError) as exc_info:
            doc_service.generate_markdown("non-existent-project")

        assert "Documentation generation failed" in str(exc_info.value)

    def test_calculate_statistics(self, doc_service, sample_project, sample_hosts, sample_scans):
        """Test statistics calculation."""
        project_data = {
            'project': sample_project,
            'hosts': sample_hosts,
            'scans': sample_scans,
            'vulnerabilities': []
        }

        stats = doc_service._calculate_statistics(project_data)

        # Assertions
        assert stats['host_count'] == 5
        assert stats['service_count'] == 15  # 5 hosts * 3 services
        assert stats['tcp_count'] == 15
        assert stats['udp_count'] == 0
        assert stats['unique_ports'] == 3  # 22, 80, 443
        assert stats['total_processing_time'] == 2300  # 1500 + 800
        assert stats['avg_processing_time'] == 1150

    def test_calculate_port_distribution(self, doc_service, sample_hosts):
        """Test port distribution calculation."""
        distribution = doc_service._calculate_port_distribution(sample_hosts)

        # Assertions
        assert len(distribution) == 3  # 3 unique ports
        assert distribution[0]['port'] in [22, 80, 443]
        assert distribution[0]['count'] == 5  # Each port appears 5 times
        assert distribution[0]['protocol'] == 'tcp'

    def test_calculate_service_statistics(self, doc_service, sample_hosts):
        """Test service statistics calculation."""
        stats = doc_service._calculate_service_statistics(sample_hosts)

        # Assertions
        assert stats['tcp_count'] == 15
        assert stats['udp_count'] == 0
        assert stats['most_common']['name'] in ['ssh', 'http', 'https']
        assert stats['most_common']['count'] == 5

    def test_export_to_file(self, doc_service, mock_db_session, sample_project, sample_hosts, sample_scans):
        """Test export to file functionality."""
        # Setup mocks
        doc_service.project_repo.get_by_id = Mock(return_value=sample_project)
        mock_db_session.query.return_value.filter.return_value.count.return_value = 5
        mock_db_session.query.return_value.filter.return_value.options.return_value.all.return_value = sample_hosts
        doc_service.scan_repo.get_by_project = Mock(return_value=sample_scans)

        with patch('pathlib.Path.write_text') as mock_write:
            with patch('pathlib.Path.mkdir'):
                # Export to file
                result = doc_service.export_to_file("test-project-123")

                # Assertions
                assert "test_project_report_" in result
                assert result.endswith(".md")
                mock_write.assert_called_once()

    def test_markdown_template_rendering(self, doc_service):
        """Test markdown template renders correctly."""
        from templates import get_template

        template = get_template('markdown.j2')

        # Minimal test data
        test_data = {
            'project': {'name': 'Test', 'description': 'Description', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            'hosts': [],
            'scans': [],
            'vulnerabilities': [],
            'stats': {
                'host_count': 0,
                'service_count': 0,
                'open_port_count': 0,
                'vulnerability_count': 0,
                'critical_count': 0,
                'port_distribution': [],
                'unique_ports': 0,
                'most_common_service': {'name': 'None', 'count': 0},
                'tcp_count': 0,
                'udp_count': 0,
                'total_processing_time': 0,
                'avg_processing_time': 0
            },
            'timestamp': datetime.now()
        }

        rendered = template.render(**test_data)

        # Assertions
        assert "Test - Penetration Test Report" in rendered
        assert "Executive Summary" in rendered
        assert "Network Discovery Results" in rendered

    def test_markdown_validation(self):
        """Test markdown syntax validation."""
        from templates import validate_markdown_syntax

        # Valid markdown
        valid_md = """
# Header
## Subheader

| Column1 | Column2 |
|---------|---------|
| Data1   | Data2   |

```python
code block
```
"""
        assert validate_markdown_syntax(valid_md) is True

        # Invalid markdown (unclosed code block)
        invalid_md = """
# Header
```python
unclosed code block
"""
        assert validate_markdown_syntax(invalid_md) is False

    def test_empty_project_handling(self, doc_service, mock_db_session, sample_project):
        """Test handling of empty project with no hosts."""
        # Setup mocks
        doc_service.project_repo.get_by_id = Mock(return_value=sample_project)
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.options.return_value.all.return_value = []
        doc_service.scan_repo.get_by_project = Mock(return_value=[])

        # Generate markdown
        result = doc_service.generate_markdown("test-project-123")

        # Assertions
        assert result is not None
        assert "**Total Hosts**: 0" in result
        assert "**Total Services**: 0" in result

    def test_hosts_without_services(self, doc_service, mock_db_session, sample_project, sample_scans):
        """Test handling hosts without services."""
        # Create hosts without services
        hosts_no_services = [
            Host(
                id="host-1",
                project_id="test-project-123",
                ip_address="192.168.1.1",
                status="up",
                services=[]  # No services
            )
        ]

        # Setup mocks
        doc_service.project_repo.get_by_id = Mock(return_value=sample_project)
        mock_db_session.query.return_value.filter.return_value.count.return_value = 1
        mock_db_session.query.return_value.filter.return_value.options.return_value.all.return_value = hosts_no_services
        doc_service.scan_repo.get_by_project = Mock(return_value=sample_scans)

        # Generate markdown
        result = doc_service.generate_markdown("test-project-123")

        # Assertions
        assert "No services detected on this host" in result or "Services (0)" in result