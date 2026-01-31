"""Tests for the repository layer."""
import os
import tempfile
import pytest
from datetime import datetime, date, timedelta

from src.database.connection import DatabaseConnection
from src.models import (
    User, Company, Job, Application, ApplicationStatus,
    Contact, ContactType, Event, EventType, Note, Tag
)
from src.repositories import (
    CompanyRepository, JobRepository, ApplicationRepository,
    ContactRepository, EventRepository, NoteRepository, TagRepository
)


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
def session(db):
    """Get a database session for testing."""
    session = db.get_session()
    yield session
    session.close()


@pytest.fixture
def test_user(session):
    """Create a test user for testing."""
    user = User(email="test@example.com")
    user.set_password("testpassword")
    session.add(user)
    session.commit()
    return user


class TestCompanyRepository:
    """Tests for CompanyRepository."""

    def test_create_and_get(self, session, test_user):
        repo = CompanyRepository(session, user_id=test_user.id)
        company = repo.create(name="Test Corp", industry="Tech")
        session.commit()

        retrieved = repo.get_by_id(company.id)
        assert retrieved.name == "Test Corp"

    def test_search_by_name(self, session, test_user):
        repo = CompanyRepository(session, user_id=test_user.id)
        repo.create(name="Apple Inc")
        repo.create(name="Pineapple Corp")
        repo.create(name="Microsoft")
        session.commit()

        results = repo.search_by_name("apple")
        assert len(results) == 2

    def test_get_by_industry(self, session, test_user):
        repo = CompanyRepository(session, user_id=test_user.id)
        repo.create(name="TechCo", industry="Technology")
        repo.create(name="FinCo", industry="Finance")
        repo.create(name="TechStart", industry="Technology")
        session.commit()

        results = repo.get_by_industry("Technology")
        assert len(results) == 2

    def test_update(self, session, test_user):
        repo = CompanyRepository(session, user_id=test_user.id)
        company = repo.create(name="Old Name")
        session.commit()

        repo.update(company.id, name="New Name", industry="Updated")
        session.commit()

        retrieved = repo.get_by_id(company.id)
        assert retrieved.name == "New Name"
        assert retrieved.industry == "Updated"

    def test_delete(self, session, test_user):
        repo = CompanyRepository(session, user_id=test_user.id)
        company = repo.create(name="ToDelete")
        session.commit()

        assert repo.delete(company.id) is True
        session.commit()

        assert repo.get_by_id(company.id) is None


