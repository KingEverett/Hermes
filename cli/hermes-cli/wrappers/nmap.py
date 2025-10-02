"""Nmap tool wrapper for Hermes."""

from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from .base import ToolWrapper


class NmapWrapper(ToolWrapper):
    """Wrapper for nmap with automatic XML output generation and import."""

    def get_tool_name(self) -> str:
        """Return the tool binary name."""
        return 'nmap'

    def prepare_arguments(self, args: List[str]) -> Tuple[List[str], Path]:
        """Prepare nmap arguments and add XML output flag.

        If the user hasn't specified XML output (-oX or -oA), this method
        will automatically add -oX to ensure we can import the results.
        If the user has specified XML output, we'll use their filename.

        Args:
            args: Original nmap command-line arguments

        Returns:
            Tuple of (modified_args, output_file_path)
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = self.output_dir / f"{self.project_id}-{timestamp}-nmap.xml"

        # Make a copy to avoid modifying the original
        modified_args = args.copy()

        # Check if user already specified XML output
        if '-oX' in modified_args:
            # Extract user-specified output file
            idx = modified_args.index('-oX')
            if idx + 1 < len(modified_args):
                user_output = Path(modified_args[idx + 1])
                # Use absolute path
                if not user_output.is_absolute():
                    user_output = Path.cwd() / user_output
                output_file = user_output
            # Keep user's arguments as-is
        elif '-oA' in modified_args:
            # User specified -oA (all formats)
            # Extract base filename and construct .xml path
            idx = modified_args.index('-oA')
            if idx + 1 < len(modified_args):
                base_name = Path(modified_args[idx + 1])
                if not base_name.is_absolute():
                    base_name = Path.cwd() / base_name
                output_file = base_name.with_suffix('.xml')
            # Keep user's arguments as-is
        else:
            # No XML output specified - add it
            modified_args.extend(['-oX', str(output_file)])

        return modified_args, output_file
