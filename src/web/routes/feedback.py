"""Feedback routes: submit and list feedback."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from ...models import Feedback

bp = Blueprint('feedback', __name__)


@bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Submit feedback."""
    if request.method == 'POST':
        db = current_app.extensions['db']
        session = db.get_session()
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


@bp.route('/feedback/list')
@login_required
def feedback_list():
    """View all submitted feedback."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        items = session.query(Feedback).order_by(Feedback.created_at.desc()).all()
        return render_template('feedback_list.html', feedback_items=items)
    finally:
        session.close()
