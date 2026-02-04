from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ResumeVersion(Base, TimestampMixin):
    """Stores different versions of a user's resume."""
    __tablename__ = 'resume_versions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # Version identification
    name = Column(String(100), nullable=False)  # e.g., "General", "Technical", "Leadership"

    # Content
    content = Column(Text)  # The actual resume text
    filename = Column(String(255))  # Original filename if uploaded

    # Relationships
    user = relationship("User", back_populates="resume_versions")
    applications = relationship("Application", back_populates="resume_version_ref",
                               foreign_keys="Application.resume_version_id")

    def __repr__(self):
        return f"<ResumeVersion(id={self.id}, name='{self.name}')>"
