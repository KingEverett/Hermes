"""Masscan tool wrapper for Hermes."""

from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from .base import ToolWrapper


class MasscanWrapper(ToolWrapper):
    """Wrapper for masscan with automatic JSON output and batch processing."""

    def __init__(self, project_id: str, api_client, batch_size: int = 1000):
        """Initialize the masscan wrapper.

        Args:
            project_id: The project to import scan results into
            api_client: HermesAPIClient instance
            batch_size: Number of results to process in each batch
        """
        super().__init__(project_id, api_client)
        self.batch_size = batch_size

    def get_tool_name(self) -> str:
        """Return the tool binary name."""
        return 'masscan'

    def prepare_arguments(self, args: List[str]) -> Tuple[List[str], Path]:
        """Prepare masscan arguments and add JSON output flag.

        If the user hasn't specified JSON output (-oJ), this method
        will automatically add it to ensure we can import the results.

        Args:
            args: Original masscan command-line arguments

        Returns:
            Tuple of (modified_args, output_file_path)
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = self.output_dir / f"{self.project_id}-{timestamp}-masscan.json"

        # Make a copy to avoid modifying the original
        modified_args = args.copy()

        # Check if user already specified JSON output
        if '-oJ' in modified_args:
            # Extract user-specified output file
            idx = modified_args.index('-oJ')
            if idx + 1 < len(modified_args):
                user_output = Path(modified_args[idx + 1])
                # Use absolute path
                if not user_output.is_absolute():
                    user_output = Path.cwd() / user_output
                output_file = user_output
            # Keep user's arguments as-is
        else:
            # No JSON output specified - add it
            modified_args.extend(['-oJ', str(output_file)])

        return modified_args, output_file
