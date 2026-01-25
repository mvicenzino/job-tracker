from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Note(Base, TimestampMixin):
    """General-purpose notes that can be attached to various entities."""
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)

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
    company = relationship("Company", back_populates="notes", foreign_keys=[company_id])
    job = relationship("Job", back_populates="notes", foreign_keys=[job_id])
    application = relationship("Application", back_populates="notes", foreign_keys=[application_id])
    contact = relationship("Contact", back_populates="contact_notes", foreign_keys=[contact_id])
    event = relationship("Event", back_populates="notes", foreign_keys=[event_id])

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"
