from sqlalchemy.orm import Session
from models.project import Project
from .base import BaseRepository

class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: Session):
        super().__init__(session, Project)

    def get_by_name(self, name: str) -> Project:
        """Get project by name"""
        return self.session.query(Project).filter(Project.name == name).first()

    def search_by_name(self, name_pattern: str, skip: int = 0, limit: int = 100):
        """Search projects by name pattern"""
        return (self.session.query(Project)
                .filter(Project.name.contains(name_pattern))
                .offset(skip)
                .limit(limit)
                .all())