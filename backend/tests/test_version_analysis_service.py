import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock
from services.research.version_analysis import VersionAnalysisService, VersionMatch, ConfidenceLevel
from models.vulnerability import Vulnerability, Severity
from models.service import Service


class TestVersionAnalysisService:
    """Test suite for the complete version analysis service."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock repositories
        self.vulnerability_repo = Mock()
        self.service_vuln_repo = Mock()
        self.review_queue_repo = Mock()

        # Create service instance
        self.service = VersionAnalysisService(
            vulnerability_repo=self.vulnerability_repo,
            service_vuln_repo=self.service_vuln_repo,
            review_queue_repo=self.review_queue_repo
        )

    def test_analyze_service_version_no_banner(self):
        """Test analysis with service having no banner."""
        service = Mock()
        service.banner = None
        service.id = "test-service-1"

        result = self.service.analyze_service_version(service)
        assert result == []

    def test_analyze_service_version_no_version_extracted(self):
        """Test analysis when no version can be extracted."""
        service = Mock()
        service.banner = "Generic service banner with no version"
        service.service_name = "unknown"
        service.id = "test-service-2"

        result = self.service.analyze_service_version(service)
        assert result == []

    def test_analyze_service_version_with_vulnerabilities(self):
        """Test successful version analysis with vulnerability matches."""
        # Setup service
        service = Mock()
        service.banner = "SSH-2.0-OpenSSH_7.4"
        service.service_name = "ssh"
        service.id = "test-service-3"

        # Setup mock vulnerability
        vulnerability = Mock()
        vulnerability.cve_id = "CVE-2024-1234"
        vulnerability.cvss_score = 7.5
        vulnerability.severity = Severity.HIGH
        vulnerability.description = "Test vulnerability"
        vulnerability.id = "vuln-1"

        # Mock repository response
        self.vulnerability_repo.find_by_product_version.return_value = [vulnerability]
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()

        result = self.service.analyze_service_version(service)

        # Verify results
        assert len(result) == 1
        assert result[0].cve_id == "CVE-2024-1234"
        assert result[0].severity == "high"
        assert result[0].confidence == ConfidenceLevel.HIGH

        # Verify repository calls
        self.vulnerability_repo.find_by_product_version.assert_called_once_with("OpenSSH", "7.4")
        self.service_vuln_repo.create.assert_called_once()

    def test_analyze_service_complete_high_confidence(self):
        """Test complete analysis with high confidence vulnerability."""
        # Setup service
        service = Mock()
        service.banner = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"
        service.service_name = "ssh"
        service.id = "test-service-4"

        # Setup mock vulnerability
        vulnerability = Mock()
        vulnerability.cve_id = "CVE-2024-5678"
        vulnerability.cvss_score = 9.8
        vulnerability.severity = Severity.CRITICAL
        vulnerability.description = "Critical SSH vulnerability"
        vulnerability.id = "vuln-2"

        # Mock repository responses
        self.vulnerability_repo.find_by_product_version.return_value = [vulnerability]
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()

        result = self.service.analyze_service_complete(service)

        # Verify results
        assert result['vulnerabilities_found'] == 1
        assert result['high_confidence_matches'] == 1
        assert result['auto_validated'] == 1
        assert result['review_queue_items'] == 0
        assert "OpenSSH 8.2p1" in result['version_extracted']

    def test_analyze_service_complete_medium_confidence(self):
        """Test complete analysis with medium confidence vulnerability (goes to review queue)."""
        # Setup service with less specific banner
        service = Mock()
        service.banner = "SSH-2.0-libssh_0.8.7"
        service.service_name = "ssh"
        service.id = "test-service-5"

        # Setup mock vulnerability
        vulnerability = Mock()
        vulnerability.cve_id = "CVE-2024-9999"
        vulnerability.cvss_score = 6.5
        vulnerability.severity = Severity.MEDIUM
        vulnerability.description = "Medium severity SSH vulnerability"
        vulnerability.id = "vuln-3"

        # Mock repository responses
        self.vulnerability_repo.find_by_product_version.return_value = [vulnerability]
        self.vulnerability_repo.find_by_cve_id.return_value = vulnerability
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()
        self.review_queue_repo.find_by_service_and_vulnerability.return_value = None
        self.review_queue_repo.create.return_value = Mock()

        result = self.service.analyze_service_complete(service)

        # Verify results
        assert result['vulnerabilities_found'] == 1
        assert result['medium_confidence_matches'] == 1
        assert result['auto_validated'] == 0
        assert result['review_queue_items'] == 1

        # Verify review queue was called
        self.review_queue_repo.create.assert_called_once()

    def test_get_service_vulnerabilities(self):
        """Test retrieving service vulnerabilities with details."""
        service_id = "test-service-6"

        # Mock service vulnerability objects
        mock_sv1 = Mock()
        mock_sv1.vulnerability.cve_id = "CVE-2024-1111"
        mock_sv1.vulnerability.severity = Severity.HIGH
        mock_sv1.vulnerability.cvss_score = 8.1
        mock_sv1.vulnerability.description = "High severity vulnerability"
        mock_sv1.confidence = ConfidenceLevel.HIGH
        mock_sv1.confidence_score = 0.9
        mock_sv1.version_matched = "2.4.41"
        mock_sv1.validated = True
        mock_sv1.detected_at = Mock()
        mock_sv1.detected_at.isoformat.return_value = "2024-01-01T12:00:00"

        mock_sv2 = Mock()
        mock_sv2.vulnerability.cve_id = "CVE-2024-2222"
        mock_sv2.vulnerability.severity = Severity.MEDIUM
        mock_sv2.vulnerability.cvss_score = 5.3
        mock_sv2.vulnerability.description = "Medium severity vulnerability"
        mock_sv2.confidence = ConfidenceLevel.MEDIUM
        mock_sv2.confidence_score = 0.6
        mock_sv2.version_matched = "2.4.41"
        mock_sv2.validated = False
        mock_sv2.detected_at = Mock()
        mock_sv2.detected_at.isoformat.return_value = "2024-01-01T12:05:00"

        self.service_vuln_repo.find_by_service_id.return_value = [mock_sv1, mock_sv2]

        result = self.service.get_service_vulnerabilities(service_id)

        # Verify results
        assert result['service_id'] == service_id
        assert result['total_count'] == 2
        assert result['validated_count'] == 1
        assert result['high_confidence_count'] == 1
        assert len(result['vulnerabilities']) == 2

        # Check first vulnerability details
        vuln1 = result['vulnerabilities'][0]
        assert vuln1['cve_id'] == "CVE-2024-1111"
        assert vuln1['severity'] == "high"
        assert vuln1['confidence'] == "high"
        assert vuln1['validated'] == True

    def test_validate_performance_meets_requirement(self):
        """Test that analysis meets 3-second performance requirement."""
        service = Mock()
        service.banner = "Apache/2.4.41 (Ubuntu)"
        service.service_name = "http"
        service.id = "test-service-7"

        # Mock fast vulnerability lookup
        self.vulnerability_repo.find_by_product_version.return_value = []

        result = self.service.validate_performance(service)

        # Verify performance metrics
        assert 'analysis_time_seconds' in result
        assert result['meets_3_second_requirement'] == True
        assert result['analysis_time_seconds'] < 3.0
        assert result['service_id'] == "test-service-7"

    def test_calculate_review_priority(self):
        """Test review priority calculation logic."""
        # High severity vulnerability
        high_vuln_match = Mock()
        high_vuln_match.severity = "critical"
        version_match = Mock()
        version_match.confidence = ConfidenceLevel.MEDIUM

        priority = self.service._calculate_review_priority(high_vuln_match, version_match)
        assert priority == "high"

        # Medium severity vulnerability
        med_vuln_match = Mock()
        med_vuln_match.severity = "medium"

        priority = self.service._calculate_review_priority(med_vuln_match, version_match)
        assert priority == "medium"

        # Low severity vulnerability
        low_vuln_match = Mock()
        low_vuln_match.severity = "low"

        priority = self.service._calculate_review_priority(low_vuln_match, version_match)
        assert priority == "low"

    def test_record_vulnerability_match_new_record(self):
        """Test recording a new vulnerability match."""
        service = Mock()
        service.id = "service-123"

        vulnerability = Mock()
        vulnerability.id = "vuln-456"

        version_match = VersionMatch(
            product="Apache httpd",
            version="2.4.41",
            confidence=ConfidenceLevel.HIGH,
            extraction_method="apache_version_exact",
            raw_banner="Apache/2.4.41 (Ubuntu)"
        )

        # Mock no existing record
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = None
        self.service_vuln_repo.create.return_value = Mock()

        self.service._record_vulnerability_match(service, vulnerability, version_match)

        # Verify create was called with correct parameters
        self.service_vuln_repo.create.assert_called_once()
        call_args = self.service_vuln_repo.create.call_args[1]

        assert call_args['service_id'] == "service-123"
        assert call_args['vulnerability_id'] == "vuln-456"
        assert call_args['confidence'] == ConfidenceLevel.HIGH
        assert call_args['version_matched'] == "2.4.41"
        assert call_args['validated'] == True  # High confidence auto-validates

    def test_record_vulnerability_match_update_existing(self):
        """Test updating an existing vulnerability match."""
        service = Mock()
        service.id = "service-123"

        vulnerability = Mock()
        vulnerability.id = "vuln-456"

        version_match = VersionMatch(
            product="Apache httpd",
            version="2.4.41",
            confidence=ConfidenceLevel.MEDIUM,
            extraction_method="apache_version_exact",
            raw_banner="Apache/2.4.41 (Ubuntu)"
        )

        # Mock existing record
        existing_record = Mock()
        existing_record.id = "existing-123"
        self.service_vuln_repo.find_by_service_and_vulnerability.return_value = existing_record
        self.service_vuln_repo.update.return_value = existing_record

        self.service._record_vulnerability_match(service, vulnerability, version_match)

        # Verify update was called
        self.service_vuln_repo.update.assert_called_once_with(
            "existing-123",
            confidence=ConfidenceLevel.MEDIUM,
            confidence_score=0.6,  # Medium confidence score
            version_matched="2.4.41",
            extraction_method="apache_version_exact",
            validated=False  # Medium confidence doesn't auto-validate
        )

    def test_no_vulnerabilities_found(self):
        """Test analysis when no vulnerabilities are found for extracted version."""
        service = Mock()
        service.banner = "SSH-2.0-OpenSSH_9.0p1"  # Newer version with no known vulns
        service.service_name = "ssh"
        service.id = "test-service-8"

        # Mock empty vulnerability response
        self.vulnerability_repo.find_by_product_version.return_value = []

        result = self.service.analyze_service_complete(service)

        # Verify no vulnerabilities found
        assert result['vulnerabilities_found'] == 0
        assert result['high_confidence_matches'] == 0
        assert result['auto_validated'] == 0
        assert result['review_queue_items'] == 0

        # Verify no repository writes were called
        self.service_vuln_repo.create.assert_not_called()
        self.review_queue_repo.create.assert_not_called()