"""API routes for AJAX operations and Chrome extension."""
import logging
import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..helpers import get_service, get_service_for_user, get_user_by_api_key
from ...models import ApplicationStatus, ContactType, Application, Job, Company, Contact, InterviewPrep
from ...services.ai_parser import is_ai_parsing_available, parse_job_description, analyze_resume_job_fit, generate_cover_letter, generate_interview_prep
from ...services.usage_tracker import UsageTracker

bp = Blueprint('api', __name__)

# Mass assignment protection: only these fields can be set via PATCH
ALLOWED_APPLICATION_FIELDS = {
    'status', 'date_applied', 'date_response', 'date_closed',
    'excitement_level', 'offered_salary', 'offered_bonus', 'offered_equity',
    'rejection_reason', 'lessons_learned', 'resume_version_id', 'cover_letter',
    'referral_contact_id', 'fit_score',
}
ALLOWED_JOB_FIELDS = {
    'title', 'description', 'requirements', 'salary_min', 'salary_max',
    'salary_currency', 'location', 'remote_type', 'job_url', 'source',
    'is_active', 'is_flagged',
}
ALLOWED_COMPANY_FIELDS = {
    'name', 'website', 'industry', 'size', 'location', 'description',
    'culture_notes', 'glassdoor_rating', 'linkedin_url',
}


def _get_cors_origin():
    """Return the allowed CORS origin for the current request, or None."""
    allowed = set()
    # App's own origin (Vercel deployment URL or local dev)
    app_url = os.environ.get('APP_URL', '').rstrip('/')
    if app_url:
        allowed.add(app_url)
    # Always allow same-origin requests
    origin = request.headers.get('Origin', '')
    # Chrome extensions use chrome-extension:// scheme
    if origin.startswith('chrome-extension://'):
        return origin
    # Local development
    if origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
        return origin
    if origin in allowed:
        return origin
    # Fallback: allow if no Origin header (same-origin requests don't send it)
    if not origin:
        return None
    return None


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
        data = {k: v for k, v in data.items() if k in ALLOWED_APPLICATION_FIELDS}
        app = service.applications.update(app_id, **data)
        session.commit()
        if app:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    finally:
        session.close()


