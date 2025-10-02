import re
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class VersionMatch:
    product: str
    version: str
    confidence: ConfidenceLevel
    extraction_method: str
    raw_banner: str

@dataclass
class VulnerabilityMatch:
    cve_id: str
    cvss_score: Optional[float]
    severity: str
    confidence: ConfidenceLevel
    vulnerable_versions: List[str]
    description: str

class VersionExtractionService:
    """Service for extracting software versions from service banners using regex patterns."""

    def __init__(self):
        self.version_patterns = self._load_version_patterns()

    def _load_version_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load regex patterns for version extraction from service banners."""
        return {
            'ssh': [
                {
                    'pattern': r'OpenSSH[_\s]+([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:p[0-9]+)?)',
                    'product': 'OpenSSH',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'openssh_version_exact'
                },
                {
                    'pattern': r'SSH-[0-9\.]+-([^\s\r\n]+)',
                    'product': 'SSH',
                    'confidence': ConfidenceLevel.MEDIUM,
                    'method': 'ssh_protocol_version'
                },
                {
                    'pattern': r'Dropbear[_\s]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Dropbear SSH',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'dropbear_version_exact'
                },
                {
                    'pattern': r'libssh[_\s]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'libssh',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'libssh_version_exact'
                }
            ],
            'http': [
                {
                    'pattern': r'Apache/([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Apache httpd',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'apache_version_exact'
                },
                {
                    'pattern': r'nginx/([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'nginx',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'nginx_version_exact'
                },
                {
                    'pattern': r'Microsoft-IIS/([0-9]+\.[0-9]+)',
                    'product': 'Microsoft IIS',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'iis_version_exact'
                },
                {
                    'pattern': r'lighttpd/([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'lighttpd',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'lighttpd_version_exact'
                },
                {
                    'pattern': r'Jetty\(([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Eclipse Jetty',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'jetty_version_exact'
                }
            ],
            'ftp': [
                {
                    'pattern': r'vsftpd\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'vsftpd',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'vsftpd_version_exact'
                },
                {
                    'pattern': r'ProFTPD\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'ProFTPD',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'proftpd_version_exact'
                },
                {
                    'pattern': r'Pure-FTPd\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Pure-FTPd',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'pureftpd_version_exact'
                },
                {
                    'pattern': r'Microsoft FTP Service \(Version ([0-9]+\.[0-9]+)\)',
                    'product': 'Microsoft FTP Service',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'ms_ftp_version_exact'
                }
            ],
            'smtp': [
                {
                    'pattern': r'Postfix\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Postfix',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'postfix_version_exact'
                },
                {
                    'pattern': r'Sendmail\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Sendmail',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'sendmail_version_exact'
                },
                {
                    'pattern': r'Exim\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Exim',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'exim_version_exact'
                },
                {
                    'pattern': r'Microsoft ESMTP MAIL Service, Version: ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
                    'product': 'Microsoft SMTP Service',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'ms_smtp_version_exact'
                }
            ],
            'telnet': [
                {
                    'pattern': r'telnetd\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'telnetd',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'telnetd_version_exact'
                }
            ],
            'snmp': [
                {
                    'pattern': r'Net-SNMP/([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'Net-SNMP',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'netsnmp_version_exact'
                }
            ],
            'dns': [
                {
                    'pattern': r'BIND\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'ISC BIND',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'bind_version_exact'
                }
            ],
            'mysql': [
                {
                    'pattern': r'([0-9]+\.[0-9]+\.[0-9]+)-MySQL',
                    'product': 'MySQL',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'mysql_version_exact'
                }
            ],
            'postgresql': [
                {
                    'pattern': r'PostgreSQL\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
                    'product': 'PostgreSQL',
                    'confidence': ConfidenceLevel.HIGH,
                    'method': 'postgresql_version_exact'
                }
            ]
        }

    def extract_version(self, banner: str, service_name: str) -> Optional[VersionMatch]:
        """
        Extract version information from a service banner.

        Args:
            banner: The service banner text
            service_name: The service name (e.g., 'ssh', 'http', 'ftp')

        Returns:
            VersionMatch object if version found, None otherwise
        """
        if not banner:
            return None

        # Normalize service name for lookup
        service_key = service_name.lower()

        # Try exact service match first
        if service_key in self.version_patterns:
            result = self._try_patterns(banner, self.version_patterns[service_key])
            if result:
                return result

        # Try common patterns across all services for unknown service types
        all_patterns = []
        for patterns in self.version_patterns.values():
            all_patterns.extend(patterns)

        # Sort by confidence level (HIGH first)
        all_patterns.sort(key=lambda x: x['confidence'].value)

        return self._try_patterns(banner, all_patterns, confidence_penalty=True)

    def _try_patterns(self, banner: str, patterns: List[Dict[str, Any]], confidence_penalty: bool = False) -> Optional[VersionMatch]:
        """Try multiple regex patterns against a banner."""
        for pattern_info in patterns:
            try:
                pattern = pattern_info['pattern']
                match = re.search(pattern, banner, re.IGNORECASE)

                if match:
                    version = match.group(1)
                    confidence = pattern_info['confidence']

                    # Apply confidence penalty for cross-service matching
                    if confidence_penalty and confidence == ConfidenceLevel.HIGH:
                        confidence = ConfidenceLevel.MEDIUM
                    elif confidence_penalty and confidence == ConfidenceLevel.MEDIUM:
                        confidence = ConfidenceLevel.LOW

                    return VersionMatch(
                        product=pattern_info['product'],
                        version=version,
                        confidence=confidence,
                        extraction_method=pattern_info['method'],
                        raw_banner=banner
                    )

            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern}: {e}")
                continue

        return None

    def get_confidence_score(self, version_match: VersionMatch) -> float:
        """
        Calculate numeric confidence score for a version match.

        Returns:
            Float between 0.0 and 1.0
        """
        confidence_scores = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.3
        }

        return confidence_scores.get(version_match.confidence, 0.1)

    def validate_version_format(self, version: str) -> bool:
        """
        Validate that extracted version follows semantic versioning format.

        Args:
            version: Version string to validate

        Returns:
            True if version format is valid
        """
        # Basic semantic version pattern: major.minor[.patch][additional]
        version_pattern = r'^[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[a-zA-Z0-9\-\+\.]+)?$'
        return bool(re.match(version_pattern, version))


class VersionAnalysisService:
    """Main service for analyzing service versions and detecting vulnerabilities."""

    def __init__(self, vulnerability_repo=None, service_vuln_repo=None, review_queue_repo=None):
        self.vulnerability_repo = vulnerability_repo
        self.service_vuln_repo = service_vuln_repo
        self.review_queue_repo = review_queue_repo
        self.extraction_service = VersionExtractionService()

    def analyze_service_version(self, service) -> List[VulnerabilityMatch]:
        """
        Analyze a service for version-based vulnerabilities.

        Args:
            service: Service model instance

        Returns:
            List of vulnerability matches
        """
        if not service.banner:
            logger.debug(f"No banner available for service {service.id}")
            return []

        # Extract version from banner
        version_match = self.extraction_service.extract_version(
            service.banner,
            service.service_name or 'unknown'
        )

        if not version_match:
            logger.debug(f"No version extracted from banner: {service.banner}")
            return []

        logger.info(f"Extracted version: {version_match.product} {version_match.version} "
                   f"(confidence: {version_match.confidence.value})")

        # Find vulnerabilities for this product/version
        if self.vulnerability_repo:
            vulnerabilities = self.vulnerability_repo.find_by_product_version(
                version_match.product,
                version_match.version
            )

            vulnerability_matches = []
            for vuln in vulnerabilities:
                vuln_match = self._create_vulnerability_match(vuln, version_match)
                vulnerability_matches.append(vuln_match)

                # Create or update ServiceVulnerability record
                self._record_vulnerability_match(service, vuln, version_match)

            return vulnerability_matches

        return []

    def analyze_service_complete(self, service):
        """
        Complete vulnerability analysis including confidence thresholds and review queue.

        Args:
            service: Service model instance

        Returns:
            Dict with analysis results and actions taken
        """
        # Perform version analysis
        vulnerability_matches = self.analyze_service_version(service)

        results = {
            'service_id': str(service.id),
            'version_extracted': None,
            'vulnerabilities_found': len(vulnerability_matches),
            'high_confidence_matches': 0,
            'medium_confidence_matches': 0,
            'low_confidence_matches': 0,
            'review_queue_items': 0,
            'auto_validated': 0
        }

        if not vulnerability_matches:
            logger.info(f"No vulnerabilities found for service {service.id}")
            return results

        # Extract version info if available
        version_match = self.extraction_service.extract_version(
            service.banner,
            service.service_name or 'unknown'
        )
        if version_match:
            results['version_extracted'] = f"{version_match.product} {version_match.version}"

        # Process each vulnerability match
        for vuln_match in vulnerability_matches:
            confidence_level = vuln_match.confidence

            # Count by confidence level
            if confidence_level == ConfidenceLevel.HIGH:
                results['high_confidence_matches'] += 1
            elif confidence_level == ConfidenceLevel.MEDIUM:
                results['medium_confidence_matches'] += 1
            else:
                results['low_confidence_matches'] += 1

            # Apply confidence threshold logic
            if confidence_level == ConfidenceLevel.HIGH:
                # Auto-validate high confidence matches
                results['auto_validated'] += 1
                logger.info(f"Auto-validated high confidence match: {vuln_match.cve_id}")
            elif confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]:
                # Add to review queue
                if self.review_queue_repo:
                    self._add_to_review_queue(service, vuln_match, version_match)
                    results['review_queue_items'] += 1

        return results

    def _create_vulnerability_match(self, vulnerability, version_match: VersionMatch) -> VulnerabilityMatch:
        """Create a VulnerabilityMatch from a vulnerability and version match."""
        return VulnerabilityMatch(
            cve_id=vulnerability.cve_id,
            cvss_score=vulnerability.cvss_score,
            severity=vulnerability.severity.value,
            confidence=version_match.confidence,
            vulnerable_versions=[version_match.version],
            description=vulnerability.description or ""
        )

    def _record_vulnerability_match(self, service, vulnerability, version_match: VersionMatch):
        """Record a vulnerability match in the ServiceVulnerability table."""
        if not self.service_vuln_repo:
            return

        # Check if this match already exists
        existing = self.service_vuln_repo.find_by_service_and_vulnerability(
            service.id, vulnerability.id
        )

        if existing:
            # Update existing record with new confidence info
            self.service_vuln_repo.update(existing.id,
                confidence=version_match.confidence,
                confidence_score=self.extraction_service.get_confidence_score(version_match),
                version_matched=version_match.version,
                extraction_method=version_match.extraction_method,
                validated=(version_match.confidence == ConfidenceLevel.HIGH)
            )
        else:
            # Create new ServiceVulnerability record
            self.service_vuln_repo.create(
                service_id=service.id,
                vulnerability_id=vulnerability.id,
                detected_at=datetime.now(UTC),
                confidence=version_match.confidence,
                confidence_score=self.extraction_service.get_confidence_score(version_match),
                version_matched=version_match.version,
                extraction_method=version_match.extraction_method,
                validated=(version_match.confidence == ConfidenceLevel.HIGH),
                validation_method='VERSION_MATCH' if version_match.confidence == ConfidenceLevel.HIGH else None
            )

    def _add_to_review_queue(self, service, vuln_match: VulnerabilityMatch, version_match: VersionMatch):
        """Add uncertain vulnerability match to review queue."""
        if not self.review_queue_repo:
            return

        # Find the vulnerability by CVE ID
        vulnerability = self.vulnerability_repo.find_by_cve_id(vuln_match.cve_id)
        if not vulnerability:
            return

        # Check if already in review queue
        existing = self.review_queue_repo.find_by_service_and_vulnerability(
            service.id, vulnerability.id
        )
        if existing:
            return  # Already queued

        # Determine priority based on severity and confidence
        priority = self._calculate_review_priority(vuln_match, version_match)

        # Create review queue item
        self.review_queue_repo.create(
            service_id=service.id,
            vulnerability_id=vulnerability.id,
            status='PENDING',
            confidence=version_match.confidence,
            priority=priority,
            detection_method=version_match.extraction_method,
            version_extracted=version_match.version,
            banner_snippet=version_match.raw_banner[:500],  # Truncate for storage
            evidence_notes=f"Version {version_match.version} matches vulnerability range"
        )

        logger.info(f"Added to review queue: {vuln_match.cve_id} for service {service.id}")

    def _calculate_review_priority(self, vuln_match: VulnerabilityMatch, version_match: VersionMatch) -> str:
        """Calculate review priority based on vulnerability severity and confidence."""
        # High severity vulnerabilities get higher priority
        if vuln_match.severity in ['critical', 'high']:
            return 'high'
        elif vuln_match.severity == 'medium':
            # Medium severity with medium confidence gets medium priority
            if version_match.confidence == ConfidenceLevel.MEDIUM:
                return 'medium'
            else:
                return 'low'
        else:
            return 'low'

    def get_service_vulnerabilities(self, service_id: str) -> Dict[str, Any]:
        """
        Get all vulnerabilities for a service with their confidence levels.

        Args:
            service_id: Service ID

        Returns:
            Dictionary with vulnerability information
        """
        if not self.service_vuln_repo:
            return {'service_id': service_id, 'vulnerabilities': []}

        service_vulns = self.service_vuln_repo.find_by_service_id(service_id)

        vulnerabilities = []
        for sv in service_vulns:
            vuln_info = {
                'cve_id': sv.vulnerability.cve_id,
                'severity': sv.vulnerability.severity.value,
                'cvss_score': sv.vulnerability.cvss_score,
                'confidence': sv.confidence.value,
                'confidence_score': sv.confidence_score,
                'version_matched': sv.version_matched,
                'validated': sv.validated,
                'detected_at': sv.detected_at.isoformat() if sv.detected_at else None,
                'description': sv.vulnerability.description
            }
            vulnerabilities.append(vuln_info)

        return {
            'service_id': service_id,
            'vulnerabilities': vulnerabilities,
            'total_count': len(vulnerabilities),
            'validated_count': sum(1 for v in vulnerabilities if v['validated']),
            'high_confidence_count': sum(1 for v in vulnerabilities if v['confidence'] == 'high')
        }

    def validate_performance(self, service) -> Dict[str, Any]:
        """
        Validate that analysis completes within performance requirements.

        Returns:
            Performance metrics
        """
        import time
        start_time = time.time()

        # Perform analysis
        results = self.analyze_service_version(service)

        end_time = time.time()
        analysis_time = end_time - start_time

        return {
            'analysis_time_seconds': analysis_time,
            'meets_3_second_requirement': analysis_time < 3.0,
            'vulnerabilities_found': len(results),
            'service_id': str(service.id)
        }