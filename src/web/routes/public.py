"""Public routes: landing, privacy, terms, demo."""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import current_user, login_user

from ...services import JobHuntService
from ...models import ApplicationStatus, EventType, ContactType, User

bp = Blueprint('public', __name__)


@bp.route('/')
def landing():
    """Landing page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('landing.html')


@bp.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('privacy.html')


@bp.route('/terms')
def terms():
    """Terms of Service page."""
    return render_template('terms.html')


@bp.route('/demo')
def demo():
    """Demo mode - log in as demo user with sample data."""
    DEMO_EMAIL = 'demo@stride-jobs.com'
    DEMO_PASSWORD = 'demo-user-2024'

    db = current_app.extensions['db']
    session = db.get_session()
    try:
        # Find or create demo user
        demo_user = session.query(User).filter(User.email == DEMO_EMAIL).first()

        if not demo_user:
            demo_user = User(email=DEMO_EMAIL)
            demo_user.set_password(DEMO_PASSWORD)
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)

        # Check if demo data needs to be created
        service = JobHuntService(session, user_id=demo_user.id)
        existing_apps = service.applications.get_all()

        if len(existing_apps) == 0:
            # Clear any partial data from failed previous attempts
            for c in service.companies.get_all():
                session.delete(c)
            for ct in service.contacts.get_all():
                session.delete(ct)
            session.commit()
            # Create sample companies
            companies_data = [
                {'name': 'TechCorp', 'industry': 'Technology', 'size': '1000-5000', 'location': 'San Francisco, CA', 'website': 'https://techcorp.example.com', 'description': 'Leading enterprise software company'},
                {'name': 'StartupXYZ', 'industry': 'SaaS', 'size': '50-200', 'location': 'New York, NY', 'website': 'https://startupxyz.example.com', 'description': 'Fast-growing B2B SaaS startup'},
                {'name': 'DataDriven Inc', 'industry': 'Data Analytics', 'size': '200-500', 'location': 'Austin, TX', 'website': 'https://datadriven.example.com', 'description': 'AI-powered analytics platform'},
                {'name': 'CloudScale', 'industry': 'Cloud Infrastructure', 'size': '500-1000', 'location': 'Seattle, WA', 'website': 'https://cloudscale.example.com', 'description': 'Enterprise cloud solutions'},
                {'name': 'FinTech Pro', 'industry': 'Financial Services', 'size': '100-300', 'location': 'Chicago, IL', 'website': 'https://fintechpro.example.com', 'description': 'Modern banking platform'},
                {'name': 'GreenEnergy Labs', 'industry': 'CleanTech', 'size': '50-100', 'location': 'Denver, CO', 'website': 'https://greenenergy.example.com', 'description': 'Renewable energy technology'},
                {'name': 'Nexus AI', 'industry': 'Artificial Intelligence', 'size': '100-500', 'location': 'Boston, MA', 'website': 'https://nexusai.example.com', 'description': 'Enterprise AI solutions'},
                {'name': 'Quantum Systems', 'industry': 'Enterprise Software', 'size': '500-2000', 'location': 'Portland, OR', 'website': 'https://quantumsys.example.com', 'description': 'Next-gen enterprise platform'},
            ]

            companies = []
            for data in companies_data:
                company = service.add_company(**data)
                companies.append(company)

            # Create sample jobs and applications
            jobs_data = [
                {'company': companies[0], 'title': 'Senior Software Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 180000, 'salary_max': 220000, 'source': 'LinkedIn'},
                {'company': companies[1], 'title': 'Full Stack Developer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 140000, 'salary_max': 170000, 'source': 'Referral'},
                {'company': companies[2], 'title': 'Data Engineer', 'location': 'Austin, TX', 'remote_type': 'onsite', 'salary_min': 150000, 'salary_max': 180000, 'source': 'Indeed'},
                {'company': companies[3], 'title': 'DevOps Engineer', 'location': 'Seattle, WA', 'remote_type': 'hybrid', 'salary_min': 160000, 'salary_max': 190000, 'source': 'Company Website'},
                {'company': companies[4], 'title': 'Backend Engineer', 'location': 'Chicago, IL', 'remote_type': 'hybrid', 'salary_min': 145000, 'salary_max': 175000, 'source': 'LinkedIn'},
                {'company': companies[5], 'title': 'Software Architect', 'location': 'Denver, CO', 'remote_type': 'remote', 'salary_min': 190000, 'salary_max': 230000, 'source': 'Recruiter'},
                {'company': companies[6], 'title': 'ML Engineer', 'location': 'Boston, MA', 'remote_type': 'hybrid', 'salary_min': 165000, 'salary_max': 195000, 'source': 'LinkedIn'},
                {'company': companies[7], 'title': 'Platform Engineer', 'location': 'Portland, OR', 'remote_type': 'remote', 'salary_min': 155000, 'salary_max': 185000, 'source': 'Indeed'},
            ]

            # Create jobs
            jobs = []
            for data in jobs_data:
                company = data.pop('company')
                job = service.jobs.create(company_id=company.id, **data)
                jobs.append(job)

            # Create applications with various statuses
            statuses = [
                ApplicationStatus.INTERVIEWING,
                ApplicationStatus.OFFER,
                ApplicationStatus.SCREENING,
                ApplicationStatus.APPLIED,
                ApplicationStatus.INTERESTED,
                ApplicationStatus.FINAL_ROUND,
                ApplicationStatus.APPLIED,
                ApplicationStatus.APPLIED,
            ]

            apps = []
            for i, (job, status) in enumerate(zip(jobs, statuses)):
                app = service.apply_to_job(job_id=job.id)
                service.update_application_status(app.id, status)
                apps.append(app)

            # Backdate APPLIED applications so they appear as stale (14+ days)
            for app in apps:
                if app.status == ApplicationStatus.APPLIED:
                    app.date_applied = date.today() - timedelta(days=20)

            # Create sample contacts
            contacts_data = [
                {'name': 'Sarah Chen', 'company_name': 'TechCorp', 'title': 'Engineering Manager', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'sarah.chen@example.com', 'linkedin_url': 'https://linkedin.com/in/sarahchen'},
                {'name': 'Mike Johnson', 'company_name': 'StartupXYZ', 'title': 'Senior Recruiter', 'contact_type': ContactType.RECRUITER, 'email': 'mike.j@example.com', 'linkedin_url': 'https://linkedin.com/in/mikejohnson'},
                {'name': 'Emily Park', 'company_name': 'DataDriven Inc', 'title': 'Tech Lead', 'contact_type': ContactType.EMPLOYEE, 'email': 'emily.park@example.com', 'linkedin_url': 'https://linkedin.com/in/emilypark'},
                {'name': 'James Wilson', 'company_name': 'CloudScale', 'title': 'VP of Engineering', 'contact_type': ContactType.REFERRAL, 'email': 'james.w@example.com', 'linkedin_url': 'https://linkedin.com/in/jameswilson'},
                {'name': 'Lisa Martinez', 'company_name': 'FinTech Pro', 'title': 'HR Director', 'contact_type': ContactType.RECRUITER, 'email': 'lisa.m@example.com', 'linkedin_url': 'https://linkedin.com/in/lisamartinez'},
            ]

            created_contacts = []
            for data in contacts_data:
                created_contacts.append(service.add_contact(**data))

            # Set follow-up dates on some contacts so they appear in "Needs Attention"
            created_contacts[0].next_followup_date = date.today() - timedelta(days=1)
            created_contacts[0].last_contact_date = date.today() - timedelta(days=8)
            created_contacts[2].next_followup_date = date.today()
            created_contacts[2].last_contact_date = date.today() - timedelta(days=5)
            created_contacts[3].next_followup_date = date.today() - timedelta(days=2)
            created_contacts[3].last_contact_date = date.today() - timedelta(days=10)

            # Create sample events
            today_base = datetime.now().replace(minute=0, second=0, microsecond=0)
            events_data = [
                # Today's events
                {'title': 'Phone Screen - FinTech Pro', 'event_type': EventType.PHONE_SCREEN, 'start_time': today_base.replace(hour=10)},
                {'title': 'Lunch Chat - James Wilson', 'event_type': EventType.COFFEE_CHAT, 'start_time': today_base.replace(hour=12, minute=30)},
                {'title': 'Recruiter Call - GreenEnergy Labs', 'event_type': EventType.PHONE_SCREEN, 'start_time': today_base.replace(hour=15)},
                # Upcoming events
                {'title': 'Coffee Chat - Emily Park', 'event_type': EventType.COFFEE_CHAT, 'start_time': today_base + timedelta(days=1, hours=10)},
                {'title': 'Technical Interview - TechCorp', 'event_type': EventType.TECHNICAL_INTERVIEW, 'start_time': today_base + timedelta(days=2, hours=10)},
                {'title': 'Follow up with Mike', 'event_type': EventType.FOLLOW_UP, 'start_time': today_base + timedelta(days=3, hours=10)},
                {'title': 'Culture Fit Call - StartupXYZ', 'event_type': EventType.BEHAVIORAL_INTERVIEW, 'start_time': today_base + timedelta(days=4, hours=14)},
                {'title': 'Final Round - DataDriven', 'event_type': EventType.PANEL_INTERVIEW, 'start_time': today_base + timedelta(days=7, hours=11)},
            ]

            for data in events_data:
                service.schedule_event(**data)

            session.commit()

        # Log in as demo user
        login_user(demo_user, remember=False)
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        session.rollback()
        import traceback
        return f'<pre>Demo error: {str(e)}\n\n{traceback.format_exc()}</pre>', 500
    finally:
        session.close()
