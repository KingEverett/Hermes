# Hermes - MVP Architecture Document

## Introduction

Hermes is an intelligent pentesting documentation platform designed to eliminate the 40-60% of assessment time that security professionals spend on manual documentation and research tasks. This architecture document outlines a pragmatic implementation optimized for individual pentesters and small teams, with a clear evolution path to enterprise deployments.

### Project Scope
- **Primary Goal**: Automate scan parsing, vulnerability research, and documentation generation
- **Scale Target**: Individual researchers to teams of 2-6 pentesters
- **Distribution Model**: Free, open-source, self-hosted
- **Deployment Model**: Docker Compose with optional Kubernetes migration path

## High Level Architecture

### Technical Summary
Hermes employs a service-oriented architecture within a monorepo structure, balancing modularity with deployment simplicity. The system prioritizes immediate value delivery through intelligent automation while maintaining flexibility for future enterprise evolution.

### Platform Choice
**Self-Hosted Docker Deployment**
- Docker Compose orchestration for simplicity
- No external cloud dependencies for security compliance
- Local-first data processing
- Optional air-gap deployment capability

### Repository Structure
**Monorepo Architecture**
```
hermes/
├── backend/
│   ├── api/
│   ├── services/
│   │   ├── parser/
│   │   ├── research/
│   │   └── documentation/
│   ├── models/
│   ├── repositories/
│   └── workers/
├── frontend/
│   └── web-app/
├── cli/
│   └── hermes-cli/
├── shared/
│   ├── types/
│   └── database/
└── infrastructure/
    ├── docker/
    └── scripts/
```

### Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface Layer"
        WEB[Web Application<br/>React + TypeScript]
        CLI[CLI Tool<br/>Python Click]
    end

    subgraph "API Layer"
        API[REST API<br/>FastAPI]
        WS[WebSocket Handler<br/>FastAPI WebSocket]
    end

    subgraph "Service Layer"
        PARSER[Parser Service<br/>Scan Processing]
        RESEARCH[Research Service<br/>CVE Enrichment]
        DOC[Documentation Service<br/>Report Generation]
        GRAPH[Graph Service<br/>Network Topology]
    end

    subgraph "Background Processing"
        CELERY[Celery Workers<br/>Async Tasks]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL/SQLite<br/>Primary Database)]
        REDIS[(Redis<br/>Cache + Queue)]
        FS[(Local Filesystem<br/>Scan Files)]
    end

    subgraph "External APIs"
        NVD[NVD API]
        CISA[CISA KEV]
        EXPLOIT[ExploitDB]
    end

    WEB --> API
    CLI --> API
    WEB --> WS
    
    API --> PARSER
    API --> RESEARCH
    API --> DOC
    API --> GRAPH
    
    PARSER --> CELERY
    RESEARCH --> CELERY
    
    CELERY --> PG
    CELERY --> REDIS
    
    RESEARCH --> NVD
    RESEARCH --> CISA
    RESEARCH --> EXPLOIT
    
    DOC --> FS
```

### Architectural Patterns
- **Service-Oriented Architecture**: Logical separation without deployment complexity
- **Repository Pattern**: Clean data access abstraction
- **Factory Pattern**: Extensible scan parser system
- **Event-Driven Processing**: Background tasks for heavy operations
- **Progressive Enhancement**: Simple MVP to team collaboration

## Technology Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| **Backend Framework** | FastAPI | 0.104+ | High performance, automatic OpenAPI, async support |
| **Frontend Framework** | React | 18+ | Component ecosystem, TypeScript support |
| **Language (Backend)** | Python | 3.11+ | Security tool ecosystem, rapid development |
| **Language (Frontend)** | TypeScript | 5.0+ | Type safety, developer experience |
| **Database (Dev)** | SQLite | 3.35+ | Zero configuration, embedded |
| **Database (Prod)** | PostgreSQL | 15+ | Scalability, concurrent access |
| **Cache/Queue** | Redis | 7.0+ | Task queue, caching, real-time |
| **File Storage** | Local FS | - | Security compliance, no cloud dependencies |
| **Container Runtime** | Docker | 24.0+ | Universal deployment |
| **Task Queue** | Celery | 5.3+ | Background processing |
| **CLI Framework** | Click | 8.1+ | Pythonic CLI development |
| **Graph Visualization** | D3.js | 7.0+ | Network topology rendering |
| **CSS Framework** | Tailwind CSS | 3.0+ | Utility-first, dark theme support |
| **State Management** | Zustand + React Query | Latest | Lightweight, TypeScript-first |

## Data Models

### Core Entities

```typescript
interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: Date;
  updated_at: Date;
  metadata: ProjectMetadata;
}

