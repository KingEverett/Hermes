# Testing Strategy

## Backend Testing

```python
# tests/test_parsers.py
import pytest
from services.parser import NmapXMLParser, ScanParserFactory

class TestNmapParser:
    @pytest.fixture
    def sample_nmap_xml(self):
        return """<?xml version="1.0"?>
        <nmaprun>
            <host>
                <address addr="192.168.1.1" addrtype="ipv4"/>
                <ports>
                    <port protocol="tcp" portid="22">
                        <service name="ssh" product="OpenSSH" version="7.4"/>
                    </port>
                </ports>
            </host>
        </nmaprun>"""
    
    def test_parse_valid_xml(self, sample_nmap_xml):
        parser = NmapXMLParser()
        assert parser.can_parse(sample_nmap_xml, "scan.xml")
        
        hosts = parser.parse(sample_nmap_xml)
        assert len(hosts) == 1
        assert hosts[0].ip_address == "192.168.1.1"
        assert len(hosts[0].services) == 1
        assert hosts[0].services[0].port == 22

    def test_parser_factory_selection(self):
        factory = ScanParserFactory()
        
        nmap_content = '<?xml version="1.0"?><nmaprun>'
        parser = factory.get_parser(nmap_content, "scan.xml")
        assert isinstance(parser, NmapXMLParser)
```

## Frontend Testing

```typescript
// tests/NetworkGraph.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { NetworkGraph } from '../components/visualization/NetworkGraph';

describe('NetworkGraph', () => {
  const mockNodes = [
    { id: 'host_1', type: 'host', label: '192.168.1.1', x: 0, y: 0 },
    { id: 'service_1', type: 'service', label: '22/tcp', x: 100, y: 0 }
  ];
  
  const mockEdges = [
    { source: 'host_1', target: 'service_1' }
  ];
  
  test('renders network nodes', () => {
    render(
      <NetworkGraph 
        nodes={mockNodes} 
        edges={mockEdges}
        onNodeSelect={jest.fn()} 
      />
    );
    
    expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
    expect(screen.getByText('22/tcp')).toBeInTheDocument();
  });
  
  test('calls onNodeSelect when node clicked', () => {
    const handleSelect = jest.fn();
    
    render(
      <NetworkGraph 
        nodes={mockNodes} 
        edges={mockEdges}
        onNodeSelect={handleSelect} 
      />
    );
    
    fireEvent.click(screen.getByText('192.168.1.1'));
    expect(handleSelect).toHaveBeenCalledWith(mockNodes[0]);
  });
});
```
