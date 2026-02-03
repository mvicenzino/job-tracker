"""Dashboard routes: dashboard, pipeline."""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from ..helpers import get_service
from ...models import ApplicationStatus, User

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard home page."""
    service, session = get_service()
    try:
        data = service.get_dashboard()
        pipeline = service.get_pipeline()

        # Calculate onboarding progress (with fallback for old DB schema)
        onboarding_completed = getattr(current_user, 'onboarding_completed', False) or False
        onboarding_dismissed = getattr(current_user, 'onboarding_dismissed', False) or False

        onboarding = {
            'show': not onboarding_completed and not onboarding_dismissed,
            'completed': onboarding_completed,
            'steps': {
                'first_company': data['summary']['total_applications'] > 0 or len(service.companies.get_all()) > 0,
                'first_application': data['summary']['total_applications'] > 0,
                'first_contact': data['summary']['total_contacts'] > 0,
                'first_event': data['summary']['events_today'] > 0 or len(data.get('upcoming', [])) > 0,
            }
        }
        onboarding['progress'] = sum(onboarding['steps'].values())
        onboarding['total'] = len(onboarding['steps'])

        # Auto-complete onboarding if all steps done
        if onboarding['progress'] == onboarding['total'] and not onboarding_completed:
            db = current_app.extensions['db']
            db_session = db.get_session()
            try:
                user = db_session.query(User).get(current_user.id)
                user.onboarding_completed = True
                db_session.commit()
                onboarding['completed'] = True
                onboarding['show'] = False
            finally:
                db_session.close()

        return render_template('dashboard.html',
                             dashboard=data,
                             pipeline=pipeline,
                             onboarding=onboarding,
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
