import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Workspace(Base, TimestampMixin):
    """A shared workspace where multiple users collaborate on CRM data."""
    __tablename__ = 'workspaces'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    invite_code = Column(String(32), unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:12])

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}')>"


class WorkspaceMember(Base, TimestampMixin):
    """Tracks membership of users in workspaces."""
    __tablename__ = 'workspace_members'
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
    )

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), nullable=False, default='member')  # 'owner' or 'member'

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User")

    def __repr__(self):
        return f"<WorkspaceMember(workspace_id={self.workspace_id}, user_id={self.user_id}, role='{self.role}')>"
