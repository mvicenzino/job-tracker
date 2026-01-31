"""Feedback routes: submit and list feedback."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ..helpers import get_service
from ...models import Feedback

bp = Blueprint('feedback', __name__)


@bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Submit feedback."""
    if request.method == 'POST':
        service, session = get_service()
        try:
            fb = Feedback(
                user_id=current_user.id,
                category=request.form.get('category', 'general'),
                subject=request.form['subject'],
                message=request.form['message']
            )
            session.add(fb)
            session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('dashboard.dashboard'))
        finally:
            session.close()

    return render_template('feedback_form.html')
