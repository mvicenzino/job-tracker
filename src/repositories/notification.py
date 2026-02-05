from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Notification


class NotificationRepository:
    """Repository for managing notifications."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str = None,
        link_url: str = None,
        job_id: int = None,
        application_id: int = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            job_id=job_id,
            application_id=application_id
        )
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """Get a notification by ID."""
        return self.session.query(Notification).filter(
            Notification.id == notification_id
        ).first()

    def get_for_user(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user, ordered by newest first."""
        query = self.session.query(Notification).filter(
            Notification.user_id == user_id
        )
        if unread_only:
            query = query.filter(Notification.is_read == False)
        return query.order_by(desc(Notification.created_at)).limit(limit).all()

    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        return self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        notification = self.session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.session.commit()
            return True
        return False

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        count = self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        })
        self.session.commit()
        return count

    def delete(self, notification_id: int, user_id: int) -> bool:
        """Delete a notification."""
        notification = self.session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notification:
            self.session.delete(notification)
            self.session.commit()
            return True
        return False

    def delete_all_read(self, user_id: int) -> int:
        """Delete all read notifications for a user. Returns count deleted."""
        count = self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == True
        ).delete()
        self.session.commit()
        return count
