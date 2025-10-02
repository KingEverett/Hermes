#!/usr/bin/env python3

import click
import requests
import os
import sys
import json
import functools
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from pathlib import Path
from api_client import HermesAPIClient, HermesAPIError, HermesConnectionError
import time
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from monitor_state import MonitorStateManager
from monitor_config import MonitorConfig, MonitorConfigFile
from monitor_daemon import MonitorDaemon

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CONFIG_DIR = Path.home() / '.hermes'
CONFIG_FILE = CONFIG_DIR / 'config.json'


def load_config() -> dict:
    """Load configuration from file"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: dict):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_api_base_url() -> str:
    """Get API base URL from environment, config, or default"""
    url = os.getenv("API_BASE_URL")
    if url:
        return url
    config = load_config()
    return config.get('api_base_url', 'http://localhost:8000')


def get_api_client() -> HermesAPIClient:
    """Create an API client instance"""
    config = load_config()
    base_url = get_api_base_url()
    timeout = config.get('timeout', 30)
    api_key = config.get('api_key')
    return HermesAPIClient(base_url, timeout, api_key)


def handle_api_error(func):
    """Decorator for consistent error handling across CLI commands with Unix exit codes"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HermesConnectionError as e:
            click.echo(f"❌ Connection error: {str(e)}", err=True)
            click.echo("   Please ensure the backend service is running: docker-compose up backend", err=True)
            sys.exit(3)  # Connection error
        except FileNotFoundError as e:
            click.echo(f"❌ File not found: {str(e)}", err=True)
            sys.exit(5)  # Not found
        except HermesAPIError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                click.echo(f"❌ {error_msg}", err=True)
                sys.exit(5)  # Not found
            else:
                click.echo(f"❌ API error: {error_msg}", err=True)
                sys.exit(1)  # General error
        except click.UsageError as e:
            click.echo(f"❌ Usage error: {str(e)}", err=True)
            sys.exit(2)  # Usage error
        except requests.exceptions.ConnectionError:
            click.echo(f"❌ Cannot connect to backend at {get_api_base_url()}", err=True)
            click.echo("   Please ensure the backend service is running: docker-compose up backend", err=True)
            sys.exit(3)  # Connection error
        except requests.exceptions.Timeout:
            click.echo("❌ Request timed out. The backend might be overloaded.", err=True)
            sys.exit(6)  # Timeout error
        except requests.exceptions.RequestException as e:
            click.echo(f"❌ Network error: {str(e)}", err=True)
            sys.exit(1)  # General error
        except json.JSONDecodeError:
            click.echo("❌ Invalid response from backend. Expected JSON format.", err=True)
            sys.exit(1)  # General error
        except Exception as e:
            click.echo(f"❌ Unexpected error: {str(e)}", err=True)
            click.echo("   Run with --debug for more details", err=True)
            if os.getenv("DEBUG"):
                import traceback
                traceback.print_exc()
            sys.exit(1)  # General error
    return wrapper

