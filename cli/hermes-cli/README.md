# Hermes CLI

Comprehensive command-line interface for Hermes - Intelligent Pentesting Documentation Tool

## Overview

The Hermes CLI provides a complete terminal-based workflow for security professionals to:
- Import scan results from various tools (nmap, masscan, dirb, gobuster)
- Process scan data via stdin for pipeline integration
- Monitor directories for automatic scan file processing
- Export professional documentation in multiple formats (markdown, PDF, JSON, CSV)
- Monitor system and project status in real-time
- Manage CLI configuration and preferences

## Installation

### From Source (Development Mode)

```bash
cd cli/hermes-cli
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

## Requirements

- Python 3.8 or higher
- Hermes backend API running (default: http://localhost:8000)
- Required packages: click, requests, python-dotenv

## Quick Start

1. **Check Backend Status**
```bash
hermes health
hermes status
```

2. **Import Scan Results**
```bash
hermes import nmap-scan.xml --project my-pentest
```

3. **Export Documentation**
```bash
hermes export my-pentest --format pdf --output report.pdf
```

## Command Reference

### Core Commands

#### `hermes import <file>`
Import a scan file into Hermes

**Options:**
- `--project, -p` (required): Project ID or name
- `--format, -f`: Scan format (auto, nmap, masscan, dirb, gobuster) [default: auto]

**Examples:**
```bash
hermes import nmap-scan.xml --project pentest-2025
hermes import scan.json --project my-test --format masscan
```

**Exit Codes:**
- 0: Success
- 3: Connection error
- 5: File not found

---

#### `hermes pipe`
Process scan data from stdin (for pipeline integration)

**Options:**
- `--project, -p` (required): Project ID or name
- `--format, -f`: Output format (auto, json, text) [default: text]

**Examples:**
```bash
nmap -oX - 192.168.1.0/24 | hermes pipe --project pentest-2025
masscan -p1-65535 10.0.0.0/8 -oJ - | hermes pipe --project scan
cat scan-results.xml | hermes pipe --project test --format json
```

**Exit Codes:**
- 0: Success
- 2: Usage error (empty stdin, missing arguments)
- 3: Connection error

---

#### `hermes export <project_id>`
Export project documentation

**Options:**
- `--format, -f`: Export format (markdown, pdf, json, csv) [default: markdown]
- `--output, -o`: Output file path [default: {project_id}-report.{ext}]
- `--no-graph`: Exclude network graph from export
- `--no-chains`: Exclude attack chains from export

**Examples:**
```bash
hermes export my-project
hermes export my-project --format pdf --output client-report.pdf
hermes export my-project --format markdown --no-graph
```

**Exit Codes:**
- 0: Success
- 1: Export job failed
- 5: Project not found
- 6: Timeout (export took longer than 5 minutes)

---

#### `hermes monitor` - Directory Monitoring Commands

Monitor directories for scan files with automatic import. Supports both single-directory foreground monitoring and multi-directory daemon mode.

---

##### `hermes monitor run <directory>` - Single Directory Monitoring

Monitor a single directory in foreground mode (legacy compatible).

**Options:**
- `--project, -p` (required): Project ID to import scans into
- `--recursive, -r`: Monitor directory recursively
- `--patterns`: File glob patterns (comma-separated) [default: *.xml,*.json,*.txt]
- `--exclude`: Exclusion patterns (comma-separated) [default: *.tmp,*.partial,*~,.*.swp]
- `--delay`: Delay in seconds before processing new files [default: 5]
- `--max-concurrent`: Maximum concurrent file processing tasks [default: 3]
- `--force-reprocess`: Reprocess files even if already processed

**Examples:**
```bash
# Monitor a directory for XML scan files
hermes monitor run ~/scans --project my-pentest

# Monitor recursively with custom patterns
hermes monitor run ~/scans --recursive --patterns "*.xml,*nmap*.xml"

# Monitor with custom delay and exclusions
hermes monitor run /data/scans --project pentest --delay 10 --exclude "*.tmp,*.bak"

