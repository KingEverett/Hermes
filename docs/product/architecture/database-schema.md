# Database Schema

## PostgreSQL/SQLite Database Design

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
