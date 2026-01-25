"""Tests for the data models and database operations."""
import os
import tempfile
import pytest
from datetime import datetime, date, timedelta

from src.database.connection import DatabaseConnection
from src.models import (
    Company, Job, Application, ApplicationStatus,
    Contact, ContactType, Event, EventType, Note, Tag
)


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = DatabaseConnection(db_path)
    db.create_tables()
    yield db

    # Cleanup
    db.drop_tables()
    os.unlink(db_path)


@pytest.fixture
def session(db):
    """Get a database session for testing."""
    session = db.get_session()
    yield session
    session.close()


class TestCompanyModel:
    """Tests for Company model."""

    def test_create_company(self, session):
        """Test creating a basic company."""
        company = Company(
            name="Acme Corp",
            website="https://acme.com",
            industry="Technology",
            location="San Francisco, CA"
        )
        session.add(company)
        session.commit()

        assert company.id is not None
        assert company.name == "Acme Corp"
        assert company.created_at is not None

    def test_company_with_all_fields(self, session):
        """Test company with all optional fields."""
        company = Company(
            name="Tech Giants Inc",
            website="https://techgiants.com",
            industry="Software",
            size="500+",
            location="New York, NY",
            description="A leading tech company",
            culture_notes="Great work-life balance",
            glassdoor_rating="4.5",
            linkedin_url="https://linkedin.com/company/techgiants"
        )
        session.add(company)
        session.commit()

        retrieved = session.query(Company).filter_by(name="Tech Giants Inc").first()
        assert retrieved.size == "500+"
        assert retrieved.culture_notes == "Great work-life balance"


class TestJobModel:
    """Tests for Job model."""

    def test_create_job_with_company(self, session):
        """Test creating a job linked to a company."""
        company = Company(name="Startup XYZ")
        session.add(company)
        session.flush()

        job = Job(
            company_id=company.id,
            title="Senior Developer",
            salary_min=120000,
            salary_max=180000,
            remote_type="hybrid",
            location="Austin, TX"
        )
        session.add(job)
        session.commit()

        assert job.id is not None
        assert job.company.name == "Startup XYZ"
        assert job.is_active is True

    def test_company_job_relationship(self, session):
        """Test bidirectional relationship between company and jobs."""
        company = Company(name="Multi-Job Corp")
        job1 = Job(title="Engineer", company=company)
        job2 = Job(title="Designer", company=company)
        session.add_all([company, job1, job2])
        session.commit()

        assert len(company.jobs) == 2
        assert job1.company == company


class TestApplicationModel:
    """Tests for Application model."""

    def test_create_application(self, session):
        """Test creating an application."""
        company = Company(name="Dream Company")
        job = Job(title="Dream Job", company=company)
        session.add_all([company, job])
        session.flush()

        application = Application(
            job_id=job.id,
            status=ApplicationStatus.APPLIED,
            date_applied=date.today(),
            excitement_level=5
        )
        session.add(application)
        session.commit()

        assert application.id is not None
        assert application.status == ApplicationStatus.APPLIED

    def test_application_status_progression(self, session):
        """Test updating application status through stages."""
        company = Company(name="Test Company")
        job = Job(title="Test Position", company=company)
        application = Application(job=job, status=ApplicationStatus.INTERESTED)
        session.add_all([company, job, application])
        session.commit()

        # Progress through statuses
        application.status = ApplicationStatus.APPLIED
        application.date_applied = date.today()
        session.commit()

        application.status = ApplicationStatus.SCREENING
        session.commit()

        application.status = ApplicationStatus.INTERVIEWING
        session.commit()

        assert application.status == ApplicationStatus.INTERVIEWING

    def test_application_with_referral(self, session):
        """Test application with a referral contact."""
        company = Company(name="Referral Corp")
        contact = Contact(name="John Smith", company=company, contact_type=ContactType.REFERRAL)
        job = Job(title="Referred Position", company=company)
        session.add_all([company, contact, job])
        session.flush()

        application = Application(
            job=job,
            status=ApplicationStatus.APPLIED,
            referral_contact_id=contact.id
        )
        session.add(application)
        session.commit()

        assert application.referral_contact.name == "John Smith"


class TestContactModel:
    """Tests for Contact model."""

    def test_create_contact(self, session):
        """Test creating a contact."""
        contact = Contact(
            name="Jane Doe",
            email="jane@example.com",
            title="Engineering Manager",
            contact_type=ContactType.HIRING_MANAGER
        )
        session.add(contact)
        session.commit()

        assert contact.id is not None
        assert contact.contact_type == ContactType.HIRING_MANAGER

    def test_contact_with_company(self, session):
        """Test contact linked to a company."""
        company = Company(name="Network Inc")
        contact = Contact(
            name="Bob Johnson",
            company=company,
            contact_type=ContactType.EMPLOYEE,
            relationship_strength=4
        )
        session.add_all([company, contact])
        session.commit()

        assert contact.company.name == "Network Inc"
        assert company.contacts[0].name == "Bob Johnson"

    def test_contact_followup_tracking(self, session):
        """Test tracking contact follow-up dates."""
        contact = Contact(
            name="Recruiter Amy",
            contact_type=ContactType.RECRUITER,
            last_contact_date=date.today() - timedelta(days=7),
            next_followup_date=date.today() + timedelta(days=7)
        )
        session.add(contact)
        session.commit()

        assert contact.next_followup_date > contact.last_contact_date


