"""Settings routes: settings, api key, resume save/delete, setup."""
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from ...models import User

bp = Blueprint('settings', __name__)


@bp.route('/setup')
@login_required
def setup():
    """Chrome extension setup guide page."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        if not user.api_key:
            user.generate_api_key()
            session.commit()
        api_key = user.api_key
    finally:
        session.close()
    server_url = request.url_root.rstrip('/')
    return render_template('setup.html', api_key=api_key, server_url=server_url)


@bp.route('/setup/generate-key', methods=['POST'])
@login_required
def setup_generate_key():
    """Regenerate API key via AJAX for the setup page."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.generate_api_key()
        session.commit()
        return jsonify({'api_key': user.api_key})
    finally:
        session.close()


@bp.route('/settings')
@login_required
def settings():
    """User settings page with API key management."""
    return render_template('settings.html')


@bp.route('/settings/api-key', methods=['POST'])
@login_required
def generate_api_key():
    """Generate a new API key for the current user."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.generate_api_key()
        session.commit()
        flash('New API key generated!', 'success')
    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/resume', methods=['POST'])
@login_required
def save_resume():
    """Save resume text from paste or PDF upload."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        mode = request.form.get('resume_mode', 'paste')

        if mode == 'upload':
            file = request.files.get('resume_file')
            if not file or file.filename == '':
                flash('Please select a PDF file to upload.', 'error')
                return redirect(url_for('settings.settings'))

            if not file.filename.lower().endswith('.pdf'):
                flash('Only PDF files are supported.', 'error')
                return redirect(url_for('settings.settings'))

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
                return redirect(url_for('settings.settings'))

            if not text:
                flash('No text could be extracted from this PDF. It may be image-based. Try pasting your resume text instead.', 'error')
                return redirect(url_for('settings.settings'))

            user.resume_text = text
            user.resume_filename = file.filename
            session.commit()
            flash('Resume uploaded and saved!', 'success')

        else:  # paste mode
            text = request.form.get('resume_text', '').strip()
            if not text:
                flash('Please enter your resume text.', 'error')
                return redirect(url_for('settings.settings'))

            user.resume_text = text
            user.resume_filename = None
            session.commit()
            flash('Resume saved!', 'success')

    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/resume/delete', methods=['POST'])
@login_required
def delete_resume():
    """Delete saved resume."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.resume_text = None
        user.resume_filename = None
        session.commit()
        flash('Resume removed.', 'success')
    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/notifications', methods=['POST'])
@login_required
def save_notifications():
    """Save notification preferences."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        
        # Email digest settings
        user.email_digest_enabled = bool(request.form.get('email_digest_enabled'))
        user.email_digest_frequency = request.form.get('email_digest_frequency', 'weekly')
        
        # In-app notification settings
        user.notify_interview_reminders = bool(request.form.get('notify_interview_reminders'))
        user.notify_follow_up_nudges = bool(request.form.get('notify_follow_up_nudges'))
        
        # Follow-up timing
        try:
            user.follow_up_nudge_days = int(request.form.get('follow_up_nudge_days', 7))
        except (ValueError, TypeError):
            user.follow_up_nudge_days = 7
        
        session.commit()
        flash('Notification settings saved!', 'success')
    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/profile', methods=['POST'])
@login_required
def save_profile():
    """Save profile settings (display name)."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.display_name = request.form.get('display_name', '').strip() or None
        session.commit()
        flash('Profile updated!', 'success')
    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Upload a profile avatar image (stored as base64 data URI)."""
    import base64

    db = current_app.extensions['db']
    session = db.get_session()

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    try:
        file = request.files.get('avatar')
        if not file or file.filename == '':
            flash('Please select an image file.', 'error')
            return redirect(url_for('settings.settings'))

        # Check extension
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            flash('Please upload a valid image (PNG, JPG, GIF, or WebP).', 'error')
            return redirect(url_for('settings.settings'))

        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Seek back to start

        if size > MAX_SIZE:
            flash('Image must be under 2MB.', 'error')
            return redirect(url_for('settings.settings'))

        # Read file and encode as base64 data URI
        data = file.read()
        b64 = base64.b64encode(data).decode('utf-8')
        mime = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'

        user = session.query(User).get(current_user.id)
        user.avatar_url = f"data:{mime};base64,{b64}"
        session.commit()

        flash('Avatar updated!', 'success')
    except Exception as e:
        current_app.logger.exception('Avatar upload error')
        flash('Error uploading avatar. Please try again.', 'error')
    finally:
        session.close()

    return redirect(url_for('settings.settings'))


@bp.route('/settings/avatar/delete', methods=['POST'])
@login_required
def delete_avatar():
    """Remove profile avatar."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.avatar_url = None
        session.commit()
        flash('Avatar removed.', 'success')
    finally:
        session.close()
    return redirect(url_for('settings.settings'))


@bp.route('/settings/upgrade', methods=['POST'])
@login_required
def upgrade():
    """Upgrade to Pro — requires payment integration (not yet implemented)."""
    return jsonify({'error': 'Not implemented. Payment integration required.'}), 501


@bp.route('/export/applications')
@login_required
def export_applications():
    """Export all applications as CSV."""
    import csv
    from io import StringIO
    from flask import Response
    from ...models import Application, Job, Company
    
    db = current_app.extensions['db']
    session = db.get_session()
    
    try:
        # Get all applications with job and company info
        apps = session.query(Application, Job, Company).join(
            Job, Application.job_id == Job.id
        ).join(
            Company, Job.company_id == Company.id
        ).filter(
            Application.user_id == current_user.id
        ).order_by(Application.updated_at.desc()).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            'Company', 'Job Title', 'Status', 'Date Applied', 'Date Response',
            'Location', 'Salary Min', 'Salary Max', 'Job URL',
            'Excitement Level', 'Resume Version', 'Notes', 
            'Created', 'Updated'
        ])
        
        # Data rows
        for app, job, company in apps:
            writer.writerow([
                company.name,
                job.title,
                app.status.value if app.status else '',
                app.date_applied.isoformat() if app.date_applied else '',
                app.date_response.isoformat() if app.date_response else '',
                job.location or '',
                job.salary_min or '',
                job.salary_max or '',
                job.url or '',
                app.excitement_level or '',
                app.resume_version or '',
                app.lessons_learned or '',
                app.created_at.isoformat() if app.created_at else '',
                app.updated_at.isoformat() if app.updated_at else '',
            ])
        
        # Return as downloadable CSV
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=stride-applications.csv'}
        )
    finally:
        session.close()


@bp.route('/export/contacts')
@login_required
def export_contacts():
    """Export all contacts as CSV."""
    import csv
    from io import StringIO
    from flask import Response
    from ...models import Contact, Company
    
    db = current_app.extensions['db']
    session = db.get_session()
    
    try:
        contacts = session.query(Contact).outerjoin(
            Company, Contact.company_id == Company.id
        ).filter(
            Contact.user_id == current_user.id
        ).order_by(Contact.name).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Name', 'Email', 'Phone', 'Company', 'Title', 'LinkedIn',
            'Contact Type', 'Notes', 'Next Follow-up', 'Created'
        ])
        
        for contact in contacts:
            writer.writerow([
                contact.name,
                contact.email or '',
                contact.phone or '',
                contact.company.name if contact.company else '',
                contact.title or '',
                contact.linkedin_url or '',
                contact.contact_type.value if contact.contact_type else '',
                contact.notes or '',
                contact.next_followup_date.isoformat() if contact.next_followup_date else '',
                contact.created_at.isoformat() if contact.created_at else '',
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=stride-contacts.csv'}
        )
    finally:
        session.close()
