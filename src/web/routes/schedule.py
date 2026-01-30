"""Schedule routes: list, new event, new interview, complete."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service
from ...models import EventType

bp = Blueprint('schedule', __name__)


@bp.route('/schedule')
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


@bp.route('/events/new', methods=['GET', 'POST'])
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
            return redirect(url_for('schedule.schedule'))

        applications = service.applications.get_active_applications()
        contacts = service.contacts.get_all()
        return render_template('event_form.html',
                             applications=applications,
                             contacts=contacts,
                             EventType=EventType)
    finally:
        session.close()


@bp.route('/events/<int:event_id>/complete', methods=['POST'])
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
    return redirect(request.referrer or url_for('schedule.schedule'))


@bp.route('/interview/new', methods=['GET', 'POST'])
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
            return redirect(url_for('schedule.schedule'))

        applications = service.applications.get_active_applications()
        return render_template('interview_form.html',
                             applications=applications,
                             EventType=EventType)
    finally:
        session.close()
