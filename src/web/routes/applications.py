"""Application routes: list, new, detail, edit, status, notes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service
from ...models import ApplicationStatus, EventType
from ...services.ai_parser import is_ai_parsing_available

bp = Blueprint('applications', __name__)


@bp.route('/applications')
@login_required
def applications():
    """List all applications with optional search and filter."""
    service, session = get_service()
    try:
        search = request.args.get('search', '').strip()
        status_str = request.args.get('status', '').strip()
        view = request.args.get('view', 'all').strip()

        # Parse status string to enum
        status = None
        if status_str:
            try:
                status = ApplicationStatus(status_str)
            except ValueError:
                pass

        # Define which statuses are "leads" vs "applied"
        lead_statuses = [ApplicationStatus.INTERESTED, ApplicationStatus.PREPARING]
        applied_statuses = [s for s in ApplicationStatus if s not in lead_statuses]

        # Get all apps for counting
        all_apps = service.applications.get_with_company_info()
        
        # Calculate counts
        counts = {
            'all': len(all_apps),
            'leads': len([a for a, j, c in all_apps if a.status in lead_statuses]),
            'applied': len([a for a, j, c in all_apps if a.status in applied_statuses]),
        }

        # Filter by view
        if view == 'leads':
            apps = [a for a in all_apps if a[0].status in lead_statuses]
        elif view == 'applied':
            apps = [a for a in all_apps if a[0].status in applied_statuses]
        else:
            apps = all_apps

        # Apply additional search/status filters
        if search or status:
            apps = service.applications.search_with_company_info(search=search, status=status)
            # Re-filter by view if needed
            if view == 'leads':
                apps = [a for a in apps if a[0].status in lead_statuses]
            elif view == 'applied':
                apps = [a for a in apps if a[0].status in applied_statuses]

        return render_template(
            'applications.html',
            applications=apps,
            search=search,
            status=status_str,
            view=view,
            counts=counts,
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
            resume_version_id = request.form.get('resume_version_id', type=int)

            # If resume_version_id is set but text name isn't, fill it from the version object
            if resume_version_id and not resume_version:
                rv_obj = service.resume_versions.get_by_id(resume_version_id)
                if rv_obj:
                    resume_version = rv_obj.name

            app = service.add_lead(
                company_name=request.form['company'],
                job_title=request.form['title'],
                job_url=request.form.get('url'),
                source=request.form.get('source'),
                company_id=company_id,
                referral_contact_id=referral_contact_id,
                resume_version=resume_version,
                resume_version_id=resume_version_id,
                **job_extras
            )
            flash(f'Lead added for {app.job.title} at {app.job.company.name}!', 'success')
            return redirect(url_for('applications.application_detail', app_id=app.id, new=1))
        finally:
            session.close()

    # GET: read query params for pre-fill
    prefill = {
        'company_name': request.args.get('company_name', ''),
        'company_id': request.args.get('company_id', ''),
        'referral_contact_id': request.args.get('referral_contact_id', ''),
        'referral_name': request.args.get('referral_name', ''),
    }
    # Get previously used resume versions for autocomplete + version objects for dropdown
    service, session = get_service()
    try:
        resume_versions = service.applications.get_resume_versions()
        resume_version_objects = service.resume_versions.get_all() if hasattr(service, 'resume_versions') else []
    finally:
        session.close()
    return render_template('application_form.html', prefill=prefill,
                           resume_versions=resume_versions,
                           resume_version_objects=resume_version_objects)


@bp.route('/applications/<int:app_id>/review')
@login_required
def review_lead(app_id):
    """Review a newly imported lead before adding to pipeline."""
    service, session = get_service()
    try:
        app = service.applications.get_by_id(app_id)
        if not app:
            flash('Application not found.', 'error')
            return redirect(url_for('applications.applications'))
        
        job = app.job
        company = job.company if job else None
        
        return render_template('review_lead.html',
                             application=app,
                             job=job,
                             company=company)
    finally:
        session.close()


@bp.route('/applications/<int:app_id>/confirm', methods=['POST'])
@login_required
def confirm_lead(app_id):
    """Process the lead review decision."""
    service, session = get_service()
    try:
        action = request.form.get('action')
        app = service.applications.get_by_id(app_id)
        
        if not app:
            flash('Application not found.', 'error')
            return redirect(url_for('applications.applications'))
        
        if action == 'delete':
            # Delete the lead
            service.applications.delete(app_id)
            session.commit()
            flash('Lead removed.', 'success')
            return redirect(url_for('jobs.jobs'))
        
        elif action == 'save':
            # Keep as saved job, delete the application
            job = app.job
            if job:
                job.is_flagged = True
            service.applications.delete(app_id)
            session.commit()
            flash('Job saved for later.', 'success')
            return redirect(url_for('jobs.jobs'))
        
        else:  # action == 'add' (Good Fit)
            # Update excitement level and notes
            excitement = request.form.get('excitement_level', type=int)
            notes = request.form.get('notes', '').strip()
            
            if excitement:
                app.excitement_level = excitement
            
            # Add note if provided
            if notes:
                from ...models import Note
                note = Note(
                    user_id=app.user_id,
                    application_id=app.id,
                    content=f"Initial assessment: {notes}"
                )
                session.add(note)
            
            session.commit()
            flash('Lead added to your pipeline!', 'success')
            return redirect(url_for('applications.application_detail', app_id=app_id))
    
    finally:
        session.close()


@bp.route('/applications/<int:app_id>')
@login_required
def application_detail(app_id):
    """View application details."""
    is_new_lead = request.args.get('new') == '1'
    service, session = get_service()
    try:
        details = service.get_application_details(app_id)
        if not details:
            flash('Application not found', 'error')
            return redirect(url_for('applications.applications'))

        # Get resume versions for AI analysis feature
        resume_versions = service.resume_versions.get_all() if hasattr(service, 'resume_versions') else []

        return render_template('application_detail.html',
                             details=details,
                             resume_versions=resume_versions,
                             ai_parsing_enabled=is_ai_parsing_available(),
                             ApplicationStatus=ApplicationStatus,
                             EventType=EventType,
                             is_new_lead=is_new_lead)
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
