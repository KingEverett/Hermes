from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def create(self, **kwargs) -> T:
        """Create a new record"""
        try:
            obj = self.model(**kwargs)
            self.session.add(obj)
            self.session.commit()
            self.session.refresh(obj)
            return obj
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, id: UUID) -> Optional[T]:
        """Get a record by ID"""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination"""
        return self.session.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: UUID, **kwargs) -> Optional[T]:
        """Update a record by ID"""
        try:
            obj = self.get_by_id(id)
            if obj:
                for key, value in kwargs.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                self.session.commit()
                self.session.refresh(obj)
            return obj
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, id: UUID) -> bool:
        """Delete a record by ID"""
        try:
            obj = self.get_by_id(id)
            if obj:
                self.session.delete(obj)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID"""
        return self.session.query(self.model).filter(self.model.id == id).first() is not None