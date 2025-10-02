from sqlalchemy.orm import Session
from models.service import Service, Protocol
from uuid import UUID
from .base import BaseRepository

class ServiceRepository(BaseRepository[Service]):
    def __init__(self, session: Session):
        super().__init__(session, Service)

    def get_by_host_id(self, host_id: UUID, skip: int = 0, limit: int = 100):
        """Get services by host ID"""
        return (self.session.query(Service)
                .filter(Service.host_id == host_id)
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_port(self, port: int, protocol: Protocol = None, skip: int = 0, limit: int = 100):
        """Get services by port and optional protocol"""
        query = self.session.query(Service).filter(Service.port == port)
        if protocol:
            query = query.filter(Service.protocol == protocol)
        return query.offset(skip).limit(limit).all()

    def get_by_service_name(self, service_name: str, skip: int = 0, limit: int = 100):
        """Get services by service name"""
        return (self.session.query(Service)
                .filter(Service.service_name == service_name)
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_host_and_port(self, host_id: UUID, port: int, protocol: Protocol):
        """Get specific service by host, port, and protocol"""
        return (self.session.query(Service)
                .filter(Service.host_id == host_id,
                       Service.port == port,
                       Service.protocol == protocol)
                .first())

    def find_by_project_id(self, project_id: str):
        """Get all services for a project by joining through hosts"""
        from models.host import Host
        return (self.session.query(Service)
                .join(Host)
                .filter(Host.project_id == project_id)
                .all())