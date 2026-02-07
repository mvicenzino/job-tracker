"""API routes for AJAX operations and Chrome extension."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from ..helpers import get_service, get_service_for_user, get_user_by_api_key
from ...models import ApplicationStatus, ContactType
from ...services.ai_parser import is_ai_parsing_available, parse_job_description, analyze_resume_job_fit, generate_cover_letter

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
            review_url = f"/applications/{application.id}/review"
        
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
    from ...models import Application, Job, Company, Contact
    import logging
    
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
                    'url': f"/contacts/{contact.id}"
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
                    'url': f"/companies/{company.id}"
                })
        except Exception as e:
            logging.error(f"Search companies error: {e}")
        
        return jsonify({'results': results[:10]})  # Max 10 total results
        
    except Exception as e:
        logging.error(f"Global search error: {e}")
        return jsonify({'results': [], 'error': str(e)}), 500
    finally:
        session.close()
