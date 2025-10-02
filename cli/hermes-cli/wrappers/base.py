"""Base class for security tool wrappers."""

import subprocess
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
import click


class ToolWrapper(ABC):
    """Base class for security tool wrappers.

    Provides common functionality for executing tools, capturing output,
    and auto-importing results into Hermes.
    """

    def __init__(self, project_id: str, api_client):
        """Initialize the tool wrapper.

        Args:
            project_id: The project to import scan results into
            api_client: HermesAPIClient instance for API communication
        """
        self.project_id = project_id
        self.api_client = api_client
        self.output_dir = Path.home() / '.hermes' / 'scans'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the tool binary name.

        Returns:
            The name of the tool executable
        """
        pass

    @abstractmethod
    def prepare_arguments(self, args: List[str]) -> Tuple[List[str], Path]:
        """Prepare tool arguments and determine output file path.

        This method should modify the arguments as needed to capture tool
        output in a format that can be imported into Hermes.

        Args:
            args: Original command-line arguments

        Returns:
            Tuple of (modified_args, output_file_path)
        """
        pass

    def get_tool_path(self) -> Optional[str]:
        """Find tool in PATH using shutil.which().

        Returns:
            Full path to tool executable, or None if not found
        """
        return shutil.which(self.get_tool_name())

    def execute_tool(
        self,
        args: List[str],
        auto_import: bool = True,
        dry_run: bool = False
    ) -> dict:
        """Execute the tool and optionally auto-import results.

        Args:
            args: Command-line arguments for the tool
            auto_import: Whether to automatically import results after execution
            dry_run: If True, show command without executing

        Returns:
            Dictionary with execution results and import status

        Raises:
            FileNotFoundError: If tool is not found in PATH
            subprocess.CalledProcessError: If tool execution fails
        """
        # Check tool exists
        tool_path = self.get_tool_path()
        if not tool_path:
            raise FileNotFoundError(
                f"{self.get_tool_name()} not found in PATH. "
                f"Please install {self.get_tool_name()} and ensure it's available."
            )

        # Prepare arguments and output file
        modified_args, output_file = self.prepare_arguments(args)

        # Build command
        cmd = [tool_path] + modified_args

        # Dry run mode - show command without executing
        if dry_run:
            click.echo(f"Would execute: {' '.join(cmd)}")
            click.echo(f"Output file: {output_file}")
            return {
                'status': 'dry_run',
                'command': ' '.join(cmd),
                'output_file': str(output_file)
            }

        # Execute tool with real-time output passthrough
        click.echo(f"Executing: {self.get_tool_name()} {' '.join(args)}")
        click.echo(f"Output will be saved to: {output_file}")
        click.echo("-" * 80)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output to terminal in real-time
            for line in process.stdout:
                click.echo(line, nl=False)

            returncode = process.wait()

            click.echo("-" * 80)

            # Handle exit codes
            if returncode != 0:
                click.echo(
                    f"⚠️  {self.get_tool_name()} exited with code {returncode}",
                    err=True
                )

            # Auto-import if successful and requested
            if returncode == 0 and auto_import and output_file.exists():
                click.echo(f"\n📥 Importing results into project '{self.project_id}'...")
                import_result = self.import_results(output_file)
                import_result['returncode'] = returncode
                import_result['output_file'] = str(output_file)
                return import_result

            return {
                'status': 'tool_executed',
                'returncode': returncode,
                'output_file': str(output_file)
            }

        except KeyboardInterrupt:
            click.echo("\n\n⚠️  Scan interrupted by user", err=True)
            if process:
                process.terminate()
                process.wait()
            raise
        except Exception as e:
            click.echo(f"\n❌ Error executing {self.get_tool_name()}: {e}", err=True)
            raise

    def import_results(self, file_path: Path) -> dict:
        """Import tool results using API client.

        Args:
            file_path: Path to the scan output file

        Returns:
            Dictionary with import results from API
        """
        try:
            result = self.api_client.import_scan(
                project_id=self.project_id,
                file_path=str(file_path),
                format='auto'
            )

            click.echo(f"✓ Imported successfully!")
            click.echo(f"  Scan ID: {result.get('scan_id', 'N/A')}")
            click.echo(f"  Hosts: {result.get('host_count', 0)}")
            click.echo(f"  Services: {result.get('service_count', 0)}")

            return result

        except Exception as e:
            click.echo(f"❌ Failed to import results: {e}", err=True)
            raise

    def capture_output(self) -> Path:
        """Generate a unique output file path for this scan.

        Returns:
            Path to output file with timestamp
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"{self.project_id}-{timestamp}-{self.get_tool_name()}"
        return self.output_dir / filename
