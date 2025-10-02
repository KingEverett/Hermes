"""
Validation Service for managing research result validation and confidence scoring.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from models import ServiceVulnerability, ValidationQueue, ConfidenceLevel
from repositories.validation_repository import ValidationRepository


class ValidationService:
    """Service for handling research result validation and confidence scoring"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ValidationRepository(db)

    def calculate_confidence_score(
        self,
        source_reliability: float,
        data_age_days: int,
        validation_status: str
    ) -> tuple[float, Dict]:
        """
        Calculate confidence score based on multiple factors.

        Formula: confidence_score = (source_reliability * 0.4) + (data_freshness * 0.3) + (validation_status * 0.3)

        Args:
            source_reliability: Score from 0.0 to 1.0 based on data source
            data_age_days: Age of the data in days
            validation_status: Current validation status

        Returns:
            Tuple of (confidence_score, confidence_factors)
        """
        # Source Reliability (weight: 0.4)
        source_score = source_reliability

        # Data Freshness (weight: 0.3)
        if data_age_days < 7:
            freshness_score = 1.0
        elif data_age_days < 30:
            freshness_score = 0.8
        elif data_age_days < 90:
            freshness_score = 0.6
        else:
            freshness_score = 0.4

        # Validation Status (weight: 0.3)
        validation_scores = {
            'approved': 1.0,
            'auto_validated': 0.9,
            'pending': 0.5,
            'needs_review': 0.3,
            'rejected': 0.0
        }
        validation_score = validation_scores.get(validation_status, 0.3)

        # Calculate weighted confidence score
        confidence_score = (
            (source_score * 0.4) +
            (freshness_score * 0.3) +
            (validation_score * 0.3)
        )

        # Build confidence factors dict
        confidence_factors = {
            'source_reliability': source_score,
            'data_freshness': freshness_score,
            'validation_status': validation_score,
            'data_age_days': data_age_days,
            'calculated_at': datetime.utcnow().isoformat()
        }

        return round(confidence_score, 2), confidence_factors

    def get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Map confidence score to confidence level enum"""
        if confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def update_vulnerability_confidence(
        self,
        vulnerability_id: UUID,
        source_reliability: float,
        data_age_days: int,
        validation_status: str = 'pending'
    ) -> ServiceVulnerability:
        """Update confidence score and factors for a vulnerability"""
        vuln = self.db.query(ServiceVulnerability).filter(
            ServiceVulnerability.id == vulnerability_id
        ).first()

        if not vuln:
            raise ValueError(f"Vulnerability {vulnerability_id} not found")

        score, factors = self.calculate_confidence_score(
            source_reliability, data_age_days, validation_status
        )

        vuln.confidence_score = score
        vuln.confidence_factors = factors
        vuln.confidence = self.get_confidence_level(score)
        vuln.validation_status = validation_status

        self.db.commit()
        self.db.refresh(vuln)

        return vuln

    def should_add_to_review_queue(
        self,
        vulnerability: ServiceVulnerability,
        cvss_score: float = 0.0
    ) -> bool:
        """Determine if a vulnerability should be added to review queue"""
        # High-severity findings (CVSS >= 7.0)
        if cvss_score >= 7.0:
            return True

        # Low-confidence results (< 0.6)
        if vulnerability.confidence_score and vulnerability.confidence_score < 0.6:
            return True

        return False

    def populate_review_queue(
        self,
        vulnerability: ServiceVulnerability,
        cvss_score: float = 0.0,
        finding_type: str = 'service_vulnerability'
    ) -> Optional[ValidationQueue]:
        """Add a vulnerability to the validation queue"""
        if not self.should_add_to_review_queue(vulnerability, cvss_score):
            return None

        # Determine priority based on CVSS score
        if cvss_score >= 9.0:
            priority = 'critical'
        elif cvss_score >= 7.0:
            priority = 'high'
        elif cvss_score >= 4.0:
            priority = 'medium'
        else:
            priority = 'low'

        return self.repository.create_queue_item(
            finding_type=finding_type,
            finding_id=vulnerability.id,
            priority=priority
        )

    def process_validation_decision(
        self,
        finding_id: UUID,
        decision: str,
        justification: str,
        validated_by: str,
        reviewer_notes: Optional[str] = None
    ) -> Dict:
        """
        Process a validation decision (approve, reject, override)

        Args:
            finding_id: UUID of the finding being validated
            decision: 'approve', 'reject', or 'override'
            justification: Required justification for the decision
            validated_by: User who made the decision
            reviewer_notes: Optional additional notes

        Returns:
            Dict with validation result and audit info
        """
        # Get the vulnerability
        vuln = self.db.query(ServiceVulnerability).filter(
            ServiceVulnerability.id == finding_id
        ).first()

        if not vuln:
            raise ValueError(f"Finding {finding_id} not found")

        # Update validation status
        if decision == 'approve':
            vuln.validation_status = 'approved'
            vuln.validated = True
        elif decision == 'reject':
            vuln.validation_status = 'rejected'
            vuln.validated = False
            vuln.false_positive = True
        elif decision == 'override':
            vuln.validation_status = 'approved'
            vuln.validated = True
            # Override requires elevated justification

        vuln.validated_at = datetime.utcnow()
        vuln.validated_by = validated_by

        # Recalculate confidence with new validation status
        if vuln.confidence_factors:
            data_age_days = vuln.confidence_factors.get('data_age_days', 0)
            source_reliability = vuln.confidence_factors.get('source_reliability', 0.5)

            score, factors = self.calculate_confidence_score(
                source_reliability, data_age_days, vuln.validation_status
            )
            vuln.confidence_score = score
            vuln.confidence_factors = factors
            vuln.confidence = self.get_confidence_level(score)

        # Update queue item if exists
        queue_item = self.repository.get_queue_item_by_finding(finding_id)
        if queue_item:
            queue_item.status = 'completed'
            queue_item.reviewed_at = datetime.utcnow()
            queue_item.review_notes = f"{decision}: {justification}"
            if reviewer_notes:
                queue_item.review_notes += f"\n\nNotes: {reviewer_notes}"

        self.db.commit()

        # Return result with audit trail
        return {
            'success': True,
            'finding_id': str(finding_id),
            'decision': decision,
            'validation_status': vuln.validation_status,
            'confidence_score': vuln.confidence_score,
            'validated_at': vuln.validated_at.isoformat() if vuln.validated_at else None,
            'validated_by': vuln.validated_by,
            'audit_created': True
        }

    def get_source_reliability_score(self, source: str) -> float:
        """Get reliability score for a data source"""
        source_scores = {
            'nvd_api': 1.0,
            'exploitdb_verified': 0.9,
            'cached_data': 0.8,
            'version_heuristics': 0.5,
            'manual_links': 0.3
        }
        return source_scores.get(source.lower(), 0.5)
