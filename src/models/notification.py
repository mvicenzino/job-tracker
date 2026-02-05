from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """Represents a notification/alert for the user."""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Notification type: 'job_added', 'application_update', 'reminder', etc.
    notification_type = Column(String(50), nullable=False)
    
    # Title and message
    title = Column(String(255), nullable=False)
    message = Column(Text)
    
    # Link to related entity (optional)
    link_url = Column(String(500))
    
    # Related entity IDs (optional, for filtering/grouping)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True)
    
    # Read status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="notifications")
    job = relationship("Job", backref="notifications")
    application = relationship("Application", backref="notifications")

    def mark_as_read(self):
        """Mark this notification as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', read={self.is_read})>"
