from typing import List, Type
import logging

from .base import ScanParser, UnsupportedScanError
from .nmap_parser import NmapXMLParser

logger = logging.getLogger(__name__)


class ScanParserFactory:
    """Factory class for selecting appropriate scan parsers"""

    def __init__(self):
        # Register available parsers
        self._parsers: List[ScanParser] = [
            NmapXMLParser(),
            # Future parsers can be added here:
            # MasscanJSONParser(),
            # DirbParser(),
            # GobusterParser()
        ]

    def get_parser(self, content: str, filename: str) -> ScanParser:
        """
        Get the appropriate parser for the given file content and filename.

        Args:
            content: The file content as string
            filename: The original filename

        Returns:
            ScanParser instance that can handle the file

        Raises:
            UnsupportedScanError: If no suitable parser is found
        """
        # Validate inputs
        if not content or not content.strip():
            raise UnsupportedScanError("File content is empty")

        if not filename:
            raise UnsupportedScanError("Filename is required for parser selection")

        # Try each parser to see if it can handle the file
        for parser in self._parsers:
            try:
                if parser.can_parse(content, filename):
                    return parser
            except Exception as e:
                # Log parser evaluation error but continue trying other parsers
                logger.warning(f"Parser {parser.__class__.__name__} failed evaluation: {e}", exc_info=True)
                continue

        # No suitable parser found
        supported_formats = self._get_supported_formats()
        raise UnsupportedScanError(
            f"No suitable parser found for file '{filename}'. "
            f"Supported formats: {', '.join(supported_formats)}"
        )

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.

        Returns:
            List of supported format descriptions
        """
        return self._get_supported_formats()

    def _get_supported_formats(self) -> List[str]:
        """Internal method to get supported format descriptions"""
        formats = []

        # Add descriptions for each parser type
        for parser in self._parsers:
            parser_type = parser.__class__.__name__
            if 'Nmap' in parser_type:
                formats.append('Nmap XML (.xml)')
            elif 'Masscan' in parser_type:
                formats.append('Masscan JSON (.json)')
            elif 'Dirb' in parser_type:
                formats.append('Dirb text output')
            elif 'Gobuster' in parser_type:
                formats.append('Gobuster text output')
            else:
                formats.append(f'{parser_type} format')

        return formats

    def register_parser(self, parser: ScanParser) -> None:
        """
        Register a new parser with the factory.

        Args:
            parser: ScanParser instance to register
        """
        if not isinstance(parser, ScanParser):
            raise ValueError("Parser must be an instance of ScanParser")

        self._parsers.append(parser)

    def get_parser_count(self) -> int:
        """Get the number of registered parsers"""
        return len(self._parsers)

    def validate_parser_configuration(self) -> bool:
        """
        Validate that all registered parsers are properly configured.

        Returns:
            True if all parsers are valid, False otherwise
        """
        if not self._parsers:
            return False

        try:
            # Test each parser with dummy data to ensure they're functional
            test_content = "test"
            test_filename = "test.xml"

            for parser in self._parsers:
                # Just test that can_parse method works without exceptions
                parser.can_parse(test_content, test_filename)

            return True
        except Exception:
            return False