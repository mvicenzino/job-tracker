from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """Represents a company you're interested in or applying to."""
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    website = Column(String(500))
    industry = Column(String(100))
    size = Column(String(50))  # e.g., "1-10", "11-50", "51-200", "201-500", "500+"
    location = Column(String(255))
    description = Column(Text)
    culture_notes = Column(Text)  # Your notes about company culture
    glassdoor_rating = Column(String(10))
    linkedin_url = Column(String(500))
    is_flagged = Column(Boolean, default=False)

    # Workspace support (nullable — NULL means personal data)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    user = relationship("User", back_populates="companies", foreign_keys=[user_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="company", cascade="all, delete-orphan",
                        foreign_keys="Note.company_id")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"
