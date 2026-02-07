import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin, UserMixin):
    """Represents a user account for authentication."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    resume_text = Column(Text, nullable=True)
    resume_filename = Column(String(255), nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=True)
    onboarding_dismissed = Column(Boolean, default=False, nullable=True)

    # Notification preferences
    email_digest_enabled = Column(Boolean, default=False, nullable=True)
    email_digest_frequency = Column(String(20), default='weekly', nullable=True)
    browser_notifications_enabled = Column(Boolean, default=True, nullable=True)
    
    # In-app notification preferences
    notify_interview_reminders = Column(Boolean, default=True, nullable=True)
    notify_follow_up_nudges = Column(Boolean, default=True, nullable=True)
    follow_up_nudge_days = Column(Integer, default=7, nullable=True)  # Days after applying to nudge
    
    # Profile
    avatar_url = Column(String(500), nullable=True)  # URL to user's profile photo
    display_name = Column(String(100), nullable=True)  # Optional display name

    # Relationships
    companies = relationship("Company", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self) -> str:
        """Generate a new API key for the user."""
        self.api_key = secrets.token_hex(32)
        return self.api_key

    @property
    def first_name(self) -> str:
        """Extract first name from email for personalized greetings."""
        if not self.email:
            return ''
        # Get the part before @ and split by common separators
        local_part = self.email.split('@')[0]
        # Split by dots, underscores, or hyphens and take the first part
        for sep in ['.', '_', '-']:
            if sep in local_part:
                local_part = local_part.split(sep)[0]
                break
        # Capitalize and return
        return local_part.capitalize()

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
