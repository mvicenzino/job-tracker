"""API routes for AJAX operations and Chrome extension."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from ..helpers import get_service, get_service_for_user, get_user_by_api_key
from ...models import ApplicationStatus, ContactType
from ...services.ai_parser import is_ai_parsing_available, parse_job_description

bp = Blueprint('api', __name__)


@bp.route('/api/applications/<int:app_id>/status', methods=['PATCH'])
@login_required
def api_update_status(app_id):
    """API: Update application status."""
    service, session = get_service()
    try:
        data = request.get_json()
        status = ApplicationStatus(data['status'])
        app = service.update_application_status(app_id, status)
        if app:
            return jsonify({'success': True, 'status': app.status.value})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    finally:
        session.close()


@bp.route('/api/applications/<int:app_id>', methods=['PATCH'])
@login_required
def api_update_application(app_id):
    """API: Update application fields."""
    service, session = get_service()
    try:
        data = request.get_json()
        app = service.applications.update(app_id, **data)
        session.commit()
        if app:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    finally:
        session.close()


@bp.route('/api/jobs/<int:job_id>', methods=['PATCH'])
@login_required
def api_update_job(job_id):
    """API: Update job fields."""
    service, session = get_service()
    try:
        data = request.get_json()
        job = service.jobs.update(job_id, **data)
        session.commit()
        if job:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    finally:
        session.close()


@bp.route('/api/companies/<int:company_id>', methods=['PATCH'])
@login_required
def api_update_company(company_id):
    """API: Update company fields."""
    service, session = get_service()
    try:
        data = request.get_json()
        company = service.companies.update(company_id, **data)
        session.commit()
        if company:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    finally:
        session.close()


@bp.route('/api/contacts', methods=['POST', 'OPTIONS'])
def api_create_contact():
    """API: Create a new contact (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None

    # Fall back to session auth
    if not user and current_user.is_authenticated:
        user = current_user

    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            response = jsonify({'success': False, 'error': 'Name is required'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400

        contact_type = ContactType(data.get('contact_type', 'networking'))
        contact = service.add_contact(
            name=data['name'],
            company_name=data.get('company'),
            email=data.get('email'),
            phone=data.get('phone'),
            title=data.get('title'),
            contact_type=contact_type,
            linkedin_url=data.get('linkedin_url'),
            notes=data.get('notes')
        )
        response = jsonify({
            'success': True,
            'contact': {
                'id': contact.id,
                'name': contact.name,
                'company': contact.company.name if contact.company else None
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
    finally:
        session.close()


@bp.route('/api/companies', methods=['POST', 'OPTIONS'])
def api_create_company():
    """API: Create a new company (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None

    # Fall back to session auth
    if not user and current_user.is_authenticated:
        user = current_user

    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            response = jsonify({'success': False, 'error': 'Company name is required'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400

        # Check if company already exists
        existing = service.find_companies(search=data['name'])
        if existing and existing[0].name.lower() == data['name'].lower():
            company = existing[0]
            # Update with any new info
            updates = {}
            if data.get('industry') and not company.industry:
                updates['industry'] = data['industry']
            if data.get('size') and not company.size:
                updates['size'] = data['size']
            if data.get('location') and not company.location:
                updates['location'] = data['location']
            if data.get('website') and not company.website:
                updates['website'] = data['website']
            if data.get('description') and not company.description:
                updates['description'] = data['description']
            if data.get('linkedin_url') and not company.linkedin_url:
                updates['linkedin_url'] = data['linkedin_url']
            if updates:
                service.companies.update(company.id, **updates)
                session.commit()
            response = jsonify({
                'success': True,
                'company': {
                    'id': company.id,
                    'name': company.name
                },
                'message': 'Company already exists, updated with new info'
            })
        else:
            company = service.add_company(
                name=data['name'],
                industry=data.get('industry'),
                location=data.get('location'),
                website=data.get('website'),
                description=data.get('description'),
                size=data.get('size'),
                linkedin_url=data.get('linkedin_url')
            )
            response = jsonify({
                'success': True,
                'company': {
                    'id': company.id,
                    'name': company.name
                }
            })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
    finally:
        session.close()


@bp.route('/api/jobs', methods=['POST', 'OPTIONS'])
def api_create_job():
    """API: Create a new job listing (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None

    # Fall back to session auth
    if not user and current_user.is_authenticated:
        user = current_user

    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('title'):
            response = jsonify({'success': False, 'error': 'Job title is required'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400

        company_name = data.get('company_name', '').strip()
        if not company_name:
            response = jsonify({'success': False, 'error': 'Company name is required'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400

        # Use service.add_job() which handles find-or-create company and commits
        job = service.add_job(
            company_name=company_name,
            title=data['title'],
            description=data.get('description', ''),
            location=data.get('location', ''),
            remote_type=data.get('remote_type', ''),
            job_url=data.get('job_url', ''),
            source=data.get('source', 'LinkedIn'),
            is_flagged=data.get('is_flagged', False)
        )
        response = jsonify({
            'success': True,
            'job': {
                'id': job.id,
                'title': job.title,
                'company': job.company.name
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
    finally:
        session.close()


@bp.route('/api/parse-job-description', methods=['POST'])
@login_required
def api_parse_job_description():
    """API: Parse a job description using AI."""
    if not is_ai_parsing_available():
        return jsonify({'success': False, 'error': 'AI parsing is not available'}), 503

    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'success': False, 'error': 'Text is required'}), 400

    text = data['text'].strip()
    if len(text) < 20:
        return jsonify({'success': False, 'error': 'Text must be at least 20 characters'}), 400

    try:
        parsed = parse_job_description(text)
        return jsonify({'success': True, 'data': parsed})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/followups/due')
@login_required
def api_followups_due():
    """API: Get contacts with follow-ups due today or overdue."""
    service, session = get_service()
    try:
        contacts = service.contacts.get_needing_followup()
        return jsonify({
            'success': True,
            'count': len(contacts),
            'contacts': [
                {
                    'id': c.id,
                    'name': c.name,
                    'company': c.company.name if c.company else None,
                    'next_followup_date': c.next_followup_date.isoformat() if c.next_followup_date else None
                }
                for c in contacts[:10]  # Limit to 10 for notifications
            ]
        })
    finally:
        session.close()


@bp.route('/api/health')
def api_health():
    """API: Health check endpoint to verify app is running."""
    from flask import current_app
    from sqlalchemy import inspect, text

    result = {
        'status': 'ok',
        'checks': {}
    }

    try:
        db = current_app.extensions.get('db')
        if db:
            result['checks']['database'] = 'connected'

            # Check users table columns
            try:
                inspector = inspect(db.engine)
                if 'users' in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns('users')]
                    result['checks']['users_columns'] = columns
                else:
                    result['checks']['users_table'] = 'missing'
            except Exception as e:
                result['checks']['schema_check'] = str(e)
        else:
            result['checks']['database'] = 'not configured'
    except Exception as e:
        result['checks']['database_error'] = str(e)

    return jsonify(result)