# High-volume scanning with more concurrent workers
hermes monitor run ~/scans --project test --max-concurrent 5
```

---

##### `hermes monitor start --config <file>` - Daemon Mode (Multi-Directory)

Start monitor daemon to watch multiple directories simultaneously using a configuration file.

**Configuration File Format** (`monitor-config.json`):
```json
{
  "monitors": [
    {
      "directory": "~/scans/nmap",
      "project": "my-pentest",
      "patterns": ["*.xml"],
      "recursive": false,
      "delay": 5,
      "max_concurrent": 3
    },
    {
      "directory": "~/scans/masscan",
      "project": "my-pentest",
      "patterns": ["*.json"],
      "delay": 3,
      "max_concurrent": 3
    }
  ]
}
```

**Examples:**
```bash
# Create example config file
cp monitor-config.example.json ~/.hermes/monitor-config.json
# Edit config file with your directories
nano ~/.hermes/monitor-config.json

# Start daemon
hermes monitor start --config ~/.hermes/monitor-config.json

# Check daemon status
hermes monitor status

# Stop daemon
hermes monitor stop
```

---

##### `hermes monitor status` - Check Daemon Status

Show whether monitor daemon is running and configuration details.

**Example Output:**
```
Monitor Daemon Status: RUNNING
  PID: 12345
  Config: /home/user/.hermes/monitor-config.json
  Log: /home/user/.hermes/monitor.log
```

---

##### `hermes monitor stop` - Stop Daemon

Stop the running monitor daemon gracefully.

---

### Systemd Integration (Optional)

For production deployments, you can run the monitor as a systemd service.

**Setup:**
```bash
# Copy example service file
sudo cp hermes-monitor.service.example /etc/systemd/system/hermes-monitor.service

# Edit service file to set your username and paths
sudo nano /etc/systemd/system/hermes-monitor.service

# Enable and start service
sudo systemctl enable hermes-monitor
sudo systemctl start hermes-monitor

# Check status
sudo systemctl status hermes-monitor