@bp.route('/api/jobs/<int:job_id>', methods=['PATCH', 'OPTIONS'])
def api_update_job(job_id):
    """API: Update job fields."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None

    # Fall back to session auth
    if not user and current_user.is_authenticated:
        user = current_user

    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        data = {k: v for k, v in data.items() if k in ALLOWED_JOB_FIELDS}
        job = service.jobs.update(job_id, **data)
        session.commit()
        if job:
            response = jsonify({'success': True})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
            return response
        response = jsonify({'success': False, 'error': 'Not found'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 404
    finally:
        session.close()


@bp.route('/api/companies/<int:company_id>', methods=['PATCH', 'OPTIONS'])
def api_update_company(company_id):
    """API: Update company fields."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None

    # Fall back to session auth
    if not user and current_user.is_authenticated:
        user = current_user

    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        data = {k: v for k, v in data.items() if k in ALLOWED_COMPANY_FIELDS}
        company = service.companies.update(company_id, **data)
        session.commit()
        if company:
            response = jsonify({'success': True})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
            return response
        response = jsonify({'success': False, 'error': 'Not found'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 404
    finally:
        session.close()


@bp.route('/api/contacts', methods=['POST', 'OPTIONS'])
def api_create_contact():
    """API: Create a new contact (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            response = jsonify({'success': False, 'error': 'Name is required'})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response
    except Exception as e:
        current_app.logger.exception('API error')
        response = jsonify({'success': False, 'error': 'Internal server error'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 500
    finally:
        session.close()


@bp.route('/api/contacts', methods=['GET', 'OPTIONS'])
def api_list_contacts():
    """API: List all contacts with optional search/followup filter."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        limit = request.args.get('limit', 100, type=int)
        search = request.args.get('q', '').strip()
        followup = request.args.get('followup')

        if search:
            contacts = service.contacts.search_by_name(search)[:limit]
        elif followup:
            contacts = service.contacts.get_needing_followup()[:limit]
        else:
            contacts = service.contacts.get_all(limit=limit)

        response = jsonify({
            'success': True,
            'contacts': [
                {
                    'id': c.id,
                    'name': c.name,
                    'email': c.email,
                    'phone': c.phone,
                    'linkedinUrl': c.linkedin_url,
                    'title': c.title,
                    'contactType': c.contact_type.value if c.contact_type else None,
                    'companyName': c.company.name if c.company else None,
                    'relationshipStrength': c.relationship_strength,
                    'lastContactDate': c.last_contact_date.isoformat() if c.last_contact_date else None,
                    'nextFollowupDate': c.next_followup_date.isoformat() if c.next_followup_date else None,
                    'notes': c.notes,
                    'howWeMet': c.how_we_met,
                    'createdAt': c.created_at.isoformat() if hasattr(c, 'created_at') and c.created_at else None,
                }
                for c in contacts
            ]
        })
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response
    except Exception as e:
        current_app.logger.exception('API error')
        response = jsonify({'success': False, 'error': 'Internal server error'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 500
    finally:
        session.close()


@bp.route('/api/contacts/<int:contact_id>', methods=['DELETE', 'OPTIONS'])
def api_delete_contact(contact_id):
    """API: Delete a contact by ID."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        c = service.contacts.get_by_id(contact_id)
        if not c:
            response = jsonify({'success': False, 'error': 'Contact not found'})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
            return response, 404

        session.delete(c)
        session.commit()
        response = jsonify({'success': True, 'deleted': contact_id})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response
    except Exception as e:
        session.rollback()
        current_app.logger.exception('API error')
        response = jsonify({'success': False, 'error': 'Internal server error'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 500
    finally:
        session.close()


@bp.route('/api/companies', methods=['POST', 'OPTIONS'])
def api_create_company():
    """API: Create a new company (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            response = jsonify({'success': False, 'error': 'Company name is required'})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response
    except Exception as e:
        current_app.logger.exception('API error')
        response = jsonify({'success': False, 'error': 'Internal server error'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 500
    finally:
        session.close()


@bp.route('/api/companies/search', methods=['GET'])
@login_required
def api_search_companies():
    """API: Search companies by name (for contact form autocomplete)."""
    service, session = get_service()
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({'companies': []})
        
        companies = service.companies.search_by_name(query)
        return jsonify({
            'companies': [
                {'id': c.id, 'name': c.name}
                for c in companies[:10]  # Limit to 10 results
            ]
        })
    finally:
        session.close()


@bp.route('/api/jobs', methods=['POST', 'OPTIONS'])
def api_create_job():
    """API: Create a new job listing (for Chrome extension)."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        if not data or not data.get('title'):
            response = jsonify({'success': False, 'error': 'Job title is required'})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
            return response, 400

        company_name = data.get('company_name', '').strip()
        if not company_name:
            response = jsonify({'success': False, 'error': 'Company name is required'})
            cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        
        # Auto-score job if user has resume, AI is available, and usage allows it
        auto_score_allowed = True
        try:
            from ...models import User as UserModel
            user_for_usage = session.query(UserModel).get(user.id)
            auto_tracker = UsageTracker(user_for_usage, session)
            auto_allowed, _ = auto_tracker.can_use_ai_score()
            auto_score_allowed = auto_allowed
        except Exception:
            pass

        if auto_score_allowed and is_ai_parsing_available() and user.resume_text and len(user.resume_text.strip()) > 100:
            job_desc = job.description or ''
            if job.requirements:
                job_desc += '\n\nRequirements:\n' + job.requirements
            
            # Only score if we have meaningful job description
            if len(job_desc.strip()) >= 50:
                try:
                    from datetime import datetime
                    import json
                    analysis = analyze_resume_job_fit(
                        resume_text=user.resume_text,
                        job_description=job_desc,
                        job_title=job.title,
                        company_name=job.company.name if job.company else None
                    )
                    job.fit_score = analysis.get('match_score')
                    job.fit_analysis = json.dumps(analysis)
                    job.scored_at = datetime.utcnow()
                    # scored_with_resume_id would be set if resume_versions exist
                    auto_tracker.record_ai_score()
                    session.commit()
                    logging.info(f"Auto-scored job {job.id}: {job.fit_score}%")
                except Exception as score_error:
                    # Don't fail job creation if scoring fails
                    logging.warning(f"Auto-scoring failed for job {job.id}: {score_error}")
        
        # Also create a lead (application in INTERESTED status) if requested
        application = None
        review_url = None
        create_lead = data.get('create_lead', True)  # Default to creating lead
        
        if create_lead:
            from ...models import Application, ApplicationStatus
            application = Application(
                user_id=user.id,
                job_id=job.id,
                status=ApplicationStatus.INTERESTED
            )
            session.add(application)
            session.commit()
            review_url = f"/applications/{application.id}?new=1"
        
        # Create notification for the new lead
        try:
            from ...repositories.notification import NotificationRepository
            notif_repo = NotificationRepository(session)
            notif_repo.create(
                user_id=user.id,
                notification_type='job_added',
                title=f"New lead: {job.title}",
                message=f"{job.company.name} • {data.get('location', 'Location TBD')}",
                link_url=review_url or f"/jobs",
                job_id=job.id,
                application_id=application.id if application else None
            )
        except Exception as notif_error:
            # Don't fail the job creation if notification fails
            print(f"Failed to create notification: {notif_error}")
        
        response = jsonify({
            'success': True,
            'job': {
                'id': job.id,
                'title': job.title,
                'company': job.company.name
            },
            'application': {
                'id': application.id,
                'review_url': review_url
            } if application else None
        })
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return response
    except Exception as e:
        current_app.logger.exception('API error')
        response = jsonify({'success': False, 'error': 'Internal server error'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
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
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/api/analyze-resume-fit', methods=['POST'])
@login_required
def api_analyze_resume_fit():
    """API: Analyze how well a resume matches a job description."""
    if not is_ai_parsing_available():
        return jsonify({'success': False, 'error': 'AI analysis is not available. Please set ANTHROPIC_API_KEY.'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    service, session = get_service()
    try:
        # Check usage limits
        from ...models import User
        user = session.query(User).get(current_user.id)
        tracker = UsageTracker(user, session)
        allowed, limit_info = tracker.can_use_ai_score()
        if not allowed:
            session.commit()
            return jsonify({'success': False, 'upgrade_required': True, 'error': limit_info['message'], 'message': limit_info['message']}), 403

        # Get job info
        job_id = data.get('job_id')
        app_id = data.get('application_id')

        job = None
        if app_id:
            app = service.applications.get_by_id(app_id)
            if app:
                job = app.job
        elif job_id:
            job = service.jobs.get_by_id(job_id)

        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        # Get job description
        job_description = job.description or ''
        if job.requirements:
            job_description += '\n\nRequirements:\n' + job.requirements

        if len(job_description.strip()) < 50:
            return jsonify({'success': False, 'error': 'Job description is too short for analysis. Please add more details to the job posting.'}), 400

        # Get resume content
        resume_text = None
        resume_version_id = data.get('resume_version_id')

        if resume_version_id:
            resume_version = service.resume_versions.get_by_id(resume_version_id)
            if resume_version:
                resume_text = resume_version.content
        else:
            # Try to get most recent resume version
            versions = service.resume_versions.get_all(limit=1)
            if versions:
                resume_text = versions[0].content

        if not resume_text or len(resume_text.strip()) < 100:
            return jsonify({'success': False, 'error': 'No resume found or resume content is too short. Please add a resume version first.'}), 400

        # Run AI analysis
        result = analyze_resume_job_fit(
            resume_text=resume_text,
            job_description=job_description,
            job_title=job.title,
            company_name=job.company.name if job.company else None
        )

        # Record usage and save the fit score to both Application and Job
        tracker.record_ai_score()
        score = result.get('match_score')
        if score is not None:
            if app_id:
                service.applications.update(app_id, fit_score=score)
            if job:
                import json as _json
                from datetime import datetime as _dt
                job.fit_score = score
                job.fit_analysis = _json.dumps(result)
                job.scored_at = _dt.utcnow()
        session.commit()

        return jsonify({'success': True, 'analysis': result})

    except Exception as e:
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    finally:
        session.close()


@bp.route('/api/generate-cover-letter', methods=['POST'])
@login_required
def api_generate_cover_letter():
    """API: Generate a cover letter using AI."""
    if not is_ai_parsing_available():
        return jsonify({'success': False, 'error': 'AI is not available. Please set ANTHROPIC_API_KEY.'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    service, session = get_service()
    try:
        # Check usage limits
        from ...models import User
        user = session.query(User).get(current_user.id)
        tracker = UsageTracker(user, session)
        allowed, limit_info = tracker.can_use_cover_letter()
        if not allowed:
            session.commit()
            return jsonify({'success': False, 'upgrade_required': True, 'error': limit_info['message'], 'message': limit_info['message']}), 403

        # Get job info
        app_id = data.get('application_id')
        job_id = data.get('job_id')

        job = None
        app = None
        if app_id:
            app = service.applications.get_by_id(app_id)
            if app:
                job = app.job
        elif job_id:
            job = service.jobs.get_by_id(job_id)

        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        # Get job description
        job_description = job.description or ''
        if job.requirements:
            job_description += '\n\nRequirements:\n' + job.requirements

        if len(job_description.strip()) < 50:
            return jsonify({'success': False, 'error': 'Job description is too short. Please add more details to the job posting.'}), 400

        # Get resume content
        resume_text = None
        resume_version_id = data.get('resume_version_id')

        if resume_version_id:
            resume_version = service.resume_versions.get_by_id(resume_version_id)
            if resume_version:
                resume_text = resume_version.content
        else:
            # Try to get most recent resume version
            versions = service.resume_versions.get_all(limit=1)
            if versions:
                resume_text = versions[0].content

        # Fall back to user's main resume text
        if not resume_text:
            resume_text = current_user.resume_text

        if not resume_text or len(resume_text.strip()) < 100:
            return jsonify({'success': False, 'error': 'No resume found. Please add a resume first.'}), 400

        # Generate cover letter
        cover_letter = generate_cover_letter(
            resume_text=resume_text,
            job_description=job_description,
            job_title=job.title,
            company_name=job.company.name if job.company else None
        )

        # Record usage
        tracker.record_cover_letter()

        # Optionally save to application
        if app_id and data.get('save', False):
            service.applications.update(app_id, cover_letter=cover_letter)
        session.commit()

        return jsonify({
            'success': True,
            'cover_letter': cover_letter,
            'job_title': job.title,
            'company_name': job.company.name if job.company else None
        })

    except Exception as e:
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    finally:
        session.close()


@bp.route('/api/jobs/score-batch', methods=['POST'])
@login_required
def api_score_batch():
    """API: Score all unscored jobs for the current user."""
    if not is_ai_parsing_available():
        return jsonify({'success': False, 'error': 'AI scoring is not available. Please set ANTHROPIC_API_KEY.'}), 503

    service, session = get_service()
    try:
        # Check usage limits
        from ...models import User as UserModel
        user = session.query(UserModel).get(current_user.id)
        tracker = UsageTracker(user, session)
        allowed, limit_info = tracker.can_use_ai_score()
        if not allowed:
            session.commit()
            return jsonify({'success': False, 'upgrade_required': True, 'error': limit_info['message'], 'message': limit_info['message']}), 403

        # Check resume
        if not current_user.resume_text or len(current_user.resume_text.strip()) < 100:
            return jsonify({'success': False, 'error': 'No resume found. Please add a resume first.'}), 400

        # Get all jobs without scores
        from ...models import Job
        from datetime import datetime
        import json

        unscored_jobs = session.query(Job).filter(
            Job.user_id == current_user.id,
            Job.fit_score.is_(None)
        ).all()

        if not unscored_jobs:
            return jsonify({'success': True, 'message': 'All jobs already scored', 'scored': 0})

        # Cap batch to remaining free scores
        remaining = tracker.remaining_scores()
        if remaining is not None:
            unscored_jobs = unscored_jobs[:remaining]

        scored_count = 0
        errors = []

        for job in unscored_jobs:
            job_desc = job.description or ''
            if job.requirements:
                job_desc += '\n\nRequirements:\n' + job.requirements

            # Skip jobs with insufficient description
            if len(job_desc.strip()) < 50:
                errors.append(f"Job {job.id} ({job.title}): description too short")
                continue

            try:
                analysis = analyze_resume_job_fit(
                    resume_text=current_user.resume_text,
                    job_description=job_desc,
                    job_title=job.title,
                    company_name=job.company.name if job.company else None
                )
                job.fit_score = analysis.get('match_score')
                job.fit_analysis = json.dumps(analysis)
                job.scored_at = datetime.utcnow()
                tracker.record_ai_score()
                scored_count += 1
            except Exception as e:
                logging.warning(f"Batch scoring failed for job {job.id}: {e}")
                errors.append(f"Job {job.id} ({job.title}): scoring failed")

        session.commit()

        result = {
            'success': True,
            'scored': scored_count,
            'total': len(unscored_jobs)
        }

        if errors:
            result['errors'] = errors[:5]  # Limit error list

        return jsonify(result)

    except Exception as e:
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    finally:
        session.close()


@bp.route('/api/applications/<int:app_id>/interview-prep', methods=['GET', 'POST'])
@login_required
def api_interview_prep(app_id):
    """API: Get or generate interview prep materials for an application."""
    from flask import current_app

    service, session = get_service()
    try:
        # Get the application
        app = service.applications.get_by_id(app_id)
        if not app:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        job = app.job
        if not job:
            return jsonify({'success': False, 'error': 'Job not found for this application'}), 404

        # GET: Return existing prep if available
        if request.method == 'GET':
            existing_prep = session.query(InterviewPrep).filter(
                InterviewPrep.application_id == app_id,
                InterviewPrep.user_id == current_user.id
            ).order_by(InterviewPrep.created_at.desc()).first()

            if existing_prep:
                return jsonify({'success': True, 'prep': existing_prep.to_dict()})
            else:
                return jsonify({'success': True, 'prep': None})

        # POST: Generate new prep
        if not is_ai_parsing_available():
            return jsonify({'success': False, 'error': 'AI is not available. Please set ANTHROPIC_API_KEY.'}), 503

        # Check usage limits (interview prep is Pro only)
        from ...models import User as UserModel
        user_obj = session.query(UserModel).get(current_user.id)
        tracker = UsageTracker(user_obj, session)
        allowed, limit_info = tracker.can_use_interview_prep()
        if not allowed:
            session.commit()
            return jsonify({'success': False, 'upgrade_required': True, 'error': limit_info['message'], 'message': limit_info['message']}), 403

        data = request.get_json() or {}

        # Get job description
        job_description = job.description or ''
        if job.requirements:
            job_description += '\n\nRequirements:\n' + job.requirements

        if len(job_description.strip()) < 50:
            return jsonify({'success': False, 'error': 'Job description is too short. Please add more details to the job posting.'}), 400

        # Get resume content
        resume_text = None
        resume_version_id = data.get('resume_version_id')

        if resume_version_id:
            resume_version = service.resume_versions.get_by_id(resume_version_id)
            if resume_version:
                resume_text = resume_version.content
        else:
            # Try to get most recent resume version
            versions = service.resume_versions.get_all(limit=1)
            if versions:
                resume_text = versions[0].content
                resume_version_id = versions[0].id

        # Fall back to user's main resume text
        if not resume_text:
            resume_text = current_user.resume_text

        if not resume_text or len(resume_text.strip()) < 100:
            return jsonify({'success': False, 'error': 'No resume found. Please add a resume first.'}), 400

        # Generate interview prep using AI
        try:
            prep_data = generate_interview_prep(
                resume_text=resume_text,
                job_description=job_description,
                job_title=job.title,
                company_name=job.company.name if job.company else None
            )
        except Exception as e:
            logging.error(f"Interview prep generation failed: {e}")
            current_app.logger.exception('Interview prep generation failed')
            return jsonify({'success': False, 'error': 'AI generation failed. Please try again.'}), 500

        # Check if we should regenerate (delete old) or create new
        regenerate = data.get('regenerate', False)
        if regenerate:
            # Delete existing preps for this application
            session.query(InterviewPrep).filter(
                InterviewPrep.application_id == app_id,
                InterviewPrep.user_id == current_user.id
            ).delete()

        # Save to database
        interview_prep = InterviewPrep(
            user_id=current_user.id,
            application_id=app_id,
            resume_version_id=resume_version_id,
            questions=prep_data.get('questions', []),
            talking_points=prep_data.get('talking_points', []),
            questions_to_ask=prep_data.get('questions_to_ask', []),
            company_brief=prep_data.get('company_brief', {}),
            red_flags=prep_data.get('red_flags', []),
            closing_strategy=prep_data.get('closing_strategy', {})
        )
        session.add(interview_prep)
        tracker.record_interview_prep()
        session.commit()

        return jsonify({
            'success': True,
            'prep': interview_prep.to_dict()
        })

    except Exception as e:
        logging.error(f"Interview prep error: {e}")
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    finally:
        session.close()


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
    from sqlalchemy import text

    result = {
        'status': 'ok',
        'checks': {}
    }

    try:
        db = current_app.extensions.get('db')
        if db:
            session = db.get_session()
            try:
                session.execute(text('SELECT 1'))
                result['checks']['database'] = 'connected'
            except Exception:
                result['checks']['database'] = 'unreachable'
            finally:
                session.close()
        else:
            result['checks']['database'] = 'not configured'
    except Exception:
        result['checks']['database'] = 'error'

    return jsonify(result)


@bp.route('/api/cron/notifications', methods=['POST'])
def cron_generate_notifications():
    """
    Cron endpoint: Generate automated notifications for all users.
    
    Should be called periodically (e.g., every 30 minutes) by a cron job.
    Secured by CRON_SECRET environment variable.
    """
    import os
    from flask import current_app
    from ...services.notification_generator import NotificationGenerator
    
    # Verify cron secret
    cron_secret = os.environ.get('CRON_SECRET')
    provided_secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')

    if not cron_secret:
        if os.environ.get('VERCEL'):
            return jsonify({'error': 'CRON_SECRET not configured'}), 401
    elif provided_secret != cron_secret:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db = current_app.extensions['db']
        session = db.get_session()

        try:
            generator = NotificationGenerator(session)
            results = generator.generate_all()
            
            return jsonify({
                'success': True,
                'generated': results
            })
        finally:
            session.close()
            
    except Exception as e:
        current_app.logger.exception('Cron notifications error')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@bp.route('/api/cron/fit-scores', methods=['POST'])
def cron_score_fit():
    """
    Cron endpoint: Auto-score unscored jobs for all active users.

    Runs daily via Vercel Cron. For each user with a resume, finds jobs
    that have descriptions but no fit score, and scores them.
    Secured by CRON_SECRET environment variable.
    """
    import os
    import json
    from datetime import datetime
    from flask import current_app
    from ...models import User, ResumeVersion

    # Verify cron secret
    cron_secret = os.environ.get('CRON_SECRET')
    provided_secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')

    if not cron_secret:
        if os.environ.get('VERCEL'):
            return jsonify({'error': 'CRON_SECRET not configured'}), 401
    elif provided_secret != cron_secret:
        return jsonify({'error': 'Unauthorized'}), 401

    if not is_ai_parsing_available():
        return jsonify({'success': False, 'error': 'AI scoring not available'}), 503

    try:
        db = current_app.extensions['db']
        session = db.get_session()

        try:
            users = session.query(User).filter(User.is_active == True).all()

            summary = {
                'users_processed': 0,
                'jobs_scored': 0,
                'errors': []
            }

            for user in users:
                # Determine resume text: prefer user.resume_text, fall back to latest ResumeVersion
                resume_text = None
                resume_version_id = None

                if user.resume_text and len(user.resume_text.strip()) >= 100:
                    resume_text = user.resume_text
                else:
                    latest_rv = session.query(ResumeVersion).filter(
                        ResumeVersion.user_id == user.id
                    ).order_by(ResumeVersion.updated_at.desc()).first()
                    if latest_rv and latest_rv.content and len(latest_rv.content.strip()) >= 100:
                        resume_text = latest_rv.content
                        resume_version_id = latest_rv.id

                if not resume_text:
                    continue

                # Get unscored jobs with sufficient descriptions
                unscored_jobs = session.query(Job).filter(
                    Job.user_id == user.id,
                    Job.fit_score.is_(None)
                ).limit(10).all()

                scored_for_user = 0
                for job in unscored_jobs:
                    job_desc = job.description or ''
                    if job.requirements:
                        job_desc += '\n\nRequirements:\n' + job.requirements

                    if len(job_desc.strip()) < 50:
                        continue

                    try:
                        analysis = analyze_resume_job_fit(
                            resume_text=resume_text,
                            job_description=job_desc,
                            job_title=job.title,
                            company_name=job.company.name if job.company else None
                        )
                        job.fit_score = analysis.get('match_score')
                        job.fit_analysis = json.dumps(analysis)
                        job.scored_at = datetime.utcnow()
                        if resume_version_id:
                            job.scored_with_resume_id = resume_version_id
                        scored_for_user += 1
                    except Exception as e:
                        logging.warning(f"Cron scoring failed for job {job.id}: {e}")
                        summary['errors'].append(f"Job {job.id}: scoring failed")

                if scored_for_user > 0:
                    session.commit()
                    summary['users_processed'] += 1
                    summary['jobs_scored'] += scored_for_user

            # Trim errors for response size
            summary['errors'] = summary['errors'][:10]

            return jsonify({'success': True, **summary})
        finally:
            session.close()

    except Exception as e:
        current_app.logger.exception('API error')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/api/notifications/generate', methods=['POST'])
@login_required
def generate_my_notifications():
    """
    Generate notifications for the current user (manual trigger).
    Useful for testing or immediate refresh.
    """
    from flask import current_app
    from ...services.notification_generator import NotificationGenerator
    
    try:
        db = current_app.extensions['db']
        session = db.get_session()
        
        try:
            generator = NotificationGenerator(session)
            
            r24, r1 = generator.generate_interview_reminders(current_user.id)
            followups = generator.generate_follow_up_nudges(current_user.id)
            
            return jsonify({
                'success': True,
                'generated': {
                    'interview_reminders_24h': r24,
                    'interview_reminders_1h': r1,
                    'follow_up_nudges': followups
                }
            })
        finally:
            session.close()
            
    except Exception as e:
        current_app.logger.exception('Cron fit-scores error')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@bp.route('/api/search')
@login_required
def global_search():
    """Global search across applications, contacts, and companies."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'results': []})
    
    db = current_app.extensions['db']
    session = db.get_session()
    
    try:
        search_term = f"%{query}%"
        results = []
        
        # Search applications (via company name and job title)
        try:
            apps = session.query(Application, Job, Company).join(
                Job, Application.job_id == Job.id
            ).join(
                Company, Job.company_id == Company.id
            ).filter(
                Application.user_id == current_user.id,
                (Company.name.ilike(search_term)) | (Job.title.ilike(search_term))
            ).limit(5).all()
            
            for app, job, company in apps:
                status_str = ''
                if app.status:
                    try:
                        status_str = app.status.value.replace('_', ' ').title()
                    except:
                        status_str = str(app.status)
                results.append({
                    'type': 'application',
                    'icon': '📄',
                    'title': f"{job.title} at {company.name}",
                    'subtitle': status_str,
                    'url': f"/applications/{app.id}"
                })
        except Exception as e:
            logging.error(f"Search applications error: {e}")
        
        # Search contacts
        try:
            contacts = session.query(Contact).outerjoin(
                Company, Contact.company_id == Company.id
            ).filter(
                Contact.user_id == current_user.id,
                (Contact.name.ilike(search_term)) | 
                (Contact.email.ilike(search_term)) |
                (Company.name.ilike(search_term))
            ).limit(5).all()
            
            for contact in contacts:
                subtitle = ''
                if contact.company:
                    subtitle = contact.company.name
                elif hasattr(contact, 'title') and contact.title:
                    subtitle = contact.title
                results.append({
                    'type': 'contact',
                    'icon': '👤',
                    'title': contact.name,
                    'subtitle': subtitle,
                    'url': f"/contacts/{contact.id}/edit"
                })
        except Exception as e:
            logging.error(f"Search contacts error: {e}")
        
        # Search companies
        try:
            companies = session.query(Company).filter(
                Company.user_id == current_user.id,
                Company.name.ilike(search_term)
            ).limit(5).all()
            
            for company in companies:
                results.append({
                    'type': 'company',
                    'icon': '🏢',
                    'title': company.name,
                    'subtitle': company.industry or '',
                    'url': f"/companies/{company.id}/edit"
                })
        except Exception as e:
            logging.error(f"Search companies error: {e}")
        
        return jsonify({'results': results[:10]})  # Max 10 total results

    except Exception as e:
        current_app.logger.exception('Global search error')
        return jsonify({'results': []}), 500
    finally:
        session.close()


# ── Langly Integration (API-key-authenticated GET endpoints) ──────────────────

def _api_key_or_session_auth():
    """Authenticate via API key or session. Returns (user, error_response)."""
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers['Access-Control-Allow-Origin'] = cors_origin
        return None, (response, 401)
    return user, None


def _cors_response(data, status=200):
    """Create a JSON response with CORS headers."""
    response = jsonify(data)
    cors_origin = _get_cors_origin()
    if cors_origin:
        response.headers['Access-Control-Allow-Origin'] = cors_origin
    return response, status


def _cors_options():
    """Handle CORS preflight for GET endpoints."""
    response = jsonify({'status': 'ok'})
    cors_origin = _get_cors_origin()
    if cors_origin:
        response.headers['Access-Control-Allow-Origin'] = cors_origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
    return response


@bp.route('/api/contacts/<int:contact_id>', methods=['GET', 'OPTIONS'])
def api_get_contact_detail(contact_id):
    """API: Get a single contact with full detail."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        c = service.contacts.get_by_id(contact_id)
        if not c:
            return _cors_response({'success': False, 'error': 'Contact not found'}, 404)
        result = {
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'phone': c.phone,
            'linkedinUrl': c.linkedin_url,
            'title': c.title,
            'contactType': c.contact_type.value if c.contact_type else None,
            'companyName': c.company.name if c.company else None,
            'relationshipStrength': c.relationship_strength,
            'lastContactDate': c.last_contact_date.isoformat() if c.last_contact_date else None,
            'nextFollowupDate': c.next_followup_date.isoformat() if c.next_followup_date else None,
            'notes': c.notes,
            'howWeMet': c.how_we_met,
            'createdAt': c.created_at.isoformat() if c.created_at else None,
            'updatedAt': c.updated_at.isoformat() if c.updated_at else None,
        }
        return _cors_response({'success': True, 'contact': result})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/contacts/search', methods=['GET', 'OPTIONS'])
def api_search_contacts():
    """API: Search contacts by name."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        q = request.args.get('q', '')
        if not q:
            return _cors_response({'success': True, 'contacts': []})
        matches = service.contacts.search_by_name(q)[:10]
        items = [{
            'id': c.id,
            'name': c.name,
            'companyName': c.company.name if c.company else None,
            'title': c.title,
        } for c in matches]
        return _cors_response({'success': True, 'contacts': items})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/pipeline', methods=['GET', 'OPTIONS'])
def api_pipeline():
    """API: Get applications grouped by pipeline status."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        pipeline = service.get_pipeline()
        result = {}
        for status_val, apps in pipeline.items():
            result[status_val] = []
            for app in apps:
                result[status_val].append({
                    'id': app.id,
                    'status': app.status.value if app.status else status_val,
                    'dateApplied': app.date_applied.isoformat() if app.date_applied else None,
                    'excitementLevel': app.excitement_level,
                    'jobTitle': app.job.title if app.job else None,
                    'companyName': app.job.company.name if app.job and app.job.company else None,
                    'location': app.job.location if app.job else None,
                    'remoteType': app.job.remote_type if app.job else None,
                    'salaryMin': app.job.salary_min if app.job else None,
                    'salaryMax': app.job.salary_max if app.job else None,
                })
        return _cors_response({'success': True, 'pipeline': result})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/applications', methods=['GET', 'OPTIONS'])
def api_get_applications():
    """API: Get all applications, optionally filtered by status."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        status_filter = request.args.get('status')
        limit = request.args.get('limit', 20, type=int)

        if status_filter:
            try:
                status_enum = ApplicationStatus(status_filter)
                apps = service.applications.get_by_status(status_enum)
            except ValueError:
                return _cors_response({'success': False, 'error': f'Invalid status: {status_filter}'}, 400)
        else:
            rows = service.applications.get_with_company_info()
            # Returns Row objects of (Application, Job, Company)
            items = []
            for row in rows[:limit]:
                app, job, company = row[0], row[1], row[2]
                items.append({
                    'id': app.id,
                    'status': app.status.value if app.status else None,
                    'dateApplied': app.date_applied.isoformat() if app.date_applied else None,
                    'excitementLevel': app.excitement_level,
                    'fitScore': app.fit_score,
                    'jobTitle': job.title,
                    'companyName': company.name,
                    'location': job.location,
                    'remoteType': job.remote_type,
                    'salaryMin': job.salary_min,
                    'salaryMax': job.salary_max,
                })
            return _cors_response({'success': True, 'applications': items})

        # Status-filtered path: apps are Application objects
        items = []
        for app in apps[:limit]:
            items.append({
                'id': app.id,
                'status': app.status.value if app.status else None,
                'dateApplied': app.date_applied.isoformat() if app.date_applied else None,
                'excitementLevel': app.excitement_level,
                'fitScore': app.fit_score,
                'jobTitle': app.job.title if app.job else None,
                'companyName': app.job.company.name if app.job and app.job.company else None,
                'location': app.job.location if app.job else None,
                'remoteType': app.job.remote_type if app.job else None,
                'salaryMin': app.job.salary_min if app.job else None,
                'salaryMax': app.job.salary_max if app.job else None,
            })
        return _cors_response({'success': True, 'applications': items})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/applications/<int:app_id>/detail', methods=['GET', 'OPTIONS'])
def api_get_application_detail(app_id):
    """API: Get full details for a single application."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        details = service.get_application_details(app_id)
        if not details:
            return _cors_response({'success': False, 'error': 'Application not found'}, 404)

        app = details['application']
        job = details['job']
        company = details['company']
        events = details['events']
        notes = details['notes']
        referral = details['referral']

        result = {
            'id': app.id,
            'status': app.status.value if app.status else None,
            'dateApplied': app.date_applied.isoformat() if app.date_applied else None,
            'dateResponse': app.date_response.isoformat() if app.date_response else None,
            'dateClosed': app.date_closed.isoformat() if app.date_closed else None,
            'excitementLevel': app.excitement_level,
            'fitScore': app.fit_score,
            'offeredSalary': app.offered_salary,
            'offeredBonus': app.offered_bonus,
            'offeredEquity': app.offered_equity,
            'rejectionReason': app.rejection_reason,
            'lessonsLearned': app.lessons_learned,
            'job': {
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'requirements': job.requirements,
                'location': job.location,
                'remoteType': job.remote_type,
                'salaryMin': job.salary_min,
                'salaryMax': job.salary_max,
                'jobUrl': job.job_url,
                'source': job.source,
            } if job else None,
            'company': {
                'id': company.id,
                'name': company.name,
                'industry': company.industry if hasattr(company, 'industry') else None,
                'location': company.location if hasattr(company, 'location') else None,
                'website': company.website if hasattr(company, 'website') else None,
            } if company else None,
            'events': [
                {
                    'id': ev.id,
                    'title': ev.title,
                    'eventType': ev.event_type.value if ev.event_type else None,
                    'startTime': ev.start_time.isoformat() if ev.start_time else None,
                    'endTime': ev.end_time.isoformat() if ev.end_time else None,
                    'location': ev.location,
                    'meetingLink': ev.meeting_link,
                    'completed': ev.completed,
                }
                for ev in (events or [])
            ],
            'notes': [
                {
                    'id': n.id,
                    'content': n.content,
                    'noteType': n.note_type if hasattr(n, 'note_type') else None,
                    'createdAt': n.created_at.isoformat() if n.created_at else None,
                }
                for n in (notes or [])
            ],
            'referral': {
                'id': referral.id,
                'name': referral.name,
                'company': referral.company.name if referral.company else None,
            } if referral else None,
        }
        return _cors_response({'success': True, 'application': result})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/dashboard/stats', methods=['GET', 'OPTIONS'])
def api_dashboard_stats():
    """API: Get dashboard summary statistics."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        dashboard = service.get_dashboard()
        result = {
            'activeApplications': dashboard['summary']['active_applications'],
            'totalApplications': dashboard['summary']['total_applications'],
            'eventsToday': dashboard['summary']['events_today'],
            'interviewRate': dashboard['metrics']['interview_rate'],
            'interviewedCount': dashboard['metrics']['interviewed_count'],
            'responseRate': dashboard['metrics']['response_rate'],
            'contactsNeedFollowup': dashboard['summary']['contacts_need_followup'],
            'appsAwaitingResponse': dashboard['summary']['apps_awaiting_response'],
            'staleLeads': dashboard['summary']['stale_leads'],
            'appsThisWeek': dashboard['metrics']['apps_this_week'],
            'weeklyChange': dashboard['metrics']['weekly_change'],
            'byStatus': dashboard.get('stats', {}).get('by_status', {}),
        }
        return _cors_response({'success': True, 'stats': result})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()


@bp.route('/api/events/upcoming', methods=['GET', 'OPTIONS'])
def api_upcoming_events():
    """API: Get upcoming events (interviews, deadlines, etc.)."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        days = request.args.get('days', 14, type=int)
        events = service.events.get_upcoming(days=days)
        items = []
        for ev in events:
            app_title = None
            company_name = None
            if ev.application and ev.application.job:
                app_title = ev.application.job.title
                if ev.application.job.company:
                    company_name = ev.application.job.company.name
            items.append({
                'id': ev.id,
                'title': ev.title,
                'eventType': ev.event_type.value if ev.event_type else None,
                'startTime': ev.start_time.isoformat() if ev.start_time else None,
                'endTime': ev.end_time.isoformat() if ev.end_time else None,
                'location': ev.location,
                'meetingLink': ev.meeting_link,
                'applicationTitle': app_title,
                'companyName': company_name,
            })
        return _cors_response({'success': True, 'events': items})
    except Exception as e:
        current_app.logger.exception('API error')
        return _cors_response({'success': False, 'error': 'Internal server error'}, 500)
    finally:
        session.close()
