"""Resume version management routes."""
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from ..helpers import get_service
from ...services.usage_tracker import UsageTracker

bp = Blueprint('resumes', __name__)


def extract_text_from_pdf(file_stream):
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_stream)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return '\n\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Could not read PDF: {str(e)}")


def extract_text_from_docx(file_stream):
    """Extract text from a Word document."""
    try:
        from docx import Document
        doc = Document(file_stream)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return '\n\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Could not read Word document: {str(e)}")


@bp.route('/resumes')
@login_required
def resumes():
    """List all resume versions."""
    service, session = get_service()
    try:
        versions = service.resume_versions.get_all()
        # Get usage counts for each version
        usage_counts = {}
        for v in versions:
            usage_counts[v.id] = service.resume_versions.get_usage_count(v.id)
        return render_template('resumes.html',
                             versions=versions,
                             usage_counts=usage_counts)
    finally:
        session.close()


@bp.route('/resumes/new', methods=['GET', 'POST'])
@login_required
def new_resume():
    """Add a new resume version."""
    if request.method == 'POST':
        service, session = get_service()
        try:
            # Check resume version limits for free users
            from ...models import User
            user = session.query(User).get(current_user.id)
            existing_count = len(service.resume_versions.get_all())
            tracker = UsageTracker(user, session)
            allowed, limit_info = tracker.can_add_resume_version(existing_count)
            if not allowed:
                session.commit()
                flash(limit_info['message'], 'warning')
                return redirect(url_for('resumes.resumes'))

            name = request.form.get('name', '').strip()
            content = request.form.get('content', '').strip()
            filename = None

            # Handle file upload
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                filename = uploaded_file.filename
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''

                try:
                    file_stream = io.BytesIO(uploaded_file.read())
                    if file_ext == 'pdf':
                        extracted = extract_text_from_pdf(file_stream)
                    elif file_ext in ('docx', 'doc'):
                        extracted = extract_text_from_docx(file_stream)
                    else:
                        flash('Unsupported file type. Please upload a PDF or Word document.', 'error')
                        return render_template('resume_form.html', name=name, content=content)

                    # Use extracted text if no content was pasted
                    if not content and extracted:
                        content = extracted
                    elif extracted:
                        # File was uploaded but content also provided - use content
                        pass
                except ValueError as e:
                    flash(str(e), 'error')
                    return render_template('resume_form.html', name=name, content=content)

            if not name:
                flash('Please provide a name for this resume version.', 'error')
                return render_template('resume_form.html', content=content)

            if not content:
                flash('Please upload a file or paste your resume content.', 'error')
                return render_template('resume_form.html', name=name)

            # Check if name already exists
            existing = service.resume_versions.get_by_name(name)
            if existing:
                flash(f'A resume version named "{name}" already exists.', 'error')
                return render_template('resume_form.html', name=name, content=content)

            version = service.resume_versions.create(name=name, content=content, filename=filename)
            session.commit()
            flash(f'Resume version "{name}" created!', 'success')
            return redirect(url_for('resumes.resumes'))
        finally:
            session.close()

    return render_template('resume_form.html')


@bp.route('/resumes/<int:version_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_resume(version_id):
    """Edit a resume version."""
    service, session = get_service()
    try:
        version = service.resume_versions.get_by_id(version_id)
        if not version:
            flash('Resume version not found.', 'error')
            return redirect(url_for('resumes.resumes'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            content = request.form.get('content', '').strip()
            filename = version.filename  # Keep existing filename by default

            # Handle file upload
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                filename = uploaded_file.filename
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''

                try:
                    file_stream = io.BytesIO(uploaded_file.read())
                    if file_ext == 'pdf':
                        extracted = extract_text_from_pdf(file_stream)
                    elif file_ext in ('docx', 'doc'):
                        extracted = extract_text_from_docx(file_stream)
                    else:
                        flash('Unsupported file type. Please upload a PDF or Word document.', 'error')
                        return render_template('resume_form.html', version=version)

                    # Replace content with extracted text
                    if extracted:
                        content = extracted
                except ValueError as e:
                    flash(str(e), 'error')
                    return render_template('resume_form.html', version=version)

            if not name:
                flash('Please provide a name for this resume version.', 'error')
                return render_template('resume_form.html', version=version)

            # Check if name already exists (excluding current)
            existing = service.resume_versions.get_by_name(name)
            if existing and existing.id != version_id:
                flash(f'A resume version named "{name}" already exists.', 'error')
                return render_template('resume_form.html', version=version)

            service.resume_versions.update(version_id, name=name, content=content, filename=filename)
            session.commit()
            flash(f'Resume version "{name}" updated!', 'success')
            return redirect(url_for('resumes.resumes'))

        return render_template('resume_form.html', version=version)
    finally:
        session.close()


@bp.route('/resumes/<int:version_id>/delete', methods=['POST'])
@login_required
def delete_resume(version_id):
    """Delete a resume version."""
    service, session = get_service()
    try:
        version = service.resume_versions.get_by_id(version_id)
        if not version:
            flash('Resume version not found.', 'error')
            return redirect(url_for('resumes.resumes'))

        # Check if it's being used
        usage_count = service.resume_versions.get_usage_count(version_id)
        if usage_count > 0:
            flash(f'Cannot delete "{version.name}" - it\'s used by {usage_count} application(s).', 'error')
            return redirect(url_for('resumes.resumes'))

        name = version.name
        service.resume_versions.delete(version_id)
        session.commit()
        flash(f'Resume version "{name}" deleted.', 'success')
    finally:
        session.close()
    return redirect(url_for('resumes.resumes'))