# View logs
sudo journalctl -u hermes-monitor -f
```

**Features:**
- Automatic file type detection (nmap XML, masscan JSON, dirb text)
- Duplicate detection using SHA256 file hashing
- Configurable processing delay to avoid incomplete files
- Background processing with thread pool executor
- Concurrent file processing (configurable worker count)
- Multi-directory monitoring with daemon mode
- Real-time notifications (foreground mode)
- State persistence in `~/.hermes/monitor-state.json`
- Graceful shutdown with proper cleanup

**Exit Codes:**
- 0: Success (monitor stopped gracefully)
- 2: Usage error (missing directory or project)
- 3: Connection error

**Notes:**
- Duplicate detection persists across monitor sessions
- State file cleaned automatically (entries older than 30 days removed)
- Daemon mode runs in background and survives terminal closure
- Use `monitor run` for quick single-directory monitoring
- Use `monitor start` for production multi-directory setups

---

#### `hermes status`
Show system and project status

**Options:**
- `--project, -p`: Show project-specific status
- `--watch, -w`: Continuously monitor status (refresh every 5s)

**Examples:**
```bash
hermes status
hermes status --project my-pentest
hermes status --watch
hermes status --project my-pentest --watch
```

**Exit Codes:**
- 0: Success
- 3: Connection error

---

#### `hermes health`
Quick health check of the backend API

**Example:**
```bash
hermes health
```

---

### Configuration Commands

#### `hermes config set <key> <value>`
Set a configuration value

**Valid Keys:**
- `api_base_url`: Backend API URL (must start with http:// or https://)
- `default_project`: Default project ID
- `scan_directory`: Default scan directory path
- `timeout`: Request timeout in seconds (integer)
- `api_key`: API authentication key (masked in output)

**Examples:**
```bash
hermes config set api_base_url http://localhost:8000
hermes config set default_project my-main-project
hermes config set timeout 60
```

**Exit Codes:**
- 0: Success
- 2: Invalid key or value

---

#### `hermes config get <key>`
Get a configuration value

**Example:**
```bash
hermes config get api_base_url
hermes config get api_key  # Output is masked
```

**Exit Codes:**
- 0: Success
- 5: Key not found

---

#### `hermes config list`
List all configuration values

**Example:**
```bash
hermes config list
```

---

### Help Commands

#### `hermes examples`
Display common usage examples and workflow patterns

**Example:**
```bash
hermes examples
```

---

## Global Options

Available for all commands:

- `--debug`: Enable debug output with detailed logging
- `--quiet, -q`: Suppress non-error output (useful for scripting)
- `--verbose, -v`: Enable verbose output
- `--version`: Show CLI version
- `--help`: Show command help

**Examples:**
```bash
hermes --debug import scan.xml --project test
hermes --quiet export my-project --format json
hermes --verbose status --project test
```

## Configuration

### Configuration File

Configuration is stored in `~/.hermes/config.json`

**Location:**
- Linux/macOS: `~/.hermes/config.json`
- Windows: `%USERPROFILE%\.hermes\config.json`

**Permissions:** 0700 (owner read/write/execute only)

### Environment Variables

The CLI supports environment variables for configuration:

- `API_BASE_URL`: Backend API base URL
- `DEBUG`: Enable debug mode (true/false)
- `HERMES_CONFIG`: Custom configuration file path

**Priority Order (highest to lowest):**
1. Command-line arguments
2. Environment variables
3. Configuration file (~/.hermes/config.json)
4. Default values

### Example .env File

Create a `.env` file in your working directory:

```bash
API_BASE_URL=http://localhost:8000
DEBUG=false
```

See `.env.example` for a template.

## Exit Codes

The CLI follows Unix exit code conventions:

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General error | Unspecified error occurred |
| 2 | Usage error | Invalid arguments or missing required options |
| 3 | Connection error | Cannot connect to backend API |
| 4 | Authentication error | API authentication failed (future) |
| 5 | Not found | Resource not found (file, project, etc.) |
| 6 | Timeout error | Request or operation timed out |

## Tool Wrappers

The CLI provides seamless integration with common pentesting tools through automatic output capture and import.

### Supported Tools

- **nmap**: Network scanning and service enumeration
- **masscan**: High-speed port scanning
- **gobuster**: Directory/DNS/vhost brute-forcing
- **dirb**: Web content discovery

### Wrapper Commands

All wrapper commands support:
- `--project` / `-p`: Project ID for auto-import (required)
- `--no-import`: Run tool without auto-importing results
- `--dry-run`: Show command without executing

#### Nmap Wrapper

```bash
# Basic scan with auto-import
hermes wrap nmap -sV -p- 192.168.1.0/24 --project pentest-2025

# Service enumeration
hermes wrap nmap -sS -sV -p22,80,443 target.com --project assessment

# Full TCP scan with scripts
hermes wrap nmap -A -p1-65535 scanme.nmap.org --project demo

# Dry run to see command
hermes wrap nmap -sV target.com --project test --dry-run
```

The wrapper automatically adds `-oX` flag to generate XML output if not specified.

#### Masscan Wrapper

```bash
# Fast port scan
hermes wrap masscan -p1-65535 10.0.0.0/8 --rate 10000 --project pentest

# Common ports scan
hermes wrap masscan -p80,443 192.168.1.0/24 --project web-scan

# With custom batch size for large results
hermes wrap masscan -p1-65535 target-range --rate 50000 --project scan --batch-size 5000
```

Automatically adds `-oJ` flag for JSON output. Optimized for handling large result sets.

#### Gobuster Wrapper

```bash
# Directory brute-force
hermes wrap gobuster dir -u http://target.com -w wordlist.txt --project pentest

# DNS subdomain enumeration
hermes wrap gobuster dns -d example.com -w subdomains.txt --project recon

# Virtual host discovery
hermes wrap gobuster vhost -u http://target.com -w vhosts.txt --project assessment
```

#### Dirb Wrapper

```bash
# Basic directory enumeration
hermes wrap dirb http://target.com --project pentest

