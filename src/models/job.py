from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """Represents a specific job posting/position."""
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    requirements = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(10), default='USD')
    location = Column(String(255))
    remote_type = Column(String(50))  # "remote", "hybrid", "onsite"
    job_url = Column(String(500))
    source = Column(String(100))  # Where you found it: LinkedIn, Indeed, referral, etc.
    is_active = Column(Boolean, default=True)  # Is the posting still open?

    # Relationships
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="job", cascade="all, delete-orphan",
                        foreign_keys="Note.job_id")

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}')>"
