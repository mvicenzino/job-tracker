from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .base import BaseRepository
from ..models import Application, ApplicationStatus, Job, Company


class ApplicationRepository(BaseRepository[Application]):
    """Repository for Application operations."""

    def __init__(self, session: Session):
        super().__init__(session, Application)

    def get_by_status(self, status: ApplicationStatus) -> List[Application]:
        """Get all applications with a specific status."""
        return self.session.query(Application).filter(
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
        return self.session.query(Application).filter(
            Application.status.notin_(inactive_statuses)
        ).order_by(desc(Application.updated_at)).all()

    def get_by_job(self, job_id: int) -> List[Application]:
        """Get all applications for a specific job."""
        return self.session.query(Application).filter(
            Application.job_id == job_id
        ).all()

    def get_recent(self, days: int = 30) -> List[Application]:
        """Get applications from the last N days."""
        cutoff = date.today() - timedelta(days=days)
        return self.session.query(Application).filter(
            Application.date_applied >= cutoff
        ).order_by(desc(Application.date_applied)).all()

    def get_awaiting_response(self, days_threshold: int = 14) -> List[Application]:
        """Get applications that have been waiting for a response."""
        cutoff = date.today() - timedelta(days=days_threshold)
        return self.session.query(Application).filter(
            Application.status == ApplicationStatus.APPLIED,
            Application.date_applied <= cutoff,
            Application.date_response.is_(None)
        ).all()

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
        total = self.count()
        stats = {'total': total, 'by_status': {}}

        for status in ApplicationStatus:
            count = self.session.query(Application).filter(
                Application.status == status
            ).count()
            if count > 0:
                stats['by_status'][status.value] = count

        return stats

    def get_with_company_info(self) -> List[tuple]:
        """Get applications with company and job info."""
        return self.session.query(Application, Job, Company).join(
            Job, Application.job_id == Job.id
        ).join(
            Company, Job.company_id == Company.id
        ).order_by(desc(Application.updated_at)).all()
