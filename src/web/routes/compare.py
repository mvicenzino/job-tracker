"""Offer comparison route: side-by-side comparison of offers."""
from flask import Blueprint, render_template
from flask_login import login_required

from ..helpers import get_service
from ...models import ApplicationStatus

bp = Blueprint('compare', __name__)


@bp.route('/compare')
@login_required
def compare_offers():
    """Compare applications at OFFER, NEGOTIATING, or ACCEPTED stage side by side."""
    service, session = get_service()
    try:
        offer_statuses = [
            ApplicationStatus.OFFER,
            ApplicationStatus.NEGOTIATING,
            ApplicationStatus.ACCEPTED,
        ]
        offers = []
        for status in offer_statuses:
            offers.extend(service.applications.get_by_status(status))

        return render_template('compare.html', offers=offers)
    finally:
        session.close()
