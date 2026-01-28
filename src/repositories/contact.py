from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .base import BaseRepository
from ..models import Contact, ContactType


class ContactRepository(BaseRepository[Contact]):
    """Repository for Contact operations."""

    def __init__(self, session: Session, user_id: int = None):
        super().__init__(session, Contact)
        self.user_id = user_id

    def _base_query(self):
        """Get base query filtered by user_id if set."""
        query = self.session.query(Contact)
        if self.user_id is not None:
            query = query.filter(Contact.user_id == self.user_id)
        return query

    def get_by_id(self, id: int) -> Optional[Contact]:
        """Get a single record by ID, filtered by user."""
        return self._base_query().filter(Contact.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Contact]:
        """Get all records with pagination, filtered by user, sorted by name."""
        return self._base_query().order_by(Contact.name).offset(offset).limit(limit).all()

    def create(self, **kwargs) -> Contact:
        """Create a new record with user_id auto-set."""
        if self.user_id is not None:
            kwargs['user_id'] = self.user_id
        return super().create(**kwargs)

    def search_by_name(self, name: str) -> List[Contact]:
        """Search contacts by name (case-insensitive partial match)."""
        return self._base_query().filter(
            Contact.name.ilike(f"%{name}%")
        ).all()

    def get_by_company(self, company_id: int) -> List[Contact]:
        """Get all contacts at a specific company."""
        return self._base_query().filter(
            Contact.company_id == company_id
        ).all()

    def get_by_type(self, contact_type: ContactType) -> List[Contact]:
        """Get all contacts of a specific type."""
        return self._base_query().filter(
            Contact.contact_type == contact_type
        ).all()

    def get_needing_followup(self) -> List[Contact]:
        """Get contacts that need follow-up (followup date is today or past)."""
        return self._base_query().filter(
            Contact.next_followup_date <= date.today()
        ).order_by(Contact.next_followup_date).all()

    def get_recently_contacted(self, days: int = 7) -> List[Contact]:
        """Get contacts you've recently been in touch with."""
        cutoff = date.today() - timedelta(days=days)
        return self._base_query().filter(
            Contact.last_contact_date >= cutoff
        ).order_by(desc(Contact.last_contact_date)).all()

    def get_stale_contacts(self, days: int = 30) -> List[Contact]:
        """Get contacts you haven't been in touch with recently."""
        cutoff = date.today() - timedelta(days=days)
        return self._base_query().filter(
            Contact.last_contact_date < cutoff
        ).order_by(Contact.last_contact_date).all()

    def get_strong_relationships(self, min_strength: int = 4) -> List[Contact]:
        """Get contacts with strong relationships."""
        return self._base_query().filter(
            Contact.relationship_strength >= min_strength
        ).all()

    def update_last_contact(self, contact_id: int,
                           next_followup_days: int = None) -> Optional[Contact]:
        """Update last contact date and optionally set next follow-up."""
        contact = self.get_by_id(contact_id)
        if contact:
            contact.last_contact_date = date.today()
            if next_followup_days:
                contact.next_followup_date = date.today() + timedelta(days=next_followup_days)
            self.session.flush()
        return contact

    def get_recruiters(self) -> List[Contact]:
        """Get all recruiter contacts."""
        return self._base_query().filter(
            Contact.contact_type.in_([ContactType.RECRUITER, ContactType.INTERNAL_RECRUITER])
        ).all()

    def count(self) -> int:
        """Get total count of records for user."""
        return self._base_query().count()
