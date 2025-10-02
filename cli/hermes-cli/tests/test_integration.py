#!/usr/bin/env python3
"""
Integration tests for Hermes CLI
Tests real workflows with backend API integration

Mark tests with @pytest.mark.integration for selective running:
  pytest -m integration
"""

import pytest
from click.testing import CliRunner
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes import cli, import_scan, pipe, export, status


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def runner():
    """Fixture to create a CliRunner instance"""
    return CliRunner()


@pytest.fixture
def sample_nmap_xml():
    """Fixture providing sample nmap XML content"""
    return """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
    <host>
        <address addr="192.168.1.100" addrtype="ipv4"/>
        <hostnames>
            <hostname name="testhost.local" type="PTR"/>
        </hostnames>
        <ports>
            <port protocol="tcp" portid="22">
                <state state="open"/>
                <service name="ssh" product="OpenSSH" version="8.9p1"/>
            </port>
            <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http" product="nginx" version="1.18.0"/>
            </port>
        </ports>
    </host>
    <host>
        <address addr="192.168.1.101" addrtype="ipv4"/>
        <ports>
            <port protocol="tcp" portid="443">
                <state state="open"/>
                <service name="https" product="Apache" version="2.4.52"/>
            </port>
        </ports>
    </host>
</nmaprun>
"""


class TestImportExportWorkflow:
    """Test complete import → export workflow"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_import_and_export_workflow(self, runner, sample_nmap_xml):
        """
        Test full workflow:
        1. Import scan file
        2. Verify import succeeded
        3. Export project
        4. Verify export file exists
        """
        with runner.isolated_filesystem():
            # Create test scan file
            scan_file = 'test-scan.xml'
            with open(scan_file, 'w') as f:
                f.write(sample_nmap_xml)

            # Step 1: Import scan
            import_result = runner.invoke(import_scan, [
                scan_file,
                '--project', 'integration-test-project'
            ])

            assert import_result.exit_code == 0, f"Import failed: {import_result.output}"
            assert '✓ Imported' in import_result.output
            assert '2 hosts' in import_result.output  # Our sample has 2 hosts

            # Step 2: Export project
            export_result = runner.invoke(export, [
                'integration-test-project',
                '--format', 'markdown',
                '--output', 'test-report.md'
            ])

            assert export_result.exit_code == 0, f"Export failed: {export_result.output}"
            assert '✓ Exported' in export_result.output

            # Step 3: Verify export file
            assert Path('test-report.md').exists()
            content = Path('test-report.md').read_text()
            assert len(content) > 0


class TestPipeWorkflow:
    """Test stdin pipe integration workflows"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_pipe_and_status_workflow(self, runner, sample_nmap_xml):
        """
        Test pipeline workflow:
        1. Pipe scan data via stdin
        2. Check status to verify processing
        """
        with runner.isolated_filesystem():
            # Step 1: Pipe scan data
            pipe_result = runner.invoke(pipe, [
                '--project', 'pipe-test-project',
                '--format', 'text'
            ], input=sample_nmap_xml)

            assert pipe_result.exit_code == 0, f"Pipe failed: {pipe_result.output}"
            assert '✓ Imported' in pipe_result.output

            # Step 2: Check status
            status_result = runner.invoke(status, [
                '--project', 'pipe-test-project'
            ])

            assert status_result.exit_code == 0
            assert 'Project Status' in status_result.output


