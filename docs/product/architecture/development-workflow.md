# Development Workflow

## Local Development Setup

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

## Docker Compose Development

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

## Environment Configuration

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
