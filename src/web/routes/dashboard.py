"""Dashboard routes: dashboard, pipeline."""
from flask import Blueprint, render_template
from flask_login import login_required

from ..helpers import get_service
from ...models import ApplicationStatus

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard home page."""
    service, session = get_service()
    try:
        data = service.get_dashboard()
        pipeline = service.get_pipeline()
        return render_template('dashboard.html',
                             dashboard=data,
                             pipeline=pipeline,
                             ApplicationStatus=ApplicationStatus)
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
