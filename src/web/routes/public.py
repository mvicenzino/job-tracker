"""Public routes: landing, privacy, terms, demo."""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import current_user, login_user

from ...services import JobHuntService
from ...models import ApplicationStatus, EventType, ContactType, User, ChecklistItem

bp = Blueprint('public', __name__)


@bp.route('/')
def landing():
    """Landing page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('landing.html')


@bp.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('privacy.html')


@bp.route('/terms')
def terms():
    """Terms of Service page."""
    return render_template('terms.html')


@bp.route('/demo')
def demo():
    """Demo mode - log in as demo user with sample data."""
    from flask import request
    DEMO_EMAIL = 'demo@stride-jobs.com'
    DEMO_PASSWORD = 'demo-user-2024'

    db = current_app.extensions['db']
    session = db.get_session()
    try:
        # Find or create demo user
        demo_user = session.query(User).filter(User.email == DEMO_EMAIL).first()

        if not demo_user:
            demo_user = User(email=DEMO_EMAIL)
            demo_user.set_password(DEMO_PASSWORD)
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)

        # Check if demo data needs to be created or refreshed
        service = JobHuntService(session, user_id=demo_user.id)
        existing_apps = service.applications.get_all()
        force_refresh = request.args.get('refresh') == '1'

        if len(existing_apps) == 0 or force_refresh:
            # Clear existing data for fresh demo using raw SQL to avoid ORM cascade issues
            from sqlalchemy import text

            # Delete in correct order: children before parents
            session.execute(text(f"DELETE FROM checklist_items WHERE application_id IN (SELECT id FROM applications WHERE user_id = {demo_user.id})"))
            session.execute(text(f"DELETE FROM notes WHERE application_id IN (SELECT id FROM applications WHERE user_id = {demo_user.id})"))
            session.execute(text(f"DELETE FROM events WHERE user_id = {demo_user.id}"))
            session.execute(text(f"DELETE FROM applications WHERE user_id = {demo_user.id}"))
            session.execute(text(f"DELETE FROM jobs WHERE company_id IN (SELECT id FROM companies WHERE user_id = {demo_user.id})"))
            session.execute(text(f"DELETE FROM contacts WHERE user_id = {demo_user.id}"))
            session.execute(text(f"DELETE FROM companies WHERE user_id = {demo_user.id}"))
            session.commit()

            # Refresh service after clearing data
            service = JobHuntService(session, user_id=demo_user.id)

            # Create sample companies - diverse industries and sizes
            companies_data = [
                {'name': 'Stripe', 'industry': 'FinTech', 'size': '5000-10000', 'location': 'San Francisco, CA', 'website': 'https://stripe.com', 'description': 'Financial infrastructure for the internet'},
                {'name': 'Notion', 'industry': 'Productivity', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://notion.so', 'description': 'All-in-one workspace for notes, docs, and collaboration'},
                {'name': 'Figma', 'industry': 'Design Tools', 'size': '1000-2000', 'location': 'San Francisco, CA', 'website': 'https://figma.com', 'description': 'Collaborative interface design tool'},
                {'name': 'Vercel', 'industry': 'Developer Tools', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://vercel.com', 'description': 'Frontend cloud platform'},
                {'name': 'Linear', 'industry': 'Developer Tools', 'size': '50-100', 'location': 'San Francisco, CA', 'website': 'https://linear.app', 'description': 'Modern issue tracking for high-performance teams'},
                {'name': 'Rippling', 'industry': 'HR Tech', 'size': '1000-3000', 'location': 'San Francisco, CA', 'website': 'https://rippling.com', 'description': 'Employee management platform'},
                {'name': 'Anthropic', 'industry': 'AI/ML', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://anthropic.com', 'description': 'AI safety and research company'},
                {'name': 'Databricks', 'industry': 'Data & Analytics', 'size': '5000-10000', 'location': 'San Francisco, CA', 'website': 'https://databricks.com', 'description': 'Unified analytics platform'},
                {'name': 'Retool', 'industry': 'Developer Tools', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://retool.com', 'description': 'Build internal tools fast'},
                {'name': 'Ramp', 'industry': 'FinTech', 'size': '500-1000', 'location': 'New York, NY', 'website': 'https://ramp.com', 'description': 'Corporate card and spend management'},
                {'name': 'Plaid', 'industry': 'FinTech', 'size': '1000-2000', 'location': 'San Francisco, CA', 'website': 'https://plaid.com', 'description': 'Financial data connectivity'},
                {'name': 'Mercury', 'industry': 'FinTech', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://mercury.com', 'description': 'Banking for startups'},
                {'name': 'Airtable', 'industry': 'Productivity', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://airtable.com', 'description': 'Low-code platform for building apps'},
                {'name': 'Webflow', 'industry': 'Design Tools', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://webflow.com', 'description': 'Visual web development platform'},
                {'name': 'Scale AI', 'industry': 'AI/ML', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://scale.com', 'description': 'Data platform for AI'},
            ]

            companies = []
            for data in companies_data:
                company = service.add_company(**data)
                companies.append(company)

            # Create jobs with realistic titles and compensation
            jobs_data = [
                # Active opportunities - various stages
                {'company': companies[0], 'title': 'Senior Software Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 200000, 'salary_max': 280000, 'source': 'Referral'},
                {'company': companies[1], 'title': 'Staff Engineer, Platform', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 220000, 'salary_max': 300000, 'source': 'LinkedIn'},
                {'company': companies[2], 'title': 'Senior Frontend Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 180000, 'salary_max': 250000, 'source': 'Company Website'},
                {'company': companies[3], 'title': 'Software Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 170000, 'salary_max': 230000, 'source': 'LinkedIn'},
                {'company': companies[4], 'title': 'Founding Engineer', 'location': 'San Francisco, CA', 'remote_type': 'onsite', 'salary_min': 180000, 'salary_max': 240000, 'source': 'Referral'},
                {'company': companies[5], 'title': 'Senior Backend Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 190000, 'salary_max': 260000, 'source': 'Recruiter'},
                {'company': companies[6], 'title': 'Research Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 250000, 'salary_max': 350000, 'source': 'Company Website'},
                {'company': companies[7], 'title': 'Staff Data Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 230000, 'salary_max': 320000, 'source': 'LinkedIn'},
                {'company': companies[8], 'title': 'Full Stack Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 175000, 'salary_max': 240000, 'source': 'AngelList'},
                {'company': companies[9], 'title': 'Senior Software Engineer', 'location': 'New York, NY', 'remote_type': 'hybrid', 'salary_min': 200000, 'salary_max': 270000, 'source': 'Referral'},
                # Saved for later / researching
                {'company': companies[10], 'title': 'Staff Engineer, Payments', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 240000, 'salary_max': 330000, 'source': 'LinkedIn'},
                {'company': companies[11], 'title': 'Senior Software Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 180000, 'salary_max': 250000, 'source': 'Company Website'},
                {'company': companies[12], 'title': 'Platform Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 185000, 'salary_max': 255000, 'source': 'Indeed'},
                {'company': companies[13], 'title': 'Senior Full Stack Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 175000, 'salary_max': 245000, 'source': 'LinkedIn'},
                {'company': companies[14], 'title': 'ML Platform Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 210000, 'salary_max': 290000, 'source': 'Recruiter'},
            ]

            jobs = []
            for data in jobs_data:
                company = data.pop('company')
                job = service.jobs.create(company_id=company.id, **data)
                jobs.append(job)

            # Create applications with realistic pipeline distribution
            # Shows a healthy job search with activity at every stage
            application_configs = [
                # OFFER stage - exciting!
                {'job_idx': 0, 'status': ApplicationStatus.OFFER, 'days_ago': 25, 'excitement': 5},
                # NEGOTIATING - actively discussing terms
                {'job_idx': 6, 'status': ApplicationStatus.NEGOTIATING, 'days_ago': 30, 'excitement': 5},
                # FINAL_ROUND - close to finish line
                {'job_idx': 1, 'status': ApplicationStatus.FINAL_ROUND, 'days_ago': 21, 'excitement': 4},
                {'job_idx': 7, 'status': ApplicationStatus.FINAL_ROUND, 'days_ago': 18, 'excitement': 4},
                # INTERVIEWING - in the thick of it
                {'job_idx': 2, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 14, 'excitement': 4},
                {'job_idx': 4, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 12, 'excitement': 5},
                {'job_idx': 9, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 10, 'excitement': 3},
                # SCREENING - early conversations
                {'job_idx': 3, 'status': ApplicationStatus.SCREENING, 'days_ago': 8, 'excitement': 3},
                {'job_idx': 5, 'status': ApplicationStatus.SCREENING, 'days_ago': 6, 'excitement': 4},
                # APPLIED - waiting to hear back (some stale for "needs attention")
                {'job_idx': 8, 'status': ApplicationStatus.APPLIED, 'days_ago': 18, 'excitement': 3},  # Stale - needs attention
                # PREPARING - working on application
                {'job_idx': 10, 'status': ApplicationStatus.PREPARING, 'days_ago': 2, 'excitement': 4},
                {'job_idx': 14, 'status': ApplicationStatus.PREPARING, 'days_ago': 1, 'excitement': 5},
                # INTERESTED - saved for later
                {'job_idx': 11, 'status': ApplicationStatus.INTERESTED, 'days_ago': 5, 'excitement': 3},
                {'job_idx': 12, 'status': ApplicationStatus.INTERESTED, 'days_ago': 3, 'excitement': 3},
                {'job_idx': 13, 'status': ApplicationStatus.INTERESTED, 'days_ago': 1, 'excitement': 4},
            ]

            apps = []
            for config in application_configs:
                job = jobs[config['job_idx']]
                app = service.apply_to_job(job_id=job.id)
                service.update_application_status(app.id, config['status'])
                app.date_applied = date.today() - timedelta(days=config['days_ago'])
                app.excitement_level = config['excitement']
                apps.append(app)

            # Set offer details on the offer
            apps[0].offered_salary = 260000
            apps[0].offered_bonus = 50000
            apps[0].offered_equity = '0.05% over 4 years'

            # Create sample contacts - networking is key!
            contacts_data = [
                {'name': 'Alex Rivera', 'company_name': 'Stripe', 'title': 'Engineering Manager', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'alex.r@stripe.com', 'linkedin_url': 'https://linkedin.com/in/alexrivera', 'notes': 'Met at SF Tech Meetup. Very responsive.'},
                {'name': 'Jordan Lee', 'company_name': 'Notion', 'title': 'Staff Engineer', 'contact_type': ContactType.REFERRAL, 'email': 'jordan.l@notion.so', 'linkedin_url': 'https://linkedin.com/in/jordanlee', 'notes': 'Former colleague from Dropbox. Offered to refer me.'},
                {'name': 'Sam Chen', 'company_name': 'Figma', 'title': 'Technical Recruiter', 'contact_type': ContactType.RECRUITER, 'email': 'sam.c@figma.com', 'linkedin_url': 'https://linkedin.com/in/samchen', 'notes': 'Very helpful, keeps me updated on process.'},
                {'name': 'Taylor Kim', 'company_name': 'Linear', 'title': 'Co-founder', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'taylor@linear.app', 'linkedin_url': 'https://linkedin.com/in/taylorkim', 'notes': 'Reached out after seeing my open source work.'},
                {'name': 'Morgan Walsh', 'company_name': 'Anthropic', 'title': 'Research Lead', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'morgan.w@anthropic.com', 'linkedin_url': 'https://linkedin.com/in/morganwalsh', 'notes': 'Had great chat about AI safety research.'},
                {'name': 'Casey Park', 'company_name': 'Ramp', 'title': 'Senior Recruiter', 'contact_type': ContactType.RECRUITER, 'email': 'casey.p@ramp.com', 'linkedin_url': 'https://linkedin.com/in/caseypark', 'notes': 'Proactive about scheduling and updates.'},
                {'name': 'Jamie Torres', 'company_name': 'Databricks', 'title': 'Principal Engineer', 'contact_type': ContactType.EMPLOYEE, 'email': 'jamie.t@databricks.com', 'linkedin_url': 'https://linkedin.com/in/jamietorres', 'notes': 'Coffee chat to learn about the team.'},
                {'name': 'Riley Nguyen', 'company_name': 'Vercel', 'title': 'Engineering Lead', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'riley.n@vercel.com', 'linkedin_url': 'https://linkedin.com/in/rileynguyen', 'notes': 'Discussed Next.js and edge computing.'},
            ]

            created_contacts = []
            for data in contacts_data:
                created_contacts.append(service.add_contact(**data))

            # Set follow-up dates - some overdue for "Needs Attention"
            created_contacts[0].next_followup_date = date.today() - timedelta(days=2)  # Overdue
            created_contacts[0].last_contact_date = date.today() - timedelta(days=9)
            created_contacts[1].next_followup_date = date.today() - timedelta(days=1)  # Overdue
            created_contacts[1].last_contact_date = date.today() - timedelta(days=8)
            created_contacts[2].next_followup_date = date.today()  # Due today
            created_contacts[2].last_contact_date = date.today() - timedelta(days=5)
            created_contacts[3].next_followup_date = date.today() + timedelta(days=2)  # Upcoming
            created_contacts[3].last_contact_date = date.today() - timedelta(days=3)
            created_contacts[4].next_followup_date = date.today() - timedelta(days=3)  # Overdue
            created_contacts[4].last_contact_date = date.today() - timedelta(days=10)
            created_contacts[5].next_followup_date = date.today() + timedelta(days=1)  # Tomorrow
            created_contacts[5].last_contact_date = date.today() - timedelta(days=4)
            created_contacts[6].next_followup_date = date.today() - timedelta(days=1)  # Overdue
            created_contacts[6].last_contact_date = date.today() - timedelta(days=7)

            # Create sample events - busy interview schedule!
            today_base = datetime.now().replace(minute=0, second=0, microsecond=0)
            events_data = [
                # TODAY - action-packed day
                {'title': 'Recruiter Sync - Ramp', 'event_type': EventType.PHONE_SCREEN, 'start_time': today_base.replace(hour=9), 'meeting_link': 'https://zoom.us/j/ramp123', 'prep_notes': 'Discuss timeline and next steps. Ask about team culture.'},
                {'title': 'System Design - Stripe', 'event_type': EventType.TECHNICAL_INTERVIEW, 'start_time': today_base.replace(hour=11), 'meeting_link': 'https://meet.google.com/stripe-design', 'prep_notes': 'Design a payment processing system. Review distributed systems concepts.'},
                {'title': 'Coffee Chat - Jamie (Databricks)', 'event_type': EventType.COFFEE_CHAT, 'start_time': today_base.replace(hour=12, minute=30), 'location': 'Sightglass Coffee, SOMA'},
                {'title': 'Hiring Manager Call - Anthropic', 'event_type': EventType.VIDEO_INTERVIEW, 'start_time': today_base.replace(hour=14), 'meeting_link': 'https://meet.google.com/anthropic-hm', 'prep_notes': 'Discuss research interests and team fit. Bring questions about safety research.'},
                {'title': 'Take-Home Due - Linear', 'event_type': EventType.APPLICATION_DEADLINE, 'start_time': today_base.replace(hour=18), 'prep_notes': 'Submit React component library challenge. Polish documentation.'},

                # TOMORROW
                {'title': 'Final Round Prep', 'event_type': EventType.REMINDER, 'start_time': today_base + timedelta(days=1, hours=9), 'prep_notes': 'Review Notion architecture and prepare STAR stories.'},
                {'title': 'Panel Interview - Notion', 'event_type': EventType.PANEL_INTERVIEW, 'start_time': today_base + timedelta(days=1, hours=10), 'meeting_link': 'https://zoom.us/j/notion-panel', 'prep_notes': '4 interviewers: 2 engineers, PM, design. Focus on collaboration stories.'},
                {'title': 'Networking Event - SF Tech', 'event_type': EventType.NETWORKING_EVENT, 'start_time': today_base + timedelta(days=1, hours=18), 'location': 'The Pearl, SOMA', 'prep_notes': 'Bring business cards. Target: meet 3 new connections.'},

                # THIS WEEK
                {'title': 'Offer Discussion - Stripe', 'event_type': EventType.OFFER_CALL, 'start_time': today_base + timedelta(days=2, hours=11), 'meeting_link': 'https://meet.google.com/stripe-offer', 'prep_notes': 'Review comp package. Prepare counter-offer talking points.'},
                {'title': 'Technical Deep Dive - Figma', 'event_type': EventType.TECHNICAL_INTERVIEW, 'start_time': today_base + timedelta(days=2, hours=14), 'meeting_link': 'https://zoom.us/j/figma-tech', 'prep_notes': 'Focus on frontend architecture and performance.'},
                {'title': 'Follow up - Alex (Stripe)', 'event_type': EventType.FOLLOW_UP, 'start_time': today_base + timedelta(days=3, hours=10), 'prep_notes': 'Send thank you note and ask about timeline.'},
                {'title': 'Final Round - Databricks', 'event_type': EventType.ONSITE_INTERVIEW, 'start_time': today_base + timedelta(days=4, hours=9), 'location': 'Databricks HQ, 160 Spear St', 'prep_notes': 'Full day: 5 rounds. Wear comfortable shoes!'},
                {'title': 'Culture Chat - Vercel', 'event_type': EventType.BEHAVIORAL_INTERVIEW, 'start_time': today_base + timedelta(days=5, hours=15), 'meeting_link': 'https://zoom.us/j/vercel-culture'},

                # NEXT WEEK
                {'title': 'Negotiation Call - Anthropic', 'event_type': EventType.NEGOTIATION_CALL, 'start_time': today_base + timedelta(days=7, hours=10), 'prep_notes': 'Discuss equity and start date flexibility.'},
                {'title': 'Meet the Team - Linear', 'event_type': EventType.PANEL_INTERVIEW, 'start_time': today_base + timedelta(days=8, hours=11), 'meeting_link': 'https://zoom.us/j/linear-team'},
            ]

            for data in events_data:
                service.schedule_event(**data)

            session.commit()

        # Log in as demo user
        login_user(demo_user, remember=False)
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        session.rollback()
        import traceback
        return f'<pre>Demo error: {str(e)}\n\n{traceback.format_exc()}</pre>', 500
    finally:
        session.close()
