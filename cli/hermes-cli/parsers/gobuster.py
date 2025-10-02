"""Gobuster text output parser."""

import re
import logging
from typing import Dict, Any
from .base import ToolOutputParser

logger = logging.getLogger(__name__)


class GobusterParser(ToolOutputParser):
    """Parser for gobuster text output format."""

    def get_tool_name(self) -> str:
        """Return the tool name."""
        return 'gobuster'

    def can_parse(self, content: str, filename: str) -> bool:
        """Check if content is gobuster output.

        Args:
            content: File content
            filename: Filename

        Returns:
            True if this appears to be gobuster output
        """
        # Look for gobuster markers
        if 'Gobuster' in content or 'by OJ Reeves' in content:
            return True
        if filename.endswith('-gobuster.txt') or 'gobuster' in filename.lower():
            return True
        return False

    def parse(self, content: str, lenient: bool = False) -> Dict[str, Any]:
        """Parse gobuster text output.

        Args:
            content: Text content
            lenient: If True, continue on errors

        Returns:
            Parsed data dictionary

        Raises:
            ValueError: If parsing fails in strict mode
        """
        result = {
            'tool': 'gobuster',
            'version': 'unknown',
            'mode': None,
            'target_url': None,
            'wordlist': None,
            'discoveries': []
        }

        lines = content.split('\n')

        # Parse header
        for line in lines[:50]:
            if 'Mode:' in line:
                match = re.search(r'Mode:\s*(\w+)', line)
                if match:
                    result['mode'] = match.group(1).lower()
            elif 'Url/Domain:' in line or 'URL:' in line:
                match = re.search(r'https?://[^\s]+', line)
                if match:
                    result['target_url'] = match.group(0)
            elif 'Wordlist:' in line:
                match = re.search(r'Wordlist:\s*(.+)', line)
                if match:
                    result['wordlist'] = match.group(1).strip()

        # Parse discoveries
        # Gobuster format varies by mode:
        # dir: "/path (Status: 200) [Size: 1234]"
        # dns: "Found: subdomain.example.com"
        # vhost: "Found: vhost.example.com (Status: 200) [Size: 1234]"

        dir_pattern = re.compile(r'(\/[^\s]+)\s+\(Status:\s*(\d+)\)\s+\[Size:\s*(\d+)\]')
        dns_pattern = re.compile(r'Found:\s+([^\s]+)')
        vhost_pattern = re.compile(r'Found:\s+([^\s]+)\s+\(Status:\s*(\d+)\)')

        for line in lines:
            try:
                # Try dir mode pattern
                match = dir_pattern.search(line)
                if match:
                    result['discoveries'].append({
                        'path': match.group(1),
                        'status_code': int(match.group(2)),
                        'size': int(match.group(3)),
                        'type': 'directory'
                    })
                    continue

                # Try vhost mode pattern
                match = vhost_pattern.search(line)
                if match:
                    result['discoveries'].append({
                        'vhost': match.group(1),
                        'status_code': int(match.group(2)),
                        'type': 'vhost'
                    })
                    continue

                # Try dns mode pattern
                match = dns_pattern.search(line)
                if match:
                    result['discoveries'].append({
                        'subdomain': match.group(1),
                        'type': 'dns'
                    })
                    continue

            except Exception as e:
                if lenient:
                    logger.warning(f"Skipped line due to error: {e}")
                    continue
                else:
                    raise

        result['total_found'] = len(result['discoveries'])
        return result
