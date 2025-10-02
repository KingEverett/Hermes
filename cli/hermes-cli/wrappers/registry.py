"""Registry for managing tool wrappers."""

from typing import Dict, Optional
from .base import ToolWrapper


class WrapperRegistry:
    """Registry for managing and discovering tool wrappers."""

    def __init__(self):
        """Initialize the wrapper registry."""
        self._wrappers: Dict[str, type] = {}
        self._discover_wrappers()

    def register_wrapper(self, tool_name: str, wrapper_class: type):
        """Register a wrapper manually.

        Args:
            tool_name: Name of the tool (e.g., 'nmap')
            wrapper_class: ToolWrapper subclass
        """
        self._wrappers[tool_name] = wrapper_class

    def get_wrapper_class(self, tool_name: str) -> Optional[type]:
        """Get wrapper class for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolWrapper subclass or None if not found
        """
        return self._wrappers.get(tool_name)

    def list_wrappers(self) -> list:
        """List all registered wrappers.

        Returns:
            List of tool names
        """
        return list(self._wrappers.keys())

    def _discover_wrappers(self):
        """Auto-discover built-in wrappers."""
        # Import built-in wrappers lazily to avoid circular imports
        try:
            from .nmap import NmapWrapper
            self.register_wrapper('nmap', NmapWrapper)
        except ImportError:
            pass

        try:
            from .masscan import MasscanWrapper
            self.register_wrapper('masscan', MasscanWrapper)
        except ImportError:
            pass

        try:
            from .web_enum import DirbWrapper, GobusterWrapper
            self.register_wrapper('dirb', DirbWrapper)
            self.register_wrapper('gobuster', GobusterWrapper)
        except ImportError:
            pass


# Global registry instance
_registry = None


def get_wrapper_registry() -> WrapperRegistry:
    """Get or create the global wrapper registry.

    Returns:
        Global WrapperRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = WrapperRegistry()
    return _registry
