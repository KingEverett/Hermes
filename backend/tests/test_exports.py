"""Tests for export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
import json
from pathlib import Path

from main import app
from database import Base, get_db
from models import Project, ExportJob, JobStatus


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_exports.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def test_project():
    """Create a test project."""
    db = TestingSessionLocal()
    try:
        project = Project(id="test-project-123", name="Test Project")
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up database after each test."""
    yield
    db = TestingSessionLocal()
    try:
        db.query(ExportJob).delete()
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()


class TestBatchExportEndpoint:
    """Test batch export functionality."""

    def test_create_batch_export(self, test_project):
        """Test creating a batch export job."""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/exports/batch",
            json={
                "filters": [
                    {
                        "severities": ["critical"],
                        "label": "Critical Only"
                    },
                    {
                        "severities": ["critical", "high"],
                        "label": "High and Critical"
                    }
                ],
                "format": "svg",
                "resolution": 1
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["project_id"] == test_project.id
        assert data["status"] == "pending"

    def test_batch_export_too_many_filters(self, test_project):
        """Test that batch export rejects more than 10 filters."""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/exports/batch",
            json={
                "filters": [{"severities": ["critical"]} for _ in range(11)],
                "format": "svg"
            }
        )

        assert response.status_code == 422
        assert "Maximum 10 filter configurations" in response.json()["detail"]

    def test_batch_export_empty_filters(self, test_project):
        """Test that batch export requires at least one filter."""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/exports/batch",
            json={
                "filters": [],
                "format": "svg"
            }
        )

        assert response.status_code == 422
        assert "At least one filter configuration required" in response.json()["detail"]

    def test_batch_export_project_not_found(self):
        """Test batch export with non-existent project."""
        response = client.post(
            "/api/v1/projects/nonexistent/exports/batch",
            json={
                "filters": [{"severities": ["critical"]}],
                "format": "svg"
            }
        )

        assert response.status_code == 404


class TestExportListEndpoint:
    """Test export history listing."""

    def test_list_exports_empty(self, test_project):
        """Test listing exports when none exist."""
        response = client.get(f"/api/v1/projects/{test_project.id}/exports")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_exports_with_jobs(self, test_project):
        """Test listing exports with existing jobs."""
        db = TestingSessionLocal()
        try:
            # Create test export jobs
            job1 = ExportJob(
                project_id=test_project.id,
                format="svg",
                status=JobStatus.COMPLETED
            )
            job2 = ExportJob(
                project_id=test_project.id,
                format="png",
                status=JobStatus.PENDING
            )
            db.add(job1)
            db.add(job2)
            db.commit()

            response = client.get(f"/api/v1/projects/{test_project.id}/exports")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["project_id"] == test_project.id

        finally:
            db.close()

    def test_list_exports_limit(self, test_project):
        """Test export listing respects limit parameter."""
        db = TestingSessionLocal()
        try:
            # Create 5 export jobs
            for i in range(5):
                job = ExportJob(
                    project_id=test_project.id,
                    format="svg",
                    status=JobStatus.COMPLETED
                )
                db.add(job)
            db.commit()

            response = client.get(
                f"/api/v1/projects/{test_project.id}/exports?limit=3"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3

        finally:
            db.close()


class TestExportDownloadEndpoint:
    """Test export download functionality."""

    def test_download_completed_export(self, test_project, tmp_path):
        """Test downloading a completed export."""
        db = TestingSessionLocal()
        try:
            # Create test file
            test_file = tmp_path / "test-export.zip"
            test_file.write_text("mock export content")

            # Create completed export job
            job = ExportJob(
                project_id=test_project.id,
                format="zip",
                status=JobStatus.COMPLETED,
                file_path=str(test_file)
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            response = client.get(f"/api/v1/exports/{job.id}/download")

            assert response.status_code == 200
            assert response.content == b"mock export content"

        finally:
            db.close()

    def test_download_pending_export(self, test_project):
        """Test downloading a pending export returns 425."""
        db = TestingSessionLocal()
        try:
            job = ExportJob(
                project_id=test_project.id,
                format="svg",
                status=JobStatus.PENDING
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            response = client.get(f"/api/v1/exports/{job.id}/download")

            assert response.status_code == 425
            assert "not ready" in response.json()["detail"].lower()

        finally:
            db.close()

    def test_download_failed_export(self, test_project):
        """Test downloading a failed export returns 500."""
        db = TestingSessionLocal()
        try:
            job = ExportJob(
                project_id=test_project.id,
                format="svg",
                status=JobStatus.FAILED,
                error_message="Export generation failed"
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            response = client.get(f"/api/v1/exports/{job.id}/download")

            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()

        finally:
            db.close()


class TestBatchExportProcessing:
    """Test batch export background processing."""

    @patch('services.graph_service.GraphService.generate_topology')
    def test_process_batch_export_creates_zip(self, mock_topology, test_project, tmp_path):
        """Test that batch export processing creates ZIP with manifest."""
        from api.exports import process_batch_export, FilterConfig

        # Mock topology generation
        mock_topology.return_value = {
            'nodes': [{'id': '1', 'label': 'host1'}],
            'edges': []
        }

        filters = [
            FilterConfig(severities=['critical'], label='Critical Only'),
            FilterConfig(severities=['high', 'critical'], label='High+Critical')
        ]

        db = TestingSessionLocal()
        try:
            job = ExportJob(
                project_id=test_project.id,
                format="zip",
                status=JobStatus.PENDING
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            # Process export
            process_batch_export(
                job.id,
                test_project.id,
                filters,
                "svg",
                1
            )

            # Refresh job
            db.refresh(job)

            # Verify job completed
            assert job.status == JobStatus.COMPLETED
            assert job.file_path is not None

            # Verify ZIP contents
            import zipfile
            if Path(job.file_path).exists():
                with zipfile.ZipFile(job.file_path, 'r') as zip_file:
                    assert 'manifest.json' in zip_file.namelist()

                    # Check manifest content
                    manifest_content = zip_file.read('manifest.json')
                    manifest = json.loads(manifest_content)
                    assert len(manifest) == 2

        finally:
            db.close()
