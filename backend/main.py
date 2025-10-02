from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from api.projects import router as projects_router
from api.scans import router as scans_router
from api.hosts import router as hosts_router
from api.services import router as services_router
from api.exports import router as exports_router
from api.vulnerabilities import router as vulnerabilities_router
from api.configuration import router as configuration_router
from api.monitoring import router as monitoring_router
from api.job_monitoring import router as job_monitoring_router
from api.documentation import router as documentation_router
from api.validation import router as validation_router
from api.staleness import router as staleness_router
from api.quality import router as quality_router
from api.topology import router as topology_router
from api.attack_chains import router as attack_chains_router
from database.connection import get_session as get_db_session
import redis.asyncio as redis
import os
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes API", version="1.0.0")

# Include routers
app.include_router(projects_router)
app.include_router(scans_router)
app.include_router(hosts_router)
app.include_router(services_router)
app.include_router(exports_router)
app.include_router(vulnerabilities_router)
app.include_router(configuration_router)
app.include_router(monitoring_router)
app.include_router(job_monitoring_router)
app.include_router(documentation_router)
app.include_router(validation_router)
app.include_router(staleness_router)
app.include_router(quality_router)
app.include_router(topology_router)
app.include_router(attack_chains_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/v1/status")
async def get_status(db: Session = Depends(get_db_session)):
    """
    Get comprehensive system status (CLI-friendly endpoint)
    """
    try:
        # Check database status
        database_status = False
        try:
            db.execute("SELECT 1")
            database_status = True
        except Exception as e:
            logger.error(f"Database check failed: {e}")

        # Check Redis status
        redis_status = False
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.from_url(redis_url)
            await redis_client.ping()
            redis_status = True
            await redis_client.close()
        except Exception as e:
            logger.error(f"Redis check failed: {e}")

        # Check Celery workers
        celery_workers = 0

        # Query active scans
        active_scans = 0
        try:
            from models.scan import Scan
            active_scans = db.query(Scan).filter(Scan.status == 'processing').count()
        except Exception as e:
            logger.error(f"Active scans query failed: {e}")

        # Query queued research tasks
        queued_research_tasks = 0

        # Query failed jobs
        failed_jobs = 0
        try:
            from models.scan import Scan
            failed_jobs = db.query(Scan).filter(Scan.status == 'failed').count()
        except Exception as e:
            logger.error(f"Failed jobs query failed: {e}")

        return {
            "database_status": database_status,
            "redis_status": redis_status,
            "celery_workers": celery_workers,
            "active_scans": active_scans,
            "queued_research_tasks": queued_research_tasks,
            "failed_jobs": failed_jobs
        }

    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {
            "database_status": False,
            "redis_status": False,
            "celery_workers": 0,
            "active_scans": 0,
            "queued_research_tasks": 0,
            "failed_jobs": 0,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {"message": "Welcome to Hermes API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)