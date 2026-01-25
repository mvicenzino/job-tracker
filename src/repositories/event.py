from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from .base import BaseRepository
from ..models import Event, EventType


class EventRepository(BaseRepository[Event]):
    """Repository for Event operations."""

    def __init__(self, session: Session):
        super().__init__(session, Event)

    def get_upcoming(self, days: int = 7) -> List[Event]:
        """Get upcoming events in the next N days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        return self.session.query(Event).filter(
            Event.start_time >= now,
            Event.start_time <= cutoff,
            Event.completed == False
        ).order_by(Event.start_time).all()

    def get_today(self) -> List[Event]:
        """Get all events for today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return self.session.query(Event).filter(
            Event.start_time >= today_start,
            Event.start_time < today_end
        ).order_by(Event.start_time).all()

    def get_by_application(self, application_id: int) -> List[Event]:
        """Get all events for a specific application."""
        return self.session.query(Event).filter(
            Event.application_id == application_id
        ).order_by(Event.start_time).all()

    def get_by_contact(self, contact_id: int) -> List[Event]:
        """Get all events with a specific contact."""
        return self.session.query(Event).filter(
            Event.contact_id == contact_id
        ).order_by(Event.start_time).all()

    def get_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type."""
        return self.session.query(Event).filter(
            Event.event_type == event_type
        ).all()

    def get_interviews(self) -> List[Event]:
        """Get all interview events."""
        interview_types = [
            EventType.PHONE_SCREEN,
            EventType.VIDEO_INTERVIEW,
            EventType.ONSITE_INTERVIEW,
            EventType.TECHNICAL_INTERVIEW,
            EventType.BEHAVIORAL_INTERVIEW,
            EventType.PANEL_INTERVIEW
        ]
        return self.session.query(Event).filter(
            Event.event_type.in_(interview_types)
        ).order_by(Event.start_time).all()

    def get_past_incomplete(self) -> List[Event]:
        """Get past events that haven't been marked complete."""
        return self.session.query(Event).filter(
            Event.start_time < datetime.now(),
            Event.completed == False
        ).order_by(desc(Event.start_time)).all()

    def mark_complete(self, event_id: int, went_well: bool = None,
                     outcome_notes: str = None) -> Optional[Event]:
        """Mark an event as completed."""
        event = self.get_by_id(event_id)
        if event:
            event.completed = True
            if went_well is not None:
                event.went_well = went_well
            if outcome_notes:
                event.outcome_notes = outcome_notes
            self.session.flush()
        return event

    def get_needs_reminder(self, minutes_before: int = None) -> List[Event]:
        """Get upcoming events that need reminders."""
        now = datetime.now()
        events = self.session.query(Event).filter(
            Event.start_time > now,
            Event.completed == False
        ).all()

        result = []
        for event in events:
            reminder_mins = minutes_before or event.reminder_minutes or 30
            reminder_time = event.start_time - timedelta(minutes=reminder_mins)
            if reminder_time <= now:
                result.append(event)

        return result
