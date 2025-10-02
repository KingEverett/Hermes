import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock
from services.research.credential_detection import DefaultCredentialDetectionService, CredentialRisk


class TestDefaultCredentialDetectionService:
    """Test suite for default credential detection service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DefaultCredentialDetectionService()

    def test_normalize_service_type(self):
        """Test service type normalization."""
        test_cases = [
            ("http", "http"),
            ("https", "http"),
            ("web", "http"),
            ("www", "http"),
            ("ssh", "ssh"),
            ("openssh", "ssh"),
            ("ftp", "ftp"),
            ("ftps", "ftp"),
            ("mysql", "mysql"),
            ("mariadb", "mysql"),
            ("postgres", "postgresql"),
            ("postgresql", "postgresql"),
            ("redis-server", "redis"),
            ("redis", "redis"),
            ("unknown-service", "unknown-service")
        ]

        for input_service, expected in test_cases:
            result = self.service._normalize_service_type(input_service)
            assert result == expected, f"Expected {expected}, got {result} for input {input_service}"

    def test_extract_product_name_from_banner(self):
        """Test product name extraction from service banners."""
        test_cases = [
            ("Apache/2.4.41 (Ubuntu)", None, "Apache httpd"),
            ("nginx/1.18.0 (Ubuntu)", None, "nginx"),
            ("SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5", None, "OpenSSH"),
            ("220 (vsFTPd 3.0.3)", None, "vsftpd"),
            ("HTTP/1.1 200 OK\r\nServer: Apache Tomcat/9.0.45", None, "Apache Tomcat"),
            ("", "MySQL", "MySQL"),  # Use product field if available
            ("Generic banner", None, "unknown")
        ]

        for banner, product_field, expected in test_cases:
            result = self.service._extract_product_name(banner, product_field)
            assert result == expected, f"Expected {expected}, got {result} for banner: {banner}"

    def test_detect_ssh_default_credentials(self):
        """Test SSH default credential detection."""
        # Create mock SSH service
        service = Mock()
        service.id = "ssh-service-1"
        service.service_name = "ssh"
        service.banner = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"
        service.product = "OpenSSH"
        service.version = "8.2p1"
        service.port = 22

        results = self.service.detect_default_credentials(service)

        # Should detect multiple common SSH credentials
        assert len(results) > 0

        # Check for admin/admin credential
        admin_matches = [r for r in results if r.credential.username == "admin" and r.credential.password == "admin"]
        assert len(admin_matches) > 0

        admin_match = admin_matches[0]
        assert admin_match.credential.risk_level == CredentialRisk.CRITICAL
        assert admin_match.confidence >= 0.4
        assert "SSH" in admin_match.remediation

    def test_detect_http_tomcat_credentials(self):
        """Test HTTP Tomcat default credential detection."""
        service = Mock()
        service.id = "http-service-1"
        service.service_name = "http"
        service.banner = "HTTP/1.1 200 OK\r\nServer: Apache-Coyote/1.1\r\nContent-Type: text/html"
        service.product = "Apache Tomcat"
        service.version = "9.0.45"
        service.port = 8080

        results = self.service.detect_default_credentials(service)

        # Should detect Tomcat credentials
        tomcat_matches = [r for r in results if "tomcat" in r.credential.username.lower()]
        assert len(tomcat_matches) > 0

        tomcat_match = tomcat_matches[0]
        assert tomcat_match.credential.risk_level in [CredentialRisk.HIGH, CredentialRisk.CRITICAL]
        assert tomcat_match.confidence > 0.4

    def test_detect_mysql_default_credentials(self):
        """Test MySQL default credential detection."""
        service = Mock()
        service.id = "mysql-service-1"
        service.service_name = "mysql"
        service.banner = "5.7.34-MySQL"
        service.product = "MySQL"
        service.version = "5.7.34"
        service.port = 3306

        results = self.service.detect_default_credentials(service)

        # Should detect root credentials
        root_matches = [r for r in results if r.credential.username == "root"]
        assert len(root_matches) > 0

        # Check for root with blank password
        blank_password_matches = [r for r in root_matches if r.credential.password == ""]
        assert len(blank_password_matches) > 0

        blank_match = blank_password_matches[0]
        assert blank_match.credential.risk_level == CredentialRisk.CRITICAL

    def test_detect_snmp_community_strings(self):
        """Test SNMP community string detection."""
        service = Mock()
        service.id = "snmp-service-1"
        service.service_name = "snmp"
        service.banner = "Net-SNMP/5.8"
        service.product = "Net-SNMP"
        service.version = "5.8"
        service.port = 161

        results = self.service.detect_default_credentials(service)

        # Should detect public/private community strings
        community_matches = [r for r in results if r.credential.password in ["public", "private"]]
        assert len(community_matches) >= 2

        public_match = [r for r in community_matches if r.credential.password == "public"][0]
        assert public_match.credential.risk_level == CredentialRisk.HIGH

    def test_detect_ftp_anonymous_access(self):
        """Test FTP anonymous access detection."""
        service = Mock()
        service.id = "ftp-service-1"
        service.service_name = "ftp"
        service.banner = "220 (vsFTPd 3.0.3)"
        service.product = "vsftpd"
        service.version = "3.0.3"
        service.port = 21

        results = self.service.detect_default_credentials(service)

        # Should detect anonymous FTP
        anonymous_matches = [r for r in results if r.credential.username == "anonymous"]
        assert len(anonymous_matches) > 0

        anon_match = anonymous_matches[0]
        assert anon_match.credential.risk_level == CredentialRisk.MEDIUM

    def test_no_credentials_for_secure_service(self):
        """Test that secure services don't trigger false positives."""
        service = Mock()
        service.id = "secure-service-1"
        service.service_name = "unknown"
        service.banner = "Custom secure service v1.0"
        service.product = "Custom Service"
        service.version = "1.0"
        service.port = 9999

        results = self.service.detect_default_credentials(service)

        # Should not detect any credentials for unknown service type
        assert len(results) == 0

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # High confidence: service type + port match
        service = Mock()
        service.id = "test-service-1"
        service.service_name = "ssh"
        service.banner = "SSH-2.0-OpenSSH_8.2p1"
        service.product = "OpenSSH"
        service.version = "8.2p1"
        service.port = 22

        results = self.service.detect_default_credentials(service)

        # Should have high confidence matches
        high_confidence_matches = [r for r in results if r.confidence >= 0.6]
        assert len(high_confidence_matches) > 0

    def test_analyze_service_credentials_complete(self):
        """Test complete credential analysis workflow."""
        service = Mock()
        service.id = "analysis-service-1"
        service.service_name = "ssh"
        service.banner = "SSH-2.0-OpenSSH_7.4"
        service.product = "OpenSSH"
        service.version = "7.4"
        service.port = 22

        results = self.service.analyze_service_credentials(service)

        # Verify analysis structure
        assert 'service_id' in results
        assert 'service_type' in results
        assert 'product' in results
        assert 'port' in results
        assert 'credentials_found' in results
        assert 'highest_risk_level' in results
        assert 'matches' in results

        # Should find SSH credentials
        assert results['credentials_found'] > 0
        assert results['service_type'] == 'ssh'
        assert results['product'] == 'OpenSSH'
        assert results['port'] == 22

        # Should have critical risk credentials
        assert results['critical_count'] > 0
        assert results['highest_risk_level'] == 'critical'

        # Matches should have required fields
        for match in results['matches']:
            assert 'username' in match
            assert 'password' in match
            assert 'description' in match
            assert 'risk_level' in match
            assert 'confidence' in match
            assert 'remediation' in match

    def test_generate_remediation_advice(self):
        """Test remediation advice generation."""
        # Test SSH remediation
        ssh_credential = Mock()
        ssh_credential.username = "admin"
        ssh_credential.password = "admin"

        remediation = self.service._generate_remediation(ssh_credential, "ssh")
        assert "SSH keys" in remediation
        assert "sshd_config" in remediation

        # Test MySQL remediation
        mysql_credential = Mock()
        mysql_credential.username = "root"
        mysql_credential.password = ""

        remediation = self.service._generate_remediation(mysql_credential, "mysql")
        assert "ALTER USER" in remediation

    def test_get_credential_statistics(self):
        """Test credential database statistics."""
        stats = self.service.get_credential_statistics()

        # Verify statistics structure
        assert 'total_credentials' in stats
        assert 'by_service_type' in stats
        assert 'by_risk_level' in stats
        assert 'by_detection_method' in stats

        # Should have entries for major service types
        assert 'ssh' in stats['by_service_type']
        assert 'http' in stats['by_service_type']
        assert 'mysql' in stats['by_service_type']

        # Should have entries for all risk levels
        assert 'critical' in stats['by_risk_level']
        assert 'high' in stats['by_risk_level']
        assert 'medium' in stats['by_risk_level']
        assert 'low' in stats['by_risk_level']

        # Total should equal sum of individual counts
        total_by_service = sum(stats['by_service_type'].values())
        assert stats['total_credentials'] == total_by_service

    def test_low_confidence_filtering(self):
        """Test that low confidence matches are filtered out."""
        # Create service that should only match generically (low confidence)
        service = Mock()
        service.id = "low-confidence-service"
        service.service_name = "unknown"
        service.banner = "Generic service"
        service.product = "unknown"
        service.version = "1.0"
        service.port = 12345  # Non-standard port

        results = self.service.detect_default_credentials(service)

        # Should not detect credentials due to low confidence
        assert len(results) == 0

    def test_case_insensitive_matching(self):
        """Test that product matching is case insensitive."""
        service = Mock()
        service.id = "case-test-service"
        service.service_name = "http"
        service.banner = "server: apache/2.4.41"  # lowercase
        service.product = "apache httpd"  # lowercase
        service.version = "2.4.41"
        service.port = 80

        results = self.service.detect_default_credentials(service)

        # Should still detect Apache credentials despite case differences
        apache_matches = [r for r in results if "apache" in r.credential.description.lower()]
        assert len(apache_matches) > 0

    def test_port_specific_detection(self):
        """Test that detection considers port-specific patterns."""
        # Test Tomcat on standard port
        service_standard = Mock()
        service_standard.id = "tomcat-standard"
        service_standard.service_name = "http"
        service_standard.banner = "Apache Tomcat/9.0"
        service_standard.product = "Apache Tomcat"
        service_standard.version = "9.0"
        service_standard.port = 8080  # Standard Tomcat port

        results_standard = self.service.detect_default_credentials(service_standard)

        # Test same service on non-standard port
        service_nonstandard = Mock()
        service_nonstandard.id = "tomcat-nonstandard"
        service_nonstandard.service_name = "http"
        service_nonstandard.banner = "Apache Tomcat/9.0"
        service_nonstandard.product = "Apache Tomcat"
        service_nonstandard.version = "9.0"
        service_nonstandard.port = 9999  # Non-standard port

        results_nonstandard = self.service.detect_default_credentials(service_nonstandard)

        # Standard port should have higher confidence
        if results_standard and results_nonstandard:
            max_confidence_standard = max(r.confidence for r in results_standard)
            max_confidence_nonstandard = max(r.confidence for r in results_nonstandard)
            assert max_confidence_standard >= max_confidence_nonstandard