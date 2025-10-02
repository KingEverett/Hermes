"""Base class for tool output parsers."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ToolOutputParser(ABC):
    """Base class for tool output parsers.

    Parsers convert tool-specific output formats into structured data
    that can be imported into Hermes.
    """

    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the tool this parser handles.

        Returns:
            Tool name (e.g., 'nmap', 'masscan')
        """
        pass

    @abstractmethod
    def can_parse(self, content: str, filename: str) -> bool:
        """Determine if this parser can handle the content.

        Args:
            content: File content (first 1KB or full content)
            filename: Name of the file being parsed

        Returns:
            True if this parser can handle the content
        """
        pass

    @abstractmethod
    def parse(self, content: str, lenient: bool = False) -> Dict[str, Any]:
        """Parse tool output into structured data.

        Args:
            content: Full file content to parse
            lenient: If True, continue on errors; if False, fail fast

        Returns:
            Dictionary with parsed data

        Raises:
            ValueError: If parsing fails in strict mode
        """
        pass

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate parsed data before submission.

        Args:
            data: Parsed data dictionary

        Returns:
            True if data is valid

        Raises:
            ValueError: If data is invalid
        """
        # Default implementation - can be overridden
        required_fields = ['tool', 'version']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        return True