@click.group()
@click.version_option(version='1.0.0')
@click.option('--debug/--no-debug', default=False, envvar='DEBUG', help='Enable debug output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, debug, quiet, verbose):
    """
    Hermes - Intelligent Pentesting Documentation Tool

    \b
    A comprehensive CLI for automated security documentation, scan import,
    and report generation integrated into your pentesting workflow.
    """
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    ctx.obj['QUIET'] = quiet
    ctx.obj['VERBOSE'] = verbose

    if debug:
        os.environ['DEBUG'] = 'true'

@cli.command()
@handle_api_error
def health():
    """Check the health status of the Hermes backend"""
    response = requests.get(f"{API_BASE_URL}/health", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"✅ Backend is healthy - Status: {data['status']}, Version: {data['version']}")
        return 0
    else:
        raise HermesAPIError(f"Health check failed with status code: {response.status_code}")

@cli.command()
@click.option('--project', '-p', help='Show project-specific status')
@click.option('--watch', '-w', is_flag=True, help='Continuously monitor status (refresh every 5s)')
@click.pass_context
@handle_api_error
def status(ctx, project, watch):
    """
    Show the status of Hermes services and processing jobs

    \b
    Examples:
      hermes status
      hermes status --project my-pentest
      hermes status --watch
    """
    def display_status():
        quiet = ctx.obj.get('QUIET', False) if ctx.obj else False

        if not quiet:
            click.echo("Checking Hermes services...")

        services_status = []

        # Check backend
        try:
            response = requests.get(f"{get_api_base_url()}/health", timeout=5)
            if response.status_code == 200:
                services_status.append(("Backend API", "✅ Running", "8000"))
            else:
                services_status.append(("Backend API", "⚠️ Unhealthy", "8000"))
        except requests.exceptions.ConnectionError:
            services_status.append(("Backend API", "❌ Not accessible", "8000"))

        # Check frontend (basic connectivity)
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            services_status.append(("Frontend", "✅ Running", "3000"))
        except:
            services_status.append(("Frontend", "❌ Not accessible", "3000"))

        # Get system status from backend
        try:
            client = get_api_client()
            system_status = client.get_system_status()

            # Update services based on system status
            if system_status.get('database_status'):
                services_status.append(("PostgreSQL", "✅ Connected", "5432"))
            else:
                services_status.append(("PostgreSQL", "❌ Not accessible", "5432"))

            if system_status.get('redis_status'):
                services_status.append(("Redis Cache", "✅ Connected", "6379"))
            else:
                services_status.append(("Redis Cache", "❌ Not accessible", "6379"))

        except:
            services_status.append(("PostgreSQL", "ℹ️ Check via backend", "5432"))
            services_status.append(("Redis Cache", "ℹ️ Check via backend", "6379"))
            system_status = {}

        # Display service table
        click.echo("\n" + "="*60)
        click.echo(f"{'Service':<20} {'Status':<25} {'Port':<10}")
        click.echo("="*60)
        for service, stat, port in services_status:
            click.echo(f"{service:<20} {stat:<25} {port:<10}")
        click.echo("="*60)

        # Display processing status if available
        if system_status:
            click.echo("\nProcessing Status:")
            click.echo("-" * 60)
            click.echo(f"  {'Active scans:':<30} {system_status.get('active_scans', 0)}")
            click.echo(f"  {'Queued research tasks:':<30} {system_status.get('queued_research_tasks', 0)}")
            click.echo(f"  {'Failed jobs:':<30} {system_status.get('failed_jobs', 0)}")
            click.echo(f"  {'Celery workers:':<30} {system_status.get('celery_workers', 0)}")
            click.echo("-" * 60)

        # Display project-specific status if requested
        if project:
            try:
                client = get_api_client()
                project_status = client.get_project_status(project)
                metadata = project_status.get('metadata', {})

                click.echo(f"\nProject Status: {project_status.get('name', project)}")
                click.echo("-" * 60)
                click.echo(f"  {'Hosts:':<30} {metadata.get('host_count', 0)}")
                click.echo(f"  {'Services:':<30} {metadata.get('service_count', 0)}")
                click.echo(f"  {'Vulnerabilities:':<30} {metadata.get('vulnerability_count', 0)}")
                click.echo("-" * 60)
            except Exception as e:
                click.echo(f"\n⚠️ Could not fetch project status: {e}")

        # Overall status
        if all("✅" in status for _, status, _ in services_status[:2]):
            click.echo("\n✅ All critical services are running")
        else:
            click.echo("\n⚠️ Some services need attention")
            click.echo("   Run 'docker-compose up' to start all services")

    if watch:
        try:
            while True:
                # Clear screen (cross-platform)
                click.clear()
                display_status()
                click.echo(f"\n[Refreshing every 5 seconds... Press Ctrl+C to stop]")
                time.sleep(5)
        except KeyboardInterrupt:
            click.echo("\n\nMonitoring stopped.")
            sys.exit(0)
    else:
        display_status()


@cli.command('import')
@click.argument('file', type=click.Path(exists=True))
@click.option('--project', '-p', required=True, help='Project ID or name')
@click.option('--format', '-f', type=click.Choice(['auto', 'nmap', 'masscan', 'dirb', 'gobuster']),
              default='auto', help='Scan format (default: auto-detect)')
@click.pass_context
@handle_api_error
def import_scan(ctx, file, project, format):
    """
    Import a scan file into Hermes

    \b
    Examples:
      hermes import nmap-scan.xml --project my-pentest
      hermes import scan.xml --project my-pentest --format nmap
    """
    quiet = ctx.obj.get('QUIET', False) if ctx.obj else False

    if not quiet:
        click.echo(f"Importing {file} into project {project}...")

    client = get_api_client()
    result = client.import_scan(project, file, format)

    if not quiet:
        host_count = result.get('host_count', 0)
        service_count = result.get('service_count', 0)
        scan_id = result.get('scan_id', 'unknown')
        filename = os.path.basename(file)

        click.echo(f"✓ Imported {host_count} hosts, {service_count} services from {filename}")
        click.echo(f"  Scan ID: {scan_id}")
        click.echo(f"  Status: {result.get('status', 'unknown')}")

    sys.exit(0)


@cli.command()
@click.option('--project', '-p', required=True, help='Project ID or name')
@click.option('--format', '-f', type=click.Choice(['auto', 'json', 'text']),
              default='text', help='Output format')
@click.pass_context
@handle_api_error
def pipe(ctx, project, format):
    """
    Process scan data from stdin (for pipeline integration)

    \b
    Examples:
      nmap -oX - 192.168.1.0/24 | hermes pipe --project pentest-2025
      cat scan.xml | hermes pipe --project my-test --format auto
    """
    quiet = ctx.obj.get('QUIET', False) if ctx.obj else False

    # Read from stdin
    if sys.stdin.isatty():
        click.echo("❌ No input data. Please pipe scan data to this command.", err=True)
        click.echo("   Example: nmap -oX - target | hermes pipe --project my-project", err=True)
        sys.exit(2)

    content = sys.stdin.read()

    if not content.strip():
        click.echo("❌ Empty input received from stdin", err=True)
        sys.exit(2)

    # Don't show processing message when outputting JSON
    if not quiet and format != 'json':
        click.echo(f"Processing piped data for project {project}...")

    client = get_api_client()

    # Auto-detect format from content
    scan_format = 'auto'
    if format == 'auto':
        if content.strip().startswith('<?xml'):
            scan_format = 'nmap'
        elif content.strip().startswith('{'):
            scan_format = 'masscan'

    result = client.import_scan_from_stdin(project, content, scan_format)

    if format == 'json':
        click.echo(json.dumps(result, indent=2))
    else:
        host_count = result.get('host_count', 0)
        service_count = result.get('service_count', 0)
        scan_id = result.get('scan_id', 'unknown')

        if not quiet:
            click.echo(f"✓ Imported {host_count} hosts, {service_count} services")
            click.echo(f"  Scan ID: {scan_id}")
            click.echo(f"  Status: {result.get('status', 'unknown')}")

    sys.exit(0)


@cli.command()
@click.argument('project_id')
@click.option('--format', '-f', type=click.Choice(['markdown', 'pdf', 'json', 'csv']),
              default='markdown', help='Export format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--no-graph', is_flag=True, help='Exclude network graph from export')
@click.option('--no-chains', is_flag=True, help='Exclude attack chains from export')
@click.pass_context
@handle_api_error
def export(ctx, project_id, format, output, no_graph, no_chains):
    """
    Export project documentation

    \b
    Examples:
      hermes export my-project
      hermes export my-project --format pdf --output report.pdf
      hermes export my-project --format markdown --no-graph
    """
    quiet = ctx.obj.get('QUIET', False) if ctx.obj else False

    if not quiet:
        click.echo(f"Exporting project {project_id} as {format}...")

    client = get_api_client()

    # Start export job
    result = client.export_project(
        project_id,
        format=format,
        include_graph=not no_graph,
        include_attack_chains=not no_chains
    )

    job_id = result.get('job_id')
    if not job_id:
        click.echo("❌ Failed to start export job", err=True)
        sys.exit(1)

    # Poll for completion
    if not quiet:
        click.echo(f"  Export job started: {job_id}")
        click.echo("  Waiting for export to complete...")

    max_attempts = 60  # 5 minutes with 5-second intervals
    attempt = 0

    while attempt < max_attempts:
        time.sleep(5)
        status = client.get_export_job_status(job_id)
        job_status = status.get('status')

        if job_status == 'completed':
            break
        elif job_status == 'failed':
            error = status.get('error', 'Unknown error')
            click.echo(f"❌ Export failed: {error}", err=True)
            sys.exit(1)

        attempt += 1
        if not quiet and attempt % 6 == 0:  # Progress update every 30 seconds
            click.echo(f"  Still processing... ({attempt * 5}s elapsed)")

    if attempt >= max_attempts:
        click.echo("❌ Export timed out after 5 minutes", err=True)
        sys.exit(6)

    # Determine output path
    if not output:
        ext_map = {'markdown': 'md', 'pdf': 'pdf', 'json': 'json', 'csv': 'csv'}
        output = f"{project_id}-report.{ext_map[format]}"

    # Download export file
    client.download_export(job_id, output)

    if not quiet:
        file_size = os.path.getsize(output) / 1024  # KB
        click.echo(f"✓ Exported to {output} ({file_size:.1f}KB)")

    sys.exit(0)


class ScanFileHandler(FileSystemEventHandler):
    """Handler for scan file creation events"""

    def __init__(self, project_id: str, api_client: HermesAPIClient,
                 patterns: list, exclude_patterns: list, delay: int,
                 state_manager: MonitorStateManager, force_reprocess: bool = False,
                 verbose: bool = False, quiet: bool = False, max_workers: int = 3):
        self.project_id = project_id
        self.api_client = api_client
        self.patterns = patterns
        self.exclude_patterns = exclude_patterns
        self.delay = delay
        self.state_manager = state_manager
        self.force_reprocess = force_reprocess
        self.verbose = verbose
        self.quiet = quiet
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending_timers = {}  # file_path -> Timer
        self.active_futures = []  # List of active Future objects
        self.observer = None

    def set_observer(self, observer):
        """Set the observer instance for shutdown handling"""
        self.observer = observer

    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            file_path = event.src_path
            if self._should_process(file_path):
                if self.verbose:
                    click.echo(f"📁 New scan file detected: {os.path.basename(file_path)}")

                # Schedule delayed processing using timer, then submit to executor
                timer = threading.Timer(self.delay, self._submit_for_processing, args=[file_path])
                self.pending_timers[file_path] = timer
                timer.start()
            elif self.verbose:
                click.echo(f"⏭️  Skipped {os.path.basename(file_path)}: Does not match patterns or is excluded")

    def _submit_for_processing(self, file_path: str):
        """Submit file to thread pool for processing"""
        # Remove from pending timers
        if file_path in self.pending_timers:
            del self.pending_timers[file_path]

        # Submit to executor
        future = self.executor.submit(self._process_file, file_path)
        self.active_futures.append(future)

        # Clean up completed futures
        self.active_futures = [f for f in self.active_futures if not f.done()]

    def _should_process(self, file_path: str) -> bool:
        """Check if file should be processed based on patterns and exclusions"""
        import fnmatch
        filename = os.path.basename(file_path)

        # Check exclusion patterns first
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return False

        # Check inclusion patterns
        return any(fnmatch.fnmatch(filename, pattern) for pattern in self.patterns)

    def _process_file(self, file_path: str):
        """Process a scan file"""
        try:
            # Check for duplicates
            if not self.force_reprocess and self.state_manager.is_duplicate(file_path):
                if not self.quiet:
                    click.echo(f"⏭️  Skipped {os.path.basename(file_path)}: Already processed (identical content)")
                return

            if not self.quiet:
                click.echo(f"⚙️  Processing {os.path.basename(file_path)}...")

            # Import using API client
            result = self.api_client.import_scan(
                project_id=self.project_id,
                file_path=file_path,
                format='auto'
            )

            host_count = result.get('host_count', 0)
            service_count = result.get('service_count', 0)
            scan_id = result.get('scan_id', 'unknown')

            # Mark as processed
            self.state_manager.mark_processed(file_path, scan_id, host_count, service_count)

            if not self.quiet:
                click.echo(f"✓ Imported {host_count} hosts, {service_count} services from {os.path.basename(file_path)}")

        except FileNotFoundError:
            click.echo(f"⚠ File deleted before processing: {os.path.basename(file_path)}", err=True)
            self.state_manager.mark_error(file_path, "File not found")
        except Exception as e:
            click.echo(f"❌ Failed to process {os.path.basename(file_path)}: {str(e)}", err=True)
            self.state_manager.mark_error(file_path, str(e))

    def shutdown(self, timeout: int = 30):
        """Gracefully shutdown the handler and wait for pending work"""
        # Cancel pending timers
        for timer in self.pending_timers.values():
            timer.cancel()
        self.pending_timers.clear()

        # Wait for active futures to complete
        if self.active_futures:
            if not self.quiet:
                click.echo(f"Waiting for {len(self.active_futures)} active tasks to complete...")

        # Shutdown executor (wait=True blocks until completion)
        self.executor.shutdown(wait=True)

    def get_active_count(self) -> int:
        """Get count of active processing tasks"""
        self.active_futures = [f for f in self.active_futures if not f.done()]
        return len(self.active_futures)


def run_multi_monitor(config_path: str):
    """Run multiple monitors from config file"""
    # Load config
    config_file = MonitorConfigFile(config_path)
    monitors = config_file.load()

    if not monitors:
        click.echo("No monitors configured in config file", err=True)
        sys.exit(1)

    click.echo(f"Starting {len(monitors)} monitor(s)...")

    # Get API client
    client = get_api_client()

    # Create observers and handlers for each monitor
    observers = []
    handlers = []

    for monitor_config in monitors:
        # Initialize state manager for this monitor
        state_manager = MonitorStateManager()

        # Create handler
        handler = ScanFileHandler(
            project_id=monitor_config.project,
            api_client=client,
            patterns=monitor_config.patterns,
            exclude_patterns=monitor_config.exclude,
            delay=monitor_config.delay,
            state_manager=state_manager,
            force_reprocess=False,
            verbose=False,
            quiet=True,
            max_workers=monitor_config.max_concurrent
        )

        # Create observer
        observer = Observer()
        handler.set_observer(observer)
        observer.schedule(handler, path=monitor_config.directory, recursive=monitor_config.recursive)

        observers.append(observer)
        handlers.append(handler)

        click.echo(f"  ✓ {monitor_config.directory} → {monitor_config.project}")

    # Signal handling for graceful shutdown
    def signal_handler(signum, frame):
        click.echo("\n\nShutting down monitors...")
        for observer in observers:
            observer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start all observers
    for observer in observers:
        observer.start()

    click.echo("All monitors started. Daemon running...")

    try:
        # Keep running
        while all(obs.is_alive() for obs in observers):
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n\nShutting down monitors...")
    finally:
        # Stop all observers
        for observer in observers:
            observer.stop()
            observer.join()

        # Shutdown all handlers
        for handler in handlers:
            handler.shutdown(timeout=30)


@cli.group()
def monitor():
    """Monitor directories for scan files"""
    pass


@monitor.command('start')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to monitor config file')
@handle_api_error
def monitor_start(config):
    """Start monitor daemon with config file"""
    daemon_mgr = MonitorDaemon()

    if daemon_mgr.is_running():
        click.echo(f"Monitor daemon is already running (PID: {daemon_mgr.get_pid()})", err=True)
        sys.exit(1)

    try:
        click.echo("Starting monitor daemon...")
        daemon_mgr.start(config, run_multi_monitor)
        click.echo(f"✓ Monitor daemon started (PID: {daemon_mgr.get_pid()})")
    except Exception as e:
        click.echo(f"Failed to start daemon: {e}", err=True)
        sys.exit(1)


@monitor.command('stop')
def monitor_stop():
    """Stop monitor daemon"""
    daemon_mgr = MonitorDaemon()

    if not daemon_mgr.is_running():
        click.echo("Monitor daemon is not running")
        sys.exit(1)

    try:
        pid = daemon_mgr.get_pid()
        click.echo(f"Stopping monitor daemon (PID: {pid})...")
        if daemon_mgr.stop():
            click.echo("✓ Monitor daemon stopped")
        else:
            click.echo("Failed to stop daemon", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error stopping daemon: {e}", err=True)
        sys.exit(1)


@monitor.command('status')
def monitor_status():
    """Show monitor daemon status"""
    daemon_mgr = MonitorDaemon()
    status = daemon_mgr.get_status()

    if status['running']:
        click.echo(f"Monitor Daemon Status: RUNNING")
        click.echo(f"  PID: {status['pid']}")
        click.echo(f"  Config: {status['config_path']}")
        if status['log_file']:
            click.echo(f"  Log: {status['log_file']}")
    else:
        click.echo("Monitor Daemon Status: STOPPED")


@monitor.command('run')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--project', '-p', required=True, help='Project ID to import scans into')
@click.option('--recursive', '-r', is_flag=True, help='Monitor directory recursively')
@click.option('--patterns', default='*.xml,*.json,*.txt', help='File glob patterns (comma-separated, default: *.xml,*.json,*.txt)')
@click.option('--exclude', default='*.tmp,*.partial,*~,.*.swp', help='Exclusion patterns (comma-separated, default: *.tmp,*.partial,*~,.*.swp)')
@click.option('--delay', default=5, type=int, help='Delay in seconds before processing new files (default: 5)')
@click.option('--max-concurrent', default=3, type=int, help='Maximum concurrent file processing tasks (default: 3)')
@click.option('--force-reprocess', is_flag=True, help='Reprocess files even if already processed')
@click.pass_context
@handle_api_error
def monitor_run(ctx, directory, project, recursive, patterns, exclude, delay, max_concurrent, force_reprocess):
    """
    Monitor a single directory for scan files (foreground mode)

    \b
    Examples:
      hermes monitor run ~/scans --project my-pentest
      hermes monitor run ~/scans --recursive --patterns "*.xml"
      hermes monitor run /data/scans --project pentest --delay 10

    Press Ctrl+C to stop monitoring.
    """
    verbose = ctx.obj.get('VERBOSE', False) if ctx.obj else False
    quiet = ctx.obj.get('QUIET', False) if ctx.obj else False

    # Parse patterns
    pattern_list = [p.strip() for p in patterns.split(',')]
    exclude_list = [p.strip() for p in exclude.split(',')]

    # Get API client
    client = get_api_client()

    # Initialize state manager
    state_manager = MonitorStateManager()

    # Cleanup old entries on start
    removed = state_manager.cleanup_old_entries()
    if removed > 0 and verbose:
        click.echo(f"Cleaned up {removed} old state entries")

    # Create handler
    handler = ScanFileHandler(
        project_id=project,
        api_client=client,
        patterns=pattern_list,
        exclude_patterns=exclude_list,
        delay=delay,
        state_manager=state_manager,
        force_reprocess=force_reprocess,
        verbose=verbose,
        quiet=quiet,
        max_workers=max_concurrent
    )

    # Create observer
    observer = Observer()
    handler.set_observer(observer)
    observer.schedule(handler, path=directory, recursive=recursive)

    # Signal handling for graceful shutdown (skip in testing)
    test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
    if not test_mode:
        def signal_handler(signum, frame):
            click.echo("\n\nShutting down monitor...")
            observer.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    observer.start()

    if not quiet:
        click.echo(click.style(f"✓ Monitoring {directory} for scan files... Press Ctrl+C to stop", fg='green'))
        if verbose:
            click.echo(f"  Project: {project}")
            click.echo(f"  Patterns: {', '.join(pattern_list)}")
            click.echo(f"  Recursive: {recursive}")
            click.echo(f"  Delay: {delay}s")
            click.echo(f"  Max concurrent: {max_concurrent} workers")

    try:
        # Keep running until interrupted
        while observer.is_alive():
            observer.join(timeout=1)
    except KeyboardInterrupt:
        click.echo("\n\nShutting down monitor...")
    finally:
        observer.stop()
        observer.join()

        # Shutdown handler and wait for pending work
        handler.shutdown(timeout=30)

        # Display summary
        if not quiet:
            stats = state_manager.get_stats()
            click.echo("\nMonitor Summary:")
            click.echo(f"  Processed: {stats.get('total_processed', 0)} files")
            click.echo(f"  Errors: {stats.get('total_errors', 0)}")
            click.echo("Monitor stopped.")

    # Only exit in non-test mode
    if not test_mode:
        sys.exit(0)


@cli.group()
def config():
    """Manage Hermes CLI configuration"""
    pass


@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set a configuration value"""
    valid_keys = ['api_base_url', 'default_project', 'scan_directory', 'timeout', 'api_key']

    if key not in valid_keys:
        click.echo(f"❌ Invalid configuration key: {key}", err=True)
        click.echo(f"   Valid keys: {', '.join(valid_keys)}", err=True)
        sys.exit(2)

    # Validate specific keys
    if key == 'api_base_url':
        if not (value.startswith('http://') or value.startswith('https://')):
            click.echo("❌ api_base_url must start with http:// or https://", err=True)
            sys.exit(2)
    elif key == 'timeout':
        try:
            value = int(value)
        except ValueError:
            click.echo("❌ timeout must be an integer", err=True)
            sys.exit(2)

    cfg = load_config()
    cfg[key] = value
    save_config(cfg)

    click.echo(f"✓ Set {key} = {value}")
    sys.exit(0)


@config.command('get')
@click.argument('key')
def config_get(key):
    """Get a configuration value"""
    cfg = load_config()

    if key not in cfg:
        click.echo(f"❌ Configuration key not found: {key}", err=True)
        sys.exit(5)

    value = cfg[key]

    # Mask API key
    if key == 'api_key' and value:
        display_value = value[:8] + '...' if len(value) > 8 else '***'
        click.echo(f"{key} = {display_value}")
    else:
        click.echo(f"{key} = {value}")

    sys.exit(0)


@config.command('list')
def config_list():
    """List all configuration"""
    cfg = load_config()

    if not cfg:
        click.echo("No configuration found. Use 'hermes config set' to add values.")
        sys.exit(0)

    click.echo("Current configuration:")
    click.echo("=" * 50)

    for key, value in cfg.items():
        # Mask API key
        if key == 'api_key' and value:
            display_value = value[:8] + '...' if len(value) > 8 else '***'
        else:
            display_value = value

        click.echo(f"  {key:<20} = {display_value}")

    click.echo("=" * 50)
    sys.exit(0)


@cli.group()
def parsers():
    """Manage and test tool output parsers"""
    pass


@parsers.command('list')
def parsers_list():
    """List all registered parsers"""
    from parsers import get_parser_registry

    registry = get_parser_registry()
    parser_list = registry.list_parsers()

    if not parser_list:
        click.echo("No parsers registered")
        return 0

    click.echo("Registered Parsers:")
    click.echo("-" * 50)
    for parser_info in parser_list:
        click.echo(f"  {parser_info['tool']:15s} {parser_info['class']}")
    click.echo(f"\nTotal: {len(parser_list)} parsers")
    return 0


@parsers.command('test')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--lenient', is_flag=True, help='Use lenient parsing mode')
def parsers_test(file_path, lenient):
    """Test parser detection and parsing on a sample file"""
    from parsers import get_parser_registry
    from pathlib import Path

    registry = get_parser_registry()

    # Read file
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        content = f.read()

    # Try to find parser
    click.echo(f"Testing file: {file_path}")
    click.echo(f"File size: {len(content)} bytes")
    click.echo("-" * 50)

    parser = registry.get_parser(content, file_path.name)

    if parser:
        click.echo(f"✓ Matched parser: {parser.get_tool_name()}")
        click.echo("\nParsing...")
        try:
            result = parser.parse(content, lenient=lenient)
            click.echo(f"✓ Parsing successful!")
            click.echo(f"\nParsed data summary:")
            for key, value in result.items():
                if isinstance(value, (list, dict)):
                    click.echo(f"  {key}: {type(value).__name__} with {len(value)} items")
                else:
                    click.echo(f"  {key}: {value}")
            return 0
        except Exception as e:
            click.echo(f"❌ Parsing failed: {e}", err=True)
            return 1
    else:
        click.echo("❌ No parser matched this file", err=True)
        return 1


@cli.command('validate')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--lenient', is_flag=True, help='Use lenient parsing mode')
def validate_scan(file_path, lenient):
    """
    Validate a scan file without importing it.

    Tests parsing and data validation without submitting to the API.
    Useful for troubleshooting scan file issues.

    \b
    Examples:
      hermes validate nmap-scan.xml
      hermes validate masscan-results.json --lenient
    """
    from parsers import get_parser_registry
    from pathlib import Path

    registry = get_parser_registry()

    # Detect encoding
    file_path = Path(file_path)
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']
        click.echo(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
    except ImportError:
        encoding = 'utf-8'
        click.echo("Note: Install chardet for encoding detection")

    # Read file with detected encoding
    try:
        with open(file_path, 'r', encoding=encoding or 'utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        click.echo(f"❌ Failed to read file: {e}", err=True)
        return 1

    click.echo(f"File: {file_path}")
    click.echo(f"Size: {len(content)} bytes")
    click.echo("-" * 50)

    # Find parser
    parser = registry.get_parser(content, file_path.name)

    if not parser:
        click.echo("❌ No parser found for this file format", err=True)
        return 1

    click.echo(f"✓ Parser: {parser.get_tool_name()}")

    # Parse
    click.echo("\nParsing...")
    try:
        result = parser.parse(content, lenient=lenient)
        click.echo("✓ Parsing successful!")

        # Validate
        click.echo("\nValidating...")
        parser.validate(result)
        click.echo("✓ Validation successful!")

        # Show summary
        click.echo("\nData summary:")
        for key, value in result.items():
            if isinstance(value, (list, dict)):
                click.echo(f"  {key}: {type(value).__name__} with {len(value)} items")
            else:
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                click.echo(f"  {key}: {value_str}")

        return 0

    except Exception as e:
        click.echo(f"❌ Failed: {e}", err=True)
        if os.getenv("DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


@cli.group()
def workflow():
    """Manage and execute assessment workflows"""
    pass


@workflow.command('list')
def workflow_list():
    """List available workflow templates"""
    from workflow import WorkflowEngine
    from pathlib import Path

    # Get templates directory
    cli_dir = Path(__file__).parent
    templates_dir = cli_dir / 'templates'

    templates = WorkflowEngine.list_templates(templates_dir)

    if not templates:
        click.echo("No workflow templates found")
        return 0

    click.echo("Available Workflow Templates:")
    click.echo("=" * 80)
    for tmpl in templates:
        click.echo(f"\n{tmpl['name']} (v{tmpl['version']})")
        click.echo(f"  File: {tmpl['file']}")
        click.echo(f"  Description: {tmpl['description']}")
    click.echo(f"\nTotal: {len(templates)} templates")
    return 0


@workflow.command('run')
@click.argument('template_name')
@click.option('--project', '-p', required=True, help='Project ID for scan imports')
@click.option('--target', '-t', required=True, help='Target IP/network/domain')
@click.option('--rate', default='10000', help='Scan rate (for masscan)')
@click.option('--wordlist', default='/usr/share/wordlists/dirb/common.txt', help='Wordlist for web enumeration')
@click.option('--dry-run', is_flag=True, help='Show workflow steps without executing')
@handle_api_error
def workflow_run(template_name, project, target, rate, wordlist, dry_run):
    """
    Execute a workflow template.

    \b
    Examples:
      hermes workflow run external-assessment --project pentest --target 192.168.1.0/24
      hermes workflow run web-app-enum --project assessment --target example.com
      hermes workflow run internal-network-scan --project internal --target 10.0.0.0/8 --rate 50000
    """
    from workflow import WorkflowEngine
    from pathlib import Path

    api_client = get_api_client()
    engine = WorkflowEngine(api_client)

    # Find template file
    cli_dir = Path(__file__).parent
    templates_dir = cli_dir / 'templates'
    template_path = templates_dir / f"{template_name}.yml"

    if not template_path.exists():
        # Try without extension
        template_path = templates_dir / template_name
        if not template_path.exists():
            click.echo(f"❌ Template not found: {template_name}", err=True)
            click.echo(f"\nRun 'hermes workflow list' to see available templates", err=True)
            return 1

    try:
        # Load workflow
        workflow = engine.load_workflow(template_path)

        # Prepare variables
        variables = {
            'project': project,
            'target': target,
            'rate': rate,
            'wordlist': wordlist
        }

        # Execute workflow
        engine.execute_workflow(workflow, variables, project, dry_run)
        return 0

    except Exception as e:
        click.echo(f"❌ Workflow failed: {e}", err=True)
        if os.getenv("DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


@workflow.command('validate')
@click.argument('template_path', type=click.Path(exists=True))
def workflow_validate(template_path):
    """Validate a workflow template file"""
    from workflow import WorkflowEngine
    from pathlib import Path

    engine = WorkflowEngine(None)

    try:
        workflow = engine.load_workflow(Path(template_path))
        click.echo("✓ Workflow template is valid")
        click.echo(f"\nName: {workflow['name']}")
        click.echo(f"Description: {workflow['description']}")
        click.echo(f"Version: {workflow['version']}")
        click.echo(f"Steps: {len(workflow['steps'])}")
        return 0
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        return 1


@cli.group()
def plugins():
    """Manage Hermes CLI plugins"""
    pass


@plugins.command('list')
def plugins_list():
    """List all loaded plugins"""
    from plugins import get_plugin_manager

    manager = get_plugin_manager()
    plugin_list = manager.list_plugins()

    if not plugin_list:
        click.echo("No plugins loaded")
        return 0

    click.echo("Loaded Plugins:")
    click.echo("=" * 80)

    # Group by type
    wrappers = [p for p in plugin_list if p['type'] == 'wrapper']
    parsers = [p for p in plugin_list if p['type'] == 'parser']

    if wrappers:
        click.echo("\nTool Wrappers:")
        for plugin in wrappers:
            click.echo(f"  {plugin['name']:20s} {plugin['class']}")

    if parsers:
        click.echo("\nOutput Parsers:")
        for plugin in parsers:
            click.echo(f"  {plugin['name']:20s} {plugin['class']}")

    click.echo(f"\nTotal: {len(plugin_list)} plugins ({len(wrappers)} wrappers, {len(parsers)} parsers)")
    return 0


@plugins.command('distributions')
def plugins_distributions():
    """List installed plugin packages"""
    from plugins import PluginManager

    dists = PluginManager.list_distributions()

    if not dists:
        click.echo("No plugin packages installed")
        return 0

    click.echo("Installed Plugin Packages:")
    click.echo("=" * 80)
    for dist in dists:
        click.echo(f"\n{dist['name']} (v{dist['version']})")
        capabilities = []
        if dist['has_wrapper']:
            capabilities.append("wrappers")
        if dist['has_parser']:
            capabilities.append("parsers")
        click.echo(f"  Provides: {', '.join(capabilities)}")

    click.echo(f"\nTotal: {len(dists)} plugin packages")
    return 0


@cli.group()
def wrap():
    """Wrap common pentesting tools with auto-import functionality"""
    pass


@wrap.command('nmap')
@click.argument('args', nargs=-1, required=True)
@click.option('--project', '-p', help='Project ID for auto-import', required=True)
@click.option('--no-import', is_flag=True, help='Run tool without auto-importing results')
@click.option('--dry-run', is_flag=True, help='Show command without executing')
@handle_api_error
def wrap_nmap(args, project, no_import, dry_run):
    """
    Run nmap with automatic result import to Hermes.

    Automatically adds -oX flag to generate XML output if not specified.
    Supports all nmap output formats: -oN, -oX, -oG, -oA.

    \b
    Examples:
      hermes wrap nmap -sV -p- 192.168.1.0/24 --project pentest-2025
      hermes wrap nmap -sS -sV -p22,80,443 target.com --project assessment
      hermes wrap nmap -A scanme.nmap.org --project demo --dry-run
    """
    from wrappers.nmap import NmapWrapper

    api_client = get_api_client()
    wrapper = NmapWrapper(project_id=project, api_client=api_client)

    try:
        result = wrapper.execute_tool(
            args=list(args),
            auto_import=not no_import,
            dry_run=dry_run
        )

        if dry_run:
            return 0

        if result.get('returncode', 0) == 0:
            if not no_import:
                click.echo(f"\n✓ Scan completed and imported to project '{project}'")
            return 0
        else:
            return 1

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(5)


@wrap.command('masscan')
@click.argument('args', nargs=-1, required=True)
@click.option('--project', '-p', help='Project ID for auto-import', required=True)
@click.option('--no-import', is_flag=True, help='Run tool without auto-importing results')
@click.option('--dry-run', is_flag=True, help='Show command without executing')
@click.option('--batch-size', default=1000, help='Batch size for processing large result sets')
@handle_api_error
def wrap_masscan(args, project, no_import, dry_run, batch_size):
    """
    Run masscan with automatic result import to Hermes.

    Automatically adds -oJ flag to generate JSON output if not specified.
    Optimized for handling large result sets with batch processing.

    \b
    Examples:
      hermes wrap masscan -p1-65535 10.0.0.0/8 --rate 10000 --project pentest
      hermes wrap masscan -p80,443 192.168.1.0/24 --project web-scan
      hermes wrap masscan -p1-1024 target.com --project demo --dry-run
    """
    from wrappers.masscan import MasscanWrapper

    api_client = get_api_client()
    wrapper = MasscanWrapper(
        project_id=project,
        api_client=api_client,
        batch_size=batch_size
    )

    try:
        result = wrapper.execute_tool(
            args=list(args),
            auto_import=not no_import,
            dry_run=dry_run
        )

        if dry_run:
            return 0

        if result.get('returncode', 0) == 0:
            if not no_import:
                click.echo(f"\n✓ Scan completed and imported to project '{project}'")
            return 0
        else:
            return 1

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(5)


@wrap.command('dirb')
@click.argument('args', nargs=-1, required=True)
@click.option('--project', '-p', help='Project ID for auto-import', required=True)
@click.option('--no-import', is_flag=True, help='Run tool without auto-importing results')
@click.option('--dry-run', is_flag=True, help='Show command without executing')
@click.option('--target-host', help='Host ID to correlate discoveries with')
@handle_api_error
def wrap_dirb(args, project, no_import, dry_run, target_host):
    """
    Run dirb with automatic result import to Hermes.

    Automatically adds -o flag to save output if not specified.
    Correlates discovered paths with existing service data.

    \b
    Examples:
      hermes wrap dirb http://target.com /usr/share/wordlists/dirb/common.txt --project pentest
      hermes wrap dirb https://example.com -p assessment
      hermes wrap dirb http://10.0.0.1 -p scan --target-host host-id-123
    """
    from wrappers.web_enum import DirbWrapper

    api_client = get_api_client()
    wrapper = DirbWrapper(
        project_id=project,
        api_client=api_client,
        target_host=target_host
    )

    try:
        result = wrapper.execute_tool(
            args=list(args),
            auto_import=not no_import,
            dry_run=dry_run
        )

        if dry_run:
            return 0

        if result.get('returncode', 0) == 0:
            if not no_import:
                click.echo(f"\n✓ Scan completed and imported to project '{project}'")
            return 0
        else:
            return 1

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(5)


@wrap.command('gobuster')
@click.argument('args', nargs=-1, required=True)
@click.option('--project', '-p', help='Project ID for auto-import', required=True)
@click.option('--no-import', is_flag=True, help='Run tool without auto-importing results')
@click.option('--dry-run', is_flag=True, help='Show command without executing')
@click.option('--target-host', help='Host ID to correlate discoveries with')
@handle_api_error
def wrap_gobuster(args, project, no_import, dry_run, target_host):
    """
    Run gobuster with automatic result import to Hermes.

    Automatically adds -o flag to save output if not specified.
    Supports dir, dns, and vhost modes.

    \b
    Examples:
      hermes wrap gobuster dir -u http://target.com -w wordlist.txt --project pentest
      hermes wrap gobuster dns -d example.com -w subdomains.txt --project recon
      hermes wrap gobuster vhost -u http://target.com -w vhosts.txt -p assessment
    """
    from wrappers.web_enum import GobusterWrapper

    api_client = get_api_client()
    wrapper = GobusterWrapper(
        project_id=project,
        api_client=api_client,
        target_host=target_host
    )

    try:
        result = wrapper.execute_tool(
            args=list(args),
            auto_import=not no_import,
            dry_run=dry_run
        )

        if dry_run:
            return 0

        if result.get('returncode', 0) == 0:
            if not no_import:
                click.echo(f"\n✓ Scan completed and imported to project '{project}'")
            return 0
        else:
            return 1

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(5)


@cli.command()
def examples():
    """Show common usage examples and workflow patterns"""
    examples_text = """
Hermes CLI - Common Usage Examples
==================================

Basic Scan Import:
  hermes import nmap-scan.xml --project my-pentest
  hermes import results.json --project my-test --format masscan

Pipeline Integration:
  nmap -oX - 192.168.1.0/24 | hermes pipe --project pentest-2025
  masscan -p1-65535 10.0.0.0/8 --rate=10000 -oJ - | hermes pipe --project scan

Export Reports:
  hermes export my-project
  hermes export my-project --format pdf --output final-report.pdf
  hermes export my-project --format markdown --no-graph

Monitoring Workflows:
  hermes status
  hermes status --project my-project --watch

Configuration:
  hermes config set api_base_url http://localhost:8000
  hermes config set default_project my-main-project
  hermes config list

Complete Workflow:
  # 1. Import scan results
  hermes import nmap-results.xml --project pentest-2025

  # 2. Check processing status
  hermes status --project pentest-2025

  # 3. Export final report
  hermes export pentest-2025 --format pdf --output client-report.pdf

For more information, visit: https://github.com/your-org/hermes
"""
    click.echo(examples_text)
    sys.exit(0)


if __name__ == '__main__':
    cli()