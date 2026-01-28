import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class EventType(enum.Enum):
    """Types of events/activities in job hunt."""
    PHONE_SCREEN = "phone_screen"
    VIDEO_INTERVIEW = "video_interview"
    ONSITE_INTERVIEW = "onsite_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    BEHAVIORAL_INTERVIEW = "behavioral_interview"
    PANEL_INTERVIEW = "panel_interview"
    COFFEE_CHAT = "coffee_chat"
    NETWORKING_EVENT = "networking_event"
    CAREER_FAIR = "career_fair"
    FOLLOW_UP = "follow_up"
    OFFER_CALL = "offer_call"
    NEGOTIATION_CALL = "negotiation_call"
    APPLICATION_DEADLINE = "application_deadline"
    TASK_DEADLINE = "task_deadline"  # Take-home assignment, etc.
    REMINDER = "reminder"
    OTHER = "other"


class Event(Base, TimestampMixin):
    """Represents a scheduled event or activity."""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), index=True)

    # Event details
    title = Column(String(255), nullable=False)
    event_type = Column(Enum(EventType), default=EventType.OTHER)
    description = Column(Text)

    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    is_all_day = Column(Boolean, default=False)

    # Location/logistics
    location = Column(String(500))  # Physical address or video link
    meeting_link = Column(String(500))

    # Preparation
    prep_notes = Column(Text)  # What to prepare
    questions_to_ask = Column(Text)  # Questions you want to ask

    # Outcome (fill after event)
    completed = Column(Boolean, default=False)
    outcome_notes = Column(Text)
    went_well = Column(Boolean)  # Quick thumbs up/down

    # Reminders
    reminder_minutes = Column(Integer, default=30)  # Minutes before to remind

    # Relationships
    user = relationship("User", backref="events")
    application = relationship("Application", back_populates="events")
    contact = relationship("Contact", back_populates="events", foreign_keys=[contact_id])
    notes = relationship("Note", back_populates="event", cascade="all, delete-orphan",
                        foreign_keys="Note.event_id")

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', start='{self.start_time}')>"