class TestJobRepository:
    """Tests for JobRepository."""

    def test_get_active_jobs(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Job Corp")
        job_repo.create(company_id=company.id, title="Active Job", is_active=True)
        job_repo.create(company_id=company.id, title="Inactive Job", is_active=False)
        session.commit()

        active = job_repo.get_active_jobs()
        assert len(active) == 1
        assert active[0].title == "Active Job"

    def test_search_by_title(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Search Corp")
        job_repo.create(company_id=company.id, title="Senior Software Engineer")
        job_repo.create(company_id=company.id, title="Junior Developer")
        job_repo.create(company_id=company.id, title="Software Architect")
        session.commit()

        results = job_repo.search_by_title("software")
        assert len(results) == 2

    def test_get_by_salary_range(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Salary Corp")
        job_repo.create(company_id=company.id, title="Low", salary_min=50000, salary_max=70000)
        job_repo.create(company_id=company.id, title="Mid", salary_min=80000, salary_max=120000)
        job_repo.create(company_id=company.id, title="High", salary_min=150000, salary_max=200000)
        session.commit()

        results = job_repo.get_by_salary_range(100000, 160000)
        assert len(results) == 2  # Mid and High

    def test_deactivate(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Deactivate Corp")
        job = job_repo.create(company_id=company.id, title="Soon Inactive")
        session.commit()

        job_repo.deactivate(job.id)
        session.commit()

        assert job.is_active is False


class TestApplicationRepository:
    """Tests for ApplicationRepository."""

    def test_get_by_status(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)
        app_repo = ApplicationRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Status Corp")
        job = job_repo.create(company_id=company.id, title="Status Job")
        app_repo.create(job_id=job.id, status=ApplicationStatus.APPLIED)
        app_repo.create(job_id=job.id, status=ApplicationStatus.INTERVIEWING)
        app_repo.create(job_id=job.id, status=ApplicationStatus.APPLIED)
        session.commit()

        applied = app_repo.get_by_status(ApplicationStatus.APPLIED)
        assert len(applied) == 2

    def test_get_active_applications(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)
        app_repo = ApplicationRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Active Corp")
        job = job_repo.create(company_id=company.id, title="Active Job")
        app_repo.create(job_id=job.id, status=ApplicationStatus.APPLIED)
        app_repo.create(job_id=job.id, status=ApplicationStatus.REJECTED)
        app_repo.create(job_id=job.id, status=ApplicationStatus.INTERVIEWING)
        session.commit()

        active = app_repo.get_active_applications()
        assert len(active) == 2  # APPLIED and INTERVIEWING

    def test_update_status(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)
        app_repo = ApplicationRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Update Corp")
        job = job_repo.create(company_id=company.id, title="Update Job")
        app = app_repo.create(job_id=job.id, status=ApplicationStatus.INTERESTED)
        session.commit()

        app_repo.update_status(app.id, ApplicationStatus.APPLIED)
        session.commit()

        assert app.status == ApplicationStatus.APPLIED
        assert app.date_applied == date.today()

    def test_get_stats(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        job_repo = JobRepository(session, user_id=test_user.id)
        app_repo = ApplicationRepository(session, user_id=test_user.id)

        company = company_repo.create(name="Stats Corp")
        job = job_repo.create(company_id=company.id, title="Stats Job")
        app_repo.create(job_id=job.id, status=ApplicationStatus.APPLIED)
        app_repo.create(job_id=job.id, status=ApplicationStatus.APPLIED)
        app_repo.create(job_id=job.id, status=ApplicationStatus.REJECTED)
        session.commit()

        stats = app_repo.get_stats()
        assert stats['total'] == 3
        assert stats['by_status']['applied'] == 2
        assert stats['by_status']['rejected'] == 1


class TestContactRepository:
    """Tests for ContactRepository."""

    def test_get_needing_followup(self, session, test_user):
        contact_repo = ContactRepository(session, user_id=test_user.id)

        contact_repo.create(
            name="Past Due",
            next_followup_date=date.today() - timedelta(days=1)
        )
        contact_repo.create(
            name="Due Today",
            next_followup_date=date.today()
        )
        contact_repo.create(
            name="Future",
            next_followup_date=date.today() + timedelta(days=7)
        )
        session.commit()

        needing = contact_repo.get_needing_followup()
        assert len(needing) == 2

    def test_update_last_contact(self, session, test_user):
        contact_repo = ContactRepository(session, user_id=test_user.id)

        contact = contact_repo.create(name="Contact Test")
        session.commit()

        contact_repo.update_last_contact(contact.id, next_followup_days=14)
        session.commit()

        assert contact.last_contact_date == date.today()
        assert contact.next_followup_date == date.today() + timedelta(days=14)

    def test_get_by_type(self, session, test_user):
        contact_repo = ContactRepository(session, user_id=test_user.id)

        contact_repo.create(name="Recruiter 1", contact_type=ContactType.RECRUITER)
        contact_repo.create(name="Recruiter 2", contact_type=ContactType.RECRUITER)
        contact_repo.create(name="Manager", contact_type=ContactType.HIRING_MANAGER)
        session.commit()

        recruiters = contact_repo.get_by_type(ContactType.RECRUITER)
        assert len(recruiters) == 2


class TestEventRepository:
    """Tests for EventRepository."""

    def test_get_upcoming(self, session, test_user):
        event_repo = EventRepository(session, user_id=test_user.id)

        event_repo.create(
            title="Tomorrow",
            start_time=datetime.now() + timedelta(days=1)
        )
        event_repo.create(
            title="Next Week",
            start_time=datetime.now() + timedelta(days=8)
        )
        event_repo.create(
            title="In 3 Days",
            start_time=datetime.now() + timedelta(days=3)
        )
        session.commit()

        upcoming = event_repo.get_upcoming(days=7)
        assert len(upcoming) == 2

    def test_get_today(self, session, test_user):
        event_repo = EventRepository(session, user_id=test_user.id)

        now = datetime.now()
        event_repo.create(
            title="Today Morning",
            start_time=now.replace(hour=9, minute=0)
        )
        event_repo.create(
            title="Today Afternoon",
            start_time=now.replace(hour=14, minute=0)
        )
        event_repo.create(
            title="Tomorrow",
            start_time=now + timedelta(days=1)
        )
        session.commit()

        today = event_repo.get_today()
        assert len(today) == 2

    def test_mark_complete(self, session, test_user):
        event_repo = EventRepository(session, user_id=test_user.id)

        event = event_repo.create(
            title="Complete Me",
            start_time=datetime.now() - timedelta(hours=2)
        )
        session.commit()

        event_repo.mark_complete(event.id, went_well=True, outcome_notes="Great call!")
        session.commit()

        assert event.completed is True
        assert event.went_well is True
        assert event.outcome_notes == "Great call!"

    def test_get_interviews(self, session, test_user):
        event_repo = EventRepository(session, user_id=test_user.id)

        event_repo.create(title="Phone Screen", event_type=EventType.PHONE_SCREEN,
                         start_time=datetime.now())
        event_repo.create(title="Tech Interview", event_type=EventType.TECHNICAL_INTERVIEW,
                         start_time=datetime.now())
        event_repo.create(title="Coffee Chat", event_type=EventType.COFFEE_CHAT,
                         start_time=datetime.now())
        session.commit()

        interviews = event_repo.get_interviews()
        assert len(interviews) == 2


class TestNoteRepository:
    """Tests for NoteRepository."""

    def test_search(self, session):
        note_repo = NoteRepository(session)

        note_repo.create(content="Great company culture and benefits")
        note_repo.create(content="Technical stack uses Python and React")
        note_repo.create(content="Need to prepare for behavioral questions")
        session.commit()

        results = note_repo.search("Python")
        assert len(results) == 1

        results = note_repo.search("company")
        assert len(results) == 1

    def test_get_recent(self, session):
        note_repo = NoteRepository(session)

        for i in range(5):
            note_repo.create(content=f"Note {i}")
        session.commit()

        recent = note_repo.get_recent(limit=3)
        assert len(recent) == 3


class TestTagRepository:
    """Tests for TagRepository."""

    def test_get_or_create(self, session):
        tag_repo = TagRepository(session)

        # First call creates
        tag1 = tag_repo.get_or_create("priority", color="#FF0000")
        session.commit()

        # Second call gets existing
        tag2 = tag_repo.get_or_create("priority")

        assert tag1.id == tag2.id
        assert tag2.color == "#FF0000"

    def test_tag_entity(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        tag_repo = TagRepository(session)

        company = company_repo.create(name="Tagged Corp")
        tag = tag_repo.create(name="tech", color="#0000FF")
        session.commit()

        tag_repo.add_tag_to_entity(tag.id, "company", company.id)
        session.commit()

        tags = tag_repo.get_entity_tags("company", company.id)
        assert len(tags) == 1
        assert tags[0].name == "tech"

    def test_remove_tag_from_entity(self, session, test_user):
        company_repo = CompanyRepository(session, user_id=test_user.id)
        tag_repo = TagRepository(session)

        company = company_repo.create(name="Untagged Corp")
        tag = tag_repo.create(name="remove-me")
        session.commit()

        tag_repo.add_tag_to_entity(tag.id, "company", company.id)
        session.commit()

        tag_repo.remove_tag_from_entity(tag.id, "company", company.id)
        session.commit()

        tags = tag_repo.get_entity_tags("company", company.id)
        assert len(tags) == 0
