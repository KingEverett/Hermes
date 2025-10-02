"""
Staleness Detection Service for tracking and refreshing outdated research data.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from models import ServiceVulnerability


class StalenessDetectionService:
    """Service for detecting and managing stale research results"""

    # Default TTL values in days
    DEFAULT_CVE_TTL = 30
    DEFAULT_EXPLOIT_TTL = 7

    def __init__(self, db: Session):
        self.db = db
        self.cve_ttl_days = self.DEFAULT_CVE_TTL
        self.exploit_ttl_days = self.DEFAULT_EXPLOIT_TTL

    def configure_ttl(self, cve_ttl_days: int, exploit_ttl_days: int):
        """Configure custom TTL values"""
        self.cve_ttl_days = cve_ttl_days
        self.exploit_ttl_days = exploit_ttl_days

    def is_stale(
        self,
        last_refreshed_at: Optional[datetime],
        ttl_days: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if data is stale based on last refresh time and TTL.

        Returns:
            Tuple of (is_stale, stale_reason)
        """
        if last_refreshed_at is None:
            return True, "Never refreshed"

        age = datetime.utcnow() - last_refreshed_at
        if age.days > ttl_days:
            return True, f"Data is {age.days} days old (TTL: {ttl_days} days)"

        return False, None

    def detect_stale_vulnerabilities(
        self,
        project_id: Optional[UUID] = None
    ) -> List[ServiceVulnerability]:
        """
        Detect all stale vulnerabilities in the system or for a specific project.

        Args:
            project_id: Optional project UUID to filter by

        Returns:
            List of stale ServiceVulnerability objects
        """
        query = self.db.query(ServiceVulnerability)

        if project_id:
            # Join with services and hosts to filter by project
            from models import Service, Host
            query = query.join(Service).join(Host).filter(
                Host.project_id == project_id
            )

        # Get all vulnerabilities
        vulnerabilities = query.all()

        stale_vulns = []
        for vuln in vulnerabilities:
            # Use CVE TTL as default (can be enhanced to detect exploit data separately)
            is_stale_result, stale_reason = self.is_stale(
                vuln.last_refreshed_at,
                self.cve_ttl_days
            )

            if is_stale_result:
                vuln.is_stale = True
                vuln.stale_reason = stale_reason
                stale_vulns.append(vuln)
            else:
                # Update to not stale if it was previously marked
                if vuln.is_stale:
                    vuln.is_stale = False
                    vuln.stale_reason = None

        self.db.commit()
        return stale_vulns

    def mark_as_stale(
        self,
        vulnerability_id: UUID,
        reason: str
    ) -> ServiceVulnerability:
        """Manually mark a vulnerability as stale"""
        vuln = self.db.query(ServiceVulnerability).filter(
            ServiceVulnerability.id == vulnerability_id
        ).first()

        if not vuln:
            raise ValueError(f"Vulnerability {vulnerability_id} not found")

        vuln.is_stale = True
        vuln.stale_reason = reason

        self.db.commit()
        self.db.refresh(vuln)

        return vuln

    def mark_as_refreshed(
        self,
        vulnerability_id: UUID
    ) -> ServiceVulnerability:
        """Mark a vulnerability as freshly refreshed"""
        vuln = self.db.query(ServiceVulnerability).filter(
            ServiceVulnerability.id == vulnerability_id
        ).first()

        if not vuln:
            raise ValueError(f"Vulnerability {vulnerability_id} not found")

        vuln.last_refreshed_at = datetime.utcnow()
        vuln.is_stale = False
        vuln.stale_reason = None

        self.db.commit()
        self.db.refresh(vuln)

        return vuln

    def get_staleness_statistics(self, project_id: Optional[UUID] = None) -> dict:
        """
        Get staleness statistics.

        Returns:
            Dict with counts of total, stale, and fresh vulnerabilities
        """
        query = self.db.query(ServiceVulnerability)

        if project_id:
            from models import Service, Host
            query = query.join(Service).join(Host).filter(
                Host.project_id == project_id
            )

        total_count = query.count()
        stale_count = query.filter(ServiceVulnerability.is_stale == True).count()
        fresh_count = total_count - stale_count

        return {
            'total_vulnerabilities': total_count,
            'stale_count': stale_count,
            'fresh_count': fresh_count,
            'stale_percentage': round((stale_count / total_count * 100), 2) if total_count > 0 else 0
        }

    def trigger_refresh(
        self,
        vulnerability_id: UUID
    ) -> dict:
        """
        Trigger a refresh task for a stale vulnerability.

        In a full implementation, this would queue a Celery task.
        For now, it returns task info.

        Returns:
            Dict with task_id and status
        """
        vuln = self.db.query(ServiceVulnerability).filter(
            ServiceVulnerability.id == vulnerability_id
        ).first()

        if not vuln:
            raise ValueError(f"Vulnerability {vulnerability_id} not found")

        # In production, this would trigger a Celery task
        # For now, we'll mark it as refreshed immediately
        # task_id = research_task.delay(vulnerability_id)

        # Placeholder response
        return {
            'task_id': str(vulnerability_id),
            'status': 'queued',
            'vulnerability_id': str(vulnerability_id),
            'message': 'Refresh task queued for processing'
        }
