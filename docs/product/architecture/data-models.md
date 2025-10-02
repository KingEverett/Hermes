# Data Models

## Core Entities

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
