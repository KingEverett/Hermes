# CLI Tool Implementation

## Command Structure

```bash
# Core commands
hermes import <file>          # Import scan file
hermes monitor <directory>    # Monitor directory for new scans
hermes pipe                   # Process stdin input
hermes export <project>       # Export documentation
hermes status                 # Show system status

# Usage examples
nmap -oX - 192.168.1.0/24 | hermes pipe
hermes monitor ~/scans --recursive
hermes export my-project --format pdf --output report.pdf
```

## Implementation

```python
import click
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

@click.group()
def cli():
    """Hermes - Intelligent Pentesting Documentation Tool"""
    pass

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--project', '-p', help='Project name')
@click.option('--format', '-f', 
              type=click.Choice(['auto', 'nmap', 'masscan', 'dirb', 'gobuster']), 
              default='auto')
def import_scan(file: str, project: str, format: str):
    """Import a scan file into Hermes"""
    with open(file, 'r') as f:
        content = f.read()
    
    # Auto-detect format if needed
    if format == 'auto':
        format = detect_format(content, file)
    
    # Parse and import
    api_client = APIClient()
    response = api_client.import_scan(project, content, format)
    
    if response.status == 'success':
        click.echo(f"✓ Imported {response.host_count} hosts, {response.service_count} services")
    else:
        click.echo(f"✗ Import failed: {response.error}", err=True)

@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True)
@click.option('--project', '-p', required=True)
def monitor(directory: str, recursive: bool, project: str):
    """Monitor a directory for new scan files"""
    
    class ScanFileHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory and is_scan_file(event.src_path):
                click.echo(f"New scan detected: {event.src_path}")
                import_scan.invoke(click.Context(import_scan), 
                                 file=event.src_path, 
                                 project=project, 
                                 format='auto')
    
    handler = ScanFileHandler()
    observer = Observer()
    observer.schedule(handler, directory, recursive=recursive)
    observer.start()
    
    click.echo(f"Monitoring {directory} for scan files... Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'text']), default='text')
def pipe(format: str):
    """Process scan data from stdin"""
    content = sys.stdin.read()
    
    # Detect format from content
    if content.startswith('<?xml'):
        scan_format = 'nmap'
    elif content.startswith('{'):
        scan_format = 'masscan'
    else:
        scan_format = 'unknown'
    
    # Process the scan
    api_client = APIClient()
    response = api_client.import_scan('stdin-import', content, scan_format)
    
    if format == 'json':
        click.echo(json.dumps(response.to_dict()))
    else:
        click.echo(f"Processed: {response.host_count} hosts, {response.service_count} services")
```
