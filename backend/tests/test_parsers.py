import pytest
from parsers import ScanParser, ParsedHost, ParsedService, NmapXMLParser, ScanParserFactory
from parsers.base import CorruptedScanError, UnsupportedScanError, ScanParsingError


class TestNmapXMLParser:
    """Test cases for NmapXMLParser"""

    def setup_method(self):
        self.parser = NmapXMLParser()

    def test_can_parse_valid_nmap_xml(self):
        """Test parser can identify valid Nmap XML files"""
        content = '<?xml version="1.0"?><nmaprun scanner="nmap" version="7.94">'
        assert self.parser.can_parse(content, "scan.xml") is True

    def test_can_parse_rejects_non_xml(self):
        """Test parser rejects non-XML files"""
        content = "some text content"
        assert self.parser.can_parse(content, "scan.txt") is False

    def test_can_parse_rejects_non_nmap_xml(self):
        """Test parser rejects XML files that aren't Nmap"""
        content = '<?xml version="1.0"?><root><data>test</data></root>'
        assert self.parser.can_parse(content, "data.xml") is False

    def test_parse_simple_host(self):
        """Test parsing a simple host with one service"""
        xml_content = '''<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
    <host>
        <status state="up" reason="localhost-response"/>
        <address addr="192.168.1.100" addrtype="ipv4"/>
        <hostnames>
            <hostname name="testhost.local" type="PTR"/>
        </hostnames>
        <ports>
            <port protocol="tcp" portid="80">
                <state state="open" reason="syn-ack" reason_ttl="0"/>
                <service name="http" product="Apache httpd" version="2.4.41" conf="10"/>
            </port>
        </ports>
    </host>
</nmaprun>'''

        hosts = self.parser.parse(xml_content)

        assert len(hosts) == 1
        host = hosts[0]

        assert host.ip_address == "192.168.1.100"
        assert host.hostname == "testhost.local"
        assert host.status == "up"
        assert len(host.services) == 1

        service = host.services[0]
        assert service.port == 80
        assert service.protocol == "tcp"
        assert service.service_name == "http"
        assert service.product == "Apache httpd"
        assert service.version == "2.4.41"
        assert service.confidence == "high"  # conf=10 should map to high

    def test_parse_host_with_os_detection(self):
        """Test parsing host with OS detection"""
        xml_content = '''<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
    <host>
        <status state="up" reason="localhost-response"/>
        <address addr="192.168.1.101" addrtype="ipv4"/>
        <address addr="00:11:22:33:44:55" addrtype="mac"/>
        <os>
            <osmatch name="Linux 5.4" accuracy="95"/>
            <osmatch name="Ubuntu 20.04" accuracy="90"/>
        </os>
        <ports>
            <port protocol="tcp" portid="22">
                <state state="open" reason="syn-ack"/>
                <service name="ssh" product="OpenSSH" version="8.2" conf="8"/>
            </port>
        </ports>
    </host>
</nmaprun>'''

        hosts = self.parser.parse(xml_content)
        host = hosts[0]

        assert host.ip_address == "192.168.1.101"
        assert host.mac_address == "00:11:22:33:44:55"
        assert host.os_family == "Linux"
        assert host.os_details == "Linux 5.4"  # Should pick highest accuracy

    def test_parse_multiple_hosts(self):
        """Test parsing multiple hosts"""
        xml_content = '''<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
    <host>
        <status state="up"/>
        <address addr="192.168.1.100" addrtype="ipv4"/>
        <ports>
            <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http"/>
            </port>
        </ports>
    </host>
    <host>
        <status state="up"/>
        <address addr="192.168.1.101" addrtype="ipv4"/>
        <ports>
            <port protocol="tcp" portid="22">
                <state state="open"/>
                <service name="ssh"/>
            </port>
        </ports>
    </host>
</nmaprun>'''

        hosts = self.parser.parse(xml_content)

        assert len(hosts) == 2
        assert hosts[0].ip_address == "192.168.1.100"
        assert hosts[1].ip_address == "192.168.1.101"

    def test_parse_host_with_closed_ports(self):
        """Test that closed ports are filtered out"""
        xml_content = '''<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
    <host>
        <status state="up"/>
        <address addr="192.168.1.100" addrtype="ipv4"/>
        <ports>
            <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http"/>
            </port>
            <port protocol="tcp" portid="443">
                <state state="closed"/>
                <service name="https"/>
            </port>
        </ports>
    </host>
</nmaprun>'''

        hosts = self.parser.parse(xml_content)
        host = hosts[0]

        # Should only include open ports
        assert len(host.services) == 1
        assert host.services[0].port == 80

    def test_parse_corrupted_xml(self):
        """Test handling of corrupted XML"""
        corrupted_xml = '<?xml version="1.0"?><nmaprun><host><address addr="192.168.1.1"'

        with pytest.raises(CorruptedScanError):
            self.parser.parse(corrupted_xml)

    def test_parse_empty_content(self):
        """Test handling of empty content"""
        with pytest.raises(CorruptedScanError):
            self.parser.parse("")

    def test_parse_non_nmap_xml(self):
        """Test handling of non-Nmap XML"""
        xml_content = '<?xml version="1.0"?><root><data>test</data></root>'

        with pytest.raises(CorruptedScanError):
            self.parser.parse(xml_content)

    def test_os_family_extraction(self):
        """Test OS family extraction from various OS names"""
        parser = self.parser

        assert parser._extract_os_family_from_name("Microsoft Windows 10") == "Windows"
        assert parser._extract_os_family_from_name("Linux 5.4.0") == "Linux"
        assert parser._extract_os_family_from_name("FreeBSD 13.0") == "FreeBSD"
        assert parser._extract_os_family_from_name("Mac OS X 10.15") == "macOS"
        assert parser._extract_os_family_from_name("Unknown OS") == "Unknown"