interface Scan {
  id: string;
  project_id: string;
  filename: string;
  tool_type: ScanToolType; // 'nmap' | 'masscan' | 'dirb' | 'gobuster'
  status: ScanStatus; // 'pending' | 'parsing' | 'completed' | 'failed'
  raw_content?: string;
  parsed_at?: Date;
  error_details?: string;
  processing_time_ms?: number;
  created_at: Date;
}

interface Host {
  id: string;
  project_id: string;
  ip_address: string;
  hostname?: string;
  os_family?: string;
  os_details?: string;
  mac_address?: string;
  status: HostStatus; // 'up' | 'down' | 'filtered'
  confidence_score?: number;
  first_seen: Date;
  last_seen: Date;
  metadata: HostMetadata;
}

interface Service {
  id: string;
  host_id: string;
  port: number;
  protocol: Protocol; // 'tcp' | 'udp'
  service_name?: string;
  product?: string;
  version?: string;
  banner?: string;
  cpe?: string;
  confidence: ConfidenceLevel; // 'high' | 'medium' | 'low'
  created_at: Date;
}

interface Vulnerability {
  id: string;
  cve_id?: string;
  cvss_score?: number;
  severity: Severity; // 'critical' | 'high' | 'medium' | 'low' | 'info'
  description: string;
  remediation?: string;
  exploit_available: boolean;
  references: Reference[];
  cisa_kev: boolean;
  published_date?: Date;
  created_at: Date;
  updated_at: Date;
}

interface ServiceVulnerability {
  service_id: string;
  vulnerability_id: string;
  confidence: ConfidenceLevel;
  validated: boolean;
  validation_method?: ValidationMethod;
  notes?: string;
  identified_at: Date;
}

interface ResearchTask {
  id: string;
  project_id: string;
  target_type: TargetType; // 'service' | 'vulnerability' | 'host'
  target_id: string;
  status: TaskStatus; // 'queued' | 'processing' | 'completed' | 'failed'
  source: ResearchSource; // 'nvd' | 'exploitdb' | 'cisa' | 'manual'
  results?: any;
  error_message?: string;
  retry_count: number;
  created_at: Date;
  completed_at?: Date;
}

interface Note {
  id: string;
  project_id: string;
  entity_type: EntityType; // 'host' | 'service' | 'vulnerability'
  entity_id: string;
  content: string;
  author?: string;
  tags: string[];
  created_at: Date;
  updated_at: Date;
}

interface ExportJob {
  id: string;
  project_id: string;
  format: ExportFormat; // 'markdown' | 'pdf' | 'json' | 'csv'
  status: JobStatus;
  file_path?: string;
  created_at: Date;
  completed_at?: Date;
}
```

## API Specification

### REST API Endpoints

```yaml
openapi: 3.0.3
info:
  title: Hermes Pentesting Documentation API
  version: 1.0.0
  description: Intelligent pentesting documentation automation platform

servers:
  - url: http://localhost:8000/api/v1
    description: Local development server

paths:
  # Projects
  /projects:
    get:
      summary: List all projects
      responses:
        '200':
          description: List of projects
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Project'
    post:
      summary: Create new project
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateProjectRequest'
      responses:
        '201':
          description: Project created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Project'

  # Scan Import
  /projects/{project_id}/scans/import:
    post:
      summary: Import scan file
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                tool_type:
                  type: string
                  enum: [auto, nmap, masscan, dirb, gobuster]
      responses:
        '202':
          description: Import started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScanImportResponse'

  # Hosts
  /projects/{project_id}/hosts:
    get:
      summary: List project hosts
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
            enum: [up, down, filtered]
      responses:
        '200':
          description: List of hosts
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Host'

  # Services
  /hosts/{host_id}/services:
    get:
      summary: List host services
      parameters:
        - name: host_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: List of services
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Service'

  # Vulnerabilities
  /projects/{project_id}/vulnerabilities:
    get:
      summary: List project vulnerabilities
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
        - name: severity
          in: query
          schema:
            type: string
            enum: [critical, high, medium, low, info]
      responses:
        '200':
          description: List of vulnerabilities
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Vulnerability'

  # Research
  /services/{service_id}/research:
    post:
      summary: Trigger vulnerability research
      parameters:
        - name: service_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '202':
          description: Research task queued
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResearchTask'

  # Network Topology
  /projects/{project_id}/topology:
    get:
      summary: Get network topology data
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Network topology graph data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NetworkTopology'

  # Export
  /projects/{project_id}/export:
    post:
      summary: Export project documentation
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                format:
                  type: string
                  enum: [markdown, pdf, json, csv]
      responses:
        '202':
          description: Export job created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExportJob'
