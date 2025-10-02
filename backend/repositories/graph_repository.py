"""
Graph repository for querying network topology data.

This repository provides optimized database queries for retrieving hosts,
services, and vulnerability data needed for network graph generation.
"""

from typing import List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from models.host import Host
from models.service import Service
from models.service_vulnerability import ServiceVulnerability
from models.vulnerability import Vulnerability, Severity


class GraphRepository:
    """Repository for graph data access with optimized queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_project_hosts_with_services(self, project_id: UUID) -> List[Host]:
        """
        Fetch all hosts with their services for a project.

        Uses eager loading to avoid N+1 queries by loading:
        - Host -> Services relationship in a single query

        Args:
            project_id: UUID of the project

        Returns:
            List of Host objects with services eagerly loaded
        """
        return (
            self.session.query(Host)
            .filter(Host.project_id == project_id)
            .options(joinedload(Host.services))
            .all()
        )

    def get_vulnerabilities_by_service(self, service_ids: List[UUID]) -> dict:
        """
        Get vulnerability data for multiple services.

        Queries the service_vulnerabilities join table to find all vulnerabilities
        associated with the given services, grouped by service_id.

        Args:
            service_ids: List of service UUIDs

        Returns:
            Dictionary mapping service_id to list of vulnerability data:
            {
                service_id: [
                    {
                        'severity': 'critical',
                        'cve_id': 'CVE-2024-1234',
                        'cvss_score': 9.8,
                        'exploit_available': True
                    },
                    ...
                ]
            }
        """
        if not service_ids:
            return {}

        # Query service vulnerabilities with joined vulnerability data
        results = (
            self.session.query(
                ServiceVulnerability.service_id,
                Vulnerability.severity,
                Vulnerability.cve_id,
                Vulnerability.cvss_score,
                Vulnerability.exploit_available
            )
            .join(Vulnerability, ServiceVulnerability.vulnerability_id == Vulnerability.id)
            .filter(ServiceVulnerability.service_id.in_(service_ids))
            .filter(ServiceVulnerability.false_positive == False)  # Exclude false positives
            .all()
        )

        # Group by service_id
        vuln_by_service = {}
        for row in results:
            service_id = row.service_id
            if service_id not in vuln_by_service:
                vuln_by_service[service_id] = []

            vuln_by_service[service_id].append({
                'severity': row.severity.value if isinstance(row.severity, Severity) else row.severity,
                'cve_id': row.cve_id,
                'cvss_score': row.cvss_score,
                'exploit_available': row.exploit_available
            })

        return vuln_by_service

    def get_vulnerability_summary_by_service(self, service_ids: List[UUID]) -> dict:
        """
        Get aggregated vulnerability counts and max severity for services.

        Optimized query that returns summary statistics without fetching
        all vulnerability details.

        Args:
            service_ids: List of service UUIDs

        Returns:
            Dictionary mapping service_id to summary:
            {
                service_id: {
                    'vuln_count': 5,
                    'max_severity': 'critical',
                    'has_exploit': True
                }
            }
        """
        if not service_ids:
            return {}

        # Query vulnerability counts and max severity per service
        results = (
            self.session.query(
                ServiceVulnerability.service_id,
                func.count(ServiceVulnerability.vulnerability_id).label('vuln_count'),
                func.max(Vulnerability.cvss_score).label('max_cvss'),
                func.max(Vulnerability.exploit_available).label('has_exploit')  # Use max instead of bool_or for SQLite compatibility
            )
            .join(Vulnerability, ServiceVulnerability.vulnerability_id == Vulnerability.id)
            .filter(ServiceVulnerability.service_id.in_(service_ids))
            .filter(ServiceVulnerability.false_positive == False)
            .group_by(ServiceVulnerability.service_id)
            .all()
        )

        # Get severity mapping for each service (requires separate query for enum)
        severity_map = {}
        for service_id in service_ids:
            severity_query = (
                self.session.query(Vulnerability.severity)
                .join(ServiceVulnerability, ServiceVulnerability.vulnerability_id == Vulnerability.id)
                .filter(ServiceVulnerability.service_id == service_id)
                .filter(ServiceVulnerability.false_positive == False)
                .order_by(
                    case(
                        (Vulnerability.severity == Severity.CRITICAL, 1),
                        (Vulnerability.severity == Severity.HIGH, 2),
                        (Vulnerability.severity == Severity.MEDIUM, 3),
                        (Vulnerability.severity == Severity.LOW, 4),
                        (Vulnerability.severity == Severity.INFO, 5),
                        else_=6
                    )
                )
                .first()
            )
            if severity_query:
                severity_map[service_id] = severity_query[0].value

        # Build summary dict
        summary = {}
        for row in results:
            service_id = row.service_id
            summary[service_id] = {
                'vuln_count': row.vuln_count,
                'max_severity': severity_map.get(service_id, 'info'),
                'has_exploit': row.has_exploit or False
            }

        return summary
