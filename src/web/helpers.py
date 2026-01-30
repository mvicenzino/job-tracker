"""Shared helpers for route handlers."""
from flask import current_app
from flask_login import current_user

from ..services import JobHuntService
from ..models import User


def get_service():
    """Get a fresh service instance with a new session for current user."""
    db = current_app.extensions['db']
    session = db.get_session()
    user_id = current_user.id if current_user.is_authenticated else None
    return JobHuntService(session, user_id=user_id), session


def get_service_for_user(user_id):
    """Get a service instance for a specific user."""
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