# With custom wordlist
hermes wrap dirb http://target.com /usr/share/wordlists/dirb/common.txt --project scan
```

## Workflow Templates

Execute pre-configured assessment workflows with multiple tools.

### Available Workflows

```bash
# List available templates
hermes workflow list
```

### Executing Workflows

#### External Network Assessment

```bash
hermes workflow run external-assessment \
  --project pentest-2025 \
  --target 192.168.1.0/24 \
  --rate 10000
```

Steps: masscan port discovery → nmap service enumeration

#### Internal Network Scan

```bash
hermes workflow run internal-network-scan \
  --project internal \
  --target 10.0.0.0/8 \
  --rate 50000
```

Steps: fast masscan → detailed nmap

#### Web Application Enumeration

```bash
hermes workflow run web-app-enum \
  --project webapp \
  --target example.com \
  --wordlist /usr/share/wordlists/dirb/common.txt
```

Steps: nmap port scan → gobuster directory enumeration

### Workflow Options

- `--dry-run`: Preview workflow steps without executing
- `--rate`: Scan rate for masscan (default: 10000)
- `--wordlist`: Wordlist path for web enumeration

### Creating Custom Workflows

Create a YAML file in `cli/hermes-cli/templates/`:

```yaml
name: Custom Assessment
description: My custom workflow
version: 1.0

variables:
  target: "{{target}}"
  project: "{{project}}"

steps:
  - name: port-scan
    tool: nmap
    args:
      - "-sV"
      - "{{target}}"
    timeout: 3600
    on_error: fail

  - name: web-enum
    tool: gobuster
    depends_on:
      - port-scan
    args:
      - "dir"
      - "-u"
      - "http://{{target}}"
      - "-w"
      - "/usr/share/wordlists/dirb/common.txt"
    timeout: 1800
    on_error: continue
```

Validate your workflow:

```bash
hermes workflow validate templates/my-workflow.yml
```

## Parser Management

### List Parsers

```bash
# List all registered parsers
hermes parsers list

# Test parser on a file
hermes parsers test nmap-scan.xml

# Test with lenient mode (continue on errors)
hermes parsers test masscan-results.json --lenient
```

### Validate Scan Files

```bash
# Validate without importing
hermes validate nmap-scan.xml

# Validate with lenient parsing
hermes validate corrupted-scan.xml --lenient
```

The validate command:
- Detects file encoding automatically
- Tests parser detection
- Validates parsed data structure
- Shows summary without API submission

## Plugin System

### List Plugins

```bash
# List loaded plugins
hermes plugins list

# List installed plugin packages
hermes plugins distributions
```

### Installing Plugins

```bash
# Install a plugin package
pip install hermes-plugin-nuclei

# Verify plugin loaded
hermes plugins list
```

### Creating Custom Plugins

Create a Python package with entry points:

```python
# setup.py
from setuptools import setup

setup(
    name="hermes-plugin-mytool",
    version="1.0.0",
    packages=['hermes_mytool'],
    install_requires=['hermes-cli>=1.0.0'],
    entry_points={
        'hermes_cli.wrappers': [
            'mytool=hermes_mytool.wrapper:MyToolWrapper',
        ],
        'hermes_cli.parsers': [
            'mytool=hermes_mytool.parser:MyToolParser',
        ],
    },
)
```

Implement `ToolWrapper` and `ToolOutputParser` base classes. See built-in wrappers/parsers for examples.

## Common Workflows

### Basic Pentest Workflow

```bash
# Option 1: Using wrappers
hermes wrap nmap -sV -p- 192.168.1.0/24 --project pentest-2025
hermes wrap gobuster dir -u http://target.com -w wordlist.txt --project pentest-2025

# Option 2: Using workflow template
hermes workflow run external-assessment --project pentest-2025 --target 192.168.1.0/24

# Check status and export
hermes status --project pentest-2025
hermes export pentest-2025 --format pdf --output client-report.pdf
```

### Pipeline Integration

```bash
# Scan and import in one command
nmap -oX - 192.168.1.0/24 | hermes pipe --project network-scan

