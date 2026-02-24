import enum
from datetime import date
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ContactType(enum.Enum):
    """Types of contacts in your network."""
    RECRUITER = "recruiter"             # External recruiter
    INTERNAL_RECRUITER = "internal_recruiter"  # Company recruiter
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    EMPLOYEE = "employee"               # Current employee at company
    FORMER_EMPLOYEE = "former_employee"
    REFERRAL = "referral"               # Someone who referred you
    NETWORKING = "networking"           # General networking contact
    MENTOR = "mentor"
    OTHER = "other"


class Contact(Base, TimestampMixin):
    """Represents a person in your job hunt network."""
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), index=True)  # Optional

    # Basic info
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    linkedin_url = Column(String(500))

    # Role info
    title = Column(String(255))
    contact_type = Column(Enum(ContactType), default=ContactType.NETWORKING)

    # Relationship tracking
    how_we_met = Column(Text)
    relationship_strength = Column(Integer)  # 1-5 scale
    last_contact_date = Column(Date)
    next_followup_date = Column(Date)

    # Notes
    notes = Column(Text)

    # Workspace support (nullable — NULL means personal data)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship("User", back_populates="contacts", foreign_keys=[user_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    company = relationship("Company", back_populates="contacts")
    events = relationship("Event", back_populates="contact", cascade="all, delete-orphan",
                         foreign_keys="Event.contact_id")
    contact_notes = relationship("Note", back_populates="contact", cascade="all, delete-orphan",
                                foreign_keys="Note.contact_id")
    mentioned_in_notes = relationship("NoteMention", back_populates="contact", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.name}')>"
