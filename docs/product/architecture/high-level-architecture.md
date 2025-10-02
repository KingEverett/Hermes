# High Level Architecture

## Technical Summary
Hermes employs a service-oriented architecture within a monorepo structure, balancing modularity with deployment simplicity. The system prioritizes immediate value delivery through intelligent automation while maintaining flexibility for future enterprise evolution.

## Platform Choice
**Self-Hosted Docker Deployment**
- Docker Compose orchestration for simplicity
- No external cloud dependencies for security compliance
- Local-first data processing
- Optional air-gap deployment capability

## Repository Structure
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

## Architecture Diagram

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

## Architectural Patterns
- **Service-Oriented Architecture**: Logical separation without deployment complexity
- **Repository Pattern**: Clean data access abstraction
- **Factory Pattern**: Extensible scan parser system
- **Event-Driven Processing**: Background tasks for heavy operations
- **Progressive Enhancement**: Simple MVP to team collaboration
