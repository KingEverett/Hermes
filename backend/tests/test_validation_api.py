"""
API integration tests for validation endpoints.
"""
import pytest
from uuid import uuid4
from datetime import datetime


def test_get_validation_queue_empty(client):
    """Test getting empty validation queue"""
    response = client.get("/api/v1/validation/queue")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 0


def test_get_validation_queue_with_filters(client):
    """Test validation queue with filters"""
    response = client.get(
        "/api/v1/validation/queue",
        params={"priority": "high", "status": "pending", "limit": 10}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data


def test_submit_validation_review_invalid_decision(client):
    """Test submitting review with invalid decision type"""
    finding_id = str(uuid4())
    review_data = {
        "decision": "invalid_action",
        "justification": "This is a test justification with enough characters",
        "validated_by": "test_user"
    }

    response = client.post(
        f"/api/v1/validation/{finding_id}/review",
        json=review_data
    )
    assert response.status_code == 400
    assert "Decision must be" in response.json()["detail"]


def test_submit_validation_review_short_justification(client):
    """Test submitting review with insufficient justification"""
    finding_id = str(uuid4())
    review_data = {
        "decision": "approve",
        "justification": "Too short",
        "validated_by": "test_user"
    }

    response = client.post(
        f"/api/v1/validation/{finding_id}/review",
        json=review_data
    )
    # Should fail pydantic validation for min_length
    assert response.status_code in [400, 422]


def test_submit_validation_override_requires_long_justification(client):
    """Test that override decisions require detailed justification"""
    finding_id = str(uuid4())
    review_data = {
        "decision": "override",
        "justification": "This is a normal length justification",
        "validated_by": "test_user"
    }

    response = client.post(
        f"/api/v1/validation/{finding_id}/review",
        json=review_data
    )
    # Should fail because override needs 50+ characters
    assert response.status_code == 400
    assert "detailed justification" in response.json()["detail"]


def test_submit_validation_review_not_found(client):
    """Test submitting review for non-existent finding"""
    finding_id = str(uuid4())
    review_data = {
        "decision": "approve",
        "justification": "This finding looks valid after manual inspection and testing",
        "validated_by": "test_user"
    }

    response = client.post(
        f"/api/v1/validation/{finding_id}/review",
        json=review_data
    )
    assert response.status_code == 404


def test_get_validation_history_not_found(client):
    """Test getting history for non-existent finding"""
    finding_id = str(uuid4())

    response = client.get(f"/api/v1/validation/history/{finding_id}")
    assert response.status_code == 404


def test_submit_feedback_invalid_type(client):
    """Test submitting feedback with invalid type"""
    feedback_data = {
        "finding_id": str(uuid4()),
        "feedback_type": "invalid_type",
        "comment": "This is test feedback with enough characters"
    }

    response = client.post("/api/v1/validation/feedback", json=feedback_data)
    assert response.status_code == 400
    assert "Feedback type must be" in response.json()["detail"]


def test_submit_feedback_short_comment(client):
    """Test submitting feedback with insufficient comment length"""
    feedback_data = {
        "finding_id": str(uuid4()),
        "feedback_type": "correct",
        "comment": "Too short"
    }

    response = client.post("/api/v1/validation/feedback", json=feedback_data)
    # Should fail pydantic validation for min_length
    assert response.status_code in [400, 422]


def test_submit_feedback_invalid_uuid(client):
    """Test submitting feedback with invalid finding_id"""
    feedback_data = {
        "finding_id": "not-a-valid-uuid",
        "feedback_type": "correct",
        "comment": "This is a valid comment with enough characters"
    }

    response = client.post("/api/v1/validation/feedback", json=feedback_data)
    assert response.status_code in [400, 422]


def test_validation_queue_pagination(client):
    """Test validation queue pagination parameters"""
    # Test with different pagination parameters
    response = client.get(
        "/api/v1/validation/queue",
        params={"limit": 5, "offset": 0}
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) <= 5

    # Test with offset
    response2 = client.get(
        "/api/v1/validation/queue",
        params={"limit": 5, "offset": 5}
    )
    assert response2.status_code == 200


def test_validation_queue_filter_combinations(client):
    """Test various filter combinations on validation queue"""
    # Filter by priority only
    response = client.get(
        "/api/v1/validation/queue",
        params={"priority": "critical"}
    )
    assert response.status_code == 200

    # Filter by status only
    response = client.get(
        "/api/v1/validation/queue",
        params={"status": "pending"}
    )
    assert response.status_code == 200

    # Filter by both
    response = client.get(
        "/api/v1/validation/queue",
        params={"priority": "high", "status": "completed"}
    )
    assert response.status_code == 200
