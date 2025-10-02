# Epic 4: CLI Integration & Workflow Automation

**Total Story Points:** 13 (MVP) + 21 (Post-MVP)
**Sprint Assignment:** Sprint 7
**Status:** Blocked (Waiting for Epic 1, 2, 3)

## Epic Goal
Develop comprehensive command-line tools and workflow automation that seamlessly integrates Hermes with existing penetration testing methodologies, enabling cybersecurity professionals to incorporate intelligent documentation into their established workflows without disrupting proven assessment practices.

## Dependencies
**Epic 1, 2, 3 → Epic 4 Requirements:**
- Core parsing functionality from US-1.3, US-1.4
- Research capabilities from US-2.1
- Export functions from Epic 3
- All core features accessible via API

**Epic 4 → End Users Provides:**
- Complete CLI interface
- Workflow automation
- Integration layer for existing tools

## MVP Stories (Sprint 7)

### US-4.1: Core CLI Tool (MVP Essential)
**Priority:** P1 (Critical)
**Story Points:** 13
**Sprint:** 7
**Dependencies:** US-1.3, US-1.4, US-2.1

**User Story:**
As a **penetration tester**, I want **command-line interface for scan import** so that **I can integrate Hermes into my terminal workflow**.

**MVP Scope:**
- Focus on import and export commands only
- Defer advanced features like piping
- Basic configuration management

**Acceptance Criteria:**
- [ ] `hermes import <file>` processes scan files
- [ ] `hermes export` generates markdown
- [ ] `hermes config` manages API keys
- [ ] Comprehensive help system
- [ ] Unix-style exit codes
- [ ] Clear error messages

**Technical Tasks:**
1. Implement Click CLI framework
2. Create import command logic
3. Build export functionality
4. Add configuration management
5. Write help documentation
6. Create integration tests

**Definition of Done:**
- All CLI commands work correctly
- Help documentation complete
- Unix conventions followed
- Error messages clear and actionable
- Integration tests pass

---

## Post-MVP Stories (Deferred)

### US-4.2: Directory Monitoring (Post-MVP)
**Priority:** P3 (Nice to have)
**Story Points:** 8
**Sprint:** Post-MVP
**Dependencies:** US-4.1
**Status:** DEFERRED TO POST-MVP

**Features Deferred:**
- `hermes monitor <directory>` command
- Real-time file watching
- Automatic processing of new scans
- Background daemon mode

---

### US-4.3: Tool Integration (Post-MVP)
**Priority:** P3 (Nice to have)
**Story Points:** 13
**Sprint:** Post-MVP
**Dependencies:** US-4.1
**Status:** DEFERRED TO POST-MVP

**Features Deferred:**
- `hermes pipe` for stdin processing
- Tool wrapper commands
- Batch processing capabilities
- Custom output templates
- JSON output mode
- Advanced query interface

---

## Sprint Breakdown

### Sprint 7 (MVP)
- **US-4.1** (13 points): Core CLI Tool
- **Total**: 13 points

### Post-MVP Sprints
- **US-4.2** (8 points): Directory Monitoring
- **US-4.3** (13 points): Tool Integration
- **Total Deferred**: 21 points

## CLI Command Structure (MVP)

```bash
# Core MVP commands
hermes import <file>          # Import scan file
hermes export <project>       # Export documentation
hermes config                 # Manage configuration
hermes status                 # Show system status
hermes --help                 # Show help

# Post-MVP commands (deferred)
hermes monitor <directory>    # Monitor directory
hermes pipe                   # Process stdin
hermes query                  # Advanced querying
```

## Integration Examples (MVP)

```bash
# Basic workflow
nmap -oX scan.xml 192.168.1.0/24
hermes import scan.xml
hermes export --format markdown --output report.md

# Configuration
hermes config set nvd-api-key "your-key"
hermes config show
```

## Success Criteria
- ✅ CLI integrates with existing pentesting workflows
- ✅ All core functionality accessible from command line
- ✅ Documentation generation automated
- ✅ Configuration management simplified
- ✅ Error handling comprehensive