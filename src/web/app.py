"""Flask web application for Job Hunt Tracker."""
import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from ..database.connection import DatabaseConnection
from ..services import JobHuntService
from ..models import ApplicationStatus, EventType, ContactType


def create_app(db_path: str = None, database_url: str = None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

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

    def get_service():
        """Get a fresh service instance with a new session."""
        session = db.get_session()
        return JobHuntService(session), session

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

    # Routes
    @app.route('/')
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
    def applications():
        """List all applications."""
        service, session = get_service()
        try:
            apps = service.applications.get_with_company_info()
            return render_template('applications.html', applications=apps)
        finally:
            session.close()

    @app.route('/applications/new', methods=['GET', 'POST'])
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

    @app.route('/contacts')
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

    @app.route('/contacts/new', methods=['GET', 'POST'])
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

    @app.route('/schedule')
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

    return app


def run_server(db_path: str = None, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask development server."""
    app = create_app(db_path)
    app.run(host=host, port=port, debug=debug)
