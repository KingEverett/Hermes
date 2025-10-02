# Hermes

Security Research and Documentation Platform

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd hermes
   cp .env.example .env
   ```

2. **Start all services**:
   ```bash
   docker-compose up
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Health Check: http://localhost:8000/health

## Services

### Backend (FastAPI)
- **URL**: http://localhost:8000
- **Health Check**: `/health`
- **Technology**: Python 3.11+ with FastAPI
- **Database**: SQLite (development), PostgreSQL (production)

### Frontend (React)
- **URL**: http://localhost:3000
- **Technology**: React 18+ with TypeScript and Tailwind CSS

### CLI Tool
- **Location**: `cli/hermes-cli/`
- **Usage**:
  ```bash
  cd cli/hermes-cli
  pip install -e .
  hermes --help
  hermes health
  ```

## Development

### Project Structure
```
hermes/
├── backend/           # FastAPI backend service
├── frontend/web-app/  # React TypeScript frontend
├── cli/hermes-cli/    # Python CLI tool
├── shared/            # Shared types and utilities
├── infrastructure/    # Docker configs and scripts
└── docs/             # Documentation
```

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `REACT_APP_API_URL`: Frontend API endpoint

### Requirements
- Docker 24.0+
- Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

## Testing

### Running Tests

**Unit and Integration Tests:**
```bash
cd frontend/web-app
npm test
```

**E2E Tests (Cypress):**

Prerequisites:
- Backend must be running at `http://localhost:8000`
- Frontend must be running at `http://localhost:3000`

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Start frontend (in separate terminal)
cd frontend/web-app
npm start

# Run E2E tests (in separate terminal)
cd frontend/web-app

# Interactive mode (Cypress UI)
npm run e2e

# Headless mode (terminal only)
npm run e2e:headless

# CI mode (with videos and screenshots)
npm run e2e:ci
```

**Test Coverage:**
- **Unit Tests**: Component-level testing with Jest and React Testing Library
- **Integration Tests**: MSW-based API mocking for component integration
- **E2E Tests**: Cypress tests for 3 critical user workflows
  - Workflow 1: Application Load & Project Display
  - Workflow 2: Node Selection & Details
  - Workflow 3: Error Handling & Retry

See [docs/architecture/testing-strategy.md](docs/architecture/testing-strategy.md) for detailed testing documentation.

## Services Overview

| Service   | Port | Description |
|-----------|------|-------------|
| Frontend  | 3000 | React TypeScript application |
| Backend   | 8000 | FastAPI Python application |
| Redis     | 6379 | Caching and task queue |
| PostgreSQL| 5432 | Production database |