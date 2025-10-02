#!/usr/bin/env python3
"""
Unit tests for Hermes CLI commands
Tests use Click's CliRunner for isolated command testing
"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, mock_open
import json
import sys
import os

# Add parent directory to path to import hermes module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes import cli, import_scan, pipe, export, status, config_set, config_get, config_list, examples


@pytest.fixture
def runner():
    """Fixture to create a CliRunner instance"""
    return CliRunner()


@pytest.fixture
def clean_config(tmp_path, monkeypatch):
    """Fixture to ensure clean config file for each test"""
    # Create temporary config directory
    config_dir = tmp_path / '.hermes'
    config_dir.mkdir(mode=0o700)
    config_file = config_dir / 'config.json'

    # Patch the config paths in hermes module
    monkeypatch.setattr('hermes.CONFIG_DIR', config_dir)
    monkeypatch.setattr('hermes.CONFIG_FILE', config_file)

    yield config_file

    # Cleanup after test
    if config_file.exists():
        config_file.unlink()


@pytest.fixture
def mock_api_client():
    """Fixture to create a mock API client"""
    with patch('hermes.get_api_client') as mock:
        client = Mock()
        mock.return_value = client
        yield client


class TestImportCommand:
    """Tests for the import command"""

    def test_import_command_success(self, runner, mock_api_client):
        """Test successful scan import"""
        # Mock API response
        mock_api_client.import_scan.return_value = {
            'scan_id': 'test-scan-123',
            'host_count': 5,
            'service_count': 20,
            'status': 'processing'
        }

        # Create test file
        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, [
                'test.xml',
                '--project', 'test-project'
            ])

        assert result.exit_code == 0
        assert '✓ Imported' in result.output
        assert '5 hosts' in result.output
        assert '20 services' in result.output
        mock_api_client.import_scan.assert_called_once()

    def test_import_command_file_not_found(self, runner):
        """Test import with non-existent file"""
        result = runner.invoke(import_scan, [
            'nonexistent.xml',
            '--project', 'test'
        ])

        assert result.exit_code != 0
        # Click handles Path validation, so error comes from Click

    def test_import_command_missing_project(self, runner):
        """Test import without required --project option"""
        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, ['test.xml'])

        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()

    def test_import_command_with_format(self, runner, mock_api_client):
        """Test import with explicit format specification"""
        mock_api_client.import_scan.return_value = {
            'scan_id': 'test-id',
            'host_count': 3,
            'service_count': 10,
            'status': 'completed'
        }

        with runner.isolated_filesystem():
            with open('scan.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, [
                'scan.xml',
                '--project', 'my-project',
                '--format', 'nmap'
            ])

        assert result.exit_code == 0
        mock_api_client.import_scan.assert_called_with('my-project', 'scan.xml', 'nmap')

    def test_import_command_quiet_mode(self, runner, mock_api_client):
        """Test import in quiet mode"""
        mock_api_client.import_scan.return_value = {
            'scan_id': 'test-id',
            'host_count': 1,
            'service_count': 5,
            'status': 'processing'
        }

        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(cli, [
                '--quiet',
                'import',
                'test.xml',
                '--project', 'test'
            ])

        assert result.exit_code == 0
        # In quiet mode, output should be minimal
        assert 'Importing' not in result.output


class TestPipeCommand:
    """Tests for the pipe command"""

    def test_pipe_command_success(self, runner, mock_api_client):
        """Test successful stdin pipe processing"""
        mock_api_client.import_scan_from_stdin.return_value = {
            'scan_id': 'pipe-test-123',
            'host_count': 10,
            'service_count': 50,
            'status': 'processing'
        }

        xml_content = '<?xml version="1.0"?><nmaprun></nmaprun>'

        result = runner.invoke(pipe, [
            '--project', 'test-project'
        ], input=xml_content)

        assert result.exit_code == 0
        assert '✓ Imported' in result.output
        assert '10 hosts' in result.output
        mock_api_client.import_scan_from_stdin.assert_called_once()

    def test_pipe_command_json_output(self, runner, mock_api_client):
        """Test pipe command with JSON output format"""
        mock_response = {
            'scan_id': 'test-id',
            'host_count': 5,
            'service_count': 15,
            'status': 'queued'
        }
        mock_api_client.import_scan_from_stdin.return_value = mock_response

        result = runner.invoke(pipe, [
            '--project', 'test',
            '--format', 'json'
        ], input='<nmaprun></nmaprun>')

        assert result.exit_code == 0
        # Output should be JSON
        output_data = json.loads(result.output)
        assert output_data['scan_id'] == 'test-id'

    def test_pipe_command_empty_stdin(self, runner):
        """Test pipe command with empty stdin"""
        result = runner.invoke(pipe, [
            '--project', 'test'
        ], input='')

        assert result.exit_code == 2  # Usage error
        assert 'Empty input' in result.output

    def test_pipe_command_auto_detect_format(self, runner, mock_api_client):
        """Test automatic format detection"""
        mock_api_client.import_scan_from_stdin.return_value = {
            'scan_id': 'test-id',
            'host_count': 2,
            'service_count': 8,
            'status': 'processing'
        }

        # Test XML detection
        result = runner.invoke(pipe, [
            '--project', 'test'
        ], input='<?xml version="1.0"?><nmaprun></nmaprun>')

        assert result.exit_code == 0


class TestExportCommand:
    """Tests for the export command"""

    def test_export_command_success(self, runner, mock_api_client):
        """Test successful project export"""
        mock_api_client.export_project.return_value = {'job_id': 'export-job-123'}
        mock_api_client.get_export_job_status.return_value = {'status': 'completed'}
        mock_api_client.download_export.return_value = None

        with runner.isolated_filesystem():
            # Mock the download to create a file
            def create_file(job_id, output_path):
                with open(output_path, 'w') as f:
                    f.write('# Test Report\n')

            mock_api_client.download_export.side_effect = create_file

            result = runner.invoke(export, ['test-project'])

        assert result.exit_code == 0
        assert '✓ Exported' in result.output
        mock_api_client.export_project.assert_called_once()

    def test_export_command_with_format(self, runner, mock_api_client):
        """Test export with specific format"""
        mock_api_client.export_project.return_value = {'job_id': 'job-id'}
        mock_api_client.get_export_job_status.return_value = {'status': 'completed'}
        mock_api_client.download_export.return_value = None

        with runner.isolated_filesystem():
            def create_file(job_id, output_path):
                with open(output_path, 'w') as f:
                    f.write('PDF content')

            mock_api_client.download_export.side_effect = create_file

            result = runner.invoke(export, [
                'my-project',
                '--format', 'pdf',
                '--output', 'report.pdf'
            ])

        assert result.exit_code == 0
        mock_api_client.export_project.assert_called_with(
            'my-project',
            format='pdf',
            include_graph=True,
            include_attack_chains=True
        )

    def test_export_command_with_options(self, runner, mock_api_client):
        """Test export with exclusion options"""
        mock_api_client.export_project.return_value = {'job_id': 'job-123'}
        mock_api_client.get_export_job_status.return_value = {'status': 'completed'}
        mock_api_client.download_export.return_value = None

        with runner.isolated_filesystem():
            def create_file(job_id, output_path):
                with open(output_path, 'w') as f:
                    f.write('Content')

            mock_api_client.download_export.side_effect = create_file

            result = runner.invoke(export, [
                'project-id',
                '--no-graph',
                '--no-chains'
            ])

        mock_api_client.export_project.assert_called_with(
            'project-id',
            format='markdown',
            include_graph=False,
            include_attack_chains=False
        )

    def test_export_command_job_failed(self, runner, mock_api_client):
        """Test export when job fails"""
        mock_api_client.export_project.return_value = {'job_id': 'fail-job'}
        mock_api_client.get_export_job_status.return_value = {
            'status': 'failed',
            'error': 'Export generation failed'
        }

        result = runner.invoke(export, ['failed-project'])

        assert result.exit_code == 1
        assert 'failed' in result.output.lower()


class TestStatusCommand:
    """Tests for the status command"""

    def test_status_command_basic(self, runner, mock_api_client):
        """Test basic status check"""
        mock_api_client.get_system_status.return_value = {
            'database_status': True,
            'redis_status': True,
            'celery_workers': 2,
            'active_scans': 3,
            'queued_research_tasks': 5,
            'failed_jobs': 0
        }

        with patch('hermes.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'healthy', 'version': '1.0.0'}
            mock_get.return_value = mock_response

            result = runner.invoke(status)

        assert result.exit_code == 0
        assert 'Backend API' in result.output
        assert 'PostgreSQL' in result.output
        assert 'Processing Status' in result.output

    def test_status_command_with_project(self, runner, mock_api_client):
        """Test status with project-specific information"""
        mock_api_client.get_system_status.return_value = {
            'database_status': True,
            'redis_status': True,
            'celery_workers': 1,
            'active_scans': 0,
            'queued_research_tasks': 0,
            'failed_jobs': 0
        }
        mock_api_client.get_project_status.return_value = {
            'name': 'Test Project',
            'metadata': {
                'host_count': 25,
                'service_count': 100,
                'vulnerability_count': 15
            }
        }

        with patch('hermes.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'healthy', 'version': '1.0.0'}
            mock_get.return_value = mock_response

            result = runner.invoke(status, ['--project', 'test-project'])

        assert result.exit_code == 0
        assert 'Project Status' in result.output
        assert '25' in result.output  # host count


class TestConfigCommands:
    """Tests for config management commands"""

    def test_config_set_valid(self, runner, clean_config):
        """Test setting valid configuration"""
        result = runner.invoke(config_set, ['api_base_url', 'http://example.com'])

        assert result.exit_code == 0
        assert '✓ Set' in result.output

    def test_config_set_invalid_key(self, runner, clean_config):
        """Test setting invalid configuration key"""
        result = runner.invoke(config_set, ['invalid_key', 'value'])

        assert result.exit_code == 2
        assert 'Invalid configuration key' in result.output

    def test_config_set_invalid_url(self, runner, clean_config):
        """Test setting invalid URL"""
        result = runner.invoke(config_set, ['api_base_url', 'not-a-url'])

        assert result.exit_code == 2
        assert 'must start with http' in result.output

    def test_config_get_existing(self, runner, clean_config):
        """Test getting existing configuration value"""
        # First set a value
        runner.invoke(config_set, ['timeout', '60'])

        # Then get it
        result = runner.invoke(config_get, ['timeout'])

        assert result.exit_code == 0
        assert '60' in result.output

    def test_config_get_nonexistent(self, runner, clean_config):
        """Test getting non-existent configuration key"""
        result = runner.invoke(config_get, ['nonexistent'])

        assert result.exit_code == 5  # Not found
        assert 'not found' in result.output.lower()

    def test_config_list_empty(self, runner, clean_config):
        """Test listing configuration when empty"""
        result = runner.invoke(config_list)

        assert result.exit_code == 0
        assert 'No configuration' in result.output

    def test_config_list_with_values(self, runner, clean_config):
        """Test listing configuration with values"""
        runner.invoke(config_set, ['api_base_url', 'http://localhost:8000'])
        runner.invoke(config_set, ['timeout', '30'])

        result = runner.invoke(config_list)

        assert result.exit_code == 0
        assert 'http://localhost:8000' in result.output
        assert '30' in result.output

    def test_config_api_key_masking(self, runner, clean_config):
        """Test that API key is masked in get and list"""
        runner.invoke(config_set, ['api_key', 'supersecretkey123456'])

        # Test get
        result_get = runner.invoke(config_get, ['api_key'])
        assert 'supersecretkey123456' not in result_get.output
        assert '...' in result_get.output

        # Test list
        result_list = runner.invoke(config_list)
        assert 'supersecretkey123456' not in result_list.output
        assert '...' in result_list.output


class TestExamplesCommand:
    """Tests for examples command"""

    def test_examples_command(self, runner):
        """Test examples command displays usage examples"""
        result = runner.invoke(examples)

        assert result.exit_code == 0
        assert 'Examples' in result.output
        assert 'hermes import' in result.output
        assert 'hermes pipe' in result.output
        assert 'hermes export' in result.output


class TestCLIOptions:
    """Tests for global CLI options"""

    def test_debug_flag(self, runner):
        """Test --debug flag"""
        result = runner.invoke(cli, ['--debug', '--help'])
        assert result.exit_code == 0

    def test_quiet_flag(self, runner):
        """Test --quiet flag"""
        result = runner.invoke(cli, ['--quiet', '--help'])
        assert result.exit_code == 0

    def test_verbose_flag(self, runner):
        """Test --verbose flag"""
        result = runner.invoke(cli, ['--verbose', '--help'])
        assert result.exit_code == 0

    def test_version_option(self, runner):
        """Test --version option"""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output


class TestErrorHandling:
    """Tests for error handling and exit codes"""

    def test_connection_error_exit_code(self, runner, mock_api_client):
        """Test that connection errors return exit code 3"""
        from api_client import HermesConnectionError
        mock_api_client.import_scan.side_effect = HermesConnectionError("Cannot connect")

        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, [
                'test.xml',
                '--project', 'test'
            ])

        assert result.exit_code == 3

    def test_api_error_exit_code(self, runner, mock_api_client):
        """Test that API errors return exit code 1"""
        from api_client import HermesAPIError
        mock_api_client.import_scan.side_effect = HermesAPIError("API error occurred")

        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, [
                'test.xml',
                '--project', 'test'
            ])

        assert result.exit_code == 1
