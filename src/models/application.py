import enum
from datetime import date
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ApplicationStatus(enum.Enum):
    """Status stages for a job application."""
    INTERESTED = "interested"           # Saved for later
    PREPARING = "preparing"             # Working on application materials
    APPLIED = "applied"                 # Application submitted
    SCREENING = "screening"             # Recruiter/phone screen scheduled or completed
    INTERVIEWING = "interviewing"       # In interview process
    FINAL_ROUND = "final_round"         # Final interviews
    OFFER = "offer"                     # Received offer
    NEGOTIATING = "negotiating"         # Negotiating terms
    ACCEPTED = "accepted"               # Accepted offer
    REJECTED = "rejected"               # Rejected by company
    WITHDRAWN = "withdrawn"             # You withdrew
    GHOSTED = "ghosted"                 # No response after reasonable time
    ARCHIVED = "archived"               # Hidden from view, can be restored


class Application(Base, TimestampMixin):
    """Tracks your application to a specific job."""
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.INTERESTED, nullable=False, index=True)

    # Key dates
    date_applied = Column(Date)
    date_response = Column(Date)  # When you first heard back
    date_closed = Column(Date)    # When application process ended

    # Application details
    resume_version = Column(String(100))  # Which resume version you used
    cover_letter = Column(Text)
    referral_contact_id = Column(Integer, ForeignKey('contacts.id'))

    # Compensation (if discussed/offered)
    offered_salary = Column(Integer)
    offered_bonus = Column(Integer)
    offered_equity = Column(String(100))

    # Notes
    rejection_reason = Column(Text)
    lessons_learned = Column(Text)
    excitement_level = Column(Integer)  # 1-5 scale of how excited you are

    # Relationships
    user = relationship("User", backref="applications")
    job = relationship("Job", back_populates="applications")
    referral_contact = relationship("Contact", foreign_keys=[referral_contact_id])
    events = relationship("Event", back_populates="application", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="application", cascade="all, delete-orphan",
                        foreign_keys="Note.application_id")

    def __repr__(self):
        return f"<Application(id={self.id}, status='{self.status.value}')>"
