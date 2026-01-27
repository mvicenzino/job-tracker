"""High-level service for job hunt operations."""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models import (
    Company, Job, Application, ApplicationStatus,
    Contact, ContactType, Event, EventType, Note, Tag
)
from ..repositories import (
    CompanyRepository, JobRepository, ApplicationRepository,
    ContactRepository, EventRepository, NoteRepository, TagRepository
)


class JobHuntService:
    """
    High-level service that coordinates job hunt operations.
    Provides workflow-oriented methods that may span multiple repositories.
    """

    def __init__(self, session: Session, user_id: int = None):
        self.session = session
        self.user_id = user_id
        self.companies = CompanyRepository(session, user_id=user_id)
        self.jobs = JobRepository(session)
        self.applications = ApplicationRepository(session)
        self.contacts = ContactRepository(session, user_id=user_id)
        self.events = EventRepository(session)
        self.notes = NoteRepository(session)
        self.tags = TagRepository(session)

    # === Company Operations ===

    def add_company(self, name: str, **kwargs) -> Company:
        """Add a new company to track."""
        company = self.companies.create(name=name, **kwargs)
        self.session.commit()
        return company

    def find_companies(self, search: str = None, industry: str = None) -> List[Company]:
        """Find companies by name or industry."""
        if search:
            return self.companies.search_by_name(search)
        if industry:
            return self.companies.get_by_industry(industry)
        return self.companies.get_all()

    # === Job Operations ===

    def add_job(self, company_id: int = None, company_name: str = None,
                title: str = None, **kwargs) -> Job:
        """
        Add a new job posting. Creates company if needed.
        """
        if company_id is None and company_name:
            # Find or create company
            companies = self.companies.search_by_name(company_name)
            if companies:
                company_id = companies[0].id
            else:
                company = self.companies.create(name=company_name)
                company_id = company.id

        job = self.jobs.create(company_id=company_id, title=title, **kwargs)
        self.session.commit()
        return job

    def find_jobs(self, search: str = None, remote_only: bool = False,
                  min_salary: int = None) -> List[Job]:
        """Find jobs with various filters."""
        if search:
            return self.jobs.search_by_title(search)
        if remote_only:
            return self.jobs.get_remote_jobs()
        if min_salary:
            return self.jobs.get_by_salary_range(min_salary)
        return self.jobs.get_active_jobs()

    # === Application Operations ===

    def apply_to_job(self, job_id: int, **kwargs) -> Application:
        """
        Create a new application for a job.
        Automatically sets status to APPLIED and records today's date.
        """
        app = self.applications.create(
            job_id=job_id,
            status=ApplicationStatus.APPLIED,
            date_applied=date.today(),
            **kwargs
        )
        self.session.commit()
        return app

    def quick_apply(self, company_name: str, job_title: str,
                   job_url: str = None, source: str = None) -> Application:
        """
        Quick workflow: Add company, job, and application in one go.
        """
        # Find or create company
        companies = self.companies.search_by_name(company_name)
        if companies:
            company = companies[0]
        else:
            company = self.companies.create(name=company_name)

        # Create job
        job = self.jobs.create(
            company_id=company.id,
            title=job_title,
            job_url=job_url,
            source=source
        )

        # Create application
        app = self.applications.create(
            job_id=job.id,
            status=ApplicationStatus.APPLIED,
            date_applied=date.today()
        )

        self.session.commit()
        return app

    def update_application_status(self, app_id: int,
                                  status: ApplicationStatus) -> Optional[Application]:
        """Update an application's status."""
        app = self.applications.update_status(app_id, status)
        self.session.commit()
        return app

    def get_pipeline(self) -> Dict[str, List[Application]]:
        """Get applications organized by status (pipeline view)."""
        pipeline = {}
        for status in ApplicationStatus:
            apps = self.applications.get_by_status(status)
            if apps:
                pipeline[status.value] = apps
        return pipeline

    def get_application_details(self, app_id: int) -> Optional[Dict[str, Any]]:
        """Get full details of an application including related data."""
        app = self.applications.get_by_id(app_id)
        if not app:
            return None

        return {
            'application': app,
            'job': app.job,
            'company': app.job.company,
            'events': self.events.get_by_application(app_id),
            'notes': self.notes.get_by_application(app_id),
            'referral': app.referral_contact
        }

    # === Contact Operations ===

    def add_contact(self, name: str, company_id: int = None,
                   company_name: str = None, **kwargs) -> Contact:
        """Add a new contact. Optionally links to company."""
        if company_id is None and company_name:
            companies = self.companies.search_by_name(company_name)
            if companies:
                company_id = companies[0].id

        contact = self.contacts.create(name=name, company_id=company_id, **kwargs)
        self.session.commit()
        return contact

    def log_contact_interaction(self, contact_id: int,
                               followup_days: int = None,
                               note: str = None) -> Contact:
        """Log an interaction with a contact."""
        contact = self.contacts.update_last_contact(contact_id, followup_days)

        if note:
            self.notes.create(
                contact_id=contact_id,
                content=note,
                note_type="interaction"
            )

        self.session.commit()
        return contact

    def get_networking_todos(self) -> Dict[str, List[Contact]]:
        """Get contacts organized by action needed."""
        return {
            'need_followup': self.contacts.get_needing_followup(),
            'going_stale': self.contacts.get_stale_contacts(days=30),
            'recruiters': self.contacts.get_recruiters()
        }

    # === Event/Schedule Operations ===

    def schedule_event(self, title: str, start_time: datetime,
                      application_id: int = None, contact_id: int = None,
                      event_type: EventType = EventType.OTHER,
                      **kwargs) -> Event:
        """Schedule a new event."""
        event = self.events.create(
            title=title,
            start_time=start_time,
            application_id=application_id,
            contact_id=contact_id,
            event_type=event_type,
            **kwargs
        )
        self.session.commit()
        return event

    def schedule_interview(self, application_id: int, start_time: datetime,
                          interview_type: EventType = EventType.VIDEO_INTERVIEW,
                          **kwargs) -> Event:
        """Schedule an interview for an application."""
        app = self.applications.get_by_id(application_id)
        if app and app.status in [ApplicationStatus.APPLIED, ApplicationStatus.SCREENING]:
            app.status = ApplicationStatus.INTERVIEWING
            if not app.date_response:
                app.date_response = date.today()

        event = self.events.create(
            title=f"Interview: {app.job.title} at {app.job.company.name}",
            start_time=start_time,
            application_id=application_id,
            event_type=interview_type,
            **kwargs
        )

        self.session.commit()
        return event

    def complete_event(self, event_id: int, went_well: bool,
                      notes: str = None) -> Optional[Event]:
        """Mark an event as completed with outcome."""
        event = self.events.mark_complete(event_id, went_well, notes)
        self.session.commit()
        return event

    def get_schedule(self, days: int = 7) -> Dict[str, List[Event]]:
        """Get upcoming schedule organized by day."""
        upcoming = self.events.get_upcoming(days=days)
        schedule = {}

        for event in upcoming:
            day_key = event.start_time.strftime("%Y-%m-%d (%A)")
            if day_key not in schedule:
                schedule[day_key] = []
            schedule[day_key].append(event)

        return schedule

    # === Dashboard/Overview ===

    def get_dashboard(self) -> Dict[str, Any]:
        """Get overview dashboard data."""
        today_events = self.events.get_today()
        upcoming_events = self.events.get_upcoming(days=7)
        followups_needed = self.contacts.get_needing_followup()
        active_apps = self.applications.get_active_applications()
        app_stats = self.applications.get_stats()
        stale_apps = self.applications.get_awaiting_response(days_threshold=14)

        return {
            'summary': {
                'active_applications': len(active_apps),
                'total_applications': app_stats['total'],
                'events_today': len(today_events),
                'events_this_week': len(upcoming_events),
                'contacts_need_followup': len(followups_needed),
                'apps_awaiting_response': len(stale_apps)
            },
            'today': today_events,
            'upcoming': upcoming_events[:5],  # Next 5 events
            'needs_attention': {
                'stale_applications': stale_apps,
                'followup_contacts': followups_needed[:5]
            },
            'stats': app_stats
        }

    # === Notes ===

    def add_note(self, content: str, title: str = None,
                company_id: int = None, job_id: int = None,
                application_id: int = None, contact_id: int = None,
                event_id: int = None, note_type: str = "general") -> Note:
        """Add a note to any entity."""
        note = self.notes.create(
            content=content,
            title=title,
            company_id=company_id,
            job_id=job_id,
            application_id=application_id,
            contact_id=contact_id,
            event_id=event_id,
            note_type=note_type
        )
        self.session.commit()
        return note

    def search_notes(self, query: str) -> List[Note]:
        """Search all notes."""
        return self.notes.search(query)

    # === Tags ===

    def tag_entity(self, entity_type: str, entity_id: int,
                  tag_name: str, tag_color: str = None):
        """Add a tag to an entity."""
        tag = self.tags.get_or_create(tag_name, tag_color)
        self.tags.add_tag_to_entity(tag.id, entity_type, entity_id)
        self.session.commit()

    def get_tags(self, entity_type: str, entity_id: int) -> List[Tag]:
        """Get tags for an entity."""
        return self.tags.get_entity_tags(entity_type, entity_id)
