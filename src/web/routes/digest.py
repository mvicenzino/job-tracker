"""Daily digest route: summary of what needs attention."""
from flask import Blueprint, render_template
from flask_login import login_required

from ..helpers import get_service

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