class TestStatusMonitoring:
    """Test status monitoring functionality"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_status_command_real_backend(self, runner):
        """Test status command with real backend"""
        result = runner.invoke(status)

        assert result.exit_code == 0
        assert 'Backend API' in result.output
        assert 'PostgreSQL' in result.output
        assert 'Redis' in result.output


class TestConfigPersistence:
    """Test configuration persistence across CLI invocations"""

    def test_config_persistence(self, runner):
        """Test that configuration persists between CLI invocations"""
        with runner.isolated_filesystem():
            # Set configuration
            set_result = runner.invoke(cli, [
                'config', 'set',
                'api_base_url', 'http://test.example.com'
            ])
            assert set_result.exit_code == 0

            # Get configuration in separate invocation
            get_result = runner.invoke(cli, [
                'config', 'get',
                'api_base_url'
            ])
            assert get_result.exit_code == 0
            assert 'http://test.example.com' in get_result.output


class TestErrorScenarios:
    """Test error handling in real scenarios"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_import_nonexistent_project(self, runner, sample_nmap_xml):
        """Test importing to non-existent project"""
        with runner.isolated_filesystem():
            with open('test.xml', 'w') as f:
                f.write(sample_nmap_xml)

            result = runner.invoke(import_scan, [
                'test.xml',
                '--project', 'nonexistent-project-12345'
            ])

            # Should fail gracefully with appropriate error
            assert result.exit_code != 0

    def test_backend_not_running(self, runner):
        """Test CLI behavior when backend is not accessible"""
        with runner.isolated_filesystem():
            # Configure to point to non-existent backend
            runner.invoke(cli, [
                'config', 'set',
                'api_base_url', 'http://localhost:9999'
            ])

            with open('test.xml', 'w') as f:
                f.write('<nmaprun></nmaprun>')

            result = runner.invoke(import_scan, [
                'test.xml',
                '--project', 'test'
            ])

            # Should fail with connection error (exit code 3)
            assert result.exit_code == 3
            assert 'connect' in result.output.lower()


class TestMultipleScansWorkflow:
    """Test importing multiple scans to same project"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_multiple_imports_same_project(self, runner, sample_nmap_xml):
        """Test importing multiple scans to the same project"""
        with runner.isolated_filesystem():
            # Import first scan
            with open('scan1.xml', 'w') as f:
                f.write(sample_nmap_xml)

            result1 = runner.invoke(import_scan, [
                'scan1.xml',
                '--project', 'multi-scan-project'
            ])
            assert result1.exit_code == 0

            # Import second scan (modified)
            modified_xml = sample_nmap_xml.replace('192.168.1.100', '192.168.1.200')
            with open('scan2.xml', 'w') as f:
                f.write(modified_xml)

            result2 = runner.invoke(import_scan, [
                'scan2.xml',
                '--project', 'multi-scan-project'
            ])
            assert result2.exit_code == 0

            # Check project status shows combined data
            status_result = runner.invoke(status, [
                '--project', 'multi-scan-project'
            ])

            assert status_result.exit_code == 0
            # Should show increased host count


class TestExportFormats:
    """Test different export formats"""

    @pytest.mark.skip(reason="Requires running backend API")
    def test_export_markdown_format(self, runner):
        """Test exporting in markdown format"""
        with runner.isolated_filesystem():
            result = runner.invoke(export, [
                'test-project',
                '--format', 'markdown',
                '--output', 'report.md'
            ])

            if result.exit_code == 0:
                assert Path('report.md').exists()
                content = Path('report.md').read_text()
                assert '#' in content  # Markdown heading

    @pytest.mark.skip(reason="Requires running backend API")
    def test_export_json_format(self, runner):
        """Test exporting in JSON format"""
        with runner.isolated_filesystem():
            result = runner.invoke(export, [
                'test-project',
                '--format', 'json',
                '--output', 'report.json'
            ])

            if result.exit_code == 0:
                assert Path('report.json').exists()
                content = Path('report.json').read_text()
                # Verify it's valid JSON
                data = json.loads(content)
                assert isinstance(data, dict)


class TestCLIHelp:
    """Test CLI help and documentation"""

    def test_main_help(self, runner):
        """Test main CLI help"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Hermes' in result.output

    def test_import_help(self, runner):
        """Test import command help"""
        result = runner.invoke(import_scan, ['--help'])
        assert result.exit_code == 0
        assert 'Import' in result.output

    def test_export_help(self, runner):
        """Test export command help"""
        result = runner.invoke(export, ['--help'])
        assert result.exit_code == 0
        assert 'Export' in result.output

    def test_config_help(self, runner):
        """Test config command help"""
        result = runner.invoke(cli, ['config', '--help'])
        assert result.exit_code == 0
        assert 'configuration' in result.output.lower()


# Fixtures for test database setup (if needed)
@pytest.fixture(scope='module')
def test_database():
    """
    Fixture to set up test database
    (Implementation depends on backend setup)
    """
    # Setup test database
    yield
    # Teardown test database


@pytest.fixture(scope='module')
def api_server():
    """
    Fixture to start test API server
    (Implementation depends on backend setup)
    """
    # Start test server
    yield
    # Stop test server
