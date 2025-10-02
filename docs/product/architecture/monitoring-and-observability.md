# Monitoring and Observability

## Health Endpoints

```python
from fastapi import FastAPI, status
from sqlalchemy import text

@app.get("/health")
async def health_check():
    """Liveness probe"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe"""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "redis": "ok",
                "celery": check_celery_workers()
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "error": str(e)}
        )
```

## Metrics Collection

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
scan_imports = Counter('hermes_scan_imports_total', 'Total scan imports')
scan_import_duration = Histogram('hermes_scan_import_duration_seconds', 'Scan import duration')
api_requests = Counter('hermes_api_requests_total', 'Total API requests', ['method', 'endpoint'])

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```