class TestScanParserFactory:
    """Test cases for ScanParserFactory"""

    def setup_method(self):
        self.factory = ScanParserFactory()

    def test_get_parser_for_nmap_xml(self):
        """Test factory returns Nmap parser for XML files"""
        content = '<?xml version="1.0"?><nmaprun scanner="nmap">'
        parser = self.factory.get_parser(content, "scan.xml")

        assert isinstance(parser, NmapXMLParser)

    def test_get_parser_unsupported_format(self):
        """Test factory raises error for unsupported formats"""
        content = "some random text"

        with pytest.raises(UnsupportedScanError):
            self.factory.get_parser(content, "scan.txt")

    def test_get_parser_empty_content(self):
        """Test factory handles empty content"""
        with pytest.raises(UnsupportedScanError):
            self.factory.get_parser("", "scan.xml")

    def test_get_parser_no_filename(self):
        """Test factory handles missing filename"""
        content = '<?xml version="1.0"?><nmaprun>'

        with pytest.raises(UnsupportedScanError):
            self.factory.get_parser(content, "")

    def test_get_supported_formats(self):
        """Test factory returns supported formats"""
        formats = self.factory.get_supported_formats()

        assert len(formats) > 0
        assert any('Nmap XML' in fmt for fmt in formats)

    def test_parser_count(self):
        """Test factory reports correct parser count"""
        count = self.factory.get_parser_count()
        assert count >= 1  # At least Nmap parser

    def test_validate_parser_configuration(self):
        """Test factory configuration validation"""
        assert self.factory.validate_parser_configuration() is True


class TestParsedDataStructures:
    """Test the parsed data structures"""

    def test_parsed_service_creation(self):
        """Test ParsedService creation and defaults"""
        service = ParsedService(port=80, protocol="tcp")

        assert service.port == 80
        assert service.protocol == "tcp"
        assert service.confidence == "medium"  # Default value
        assert service.service_name is None

    def test_parsed_host_creation(self):
        """Test ParsedHost creation and defaults"""
        host = ParsedHost(ip_address="192.168.1.1")

        assert host.ip_address == "192.168.1.1"
        assert host.status == "up"  # Default value
        assert host.services == []  # Default empty list
        assert host.metadata == {}  # Default empty dict

    def test_parsed_host_with_services(self):
        """Test ParsedHost with services"""
        service = ParsedService(port=80, protocol="tcp", service_name="http")
        host = ParsedHost(ip_address="192.168.1.1", services=[service])

        assert len(host.services) == 1
        assert host.services[0].service_name == "http"


