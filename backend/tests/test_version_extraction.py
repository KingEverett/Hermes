import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.research.version_analysis import (
    VersionExtractionService,
    VersionMatch,
    ConfidenceLevel
)


class TestVersionExtractionService:
    """Test suite for version extraction from service banners."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = VersionExtractionService()

    def test_ssh_version_extraction(self):
        """Test SSH version extraction patterns."""
        test_cases = [
            # OpenSSH versions
            {
                'banner': 'SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5',
                'service': 'ssh',
                'expected_product': 'OpenSSH',
                'expected_version': '8.2p1',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            {
                'banner': 'SSH-2.0-OpenSSH_7.4',
                'service': 'ssh',
                'expected_product': 'OpenSSH',
                'expected_version': '7.4',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # Dropbear SSH
            {
                'banner': 'SSH-2.0-dropbear_2019.78',
                'service': 'ssh',
                'expected_product': 'SSH',
                'expected_version': 'dropbear_2019.78',
                'expected_confidence': ConfidenceLevel.MEDIUM
            },
            # Generic SSH protocol version
            {
                'banner': 'SSH-2.0-libssh_0.8.7',
                'service': 'ssh',
                'expected_product': 'SSH',
                'expected_version': 'libssh_0.8.7',
                'expected_confidence': ConfidenceLevel.MEDIUM
            }
        ]

        for case in test_cases:
            result = self.service.extract_version(case['banner'], case['service'])
            assert result is not None, f"Failed to extract version from: {case['banner']}"
            assert result.product == case['expected_product']
            assert result.version == case['expected_version']
            assert result.confidence == case['expected_confidence']

    def test_http_version_extraction(self):
        """Test HTTP server version extraction patterns."""
        test_cases = [
            # Apache versions
            {
                'banner': 'Apache/2.4.41 (Ubuntu)',
                'service': 'http',
                'expected_product': 'Apache httpd',
                'expected_version': '2.4.41',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            {
                'banner': 'Server: Apache/2.2.15',
                'service': 'http',
                'expected_product': 'Apache httpd',
                'expected_version': '2.2.15',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # Nginx versions
            {
                'banner': 'nginx/1.18.0 (Ubuntu)',
                'service': 'http',
                'expected_product': 'nginx',
                'expected_version': '1.18.0',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            {
                'banner': 'Server: nginx/1.14.2',
                'service': 'http',
                'expected_product': 'nginx',
                'expected_version': '1.14.2',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # IIS versions
            {
                'banner': 'Microsoft-IIS/10.0',
                'service': 'http',
                'expected_product': 'Microsoft IIS',
                'expected_version': '10.0',
                'expected_confidence': ConfidenceLevel.HIGH
            }
        ]

        for case in test_cases:
            result = self.service.extract_version(case['banner'], case['service'])
            assert result is not None, f"Failed to extract version from: {case['banner']}"
            assert result.product == case['expected_product']
            assert result.version == case['expected_version']
            assert result.confidence == case['expected_confidence']

    def test_ftp_version_extraction(self):
        """Test FTP server version extraction patterns."""
        test_cases = [
            # vsftpd
            {
                'banner': '220 (vsFTPd 3.0.3)',
                'service': 'ftp',
                'expected_product': 'vsftpd',
                'expected_version': '3.0.3',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # ProFTPD
            {
                'banner': '220 ProFTPD 1.3.6 Server ready',
                'service': 'ftp',
                'expected_product': 'ProFTPD',
                'expected_version': '1.3.6',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # Pure-FTPd
            {
                'banner': '220---------- Welcome to Pure-FTPd 1.0.47 ----------',
                'service': 'ftp',
                'expected_product': 'Pure-FTPd',
                'expected_version': '1.0.47',
                'expected_confidence': ConfidenceLevel.HIGH
            }
        ]

        for case in test_cases:
            result = self.service.extract_version(case['banner'], case['service'])
            assert result is not None, f"Failed to extract version from: {case['banner']}"
            assert result.product == case['expected_product']
            assert result.version == case['expected_version']
            assert result.confidence == case['expected_confidence']

    def test_smtp_version_extraction(self):
        """Test SMTP server version extraction patterns."""
        test_cases = [
            # Postfix
            {
                'banner': '220 mail.example.com ESMTP Postfix 3.4.13',
                'service': 'smtp',
                'expected_product': 'Postfix',
                'expected_version': '3.4.13',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # Sendmail
            {
                'banner': '220 mail.example.com ESMTP Sendmail 8.15.2',
                'service': 'smtp',
                'expected_product': 'Sendmail',
                'expected_version': '8.15.2',
                'expected_confidence': ConfidenceLevel.HIGH
            },
            # Exim
            {
                'banner': '220 mail.example.com ESMTP Exim 4.94.2',
                'service': 'smtp',
                'expected_product': 'Exim',
                'expected_version': '4.94.2',
                'expected_confidence': ConfidenceLevel.HIGH
            }
        ]

        for case in test_cases:
            result = self.service.extract_version(case['banner'], case['service'])
            assert result is not None, f"Failed to extract version from: {case['banner']}"
            assert result.product == case['expected_product']
            assert result.version == case['expected_version']
            assert result.confidence == case['expected_confidence']

    def test_unknown_service_fallback(self):
        """Test version extraction for unknown service types."""
        # Should still extract Apache version even for unknown service
        result = self.service.extract_version('Apache/2.4.41 (Ubuntu)', 'unknown')
        assert result is not None
        assert result.product == 'Apache httpd'
        assert result.version == '2.4.41'
        # Confidence should be reduced due to cross-service matching
        assert result.confidence == ConfidenceLevel.MEDIUM

    def test_no_version_found(self):
        """Test behavior when no version can be extracted."""
        test_cases = [
            ('No version info here', 'http'),
            ('', 'ssh'),
            ('Some random text', 'ftp'),
            ('220 FTP server ready', 'ftp')  # Generic FTP banner without version
        ]

        for banner, service in test_cases:
            result = self.service.extract_version(banner, service)
            assert result is None, f"Unexpected version extraction from: {banner}"

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        # High confidence match
        high_result = VersionMatch(
            product='OpenSSH',
            version='8.2p1',
            confidence=ConfidenceLevel.HIGH,
            extraction_method='openssh_version_exact',
            raw_banner='SSH-2.0-OpenSSH_8.2p1'
        )
        assert self.service.get_confidence_score(high_result) == 0.9

        # Medium confidence match
        medium_result = VersionMatch(
            product='SSH',
            version='libssh_0.8.7',
            confidence=ConfidenceLevel.MEDIUM,
            extraction_method='ssh_protocol_version',
            raw_banner='SSH-2.0-libssh_0.8.7'
        )
        assert self.service.get_confidence_score(medium_result) == 0.6

        # Low confidence match
        low_result = VersionMatch(
            product='Apache httpd',
            version='2.4.41',
            confidence=ConfidenceLevel.LOW,
            extraction_method='apache_version_exact',
            raw_banner='Apache/2.4.41 (Ubuntu)'
        )
        assert self.service.get_confidence_score(low_result) == 0.3

    def test_version_format_validation(self):
        """Test version format validation."""
        valid_versions = [
            '8.2p1',
            '2.4.41',
            '1.18.0',
            '10.0',
            '3.0.3',
            '1.3.6-beta',
            '2.4.41-ubuntu'
        ]

        invalid_versions = [
            'invalid',
            '',
            'version',
            'abc.def'
        ]

        for version in valid_versions:
            assert self.service.validate_version_format(version), f"Valid version rejected: {version}"

        for version in invalid_versions:
            assert not self.service.validate_version_format(version), f"Invalid version accepted: {version}"

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Very long banner
        long_banner = 'A' * 10000 + 'Apache/2.4.41' + 'B' * 10000
        result = self.service.extract_version(long_banner, 'http')
        assert result is not None
        assert result.product == 'Apache httpd'
        assert result.version == '2.4.41'

        # Special characters in banner
        special_banner = 'Server: nginx/1.18.0 (Ubuntu) with special chars: @#$%^&*()'
        result = self.service.extract_version(special_banner, 'http')
        assert result is not None
        assert result.product == 'nginx'
        assert result.version == '1.18.0'

        # Multiple version patterns in same banner
        multiple_banner = 'Apache/2.4.41 nginx/1.18.0'
        result = self.service.extract_version(multiple_banner, 'http')
        assert result is not None
        # Should match the first pattern (Apache)
        assert result.product == 'Apache httpd'
        assert result.version == '2.4.41'

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        test_cases = [
            ('APACHE/2.4.41', 'http', 'Apache httpd', '2.4.41'),
            ('nginx/1.18.0', 'http', 'nginx', '1.18.0'),
            ('NGINX/1.18.0', 'http', 'nginx', '1.18.0'),
            ('ssh-2.0-openssh_8.2p1', 'ssh', 'OpenSSH', '8.2p1')
        ]

        for banner, service, expected_product, expected_version in test_cases:
            result = self.service.extract_version(banner, service)
            assert result is not None, f"Failed to extract from case variant: {banner}"
            assert result.product == expected_product
            assert result.version == expected_version

    def test_real_nmap_banners(self):
        """Test with real banner examples from nmap scans."""
        real_banners = [
            # Real SSH banners
            {
                'banner': 'SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5',
                'service': 'ssh',
                'expected_product': 'OpenSSH',
                'expected_version': '8.2p1'
            },
            {
                'banner': 'SSH-2.0-OpenSSH_7.4',
                'service': 'ssh',
                'expected_product': 'OpenSSH',
                'expected_version': '7.4'
            },
            # Real HTTP banners
            {
                'banner': 'HTTP/1.1 200 OK\r\nDate: Sun, 18 Oct 2009 08:56:53 GMT\r\nServer: Apache/2.2.14 (Win32)\r\nLast-Modified: Sat, 20 Nov 2004 07:16:26 GMT\r\nETag: "10000000565a5-2c-3e94b66c2e680"\r\nAccept-Ranges: bytes\r\nContent-Length: 44\r\nConnection: close\r\nContent-Type: text/html\r\nX-Pad: avoid browser bug',
                'service': 'http',
                'expected_product': 'Apache httpd',
                'expected_version': '2.2.14'
            },
            # Real FTP banners
            {
                'banner': '220 (vsFTPd 3.0.3)\r\n',
                'service': 'ftp',
                'expected_product': 'vsftpd',
                'expected_version': '3.0.3'
            }
        ]

        for case in real_banners:
            result = self.service.extract_version(case['banner'], case['service'])
            assert result is not None, f"Failed to extract from real banner: {case['banner'][:50]}..."
            assert result.product == case['expected_product']
            assert result.version == case['expected_version']