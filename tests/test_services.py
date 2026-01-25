"""Tests for the service layer."""
import os
import tempfile
import pytest
from datetime import datetime, date, timedelta

from src.database.connection import DatabaseConnection
from src.models import ApplicationStatus, EventType, ContactType
from src.services import JobHuntService


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = DatabaseConnection(db_path)
    db.create_tables()
    yield db

    db.drop_tables()
    os.unlink(db_path)


@pytest.fixture
def service(db):
    """Get a JobHuntService instance for testing."""
    session = db.get_session()
    svc = JobHuntService(session)
    yield svc
    session.close()


class TestCompanyOperations:
    """Tests for company-related service operations."""

    def test_add_company(self, service):
        company = service.add_company(
            name="Test Corp",
            industry="Technology",
            location="San Francisco"
        )

        assert company.id is not None
        assert company.name == "Test Corp"

    def test_find_companies(self, service):
        service.add_company(name="Alpha Tech")
        service.add_company(name="Beta Tech")
        service.add_company(name="Gamma Corp")

        results = service.find_companies(search="Tech")
        assert len(results) == 2


class TestJobOperations:
    """Tests for job-related service operations."""

    def test_add_job_with_existing_company(self, service):
        company = service.add_company(name="Job Corp")
        job = service.add_job(
            company_id=company.id,
            title="Software Engineer",
            salary_min=100000,
            salary_max=150000
        )

        assert job.id is not None
        assert job.company_id == company.id

    def test_add_job_creates_company(self, service):
        job = service.add_job(
            company_name="New Company",
            title="Designer"
        )

        assert job.id is not None
        assert job.company.name == "New Company"

    def test_find_jobs(self, service):
        company = service.add_company(name="Search Corp")
        service.add_job(company_id=company.id, title="Frontend Developer")
        service.add_job(company_id=company.id, title="Backend Developer")
        service.add_job(company_id=company.id, title="Product Manager")

        results = service.find_jobs(search="Developer")
        assert len(results) == 2


class TestApplicationOperations:
    """Tests for application-related service operations."""

    def test_apply_to_job(self, service):
        company = service.add_company(name="Apply Corp")
        job = service.add_job(company_id=company.id, title="Test Job")

        app = service.apply_to_job(job_id=job.id, excitement_level=4)

        assert app.id is not None
        assert app.status == ApplicationStatus.APPLIED
        assert app.date_applied == date.today()

    def test_quick_apply(self, service):
        app = service.quick_apply(
            company_name="Quick Corp",
            job_title="Quick Position",
            job_url="https://example.com/job",
            source="LinkedIn"
        )

        assert app.id is not None
        assert app.status == ApplicationStatus.APPLIED
        assert app.job.title == "Quick Position"
        assert app.job.company.name == "Quick Corp"

    def test_update_application_status(self, service):
        app = service.quick_apply("Status Corp", "Status Job")

        updated = service.update_application_status(
            app.id,
            ApplicationStatus.SCREENING
        )

        assert updated.status == ApplicationStatus.SCREENING

    def test_get_pipeline(self, service):
        service.quick_apply("Pipeline1", "Job1")
        service.quick_apply("Pipeline2", "Job2")

        app3 = service.quick_apply("Pipeline3", "Job3")
        service.update_application_status(app3.id, ApplicationStatus.INTERVIEWING)

        pipeline = service.get_pipeline()

        assert 'applied' in pipeline
        assert len(pipeline['applied']) == 2
        assert 'interviewing' in pipeline
        assert len(pipeline['interviewing']) == 1

    def test_get_application_details(self, service):
        app = service.quick_apply("Details Corp", "Details Job")

        details = service.get_application_details(app.id)

        assert details['application'] == app
        assert details['job'].title == "Details Job"
        assert details['company'].name == "Details Corp"