# Sample XML data for integration testing
SAMPLE_NMAP_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="nmap -sS -O 192.168.1.0/24" version="7.94" xmloutputversion="1.05">
    <scaninfo type="syn" protocol="tcp" numservices="1000" services="1,3-4,6-7,9,13,17,19-26,30,32-33"/>
    <verbose level="0"/>
    <debugging level="0"/>
    <host starttime="1635789600" endtime="1635789700">
        <status state="up" reason="localhost-response" reason_ttl="0"/>
        <address addr="192.168.1.100" addrtype="ipv4"/>
        <hostnames>
            <hostname name="webserver.local" type="PTR"/>
        </hostnames>
        <ports>
            <extraports state="closed" count="997">
                <extrareasons reason="resets" count="997"/>
            </extraports>
            <port protocol="tcp" portid="22">
                <state state="open" reason="syn-ack" reason_ttl="0"/>
                <service name="ssh" product="OpenSSH" version="8.2p1 Ubuntu 4ubuntu0.3" extrainfo="Ubuntu Linux; protocol 2.0" ostype="Linux" method="probes" conf="10">
                    <cpe>cpe:/a:openbsd:openssh:8.2p1</cpe>
                </service>
            </port>
            <port protocol="tcp" portid="80">
                <state state="open" reason="syn-ack" reason_ttl="0"/>
                <service name="http" product="Apache httpd" version="2.4.41" extrainfo="(Ubuntu)" method="probes" conf="10">
                    <cpe>cpe:/a:apache:http_server:2.4.41</cpe>
                </service>
            </port>
            <port protocol="tcp" portid="443">
                <state state="open" reason="syn-ack" reason_ttl="0"/>
                <service name="https" product="Apache httpd" version="2.4.41" tunnel="ssl" method="probes" conf="10">
                    <cpe>cpe:/a:apache:http_server:2.4.41</cpe>
                </service>
            </port>
        </ports>
        <os>
            <portused state="open" proto="tcp" portid="22"/>
            <portused state="closed" proto="tcp" portid="1"/>
            <portused state="closed" proto="udp" portid="31337"/>
            <osmatch name="Linux 5.4" accuracy="95" line="61504">
                <osclass type="general purpose" vendor="Linux" osfamily="Linux" osgen="5.X" accuracy="95">
                    <cpe>cpe:/o:linux:linux_kernel:5.4</cpe>
                </osclass>
            </osmatch>
            <osmatch name="Ubuntu 20.04" accuracy="90" line="61505">
                <osclass type="general purpose" vendor="Linux" osfamily="Linux" osgen="5.X" accuracy="90">
                    <cpe>cpe:/o:linux:linux_kernel</cpe>
                </osclass>
            </osmatch>
        </os>
        <uptime seconds="1425614" lastboot="Wed Oct 15 12:34:56 2021"/>
        <distance value="0"/>
        <tcpsequence index="260" difficulty="Good luck!" values="A1B2C3D4,E5F6A7B8,C9D0E1F2,F3A4B5C6,D7E8F9A0,B1C2D3E4"/>
        <ipidsequence class="All zeros" values="0,0,0,0,0,0"/>
        <tcptssequence class="1000HZ" values="1A2B3C4D,E5F6A7B8,C9D0E1F2"/>
    </host>
</nmaprun>'''


@pytest.fixture
def sample_nmap_xml():
    """Fixture providing sample Nmap XML for testing"""
    return SAMPLE_NMAP_XML


class TestNmapParserIntegration:
    """Integration tests with realistic Nmap XML data"""

    def test_parse_realistic_nmap_scan(self, sample_nmap_xml):
        """Test parsing realistic Nmap XML output"""
        parser = NmapXMLParser()
        hosts = parser.parse(sample_nmap_xml)

        assert len(hosts) == 1
        host = hosts[0]

        # Verify host information
        assert host.ip_address == "192.168.1.100"
        assert host.hostname == "webserver.local"
        assert host.os_family == "Linux"
        assert host.os_details == "Linux 5.4"
        assert host.status == "up"

        # Verify services
        assert len(host.services) == 3  # SSH, HTTP, HTTPS

        # Check SSH service
        ssh_service = next(s for s in host.services if s.port == 22)
        assert ssh_service.service_name == "ssh"
        assert ssh_service.product == "OpenSSH"
        assert ssh_service.version == "8.2p1 Ubuntu 4ubuntu0.3"
        assert ssh_service.confidence == "high"
        assert "cpe:/a:openbsd:openssh:8.2p1" in ssh_service.cpe

        # Check HTTP service
        http_service = next(s for s in host.services if s.port == 80)
        assert http_service.service_name == "http"
        assert http_service.product == "Apache httpd"
        assert http_service.version == "2.4.41"