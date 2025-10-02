# Epic 1: Foundation & Core Intelligence Engine

**Total Story Points:** 26
**Sprint Assignment:** Sprints 1-2
**Status:** Ready for Development

## Epic Goal
Establish the foundational project infrastructure and intelligent note-taking engine that automatically transforms nmap scan outputs into structured markdown documentation, delivering immediate time-savings value to cybersecurity professionals while providing the technical foundation for all subsequent features.

## Dependencies
**Epic 1 → All Other Epics**
- Provides data models for Epic 2
- Provides parser output for Epic 3
- Provides core functions for Epic 4

## Stories

### US-1.1: Project Infrastructure Setup
**Priority:** P0 (Blocker)
**Story Points:** 3
**Sprint:** 1
**Dependencies:** None (Starting point)

**User Story:**
As a **developer**, I want **complete project scaffolding with Docker containerization** so that **the development environment supports all planned services**.

**Acceptance Criteria:**
- [ ] Monorepo structure created with backend/, frontend/, cli/, shared/ directories
- [ ] Docker Compose configuration for all services (FastAPI, React, Redis, PostgreSQL)
- [ ] SQLite database connection for development environment
- [ ] Basic FastAPI health check endpoint returning JSON
- [ ] React TypeScript app with "Hello Hermes" and Tailwind CSS
- [ ] Single `docker-compose up` starts all services

**Technical Tasks:**
1. Initialize monorepo with proper .gitignore
2. Create Docker configurations for each service
3. Set up docker-compose.yml with service dependencies
4. Configure environment variables and .env.example
5. Create basic CI/CD pipeline configuration

**Definition of Done:**
- All services start with docker-compose up
- Health check endpoints return 200
- Frontend displays "Hello Hermes"
- Code reviewed and merged
- Documentation updated

---

### US-1.2: Core Data Models and Schema
**Priority:** P0 (Blocker)
**Story Points:** 5
**Sprint:** 1
**Dependencies:** US-1.1

**User Story:**
As a **developer**, I want **database schema for hosts, services, and vulnerabilities** so that **parsed scan data can be persisted efficiently**.

**Acceptance Criteria:**
- [ ] Host model with IP, hostname, OS detection, scan metadata
- [ ] Service model with port, protocol, service name, version, banner
- [ ] Vulnerability model with CVE, severity, description, research status
- [ ] Scan model tracking source file, timestamp, tool type, status
- [ ] SQLAlchemy models with proper relationships
- [ ] Alembic migrations configured and applied
- [ ] Basic CRUD operations via FastAPI endpoints

**Technical Tasks:**
1. Design database schema with proper normalization
2. Implement SQLAlchemy models
3. Create Alembic migration scripts
4. Build repository pattern for data access
5. Create FastAPI CRUD endpoints
6. Write unit tests for models and repositories

**Definition of Done:**
- All models create/update/delete successfully
- Relationships work correctly
- API endpoints return proper JSON
- Unit tests pass at 90%+ coverage
- Migration scripts work forward/backward

---

### US-1.3: Nmap XML Parser (MVP Core)
**Priority:** P0 (Blocker)
**Story Points:** 13
**Sprint:** 2
**Dependencies:** US-1.2

**User Story:**
As a **penetration tester**, I want **automatic parsing of nmap XML files** so that **I get structured documentation without manual processing**.

**Acceptance Criteria:**
- [ ] Extract host information (IP, hostname, OS) from nmap XML
- [ ] Capture all service details (port, protocol, service, version, banner)
- [ ] Handle 1000+ hosts without memory errors
- [ ] Detect and report corrupted XML with clear errors
- [ ] Store parsed data with proper relationships
- [ ] Process 100 hosts in under 5 seconds
- [ ] Maintain audit trail of scan source and timestamp

**Technical Tasks:**
1. Implement XML parsing with error handling
2. Create data extraction logic for hosts/services
3. Build database insertion with transaction support
4. Add performance optimization for large files
5. Implement duplicate detection logic
6. Create comprehensive test suite with sample files

**Definition of Done:**
- Parses sample nmap files correctly
- Performance requirements met (5 seconds/100 hosts)
- Error handling covers all edge cases
- Integration tests pass
- Memory usage remains stable

---

### US-1.4: Basic Markdown Documentation Generator
**Priority:** P1 (Critical)
**Story Points:** 5
**Sprint:** 2
**Dependencies:** US-1.3

**User Story:**
As a **penetration tester**, I want **automatic markdown generation from parsed data** so that **I have readable documentation immediately**.

**Acceptance Criteria:**
- [ ] Generate GitHub-flavored markdown with headers, tables, code blocks
- [ ] Host sections with collapsible service details
- [ ] Service information in readable tables
- [ ] Code blocks preserve banner information
- [ ] Include metadata section with scan info and statistics
- [ ] Valid markdown syntax that renders correctly
- [ ] Generate docs for 500+ hosts in under 10 seconds

**Technical Tasks:**
1. Create markdown template engine
2. Implement host/service formatting logic
3. Add collapsible section generation
4. Build export functionality
5. Optimize for large datasets
6. Add markdown validation

**Definition of Done:**
- Generated markdown renders correctly in GitHub
- Performance requirements met (10 seconds/500 hosts)
- All required sections included
- Template system allows customization
- Export functionality works via API

---

## Sprint Breakdown

### Sprint 1 Stories
- **US-1.1** (3 points): Infrastructure Setup
- **US-1.2** (5 points): Data Models
- **Total**: 8 points

### Sprint 2 Stories
- **US-1.3** (13 points): Nmap Parser
- **US-1.4** (5 points): Markdown Generator
- **Total**: 18 points

## Validation Gate
Epic 2 cannot start until:
- ✅ Parser successfully processes nmap files
- ✅ Database schema supports vulnerability data
- ✅ Service version extraction working
- ✅ API framework operational