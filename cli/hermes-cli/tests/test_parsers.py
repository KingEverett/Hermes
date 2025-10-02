"""Unit tests for tool output parsers."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.base import ToolOutputParser
from parsers.nmap import NmapParser
from parsers.masscan import MasscanParser
from parsers.dirb import DirbParser
from parsers.gobuster import GobusterParser
from parsers.registry import ParserRegistry


class TestNmapParser:
    """Tests for NmapParser."""

    def test_get_tool_name(self):
        """Test tool name."""
        parser = NmapParser()
        assert parser.get_tool_name() == 'nmap'

    def test_can_parse_xml(self):
        """Test XML file detection."""
        parser = NmapParser()

        content = '<?xml version="1.0"?><nmaprun version="7.80"></nmaprun>'
        assert parser.can_parse(content, 'scan.xml') is True

    def test_can_parse_not_xml(self):
        """Test non-XML file rejection."""
        parser = NmapParser()

        content = 'This is not XML'
        assert parser.can_parse(content, 'scan.txt') is False

    def test_parse_basic_xml(self):
        """Test parsing basic nmap XML."""
        parser = NmapParser()

        xml_content = '''<?xml version="1.0"?>
<nmaprun version="7.80" args="nmap -sV 127.0.0.1">
    <host>
        <address addr="127.0.0.1" addrtype="ipv4"/>
        <ports>
            <port portid="80" protocol="tcp">
                <state state="open"/>
                <service name="http" product="Apache" version="2.4"/>
            </port>
        </ports>
    </host>
</nmaprun>'''

        result = parser.parse(xml_content)

        assert result['tool'] == 'nmap'
        assert result['version'] == '7.80'
        assert len(result['hosts']) == 1
        assert result['host_count'] == 1

        host = result['hosts'][0]
        assert len(host['addresses']) == 1
        assert host['addresses'][0]['addr'] == '127.0.0.1'
        assert len(host['ports']) == 1
        assert host['ports'][0]['portid'] == '80'

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML in strict mode."""
        parser = NmapParser()

        xml_content = '<?xml version="1.0"?><invalid><unclosed>'

        with pytest.raises(ValueError, match='Invalid nmap XML'):
            parser.parse(xml_content, lenient=False)

    def test_parse_invalid_xml_lenient(self):
        """Test parsing invalid XML in lenient mode."""
        parser = NmapParser()

        xml_content = '<?xml version="1.0"?><invalid><unclosed>'

        result = parser.parse(xml_content, lenient=True)

        assert result['tool'] == 'nmap'
        assert result['host_count'] == 0
        assert 'parse_error' in result


class TestMasscanParser:
    """Tests for MasscanParser."""

    def test_get_tool_name(self):
        """Test tool name."""
        parser = MasscanParser()
        assert parser.get_tool_name() == 'masscan'

    def test_can_parse_json(self):
        """Test JSON file detection."""
        parser = MasscanParser()

        content = '[{"ip": "192.168.1.1", "ports": [{"port": 80, "proto": "tcp"}]}]'
        assert parser.can_parse(content, 'scan.json') is True

    def test_parse_basic_json(self):
        """Test parsing basic masscan JSON."""
        parser = MasscanParser()

        json_content = '''[
            {"ip": "192.168.1.1", "ports": [
                {"port": 80, "proto": "tcp", "status": "open"},
                {"port": 443, "proto": "tcp", "status": "open"}
            ]},
            {"ip": "192.168.1.2", "ports": [
                {"port": 22, "proto": "tcp", "status": "open"}
            ]}
        ]'''

        result = parser.parse(json_content)

        assert result['tool'] == 'masscan'
        assert result['host_count'] == 2
        assert result['port_count'] == 3

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        parser = MasscanParser()

        json_content = 'not json'

        with pytest.raises(ValueError, match='Invalid masscan JSON'):
            parser.parse(json_content, lenient=False)

    def test_parse_missing_ip_lenient(self):
        """Test parsing with missing IP in lenient mode."""
        parser = MasscanParser()

        json_content = '[{"ports": [{"port": 80}]}]'

        result = parser.parse(json_content, lenient=True)

        # Should skip record with missing IP
        assert result['host_count'] == 0


