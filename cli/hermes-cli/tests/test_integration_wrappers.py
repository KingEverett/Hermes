"""Integration tests for tool wrappers.

These tests require actual tool binaries (nmap, masscan, etc.) to be installed.
They can be skipped in CI/CD or marked with pytest.mark.integration.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrappers.nmap import NmapWrapper
from wrappers.masscan import MasscanWrapper
from wrappers.web_enum import GobusterWrapper

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.requires_tools(['nmap'])
class TestNmapIntegration:
    """Integration tests for nmap wrapper."""

    @pytest.mark.skipif(not os.path.exists('/usr/bin/nmap'), reason="nmap not installed")
    def test_nmap_version(self):
        """Test nmap is installed and accessible."""
        import subprocess
        result = subprocess.run(['nmap', '--version'], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'Nmap' in result.stdout

    def test_nmap_dry_run(self):
        """Test nmap wrapper in dry-run mode."""
        mock_client = Mock()
        wrapper = NmapWrapper(project_id='test', api_client=mock_client)

        # Dry run doesn't require nmap to be installed
        result = wrapper.execute_tool(['-sV', '127.0.0.1'], dry_run=True)

        assert result['status'] == 'dry_run'
        assert 'nmap' in result['command']
        assert '-sV' in result['command']


@pytest.mark.requires_tools(['masscan'])
class TestMasscanIntegration:
    """Integration tests for masscan wrapper."""

    @pytest.mark.skipif(not os.path.exists('/usr/bin/masscan') and not os.path.exists('/usr/local/bin/masscan'),
                       reason="masscan not installed")
    def test_masscan_version(self):
        """Test masscan is installed and accessible."""
        import subprocess
        result = subprocess.run(['masscan', '--version'], capture_output=True, text=True)
        # masscan returns version in stderr
        assert 'Masscan' in result.stdout or 'Masscan' in result.stderr

    def test_masscan_dry_run(self):
        """Test masscan wrapper in dry-run mode."""
        mock_client = Mock()
        wrapper = MasscanWrapper(project_id='test', api_client=mock_client)

        result = wrapper.execute_tool(['-p80,443', '127.0.0.1'], dry_run=True)

        assert result['status'] == 'dry_run'
        assert 'masscan' in result['command']
        assert '-p80,443' in result['command']


@pytest.mark.requires_tools(['gobuster'])
class TestGobusterIntegration:
    """Integration tests for gobuster wrapper."""

    @pytest.mark.skipif(not os.path.exists('/usr/bin/gobuster') and not os.path.exists('/usr/local/bin/gobuster'),
                       reason="gobuster not installed")
    def test_gobuster_version(self):
        """Test gobuster is installed and accessible."""
        import subprocess
        result = subprocess.run(['gobuster', 'version'], capture_output=True, text=True)
        assert result.returncode == 0

    def test_gobuster_dry_run(self):
        """Test gobuster wrapper in dry-run mode."""
        mock_client = Mock()
        wrapper = GobusterWrapper(project_id='test', api_client=mock_client)

        result = wrapper.execute_tool(
            ['dir', '-u', 'http://example.com', '-w', '/tmp/wordlist.txt'],
            dry_run=True
        )

        assert result['status'] == 'dry_run'
        assert 'gobuster' in result['command']


class TestWrapperImportFlow:
    """Test the full wrapper workflow with mocked API."""

    def test_wrapper_import_flow(self, tmp_path):
        """Test wrapper execution with mocked import."""
        mock_client = Mock()
        mock_client.import_scan.return_value = {
            'scan_id': 'test-scan-id',
            'status': 'success',
            'host_count': 5,
            'service_count': 15
        }

        wrapper = NmapWrapper(project_id='test', api_client=mock_client)

        # Create a fake output file
        output_file = tmp_path / "test-scan.xml"
        output_file.write_text('<?xml version="1.0"?><nmaprun></nmaprun>')

        # Mock the wrapper to use our test file
        with patch.object(wrapper, 'prepare_arguments', return_value=(['-sV'], output_file)):
            with patch('wrappers.base.shutil.which', return_value='/usr/bin/nmap'):
                with patch('wrappers.base.subprocess.Popen') as mock_popen:
                    # Mock successful scan execution
                    mock_process = Mock()
                    mock_process.stdout = iter(['Scanning...\n', 'Done.\n'])
                    mock_process.wait.return_value = 0
                    mock_popen.return_value = mock_process

                    result = wrapper.execute_tool(['-sV'], auto_import=True)

                    # Should have imported
                    assert 'scan_id' in result
                    assert result['scan_id'] == 'test-scan-id'
                    mock_client.import_scan.assert_called_once()
