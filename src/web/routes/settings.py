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
