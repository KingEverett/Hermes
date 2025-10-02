"""Unit tests for tool wrappers."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrappers.base import ToolWrapper
from wrappers.nmap import NmapWrapper
from wrappers.masscan import MasscanWrapper
from wrappers.web_enum import DirbWrapper, GobusterWrapper
from wrappers.registry import WrapperRegistry


class TestToolWrapper:
    """Tests for base ToolWrapper class."""

    def test_init(self, tmp_path):
        """Test wrapper initialization."""
        mock_client = Mock()
        wrapper = NmapWrapper(project_id='test-project', api_client=mock_client)

        assert wrapper.project_id == 'test-project'
        assert wrapper.api_client == mock_client
        assert wrapper.output_dir == Path.home() / '.hermes' / 'scans'

    def test_get_tool_path(self):
        """Test tool path discovery."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        # Should use shutil.which
        with patch('wrappers.base.shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/nmap'
            path = wrapper.get_tool_path()
            assert path == '/usr/bin/nmap'
            mock_which.assert_called_once_with('nmap')

    def test_get_tool_path_not_found(self):
        """Test tool not found."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        with patch('wrappers.base.shutil.which', return_value=None):
            path = wrapper.get_tool_path()
            assert path is None

    def test_execute_tool_not_found(self):
        """Test execute with tool not found."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        with patch('wrappers.base.shutil.which', return_value=None):
            with pytest.raises(FileNotFoundError, match='nmap not found'):
                wrapper.execute_tool(['-sV', '127.0.0.1'])

    def test_execute_tool_dry_run(self):
        """Test dry run mode."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        with patch('wrappers.base.shutil.which', return_value='/usr/bin/nmap'):
            result = wrapper.execute_tool(['-sV', '127.0.0.1'], dry_run=True)

            assert result['status'] == 'dry_run'
            assert 'command' in result
            assert 'nmap' in result['command']


class TestNmapWrapper:
    """Tests for NmapWrapper."""

    def test_get_tool_name(self):
        """Test tool name."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())
        assert wrapper.get_tool_name() == 'nmap'

    def test_prepare_arguments_auto_add_xml(self):
        """Test automatic XML output addition."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        args = ['-sV', '-p-', '192.168.1.1']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should add -oX flag
        assert '-oX' in modified_args
        assert output_file.name.startswith('test-')
        assert output_file.suffix == '.xml'

        # Original args should be preserved
        assert '-sV' in modified_args
        assert '-p-' in modified_args
        assert '192.168.1.1' in modified_args

    def test_prepare_arguments_user_xml(self):
        """Test with user-specified XML output."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        args = ['-sV', '-oX', 'my-scan.xml', '192.168.1.1']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should use user's file
        assert output_file.name == 'my-scan.xml'
        # Should not add another -oX
        assert modified_args.count('-oX') == 1

    def test_prepare_arguments_all_formats(self):
        """Test with -oA (all formats)."""
        wrapper = NmapWrapper(project_id='test', api_client=Mock())

        args = ['-sV', '-oA', 'scan-output', '192.168.1.1']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should extract XML file from -oA
        assert output_file.name == 'scan-output.xml'


class TestMasscanWrapper:
    """Tests for MasscanWrapper."""

    def test_get_tool_name(self):
        """Test tool name."""
        wrapper = MasscanWrapper(project_id='test', api_client=Mock())
        assert wrapper.get_tool_name() == 'masscan'

    def test_prepare_arguments_auto_add_json(self):
        """Test automatic JSON output addition."""
        wrapper = MasscanWrapper(project_id='test', api_client=Mock())

        args = ['-p1-65535', '10.0.0.0/8', '--rate', '10000']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should add -oJ flag
        assert '-oJ' in modified_args
        assert output_file.name.startswith('test-')
        assert output_file.suffix == '.json'

    def test_prepare_arguments_user_json(self):
        """Test with user-specified JSON output."""
        wrapper = MasscanWrapper(project_id='test', api_client=Mock())

        args = ['-p80,443', '-oJ', 'results.json', '192.168.1.0/24']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should use user's file
        assert output_file.name == 'results.json'
        # Should not add another -oJ
        assert modified_args.count('-oJ') == 1

    def test_batch_size(self):
        """Test custom batch size."""
        wrapper = MasscanWrapper(project_id='test', api_client=Mock(), batch_size=5000)
        assert wrapper.batch_size == 5000


class TestWebEnumWrappers:
    """Tests for web enumeration wrappers."""

    def test_dirb_get_tool_name(self):
        """Test dirb tool name."""
        wrapper = DirbWrapper(project_id='test', api_client=Mock())
        assert wrapper.get_tool_name() == 'dirb'

    def test_dirb_prepare_arguments(self):
        """Test dirb argument preparation."""
        wrapper = DirbWrapper(project_id='test', api_client=Mock())

        args = ['http://target.com', '/usr/share/wordlists/dirb/common.txt']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should add -o flag
        assert '-o' in modified_args
        assert output_file.name.startswith('test-')
        assert output_file.name.endswith('-dirb.txt')

    def test_gobuster_get_tool_name(self):
        """Test gobuster tool name."""
        wrapper = GobusterWrapper(project_id='test', api_client=Mock())
        assert wrapper.get_tool_name() == 'gobuster'

    def test_gobuster_prepare_arguments(self):
        """Test gobuster argument preparation."""
        wrapper = GobusterWrapper(project_id='test', api_client=Mock())

        args = ['dir', '-u', 'http://target.com', '-w', 'wordlist.txt']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should add -o flag
        assert '-o' in modified_args
        assert output_file.name.startswith('test-')
        assert output_file.name.endswith('-gobuster.txt')

    def test_gobuster_long_form_output(self):
        """Test gobuster with --output flag."""
        wrapper = GobusterWrapper(project_id='test', api_client=Mock())

        args = ['dir', '-u', 'http://target.com', '--output', 'results.txt']
        modified_args, output_file = wrapper.prepare_arguments(args)

        # Should use user's file
        assert output_file.name == 'results.txt'


class TestWrapperRegistry:
    """Tests for WrapperRegistry."""

    def test_registry_init(self):
        """Test registry initialization."""
        registry = WrapperRegistry()
        assert isinstance(registry, WrapperRegistry)

    def test_register_wrapper(self):
        """Test manual wrapper registration."""
        registry = WrapperRegistry()
        registry.register_wrapper('test-tool', Mock)

        wrapper_class = registry.get_wrapper_class('test-tool')
        assert wrapper_class == Mock

    def test_list_wrappers(self):
        """Test listing wrappers."""
        registry = WrapperRegistry()
        wrappers = registry.list_wrappers()

        # Should include built-in wrappers
        assert isinstance(wrappers, list)
        assert 'nmap' in wrappers
        assert 'masscan' in wrappers
        assert 'dirb' in wrappers
        assert 'gobuster' in wrappers

    def test_get_unknown_wrapper(self):
        """Test getting unknown wrapper."""
        registry = WrapperRegistry()
        wrapper_class = registry.get_wrapper_class('unknown-tool')
        assert wrapper_class is None
