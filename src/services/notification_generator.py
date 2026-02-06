"""Service to generate automated notifications for users."""
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models import User, Event, Application, Notification, ApplicationStatus, EventType
from ..repositories.notification import NotificationRepository


class NotificationGenerator:
    """Generates automated notifications based on user data."""

    # Event types that count as interviews
    INTERVIEW_TYPES = {
        EventType.PHONE_SCREEN,
        EventType.VIDEO_INTERVIEW,
        EventType.ONSITE_INTERVIEW,
        EventType.TECHNICAL_INTERVIEW,
        EventType.BEHAVIORAL_INTERVIEW,
        EventType.PANEL_INTERVIEW,
        EventType.OFFER_CALL,
        EventType.NEGOTIATION_CALL,
    }

    def __init__(self, session: Session):
        self.session = session
        self.notif_repo = NotificationRepository(session)

    def generate_all(self) -> dict:
        """Generate all notification types for all users. Returns counts."""
        results = {
            'interview_reminders_24h': 0,
            'interview_reminders_1h': 0,
            'follow_up_nudges': 0,
            'users_processed': 0,
            'users_skipped': 0,
        }
        
        users = self.session.query(User).filter(User.is_active == True).all()
        
        for user in users:
            # Check user preferences (default to True if not set)
            wants_interview_reminders = user.notify_interview_reminders is None or user.notify_interview_reminders
            wants_follow_up_nudges = user.notify_follow_up_nudges is None or user.notify_follow_up_nudges
            
            if wants_interview_reminders:
                r24, r1 = self.generate_interview_reminders(user.id)
                results['interview_reminders_24h'] += r24
                results['interview_reminders_1h'] += r1
            
            if wants_follow_up_nudges:
                days_threshold = user.follow_up_nudge_days or 7
                followups = self.generate_follow_up_nudges(user.id, days_threshold=days_threshold)
                results['follow_up_nudges'] += followups
            
            if wants_interview_reminders or wants_follow_up_nudges:
                results['users_processed'] += 1
            else:
                results['users_skipped'] += 1
        
        return results

    def generate_interview_reminders(self, user_id: int) -> Tuple[int, int]:
        """
        Generate interview reminder notifications.
        Returns (24h_count, 1h_count).
        """
        now = datetime.utcnow()
        count_24h = 0
        count_1h = 0
        
        # Find upcoming events in the next 25 hours (to catch both windows)
        upcoming_events = self.session.query(Event).filter(
            Event.user_id == user_id,
            Event.start_time > now,
            Event.start_time < now + timedelta(hours=25),
            Event.completed == False,
            Event.event_type.in_(self.INTERVIEW_TYPES)
        ).all()
        
        for event in upcoming_events:
            time_until = event.start_time - now
            hours_until = time_until.total_seconds() / 3600
            
            # 24-hour reminder (between 23-25 hours out)
            if 23 <= hours_until <= 25:
                if self._create_reminder_if_not_exists(
                    user_id, event, '24h',
                    f"📅 Interview tomorrow: {event.title}",
                    self._format_interview_message(event, "tomorrow")
                ):
                    count_24h += 1
            
            # 1-hour reminder (between 0.5-1.5 hours out)
            elif 0.5 <= hours_until <= 1.5:
                if self._create_reminder_if_not_exists(
                    user_id, event, '1h',
                    f"⏰ Interview in 1 hour: {event.title}",
                    self._format_interview_message(event, "in 1 hour")
                ):
                    count_1h += 1
        
        return count_24h, count_1h

    def generate_follow_up_nudges(self, user_id: int, days_threshold: int = 7) -> int:
        """
        Generate follow-up nudge notifications for stale applications.
        Returns count of notifications created.
        """
        count = 0
        today = datetime.utcnow().date()
        threshold_date = today - timedelta(days=days_threshold)
        
        # Find applications that:
        # - Status is 'applied' (submitted but no response yet)
        # - Applied more than X days ago
        # - No response date set
        stale_applications = self.session.query(Application).filter(
            Application.user_id == user_id,
            Application.status == ApplicationStatus.APPLIED,
            Application.date_applied != None,
            Application.date_applied <= threshold_date,
            Application.date_response == None
        ).all()
        
        for app in stale_applications:
            days_ago = (today - app.date_applied).days
            
            # Only nudge at specific intervals: 7, 14, 21 days
            if days_ago in [7, 14, 21]:
                if self._create_followup_if_not_exists(user_id, app, days_ago):
                    count += 1
        
        return count

    def _create_reminder_if_not_exists(
        self, 
        user_id: int, 
        event: Event, 
        reminder_type: str,
        title: str,
        message: str
    ) -> bool:
        """Create interview reminder if one doesn't exist for this event/type combo."""
        # Check if we already sent this reminder
        notification_type = f"interview_reminder_{reminder_type}"
        
        existing = self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.application_id == event.application_id,
            # Check created in last 24 hours to avoid re-sending
            Notification.created_at > datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if existing:
            return False
        
        # Build link URL
        link_url = f"/applications/{event.application_id}" if event.application_id else "/schedule"
        
        self.notif_repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            application_id=event.application_id
        )
        return True

    def _create_followup_if_not_exists(
        self,
        user_id: int,
        application: Application,
        days_ago: int
    ) -> bool:
        """Create follow-up nudge if one doesn't exist for this application/day combo."""
        notification_type = f"follow_up_nudge_{days_ago}d"
        
        # Check if we already sent this specific nudge
        existing = self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.application_id == application.id
        ).first()
        
        if existing:
            return False
        
        company_name = application.job.company.name if application.job and application.job.company else "this company"
        job_title = application.job.title if application.job else "this position"
        
        title = f"🔄 Follow up with {company_name}?"
        message = (
            f"You applied for {job_title} at {company_name} {days_ago} days ago. "
            f"Consider sending a follow-up email to check on your application status."
        )
        
        self.notif_repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link_url=f"/applications/{application.id}",
            application_id=application.id
        )
        return True

    def _format_interview_message(self, event: Event, when: str) -> str:
        """Format a helpful interview reminder message."""
        parts = [f"Your {event.event_type.value.replace('_', ' ')} is {when}."]
        
        if event.location:
            parts.append(f"📍 Location: {event.location}")
        if event.meeting_link:
            parts.append(f"🔗 Meeting link: {event.meeting_link}")
        if event.prep_notes:
            parts.append(f"📝 Your prep notes: {event.prep_notes[:100]}...")
        
        # Add company name if available
        if event.application and event.application.job and event.application.job.company:
            parts.insert(1, f"🏢 Company: {event.application.job.company.name}")
        
        return "\n".join(parts)