```

### WebSocket Events

```typescript
// Real-time updates for scan processing and research
interface WebSocketEvents {
  // Scan processing events
  'scan.import.started': { scan_id: string; filename: string };
  'scan.import.progress': { scan_id: string; percentage: number };
  'scan.import.completed': { scan_id: string; stats: ImportStats };
  'scan.import.failed': { scan_id: string; error: string };
  
  // Research events
  'research.started': { task_id: string; target: string };
  'research.completed': { task_id: string; results: ResearchResults };
  'research.failed': { task_id: string; error: string };
  
  // Discovery events
  'host.discovered': { host_id: string; ip_address: string };
  'service.discovered': { service_id: string; port: number; name: string };
  'vulnerability.identified': { vuln_id: string; severity: string };
}
```

## Backend Services

### Scan Parser Service
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

### Vulnerability Research Service
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

### Documentation Generation Service
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

### Network Graph Service
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

## CLI Tool Implementation

### Command Structure

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

### Implementation

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

## Frontend Architecture

### React Application Structure

```
frontend/web-app/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── ThreePanelLayout.tsx
│   │   │   ├── LeftSidebar.tsx
│   │   │   └── RightPanel.tsx
│   │   ├── visualization/
│   │   │   ├── NetworkGraph.tsx
│   │   │   └── GraphControls.tsx
│   │   ├── scan/
│   │   │   ├── ScanImport.tsx
│   │   │   └── ScanProgress.tsx
│   │   └── common/
│   │       └── DataTable.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ProjectView.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useNetworkData.ts
│   ├── services/
│   │   └── api.ts
│   ├── stores/
│   │   └── projectStore.ts
│   └── App.tsx
└── package.json
```

### Three-Panel Layout Implementation

```typescript
import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

export const ThreePanelLayout: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState(null);
  
  return (
    <div className="h-screen bg-gray-900 text-gray-100">
      <PanelGroup direction="horizontal">
        {/* Left Sidebar - Navigation */}
        <Panel defaultSize={15} minSize={10} maxSize={25}>
          <div className="h-full bg-gray-800 border-r border-gray-700 p-4">
            <ProjectBrowser />
            <ScanHistory />
            <FilterPanel />
          </div>
        </Panel>
        
        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600" />
        
        {/* Center - Network Visualization */}
        <Panel defaultSize={60}>
          <div className="h-full relative">
            <NetworkGraph onNodeSelect={setSelectedNode} />
            <GraphControls />
          </div>
        </Panel>
        
        <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-600" />
        
        {/* Right Panel - Context Information */}
        <Panel defaultSize={25} minSize={15} maxSize={40}>
          <div className="h-full bg-gray-800 border-l border-gray-700 p-4">
            {selectedNode ? (
              <NodeDetails node={selectedNode} />
            ) : (
              <ProjectSummary />
            )}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
};
```

### Network Visualization Component

```typescript
import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { useNetworkData } from '../hooks/useNetworkData';

export const NetworkGraph: React.FC<{ onNodeSelect: (node: any) => void }> = ({ 
  onNodeSelect 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { nodes, edges } = useNetworkData();
  
  useEffect(() => {
    if (!svgRef.current || !nodes.length) return;
    
    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;
    
    // Clear previous render
    svg.selectAll('*').remove();
    
    // Create zoom container
    const g = svg.append('g');
    
    // Setup zoom
    const zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    
    svg.call(zoom);
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Draw edges
    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .enter().append('line')
      .attr('stroke', '#4B5563')
      .attr('stroke-width', 2);
    
    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')
      .on('click', (event, d) => onNodeSelect(d))
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));
    
    // Node circles with severity-based colors
    node.append('circle')
      .attr('r', d => d.type === 'host' ? 20 : 15)
      .attr('fill', d => {
        if (d.type === 'host') return '#3B82F6';
        if (d.vulnerabilities?.some(v => v.severity === 'critical')) return '#DC2626';
        if (d.vulnerabilities?.some(v => v.severity === 'high')) return '#F59E0B';
        return '#10B981';
      });
    
    // Node labels
    node.append('text')
      .attr('dy', 30)
      .attr('text-anchor', 'middle')
      .attr('fill', '#D1D5DB')
      .style('font-size', '12px')
      .text(d => d.label);
    
    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    function dragStarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragEnded(event, d) {
      if (!event.active) simulation.alphaTarget(0);
    }
    
  }, [nodes, edges]);
  
  return <svg ref={svgRef} className="w-full h-full" />;
};
```

## Database Schema

### PostgreSQL/SQLite Database Design

```sql
-- Projects table (root entity)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Scans table
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    tool_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    raw_content TEXT,
    parsed_at TIMESTAMP,
    error_details TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hosts table
