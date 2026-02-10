"""Interview prep model for storing AI-generated interview preparation materials."""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class InterviewPrep(Base, TimestampMixin):
    """Stores AI-generated interview preparation materials for an application."""
    __tablename__ = 'interview_preps'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    resume_version_id = Column(Integer, ForeignKey('resume_versions.id'), nullable=True)

    # AI-generated content stored as JSONB
    questions = Column(JSONB)  # List of interview questions with tips
    talking_points = Column(JSONB)  # List of key talking points
    questions_to_ask = Column(JSONB)  # List of questions to ask interviewer
    company_brief = Column(JSONB)  # Company summary info

    # Relationships
    user = relationship("User", backref="interview_preps")
    application = relationship("Application", backref="interview_preps")
    resume_version = relationship("ResumeVersion", backref="interview_preps")

    def __repr__(self):
        return f"<InterviewPrep(id={self.id}, application_id={self.application_id})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'application_id': self.application_id,
            'resume_version_id': self.resume_version_id,
            'questions': self.questions or [],
            'talking_points': self.talking_points or [],
            'questions_to_ask': self.questions_to_ask or [],
            'company_brief': self.company_brief or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
