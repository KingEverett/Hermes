from sqlalchemy.orm import Session
from models.scan import Scan, ScanStatus, ToolType
from uuid import UUID
from .base import BaseRepository

class ScanRepository(BaseRepository[Scan]):
    def __init__(self, session: Session):
        super().__init__(session, Scan)

    def get_by_project_id(self, project_id: UUID, skip: int = 0, limit: int = 100):
        """Get scans by project ID"""
        return (self.session.query(Scan)
                .filter(Scan.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_status(self, status: ScanStatus, skip: int = 0, limit: int = 100):
        """Get scans by status"""
        return (self.session.query(Scan)
                .filter(Scan.status == status)
                .offset(skip)
                .limit(limit)
                .all())

    def get_by_tool_type(self, tool_type: ToolType, skip: int = 0, limit: int = 100):
        """Get scans by tool type"""
        return (self.session.query(Scan)
                .filter(Scan.tool_type == tool_type)
                .offset(skip)
                .limit(limit)
                .all())

    def update_status(self, id: UUID, status: ScanStatus, error_details: str = None):
        """Update scan status"""
        update_data = {"status": status}
        if error_details:
            update_data["error_details"] = error_details
        return self.update(id, **update_data)