CREATE TABLE hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    ip_address INET NOT NULL,
    hostname VARCHAR(255),
    os_family VARCHAR(100),
    os_details TEXT,
    mac_address MACADDR,
    status VARCHAR(50) DEFAULT 'up',
    confidence_score FLOAT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(project_id, ip_address)
);

-- Services table
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID REFERENCES hosts(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    protocol VARCHAR(10) NOT NULL,
    service_name VARCHAR(100),
    product VARCHAR(255),
    version VARCHAR(100),
    banner TEXT,
    cpe VARCHAR(255),
    confidence VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(host_id, port, protocol)
);

-- Vulnerabilities table
CREATE TABLE vulnerabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cve_id VARCHAR(20),
    cvss_score DECIMAL(3,1),
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    remediation TEXT,
    exploit_available BOOLEAN DEFAULT FALSE,
    references JSONB DEFAULT '[]',
    cisa_kev BOOLEAN DEFAULT FALSE,
    published_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Service-Vulnerability junction table
CREATE TABLE service_vulnerabilities (
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    vulnerability_id UUID REFERENCES vulnerabilities(id),
    confidence VARCHAR(20) DEFAULT 'medium',
    validated BOOLEAN DEFAULT FALSE,
    validation_method VARCHAR(50),
    notes TEXT,
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    PRIMARY KEY (service_id, vulnerability_id)
);

-- Research tasks table
CREATE TABLE research_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    source VARCHAR(50),
    results JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Notes table
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255),
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_hosts_project ON hosts(project_id);
CREATE INDEX idx_hosts_ip ON hosts(ip_address);
CREATE INDEX idx_services_host ON services(host_id);
CREATE INDEX idx_services_port ON services(port);
CREATE INDEX idx_vulnerabilities_cve ON vulnerabilities(cve_id);
CREATE INDEX idx_vulnerabilities_severity ON vulnerabilities(severity);
CREATE INDEX idx_research_status ON research_tasks(status);
CREATE INDEX idx_research_target ON research_tasks(target_type, target_id);
CREATE INDEX idx_notes_entity ON notes(entity_type, entity_id);
CREATE INDEX idx_audit_project ON audit_log(project_id, created_at DESC);

-- Update triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vulnerabilities_updated_at BEFORE UPDATE ON vulnerabilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Development Workflow

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/hermes.git
cd hermes

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database setup (SQLite for development)
alembic upgrade head

# Start backend
uvicorn api.main:app --reload --port 8000

# In another terminal - Frontend setup
cd frontend/web-app
npm install
npm run dev  # Starts on http://localhost:3000

# In another terminal - Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# In another terminal - Start Celery worker
cd backend
celery -A workers.celery_app worker --loglevel=info
```

### Docker Compose Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - scan_data:/data/scans
    environment:
      - DATABASE_URL=sqlite:///./hermes.db
      - REDIS_URL=redis://redis:6379/0
      - DEVELOPMENT=true
    depends_on:
      - redis
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend/web-app
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/web-app:/app
      - /app/node_modules
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    command: npm run dev

  worker:
    build: ./backend
    volumes:
      - ./backend:/app
      - scan_data:/data/scans
    environment:
      - DATABASE_URL=sqlite:///./hermes.db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A workers.celery_app worker --loglevel=info

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  scan_data:
  redis_data:
```

### Environment Configuration

```bash
# .env.development
# Database
DATABASE_URL=sqlite:///./hermes.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/hermes

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# External APIs (Optional)
NVD_API_KEY=  # Optional, works without but with rate limits
ENABLE_NVD=true
ENABLE_CISA_KEV=true
ENABLE_EXPLOITDB=true

# File Storage
UPLOAD_PATH=/tmp/hermes/uploads
EXPORT_PATH=/tmp/hermes/exports
MAX_UPLOAD_SIZE=104857600  # 100MB

# Security
SECRET_KEY=development-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Features
ENABLE_WEBSOCKET=true
ENABLE_BACKGROUND_TASKS=true
```

## Testing Strategy

### Backend Testing

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

### Frontend Testing

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

## Deployment Guide

