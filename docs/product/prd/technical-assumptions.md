# Technical Assumptions

## Repository Structure: Monorepo

Single repository containing frontend, backend, CLI tools, and documentation with shared types package and comprehensive API documentation via OpenAPI/Swagger. This approach supports the tight integration between components while maintaining development simplicity for MVP phase.

## Service Architecture

**Microservices pattern within monorepo** with separate services for:
- Scan parsing engine (handles nmap XML, masscan JSON, dirb/gobuster text)
- Vulnerability research service (NVD, CISA KEV, ExploitDB API integration)
- Graph generation service (network topology visualization)
- File management service (CLI integration, directory monitoring)
- Web interface service (React frontend with API gateway)

## Testing Requirements

**Unit + Integration testing approach** with:
- Unit tests for scan parsing algorithms and vulnerability research logic
- Integration tests for API endpoints and database operations
- End-to-end tests for CLI workflow and UI interaction paths
- Performance testing for 1000-host scan processing requirements
- Security testing for input validation and API key handling

## Additional Technical Assumptions and Requests

- **Backend Technology**: Python 3.9+ with FastAPI for async API handling, SQLAlchemy for database abstraction, Pydantic for data validation
- **Frontend Technology**: React 18+ with TypeScript for type safety, D3.js for network visualization, Tailwind CSS for responsive design
- **Database Strategy**: SQLite for development and single-user deployments, PostgreSQL for team environments requiring concurrent access
- **Caching Layer**: Redis for vulnerability research caching with 24-hour TTL and API rate limit management
- **Background Processing**: Celery with Redis broker for asynchronous vulnerability research tasks
- **Deployment Model**: Docker containerization for consistent deployment, docker-compose for local development, self-hosted deployment model with no cloud dependencies
- **Security Requirements**: All data processing occurs locally, API keys encrypted at rest using OS keyring services, HTTPS required for production
- **Performance Targets**: 15-second processing for 1000-host scans, 2-second visualization updates, 30-second vulnerability research completion
- **CLI Integration**: Support for stdin/stdout pipes, file monitoring, and integration with existing pentesting tool chains
