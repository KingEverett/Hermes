# API Specification

## REST API Endpoints

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

## WebSocket Events

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
