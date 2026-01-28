"""Flask web application for Job Hunt Tracker."""
import io
import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from ..database.connection import DatabaseConnection
from ..services import JobHuntService
from ..models import ApplicationStatus, EventType, ContactType, User

# Stable fallback secret key for development (production should set SECRET_KEY env var)
DEFAULT_SECRET_KEY = 'stride-app-dev-key-change-in-production-abc123xyz'


def create_app(db_path: str = None, database_url: str = None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.secret_key = os.environ.get('SECRET_KEY', DEFAULT_SECRET_KEY)

    # Session configuration - keep users logged in for 30 days
    is_production = os.environ.get('VERCEL') or os.environ.get('DATABASE_URL')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = bool(is_production)  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['REMEMBER_COOKIE_SECURE'] = bool(is_production)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB upload limit

    # Database setup - prefer DATABASE_URL for production
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')

    if database_url:
        db = DatabaseConnection(database_url=database_url)
    else:
        if db_path is None:
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".job-hunt-tracker")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "job_hunt.db")
        db = DatabaseConnection(db_path=db_path)

    db.create_tables()

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please sign in to continue.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        session = db.get_session()
        try:
            return session.query(User).get(int(user_id))
        finally:
            session.close()

    def get_service():
        """Get a fresh service instance with a new session for current user."""
        session = db.get_session()
        user_id = current_user.id if current_user.is_authenticated else None
        return JobHuntService(session, user_id=user_id), session

    def get_user_by_api_key(api_key):
        """Get user by API key for API authentication."""
        if not api_key:
            return None
        session = db.get_session()
        try:
            return session.query(User).filter(User.api_key == api_key).first()
        finally:
            session.close()

    def get_service_for_user(user_id):
        """Get a service instance for a specific user."""
        session = db.get_session()
        return JobHuntService(session, user_id=user_id), session

    # Template filters
    @app.template_filter('status_color')
    def status_color(status):
        colors = {
            'interested': '#6b7280',
            'preparing': '#8b5cf6',
            'applied': '#3b82f6',
            'screening': '#06b6d4',
            'interviewing': '#f59e0b',
            'final_round': '#f97316',
            'offer': '#22c55e',
            'negotiating': '#14b8a6',
            'accepted': '#10b981',
            'rejected': '#ef4444',
            'withdrawn': '#9ca3af',
            'ghosted': '#6b7280'
        }
        return colors.get(status, '#6b7280')

    @app.template_filter('event_type_icon')
    def event_type_icon(event_type):
        icons = {
            'phone_screen': '📞',
            'video_interview': '💻',
            'onsite_interview': '🏢',
            'technical_interview': '⚙️',
            'behavioral_interview': '💬',
            'panel_interview': '👥',
            'coffee_chat': '☕',
            'networking_event': '🤝',
            'career_fair': '🎪',
            'follow_up': '📧',
            'offer_call': '🎉',
            'negotiation_call': '💰',
            'application_deadline': '⏰',
            'task_deadline': '📋',
            'reminder': '🔔',
            'other': '📌'
        }
        return icons.get(event_type, '📌')

    # Auth Routes
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration page."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not email or not password:
                flash('Email and password are required.', 'error')
                return render_template('register.html')

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')

            if len(password) < 8:
                flash('Password must be at least 8 characters.', 'error')
                return render_template('register.html')

            session = db.get_session()
            try:
                # Check if user already exists
                existing_user = session.query(User).filter(User.email == email).first()
                if existing_user:
                    flash('An account with this email already exists.', 'error')
                    return render_template('register.html')

                # Create new user
                user = User(email=email)
                user.set_password(password)
                session.add(user)
                session.commit()

                login_user(user, remember=True)
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard'))
            finally:
                session.close()

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login page."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            session = db.get_session()
            try:
                user = session.query(User).filter(User.email == email).first()

                if user and user.check_password(password):
                    login_user(user, remember=True)
                    next_page = request.args.get('next')
                    flash('Logged in successfully!', 'success')
                    return redirect(next_page or url_for('dashboard'))
                else:
                    flash('Invalid email or password.', 'error')
            finally:
                session.close()

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """Log out the current user."""
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('landing'))

    # Public Routes
    @app.route('/')
    def landing():
        """Landing page for unauthenticated users."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')

    @app.route('/privacy')
    def privacy():
        """Privacy Policy page."""
        return render_template('privacy.html')

    @app.route('/terms')
    def terms():
        """Terms of Service page."""
        return render_template('terms.html')

    @app.route('/demo')
    def demo():
        """Demo mode - log in as demo user with sample data."""
        DEMO_EMAIL = 'demo@stride-jobs.com'
        DEMO_PASSWORD = 'demo-user-2024'

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
            return redirect(url_for('dashboard'))
        except Exception as e:
            session.rollback()
            import traceback
            return f'<pre>Demo error: {str(e)}\n\n{traceback.format_exc()}</pre>', 500
        finally:
            session.close()

    @app.route('/settings')
    @login_required
    def settings():
        """User settings page with API key management."""
        return render_template('settings.html')

    @app.route('/settings/api-key', methods=['POST'])
    @login_required
    def generate_api_key():
        """Generate a new API key for the current user."""
        session = db.get_session()
        try:
            user = session.query(User).get(current_user.id)
            user.generate_api_key()
            session.commit()
            flash('New API key generated!', 'success')
        finally:
            session.close()
        return redirect(url_for('settings'))

    @app.route('/settings/resume', methods=['POST'])
    @login_required
    def save_resume():
        """Save resume text from paste or PDF upload."""
        session = db.get_session()
        try:
            user = session.query(User).get(current_user.id)
            mode = request.form.get('resume_mode', 'paste')

            if mode == 'upload':
                file = request.files.get('resume_file')
                if not file or file.filename == '':
                    flash('Please select a PDF file to upload.', 'error')
                    return redirect(url_for('settings'))

                if not file.filename.lower().endswith('.pdf'):
                    flash('Only PDF files are supported.', 'error')
                    return redirect(url_for('settings'))

                try:
                    from PyPDF2 import PdfReader
                    pdf_bytes = file.read()
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    text = ''
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + '\n'
                    text = text.strip()
                except Exception:
                    flash('Could not read PDF file. The file may be corrupted.', 'error')
                    return redirect(url_for('settings'))

                if not text:
                    flash('No text could be extracted from this PDF. It may be image-based. Try pasting your resume text instead.', 'error')
                    return redirect(url_for('settings'))

                user.resume_text = text
                user.resume_filename = file.filename
                session.commit()
                flash('Resume uploaded and saved!', 'success')

            else:  # paste mode
                text = request.form.get('resume_text', '').strip()
                if not text:
                    flash('Please enter your resume text.', 'error')
                    return redirect(url_for('settings'))

                user.resume_text = text
                user.resume_filename = None
                session.commit()
                flash('Resume saved!', 'success')

        finally:
            session.close()
        return redirect(url_for('settings'))

    @app.route('/settings/resume/delete', methods=['POST'])
    @login_required
    def delete_resume():
        """Delete saved resume."""
        session = db.get_session()
        try:
            user = session.query(User).get(current_user.id)
            user.resume_text = None
            user.resume_filename = None
            session.commit()
            flash('Resume removed.', 'success')
        finally:
            session.close()
        return redirect(url_for('settings'))

    # Protected Routes
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard home page."""
        service, session = get_service()
        try:
            data = service.get_dashboard()
            pipeline = service.get_pipeline()
            return render_template('dashboard.html',
                                 dashboard=data,
                                 pipeline=pipeline,
                                 ApplicationStatus=ApplicationStatus)
        finally:
            session.close()

    @app.route('/pipeline')
    @login_required
    def pipeline():
        """Application pipeline view."""
        service, session = get_service()
        try:
            pipeline = service.get_pipeline()
            return render_template('pipeline.html',
                                 pipeline=pipeline,
                                 ApplicationStatus=ApplicationStatus)
        finally:
            session.close()

    @app.route('/applications')
    @login_required
    def applications():
        """List all applications."""
        service, session = get_service()
        try:
            apps = service.applications.get_with_company_info()
            return render_template('applications.html', applications=apps)
        finally:
            session.close()

    @app.route('/applications/new', methods=['GET', 'POST'])
    @login_required
    def new_application():
        """Create a new application (quick apply)."""
        if request.method == 'POST':
            service, session = get_service()
            try:
                app = service.quick_apply(
                    company_name=request.form['company'],
                    job_title=request.form['title'],
                    job_url=request.form.get('url'),
                    source=request.form.get('source')
                )
                flash(f'Application created for {app.job.title} at {app.job.company.name}!', 'success')
                return redirect(url_for('pipeline'))
            finally:
                session.close()
        return render_template('application_form.html')

    @app.route('/applications/<int:app_id>')
    @login_required
    def application_detail(app_id):
        """View application details."""
        service, session = get_service()
        try:
            details = service.get_application_details(app_id)
            if not details:
                flash('Application not found', 'error')
                return redirect(url_for('applications'))
            return render_template('application_detail.html',
                                 details=details,
                                 ApplicationStatus=ApplicationStatus,
                                 EventType=EventType)
        finally:
            session.close()

    @app.route('/applications/<int:app_id>/status', methods=['POST'])
    @login_required
    def update_status(app_id):
        """Update application status."""
        service, session = get_service()
        try:
            status = ApplicationStatus(request.form['status'])
            service.update_application_status(app_id, status)
            flash('Status updated!', 'success')
        finally:
            session.close()
        return redirect(request.referrer or url_for('pipeline'))

    @app.route('/companies')
    @login_required
    def companies():
        """List all companies."""
        service, session = get_service()
        try:
            search = request.args.get('search')
            companies = service.find_companies(search=search)
            return render_template('companies.html', companies=companies, search=search)
        finally:
            session.close()

    @app.route('/companies/new', methods=['GET', 'POST'])
    @login_required
    def new_company():
        """Add a new company."""
        if request.method == 'POST':
            service, session = get_service()
            try:
                company = service.add_company(
                    name=request.form['name'],
                    industry=request.form.get('industry'),
                    location=request.form.get('location'),
                    website=request.form.get('website'),
                    description=request.form.get('description')
                )
                flash(f'Company {company.name} added!', 'success')
                return redirect(url_for('companies'))
            finally:
                session.close()
        return render_template('company_form.html')

    @app.route('/jobs')
    @login_required
    def jobs():
        """List all job listings."""
        service, session = get_service()
        try:
            search = request.args.get('search')
            flagged_only = request.args.get('flagged')
            if search:
                jobs = service.jobs.search(search)
            elif flagged_only:
                jobs = service.jobs.get_flagged()
            else:
                jobs = service.jobs.get_all()
            return render_template('jobs.html',
                                 jobs=jobs,
                                 search=search,
                                 flagged_only=flagged_only)
        finally:
            session.close()

    @app.route('/jobs/new', methods=['GET', 'POST'])
    @login_required
    def new_job():
        """Add a new job listing."""
        service, session = get_service()
        try:
            if request.method == 'POST':
                company_id = request.form.get('company_id')
                if not company_id:
                    # Create company if it doesn't exist
                    company_name = request.form.get('company_name', '').strip()
                    if company_name:
                        existing = service.find_companies(search=company_name)
                        if existing:
                            company_id = existing[0].id
                        else:
                            company = service.companies.create(name=company_name)
                            company_id = company.id

                if company_id:
                    job = service.jobs.create(
                        company_id=int(company_id),
                        title=request.form.get('title', '').strip(),
                        description=request.form.get('description', '').strip(),
                        location=request.form.get('location', '').strip(),
                        remote_type=request.form.get('remote_type'),
                        salary_min=int(request.form.get('salary_min')) if request.form.get('salary_min') else None,
                        salary_max=int(request.form.get('salary_max')) if request.form.get('salary_max') else None,
                        job_url=request.form.get('job_url', '').strip(),
                        source=request.form.get('source', '').strip(),
                        is_flagged=bool(request.form.get('is_flagged'))
                    )
                    flash('Job added successfully!', 'success')
                    return redirect(url_for('jobs'))
                else:
                    flash('Please select or enter a company.', 'error')

            companies = service.companies.get_all()
            return render_template('job_form.html', companies=companies)
        finally:
            session.close()

    @app.route('/jobs/<int:job_id>/flag', methods=['POST'])
    @login_required
    def toggle_job_flag(job_id):
        """Toggle the flagged/saved status of a job."""
        service, session = get_service()
        try:
            job = service.jobs.toggle_flag(job_id)
            if job:
                status = 'saved' if job.is_flagged else 'unsaved'
                flash(f'Job {status}!', 'success')
            return redirect(request.referrer or url_for('jobs'))
        finally:
            session.close()

    @app.route('/contacts')
    @login_required
    def contacts():
        """List all contacts."""
        service, session = get_service()
        try:
            search = request.args.get('search')
            followup = request.args.get('followup')
            if search:
                contacts = service.contacts.search_by_name(search)
            elif followup:
                contacts = service.contacts.get_needing_followup()
            else:
                contacts = service.contacts.get_all()
            return render_template('contacts.html',
                                 contacts=contacts,
                                 search=search,
                                 followup=followup,
                                 today=date.today())
        finally:
            session.close()

    @app.route('/contacts/export')
    @login_required
    def export_contacts_csv():
        """Export contacts to CSV."""
        import csv
        from io import StringIO
        from flask import Response

        service, session = get_service()
        try:
            contacts = service.contacts.get_all()

            # Check if user wants Google Sheets format (opens in browser)
            format_type = request.args.get('format')

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)

            # Header row
            writer.writerow(['Name', 'Email', 'Phone', 'Company', 'Title', 'Type', 'LinkedIn', 'Last Contact', 'Next Follow-up', 'Notes'])

            # Data rows
            for contact in contacts:
                writer.writerow([
                    contact.name,
                    contact.email or '',
                    contact.phone or '',
                    contact.company.name if contact.company else '',
                    contact.title or '',
                    contact.contact_type.value.replace('_', ' ').title(),
                    contact.linkedin_url or '',
                    contact.last_contact_date.strftime('%Y-%m-%d') if contact.last_contact_date else '',
                    contact.next_followup_date.strftime('%Y-%m-%d') if contact.next_followup_date else '',
                    contact.notes or ''
                ])

            csv_content = output.getvalue()
            output.close()

            if format_type == 'sheets':
                # Redirect to Google Sheets with the CSV data
                # This creates a new sheet from CSV
                import urllib.parse
                encoded_csv = urllib.parse.quote(csv_content)
                sheets_url = f"https://docs.google.com/spreadsheets/d/create?title=Stride%20Contacts%20Export"
                # For now, just download - proper Sheets integration requires OAuth
                # Fall back to CSV download
                pass

            # Return as downloadable CSV
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=stride_contacts_{date.today().strftime("%Y%m%d")}.csv'}
            )
        finally:
            session.close()

    @app.route('/contacts/new', methods=['GET', 'POST'])
    @login_required
    def new_contact():
        """Add a new contact."""
        service, session = get_service()
        try:
            if request.method == 'POST':
                contact_type = ContactType(request.form.get('contact_type', 'networking'))
                contact = service.add_contact(
                    name=request.form['name'],
                    company_name=request.form.get('company'),
                    email=request.form.get('email'),
                    phone=request.form.get('phone'),
                    title=request.form.get('title'),
                    contact_type=contact_type,
                    linkedin_url=request.form.get('linkedin_url'),
                    notes=request.form.get('notes')
                )
                flash(f'Contact {contact.name} added!', 'success')
                return redirect(url_for('contacts'))
            companies = service.companies.get_all()
            return render_template('contact_form.html',
                                 companies=companies,
                                 ContactType=ContactType)
        finally:
            session.close()

    @app.route('/contacts/<int:contact_id>/log', methods=['POST'])
    @login_required
    def log_contact(contact_id):
        """Log an interaction with a contact."""
        service, session = get_service()
        try:
            followup_days = request.form.get('followup_days')
            followup_days = int(followup_days) if followup_days else None
            service.log_contact_interaction(
                contact_id=contact_id,
                followup_days=followup_days,
                note=request.form.get('note')
            )
            flash('Interaction logged!', 'success')
        finally:
            session.close()
        return redirect(request.referrer or url_for('contacts'))

    @app.route('/contacts/<int:contact_id>/delete', methods=['POST'])
    @login_required
    def delete_contact(contact_id):
        """Delete a contact."""
        service, session = get_service()
        try:
            contact = service.contacts.get_by_id(contact_id)
            if contact:
                name = contact.name
                service.contacts.delete(contact_id)
                session.commit()
                flash(f'Contact {name} deleted.', 'success')
            else:
                flash('Contact not found.', 'error')
        finally:
            session.close()
        return redirect(url_for('contacts'))

    @app.route('/schedule')
    @login_required
    def schedule():
        """View schedule."""
        service, session = get_service()
        try:
            days = int(request.args.get('days', 14))
            schedule = service.get_schedule(days=days)
            today = service.events.get_today()
            return render_template('schedule.html',
                                 schedule=schedule,
                                 today=today,
                                 days=days)
        finally:
            session.close()

    @app.route('/events/new', methods=['GET', 'POST'])
    @login_required
    def new_event():
        """Schedule a new event."""
        service, session = get_service()
        try:
            if request.method == 'POST':
                start_time = datetime.strptime(
                    f"{request.form['date']} {request.form['time']}",
                    "%Y-%m-%d %H:%M"
                )
                event_type = EventType(request.form.get('event_type', 'other'))

                app_id = request.form.get('application_id')
                contact_id = request.form.get('contact_id')

                event = service.schedule_event(
                    title=request.form['title'],
                    start_time=start_time,
                    event_type=event_type,
                    application_id=int(app_id) if app_id else None,
                    contact_id=int(contact_id) if contact_id else None,
                    location=request.form.get('location'),
                    meeting_link=request.form.get('meeting_link'),
                    prep_notes=request.form.get('prep_notes')
                )
                flash(f'Event "{event.title}" scheduled!', 'success')
                return redirect(url_for('schedule'))

            applications = service.applications.get_active_applications()
            contacts = service.contacts.get_all()
            return render_template('event_form.html',
                                 applications=applications,
                                 contacts=contacts,
                                 EventType=EventType)
        finally:
            session.close()

    @app.route('/events/<int:event_id>/complete', methods=['POST'])
    @login_required
    def complete_event(event_id):
        """Mark an event as complete."""
        service, session = get_service()
        try:
            went_well = request.form.get('went_well')
            if went_well:
                went_well = went_well == 'true'
            service.complete_event(
                event_id=event_id,
                went_well=went_well,
                notes=request.form.get('notes')
            )
            flash('Event marked complete!', 'success')
        finally:
            session.close()
        return redirect(request.referrer or url_for('schedule'))

    @app.route('/interview/new', methods=['GET', 'POST'])
    @login_required
    def new_interview():
        """Schedule an interview."""
        service, session = get_service()
        try:
            if request.method == 'POST':
                start_time = datetime.strptime(
                    f"{request.form['date']} {request.form['time']}",
                    "%Y-%m-%d %H:%M"
                )
                interview_type = EventType(request.form.get('interview_type', 'video_interview'))

                event = service.schedule_interview(
                    application_id=int(request.form['application_id']),
                    start_time=start_time,
                    interview_type=interview_type,
                    meeting_link=request.form.get('meeting_link'),
                    prep_notes=request.form.get('prep_notes')
                )
                flash(f'Interview scheduled!', 'success')
                return redirect(url_for('schedule'))

            applications = service.applications.get_active_applications()
            return render_template('interview_form.html',
                                 applications=applications,
                                 EventType=EventType)
        finally:
            session.close()

    # === Edit Routes ===

    @app.route('/applications/<int:app_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_application(app_id):
        """Edit application details."""
        service, session = get_service()
        try:
            app_obj = service.applications.get_by_id(app_id)
            if not app_obj:
                flash('Application not found', 'error')
                return redirect(url_for('applications'))

            if request.method == 'POST':
                # Update application fields
                updates = {}
                if request.form.get('excitement_level'):
                    updates['excitement_level'] = int(request.form['excitement_level'])
                if request.form.get('resume_version'):
                    updates['resume_version'] = request.form['resume_version']
                if request.form.get('cover_letter'):
                    updates['cover_letter'] = request.form['cover_letter']
                if request.form.get('lessons_learned'):
                    updates['lessons_learned'] = request.form['lessons_learned']

                service.applications.update(app_id, **updates)
                session.commit()
                flash('Application updated!', 'success')
                return redirect(url_for('application_detail', app_id=app_id))

            return render_template('edit_application.html',
                                 app=app_obj,
                                 ApplicationStatus=ApplicationStatus)
        finally:
            session.close()

    @app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_job(job_id):
        """Edit job details."""
        service, session = get_service()
        try:
            job = service.jobs.get_by_id(job_id)
            if not job:
                flash('Job not found', 'error')
                return redirect(url_for('applications'))

            if request.method == 'POST':
                updates = {
                    'title': request.form.get('title', job.title),
                    'description': request.form.get('description'),
                    'requirements': request.form.get('requirements'),
                    'location': request.form.get('location'),
                    'remote_type': request.form.get('remote_type'),
                    'job_url': request.form.get('job_url'),
                    'source': request.form.get('source'),
                }

                salary_min = request.form.get('salary_min')
                salary_max = request.form.get('salary_max')
                if salary_min:
                    updates['salary_min'] = int(salary_min)
                if salary_max:
                    updates['salary_max'] = int(salary_max)

                service.jobs.update(job_id, **updates)
                session.commit()
                flash('Job updated!', 'success')

                # Redirect back to application if we came from there
                app_id = request.args.get('app_id')
                if app_id:
                    return redirect(url_for('application_detail', app_id=app_id))
                return redirect(url_for('jobs'))

            return render_template('edit_job.html', job=job)
        finally:
            session.close()

    @app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_company(company_id):
        """Edit company details."""
        service, session = get_service()
        try:
            company = service.companies.get_by_id(company_id)
            if not company:
                flash('Company not found', 'error')
                return redirect(url_for('companies'))

            if request.method == 'POST':
                updates = {
                    'name': request.form.get('name', company.name),
                    'website': request.form.get('website'),
                    'industry': request.form.get('industry'),
                    'size': request.form.get('size'),
                    'location': request.form.get('location'),
                    'description': request.form.get('description'),
                    'culture_notes': request.form.get('culture_notes'),
                    'glassdoor_rating': request.form.get('glassdoor_rating'),
                    'linkedin_url': request.form.get('linkedin_url'),
                }

                service.companies.update(company_id, **updates)
                session.commit()
                flash('Company updated!', 'success')

                # Redirect back to application if we came from there
                app_id = request.args.get('app_id')
                if app_id:
                    return redirect(url_for('application_detail', app_id=app_id))
                return redirect(url_for('companies'))

            return render_template('edit_company.html', company=company)
        finally:
            session.close()

    @app.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_contact(contact_id):
        """Edit contact details."""
        service, session = get_service()
        try:
            contact = service.contacts.get_by_id(contact_id)
            if not contact:
                flash('Contact not found', 'error')
                return redirect(url_for('contacts'))

            if request.method == 'POST':
                contact_type = ContactType(request.form.get('contact_type', 'networking'))
                updates = {
                    'name': request.form.get('name', contact.name),
                    'email': request.form.get('email'),
                    'phone': request.form.get('phone'),
                    'title': request.form.get('title'),
                    'contact_type': contact_type,
                    'linkedin_url': request.form.get('linkedin_url'),
                    'how_we_met': request.form.get('how_we_met'),
                    'notes': request.form.get('notes'),
                }

                relationship_strength = request.form.get('relationship_strength')
                if relationship_strength:
                    updates['relationship_strength'] = int(relationship_strength)

                service.contacts.update(contact_id, **updates)
                session.commit()
                flash('Contact updated!', 'success')
                return redirect(url_for('contacts'))

            companies = service.companies.get_all()
            return render_template('edit_contact.html',
                                 contact=contact,
                                 companies=companies,
                                 ContactType=ContactType)
        finally:
            session.close()

    @app.route('/applications/<int:app_id>/notes', methods=['POST'])
    @login_required
    def add_application_note(app_id):
        """Add a note to an application."""
        service, session = get_service()
        try:
            service.add_note(
                content=request.form['content'],
                title=request.form.get('title'),
                application_id=app_id,
                note_type=request.form.get('note_type', 'general')
            )
            flash('Note added!', 'success')
        finally:
            session.close()
        return redirect(url_for('application_detail', app_id=app_id))

    # API endpoints for AJAX operations
    @app.route('/api/applications/<int:app_id>/status', methods=['PATCH'])
    @login_required
    def api_update_status(app_id):
        """API: Update application status."""
        service, session = get_service()
        try:
            data = request.get_json()
            status = ApplicationStatus(data['status'])
            app = service.update_application_status(app_id, status)
            if app:
                return jsonify({'success': True, 'status': app.status.value})
            return jsonify({'success': False, 'error': 'Not found'}), 404
        finally:
            session.close()

    @app.route('/api/applications/<int:app_id>', methods=['PATCH'])
    @login_required
    def api_update_application(app_id):
        """API: Update application fields."""
        service, session = get_service()
        try:
            data = request.get_json()
            app = service.applications.update(app_id, **data)
            session.commit()
            if app:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Not found'}), 404
        finally:
            session.close()

    @app.route('/api/jobs/<int:job_id>', methods=['PATCH'])
    @login_required
    def api_update_job(job_id):
        """API: Update job fields."""
        service, session = get_service()
        try:
            data = request.get_json()
            job = service.jobs.update(job_id, **data)
            session.commit()
            if job:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Not found'}), 404
        finally:
            session.close()

    @app.route('/api/companies/<int:company_id>', methods=['PATCH'])
    @login_required
    def api_update_company(company_id):
        """API: Update company fields."""
        service, session = get_service()
        try:
            data = request.get_json()
            company = service.companies.update(company_id, **data)
            session.commit()
            if company:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Not found'}), 404
        finally:
            session.close()

    @app.route('/api/contacts', methods=['POST', 'OPTIONS'])
    def api_create_contact():
        """API: Create a new contact (for Chrome extension)."""
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
            return response

        # Check for API key authentication
        api_key = request.headers.get('X-API-Key')
        user = get_user_by_api_key(api_key) if api_key else None

        # Fall back to session auth
        if not user and current_user.is_authenticated:
            user = current_user

        if not user:
            response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 401

        service, session = get_service_for_user(user.id)
        try:
            data = request.get_json()
            if not data or not data.get('name'):
                response = jsonify({'success': False, 'error': 'Name is required'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            contact_type = ContactType(data.get('contact_type', 'networking'))
            contact = service.add_contact(
                name=data['name'],
                company_name=data.get('company'),
                email=data.get('email'),
                phone=data.get('phone'),
                title=data.get('title'),
                contact_type=contact_type,
                linkedin_url=data.get('linkedin_url'),
                notes=data.get('notes')
            )
            response = jsonify({
                'success': True,
                'contact': {
                    'id': contact.id,
                    'name': contact.name,
                    'company': contact.company.name if contact.company else None
                }
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            response = jsonify({'success': False, 'error': str(e)})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        finally:
            session.close()

    @app.route('/api/companies', methods=['POST', 'OPTIONS'])
    def api_create_company():
        """API: Create a new company (for Chrome extension)."""
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
            return response

        # Check for API key authentication
        api_key = request.headers.get('X-API-Key')
        user = get_user_by_api_key(api_key) if api_key else None

        # Fall back to session auth
        if not user and current_user.is_authenticated:
            user = current_user

        if not user:
            response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 401

        service, session = get_service_for_user(user.id)
        try:
            data = request.get_json()
            if not data or not data.get('name'):
                response = jsonify({'success': False, 'error': 'Company name is required'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            # Check if company already exists
            existing = service.find_companies(search=data['name'])
            if existing and existing[0].name.lower() == data['name'].lower():
                company = existing[0]
                # Update with any new info
                updates = {}
                if data.get('industry') and not company.industry:
                    updates['industry'] = data['industry']
                if data.get('size') and not company.size:
                    updates['size'] = data['size']
                if data.get('location') and not company.location:
                    updates['location'] = data['location']
                if data.get('website') and not company.website:
                    updates['website'] = data['website']
                if data.get('description') and not company.description:
                    updates['description'] = data['description']
                if data.get('linkedin_url') and not company.linkedin_url:
                    updates['linkedin_url'] = data['linkedin_url']
                if updates:
                    service.companies.update(company.id, **updates)
                    session.commit()
                response = jsonify({
                    'success': True,
                    'company': {
                        'id': company.id,
                        'name': company.name
                    },
                    'message': 'Company already exists, updated with new info'
                })
            else:
                company = service.add_company(
                    name=data['name'],
                    industry=data.get('industry'),
                    location=data.get('location'),
                    website=data.get('website'),
                    description=data.get('description'),
                    size=data.get('size'),
                    linkedin_url=data.get('linkedin_url')
                )
                response = jsonify({
                    'success': True,
                    'company': {
                        'id': company.id,
                        'name': company.name
                    }
                })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            response = jsonify({'success': False, 'error': str(e)})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        finally:
            session.close()

    @app.route('/api/jobs', methods=['POST', 'OPTIONS'])
    def api_create_job():
        """API: Create a new job listing (for Chrome extension)."""
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
            return response

        # Check for API key authentication
        api_key = request.headers.get('X-API-Key')
        user = get_user_by_api_key(api_key) if api_key else None

        # Fall back to session auth
        if not user and current_user.is_authenticated:
            user = current_user

        if not user:
            response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 401

        service, session = get_service_for_user(user.id)
        try:
            data = request.get_json()
            if not data or not data.get('title'):
                response = jsonify({'success': False, 'error': 'Job title is required'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            # Find or create company
            company_id = None
            company_name = data.get('company_name', '').strip()
            if company_name:
                existing = service.find_companies(search=company_name)
                if existing:
                    company_id = existing[0].id
                else:
                    company = service.companies.create(name=company_name)
                    company_id = company.id

            if not company_id:
                response = jsonify({'success': False, 'error': 'Company name is required'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            job = service.jobs.create(
                company_id=company_id,
                title=data['title'],
                description=data.get('description', ''),
                location=data.get('location', ''),
                remote_type=data.get('remote_type', ''),
                job_url=data.get('job_url', ''),
                source=data.get('source', 'LinkedIn'),
                is_flagged=data.get('is_flagged', False)
            )
            response = jsonify({
                'success': True,
                'job': {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company.name
                }
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            response = jsonify({'success': False, 'error': str(e)})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        finally:
            session.close()

    return app


def run_server(db_path: str = None, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask development server."""
    app = create_app(db_path)
    app.run(host=host, port=port, debug=debug)