### Production Deployment with Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  backend:
    image: hermes/backend:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data:/data
    environment:
      - DATABASE_URL=postgresql://hermes:${DB_PASSWORD}@postgres:5432/hermes
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis

  frontend:
    image: hermes/frontend:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - REACT_APP_API_URL=https://hermes.yourdomain.com/api

  worker:
    image: hermes/backend:latest
    restart: unless-stopped
    command: celery -A workers.celery_app worker
    environment:
      - DATABASE_URL=postgresql://hermes:${DB_PASSWORD}@postgres:5432/hermes
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=hermes
      - POSTGRES_USER=hermes
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
```

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }
    
    upstream frontend {
        server frontend:3000;
    }
    
    server {
        listen 80;
        server_name hermes.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name hermes.yourdomain.com;
        
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        # API routes
        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # WebSocket support
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
        }
    }
}
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

# Build images
docker build -t hermes/backend:latest ./backend
docker build -t hermes/frontend:latest ./frontend/web-app

# Run database migrations
docker-compose -f docker-compose.production.yml run --rm backend \
    alembic upgrade head

# Start services
docker-compose -f docker-compose.production.yml up -d

# Health check
sleep 10
curl -f http://localhost:8000/health || exit 1
echo "Deployment successful!"
```

## Performance Optimization

### Caching Strategy

```python
# Redis caching implementation
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=86400)  # 24 hours
async def get_cve_details(cve_id: str):
    # Expensive API call
    return await nvd_service.fetch_cve(cve_id)
```

### Database Optimization

```sql
-- Materialized view for project statistics
CREATE MATERIALIZED VIEW project_statistics AS
SELECT 
    p.id as project_id,
    COUNT(DISTINCT h.id) as host_count,
    COUNT(DISTINCT s.id) as service_count,
    COUNT(DISTINCT v.id) as vulnerability_count,
    SUM(CASE WHEN v.severity = 'critical' THEN 1 ELSE 0 END) as critical_count
FROM projects p
LEFT JOIN hosts h ON p.id = h.project_id
LEFT JOIN services s ON h.id = s.host_id
LEFT JOIN service_vulnerabilities sv ON s.id = sv.service_id
LEFT JOIN vulnerabilities v ON sv.vulnerability_id = v.id
GROUP BY p.id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW project_statistics;
```

## Monitoring and Observability

### Health Endpoints

```python
from fastapi import FastAPI, status
from sqlalchemy import text

@app.get("/health")
async def health_check():
    """Liveness probe"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe"""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "redis": "ok",
                "celery": check_celery_workers()
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "error": str(e)}
        )
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
scan_imports = Counter('hermes_scan_imports_total', 'Total scan imports')
scan_import_duration = Histogram('hermes_scan_import_duration_seconds', 'Scan import duration')
api_requests = Counter('hermes_api_requests_total', 'Total API requests', ['method', 'endpoint'])

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Migration Path to Enterprise

### Phase 1: Current MVP (Free, Open Source)
- Single-tenant deployment
- SQLite/PostgreSQL database
- Local file storage
- Basic authentication
- Docker Compose deployment

### Phase 2: Team Features (Future Premium Branch)
- User management and roles
- Team collaboration
- Project permissions
- Audit logging
- Advanced reporting templates

### Phase 3: Enterprise Features (Separate Architecture)
- Multi-tenancy with organization isolation
- SSO/SAML authentication
- Kubernetes orchestration
- High availability
- SLA guarantees
- Priority support

### Database Migration Path

```sql
-- Future migration to add multi-tenancy
ALTER TABLE projects ADD COLUMN organization_id UUID;
ALTER TABLE projects ADD CONSTRAINT fk_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id);

-- Add row-level security
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY project_isolation ON projects
    FOR ALL
    USING (organization_id = current_setting('app.organization_id')::UUID);
```

---

## Architecture Summary

This MVP architecture delivers on the core promise of Hermes: **eliminating 40-60% of penetration testing documentation time** through intelligent automation. The design focuses on:

✅ **Immediate Value**: Automatic scan parsing and vulnerability research  
✅ **Simple Deployment**: Docker Compose with no cloud dependencies  
✅ **Security First**: Local-only processing, no data transmission  
✅ **Developer Friendly**: Monorepo structure, clear service boundaries  
✅ **Community Focus**: Free, open-source, extensible  
✅ **Growth Ready**: Clear path to enterprise features without rewriting  

The architecture is optimized for the target market of individual pentesters and small teams while maintaining the flexibility to evolve into an enterprise platform through a separate commercial branch when needed.