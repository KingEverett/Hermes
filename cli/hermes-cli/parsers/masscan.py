"""Masscan JSON output parser."""

import json
import logging
from typing import Dict, Any
from .base import ToolOutputParser

logger = logging.getLogger(__name__)


class MasscanParser(ToolOutputParser):
    """Parser for masscan JSON output format."""

    def get_tool_name(self) -> str:
        """Return the tool name."""
        return 'masscan'

    def can_parse(self, content: str, filename: str) -> bool:
        """Check if content is masscan JSON format.

        Args:
            content: File content
            filename: Filename

        Returns:
            True if this appears to be masscan JSON
        """
        # Check file extension
        if filename.endswith('.json'):
            # Check for masscan JSON markers
            if 'masscan' in content or ('ip' in content and 'ports' in content):
                try:
                    # Try to parse as JSON
                    data = json.loads(content[:1000])  # Check first 1KB
                    # Look for masscan-specific fields
                    if isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        if 'ip' in first_item and 'ports' in first_item:
                            return True
                except:
                    pass
        return False

    def parse(self, content: str, lenient: bool = False) -> Dict[str, Any]:
        """Parse masscan JSON output.

        Args:
            content: JSON content
            lenient: If True, continue on errors

        Returns:
            Parsed data dictionary

        Raises:
            ValueError: If parsing fails in strict mode
        """
        try:
            data = json.loads(content)

            result = {
                'tool': 'masscan',
                'version': 'unknown',
                'hosts': []
            }

            # Masscan outputs array of port records
            host_map = {}

            for record in data:
                try:
                    ip = record.get('ip')
                    if not ip:
                        if not lenient:
                            raise ValueError("Missing 'ip' field in record")
                        continue

                    # Group by IP
                    if ip not in host_map:
                        host_map[ip] = {
                            'ip': ip,
                            'timestamp': record.get('timestamp'),
                            'ports': []
                        }

                    # Extract port info
                    ports = record.get('ports', [])
                    for port in ports:
                        port_data = {
                            'port': port.get('port'),
                            'proto': port.get('proto', 'tcp'),
                            'status': port.get('status', 'open'),
                            'reason': port.get('reason', ''),
                            'ttl': port.get('ttl')
                        }
                        host_map[ip]['ports'].append(port_data)

                except Exception as e:
                    if lenient:
                        logger.warning(f"Skipped record due to error: {e}")
                        continue
                    else:
                        raise

            # Convert to list
            result['hosts'] = list(host_map.values())
            result['host_count'] = len(result['hosts'])
            result['port_count'] = sum(len(h['ports']) for h in result['hosts'])

            return result

        except json.JSONDecodeError as e:
            if lenient:
                logger.warning(f"JSON parse error (lenient mode): {e}")
                return {
                    'tool': 'masscan',
                    'version': 'unknown',
                    'hosts': [],
                    'host_count': 0,
                    'parse_error': str(e)
                }
            else:
                raise ValueError(f"Invalid masscan JSON: {e}")
