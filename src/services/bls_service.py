"""Bureau of Labor Statistics API service for job market data."""

import requests
from datetime import datetime, timedelta
from functools import lru_cache
import json

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def safe_float(value, default=0.0):
    """Safely convert BLS value to float, handling '-' for missing data."""
    if value is None or value == '-' or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# Key BLS Series IDs
SERIES = {
    # Job Openings (JOLTS) - Total Nonfarm
    'job_openings': 'JTS000000000000000JOL',
    # Hires - Total Nonfarm  
    'hires': 'JTS000000000000000HIL',
    # Separations - Total Nonfarm
    'separations': 'JTS000000000000000TSL',
    # Quits - Total Nonfarm (people voluntarily leaving)
    'quits': 'JTS000000000000000QUL',
    # Unemployment Rate
    'unemployment_rate': 'LNS14000000',
    # Employment Level
    'employment_level': 'LNS12000000',
    # Labor Force Participation Rate
    'labor_force_participation': 'LNS11300000',
}

# Industry-specific job openings
INDUSTRY_SERIES = {
    'professional_business': 'JTS540000000000000JOL',  # Professional & Business Services
    'information': 'JTS510000000000000JOL',  # Information (Tech)
    'finance': 'JTS520000000000000JOL',  # Finance & Insurance
    'healthcare': 'JTS620000000000000JOL',  # Healthcare
    'retail': 'JTS440000000000000JOL',  # Retail
    'manufacturing': 'JTS300000000000000JOL',  # Manufacturing
}


@lru_cache(maxsize=32)
def fetch_bls_series(series_ids: tuple, start_year: int = None, end_year: int = None):
    """Fetch data from BLS API for given series."""
    if not start_year:
        start_year = datetime.now().year - 2
    if not end_year:
        end_year = datetime.now().year
    
    payload = {
        "seriesid": list(series_ids),
        "startyear": str(start_year),
        "endyear": str(end_year),
        "calculations": True,
        "annualaverage": True,
    }
    
    try:
        response = requests.post(BLS_API_URL, json=payload, timeout=10)
        data = response.json()
        
        if data.get('status') == 'REQUEST_SUCCEEDED':
            return data.get('Results', {}).get('series', [])
        else:
            print(f"BLS API error: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"BLS API request failed: {e}")
        return []


def get_market_overview():
    """Get high-level job market overview."""
    series_ids = tuple([
        SERIES['job_openings'],
        SERIES['unemployment_rate'],
        SERIES['quits'],
        SERIES['hires'],
    ])
    
    raw_data = fetch_bls_series(series_ids)
    
    results = {}
    for series in raw_data:
        series_id = series.get('seriesID')
        data_points = series.get('data', [])
        
        # Get latest and previous values
        if len(data_points) >= 2:
            latest = data_points[0]
            previous = data_points[1]
            
            latest_val = safe_float(latest.get('value'))
            prev_val = safe_float(previous.get('value'))
            
            # Calculate change
            if prev_val > 0:
                pct_change = ((latest_val - prev_val) / prev_val) * 100
            else:
                pct_change = 0
            
            # Map series ID to friendly name
            for name, sid in SERIES.items():
                if sid == series_id:
                    results[name] = {
                        'value': latest_val,
                        'previous': prev_val,
                        'change': pct_change,
                        'period': f"{latest.get('periodName', '')} {latest.get('year', '')}",
                        'unit': 'thousands' if 'JTS' in series_id else 'percent' if 'LNS14' in series_id else 'thousands'
                    }
                    break
    
    return results


def get_industry_trends():
    """Get job openings by industry."""
    series_ids = tuple(INDUSTRY_SERIES.values())
    raw_data = fetch_bls_series(series_ids)
    
    results = {}
    for series in raw_data:
        series_id = series.get('seriesID')
        data_points = series.get('data', [])
        
        if len(data_points) >= 2:
            latest = data_points[0]
            previous = data_points[1]
            year_ago = data_points[12] if len(data_points) > 12 else previous
            
            latest_val = safe_float(latest.get('value'))
            prev_val = safe_float(previous.get('value'))
            year_ago_val = safe_float(year_ago.get('value'))
            
            mom_change = ((latest_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
            yoy_change = ((latest_val - year_ago_val) / year_ago_val * 100) if year_ago_val > 0 else 0
            
            for name, sid in INDUSTRY_SERIES.items():
                if sid == series_id:
                    results[name] = {
                        'value': latest_val,
                        'mom_change': mom_change,
                        'yoy_change': yoy_change,
                        'period': f"{latest.get('periodName', '')} {latest.get('year', '')}",
                    }
                    break
    
    return results


def get_historical_trend(series_name: str, months: int = 24):
    """Get historical data for charting."""
    if series_name not in SERIES:
        return []
    
    series_id = SERIES[series_name]
    raw_data = fetch_bls_series((series_id,))
    
    if not raw_data:
        return []
    
    data_points = raw_data[0].get('data', [])[:months]
    
    # Reverse to get chronological order, skip entries with missing values
    result = []
    for dp in reversed(data_points):
        val = dp.get('value', '0')
        # BLS returns '-' for missing/unavailable data
        if val == '-' or val == '':
            continue
        try:
            result.append({
                'period': f"{dp.get('periodName', '')[:3]} {dp.get('year', '')}",
                'value': float(val)
            })
        except (ValueError, TypeError):
            continue  # Skip bad values
    return result
