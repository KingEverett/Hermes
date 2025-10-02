"""Nmap XML output parser."""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any
from .base import ToolOutputParser

logger = logging.getLogger(__name__)


class NmapParser(ToolOutputParser):
    """Parser for nmap XML output format."""

    def get_tool_name(self) -> str:
        """Return the tool name."""
        return 'nmap'

    def can_parse(self, content: str, filename: str) -> bool:
        """Check if content is nmap XML format.

        Args:
            content: File content
            filename: Filename

        Returns:
            True if this appears to be nmap XML
        """
        # Check file extension
        if filename.endswith('.xml'):
            # Check for nmap XML markers
            if '<?xml' in content and ('<nmaprun' in content or 'nmap' in content.lower()):
                return True
        return False

    def parse(self, content: str, lenient: bool = False) -> Dict[str, Any]:
        """Parse nmap XML output.

        Args:
            content: XML content
            lenient: If True, continue on errors

        Returns:
            Parsed data dictionary

        Raises:
            ValueError: If parsing fails in strict mode
        """
        try:
            root = ET.fromstring(content)

            # Extract basic scan info
            result = {
                'tool': 'nmap',
                'version': root.get('version', 'unknown'),
                'start_time': root.get('start'),
                'args': root.get('args', ''),
                'hosts': []
            }

            # Parse hosts
            for host_elem in root.findall('.//host'):
                try:
                    host = self._parse_host(host_elem)
                    result['hosts'].append(host)
                except Exception as e:
                    if lenient:
                        logger.warning(f"Skipped host due to error: {e}")
                        continue
                    else:
                        raise

            result['host_count'] = len(result['hosts'])
            return result

        except ET.ParseError as e:
            if lenient:
                # Try to salvage partial results
                logger.warning(f"XML parse error (lenient mode): {e}")
                return self._parse_partial_xml(content)
            else:
                raise ValueError(f"Invalid nmap XML: {e}")

    def _parse_host(self, host_elem: ET.Element) -> Dict[str, Any]:
        """Parse a single host element.

        Args:
            host_elem: Host XML element

        Returns:
            Host data dictionary
        """
        host = {
            'addresses': [],
            'hostnames': [],
            'ports': [],
            'os': None
        }

        # Get addresses
        for addr in host_elem.findall('.//address'):
            host['addresses'].append({
                'addr': addr.get('addr'),
                'addrtype': addr.get('addrtype')
            })

        # Get hostnames
        for hostname in host_elem.findall('.//hostname'):
            host['hostnames'].append(hostname.get('name'))

        # Get ports
        for port in host_elem.findall('.//port'):
            port_data = {
                'portid': port.get('portid'),
                'protocol': port.get('protocol'),
                'state': None,
                'service': None
            }

            state = port.find('state')
            if state is not None:
                port_data['state'] = state.get('state')

            service = port.find('service')
            if service is not None:
                port_data['service'] = {
                    'name': service.get('name'),
                    'product': service.get('product'),
                    'version': service.get('version')
                }

            host['ports'].append(port_data)

        return host

    def _parse_partial_xml(self, content: str) -> Dict[str, Any]:
        """Attempt to parse partial/corrupted XML.

        Args:
            content: Partial XML content

        Returns:
            Best-effort parsed data
        """
        # Return minimal valid structure
        return {
            'tool': 'nmap',
            'version': 'unknown',
            'hosts': [],
            'host_count': 0,
            'parse_error': 'Partial XML - unable to fully parse'
        }