class TestContactOperations:
    """Tests for contact-related service operations."""

    def test_add_contact(self, service):
        contact = service.add_contact(
            name="John Doe",
            email="john@example.com",
            contact_type=ContactType.RECRUITER
        )

        assert contact.id is not None
        assert contact.name == "John Doe"

    def test_add_contact_with_company(self, service):
        company = service.add_company(name="Contact Corp")
        contact = service.add_contact(
            name="Jane Smith",
            company_id=company.id
        )

        assert contact.company_id == company.id

    def test_add_contact_finds_company(self, service):
        service.add_company(name="Existing Corp")
        contact = service.add_contact(
            name="Bob Jones",
            company_name="Existing Corp"
        )

        assert contact.company is not None
        assert contact.company.name == "Existing Corp"

    def test_log_contact_interaction(self, service):
        contact = service.add_contact(name="Interact Contact")

        updated = service.log_contact_interaction(
            contact.id,
            followup_days=14,
            note="Had a great conversation about opportunities"
        )

        assert updated.last_contact_date == date.today()
        assert updated.next_followup_date == date.today() + timedelta(days=14)

    def test_get_networking_todos(self, service):
        # Contact needing followup
        contact1 = service.add_contact(name="Followup Contact")
        contact1.next_followup_date = date.today() - timedelta(days=1)

        # Recruiter
        service.add_contact(name="Recruiter", contact_type=ContactType.RECRUITER)

        service.session.commit()

        todos = service.get_networking_todos()

        assert len(todos['need_followup']) == 1
        assert len(todos['recruiters']) == 1


class TestEventOperations:
    """Tests for event/schedule-related service operations."""

    def test_schedule_event(self, service):
        event = service.schedule_event(
            title="Coffee Chat",
            start_time=datetime.now() + timedelta(days=2),
            event_type=EventType.COFFEE_CHAT
        )

        assert event.id is not None
        assert event.title == "Coffee Chat"

    def test_schedule_interview(self, service):
        app = service.quick_apply("Interview Corp", "Interview Job")
        interview_time = datetime.now() + timedelta(days=5)

        event = service.schedule_interview(
            application_id=app.id,
            start_time=interview_time,
            interview_type=EventType.TECHNICAL_INTERVIEW,
            prep_notes="Review algorithms"
        )

        assert event.id is not None
        assert event.application_id == app.id
        assert "Interview Corp" in event.title

        # Check that application status was updated
        assert app.status == ApplicationStatus.INTERVIEWING

    def test_complete_event(self, service):
        event = service.schedule_event(
            title="Complete Me",
            start_time=datetime.now() - timedelta(hours=2)
        )

        completed = service.complete_event(
            event.id,
            went_well=True,
            notes="Great conversation!"
        )

        assert completed.completed is True
        assert completed.went_well is True

    def test_get_schedule(self, service):
        now = datetime.now()
        service.schedule_event(
            title="Tomorrow Event",
            start_time=now + timedelta(days=1)
        )
        service.schedule_event(
            title="Day After Event",
            start_time=now + timedelta(days=2)
        )

        schedule = service.get_schedule(days=7)

        assert len(schedule) == 2  # Two different days


class TestDashboard:
    """Tests for dashboard functionality."""

    def test_get_dashboard(self, service):
        # Add some data
        service.quick_apply("Dashboard Corp 1", "Job 1")
        service.quick_apply("Dashboard Corp 2", "Job 2")

        contact = service.add_contact(name="Dashboard Contact")
        contact.next_followup_date = date.today()
        service.session.commit()

        service.schedule_event(
            title="Today Event",
            start_time=datetime.now().replace(hour=15, minute=0)
        )

        dashboard = service.get_dashboard()

        assert dashboard['summary']['active_applications'] == 2
        assert dashboard['summary']['total_applications'] == 2
        assert 'stats' in dashboard
        assert 'today' in dashboard


class TestNotes:
    """Tests for notes functionality."""

    def test_add_note(self, service):
        company = service.add_company(name="Note Corp")
        note = service.add_note(
            content="Interesting company culture",
            title="Culture Notes",
            company_id=company.id,
            note_type="research"
        )

        assert note.id is not None
        assert note.company_id == company.id

    def test_search_notes(self, service):
        service.add_note(content="Python and Django expertise")
        service.add_note(content="React and TypeScript skills")

        results = service.search_notes("Python")
        assert len(results) == 1


class TestTags:
    """Tests for tagging functionality."""

    def test_tag_entity(self, service):
        company = service.add_company(name="Tagged Corp")

        service.tag_entity("company", company.id, "high-priority", "#FF0000")
        service.tag_entity("company", company.id, "tech", "#0000FF")

        tags = service.get_tags("company", company.id)
        assert len(tags) == 2
        tag_names = [t.name for t in tags]
        assert "high-priority" in tag_names
        assert "tech" in tag_names
