"""Web enumeration tool wrappers (dirb, gobuster) for Hermes."""

from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from .base import ToolWrapper


class DirbWrapper(ToolWrapper):
    """Wrapper for dirb with automatic output capture."""

    def __init__(self, project_id: str, api_client, target_host: Optional[str] = None):
        """Initialize the dirb wrapper.

        Args:
            project_id: The project to import scan results into
            api_client: HermesAPIClient instance
            target_host: Optional host ID to correlate discoveries with
        """
        super().__init__(project_id, api_client)
        self.target_host = target_host

    def get_tool_name(self) -> str:
        """Return the tool binary name."""
        return 'dirb'

    def prepare_arguments(self, args: List[str]) -> Tuple[List[str], Path]:
        """Prepare dirb arguments and add output file.

        Args:
            args: Original dirb command-line arguments

        Returns:
            Tuple of (modified_args, output_file_path)
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = self.output_dir / f"{self.project_id}-{timestamp}-dirb.txt"

        # Make a copy to avoid modifying the original
        modified_args = args.copy()

        # Check if user already specified output file
        if '-o' in modified_args:
            # Extract user-specified output file
            idx = modified_args.index('-o')
            if idx + 1 < len(modified_args):
                user_output = Path(modified_args[idx + 1])
                if not user_output.is_absolute():
                    user_output = Path.cwd() / user_output
                output_file = user_output
        else:
            # Add output file
            modified_args.extend(['-o', str(output_file)])

        return modified_args, output_file


class GobusterWrapper(ToolWrapper):
    """Wrapper for gobuster with automatic output capture."""

    def __init__(self, project_id: str, api_client, target_host: Optional[str] = None):
        """Initialize the gobuster wrapper.

        Args:
            project_id: The project to import scan results into
            api_client: HermesAPIClient instance
            target_host: Optional host ID to correlate discoveries with
        """
        super().__init__(project_id, api_client)
        self.target_host = target_host

    def get_tool_name(self) -> str:
        """Return the tool binary name."""
        return 'gobuster'

    def prepare_arguments(self, args: List[str]) -> Tuple[List[str], Path]:
        """Prepare gobuster arguments and add output file.

        Args:
            args: Original gobuster command-line arguments

        Returns:
            Tuple of (modified_args, output_file_path)
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = self.output_dir / f"{self.project_id}-{timestamp}-gobuster.txt"

        # Make a copy to avoid modifying the original
        modified_args = args.copy()

        # Check if user already specified output file
        if '-o' in modified_args:
            # Extract user-specified output file
            idx = modified_args.index('-o')
            if idx + 1 < len(modified_args):
                user_output = Path(modified_args[idx + 1])
                if not user_output.is_absolute():
                    user_output = Path.cwd() / user_output
                output_file = user_output
        elif '--output' in modified_args:
            # Long form
            idx = modified_args.index('--output')
            if idx + 1 < len(modified_args):
                user_output = Path(modified_args[idx + 1])
                if not user_output.is_absolute():
                    user_output = Path.cwd() / user_output
                output_file = user_output
        else:
            # Add output file
            modified_args.extend(['-o', str(output_file)])

        return modified_args, output_file
