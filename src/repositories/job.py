from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models import Job


class JobRepository(BaseRepository[Job]):
    """Repository for Job operations."""

    def __init__(self, session: Session, user_id: int = None, workspace_id: int = None):
        super().__init__(session, Job)
        self.user_id = user_id
        self.workspace_id = workspace_id

    def _base_query(self):
        """Get base query filtered by workspace or user."""
        query = self.session.query(Job)
        if self.workspace_id is not None:
            query = query.filter(Job.workspace_id == self.workspace_id)
        elif self.user_id is not None:
            query = query.filter(Job.user_id == self.user_id, Job.workspace_id.is_(None))
        return query

    def get_by_id(self, id: int) -> Optional[Job]:
        """Get a single record by ID, filtered by user."""
        return self._base_query().filter(Job.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Job]:
        """Get all records with pagination, filtered by user."""
        return self._base_query().offset(offset).limit(limit).all()

    def create(self, **kwargs) -> Job:
        """Create a new record with user_id and workspace auto-set."""
        if self.user_id is not None:
            kwargs['user_id'] = self.user_id
        if self.workspace_id is not None:
            kwargs['workspace_id'] = self.workspace_id
            kwargs.setdefault('created_by', self.user_id)
        return super().create(**kwargs)

    def get_by_company(self, company_id: int) -> List[Job]:
        """Get all jobs for a company."""
        return self._base_query().filter(Job.company_id == company_id).all()

    def get_active_jobs(self) -> List[Job]:
        """Get all active job postings."""
        return self._base_query().filter(Job.is_active == True).all()

    def search_by_title(self, title: str) -> List[Job]:
        """Search jobs by title (case-insensitive partial match)."""
        return self._base_query().filter(
            Job.title.ilike(f"%{title}%")
        ).all()

    def get_remote_jobs(self) -> List[Job]:
        """Get all remote jobs."""
        return self._base_query().filter(Job.remote_type == "remote").all()

    def get_by_salary_range(self, min_salary: int, max_salary: int = None) -> List[Job]:
        """Get jobs within a salary range."""
        query = self._base_query().filter(Job.salary_max >= min_salary)
        if max_salary:
            query = query.filter(Job.salary_min <= max_salary)
        return query.all()

    def get_by_source(self, source: str) -> List[Job]:
        """Get jobs by source (LinkedIn, Indeed, referral, etc.)."""
        return self._base_query().filter(
            Job.source.ilike(f"%{source}%")
        ).all()

    def deactivate(self, job_id: int) -> Optional[Job]:
        """Mark a job as no longer active."""
        return self.update(job_id, is_active=False)

    def get_flagged(self) -> List[Job]:
        """Get all flagged/saved jobs."""
        return self._base_query().filter(Job.is_flagged == True).order_by(Job.created_at.desc()).all()

    def toggle_flag(self, job_id: int) -> Optional[Job]:
        """Toggle the flagged status of a job."""
        job = self.get_by_id(job_id)
        if job:
            job.is_flagged = not job.is_flagged
            self.session.flush()
        return job

    def search(self, query: str) -> List[Job]:
        """Search jobs by title or company name."""
        from ..models import Company
        return self._base_query().join(Company).filter(
            (Job.title.ilike(f"%{query}%")) |
            (Company.name.ilike(f"%{query}%"))
        ).order_by(Job.created_at.desc()).all()
