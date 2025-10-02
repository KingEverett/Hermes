"""Dirb text output parser."""

import re
import logging
from typing import Dict, Any, List
from .base import ToolOutputParser

logger = logging.getLogger(__name__)


class DirbParser(ToolOutputParser):
    """Parser for dirb text output format."""

    def get_tool_name(self) -> str:
        """Return the tool name."""
        return 'dirb'

    def can_parse(self, content: str, filename: str) -> bool:
        """Check if content is dirb output.

        Args:
            content: File content
            filename: Filename

        Returns:
            True if this appears to be dirb output
        """
        # Look for dirb markers
        if 'DIRB' in content or 'Directory Brute Force' in content:
            return True
        if filename.endswith('-dirb.txt') or 'dirb' in filename.lower():
            return True
        return False

    def parse(self, content: str, lenient: bool = False) -> Dict[str, Any]:
        """Parse dirb text output.

        Args:
            content: Text content
            lenient: If True, continue on errors

        Returns:
            Parsed data dictionary

        Raises:
            ValueError: If parsing fails in strict mode
        """
        result = {
            'tool': 'dirb',
            'version': 'unknown',
            'target_url': None,
            'wordlist': None,
            'directories': [],
            'files': []
        }

        lines = content.split('\n')

        # Parse header to get target and wordlist
        for line in lines[:50]:  # Check first 50 lines for header
            if 'URL_BASE:' in line or 'TESTING:' in line:
                match = re.search(r'https?://[^\s]+', line)
                if match:
                    result['target_url'] = match.group(0)
            elif 'WORDLIST_FILES:' in line:
                match = re.search(r':\s*(.+)', line)
                if match:
                    result['wordlist'] = match.group(1).strip()

        # Parse discovered paths
        # Dirb format: "+ http://example.com/path (CODE:200|SIZE:1234)"
        path_pattern = re.compile(r'\+\s+(https?://[^\s]+)\s+\(CODE:(\d+)\|SIZE:(\d+)\)')

        for line in lines:
            try:
                match = path_pattern.search(line)
                if match:
                    url = match.group(1)
                    code = int(match.group(2))
                    size = int(match.group(3))

                    item = {
                        'url': url,
                        'status_code': code,
                        'size': size
                    }

                    # Determine if directory or file
                    if url.endswith('/'):
                        result['directories'].append(item)
                    else:
                        result['files'].append(item)

            except Exception as e:
                if lenient:
                    logger.warning(f"Skipped line due to error: {e}")
                    continue
                else:
                    raise

        result['total_found'] = len(result['directories']) + len(result['files'])
        return result
