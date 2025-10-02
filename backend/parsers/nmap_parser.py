import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
import re
import logging

from .base import ScanParser, ParsedHost, ParsedService, CorruptedScanError, ScanParsingError

logger = logging.getLogger(__name__)


class NmapXMLParser(ScanParser):
    """Parser for Nmap XML output files"""

    def can_parse(self, content: str, filename: str) -> bool:
        """Check if this is a valid Nmap XML file"""
        if not filename.endswith('.xml'):
            return False

        # Check for nmap XML signature in first 1000 characters
        return '<nmaprun' in content[:1000].lower()

    def parse(self, content: str) -> List[ParsedHost]:
        """Parse Nmap XML content into structured host data"""
        self.validate_content(content)

        try:
            # Parse XML with proper error handling
            root = self._parse_xml(content)

            # Extract hosts from XML
            hosts = []
            for host_elem in root.findall('.//host'):
                try:
                    parsed_host = self._parse_host(host_elem)
                    if parsed_host:
                        hosts.append(parsed_host)
                except Exception as e:
                    # Log individual host parsing errors but continue
                    logger.warning(f"Failed to parse host: {e}", exc_info=True)
                    continue

            return hosts

        except ET.ParseError as e:
            raise CorruptedScanError(f"Invalid XML structure: {e}")
        except CorruptedScanError:
            # Re-raise CorruptedScanError as-is
            raise
        except Exception as e:
            raise ScanParsingError(f"Failed to parse Nmap XML: {e}")

    def validate_content(self, content: str) -> None:
        """Validate Nmap XML content for corruption"""
        super().validate_content(content)

        # Check for basic XML structure
        if not content.strip().startswith('<?xml') and '<nmaprun' not in content[:200]:
            raise CorruptedScanError("File does not appear to be valid Nmap XML")

        # Check for minimum required elements
        if '<host' not in content:
            raise CorruptedScanError("No host elements found in XML")

    def _parse_xml(self, content: str) -> ET.Element:
        """Parse XML content with error handling"""
        try:
            return ET.fromstring(content)
        except ET.ParseError as e:
            # Try to detect common XML corruption issues
            if "not well-formed" in str(e):
                raise CorruptedScanError(f"XML is malformed: {e}")
            elif "no element found" in str(e):
                raise CorruptedScanError(f"XML is empty or truncated: {e}")
            else:
                raise CorruptedScanError(f"XML parsing failed: {e}")

    def _parse_host(self, host_elem: ET.Element) -> Optional[ParsedHost]:
        """Parse individual host element"""
        # Extract IP address (required)
        ip_address = self._extract_ip_address(host_elem)
        if not ip_address:
            return None

        # Extract hostname
        hostname = self._extract_hostname(host_elem)

        # Extract OS information
        os_family, os_details = self._extract_os_info(host_elem)

        # Extract MAC address
        mac_address = self._extract_mac_address(host_elem)

        # Extract host status
        status = self._extract_host_status(host_elem)

        # Extract services
        services = self._extract_services(host_elem)

        return ParsedHost(
            ip_address=ip_address,
            hostname=hostname,
            os_family=os_family,
            os_details=os_details,
            mac_address=mac_address,
            status=status,
            services=services,
            metadata={
                'scan_type': 'nmap',
                'parser_version': '1.0'
            }
        )

    def _extract_ip_address(self, host_elem: ET.Element) -> Optional[str]:
        """Extract IP address from host element"""
        address_elem = host_elem.find('.//address[@addrtype="ipv4"]')
        if address_elem is not None:
            return address_elem.get('addr')

        # Fallback to any address type
        address_elem = host_elem.find('.//address')
        if address_elem is not None:
            return address_elem.get('addr')

        return None

    def _extract_hostname(self, host_elem: ET.Element) -> Optional[str]:
        """Extract hostname from host element"""
        hostname_elem = host_elem.find('.//hostname')
        if hostname_elem is not None:
            return hostname_elem.get('name')
        return None

    def _extract_os_info(self, host_elem: ET.Element) -> tuple[Optional[str], Optional[str]]:
        """Extract OS family and details from host element"""
        os_elem = host_elem.find('.//os')
        if os_elem is None:
            return None, None

        # Get OS family from osmatch with highest accuracy
        osmatch_elems = os_elem.findall('.//osmatch')
        if osmatch_elems:
            # Sort by accuracy (highest first)
            osmatch_elems.sort(key=lambda x: int(x.get('accuracy', '0')), reverse=True)
            best_match = osmatch_elems[0]
            os_name = best_match.get('name', '')

            # Extract family from name (simplified)
            os_family = self._extract_os_family_from_name(os_name)
            return os_family, os_name

        return None, None

    def _extract_os_family_from_name(self, os_name: str) -> Optional[str]:
        """Extract OS family from OS name string"""
        if not os_name:
            return None

        os_name_lower = os_name.lower()

        if 'windows' in os_name_lower:
            return 'Windows'
        elif 'linux' in os_name_lower:
            return 'Linux'
        elif 'freebsd' in os_name_lower:
            return 'FreeBSD'
        elif 'openbsd' in os_name_lower:
            return 'OpenBSD'
        elif 'netbsd' in os_name_lower:
            return 'NetBSD'
        elif 'solaris' in os_name_lower or 'sunos' in os_name_lower:
            return 'Solaris'
        elif 'mac' in os_name_lower or 'darwin' in os_name_lower:
            return 'macOS'
        elif 'unix' in os_name_lower:
            return 'Unix'

        return 'Unknown'

    def _extract_mac_address(self, host_elem: ET.Element) -> Optional[str]:
        """Extract MAC address from host element"""
        mac_elem = host_elem.find('.//address[@addrtype="mac"]')
        if mac_elem is not None:
            return mac_elem.get('addr')
        return None

    def _extract_host_status(self, host_elem: ET.Element) -> str:
        """Extract host status from host element"""
        status_elem = host_elem.find('.//status')
        if status_elem is not None:
            state = status_elem.get('state', 'unknown')
            # Map nmap states to our standard states
            if state == 'up':
                return 'up'
            elif state == 'down':
                return 'down'
            else:
                return 'filtered'
        return 'up'  # Default to up if no status found

    def _extract_services(self, host_elem: ET.Element) -> List[ParsedService]:
        """Extract all services from host element"""
        services = []

        ports_elem = host_elem.find('.//ports')
        if ports_elem is None:
            return services

        for port_elem in ports_elem.findall('.//port'):
            service = self._parse_service(port_elem)
            if service:
                services.append(service)

        return services

    def _parse_service(self, port_elem: ET.Element) -> Optional[ParsedService]:
        """Parse individual service/port element"""
        # Extract port number and protocol
        port_num = port_elem.get('portid')
        protocol = port_elem.get('protocol', 'tcp')

        if not port_num:
            return None

        try:
            port_num = int(port_num)
        except ValueError:
            return None

        # Extract service information
        service_elem = port_elem.find('.//service')
        service_name = None
        product = None
        version = None
        banner = None
        cpe = None
        confidence = 'medium'

        if service_elem is not None:
            service_name = service_elem.get('name')
            product = service_elem.get('product')
            version = service_elem.get('version')

            # Combine product and version for banner if available
            if product:
                banner_parts = [product]
                if version:
                    banner_parts.append(version)
                banner = ' '.join(banner_parts)

            # Extract CPE if available
            cpe_elem = service_elem.find('.//cpe')
            if cpe_elem is not None:
                cpe = cpe_elem.text

            # Determine confidence based on service detection
            conf = service_elem.get('conf')
            if conf:
                try:
                    conf_num = int(conf)
                    if conf_num >= 8:
                        confidence = 'high'
                    elif conf_num >= 5:
                        confidence = 'medium'
                    else:
                        confidence = 'low'
                except ValueError:
                    pass

        # Check port state
        state_elem = port_elem.find('.//state')
        if state_elem is not None and state_elem.get('state') != 'open':
            # Skip closed or filtered ports
            return None

        return ParsedService(
            port=port_num,
            protocol=protocol,
            service_name=service_name,
            product=product,
            version=version,
            banner=banner,
            cpe=cpe,
            confidence=confidence
        )