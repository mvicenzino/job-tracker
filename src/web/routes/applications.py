"""Application routes: list, new, detail, edit, status, notes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service
from ...models import ApplicationStatus, EventType

bp = Blueprint('applications', __name__)


@bp.route('/applications')
@login_required
def applications():
    """List all applications."""
    service, session = get_service()
    try:
        apps = service.applications.get_with_company_info()
        return render_template('applications.html', applications=apps)
    finally:
        session.close()


@bp.route('/applications/new', methods=['GET', 'POST'])
@login_required
def new_application():
    """Add a new lead to the pipeline."""
    if request.method == 'POST':
        service, session = get_service()
        try:
            company_id = request.form.get('company_id', type=int)
            referral_contact_id = request.form.get('referral_contact_id', type=int)
            app = service.add_lead(
                company_name=request.form['company'],
                job_title=request.form['title'],
                job_url=request.form.get('url'),
                source=request.form.get('source'),
                company_id=company_id,
                referral_contact_id=referral_contact_id
            )
            flash(f'Lead added for {app.job.title} at {app.job.company.name}!', 'success')
            return redirect(url_for('dashboard.pipeline'))
        finally:
            session.close()

    # GET: read query params for pre-fill
    prefill = {
        'company_name': request.args.get('company_name', ''),
        'company_id': request.args.get('company_id', ''),
        'referral_contact_id': request.args.get('referral_contact_id', ''),
        'referral_name': request.args.get('referral_name', ''),
    }
    return render_template('application_form.html', prefill=prefill)


@bp.route('/applications/<int:app_id>')
@login_required
def application_detail(app_id):
    """View application details."""
    service, session = get_service()
    try:
        details = service.get_application_details(app_id)
        if not details:
            flash('Application not found', 'error')
            return redirect(url_for('applications.applications'))
        return render_template('application_detail.html',
                             details=details,
                             ApplicationStatus=ApplicationStatus,
                             EventType=EventType)
    finally:
        session.close()


@bp.route('/applications/<int:app_id>/status', methods=['POST'])
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
    return redirect(request.referrer or url_for('dashboard.pipeline'))


@bp.route('/applications/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(app_id):
    """Edit application details."""
    service, session = get_service()
    try:
        app_obj = service.applications.get_by_id(app_id)
        if not app_obj:
            flash('Application not found', 'error')
            return redirect(url_for('applications.applications'))

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
            return redirect(url_for('applications.application_detail', app_id=app_id))

        return render_template('edit_application.html',
                             app=app_obj,
                             ApplicationStatus=ApplicationStatus)
    finally:
        session.close()


@bp.route('/applications/<int:app_id>/notes', methods=['POST'])
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
    return redirect(url_for('applications.application_detail', app_id=app_id))
