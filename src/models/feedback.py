from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    """User feedback stored in the database."""
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category = Column(String(50))  # e.g., "bug", "feature", "general", "praise"
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    def __repr__(self):
        return f"<Feedback(id={self.id}, subject='{self.subject}')>"
