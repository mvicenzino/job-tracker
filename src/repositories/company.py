from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models import Company


class CompanyRepository(BaseRepository[Company]):
    """Repository for Company operations."""

    def __init__(self, session: Session):
        super().__init__(session, Company)

    def search_by_name(self, name: str) -> List[Company]:
        """Search companies by name (case-insensitive partial match)."""
        return self.session.query(Company).filter(
            Company.name.ilike(f"%{name}%")
        ).all()

    def get_by_industry(self, industry: str) -> List[Company]:
        """Get all companies in a specific industry."""
        return self.session.query(Company).filter(
            Company.industry.ilike(f"%{industry}%")
        ).all()

    def get_with_active_jobs(self) -> List[Company]:
        """Get companies that have active job postings."""
        from ..models import Job
        return self.session.query(Company).join(Company.jobs).filter(
            Job.is_active == True
        ).distinct().all()

    def get_with_contacts(self) -> List[Company]:
        """Get companies where you have contacts."""
        return self.session.query(Company).filter(
            Company.contacts.any()
        ).all()
