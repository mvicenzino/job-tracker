from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .base import BaseRepository
from ..models import ResumeVersion


class ResumeVersionRepository(BaseRepository[ResumeVersion]):
    """Repository for ResumeVersion operations."""

    def __init__(self, session: Session, user_id: int = None):
        super().__init__(session, ResumeVersion)
        self.user_id = user_id

    def _base_query(self):
        """Get base query filtered by user_id if set."""
        query = self.session.query(ResumeVersion)
        if self.user_id is not None:
            query = query.filter(ResumeVersion.user_id == self.user_id)
        return query

    def get_by_id(self, id: int) -> Optional[ResumeVersion]:
        """Get a single record by ID, filtered by user."""
        return self._base_query().filter(ResumeVersion.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[ResumeVersion]:
        """Get all records with pagination, filtered by user."""
        return self._base_query().order_by(desc(ResumeVersion.updated_at)).offset(offset).limit(limit).all()

    def create(self, **kwargs) -> ResumeVersion:
        """Create a new record with user_id auto-set."""
        if self.user_id is not None:
            kwargs['user_id'] = self.user_id
        return super().create(**kwargs)

    def get_by_name(self, name: str) -> Optional[ResumeVersion]:
        """Get a resume version by name."""
        return self._base_query().filter(ResumeVersion.name == name).first()

    def get_usage_count(self, resume_version_id: int) -> int:
        """Get the number of applications using this resume version."""
        from ..models import Application
        return self.session.query(Application).filter(
            Application.resume_version_id == resume_version_id
        ).count()
