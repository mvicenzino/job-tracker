"""Notification routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request, current_app
from flask_login import login_required, current_user
from ...repositories.notification import NotificationRepository


def get_db_session():
    """Get a database session from the app context."""
    db = current_app.extensions['db']
    return db.get_session()

bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@bp.route('/')
@login_required
def notifications():
    """Show all notifications."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        all_notifications = repo.get_for_user(current_user.id, limit=100)
        unread_count = repo.get_unread_count(current_user.id)
        return render_template(
            'notifications.html',
            notifications=all_notifications,
            unread_count=unread_count
        )
    finally:
        session.close()


@bp.route('/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a single notification as read."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        repo.mark_as_read(notification_id, current_user.id)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        return redirect(url_for('notifications.notifications'))
    finally:
        session.close()


@bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        count = repo.mark_all_as_read(current_user.id)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'count': count})
        flash(f'Marked {count} notifications as read.', 'success')
        return redirect(url_for('notifications.notifications'))
    finally:
        session.close()


@bp.route('/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete(notification_id):
    """Delete a notification."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        repo.delete(notification_id, current_user.id)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        return redirect(url_for('notifications.notifications'))
    finally:
        session.close()


@bp.route('/clear-read', methods=['POST'])
@login_required
def clear_read():
    """Delete all read notifications."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        count = repo.delete_all_read(current_user.id)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'count': count})
        flash(f'Cleared {count} read notifications.', 'success')
        return redirect(url_for('notifications.notifications'))
    finally:
        session.close()


@bp.route('/count')
@login_required
def count():
    """Get unread notification count (for AJAX badge updates)."""
    session = get_db_session()
    try:
        repo = NotificationRepository(session)
        unread = repo.get_unread_count(current_user.id)
        return jsonify({'count': unread})
    finally:
        session.close()
