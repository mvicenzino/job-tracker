"""Resume version management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service

bp = Blueprint('resumes', __name__)


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
            name = request.form.get('name', '').strip()
            content = request.form.get('content', '').strip()

            if not name:
                flash('Please provide a name for this resume version.', 'error')
                return render_template('resume_form.html')

            # Check if name already exists
            existing = service.resume_versions.get_by_name(name)
            if existing:
                flash(f'A resume version named "{name}" already exists.', 'error')
                return render_template('resume_form.html', name=name, content=content)

            version = service.resume_versions.create(name=name, content=content)
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

            if not name:
                flash('Please provide a name for this resume version.', 'error')
                return render_template('resume_form.html', version=version)

            # Check if name already exists (excluding current)
            existing = service.resume_versions.get_by_name(name)
            if existing and existing.id != version_id:
                flash(f'A resume version named "{name}" already exists.', 'error')
                return render_template('resume_form.html', version=version)

            service.resume_versions.update(version_id, name=name, content=content)
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