class TestEventModel:
    """Tests for Event model."""

    def test_create_interview_event(self, session):
        """Test creating an interview event."""
        company = Company(name="Interview Corp")
        job = Job(title="Interview Position", company=company)
        application = Application(job=job, status=ApplicationStatus.INTERVIEWING)
        session.add_all([company, job, application])
        session.flush()

        event = Event(
            application_id=application.id,
            title="Technical Interview Round 1",
            event_type=EventType.TECHNICAL_INTERVIEW,
            start_time=datetime.now() + timedelta(days=3),
            end_time=datetime.now() + timedelta(days=3, hours=1),
            meeting_link="https://zoom.us/j/12345",
            prep_notes="Review algorithms and data structures"
        )
        session.add(event)
        session.commit()

        assert event.id is not None
        assert event.application.job.title == "Interview Position"

    def test_event_with_contact(self, session):
        """Test event linked to a contact."""
        contact = Contact(name="Coffee Chat Contact")
        event = Event(
            title="Coffee chat with contact",
            event_type=EventType.COFFEE_CHAT,
            contact=contact,
            start_time=datetime.now() + timedelta(days=1),
            location="Blue Bottle Coffee"
        )
        session.add_all([contact, event])
        session.commit()

        assert event.contact.name == "Coffee Chat Contact"

    def test_event_completion(self, session):
        """Test marking an event as completed."""
        event = Event(
            title="Phone Screen",
            event_type=EventType.PHONE_SCREEN,
            start_time=datetime.now() - timedelta(hours=2)
        )
        session.add(event)
        session.commit()

        event.completed = True
        event.went_well = True
        event.outcome_notes = "Great conversation, moving to next round"
        session.commit()

        assert event.completed is True
        assert event.went_well is True


class TestNoteModel:
    """Tests for Note model."""

    def test_create_note_for_company(self, session):
        """Test creating a note attached to a company."""
        company = Company(name="Noted Company")
        note = Note(
            company=company,
            title="Research Notes",
            content="Found interesting info about their tech stack",
            note_type="research"
        )
        session.add_all([company, note])
        session.commit()

        assert note.id is not None
        assert company.notes[0].title == "Research Notes"

    def test_create_note_for_application(self, session):
        """Test creating a note attached to an application."""
        company = Company(name="App Note Corp")
        job = Job(title="Noted Position", company=company)
        application = Application(job=job)
        note = Note(
            application=application,
            title="Interview Prep",
            content="Research company values and recent news"
        )
        session.add_all([company, job, application, note])
        session.commit()

        assert application.notes[0].content == "Research company values and recent news"


class TestTagModel:
    """Tests for Tag model."""

    def test_create_tag(self, session):
        """Test creating a tag."""
        tag = Tag(
            name="high-priority",
            color="#FF0000",
            description="High priority applications"
        )
        session.add(tag)
        session.commit()

        assert tag.id is not None
        assert tag.name == "high-priority"

    def test_tag_uniqueness(self, session):
        """Test that tag names must be unique."""
        tag1 = Tag(name="unique-tag")
        session.add(tag1)
        session.commit()

        tag2 = Tag(name="unique-tag")
        session.add(tag2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestCascadeDeletes:
    """Tests for cascade delete behavior."""

    def test_delete_company_cascades_to_jobs(self, session):
        """Test that deleting a company deletes its jobs."""
        company = Company(name="Cascade Corp")
        job = Job(title="Cascade Job", company=company)
        session.add_all([company, job])
        session.commit()

        job_id = job.id
        session.delete(company)
        session.commit()

        assert session.query(Job).filter_by(id=job_id).first() is None

    def test_delete_job_cascades_to_applications(self, session):
        """Test that deleting a job deletes its applications."""
        company = Company(name="Delete Corp")
        job = Job(title="Delete Job", company=company)
        application = Application(job=job)
        session.add_all([company, job, application])
        session.commit()

        app_id = application.id
        session.delete(job)
        session.commit()

        assert session.query(Application).filter_by(id=app_id).first() is None


class TestDatabaseConnection:
    """Tests for database connection management."""

    def test_session_scope_commits(self, db):
        """Test that session_scope commits on success."""
        with db.session_scope() as session:
            company = Company(name="Scope Test Corp")
            session.add(company)

        # Verify in new session
        with db.session_scope() as session:
            found = session.query(Company).filter_by(name="Scope Test Corp").first()
            assert found is not None

    def test_session_scope_rollback_on_error(self, db):
        """Test that session_scope rolls back on error."""
        try:
            with db.session_scope() as session:
                company = Company(name="Rollback Corp")
                session.add(company)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify not committed
        with db.session_scope() as session:
            found = session.query(Company).filter_by(name="Rollback Corp").first()
            assert found is None
