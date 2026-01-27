from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models import Company


class CompanyRepository(BaseRepository[Company]):
    """Repository for Company operations."""

    def __init__(self, session: Session, user_id: int = None):
        super().__init__(session, Company)
        self.user_id = user_id

    def _base_query(self):
        """Get base query filtered by user_id if set."""
        query = self.session.query(Company)
        if self.user_id is not None:
            query = query.filter(Company.user_id == self.user_id)
        return query

    def get_by_id(self, id: int) -> Optional[Company]:
        """Get a single record by ID, filtered by user."""
        return self._base_query().filter(Company.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Company]:
        """Get all records with pagination, filtered by user."""
        return self._base_query().offset(offset).limit(limit).all()

    def create(self, **kwargs) -> Company:
        """Create a new record with user_id auto-set."""
        if self.user_id is not None:
            kwargs['user_id'] = self.user_id
        return super().create(**kwargs)

    def search_by_name(self, name: str) -> List[Company]:
        """Search companies by name (case-insensitive partial match)."""
        return self._base_query().filter(
            Company.name.ilike(f"%{name}%")
        ).all()

    def get_by_industry(self, industry: str) -> List[Company]:
        """Get all companies in a specific industry."""
        return self._base_query().filter(
            Company.industry.ilike(f"%{industry}%")
        ).all()

    def get_with_active_jobs(self) -> List[Company]:
        """Get companies that have active job postings."""
        from ..models import Job
        return self._base_query().join(Company.jobs).filter(
            Job.is_active == True
        ).distinct().all()

    def get_with_contacts(self) -> List[Company]:
        """Get companies where you have contacts."""
        return self._base_query().filter(
            Company.contacts.any()
        ).all()

    def count(self) -> int:
        """Get total count of records for user."""
        return self._base_query().count()
