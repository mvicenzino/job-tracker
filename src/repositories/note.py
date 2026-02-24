from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from .base import BaseRepository
from ..models import Note


class NoteRepository(BaseRepository[Note]):
    """Repository for Note operations."""

    def __init__(self, session: Session, user_id: int = None, workspace_id: int = None):
        super().__init__(session, Note)
        self.user_id = user_id
        self.workspace_id = workspace_id

    def _base_query(self):
        """Get base query filtered by workspace or user."""
        query = self.session.query(Note)
        if self.workspace_id is not None:
            query = query.filter(Note.workspace_id == self.workspace_id)
        elif self.user_id is not None:
            query = query.filter(Note.user_id == self.user_id, Note.workspace_id.is_(None))
        return query

    def create(self, **kwargs) -> Note:
        """Create a new note with user_id and workspace auto-set."""
        if self.user_id is not None:
            kwargs.setdefault('user_id', self.user_id)
        if self.workspace_id is not None:
            kwargs['workspace_id'] = self.workspace_id
            kwargs.setdefault('created_by', self.user_id)
        return super().create(**kwargs)

    def get_all_for_user(self, user_id: int, limit: int = 50) -> List[Note]:
        """Get all notes for a user, eager-loading parents."""
        query = self._base_query() if (self.workspace_id or self.user_id) else self.session.query(Note).filter(Note.user_id == user_id)
        return query.options(
            joinedload(Note.company),
            joinedload(Note.job),
            joinedload(Note.application),
            joinedload(Note.contact),
            joinedload(Note.event),
            joinedload(Note.mentioned_contacts),
        ).order_by(desc(Note.updated_at)).limit(limit).all()

    def get_by_id_for_user(self, note_id: int, user_id: int) -> Optional[Note]:
        """Get a note by ID with ownership check."""
        return self.session.query(Note).filter(
            Note.id == note_id,
            Note.user_id == user_id
        ).first()

    def get_by_company(self, company_id: int) -> List[Note]:
        """Get all notes for a company."""
        return self.session.query(Note).filter(
            Note.company_id == company_id
        ).order_by(desc(Note.created_at)).all()

    def get_by_job(self, job_id: int) -> List[Note]:
        """Get all notes for a job."""
        return self.session.query(Note).filter(
            Note.job_id == job_id
        ).order_by(desc(Note.created_at)).all()

    def get_by_application(self, application_id: int) -> List[Note]:
        """Get all notes for an application."""
        return self.session.query(Note).filter(
            Note.application_id == application_id
        ).order_by(desc(Note.created_at)).all()

    def get_by_contact(self, contact_id: int) -> List[Note]:
        """Get all notes for a contact."""
        return self.session.query(Note).filter(
            Note.contact_id == contact_id
        ).order_by(desc(Note.created_at)).all()

    def get_by_event(self, event_id: int) -> List[Note]:
        """Get all notes for an event."""
        return self.session.query(Note).filter(
            Note.event_id == event_id
        ).order_by(desc(Note.created_at)).all()

    def get_by_type(self, note_type: str) -> List[Note]:
        """Get all notes of a specific type."""
        return self.session.query(Note).filter(
            Note.note_type == note_type
        ).order_by(desc(Note.created_at)).all()

    def search(self, query: str) -> List[Note]:
        """Search notes by content (case-insensitive)."""
        return self.session.query(Note).filter(
            Note.content.ilike(f"%{query}%")
        ).order_by(desc(Note.created_at)).all()

    def get_recent(self, limit: int = 20) -> List[Note]:
        """Get most recent notes."""
        return self.session.query(Note).order_by(
            desc(Note.created_at)
        ).limit(limit).all()
