from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models import Job


class JobRepository(BaseRepository[Job]):
    """Repository for Job operations."""

    def __init__(self, session: Session):
        super().__init__(session, Job)

    def get_by_company(self, company_id: int) -> List[Job]:
        """Get all jobs for a company."""
        return self.session.query(Job).filter(Job.company_id == company_id).all()

    def get_active_jobs(self) -> List[Job]:
        """Get all active job postings."""
        return self.session.query(Job).filter(Job.is_active == True).all()

    def search_by_title(self, title: str) -> List[Job]:
        """Search jobs by title (case-insensitive partial match)."""
        return self.session.query(Job).filter(
            Job.title.ilike(f"%{title}%")
        ).all()

    def get_remote_jobs(self) -> List[Job]:
        """Get all remote jobs."""
        return self.session.query(Job).filter(Job.remote_type == "remote").all()

    def get_by_salary_range(self, min_salary: int, max_salary: int = None) -> List[Job]:
        """Get jobs within a salary range."""
        query = self.session.query(Job).filter(Job.salary_max >= min_salary)
        if max_salary:
            query = query.filter(Job.salary_min <= max_salary)
        return query.all()

    def get_by_source(self, source: str) -> List[Job]:
        """Get jobs by source (LinkedIn, Indeed, referral, etc.)."""
        return self.session.query(Job).filter(
            Job.source.ilike(f"%{source}%")
        ).all()

    def deactivate(self, job_id: int) -> Optional[Job]:
        """Mark a job as no longer active."""
        return self.update(job_id, is_active=False)
