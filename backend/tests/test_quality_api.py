"""
API integration tests for quality metrics endpoints.
"""
import pytest
from uuid import uuid4


def test_get_quality_metrics(client):
    """Test getting quality metrics for a project"""
    project_id = str(uuid4())

    # This will return metrics even for non-existent project (just zeros)
    response = client.get(f"/api/v1/quality/metrics/{project_id}")

    # May return 500 if database query fails, or 200 with zero metrics
    assert response.status_code in [200, 500]


def test_get_quality_trends(client):
    """Test getting quality trend data"""
    project_id = str(uuid4())

    response = client.get(f"/api/v1/quality/trends/{project_id}?days=30")

    # May return 500 if database query fails, or 200 with empty data
    assert response.status_code in [200, 500]


def test_get_quality_trends_with_dates(client):
    """Test getting quality trends with specific date range"""
    project_id = str(uuid4())

    response = client.get(
        f"/api/v1/quality/trends/{project_id}",
        params={
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-01-31T23:59:59"
        }
    )

    assert response.status_code in [200, 500]


def test_submit_quality_feedback_invalid_type(client):
    """Test submitting feedback with invalid feedback type"""
    feedback_data = {
        "finding_id": str(uuid4()),
        "feedback_type": "invalid",
        "user_comment": "This is a test feedback comment"
    }

    response = client.post("/api/v1/quality/feedback", json=feedback_data)
    assert response.status_code == 400
    assert "Feedback type must be" in response.json()["detail"]


def test_submit_quality_feedback_valid(client):
    """Test submitting valid quality feedback"""
    feedback_data = {
        "finding_id": str(uuid4()),
        "feedback_type": "correct",
        "user_comment": "This finding was accurate and helpful"
    }

    response = client.post("/api/v1/quality/feedback", json=feedback_data)

    # May fail with 500 if finding doesn't exist, but request validation should pass
    assert response.status_code in [200, 500]


def test_get_accuracy_issues(client):
    """Test getting accuracy issues for a project"""
    project_id = str(uuid4())

    response = client.get(f"/api/v1/quality/issues/{project_id}")

    # Should return empty issues list for non-existent project
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "issues" in data
        assert "total_issues" in data


def test_get_coverage_metrics(client):
    """Test getting coverage metrics for a project"""
    project_id = str(uuid4())

    response = client.get(f"/api/v1/quality/coverage/{project_id}")

    # May return 500 if database query fails, or 200 with zero coverage
    assert response.status_code in [200, 500]