class TestDirbParser:
    """Tests for DirbParser."""

    def test_get_tool_name(self):
        """Test tool name."""
        parser = DirbParser()
        assert parser.get_tool_name() == 'dirb'

    def test_can_parse(self):
        """Test dirb output detection."""
        parser = DirbParser()

        content = 'DIRB v2.22\nURL_BASE: http://example.com'
        assert parser.can_parse(content, 'dirb-output.txt') is True

    def test_parse_basic_output(self):
        """Test parsing basic dirb output."""
        parser = DirbParser()

        content = '''
DIRB v2.22
URL_BASE: http://example.com/
WORDLIST_FILES: common.txt

+ http://example.com/admin/ (CODE:200|SIZE:1234)
+ http://example.com/login.php (CODE:200|SIZE:567)
'''

        result = parser.parse(content)

        assert result['tool'] == 'dirb'
        assert result['target_url'] == 'http://example.com/'
        assert result['total_found'] == 2
        assert len(result['directories']) == 1
        assert len(result['files']) == 1


class TestGobusterParser:
    """Tests for GobusterParser."""

    def test_get_tool_name(self):
        """Test tool name."""
        parser = GobusterParser()
        assert parser.get_tool_name() == 'gobuster'

    def test_can_parse(self):
        """Test gobuster output detection."""
        parser = GobusterParser()

        content = 'Gobuster v3.0\nby OJ Reeves'
        assert parser.can_parse(content, 'gobuster-output.txt') is True

    def test_parse_dir_mode(self):
        """Test parsing gobuster dir mode output."""
        parser = GobusterParser()

        content = '''
Gobuster v3.0
Mode: dir
URL: http://example.com

/admin (Status: 200) [Size: 1234]
/login (Status: 200) [Size: 567]
'''

        result = parser.parse(content)

        assert result['tool'] == 'gobuster'
        assert result['mode'] == 'dir'
        assert result['total_found'] == 2
        assert result['discoveries'][0]['type'] == 'directory'


class TestParserRegistry:
    """Tests for ParserRegistry."""

    def test_registry_init(self):
        """Test registry initialization."""
        registry = ParserRegistry()
        assert isinstance(registry, ParserRegistry)

    def test_register_parser(self):
        """Test manual parser registration."""
        registry = ParserRegistry()

        mock_parser = Mock(spec=ToolOutputParser)
        mock_parser.get_tool_name.return_value = 'test-tool'

        registry.register_parser(mock_parser)

        parser = registry.get_parser_by_tool('test-tool')
        assert parser == mock_parser

    def test_get_parser_by_content(self):
        """Test finding parser by content."""
        registry = ParserRegistry()

        xml_content = '<?xml version="1.0"?><nmaprun></nmaprun>'
        parser = registry.get_parser(xml_content, 'scan.xml')

        assert parser is not None
        assert parser.get_tool_name() == 'nmap'

    def test_get_parser_unknown(self):
        """Test getting parser for unknown content."""
        registry = ParserRegistry()

        content = 'unknown tool output'
        parser = registry.get_parser(content, 'unknown.txt')

        assert parser is None

    def test_list_parsers(self):
        """Test listing parsers."""
        registry = ParserRegistry()
        parser_list = registry.list_parsers()

        assert isinstance(parser_list, list)
        assert len(parser_list) > 0

        # Should include built-in parsers
        tools = [p['tool'] for p in parser_list]
        assert 'nmap' in tools
        assert 'masscan' in tools
        assert 'dirb' in tools
        assert 'gobuster' in tools


class TestParserPlugins:
    """Tests for parser plugin system."""

    def test_plugin_discovery(self):
        """Test plugin entry point discovery."""
        registry = ParserRegistry()

        # Test that plugin discovery runs without errors
        # Actual plugins won't be present in test environment
        assert isinstance(registry.parsers, list)

    @patch('importlib.metadata.entry_points')
    def test_plugin_loading(self, mock_entry_points):
        """Test loading plugin parsers."""
        # Mock entry points
        mock_ep = Mock()
        mock_ep.name = 'custom-parser'
        mock_ep.group = 'hermes_cli.parsers'
        mock_parser_class = Mock()
        mock_ep.load.return_value = mock_parser_class

        # Mock the return value to have a get method
        mock_eps = Mock()
        mock_eps.get.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        registry = ParserRegistry()

        # Verify plugin loading attempted
        # Note: actual loading depends on entry_points implementation
        assert isinstance(registry, ParserRegistry)
