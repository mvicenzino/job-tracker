"""Weekly reflection routes: create and view journal entries."""
from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc

from ...models import WeeklyReflection

bp = Blueprint('reflections', __name__)


def _monday_of_week(d=None):
    """Get the Monday of the current week."""
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())


@bp.route('/reflections')
@login_required
def reflections():
    """View all weekly reflections."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        entries = session.query(WeeklyReflection).filter_by(
            user_id=current_user.id
        ).order_by(desc(WeeklyReflection.week_of)).all()

        # Check if there's already a reflection for this week
        this_monday = _monday_of_week()
        has_current_week = any(e.week_of == this_monday for e in entries)

        return render_template('reflections.html',
                             entries=entries,
                             has_current_week=has_current_week)
    finally:
        session.close()


@bp.route('/reflections/new', methods=['GET', 'POST'])
@login_required
def new_reflection():
    """Create a new weekly reflection."""
    if request.method == 'POST':
        db = current_app.extensions['db']
        session = db.get_session()
        try:
            this_monday = _monday_of_week()

            # Check for duplicate
            existing = session.query(WeeklyReflection).filter_by(
                user_id=current_user.id, week_of=this_monday
            ).first()
            if existing:
                flash('You already have a reflection for this week. Edit it instead.', 'warning')
                return redirect(url_for('reflections.reflections'))

            entry = WeeklyReflection(
                user_id=current_user.id,
                week_of=this_monday,
                energy_level=int(request.form.get('energy_level', 3)),
                momentum=request.form.get('momentum', 'steady'),
                wins=request.form.get('wins', '').strip() or None,
                challenges=request.form.get('challenges', '').strip() or None,
                next_week_goals=request.form.get('next_week_goals', '').strip() or None,
            )
            session.add(entry)
            session.commit()
            flash('Reflection saved!', 'success')
            return redirect(url_for('reflections.reflections'))
        finally:
            session.close()

    return render_template('reflection_form.html')
