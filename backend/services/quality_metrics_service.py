"""
Quality Metrics Service for tracking research accuracy and performance.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from models import (
    QualityMetrics,
    ServiceVulnerability,
    ValidationFeedback,
    ValidationQueue
)


class QualityMetricsService:
    """Service for calculating and tracking quality control metrics"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_project_metrics(self, project_id: UUID) -> Dict:
        """
        Calculate comprehensive quality metrics for a project.

        Returns:
            Dict with various quality metrics
        """
        # Get all vulnerabilities for the project
        from models import Service, Host
        vulns_query = self.db.query(ServiceVulnerability).join(
            Service
        ).join(Host).filter(Host.project_id == project_id)

        total_findings = vulns_query.count()
        validated_findings = vulns_query.filter(
            ServiceVulnerability.validated == True
        ).count()
        false_positives = vulns_query.filter(
            ServiceVulnerability.false_positive == True
        ).count()

        # Calculate accuracy rate
        accuracy_rate = 0.0
        if validated_findings > 0:
            correct_findings = validated_findings - false_positives
            accuracy_rate = (correct_findings / validated_findings) * 100

        # Calculate false positive rate
        false_positive_rate = 0.0
        if validated_findings > 0:
            false_positive_rate = (false_positives / validated_findings) * 100

        # Get confidence distribution
        confidence_distribution = {
            'high': vulns_query.filter(
                ServiceVulnerability.confidence_score >= 0.8
            ).count(),
            'medium': vulns_query.filter(
                ServiceVulnerability.confidence_score >= 0.5,
                ServiceVulnerability.confidence_score < 0.8
            ).count(),
            'low': vulns_query.filter(
                ServiceVulnerability.confidence_score < 0.5
            ).count()
        }

        # Get validation queue size
        queue_size = self.db.query(ValidationQueue).filter(
            ValidationQueue.status == 'pending'
        ).count()

        return {
            'total_findings': total_findings,
            'validated_findings': validated_findings,
            'false_positives': false_positives,
            'accuracy_rate': round(accuracy_rate, 2),
            'false_positive_rate': round(false_positive_rate, 2),
            'confidence_distribution': confidence_distribution,
            'validation_queue_size': queue_size,
            'calculated_at': datetime.utcnow().isoformat()
        }

    def store_metric(
        self,
        project_id: UUID,
        metric_type: str,
        value: float,
        metadata: Optional[Dict] = None
    ) -> QualityMetrics:
        """Store a quality metric in the database"""
        metric = QualityMetrics(
            project_id=project_id,
            metric_type=metric_type,
            value=value,
            metric_metadata=metadata or {},
            calculated_at=datetime.utcnow()
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)

        return metric

    def get_trend_data(
        self,
        project_id: UUID,
        start_date: datetime,
        end_date: datetime,
        metric_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get historical trend data for quality metrics.

        Args:
            project_id: Project UUID
            start_date: Start of time range
            end_date: End of time range
            metric_type: Optional filter by metric type

        Returns:
            List of trend data points
        """
        query = self.db.query(QualityMetrics).filter(
            QualityMetrics.project_id == project_id,
            QualityMetrics.calculated_at >= start_date,
            QualityMetrics.calculated_at <= end_date
        )

        if metric_type:
            query = query.filter(QualityMetrics.metric_type == metric_type)

        metrics = query.order_by(QualityMetrics.calculated_at).all()

        return [
            {
                'metric_type': m.metric_type,
                'value': m.value,
                'calculated_at': m.calculated_at.isoformat(),
                'metadata': m.metric_metadata
            }
            for m in metrics
        ]

    def process_feedback(self, feedback: ValidationFeedback) -> None:
        """
        Process feedback to update quality metrics.

        This method analyzes feedback patterns to identify systematic issues.
        """
        # Count feedback by type
        feedback_stats = self.db.query(
            ValidationFeedback.feedback_type,
            func.count(ValidationFeedback.id).label('count')
        ).group_by(ValidationFeedback.feedback_type).all()

        # Store aggregated feedback as metrics
        for feedback_type, count in feedback_stats:
            # This could trigger alerts or metric updates
            pass

    def identify_accuracy_issues(self, project_id: UUID) -> List[Dict]:
        """
        Identify systematic accuracy issues in the project.

        Returns:
            List of identified issues with descriptions
        """
        issues = []

        # Check false positive rate
        metrics = self.calculate_project_metrics(project_id)
        if metrics['false_positive_rate'] > 20:
            issues.append({
                'type': 'high_false_positive_rate',
                'severity': 'high',
                'description': f"False positive rate is {metrics['false_positive_rate']}% (threshold: 20%)",
                'recommendation': 'Review confidence scoring algorithm and data sources'
            })

        # Check validation backlog
        if metrics['validation_queue_size'] > 50:
            issues.append({
                'type': 'large_validation_backlog',
                'severity': 'medium',
                'description': f"Validation queue has {metrics['validation_queue_size']} pending items",
                'recommendation': 'Increase validation capacity or adjust queue thresholds'
            })

        # Check low confidence findings
        if metrics['confidence_distribution']['low'] > metrics['total_findings'] * 0.3:
            issues.append({
                'type': 'high_low_confidence_rate',
                'severity': 'medium',
                'description': f"{metrics['confidence_distribution']['low']} findings have low confidence",
                'recommendation': 'Improve data source reliability or validation processes'
            })

        return issues

    def calculate_coverage_metrics(self, project_id: UUID) -> Dict:
        """
        Calculate research coverage metrics.

        Returns:
            Dict with coverage statistics
        """
        from models import Service, Host

        # Get services for project
        services_query = self.db.query(Service).join(Host).filter(
            Host.project_id == project_id
        )

        total_services = services_query.count()
        services_with_vulns = services_query.filter(
            Service.vulnerabilities.any()
        ).count()

        # Calculate coverage
        coverage_rate = 0.0
        if total_services > 0:
            coverage_rate = (services_with_vulns / total_services) * 100

        return {
            'total_services': total_services,
            'services_researched': services_with_vulns,
            'coverage_rate': round(coverage_rate, 2),
            'services_pending': total_services - services_with_vulns
        }
