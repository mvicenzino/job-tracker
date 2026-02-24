"""Notes routes — aggregated My Notes page + CRUD for entity notes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ..helpers import get_service

bp = Blueprint('notes', __name__)


@bp.route('/my-notes')
@login_required
def my_notes():
    """Aggregated notes page for the current user."""
    service, session = get_service()
    try:
        notes = service.get_all_user_notes(limit=100)
        return render_template('my_notes.html', notes=notes)
    finally:
        session.close()


@bp.route('/my-notes', methods=['POST'])
@login_required
def create_standalone_note():
    """Create a standalone note (no parent entity)."""
    service, session = get_service()
    try:
        service.add_note(
            content=request.form['content'],
            title=request.form.get('title'),
            note_type=request.form.get('note_type', 'general')
        )
        flash('Note added!', 'success')
    finally:
        session.close()
    return redirect(url_for('notes.my_notes'))


@bp.route('/notes/<int:note_id>/edit', methods=['POST'])
@login_required
def edit_note(note_id):
    """Edit an existing note."""
    service, session = get_service()
    try:
        note = service.update_note(
            note_id,
            content=request.form.get('content'),
            title=request.form.get('title'),
            note_type=request.form.get('note_type')
        )
        if note:
            flash('Note updated!', 'success')
        else:
            flash('Note not found.', 'error')
    finally:
        session.close()
    return redirect(request.form.get('redirect_url') or request.referrer or url_for('notes.my_notes'))


@bp.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    """Delete a note."""
    service, session = get_service()
    try:
        if service.delete_note(note_id):
            flash('Note deleted.', 'success')
        else:
            flash('Note not found.', 'error')
    finally:
        session.close()
    return redirect(request.form.get('redirect_url') or request.referrer or url_for('notes.my_notes'))


@bp.route('/contacts/<int:contact_id>/notes', methods=['POST'])
@login_required
def add_contact_note(contact_id):
    """Add a note to a contact."""
    service, session = get_service()
    try:
        service.add_note(
            content=request.form['content'],
            title=request.form.get('title'),
            contact_id=contact_id,
            note_type=request.form.get('note_type', 'general')
        )
        flash('Note added!', 'success')
    finally:
        session.close()
    return redirect(url_for('contacts.edit_contact', contact_id=contact_id))


@bp.route('/companies/<int:company_id>/notes', methods=['POST'])
@login_required
def add_company_note(company_id):
    """Add a note to a company."""
    service, session = get_service()
    try:
        service.add_note(
            content=request.form['content'],
            title=request.form.get('title'),
            company_id=company_id,
            note_type=request.form.get('note_type', 'general')
        )
        flash('Note added!', 'success')
    finally:
        session.close()
    return redirect(url_for('companies.edit_company', company_id=company_id))


@bp.route('/jobs/<int:job_id>/notes', methods=['POST'])
@login_required
def add_job_note(job_id):
    """Add a note to a job."""
    service, session = get_service()
    try:
        service.add_note(
            content=request.form['content'],
            title=request.form.get('title'),
            job_id=job_id,
            note_type=request.form.get('note_type', 'general')
        )
        flash('Note added!', 'success')
    finally:
        session.close()
    return redirect(url_for('jobs.edit_job', job_id=job_id))
