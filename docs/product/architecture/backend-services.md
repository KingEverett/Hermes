# Backend Services

## Scan Parser Service
**Technology**: Python with XML/JSON parsing libraries
**Responsibilities**:
- Parse multiple scan formats (nmap XML, masscan JSON, dirb text, gobuster)
- Extract hosts, services, and initial vulnerability indicators
- Handle corrupted or partial files with graceful degradation
- Detect duplicate scans and merge data intelligently

**Implementation**:
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import xml.etree.ElementTree as ET
import json
import re

class ScanParser(ABC):
    @abstractmethod
    def can_parse(self, content: str, filename: str) -> bool:
        """Determine if this parser can handle the file"""
        pass
    
    @abstractmethod
    def parse(self, content: str) -> List[ParsedHost]:
        """Parse scan output into structured data"""
        pass

class NmapXMLParser(ScanParser):
    def can_parse(self, content: str, filename: str) -> bool:
        return filename.endswith('.xml') and '<nmaprun' in content[:1000]
    
    def parse(self, content: str) -> List[ParsedHost]:
        root = ET.fromstring(content)
        hosts = []
        
        for host_elem in root.findall('.//host'):
            # Extract host information
            ip_address = self._extract_ip(host_elem)
            hostname = self._extract_hostname(host_elem)
            os_info = self._extract_os(host_elem)
            services = self._extract_services(host_elem)
            
            hosts.append(ParsedHost(
                ip_address=ip_address,
                hostname=hostname,
                os_family=os_info.family,
                os_details=os_info.details,
                services=services
            ))
        
        return hosts

class ScanParserFactory:
    def __init__(self):
        self.parsers = [
            NmapXMLParser(),
            MasscanJSONParser(),
            DirbParser(),
            GobusterParser()
        ]
    
    def get_parser(self, content: str, filename: str) -> ScanParser:
        for parser in self.parsers:
            if parser.can_parse(content, filename):
                return parser
        raise ValueError(f"No suitable parser found for {filename}")
```

## Vulnerability Research Service
**Technology**: Python with async HTTP clients
**Responsibilities**:
- Integrate with NVD API for CVE enrichment
- Query CISA KEV for active exploitation data
- Generate ExploitDB search links
- Implement rate limiting and caching
- Provide fallback manual research links when APIs unavailable

**Implementation**:
```python
import asyncio
import httpx
from datetime import datetime, timedelta
import redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis, calls: int = 1, period: int = 6):
        self.redis = redis_client
        self.calls = calls
        self.period = period
    
    async def acquire(self):
        """Enforce NVD's 6-second rate limit"""
        key = f"ratelimit:nvd:{datetime.now().minute}"
        current = self.redis.incr(key)
        
        if current == 1:
            self.redis.expire(key, self.period)
        elif current > self.calls:
            await asyncio.sleep(self.period)
            await self.acquire()

class NVDService:
    def __init__(self, redis_client: redis.Redis):
        self.base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.rate_limiter = RateLimiter(redis_client)
        self.cache = redis_client
    
    async def get_cve_details(self, cve_id: str) -> CVEDetails:
        # Check cache first
        cached = self.cache.get(f"cve:{cve_id}")
        if cached:
            return CVEDetails.from_json(cached)
        
        # Rate limit and fetch
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={"cveId": cve_id}
            )
            
            if response.status_code == 200:
                details = self._parse_nvd_response(response.json())
                self.cache.setex(f"cve:{cve_id}", 86400, details.to_json())
                return details
            else:
                # Return manual research links
                return self._create_fallback_details(cve_id)
```

## Documentation Generation Service
**Technology**: Python with Jinja2 templates
**Responsibilities**:
- Generate markdown documentation from project data
- Support multiple export formats (PDF, HTML, CSV)
- Include network topology visualizations
- Create executive and technical report variants

**Implementation**:
```python
from jinja2 import Template
from typing import Dict, List
import markdown
from weasyprint import HTML

class DocumentationService:
    def __init__(self):
        self.markdown_template = self._load_template('markdown.j2')
    
    def generate_markdown(self, project_id: str) -> str:
        # Gather project data
        project_data = self._fetch_project_data(project_id)
        
        # Calculate statistics
        stats = {
            'host_count': len(project_data['hosts']),
            'service_count': sum(len(h['services']) for h in project_data['hosts']),
            'vulnerability_count': len(project_data['vulnerabilities']),
            'critical_count': len([v for v in project_data['vulnerabilities'] 
                                  if v['severity'] == 'critical'])
        }
        
        # Render template
        return self.markdown_template.render(
            project=project_data['project'],
            hosts=project_data['hosts'],
            vulnerabilities=project_data['vulnerabilities'],
            stats=stats,
            timestamp=datetime.now()
        )
    
    def export_pdf(self, markdown_content: str) -> bytes:
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        styled_html = f"""
        <html>
        <head>
            <style>{self._get_pdf_styles()}</style>
        </head>
        <body>{html_content}</body>
        </html>
        """
        
        return HTML(string=styled_html).write_pdf()
```

## Network Graph Service
**Technology**: Python with NetworkX
**Responsibilities**:
- Generate network topology from host/service data
- Calculate optimal graph layout
- Provide D3.js-compatible JSON output
- Support filtering and clustering for large networks

**Implementation**:
```python
import networkx as nx
from typing import Dict, List

class GraphService:
    def generate_topology(self, project_id: str) -> Dict:
        hosts = self._fetch_hosts(project_id)
        
        # Build graph
        G = nx.Graph()
        
        # Add host nodes
        for host in hosts:
            G.add_node(
                f"host_{host.id}",
                type='host',
                label=host.ip_address,
                os=host.os_family,
                status=host.status
            )
            
            # Add service nodes
            for service in host.services:
                service_id = f"service_{service.id}"
                G.add_node(
                    service_id,
                    type='service',
                    label=f"{service.port}/{service.protocol}",
                    name=service.service_name
                )
                G.add_edge(f"host_{host.id}", service_id)
        
        # Calculate layout
        if len(G.nodes) < 50:
            pos = nx.spring_layout(G, k=2, iterations=50)
        else:
            pos = nx.kamada_kawai_layout(G)
        
        # Convert to D3 format
        return {
            'nodes': [
                {
                    'id': node,
                    'x': pos[node][0] * 1000,
                    'y': pos[node][1] * 1000,
                    **G.nodes[node]
                }
                for node in G.nodes
            ],
            'edges': [
                {'source': u, 'target': v}
                for u, v in G.edges
            ]
        }
```