# Masscan pipeline
masscan -p1-65535 10.0.0.0/8 --rate=10000 -oJ - | hermes pipe --project fast-scan

# Process existing scan with pipeline
cat old-scan.xml | hermes pipe --project archive-2024
```

### Directory Monitoring (Automatic Scan Processing)

```bash
# Monitor a scan output directory
hermes monitor ~/scans --project pentest-2025

# Monitor recursively with custom file patterns
hermes monitor ~/nmap-output --project pentest-2025 --recursive --patterns "*.xml"

# Run continuous scanning workflow
# Terminal 1: Start monitoring
hermes monitor ~/scans --project pentest-2025 --delay 3

# Terminal 2: Run scans (files automatically imported)
nmap -oX ~/scans/network-scan.xml 192.168.1.0/24
masscan -p1-65535 10.0.0.0/8 -oJ ~/scans/masscan-results.json
```

### Continuous Status Monitoring

```bash
# Watch system status in real-time
hermes status --watch

# Monitor specific project
hermes status --project pentest-2025 --watch

# Stop with Ctrl+C
```

### Scripting Integration

```bash
#!/bin/bash
# Example: Automated scan and report generation

PROJECT="automated-scan-$(date +%Y%m%d)"

# Run scan and import
nmap -oX - -p- --open 192.168.1.0/24 | hermes --quiet pipe --project "$PROJECT"

# Wait for processing
sleep 30

# Export report
hermes --quiet export "$PROJECT" --format markdown --output "report-$PROJECT.md"

# Check exit code
if [ $? -eq 0 ]; then
    echo "Report generated successfully"
else
    echo "Report generation failed" >&2
    exit 1
fi
```

## Testing

### Run Unit Tests

```bash
cd cli/hermes-cli
pytest tests/test_cli.py -v
```

### Run Integration Tests

Integration tests require a running backend:

```bash
# Start backend first
docker-compose up -d backend

# Run integration tests
pytest tests/test_integration.py -v -m integration
```

### Run All Tests with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Troubleshooting

### Backend Not Accessible

**Error:** `❌ Cannot connect to backend at http://localhost:8000`

**Solutions:**
1. Ensure backend is running: `docker-compose up backend`
2. Check backend URL: `hermes config get api_base_url`
3. Update URL if needed: `hermes config set api_base_url http://correct-url:8000`

### File Not Found

**Error:** `❌ File not found: scan.xml`

**Solutions:**
1. Verify file path is correct
2. Use absolute path: `hermes import /full/path/to/scan.xml --project test`
3. Check file permissions

### Import Timeout

**Error:** `❌ Request timed out`

**Solutions:**
1. Increase timeout: `hermes config set timeout 120`
2. Check backend logs for processing issues
3. Try smaller scan files

### Configuration Issues

**Error:** `❌ Invalid configuration key`

**Solutions:**
1. Check valid keys: `hermes config set --help`
2. List current config: `hermes config list`
3. Reset config: `rm ~/.hermes/config.json`

## Development

### Project Structure

```
cli/hermes-cli/
├── hermes.py              # Main CLI implementation
├── api_client.py          # API client abstraction layer
├── monitor_state.py       # Monitor state management
├── setup.py               # Package configuration
├── .env.example           # Example environment variables
├── README.md              # This file
└── tests/
    ├── __init__.py
    ├── test_cli.py        # Unit tests
    ├── test_monitor.py    # Monitor command tests
    └── test_integration.py # Integration tests
```

### Adding New Commands

1. Add command function in `hermes.py`
2. Use `@cli.command()` decorator
3. Add `@handle_api_error` for error handling
4. Add corresponding API client method in `api_client.py`
5. Write tests in `tests/test_cli.py`
6. Update this README

### Running in Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run CLI directly
python hermes.py --help

# Run with debugging
DEBUG=true python hermes.py status
```

## Support

For issues, feature requests, or contributions:
- GitHub Issues: https://github.com/your-org/hermes/issues
- Documentation: https://docs.hermes.example.com

## License

See main project LICENSE file.
