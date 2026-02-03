from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .base import BaseRepository
from ..models import Application, ApplicationStatus, Job, Company


class ApplicationRepository(BaseRepository[Application]):
    """Repository for Application operations."""

    def __init__(self, session: Session, user_id: int = None):
        super().__init__(session, Application)
        self.user_id = user_id

    def _base_query(self):
        """Get base query filtered by user_id if set."""
        query = self.session.query(Application)
        if self.user_id is not None:
            query = query.filter(Application.user_id == self.user_id)
        return query

    def get_by_id(self, id: int) -> Optional[Application]:
        """Get a single record by ID, filtered by user."""
        return self._base_query().filter(Application.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Application]:
        """Get all records with pagination, filtered by user."""
        return self._base_query().offset(offset).limit(limit).all()

    def create(self, **kwargs) -> Application:
        """Create a new record with user_id auto-set."""
        if self.user_id is not None:
            kwargs['user_id'] = self.user_id
        return super().create(**kwargs)

    def get_by_status(self, status: ApplicationStatus) -> List[Application]:
        """Get all applications with a specific status."""
        return self._base_query().filter(
            Application.status == status
        ).all()

    def get_active_applications(self) -> List[Application]:
        """Get all applications that are still in progress."""
        inactive_statuses = [
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.GHOSTED,
            ApplicationStatus.ACCEPTED
        ]
        return self._base_query().filter(
            Application.status.notin_(inactive_statuses)
        ).order_by(desc(Application.updated_at)).all()

    def get_by_job(self, job_id: int) -> List[Application]:
        """Get all applications for a specific job."""
        return self._base_query().filter(
            Application.job_id == job_id
        ).all()

    def get_recent(self, days: int = 30) -> List[Application]:
        """Get applications from the last N days."""
        cutoff = date.today() - timedelta(days=days)
        return self._base_query().filter(
            Application.date_applied >= cutoff
        ).order_by(desc(Application.date_applied)).all()

    def get_awaiting_response(self, days_threshold: int = 14) -> List[Application]:
        """Get applications that have been waiting for a response."""
        cutoff = date.today() - timedelta(days=days_threshold)
        return self._base_query().filter(
            Application.status == ApplicationStatus.APPLIED,
            Application.date_applied <= cutoff,
            Application.date_response.is_(None)
        ).all()

    def get_stale_leads(self, days_threshold: int = 14) -> List[Application]:
        """Get leads in INTERESTED or PREPARING that haven't been updated recently."""
        from datetime import datetime
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        return self._base_query().filter(
            Application.status.in_([ApplicationStatus.INTERESTED, ApplicationStatus.PREPARING]),
            Application.updated_at <= cutoff
        ).order_by(Application.updated_at).all()

    def update_status(self, app_id: int, new_status: ApplicationStatus) -> Optional[Application]:
        """Update application status with automatic date handling."""
        app = self.get_by_id(app_id)
        if app:
            app.status = new_status
            if new_status == ApplicationStatus.APPLIED and not app.date_applied:
                app.date_applied = date.today()
            elif new_status in [ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN,
                               ApplicationStatus.GHOSTED, ApplicationStatus.ACCEPTED]:
                app.date_closed = date.today()
            self.session.flush()
        return app

    def get_stats(self) -> dict:
        """Get application statistics."""
        total = self._base_query().count()
        stats = {'total': total, 'by_status': {}}

        for status in ApplicationStatus:
            count = self._base_query().filter(
                Application.status == status
            ).count()
            if count > 0:
                stats['by_status'][status.value] = count

        return stats

    def get_with_company_info(self) -> List[tuple]:
        """Get applications with company and job info."""
        query = self.session.query(Application, Job, Company).join(
            Job, Application.job_id == Job.id
        ).join(
            Company, Job.company_id == Company.id
        )
        if self.user_id is not None:
            query = query.filter(Application.user_id == self.user_id)
        return query.order_by(desc(Application.updated_at)).all()

    def search_with_company_info(
        self,
        search: Optional[str] = None,
        status: Optional[ApplicationStatus] = None
    ) -> List[tuple]:
        """Search applications with company and job info.

        Args:
            search: Text to search in company name and job title
            status: Filter by application status
        """
        query = self.session.query(Application, Job, Company).join(
            Job, Application.job_id == Job.id
        ).join(
            Company, Job.company_id == Company.id
        )
        if self.user_id is not None:
            query = query.filter(Application.user_id == self.user_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Company.name.ilike(search_term)) | (Job.title.ilike(search_term))
            )

        if status:
            query = query.filter(Application.status == status)

        return query.order_by(desc(Application.updated_at)).all()
