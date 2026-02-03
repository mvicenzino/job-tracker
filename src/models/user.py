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
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_dismissed = Column(Boolean, default=False, nullable=False)

    # Notification preferences
    email_digest_enabled = Column(Boolean, default=False, nullable=False)
    email_digest_frequency = Column(String(20), default='weekly')  # 'daily' or 'weekly'
    browser_notifications_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    companies = relationship("Company", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")

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

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
