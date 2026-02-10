"""Schedule routes: list, new event, new interview, complete, .ics export."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
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


@bp.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    """View event detail."""
    service, session = get_service()
    try:
        event = service.events.get_by_id(event_id)
        if not event:
            flash('Event not found.', 'error')
            return redirect(url_for('schedule.schedule'))
        return render_template('event_detail.html', event=event)
    finally:
        session.close()


@bp.route('/events/<int:event_id>/update', methods=['POST'])
@login_required
def update_event(event_id):
    """Update event details including outcome notes."""
    service, session = get_service()
    try:
        event = service.events.get_by_id(event_id)
        if not event:
            flash('Event not found.', 'error')
            return redirect(url_for('schedule.schedule'))

        # Update outcome notes
        outcome_notes = request.form.get('outcome_notes')
        if outcome_notes is not None:
            event.outcome_notes = outcome_notes

        # Update completion status if provided
        completed = request.form.get('completed')
        if completed is not None:
            event.completed = completed == 'true'

        went_well = request.form.get('went_well')
        if went_well:
            event.went_well = went_well == 'true'

        session.commit()
        flash('Event updated!', 'success')
        return redirect(url_for('schedule.event_detail', event_id=event_id))
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


def _ics_escape(text):
    """Escape text for iCalendar format (RFC 5545)."""
    if not text:
        return ''
    return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


@bp.route('/events/<int:event_id>/export.ics')
@login_required
def export_ics(event_id):
    """Export an event as an .ics (iCalendar) file."""
    service, session = get_service()
    try:
        event = service.events.get_by_id(event_id)
        if not event:
            flash('Event not found.', 'error')
            return redirect(url_for('schedule.schedule'))

        dtstart = event.start_time.strftime('%Y%m%dT%H%M%S')
        if event.end_time:
            dtend = event.end_time.strftime('%Y%m%dT%H%M%S')
        else:
            dtend = (event.start_time + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')

        dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        description_parts = []
        if event.description:
            description_parts.append(event.description)
        if event.prep_notes:
            description_parts.append(f"Prep: {event.prep_notes}")
        if event.questions_to_ask:
            description_parts.append(f"Questions: {event.questions_to_ask}")
        description = '\\n'.join(description_parts)

        location = event.location or event.meeting_link or ''

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Stride//Job Hunt Tracker//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            'BEGIN:VEVENT',
            f'UID:{event.id}@stride-jobs.vercel.app',
            f'DTSTAMP:{dtstamp}',
            f'DTSTART:{dtstart}',
            f'DTEND:{dtend}',
            f'SUMMARY:{_ics_escape(event.title)}',
        ]
        if description:
            lines.append(f'DESCRIPTION:{_ics_escape(description)}')
        if location:
            lines.append(f'LOCATION:{_ics_escape(location)}')
        if event.meeting_link:
            lines.append(f'URL:{event.meeting_link}')
        lines += [
            'END:VEVENT',
            'END:VCALENDAR',
        ]

        ics_content = '\r\n'.join(lines) + '\r\n'
        safe_title = event.title.replace(' ', '_').replace('/', '-')[:50]

        return Response(
            ics_content,
            mimetype='text/calendar',
            headers={
                'Content-Disposition': f'attachment; filename="{safe_title}.ics"'
            }
        )
    finally:
        session.close()
