# Deployment Guide

## Production Deployment with Docker Compose

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

## Nginx Configuration

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

## Deployment Script

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
