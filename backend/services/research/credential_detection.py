import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CredentialRisk(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class DefaultCredential:
    service_type: str
    product: str
    version_pattern: Optional[str]
    username: str
    password: str
    description: str
    risk_level: CredentialRisk
    common_ports: List[int]
    detection_method: str

@dataclass
class CredentialMatch:
    service_id: str
    credential: DefaultCredential
    confidence: float
    match_reason: str
    remediation: str

class DefaultCredentialDetectionService:
    """Service for detecting potential default credential usage in services."""

    def __init__(self):
        self.credential_database = self._load_default_credentials()

    def _load_default_credentials(self) -> List[DefaultCredential]:
        """Load database of known default credentials by service type."""
        return [
            # SSH / Telnet Default Credentials
            DefaultCredential(
                service_type="ssh",
                product="Generic SSH",
                version_pattern=None,
                username="admin",
                password="admin",
                description="Common admin/admin default credentials",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[22],
                detection_method="service_type_match"
            ),
            DefaultCredential(
                service_type="ssh",
                product="Generic SSH",
                version_pattern=None,
                username="root",
                password="root",
                description="Root account with default password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[22],
                detection_method="service_type_match"
            ),
            DefaultCredential(
                service_type="ssh",
                product="Generic SSH",
                version_pattern=None,
                username="admin",
                password="password",
                description="Admin account with common default password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[22],
                detection_method="service_type_match"
            ),

            # Telnet Default Credentials
            DefaultCredential(
                service_type="telnet",
                product="Generic Telnet",
                version_pattern=None,
                username="admin",
                password="admin",
                description="Default telnet admin credentials",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[23],
                detection_method="service_type_match"
            ),
            DefaultCredential(
                service_type="telnet",
                product="Generic Telnet",
                version_pattern=None,
                username="admin",
                password="",
                description="Admin account with blank password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[23],
                detection_method="service_type_match"
            ),

            # Web/HTTP Default Credentials
            DefaultCredential(
                service_type="http",
                product="Apache Tomcat",
                version_pattern=r".*",
                username="admin",
                password="admin",
                description="Tomcat manager default credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[8080, 8443],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="http",
                product="Apache Tomcat",
                version_pattern=r".*",
                username="tomcat",
                password="tomcat",
                description="Tomcat service default credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[8080, 8443],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="http",
                product="nginx",
                version_pattern=r".*",
                username="admin",
                password="admin",
                description="Common nginx admin panel credentials",
                risk_level=CredentialRisk.MEDIUM,
                common_ports=[80, 443, 8080],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="http",
                product="Apache httpd",
                version_pattern=r".*",
                username="admin",
                password="admin",
                description="Apache web server admin credentials",
                risk_level=CredentialRisk.MEDIUM,
                common_ports=[80, 443],
                detection_method="product_match"
            ),

            # Database Default Credentials
            DefaultCredential(
                service_type="mysql",
                product="MySQL",
                version_pattern=r".*",
                username="root",
                password="",
                description="MySQL root account with blank password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[3306],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="mysql",
                product="MySQL",
                version_pattern=r".*",
                username="root",
                password="root",
                description="MySQL root account with default password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[3306],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="postgresql",
                product="PostgreSQL",
                version_pattern=r".*",
                username="postgres",
                password="postgres",
                description="PostgreSQL default credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[5432],
                detection_method="product_match"
            ),
            DefaultCredential(
                service_type="postgresql",
                product="PostgreSQL",
                version_pattern=r".*",
                username="postgres",
                password="",
                description="PostgreSQL with blank password",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[5432],
                detection_method="product_match"
            ),

            # SNMP Default Credentials
            DefaultCredential(
                service_type="snmp",
                product="Generic SNMP",
                version_pattern=None,
                username="",
                password="public",
                description="SNMP default community string 'public'",
                risk_level=CredentialRisk.HIGH,
                common_ports=[161],
                detection_method="service_type_match"
            ),
            DefaultCredential(
                service_type="snmp",
                product="Generic SNMP",
                version_pattern=None,
                username="",
                password="private",
                description="SNMP default community string 'private'",
                risk_level=CredentialRisk.HIGH,
                common_ports=[161],
                detection_method="service_type_match"
            ),

            # FTP Default Credentials
            DefaultCredential(
                service_type="ftp",
                product="Generic FTP",
                version_pattern=None,
                username="anonymous",
                password="anonymous",
                description="FTP anonymous access enabled",
                risk_level=CredentialRisk.MEDIUM,
                common_ports=[21],
                detection_method="service_type_match"
            ),
            DefaultCredential(
                service_type="ftp",
                product="vsftpd",
                version_pattern=r".*",
                username="admin",
                password="admin",
                description="vsftpd default admin credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[21],
                detection_method="product_match"
            ),

            # VNC Default Credentials
            DefaultCredential(
                service_type="vnc",
                product="Generic VNC",
                version_pattern=None,
                username="",
                password="",
                description="VNC with no password authentication",
                risk_level=CredentialRisk.CRITICAL,
                common_ports=[5900, 5901, 5902],
                detection_method="service_type_match"
            ),

            # Redis Default Credentials
            DefaultCredential(
                service_type="redis",
                product="Redis",
                version_pattern=r".*",
                username="",
                password="",
                description="Redis with no authentication",
                risk_level=CredentialRisk.HIGH,
                common_ports=[6379],
                detection_method="product_match"
            ),

            # MongoDB Default Credentials
            DefaultCredential(
                service_type="mongodb",
                product="MongoDB",
                version_pattern=r".*",
                username="",
                password="",
                description="MongoDB with no authentication",
                risk_level=CredentialRisk.HIGH,
                common_ports=[27017],
                detection_method="product_match"
            ),

            # Router/IoT Device Defaults
            DefaultCredential(
                service_type="http",
                product="Generic Router",
                version_pattern=None,
                username="admin",
                password="admin",
                description="Common router admin panel credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[80, 443, 8080],
                detection_method="banner_heuristics"
            ),
            DefaultCredential(
                service_type="telnet",
                product="Generic IoT",
                version_pattern=None,
                username="admin",
                password="123456",
                description="Common IoT device credentials",
                risk_level=CredentialRisk.HIGH,
                common_ports=[23],
                detection_method="banner_heuristics"
            ),

            # Low risk examples
            DefaultCredential(
                service_type="ftp",
                product="Generic FTP",
                version_pattern=None,
                username="guest",
                password="guest",
                description="Guest FTP access (informational)",
                risk_level=CredentialRisk.LOW,
                common_ports=[21],
                detection_method="service_type_match"
            )
        ]

    def detect_default_credentials(self, service) -> List[CredentialMatch]:
        """
        Detect potential default credentials for a service.

        Args:
            service: Service model instance

        Returns:
            List of potential default credential matches
        """
        matches = []

        if not service:
            return matches

        # Extract service information
        service_type = self._normalize_service_type(service.service_name)
        product = self._extract_product_name(service.banner, service.product)
        port = service.port

        logger.debug(f"Analyzing service {service.id}: type={service_type}, product={product}, port={port}")

        # Check each credential in database
        for credential in self.credential_database:
            match_info = self._check_credential_match(service, credential, service_type, product, port)
            if match_info:
                matches.append(match_info)

        return matches

    def _normalize_service_type(self, service_name: str) -> str:
        """Normalize service name for credential matching."""
        if not service_name:
            return "unknown"

        service_name = service_name.lower().strip()

        # Handle common service name variations
        if service_name in ["http", "https", "web", "www"]:
            return "http"
        elif service_name in ["ssh", "openssh"]:
            return "ssh"
        elif service_name in ["ftp", "ftps"]:
            return "ftp"
        elif service_name in ["mysql", "mariadb"]:
            return "mysql"
        elif service_name in ["postgres", "postgresql"]:
            return "postgresql"
        elif service_name in ["redis-server", "redis"]:
            return "redis"
        elif service_name in ["mongo", "mongodb"]:
            return "mongodb"
        elif service_name in ["snmp"]:
            return "snmp"
        elif service_name in ["vnc", "vnc-server"]:
            return "vnc"
        elif service_name in ["telnet"]:
            return "telnet"

        return service_name

    def _extract_product_name(self, banner: str, product_field: str) -> str:
        """Extract product name from banner or product field."""
        if product_field and isinstance(product_field, str):
            return product_field.strip()

        if not banner or not isinstance(banner, str):
            return "unknown"

        banner = banner.strip()

        # Common product extraction patterns
        product_patterns = [
            (r"Apache/[\d\.]+", "Apache httpd"),
            (r"nginx/[\d\.]+", "nginx"),
            (r"OpenSSH[_\s]+[\d\.]+", "OpenSSH"),
            (r"MySQL[\s\d\.]*", "MySQL"),
            (r"PostgreSQL[\s\d\.]*", "PostgreSQL"),
            (r"vsftpd[\s\d\.]*", "vsftpd"),
            (r"Postfix[\s\d\.]*", "Postfix"),
            (r"Tomcat[/\s][\d\.]+", "Apache Tomcat"),
            (r"Redis[\s\d\.]*", "Redis"),
            (r"MongoDB[\s\d\.]*", "MongoDB")
        ]

        for pattern, product in product_patterns:
            if re.search(pattern, banner, re.IGNORECASE):
                return product

        return "unknown"

    def _check_credential_match(self, service, credential: DefaultCredential,
                              service_type: str, product: str, port: int) -> Optional[CredentialMatch]:
        """Check if a service matches a default credential pattern."""

        confidence = 0.0
        match_reasons = []

        # Check service type match
        if credential.service_type == service_type:
            confidence += 0.4
            match_reasons.append(f"Service type '{service_type}' matches")

        # Check product match (with type checking for mock safety)
        if not credential.product.startswith("Generic") and isinstance(product, str):
            if credential.product.lower() in product.lower() or product.lower() in credential.product.lower():
                confidence += 0.4
                match_reasons.append(f"Product '{product}' matches '{credential.product}'")

        # Check port match
        if port in credential.common_ports:
            confidence += 0.2
            match_reasons.append(f"Port {port} is common for this service")

        # Check version pattern if specified (with type checking for mock safety)
        if credential.version_pattern and service.version and isinstance(service.version, str):
            if re.match(credential.version_pattern, service.version):
                confidence += 0.1
                match_reasons.append("Version pattern matches")

        # Minimum confidence threshold
        if confidence < 0.4:
            return None

        # Generate remediation advice
        remediation = self._generate_remediation(credential, service_type)

        return CredentialMatch(
            service_id=str(service.id),
            credential=credential,
            confidence=confidence,
            match_reason="; ".join(match_reasons),
            remediation=remediation
        )

    def _generate_remediation(self, credential: DefaultCredential, service_type: str) -> str:
        """Generate remediation advice for default credentials."""

        base_advice = f"Change default credentials ({credential.username}/{credential.password})"

        specific_advice = {
            "ssh": "Disable password authentication and use SSH keys. Edit /etc/ssh/sshd_config",
            "telnet": "Replace Telnet with SSH for secure remote access",
            "http": "Change web admin panel credentials and enable HTTPS",
            "mysql": "Set strong root password: ALTER USER 'root'@'localhost' IDENTIFIED BY 'strong_password';",
            "postgresql": "Set postgres user password and configure pg_hba.conf for authentication",
            "ftp": "Disable anonymous FTP access and use SFTP/FTPS instead",
            "snmp": "Change community strings and use SNMPv3 with authentication",
            "vnc": "Set VNC password and use SSH tunneling for secure access",
            "redis": "Enable authentication with requirepass directive in redis.conf",
            "mongodb": "Enable authentication and create admin user"
        }

        service_advice = specific_advice.get(service_type, "Follow vendor security hardening guidelines")

        return f"{base_advice}. {service_advice}"

    def analyze_service_credentials(self, service) -> Dict[str, Any]:
        """
        Complete credential analysis for a service.

        Args:
            service: Service model instance

        Returns:
            Dictionary with analysis results
        """
        credential_matches = self.detect_default_credentials(service)

        results = {
            'service_id': str(service.id),
            'service_type': self._normalize_service_type(service.service_name),
            'product': self._extract_product_name(service.banner, service.product),
            'port': service.port,
            'credentials_found': len(credential_matches),
            'highest_risk_level': None,
            'critical_count': 0,
            'high_count': 0,
            'medium_count': 0,
            'low_count': 0,
            'matches': []
        }

        if not credential_matches:
            return results

        # Process matches
        highest_risk = CredentialRisk.LOW
        for match in credential_matches:
            risk_level = match.credential.risk_level

            # Count by risk level
            if risk_level == CredentialRisk.CRITICAL:
                results['critical_count'] += 1
                highest_risk = CredentialRisk.CRITICAL
            elif risk_level == CredentialRisk.HIGH:
                results['high_count'] += 1
                if highest_risk != CredentialRisk.CRITICAL:
                    highest_risk = CredentialRisk.HIGH
            elif risk_level == CredentialRisk.MEDIUM:
                results['medium_count'] += 1
                if highest_risk not in [CredentialRisk.CRITICAL, CredentialRisk.HIGH]:
                    highest_risk = CredentialRisk.MEDIUM
            else:
                results['low_count'] += 1

            # Add match details
            match_info = {
                'username': match.credential.username,
                'password': match.credential.password,
                'description': match.credential.description,
                'risk_level': risk_level.value,
                'confidence': match.confidence,
                'match_reason': match.match_reason,
                'remediation': match.remediation
            }
            results['matches'].append(match_info)

        results['highest_risk_level'] = highest_risk.value

        return results

    def get_credential_statistics(self) -> Dict[str, Any]:
        """Get statistics about the credential database."""
        stats = {
            'total_credentials': len(self.credential_database),
            'by_service_type': {},
            'by_risk_level': {},
            'by_detection_method': {}
        }

        for cred in self.credential_database:
            # Count by service type
            service_type = cred.service_type
            stats['by_service_type'][service_type] = stats['by_service_type'].get(service_type, 0) + 1

            # Count by risk level
            risk_level = cred.risk_level.value
            stats['by_risk_level'][risk_level] = stats['by_risk_level'].get(risk_level, 0) + 1

            # Count by detection method
            method = cred.detection_method
            stats['by_detection_method'][method] = stats['by_detection_method'].get(method, 0) + 1

        return stats