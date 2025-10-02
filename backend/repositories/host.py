from sqlalchemy.orm import Session
from models.host import Host
from uuid import UUID
from .base import BaseRepository

class HostRepository(BaseRepository[Host]):
    def __init__(self, session: Session):
        super().__init__(session, Host)

    def get_by_project_id(self, project_id: UUID, skip: int = 0, limit: int = 100):
        """Get hosts by project ID"""
        return (self.session.query(Host)
                .filter(Host.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_ip_address(self, project_id: UUID, ip_address: str):
        """Get host by IP address within a project"""
        return (self.session.query(Host)
                .filter(Host.project_id == project_id, Host.ip_address == ip_address)
                .first())

    def search_by_hostname(self, project_id: UUID, hostname_pattern: str, skip: int = 0, limit: int = 100):
        """Search hosts by hostname pattern within a project"""
        return (self.session.query(Host)
                .filter(Host.project_id == project_id, Host.hostname.contains(hostname_pattern))
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_os_family(self, project_id: UUID, os_family: str, skip: int = 0, limit: int = 100):
        """Get hosts by OS family within a project"""
        return (self.session.query(Host)
                .filter(Host.project_id == project_id, Host.os_family == os_family)
                .offset(skip)
                .limit(limit)
                .all())