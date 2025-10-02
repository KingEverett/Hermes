"""
Repository for Quality Metrics operations.
"""
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import QualityMetrics


class QualityRepository:
    """Repository for quality metrics database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_metric(
        self,
        project_id: UUID,
        metric_type: str,
        value: float,
        metric_metadata: Optional[Dict] = None,
        calculated_at: Optional[datetime] = None
    ) -> QualityMetrics:
        """Create a new quality metric entry"""
        metric = QualityMetrics(
            project_id=project_id,
            metric_type=metric_type,
            value=value,
            metric_metadata=metric_metadata or {},
            calculated_at=calculated_at or datetime.utcnow()
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)

        return metric

    def get_latest_metrics(
        self,
        project_id: UUID,
        metric_type: Optional[str] = None
    ) -> List[QualityMetrics]:
        """Get the latest metrics for a project"""
        query = self.db.query(QualityMetrics).filter(
            QualityMetrics.project_id == project_id
        )

        if metric_type:
            query = query.filter(QualityMetrics.metric_type == metric_type)

        # Get latest metrics by grouping on metric_type
        subquery = self.db.query(
            QualityMetrics.metric_type,
            func.max(QualityMetrics.calculated_at).label('max_date')
        ).filter(
            QualityMetrics.project_id == project_id
        ).group_by(QualityMetrics.metric_type).subquery()

        query = self.db.query(QualityMetrics).join(
            subquery,
            (QualityMetrics.metric_type == subquery.c.metric_type) &
            (QualityMetrics.calculated_at == subquery.c.max_date)
        ).filter(QualityMetrics.project_id == project_id)

        return query.all()

    def get_metrics_in_range(
        self,
        project_id: UUID,
        start_date: datetime,
        end_date: datetime,
        metric_type: Optional[str] = None
    ) -> List[QualityMetrics]:
        """Get metrics within a date range"""
        query = self.db.query(QualityMetrics).filter(
            QualityMetrics.project_id == project_id,
            QualityMetrics.calculated_at >= start_date,
            QualityMetrics.calculated_at <= end_date
        )

        if metric_type:
            query = query.filter(QualityMetrics.metric_type == metric_type)

        return query.order_by(QualityMetrics.calculated_at).all()

    def delete_old_metrics(
        self,
        project_id: UUID,
        before_date: datetime
    ) -> int:
        """Delete metrics older than specified date"""
        deleted = self.db.query(QualityMetrics).filter(
            QualityMetrics.project_id == project_id,
            QualityMetrics.calculated_at < before_date
        ).delete()

        self.db.commit()
        return deleted
