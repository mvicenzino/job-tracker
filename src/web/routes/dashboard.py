"""Dashboard routes: dashboard, pipeline."""
from datetime import date, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc

from ..helpers import get_service
from ...models import ApplicationStatus, User, WeeklyReflection

bp = Blueprint('dashboard', __name__)


def _monday_of_week(d=None):
    """Get the Monday of the current week."""
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())


def _get_reflection_data(session):
    """Get reflection data for dashboard widget."""
    try:
        this_monday = _monday_of_week()

        # Get recent reflections (last 8 weeks)
        reflections = session.query(WeeklyReflection).filter_by(
            user_id=current_user.id
        ).order_by(desc(WeeklyReflection.week_of)).limit(8).all()

        # Check if current week has a reflection
        current_week = next((r for r in reflections if r.week_of == this_monday), None)
        has_current_week = current_week is not None

        # Calculate streak (consecutive weeks with reflections)
        streak = 0
        check_date = this_monday
        for r in reflections:
            if r.week_of == check_date:
                streak += 1
                check_date -= timedelta(days=7)
            elif r.week_of < check_date:
                break

        # If no reflection this week yet, check if last week continues streak
        if not has_current_week and reflections:
            last_monday = this_monday - timedelta(days=7)
            streak = 0
            check_date = last_monday
            for r in reflections:
                if r.week_of == check_date:
                    streak += 1
                    check_date -= timedelta(days=7)
                elif r.week_of < check_date:
                    break

        # Get mood trend (energy levels over last 4 weeks)
        mood_trend = []
        for r in reflections[:4]:
            mood_trend.append({
                'week': r.week_of.strftime('%b %d'),
                'energy': r.energy_level or 3,
                'momentum': r.momentum or 'steady'
            })
        mood_trend.reverse()  # Oldest first

        # Calculate average energy
        energies = [r.energy_level for r in reflections if r.energy_level]
        avg_energy = sum(energies) / len(energies) if energies else 0

        # Get last reflection for context
        last_reflection = reflections[0] if reflections else None

        return {
            'has_current_week': has_current_week,
            'current_week': current_week,
            'streak': streak,
            'mood_trend': mood_trend,
            'avg_energy': round(avg_energy, 1),
            'total_reflections': len(reflections),
            'last_reflection': last_reflection
        }
    except Exception as e:
        print(f"Error getting reflection data: {e}")
        return {
            'has_current_week': False,
            'current_week': None,
            'streak': 0,
            'mood_trend': [],
            'avg_energy': 0,
            'total_reflections': 0,
            'last_reflection': None
        }


@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard home page."""
    service, session = get_service()
    try:
        data = service.get_dashboard()
        pipeline = service.get_pipeline()

        # Calculate onboarding progress (with fallback for old DB schema)
        try:
            onboarding_completed = getattr(current_user, 'onboarding_completed', False) or False
            onboarding_dismissed = getattr(current_user, 'onboarding_dismissed', False) or False
        except Exception:
            onboarding_completed = False
            onboarding_dismissed = False

        # Check if user has uploaded a resume
        has_resume = bool(getattr(current_user, 'resume_text', None) or getattr(current_user, 'resume_filename', None))

        onboarding = {
            'show': not onboarding_completed and not onboarding_dismissed,
            'completed': onboarding_completed,
            'steps': {
                'resume_uploaded': has_resume,
                'first_application': data['summary']['total_applications'] > 0,
                'first_contact': data['summary']['total_contacts'] > 0,
                'first_event': data['summary']['events_today'] > 0 or len(data.get('upcoming', [])) > 0,
                'first_company': data['summary']['total_applications'] > 0 or len(service.companies.get_all()) > 0,
            }
        }
        onboarding['progress'] = sum(onboarding['steps'].values())
        onboarding['total'] = len(onboarding['steps'])

        # Auto-complete onboarding if all steps done
        if onboarding['progress'] == onboarding['total'] and not onboarding_completed:
            try:
                db = current_app.extensions['db']
                db_session = db.get_session()
                try:
                    user = db_session.query(User).get(current_user.id)
                    if user and hasattr(user, 'onboarding_completed'):
                        user.onboarding_completed = True
                        db_session.commit()
                        onboarding['completed'] = True
                        onboarding['show'] = False
                finally:
                    db_session.close()
            except Exception:
                pass  # Non-critical - don't crash if auto-complete fails

        # Fetch reflection data for dashboard widget
        reflection_data = _get_reflection_data(session)

        return render_template('dashboard.html',
                             dashboard=data,
                             pipeline=pipeline,
                             onboarding=onboarding,
                             reflection=reflection_data,
                             ApplicationStatus=ApplicationStatus)
    finally:
        session.close()


@bp.route('/onboarding/dismiss', methods=['POST'])
@login_required
def dismiss_onboarding():
    """Dismiss the onboarding checklist."""
    db = current_app.extensions['db']
    session = db.get_session()
    try:
        user = session.query(User).get(current_user.id)
        user.onboarding_dismissed = True
        session.commit()
        return jsonify({'success': True})
    finally:
        session.close()


@bp.route('/pipeline')
@login_required
def pipeline():
    """Application pipeline view."""
    service, session = get_service()
    try:
        pipeline = service.get_pipeline()
        return render_template('pipeline.html',
                             pipeline=pipeline,
                             ApplicationStatus=ApplicationStatus)
    finally:
        session.close()
