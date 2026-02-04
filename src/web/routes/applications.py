"""Application routes: list, new, detail, edit, status, notes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service
from ...models import ApplicationStatus, EventType

bp = Blueprint('applications', __name__)


@bp.route('/applications')
@login_required
def applications():
    """List all applications with optional search and filter."""
    service, session = get_service()
    try:
        search = request.args.get('search', '').strip()
        status_str = request.args.get('status', '').strip()

        # Parse status string to enum
        status = None
        if status_str:
            try:
                status = ApplicationStatus(status_str)
            except ValueError:
                pass

        # Use search method if filters are active, otherwise get all
        if search or status:
            apps = service.applications.search_with_company_info(search=search, status=status)
        else:
            apps = service.applications.get_with_company_info()

        return render_template(
            'applications.html',
            applications=apps,
            search=search,
            status=status_str,
            ApplicationStatus=ApplicationStatus
        )
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

            # Collect optional job detail fields
            job_extras = {}
            if request.form.get('description'):
                job_extras['description'] = request.form['description']
            if request.form.get('requirements'):
                job_extras['requirements'] = request.form['requirements']
            if request.form.get('location'):
                job_extras['location'] = request.form['location']
            if request.form.get('remote_type'):
                job_extras['remote_type'] = request.form['remote_type']
            if request.form.get('salary_min'):
                try:
                    job_extras['salary_min'] = int(request.form['salary_min'])
                except ValueError:
                    pass
            if request.form.get('salary_max'):
                try:
                    job_extras['salary_max'] = int(request.form['salary_max'])
                except ValueError:
                    pass
            if request.form.get('salary_currency'):
                job_extras['salary_currency'] = request.form['salary_currency']

            resume_version = request.form.get('resume_version', '').strip() or None

            app = service.add_lead(
                company_name=request.form['company'],
                job_title=request.form['title'],
                job_url=request.form.get('url'),
                source=request.form.get('source'),
                company_id=company_id,
                referral_contact_id=referral_contact_id,
                resume_version=resume_version,
                **job_extras
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
    # Get previously used resume versions for autocomplete
    service, session = get_service()
    try:
        resume_versions = service.applications.get_resume_versions()
    finally:
        session.close()
    return render_template('application_form.html', prefill=prefill, resume_versions=resume_versions)


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

        resume_versions = service.applications.get_resume_versions()
        return render_template('edit_application.html',
                             app=app_obj,
                             ApplicationStatus=ApplicationStatus,
                             resume_versions=resume_versions)
    finally:
        session.close()


@bp.route('/applications/checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_checklist(item_id):
    """Toggle a checklist item's completed state."""
    service, session = get_service()
    try:
        item = service.toggle_checklist_item(item_id)
        if item:
            return redirect(request.referrer or url_for('applications.application_detail', app_id=item.application_id))
        flash('Checklist item not found', 'error')
        return redirect(request.referrer or url_for('dashboard.pipeline'))
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


@bp.route('/applications/<int:app_id>/archive', methods=['POST'])
@login_required
def archive_application(app_id):
    """Archive an application (soft delete)."""
    service, session = get_service()
    try:
        app = service.applications.get_by_id(app_id)
        if app:
            service.update_application_status(app_id, ApplicationStatus.ARCHIVED)
            flash('Application archived. You can restore it anytime.', 'success')
            return redirect(url_for('dashboard.pipeline'))
        flash('Application not found', 'error')
    finally:
        session.close()
    return redirect(url_for('applications.applications'))


@bp.route('/applications/<int:app_id>/delete', methods=['POST'])
@login_required
def delete_application(app_id):
    """Permanently delete an application."""
    service, session = get_service()
    try:
        app = service.applications.get_by_id(app_id)
        if app:
            job_title = app.job.title
            company_name = app.job.company.name
            service.applications.delete(app_id)
            session.commit()
            flash(f'Application for {job_title} at {company_name} permanently deleted.', 'success')
            return redirect(url_for('dashboard.pipeline'))
        flash('Application not found', 'error')
    finally:
        session.close()
    return redirect(url_for('applications.applications'))
