"""Market insights routes - BLS data integration."""

from flask import Blueprint, render_template
from flask_login import login_required
from src.services.bls_service import get_market_overview, get_industry_trends, get_historical_trend

insights_bp = Blueprint('insights', __name__, url_prefix='/insights')


@insights_bp.route('/')
@login_required
def market_insights():
    """Display job market insights from BLS data."""
    overview = get_market_overview()
    industries = get_industry_trends()
    job_openings_history = get_historical_trend('job_openings', 24)
    unemployment_history = get_historical_trend('unemployment_rate', 24)
    
    # Format industry names nicely
    industry_labels = {
        'professional_business': 'Professional & Business Services',
        'information': 'Information / Tech',
        'finance': 'Finance & Insurance',
        'healthcare': 'Healthcare',
        'retail': 'Retail Trade',
        'manufacturing': 'Manufacturing',
    }
    
    return render_template('insights.html',
                         overview=overview,
                         industries=industries,
                         industry_labels=industry_labels,
                         job_openings_history=job_openings_history,
                         unemployment_history=unemployment_history)
