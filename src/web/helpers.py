"""Shared helpers for route handlers."""
from flask import current_app, session as flask_session
from flask_login import current_user

from ..services import JobHuntService
from ..models import User, WorkspaceMember


def get_active_workspace_id():
    """Get the active workspace ID from session, verifying membership."""
    ws_id = flask_session.get('active_workspace_id')
    if not ws_id or not current_user.is_authenticated:
        return None
    # Verify the user is still a member
    db = current_app.extensions['db']
    db_session = db.get_session()
    try:
        member = db_session.query(WorkspaceMember).filter_by(
            workspace_id=ws_id, user_id=current_user.id
        ).first()
        if not member:
            flask_session.pop('active_workspace_id', None)
            return None
        return ws_id
    finally:
        db_session.close()


def get_service():
    """Get a fresh service instance with a new session for current user."""
    db = current_app.extensions['db']
    session = db.get_session()
    user_id = current_user.id if current_user.is_authenticated else None
    workspace_id = get_active_workspace_id() if current_user.is_authenticated else None
    return JobHuntService(session, user_id=user_id, workspace_id=workspace_id), session


def get_service_for_user(user_id):
    """Get a service instance for a specific user (personal mode only)."""
    db = current_app.extensions['db']
    session = db.get_session()
    return JobHuntService(session, user_id=user_id), session


def get_user_by_api_key(api_key):
    """Get user by API key for API authentication."""
    if not api_key:
        return None
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        return session.query(User).filter(User.api_key == api_key).first()
    finally:
        session.close()
