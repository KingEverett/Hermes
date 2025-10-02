"""Registry for managing tool output parsers."""

from typing import Dict, List, Optional
import logging
from .base import ToolOutputParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing and discovering tool output parsers."""

    def __init__(self):
        """Initialize the parser registry."""
        self.parsers: List[ToolOutputParser] = []
        self._parser_map: Dict[str, ToolOutputParser] = {}
        self._discover_parsers()

    def register_parser(self, parser: ToolOutputParser):
        """Register a parser manually.

        Args:
            parser: ToolOutputParser instance
        """
        tool_name = parser.get_tool_name()
        self.parsers.append(parser)
        self._parser_map[tool_name] = parser
        logger.debug(f"Registered parser for {tool_name}")

    def get_parser(self, content: str, filename: str) -> Optional[ToolOutputParser]:
        """Find suitable parser for content.

        Tries each registered parser's can_parse() method to find a match.

        Args:
            content: File content (or first chunk)
            filename: Filename being parsed

        Returns:
            ToolOutputParser instance or None if no match
        """
        for parser in self.parsers:
            try:
                if parser.can_parse(content, filename):
                    logger.debug(f"Matched parser: {parser.get_tool_name()}")
                    return parser
            except Exception as e:
                logger.warning(f"Error in parser {parser.get_tool_name()}.can_parse(): {e}")
                continue

        logger.warning(f"No parser found for file: {filename}")
        return None

    def get_parser_by_tool(self, tool_name: str) -> Optional[ToolOutputParser]:
        """Get parser by tool name.

        Args:
            tool_name: Name of the tool (e.g., 'nmap')

        Returns:
            ToolOutputParser instance or None
        """
        return self._parser_map.get(tool_name)

    def list_parsers(self) -> List[Dict[str, str]]:
        """List all registered parsers.

        Returns:
            List of parser info dictionaries
        """
        return [
            {
                'tool': parser.get_tool_name(),
                'class': parser.__class__.__name__
            }
            for parser in self.parsers
        ]

    def _discover_parsers(self):
        """Auto-discover built-in and plugin parsers."""
        # Import built-in parsers
        self._discover_builtin_parsers()

        # Discover plugin parsers via entry points
        self._discover_plugin_parsers()

    def _discover_builtin_parsers(self):
        """Discover built-in parsers."""
        # Try to import each built-in parser
        # Use lazy imports to avoid import errors if a parser isn't available

        try:
            from .nmap import NmapParser
            self.register_parser(NmapParser())
        except ImportError as e:
            logger.debug(f"NmapParser not available: {e}")

        try:
            from .masscan import MasscanParser
            self.register_parser(MasscanParser())
        except ImportError as e:
            logger.debug(f"MasscanParser not available: {e}")

        try:
            from .dirb import DirbParser
            self.register_parser(DirbParser())
        except ImportError as e:
            logger.debug(f"DirbParser not available: {e}")

        try:
            from .gobuster import GobusterParser
            self.register_parser(GobusterParser())
        except ImportError as e:
            logger.debug(f"GobusterParser not available: {e}")

    def _discover_plugin_parsers(self):
        """Discover plugin parsers via entry points."""
        try:
            from importlib.metadata import entry_points
        except ImportError:
            # Python < 3.8
            from importlib_metadata import entry_points

        try:
            # Get entry points for hermes_cli.parsers
            eps = entry_points()

            # Handle different entry_points() return types
            if hasattr(eps, 'select'):
                # Python 3.10+
                parser_eps = eps.select(group='hermes_cli.parsers')
            else:
                # Python 3.9 and earlier
                parser_eps = eps.get('hermes_cli.parsers', [])

            for ep in parser_eps:
                try:
                    parser_class = ep.load()
                    parser_instance = parser_class()
                    self.register_parser(parser_instance)
                    logger.info(f"Loaded plugin parser: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin parser {ep.name}: {e}")

        except Exception as e:
            logger.debug(f"Plugin discovery failed: {e}")


# Global registry instance
_registry = None


def get_parser_registry() -> ParserRegistry:
    """Get or create the global parser registry.

    Returns:
        Global ParserRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ParserRegistry()
    return _registry
