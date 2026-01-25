from typing import TypeVar, Generic, List, Optional, Type
from sqlalchemy.orm import Session
from ..models.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> Optional[T]:
        """Get a single record by ID."""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination."""
        return self.session.query(self.model).offset(offset).limit(limit).all()

    def create(self, **kwargs) -> T:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, id: int, **kwargs) -> Optional[T]:
        """Update a record by ID."""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.flush()
        return instance

    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.flush()
            return True
        return False

    def count(self) -> int:
        """Get total count of records."""
        return self.session.query(self.model).count()

    def exists(self, id: int) -> bool:
        """Check if a record exists."""
        return self.get_by_id(id) is not None
