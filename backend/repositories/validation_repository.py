"""
Repository for Validation Queue and Feedback operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from models import ValidationQueue, ValidationFeedback


class ValidationRepository:
    """Repository for validation-related database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_queue_item(
        self,
        finding_type: str,
        finding_id: UUID,
        priority: str,
        status: str = 'pending',
        assigned_to: Optional[str] = None
    ) -> ValidationQueue:
        """Create a new validation queue item"""
        queue_item = ValidationQueue(
            finding_type=finding_type,
            finding_id=finding_id,
            priority=priority,
            status=status,
            assigned_to=assigned_to
        )
        self.db.add(queue_item)
        self.db.commit()
        self.db.refresh(queue_item)
        return queue_item

    def get_queue_items(
        self,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        finding_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[ValidationQueue], int]:
        """Get validation queue items with optional filters"""
        query = self.db.query(ValidationQueue)

        if priority:
            query = query.filter(ValidationQueue.priority == priority)
        if status:
            query = query.filter(ValidationQueue.status == status)
        if finding_type:
            query = query.filter(ValidationQueue.finding_type == finding_type)

        total = query.count()
        items = query.order_by(ValidationQueue.created_at.desc()).offset(offset).limit(limit).all()

        return items, total

    def get_queue_item_by_finding(self, finding_id: UUID) -> Optional[ValidationQueue]:
        """Get queue item by finding ID"""
        return self.db.query(ValidationQueue).filter(
            ValidationQueue.finding_id == finding_id
        ).first()

    def update_queue_item_status(
        self,
        queue_id: UUID,
        status: str,
        review_notes: Optional[str] = None
    ) -> ValidationQueue:
        """Update validation queue item status"""
        item = self.db.query(ValidationQueue).filter(ValidationQueue.id == queue_id).first()
        if not item:
            raise ValueError(f"Queue item {queue_id} not found")

        item.status = status
        if status == 'completed':
            item.reviewed_at = datetime.utcnow()
        if review_notes:
            item.review_notes = review_notes

        self.db.commit()
        self.db.refresh(item)
        return item

    def create_feedback(
        self,
        finding_id: UUID,
        feedback_type: str,
        user_comment: str,
        user_id: Optional[str] = None
    ) -> ValidationFeedback:
        """Create a new validation feedback entry"""
        feedback = ValidationFeedback(
            finding_id=finding_id,
            feedback_type=feedback_type,
            user_comment=user_comment,
            user_id=user_id
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_feedback_by_finding(self, finding_id: UUID) -> List[ValidationFeedback]:
        """Get all feedback for a specific finding"""
        return self.db.query(ValidationFeedback).filter(
            ValidationFeedback.finding_id == finding_id
        ).order_by(ValidationFeedback.created_at.desc()).all()

    def get_feedback_statistics(self, finding_type: str = 'service_vulnerability') -> dict:
        """Get aggregated feedback statistics"""
        feedbacks = self.db.query(ValidationFeedback).all()

        stats = {
            'total_feedback': len(feedbacks),
            'false_positive': 0,
            'false_negative': 0,
            'correct': 0
        }

        for feedback in feedbacks:
            if feedback.feedback_type in stats:
                stats[feedback.feedback_type] += 1

        return stats
