"""Plugin management for Hermes CLI."""

import logging
from typing import Dict, List
from importlib.metadata import entry_points, version, distributions

logger = logging.getLogger(__name__)


class PluginManager:
    """Manager for loading and discovering plugins."""

    def __init__(self):
        """Initialize the plugin manager."""
        self.loaded_wrappers = {}
        self.loaded_parsers = {}
        self._discover_plugins()

    def _discover_plugins(self):
        """Discover and load plugins via entry points."""
        # Discover wrapper plugins
        self._discover_wrapper_plugins()

        # Discover parser plugins
        self._discover_parser_plugins()

    def _discover_wrapper_plugins(self):
        """Discover wrapper plugins."""
        try:
            eps = entry_points()

            # Handle different entry_points() return types
            if hasattr(eps, 'select'):
                # Python 3.10+
                wrapper_eps = eps.select(group='hermes_cli.wrappers')
            else:
                # Python 3.9 and earlier
                wrapper_eps = eps.get('hermes_cli.wrappers', [])

            for ep in wrapper_eps:
                try:
                    wrapper_class = ep.load()
                    self.loaded_wrappers[ep.name] = wrapper_class
                    logger.info(f"Loaded wrapper plugin: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load wrapper plugin {ep.name}: {e}")

        except Exception as e:
            logger.debug(f"Wrapper plugin discovery failed: {e}")

    def _discover_parser_plugins(self):
        """Discover parser plugins."""
        try:
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
                    self.loaded_parsers[ep.name] = parser_class
                    logger.info(f"Loaded parser plugin: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load parser plugin {ep.name}: {e}")

        except Exception as e:
            logger.debug(f"Parser plugin discovery failed: {e}")

    def list_plugins(self) -> List[Dict[str, str]]:
        """List all loaded plugins.

        Returns:
            List of plugin info dictionaries
        """
        plugins = []

        # Add wrapper plugins
        for name, wrapper_class in self.loaded_wrappers.items():
            plugins.append({
                'name': name,
                'type': 'wrapper',
                'class': wrapper_class.__name__
            })

        # Add parser plugins
        for name, parser_class in self.loaded_parsers.items():
            plugins.append({
                'name': name,
                'type': 'parser',
                'class': parser_class.__name__
            })

        return plugins

    @staticmethod
    def list_distributions() -> List[Dict[str, str]]:
        """List all installed distributions that provide Hermes plugins.

        Returns:
            List of distribution info dictionaries
        """
        plugin_dists = []

        try:
            for dist in distributions():
                # Check if distribution has hermes_cli entry points
                eps = dist.entry_points
                has_wrapper = any(ep.group == 'hermes_cli.wrappers' for ep in eps)
                has_parser = any(ep.group == 'hermes_cli.parsers' for ep in eps)

                if has_wrapper or has_parser:
                    plugin_dists.append({
                        'name': dist.name,
                        'version': dist.version,
                        'has_wrapper': has_wrapper,
                        'has_parser': has_parser
                    })
        except Exception as e:
            logger.error(f"Failed to list distributions: {e}")

        return plugin_dists


# Global plugin manager instance
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """Get or create the global plugin manager.

    Returns:
        Global PluginManager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
