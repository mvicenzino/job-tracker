from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class NoteMention(Base, TimestampMixin):
    """Tracks @contact mentions within notes (many-to-many)."""
    __tablename__ = 'note_mentions'
    __table_args__ = (
        UniqueConstraint('note_id', 'contact_id', name='uq_note_mention'),
    )

    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey('notes.id', ondelete='CASCADE'), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False, index=True)

    note = relationship("Note", back_populates="mentioned_contacts")
    contact = relationship("Contact", back_populates="mentioned_in_notes")

    def __repr__(self):
        return f"<NoteMention(note_id={self.note_id}, contact_id={self.contact_id})>"


class Note(Base, TimestampMixin):
    """General-purpose notes that can be attached to various entities."""
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    # Polymorphic foreign keys - only one should be set
    company_id = Column(Integer, ForeignKey('companies.id'), index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), index=True)
    event_id = Column(Integer, ForeignKey('events.id'), index=True)

    # Note content
    title = Column(String(255))
    content = Column(Text, nullable=False)
    note_type = Column(String(50))  # e.g., "research", "preparation", "followup", "general"

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", back_populates="notes", foreign_keys=[company_id])
    job = relationship("Job", back_populates="notes", foreign_keys=[job_id])
    application = relationship("Application", back_populates="notes", foreign_keys=[application_id])
    contact = relationship("Contact", back_populates="contact_notes", foreign_keys=[contact_id])
    event = relationship("Event", back_populates="notes", foreign_keys=[event_id])
    mentioned_contacts = relationship("NoteMention", back_populates="note", cascade="all, delete-orphan")

    @property
    def parent_type(self):
        if self.application_id:
            return "application"
        if self.job_id:
            return "job"
        if self.contact_id:
            return "contact"
        if self.company_id:
            return "company"
        if self.event_id:
            return "event"
        return "general"

    @property
    def parent_label(self):
        if self.application_id and self.application:
            app = self.application
            job_title = app.job.title if app.job else "Unknown Role"
            company = app.job.company.name if app.job and app.job.company else (app.company_name or "Unknown")
            return f"{job_title} @ {company}"
        if self.job_id and self.job:
            company = self.job.company.name if self.job.company else ""
            return f"{self.job.title} @ {company}" if company else self.job.title
        if self.contact_id and self.contact:
            return self.contact.name
        if self.company_id and self.company:
            return self.company.name
        if self.event_id and self.event:
            return self.event.title
        return "General"

    @property
    def parent_url(self):
        try:
            from flask import url_for
            if self.application_id:
                return url_for('applications.application_detail', app_id=self.application_id)
            if self.job_id:
                return url_for('jobs.edit_job', job_id=self.job_id)
            if self.contact_id:
                return url_for('contacts.edit_contact', contact_id=self.contact_id)
            if self.company_id:
                return url_for('companies.edit_company', company_id=self.company_id)
            if self.event_id:
                return url_for('schedule.events')
        except RuntimeError:
            pass
        return None

    @property
    def parent_icon(self):
        icons = {
            "application": "📋",
            "job": "💼",
            "contact": "👤",
            "company": "🏢",
            "event": "📅",
            "general": "📝",
        }
        return icons.get(self.parent_type, "📝")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"
