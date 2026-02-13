"""API routes for AJAX operations and Chrome extension."""
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..helpers import get_service, get_service_for_user, get_user_by_api_key
from ...models import ApplicationStatus, ContactType, Application, Job, Company, Contact, InterviewPrep
from ...services.ai_parser import is_ai_parsing_available, parse_job_description, analyze_resume_job_fit, generate_cover_letter, generate_interview_prep

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


@bp.route('/api/jobs/<int:job_id>', methods=['PATCH', 'OPTIONS'])
def api_update_job(job_id):
    """API: Update job fields."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
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
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        job = service.jobs.update(job_id, **data)
        session.commit()
        if job:
            response = jsonify({'success': True})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        response = jsonify({'success': False, 'error': 'Not found'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 404
    finally:
        session.close()


@bp.route('/api/companies/<int:company_id>', methods=['PATCH', 'OPTIONS'])
def api_update_company(company_id):
    """API: Update company fields."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
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
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        data = request.get_json()
        company = service.companies.update(company_id, **data)
        session.commit()
        if company:
            response = jsonify({'success': True})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        response = jsonify({'success': False, 'error': 'Not found'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 404
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


@bp.route('/api/contacts', methods=['GET', 'OPTIONS'])
def api_list_contacts():
    """API: List all contacts with optional search/followup filter."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
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
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        response = jsonify({'success': False, 'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
    finally:
        session.close()


@bp.route('/api/contacts/<int:contact_id>', methods=['GET', 'OPTIONS'])
def api_get_contact(contact_id):
    """API: Get a single contact by ID."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        c = service.contacts.get_by_id(contact_id)
        if not c:
            response = jsonify({'success': False, 'error': 'Contact not found'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 404

        response = jsonify({
            'success': True,
            'contact': {
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
                'updatedAt': c.updated_at.isoformat() if hasattr(c, 'updated_at') and c.updated_at else None,
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


@bp.route('/api/contacts/<int:contact_id>', methods=['DELETE', 'OPTIONS'])
def api_delete_contact(contact_id):
    """API: Delete a contact by ID."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return response

    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required. Provide X-API-Key header.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        c = service.contacts.get_by_id(contact_id)
        if not c:
            response = jsonify({'success': False, 'error': 'Contact not found'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 404

        session.delete(c)
        session.commit()
        response = jsonify({'success': True, 'deleted': contact_id})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        session.rollback()
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
        
        # Auto-score job if user has resume and AI is available
        if is_ai_parsing_available() and user.resume_text and len(user.resume_text.strip()) > 100:
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

        # Save the fit score to the application
        if app_id and result.get('match_score') is not None:
            service.applications.update(app_id, fit_score=result['match_score'])
            session.commit()

        return jsonify({'success': True, 'analysis': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
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
        return jsonify({'success': False, 'error': str(e)}), 500
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
                scored_count += 1
            except Exception as e:
                errors.append(f"Job {job.id} ({job.title}): {str(e)}")

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
        return jsonify({'success': False, 'error': str(e)}), 500
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
            return jsonify({'success': False, 'error': f'AI generation failed: {str(e)}'}), 500

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
        session.commit()

        return jsonify({
            'success': True,
            'prep': interview_prep.to_dict()
        })

    except Exception as e:
        logging.error(f"Interview prep error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/api/contacts/search')
def api_contacts_search():
    """API: Search contacts by name for @mention autocomplete."""
    api_key = request.headers.get('X-API-Key')
    user = get_user_by_api_key(api_key) if api_key else None
    if not user and current_user.is_authenticated:
        user = current_user
    if not user:
        response = jsonify({'success': False, 'error': 'Authentication required.'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401

    service, session = get_service_for_user(user.id)
    try:
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'success': True, 'contacts': []})
        contacts = service.contacts.search_by_name(q)
        response = jsonify({
            'success': True,
            'contacts': [
                {
                    'id': c.id,
                    'name': c.name,
                    'companyName': c.company.name if c.company else None
                }
                for c in contacts[:10]
            ]
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
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
    from sqlalchemy import inspect, text

    result = {
        'status': 'ok',
        'checks': {}
    }

    try:
        db = current_app.extensions.get('db')
        if db:
            result['checks']['database'] = 'connected'

            try:
                inspector = inspect(db.engine)
                # Check users table columns
                if 'users' in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns('users')]
                    result['checks']['users_columns'] = columns
                else:
                    result['checks']['users_table'] = 'missing'

                # Check applications table columns
                if 'applications' in inspector.get_table_names():
                    app_columns = [col['name'] for col in inspector.get_columns('applications')]
                    result['checks']['applications_columns'] = app_columns
                else:
                    result['checks']['applications_table'] = 'missing'
            except Exception as e:
                result['checks']['schema_check'] = str(e)
        else:
            result['checks']['database'] = 'not configured'
    except Exception as e:
        result['checks']['database_error'] = str(e)

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
    
    # Verify cron secret (optional but recommended)
    cron_secret = os.environ.get('CRON_SECRET')
    provided_secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')
    
    if cron_secret and provided_secret != cron_secret:
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({
            'success': False,
            'error': str(e)
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
        logging.error(f"Global search error: {e}")
        return jsonify({'results': [], 'error': str(e)}), 500
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
        response.headers['Access-Control-Allow-Origin'] = '*'
        return None, (response, 401)
    return user, None


def _cors_response(data, status=200):
    """Create a JSON response with CORS headers."""
    response = jsonify(data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, status


def _cors_options():
    """Handle CORS preflight for GET endpoints."""
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
    return response


@bp.route('/api/contacts', methods=['GET', 'OPTIONS'])
def api_list_contacts():
    """API: Get all contacts with company info."""
    if request.method == 'OPTIONS':
        return _cors_options()

    user, err = _api_key_or_session_auth()
    if err:
        return err

    service, session = get_service_for_user(user.id)
    try:
        limit = request.args.get('limit', 100, type=int)
        contacts = service.contacts.get_all(limit=limit)
        items = []
        for c in contacts:
            items.append({
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
            })
        return _cors_response({'success': True, 'contacts': items})
    except Exception as e:
        return _cors_response({'success': False, 'error': str(e)}, 500)
    finally:
        session.close()


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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
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
        return _cors_response({'success': False, 'error': str(e)}, 500)
    finally:
        session.close()
