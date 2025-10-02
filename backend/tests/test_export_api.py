"""Integration tests for export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from main import app
from models import ExportJob, ExportFormat, JobStatus, Project, Host, Service, Scan


class TestExportAPI:
    """Integration test suite for export API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        with patch('api.exports.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def sample_project(self):
        """Create sample project."""
        return Project(
            id="test-project-123",
            name="Test Project",
            description="Test project for API testing",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_export_job(self):
        """Create sample export job."""
        return ExportJob(
            id="job-123",
            project_id="test-project-123",
            format=ExportFormat.MARKDOWN,
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )

    def test_export_project_success(self, client, mock_db, sample_project):
        """Test successful project export."""
        # Setup mocks
        mock_project_repo = MagicMock()
        mock_project_repo.get_by_id.return_value = sample_project

        with patch('api.exports.ProjectRepository', return_value=mock_project_repo):
            # Mock the database operations
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.refresh = MagicMock(side_effect=lambda job: setattr(job, 'id', 'job-123'))

            # Make request
            response = client.post(
                "/api/v1/projects/test-project-123/export",
                json={"format": "markdown"}
            )

            # Assertions
            assert response.status_code == 202
            data = response.json()
            assert data["project_id"] == "test-project-123"
            assert data["format"] == "markdown"
            assert data["status"] == "pending"
            assert "id" in data
            assert "created_at" in data

    def test_export_project_not_found(self, client, mock_db):
        """Test export for non-existent project."""
        # Setup mocks
        mock_project_repo = MagicMock()
        mock_project_repo.get_by_id.return_value = None

        with patch('api.exports.ProjectRepository', return_value=mock_project_repo):
            # Make request
            response = client.post(
                "/api/v1/projects/non-existent/export",
                json={"format": "markdown"}
            )

            # Assertions
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_export_job_status(self, client, mock_db, sample_export_job):
        """Test getting export job status."""
        # Make request - endpoint will query real DB
        with patch('api.exports.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.first.return_value = sample_export_job
            response = client.get("/api/v1/projects/test-project-123/export/job-123")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "job-123"
            assert data["project_id"] == "test-project-123"
            assert data["format"] == "markdown"
            assert data["status"] == "pending"

    def test_get_export_job_not_found(self, client, mock_db):
        """Test getting non-existent export job."""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.get("/api/v1/projects/test-project-123/export/non-existent")

        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_download_export_success(self, client, mock_db):
        """Test successful export download."""
        # Create completed job
        completed_job = ExportJob(
            id="job-123",
            project_id="test-project-123",
            format=ExportFormat.MARKDOWN,
            status=JobStatus.COMPLETED,
            file_path="/tmp/export.md",
            created_at=datetime.now(),
            completed_at=datetime.now()
        )

        with patch('api.exports.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.first.return_value = completed_job

            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.read_text', return_value="# Test Export Content"):
                    # Make request
                    response = client.get("/api/v1/projects/test-project-123/export/job-123/download")

                    # Assertions
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
                    assert "Test Export Content" in response.text

    def test_download_export_not_ready(self, client, mock_db, sample_export_job):
        """Test download when export is not ready."""
        # Job is still pending
        sample_export_job.status = JobStatus.PROCESSING

        with patch('api.exports.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.first.return_value = sample_export_job

            # Make request
            response = client.get("/api/v1/projects/test-project-123/export/job-123/download")

            # Assertions
            assert response.status_code == 425
            assert "not ready" in response.json()["detail"].lower()

    def test_download_export_failed(self, client, mock_db):
        """Test download when export failed."""
        # Create failed job
        failed_job = ExportJob(
            id="job-123",
            project_id="test-project-123",
            format=ExportFormat.MARKDOWN,
            status=JobStatus.FAILED,
            error_message="Generation failed due to error",
            created_at=datetime.now(),
            completed_at=datetime.now()
        )

        with patch('api.exports.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.first.return_value = failed_job

            # Make request
            response = client.get("/api/v1/projects/test-project-123/export/job-123/download")

            # Assertions
            assert response.status_code == 500
            assert "Generation failed" in response.json()["detail"]

    def test_process_export_background_task(self, mock_db):
        """Test the background export processing task."""
        from api.exports import process_export

        # Create pending job
        job = ExportJob(
            id="job-123",
            project_id="test-project-123",
            format=ExportFormat.MARKDOWN,
            status=JobStatus.PENDING
        )

        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = job
        mock_db.commit = MagicMock()
        mock_db.close = MagicMock()

        with patch('database.SessionLocal', return_value=mock_db):
            with patch('services.documentation.DocumentationService') as mock_doc_service:
                mock_doc_service.return_value.export_to_file.return_value = "/tmp/export.md"

                # Process export
                process_export("job-123", "test-project-123", ExportFormat.MARKDOWN)

                # Assertions
                assert job.status == JobStatus.COMPLETED
                assert job.file_path == "/tmp/export.md"
                assert job.completed_at is not None
                mock_db.commit.assert_called()

    def test_process_export_failure(self, mock_db):
        """Test background export processing when generation fails."""
        from api.exports import process_export

        # Create pending job
        job = ExportJob(
            id="job-123",
            project_id="test-project-123",
            format=ExportFormat.MARKDOWN,
            status=JobStatus.PENDING
        )

        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = job
        mock_db.commit = MagicMock()
        mock_db.close = MagicMock()

        with patch('database.SessionLocal', return_value=mock_db):
            with patch('services.documentation.DocumentationService') as mock_doc_service:
                mock_doc_service.return_value.export_to_file.side_effect = Exception("Test error")

                # Process export
                process_export("job-123", "test-project-123", ExportFormat.MARKDOWN)

                # Assertions
                assert job.status == JobStatus.FAILED
                assert "Test error" in job.error_message
                assert job.completed_at is not None
                mock_db.commit.assert_called()

    def test_export_formats(self, client, mock_db, sample_project):
        """Test different export formats."""
        # Setup mocks
        mock_project_repo = MagicMock()
        mock_project_repo.get_by_id.return_value = sample_project

        with patch('api.exports.ProjectRepository', return_value=mock_project_repo):
            with patch('api.exports.BackgroundTasks'):
                mock_db.add = MagicMock()
                mock_db.commit = MagicMock()
                mock_db.refresh = MagicMock()

                # Test markdown format (default)
                response = client.post(
                    "/api/v1/projects/test-project-123/export",
                    json={}  # No format specified, should default to markdown
                )
                assert response.status_code == 202
                assert response.json()["format"] == "markdown"

                # Test explicit markdown format
                response = client.post(
                    "/api/v1/projects/test-project-123/export",
                    json={"format": "markdown"}
                )
                assert response.status_code == 202
                assert response.json()["format"] == "markdown"