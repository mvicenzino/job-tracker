"""Market insights routes - BLS data integration."""

from flask import Blueprint, render_template
from flask_login import login_required
from src.services.bls_service import get_market_overview, get_industry_trends, get_historical_trend

insights_bp = Blueprint('insights', __name__, url_prefix='/insights')


@insights_bp.route('/')
@login_required
def market_insights():
    """Display job market insights from BLS data."""
    try:
        overview = get_market_overview()
    except Exception as e:
        return f"BLS Overview Error: {type(e).__name__}: {e}", 500
    
    try:
        industries = get_industry_trends()
    except Exception as e:
        return f"BLS Industries Error: {type(e).__name__}: {e}", 500
    
    try:
        job_openings_history = get_historical_trend('job_openings', 24)
        unemployment_history = get_historical_trend('unemployment_rate', 24)
    except Exception as e:
        return f"BLS History Error: {type(e).__name__}: {e}", 500
    
    # Format industry names nicely
    industry_labels = {
        'professional_business': 'Professional & Business Services',
        'information': 'Information / Tech',
        'finance': 'Finance & Insurance',
        'healthcare': 'Healthcare',
        'retail': 'Retail Trade',
        'manufacturing': 'Manufacturing',
    }
    
    try:
        return render_template('insights.html',
                             overview=overview,
                             industries=industries,
                             industry_labels=industry_labels,
                             job_openings_history=job_openings_history,
                             unemployment_history=unemployment_history)
    except Exception as e:
        return f"Template Error: {type(e).__name__}: {e}", 500
