from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta, UTC

from models.default_credential import DefaultCredential, CredentialRisk
from .base import BaseRepository


class DefaultCredentialRepository(BaseRepository[DefaultCredential]):
    """Repository for default credential findings data access."""

    def __init__(self, db: Session):
        super().__init__(db, DefaultCredential)

    def find_by_service_id(self, service_id: str) -> List[DefaultCredential]:
        """Find all default credentials for a specific service."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.service_id == service_id
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_by_risk_level(self, risk_level: CredentialRisk) -> List[DefaultCredential]:
        """Find credentials by risk level."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.risk_level == risk_level
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_critical_unvalidated(self) -> List[DefaultCredential]:
        """Find critical risk credentials that haven't been validated."""
        return self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.risk_level == CredentialRisk.CRITICAL,
                DefaultCredential.validated == False
            )
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_high_risk_unremediated(self) -> List[DefaultCredential]:
        """Find high risk credentials that haven't been remediated."""
        return self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.risk_level.in_([CredentialRisk.CRITICAL, CredentialRisk.HIGH]),
                DefaultCredential.remediation_completed == False,
                DefaultCredential.false_positive == False
            )
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_by_service_type(self, service_type: str) -> List[DefaultCredential]:
        """Find credentials by service type (ssh, http, ftp, etc.)."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.service_type == service_type
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_by_username(self, username: str) -> List[DefaultCredential]:
        """Find credentials by username."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.username.ilike(f"%{username}%")
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_recent(self, days: int = 7) -> List[DefaultCredential]:
        """Find recently detected credentials."""
        since_date = datetime.now(UTC) - timedelta(days=days)
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.detected_at >= since_date
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_false_positives(self) -> List[DefaultCredential]:
        """Find all credentials marked as false positives."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.false_positive == True
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_validated(self) -> List[DefaultCredential]:
        """Find all validated credentials."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.validated == True
        ).order_by(DefaultCredential.validated_at.desc()).all()

    def find_pending_validation(self) -> List[DefaultCredential]:
        """Find credentials pending validation."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.validated == False
        ).order_by(DefaultCredential.detected_at.desc()).all()

    def find_by_confidence_threshold(self, min_confidence: float) -> List[DefaultCredential]:
        """Find credentials above a confidence threshold."""
        return self.session.query(DefaultCredential).filter(
            DefaultCredential.confidence >= min_confidence
        ).order_by(DefaultCredential.confidence.desc()).all()

    def find_duplicate_credentials(self, service_id: str, username: str, password: str) -> Optional[DefaultCredential]:
        """Find if this credential combination already exists for this service."""
        return self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.service_id == service_id,
                DefaultCredential.username == username,
                DefaultCredential.password == password
            )
        ).first()

    def mark_as_validated(self, credential_id: str, notes: str = None) -> bool:
        """Mark a credential as validated."""
        credential = self.get_by_id(credential_id)
        if credential:
            credential.validated = True
            credential.validated_at = datetime.now(UTC)
            if notes:
                credential.remediation_notes = notes
            self.session.commit()
            return True
        return False

    def mark_as_false_positive(self, credential_id: str, notes: str = None) -> bool:
        """Mark a credential as false positive."""
        credential = self.get_by_id(credential_id)
        if credential:
            credential.false_positive = True
            credential.validated = True
            credential.validated_at = datetime.now(UTC)
            if notes:
                credential.remediation_notes = notes
            self.session.commit()
            return True
        return False

    def mark_as_remediated(self, credential_id: str, notes: str = None) -> bool:
        """Mark a credential issue as remediated."""
        credential = self.get_by_id(credential_id)
        if credential:
            credential.remediation_completed = True
            credential.remediated_at = datetime.now(UTC)
            if notes:
                credential.remediation_notes = notes
            self.session.commit()
            return True
        return False

    def bulk_validate_low_confidence(self, max_confidence: float = 0.5) -> int:
        """Bulk validate low confidence detections. Returns count of updated records."""
        updated = self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.confidence <= max_confidence,
                DefaultCredential.validated == False,
                DefaultCredential.risk_level == CredentialRisk.LOW
            )
        ).update({
            'validated': True,
            'validated_at': datetime.now(UTC),
            'remediation_notes': f'Auto-validated: Low confidence detection (< {max_confidence})'
        })
        self.session.commit()
        return updated

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about default credentials."""
        total = self.session.query(DefaultCredential).count()

        stats = {
            'total_credentials': total,
            'by_risk_level': {},
            'by_service_type': {},
            'by_status': {
                'pending_validation': 0,
                'validated': 0,
                'false_positives': 0,
                'remediated': 0
            },
            'recent_detections': {
                'last_24h': 0,
                'last_7d': 0,
                'last_30d': 0
            },
            'critical_unremediated': 0,
            'high_risk_unremediated': 0
        }

        # Count by risk level
        for risk_level in CredentialRisk:
            count = self.session.query(DefaultCredential).filter(
                DefaultCredential.risk_level == risk_level
            ).count()
            stats['by_risk_level'][risk_level.value] = count

        # Count by service type
        service_types = self.session.query(DefaultCredential.service_type).distinct().all()
        for (service_type,) in service_types:
            if service_type:
                count = self.session.query(DefaultCredential).filter(
                    DefaultCredential.service_type == service_type
                ).count()
                stats['by_service_type'][service_type] = count

        # Count by status
        stats['by_status']['pending_validation'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.validated == False
        ).count()

        stats['by_status']['validated'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.validated == True
        ).count()

        stats['by_status']['false_positives'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.false_positive == True
        ).count()

        stats['by_status']['remediated'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.remediation_completed == True
        ).count()

        # Recent detections
        now = datetime.now(UTC)
        stats['recent_detections']['last_24h'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.detected_at >= now - timedelta(hours=24)
        ).count()

        stats['recent_detections']['last_7d'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.detected_at >= now - timedelta(days=7)
        ).count()

        stats['recent_detections']['last_30d'] = self.session.query(DefaultCredential).filter(
            DefaultCredential.detected_at >= now - timedelta(days=30)
        ).count()

        # Critical/high risk unremediated
        stats['critical_unremediated'] = self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.risk_level == CredentialRisk.CRITICAL,
                DefaultCredential.remediation_completed == False,
                DefaultCredential.false_positive == False
            )
        ).count()

        stats['high_risk_unremediated'] = self.session.query(DefaultCredential).filter(
            and_(
                DefaultCredential.risk_level.in_([CredentialRisk.CRITICAL, CredentialRisk.HIGH]),
                DefaultCredential.remediation_completed == False,
                DefaultCredential.false_positive == False
            )
        ).count()

        return stats

    def get_service_credential_summary(self, service_id: str) -> Dict[str, Any]:
        """Get summary of default credentials for a service."""
        credentials = self.find_by_service_id(service_id)

        summary = {
            'service_id': service_id,
            'total_credentials': len(credentials),
            'by_risk_level': {level.value: 0 for level in CredentialRisk},
            'validated_count': 0,
            'false_positive_count': 0,
            'remediated_count': 0,
            'critical_pending': 0,
            'high_risk_pending': 0,
            'credentials': []
        }

        for cred in credentials:
            # Count by risk level
            summary['by_risk_level'][cred.risk_level.value] += 1

            # Count status
            if cred.validated:
                summary['validated_count'] += 1
            if cred.false_positive:
                summary['false_positive_count'] += 1
            if cred.remediation_completed:
                summary['remediated_count'] += 1

            # Count pending critical/high risk
            if not cred.validated and not cred.false_positive:
                if cred.risk_level == CredentialRisk.CRITICAL:
                    summary['critical_pending'] += 1
                elif cred.risk_level == CredentialRisk.HIGH:
                    summary['high_risk_pending'] += 1

            # Add credential details
            cred_info = {
                'id': str(cred.id),
                'username': cred.username,
                'password': cred.password,
                'description': cred.description,
                'risk_level': cred.risk_level.value,
                'confidence': cred.confidence,
                'validated': cred.validated,
                'false_positive': cred.false_positive,
                'remediated': cred.remediation_completed,
                'detected_at': cred.detected_at.isoformat() if cred.detected_at else None
            }
            summary['credentials'].append(cred_info)

        return summary

    def create_credential_finding(self, service_id: str, username: str, password: str,
                                description: str, risk_level: CredentialRisk,
                                confidence: float, **kwargs) -> DefaultCredential:
        """Create a new default credential finding."""

        # Check for duplicates
        existing = self.find_duplicate_credentials(service_id, username, password)
        if existing:
            return existing

        credential_data = {
            'service_id': service_id,
            'username': username,
            'password': password,
            'description': description,
            'risk_level': risk_level,
            'confidence': confidence,
            **kwargs
        }

        return self.create(**credential_data)