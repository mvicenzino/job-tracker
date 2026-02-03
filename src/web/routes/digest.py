"""Daily digest route: summary of what needs attention."""
import os
from datetime import date
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required

from ..helpers import get_service
from ...models import User
from ...services.job_hunt import JobHuntService
from ...services.email_digest import send_digest_to_user, is_email_configured

bp = Blueprint('digest', __name__)


@bp.route('/digest')
@login_required
def daily_digest():
    """Show the daily digest — everything that needs attention today."""
    service, session = get_service()
    try:
        digest = service.get_daily_digest()
        return render_template('digest.html', digest=digest)
    finally:
        session.close()


@bp.route('/digest/send', methods=['POST'])
def send_digest_emails():
    """
    Send digest emails to all users who have it enabled.
    Should be called by a cron job. Requires DIGEST_SECRET env var for auth.
    """
    # Simple auth via secret token
    secret = os.environ.get('DIGEST_SECRET')
    provided_secret = request.headers.get('X-Digest-Secret') or request.args.get('secret')

    if not secret or provided_secret != secret:
        return jsonify({'error': 'Unauthorized'}), 401

    if not is_email_configured():
        return jsonify({'error': 'Email not configured', 'sent': 0}), 503

    db = current_app.extensions['db']
    session = db.get_session()

    try:
        # Get frequency from request (daily or weekly)
        frequency = request.args.get('frequency', 'daily')

        # On weekly digests, only send on Mondays
        if frequency == 'weekly' and date.today().weekday() != 0:
            return jsonify({'message': 'Weekly digest only sends on Mondays', 'sent': 0})

        # Get all users with digest enabled for this frequency
        users = session.query(User).filter(
            User.email_digest_enabled == True,
            User.email_digest_frequency == frequency
        ).all()

        sent_count = 0
        errors = []

        for user in users:
            try:
                service = JobHuntService(session, user_id=user.id)
                if send_digest_to_user(user, service):
                    sent_count += 1
            except Exception as e:
                errors.append(f"{user.email}: {str(e)}")

        return jsonify({
            'success': True,
            'sent': sent_count,
            'total_users': len(users),
            'errors': errors if errors else None
        })
    finally:
        session.close()
